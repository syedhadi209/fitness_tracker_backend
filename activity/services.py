from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from progress.calculations import exercise_calories, step_calories
from progress.services import current_weight_kg

from .models import EntrySource, ExerciseType, StepLog, WorkoutLog

DEFAULT_MET = Decimal("4.0")


def _resolve_met(description, met_value):
    """Prefer an explicit MET, then the catalogue, then a moderate-effort default."""
    if met_value:
        return Decimal(str(met_value))

    match = ExerciseType.objects.filter(name__iexact=description).first()
    if match:
        return match.met_value

    match = ExerciseType.objects.filter(name__icontains=description.split()[0]).first()
    return match.met_value if match else DEFAULT_MET


@transaction.atomic
def log_workout(
    user,
    description,
    duration_minutes,
    met_value=None,
    date=None,
    raw_text="",
    source=EntrySource.MANUAL,
    source_message=None,
):
    """Record a workout, computing the burn server-side from the user's bodyweight."""
    date = date or timezone.localdate()
    met = _resolve_met(description, met_value)
    weight = current_weight_kg(user, date)

    return WorkoutLog.objects.create(
        user=user,
        date=date,
        exercise_type=ExerciseType.objects.filter(name__iexact=description).first(),
        description=description,
        duration_minutes=Decimal(str(duration_minutes)),
        met_value=met,
        calories_burned=exercise_calories(met, weight, duration_minutes),
        raw_text=raw_text or "",
        source=source or EntrySource.MANUAL,
        source_message=source_message,
    )


@transaction.atomic
def set_steps(user, steps, date=None, source=EntrySource.MANUAL, source_message=None):
    """Set the step count for a day, replacing any existing entry.

    Upserts rather than erroring on a duplicate day, since re-reporting a running
    total is the natural way to talk about steps.
    """
    date = date or timezone.localdate()
    weight = current_weight_kg(user, date)

    entry, _ = StepLog.objects.update_or_create(
        user=user,
        date=date,
        defaults={
            "steps": steps,
            "calories_burned": step_calories(steps, weight),
            "source": source or EntrySource.MANUAL,
            "source_message": source_message,
        },
    )
    return entry
