from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from progress.calculations import exercise_calories, step_calories
from progress.services import current_weight_kg

from .estimates import is_strength, resolve_duration, resolve_strength_met
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
    duration_minutes=None,
    met_value=None,
    date=None,
    raw_text="",
    source=EntrySource.MANUAL,
    source_message=None,
    sets=None,
    reps=None,
):
    """Record a workout, computing the burn server-side from the user's bodyweight.

    Sets × reps beat a guessed duration: 3×12 bench press is not a 30-minute MET session.
    """
    date = date or timezone.localdate()
    text = " ".join(part for part in (description, raw_text) if part)
    duration = resolve_duration(
        text, duration_minutes, sets=sets, reps=reps, source=source or EntrySource.MANUAL
    )

    met = _resolve_met(description, met_value)
    if is_strength(text) or (sets and reps):
        met = resolve_strength_met(text, met, sets=sets, reps=reps)

    weight = current_weight_kg(user, date)
    burned = exercise_calories(met, weight, duration) if weight else Decimal("0")

    return WorkoutLog.objects.create(
        user=user,
        date=date,
        exercise_type=ExerciseType.objects.filter(name__iexact=description).first(),
        description=description,
        duration_minutes=Decimal(str(duration)),
        met_value=met,
        calories_burned=burned,
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
    burned = step_calories(steps, weight) if weight else Decimal("0")

    entry, _ = StepLog.objects.update_or_create(
        user=user,
        date=date,
        defaults={
            "steps": steps,
            "calories_burned": burned,
            "source": source or EntrySource.MANUAL,
            "source_message": source_message,
        },
    )
    return entry
