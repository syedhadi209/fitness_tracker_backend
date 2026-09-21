"""Builds the per-user system prompt for the assistant.

Everything here is derived from the requesting user only. The date and timezone
matter as much as the fitness data: without them the model cannot resolve
"yesterday" or "this morning", which is how people actually describe their logs.
"""

from datetime import timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from django.utils import timezone

from activity.models import WorkoutLog
from nutrition.models import MealLog
from progress import aggregation
from progress.models import WeightLog

RECENT_ENTRY_LIMIT = 10

SYSTEM_PROMPT = """You are a friendly, concise fitness coach inside a tracking app. \
The user talks to you the way they would message a personal trainer.

Your job:
- When the user mentions food they ate, exercise they did, steps they took, or their \
weight, log it immediately using the tools. Do not ask for confirmation first.
- Estimate calories and macros from your own nutrition knowledge. Be realistic about \
portion sizes. If a description is too vague to estimate at all (for example "I ate \
lunch"), ask one short clarifying question instead of guessing wildly.
- For exercise, supply a MET value; the app computes the calorie burn from the user's \
bodyweight.
- When the user corrects something they just logged, use update_entry or delete_entry \
with the id from the recent entries listed below.
- When the user asks how they are doing, use get_progress rather than guessing.

Keep replies short and conversational, like a text message. After logging something, \
confirm what you recorded with the key numbers.
"""


def _user_today(profile):
    if profile and profile.timezone:
        try:
            return timezone.now().astimezone(ZoneInfo(profile.timezone)).date()
        except (ZoneInfoNotFoundError, ValueError):
            pass
    return timezone.localdate()


def _profile_block(user, profile, today):
    if profile is None:
        return "The user has not filled in their profile yet."

    weight = aggregation.current_weight_kg(user, today)
    lines = [
        f"Weight: {weight} kg",
        f"Goal: {profile.get_goal_display()}",
        f"Activity level: {profile.get_activity_level_display()}",
    ]
    if profile.height_cm:
        lines.append(f"Height: {profile.height_cm} cm")
    if profile.age is not None:
        lines.append(f"Age: {profile.age}")
    if profile.sex:
        lines.append(f"Sex: {profile.get_sex_display()}")
    if profile.target_weight_kg:
        lines.append(f"Target weight: {profile.target_weight_kg} kg")
    return "\n".join(lines)


def _recent_entries_block(user, today):
    """Recent ids so the model has something real to reference when amending."""
    since = today - timedelta(days=2)
    lines = []

    for meal in MealLog.objects.filter(user=user, date__gte=since).prefetch_related("items")[
        :RECENT_ENTRY_LIMIT
    ]:
        foods = ", ".join(item.description for item in meal.items.all())
        lines.append(f"meal id={meal.id} date={meal.date} {meal.meal_type}: {foods}")

    for workout in WorkoutLog.objects.filter(user=user, date__gte=since)[:RECENT_ENTRY_LIMIT]:
        lines.append(
            f"workout id={workout.id} date={workout.date}: {workout.description} "
            f"{workout.duration_minutes}min"
        )

    for weight in WeightLog.objects.filter(user=user, date__gte=since)[:RECENT_ENTRY_LIMIT]:
        lines.append(f"weight id={weight.id} date={weight.date}: {weight.weight_kg}kg")

    return "\n".join(lines) if lines else "No entries in the last few days."


def build_system_prompt(user):
    profile = getattr(user, "profile", None)
    today = _user_today(profile)
    tz_name = profile.timezone if profile else "UTC"

    today_data = aggregation.dashboard(user, today)
    consumed = today_data["consumed"]
    burned = today_data["burned"]
    week = aggregation.recent_summary(user, days=7)

    return "\n\n".join(
        [
            SYSTEM_PROMPT,
            f"Today's date is {today.isoformat()} ({today.strftime('%A')}). "
            f"The user's timezone is {tz_name}. Use this to resolve relative dates such as "
            f'"yesterday" or "this morning".',
            f"USER PROFILE\n{_profile_block(user, profile, today)}",
            (
                "TODAY SO FAR\n"
                f"Consumed: {consumed['calories']:.0f} kcal "
                f"(protein {consumed['protein_g']:.0f}g, carbs {consumed['carbs_g']:.0f}g, "
                f"fat {consumed['fat_g']:.0f}g)\n"
                f"Burned: {burned['total']:.0f} kcal "
                f"(exercise {burned['exercise']:.0f}, {burned['step_count']} steps)\n"
                f"Calorie target: {today_data['targets']['calories'] or 'not set'}"
            ),
            (
                "LAST 7 DAYS\n"
                f"Average consumed: {week['avg_consumed']:.0f} kcal/day\n"
                f"Average burned: {week['avg_burned']:.0f} kcal/day"
            ),
            f"RECENT ENTRIES (use these ids to amend or delete)\n{_recent_entries_block(user, today)}",
        ]
    )
