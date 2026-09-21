"""Read-side aggregation for the dashboard and progress charts."""

from datetime import timedelta
from decimal import Decimal

from django.db.models import Sum
from django.utils import timezone

from activity.models import StepLog, WorkoutLog
from nutrition.models import MealItem

from .calculations import bmr_mifflin_st_jeor, goal_calorie_target, tdee
from .models import WeightLog
from .services import current_weight_kg

ZERO = Decimal("0")


def _sum(queryset, field):
    return queryset.aggregate(total=Sum(field))["total"] or ZERO


def consumed_totals(user, date):
    """Calories and macros eaten on a given day."""
    items = MealItem.objects.filter(meal__user=user, meal__date=date)
    return {
        "calories": _sum(items, "calories"),
        "protein_g": _sum(items, "protein_g"),
        "carbs_g": _sum(items, "carbs_g"),
        "fat_g": _sum(items, "fat_g"),
    }


def burned_totals(user, date):
    """Calories burned through logged workouts and steps."""
    workouts = _sum(WorkoutLog.objects.filter(user=user, date=date), "calories_burned")
    steps_entry = StepLog.objects.filter(user=user, date=date).first()
    steps_burn = steps_entry.calories_burned if steps_entry else ZERO

    return {
        "exercise": workouts,
        "steps": steps_burn,
        "step_count": steps_entry.steps if steps_entry else 0,
        "total": workouts + steps_burn,
    }


def daily_targets(user, date):
    """Explicit profile targets, else TDEE, shifted by goal pace when set."""
    profile = getattr(user, "profile", None)
    if profile is None:
        return {"calories": None, "protein_g": None, "carbs_g": None, "fat_g": None, "bmr": None}

    bmr = None
    weight = current_weight_kg(user, date)
    if weight and profile.height_cm and profile.age is not None and profile.sex:
        bmr = bmr_mifflin_st_jeor(
            weight_kg=weight,
            height_cm=profile.height_cm,
            age_years=profile.age,
            sex=profile.sex,
        )

    calorie_target = profile.daily_calorie_target
    if calorie_target is None and bmr is not None:
        maintenance = tdee(bmr, profile.activity_level)
        if profile.goal != "maintain" and profile.target_weight_kg and profile.goal_duration_weeks:
            calorie_target = goal_calorie_target(
                maintenance,
                weight,
                profile.target_weight_kg,
                profile.goal_duration_weeks,
                profile.sex,
            )
        else:
            calorie_target = int(maintenance)

    return {
        "calories": calorie_target,
        "protein_g": profile.daily_protein_target_g,
        "carbs_g": profile.daily_carbs_target_g,
        "fat_g": profile.daily_fat_target_g,
        "bmr": int(bmr) if bmr is not None else None,
    }


def dashboard(user, date=None):
    date = date or timezone.localdate()
    consumed = consumed_totals(user, date)
    burned = burned_totals(user, date)
    targets = daily_targets(user, date)

    remaining = None
    if targets["calories"] is not None:
        remaining = Decimal(targets["calories"]) - consumed["calories"] + burned["total"]

    return {
        "date": date,
        "consumed": consumed,
        "burned": burned,
        "net_calories": consumed["calories"] - burned["total"],
        "targets": targets,
        "calories_remaining": remaining,
        "weight_kg": current_weight_kg(user, date),
    }


def history(user, start, end, metric="calories"):
    """Date-bucketed series for the progress graphs."""
    if metric == "weight":
        rows = WeightLog.objects.filter(user=user, date__range=(start, end)).order_by("date")
        return [{"date": r.date, "weight_kg": r.weight_kg, "body_fat_pct": r.body_fat_pct} for r in rows]

    if metric == "steps":
        rows = StepLog.objects.filter(user=user, date__range=(start, end)).order_by("date")
        return [{"date": r.date, "steps": r.steps, "calories_burned": r.calories_burned} for r in rows]

    # Default: per-day calories in and out. Grouped in Python because the source
    # rows span three tables and the ranges here are days, not millions of rows.
    consumed_by_date = {
        row["meal__date"]: row["total"]
        for row in MealItem.objects.filter(meal__user=user, meal__date__range=(start, end))
        .values("meal__date")
        .annotate(total=Sum("calories"))
    }
    workouts_by_date = {
        row["date"]: row["total"]
        for row in WorkoutLog.objects.filter(user=user, date__range=(start, end))
        .values("date")
        .annotate(total=Sum("calories_burned"))
    }
    steps_by_date = {
        row.date: (row.steps, row.calories_burned)
        for row in StepLog.objects.filter(user=user, date__range=(start, end))
    }

    series = []
    day = start
    while day <= end:
        steps, step_burn = steps_by_date.get(day, (0, ZERO))
        burned = workouts_by_date.get(day, ZERO) + step_burn
        consumed = consumed_by_date.get(day, ZERO)
        series.append(
            {
                "date": day,
                "consumed": consumed,
                "burned": burned,
                "net": consumed - burned,
                "steps": steps,
            }
        )
        day += timedelta(days=1)

    return series


def recent_summary(user, days=7):
    """Compact recent history, used to give the assistant context."""
    end = timezone.localdate()
    start = end - timedelta(days=days - 1)
    series = history(user, start, end)

    if not series:
        return {"days": 0, "avg_consumed": ZERO, "avg_burned": ZERO}

    return {
        "days": len(series),
        "avg_consumed": sum(d["consumed"] for d in series) / len(series),
        "avg_burned": sum(d["burned"] for d in series) / len(series),
        "series": series,
    }
