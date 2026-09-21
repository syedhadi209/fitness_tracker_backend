"""Maps tool calls from the model onto the apps' service functions.

Two invariants hold here regardless of what the model asks for:

1. Every row is looked up with `user=user`, so an id the model invented or
   borrowed from another account resolves to nothing rather than someone
   else's data.
2. Execution is keyed by OpenRouter's `tool_call_id`, so a retried request
   cannot log the same meal twice.
"""

from datetime import date as date_cls
from datetime import datetime, timedelta
from decimal import Decimal

from django.db import IntegrityError, transaction
from django.utils import timezone

from activity.models import EntrySource, StepLog, WorkoutLog
from activity.services import log_workout, set_steps
from nutrition.models import FoodSource, MealItem, MealLog
from nutrition.services import create_meal
from progress import aggregation
from progress.models import WeightLog
from progress.services import set_weight

from .models import Role, ToolInvocation


class ToolError(Exception):
    """Reported back to the model as a tool result so it can recover in-conversation."""


ENTRY_MODELS = {
    "meal": MealLog,
    "workout": WorkoutLog,
    "steps": StepLog,
    "weight": WeightLog,
}


def _parse_date(value):
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        raise ToolError(f"Could not read '{value}' as a YYYY-MM-DD date.")


def _owned(user, entry_type, entry_id):
    """Fetch a row belonging to this user, or fail."""
    model = ENTRY_MODELS.get(entry_type)
    if model is None:
        raise ToolError(f"Unknown entry type '{entry_type}'.")

    instance = model.objects.filter(pk=entry_id, user=user).first()
    if instance is None:
        raise ToolError(f"No {entry_type} entry with id {entry_id} belongs to this user.")
    return instance


def _serialize_meal(meal):
    return {
        "entry_type": "meal",
        "id": meal.id,
        "date": meal.date.isoformat(),
        "meal_type": meal.meal_type,
        "items": [
            {
                "description": item.description,
                "calories": float(item.calories),
                "protein_g": float(item.protein_g),
                "carbs_g": float(item.carbs_g),
                "fat_g": float(item.fat_g),
            }
            for item in meal.items.all()
        ],
        "total_calories": float(sum(item.calories for item in meal.items.all())),
    }


# --- tool implementations ------------------------------------------------


def _log_meal(user, args, message):
    items = args.get("items") or []
    if not items:
        raise ToolError("No food items were provided.")

    meal = create_meal(
        user=user,
        items=items,
        meal_type=args.get("meal_type", "snack"),
        date=_parse_date(args.get("date")),
        raw_text=args.get("raw_text", ""),
        source=FoodSource.AI,
        source_message=message,
    )
    return _serialize_meal(meal)


def _latest_user_text(message):
    if message is None:
        return ""
    last = (
        message.session.messages.filter(role=Role.USER).order_by("-created_at", "-id").first()
    )
    return last.content if last else ""


def _log_exercise(user, args, message):
    original = args["description"]
    sets = args.get("sets")
    reps = args.get("reps")
    load_kg = args.get("load_kg")
    user_text = _latest_user_text(message)
    description = original
    if sets and reps:
        load = f" @ {load_kg}kg" if load_kg else ""
        description = f"{original} · {int(sets)}×{int(reps)}{load}"

    workout = log_workout(
        user=user,
        description=description,
        duration_minutes=args.get("duration_minutes"),
        met_value=args.get("met_value"),
        date=_parse_date(args.get("date")),
        source=EntrySource.AI,
        source_message=message,
        sets=sets,
        reps=reps,
        raw_text=user_text or original,
    )
    return {
        "entry_type": "workout",
        "id": workout.id,
        "date": workout.date.isoformat(),
        "description": workout.description,
        "duration_minutes": float(workout.duration_minutes),
        "calories_burned": float(workout.calories_burned),
    }


def _log_steps(user, args, message):
    entry = set_steps(
        user=user,
        steps=int(args["steps"]),
        date=_parse_date(args.get("date")),
        source=EntrySource.AI,
        source_message=message,
    )
    return {
        "entry_type": "steps",
        "id": entry.id,
        "date": entry.date.isoformat(),
        "steps": entry.steps,
        "calories_burned": float(entry.calories_burned),
    }


def _log_weight(user, args, message):
    entry = set_weight(
        user=user,
        weight_kg=args["weight_kg"],
        date=_parse_date(args.get("date")),
        body_fat_pct=args.get("body_fat_pct"),
        source_message=message,
    )
    return {
        "entry_type": "weight",
        "id": entry.id,
        "date": entry.date.isoformat(),
        "weight_kg": float(entry.weight_kg),
    }


def _jsonify(value):
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, date_cls):
        return value.isoformat()
    return value


def _get_progress(user, args, message):
    end = _parse_date(args.get("end_date")) or timezone.localdate()
    start = _parse_date(args.get("start_date")) or end - timedelta(days=6)
    metric = args.get("metric", "calories")

    results = aggregation.history(user, start, end, metric)
    return {
        "metric": metric,
        "start": start.isoformat(),
        "end": end.isoformat(),
        "results": [{k: _jsonify(v) for k, v in row.items()} for row in results],
    }


def _update_entry(user, args, message):
    entry_type = args["entry_type"]
    instance = _owned(user, entry_type, args["entry_id"])
    changes = args.get("changes") or {}

    if entry_type == "meal":
        if "items" in changes:
            instance.items.all().delete()
            for item in changes["items"]:
                MealItem.objects.create(
                    meal=instance,
                    description=item["description"],
                    quantity=Decimal(str(item.get("quantity", 1))),
                    unit=item.get("unit", ""),
                    calories=Decimal(str(item.get("calories", 0))),
                    protein_g=Decimal(str(item.get("protein_g", 0))),
                    carbs_g=Decimal(str(item.get("carbs_g", 0))),
                    fat_g=Decimal(str(item.get("fat_g", 0))),
                )
        if "meal_type" in changes:
            instance.meal_type = changes["meal_type"]
        if "date" in changes:
            instance.date = _parse_date(changes["date"])
        instance.save()
        return _serialize_meal(instance)

    if entry_type == "workout":
        # Re-run through the service so the burn is recomputed rather than patched.
        date = _parse_date(changes.get("date")) or instance.date
        replacement = log_workout(
            user=user,
            description=changes.get("description", instance.description),
            duration_minutes=changes.get("duration_minutes", instance.duration_minutes),
            met_value=changes.get("met_value", instance.met_value),
            date=date,
            source=instance.source,
            source_message=message,
        )
        instance.delete()
        return {
            "entry_type": "workout",
            "id": replacement.id,
            "calories_burned": float(replacement.calories_burned),
            "duration_minutes": float(replacement.duration_minutes),
        }

    if entry_type == "steps":
        entry = set_steps(
            user=user,
            steps=int(changes.get("steps", instance.steps)),
            date=_parse_date(changes.get("date")) or instance.date,
            source=instance.source,
            source_message=message,
        )
        return {"entry_type": "steps", "id": entry.id, "steps": entry.steps}

    entry = set_weight(
        user=user,
        weight_kg=changes.get("weight_kg", instance.weight_kg),
        date=_parse_date(changes.get("date")) or instance.date,
        body_fat_pct=changes.get("body_fat_pct", instance.body_fat_pct),
        source_message=message,
    )
    return {"entry_type": "weight", "id": entry.id, "weight_kg": float(entry.weight_kg)}


def _delete_entry(user, args, message):
    instance = _owned(user, args["entry_type"], args["entry_id"])
    instance.delete()
    return {"deleted": True, "entry_type": args["entry_type"], "id": args["entry_id"]}


HANDLERS = {
    "log_meal": _log_meal,
    "log_exercise": _log_exercise,
    "log_steps": _log_steps,
    "log_weight": _log_weight,
    "get_progress": _get_progress,
    "update_entry": _update_entry,
    "delete_entry": _delete_entry,
}

WRITE_TOOLS = {"log_meal", "log_exercise", "log_steps", "log_weight", "update_entry", "delete_entry"}


def execute(session, user, tool_call_id, name, arguments, message=None):
    """Run one tool call, at most once per tool_call_id."""
    handler = HANDLERS.get(name)
    if handler is None:
        return {"error": f"Unknown tool '{name}'."}

    existing = ToolInvocation.objects.filter(tool_call_id=tool_call_id).first()
    if existing:
        return existing.result

    try:
        with transaction.atomic():
            result = handler(user, arguments, message)
            ToolInvocation.objects.create(
                session=session,
                tool_call_id=tool_call_id,
                name=name,
                arguments=arguments,
                result=result,
            )
    except ToolError as exc:
        return {"error": str(exc)}
    except IntegrityError:
        # Lost a race against a concurrent identical call; reuse its result.
        existing = ToolInvocation.objects.filter(tool_call_id=tool_call_id).first()
        return existing.result if existing else {"error": "Could not record the tool call."}
    except (KeyError, TypeError, ValueError) as exc:
        return {"error": f"Invalid arguments for {name}: {exc}"}

    return result
