from decimal import Decimal

from django.utils import timezone

from .models import WeightLog


def current_weight_kg(user, on_date=None):
    """Most recent logged weight on or before `on_date`.

    Returns None when the user has never weighed in — callers must not invent a
    bodyweight, because BMR and TDEE are linear in kilograms.
    """
    on_date = on_date or timezone.localdate()
    entry = (
        WeightLog.objects.filter(user=user, date__lte=on_date).order_by("-date").first()
        or WeightLog.objects.filter(user=user).order_by("date").first()
    )
    return entry.weight_kg if entry else None


def set_weight(user, weight_kg, date=None, body_fat_pct=None, note="", source_message=None):
    """Record a bodyweight, replacing any existing entry for the same day."""
    date = date or timezone.localdate()
    entry, _ = WeightLog.objects.update_or_create(
        user=user,
        date=date,
        defaults={
            "weight_kg": Decimal(str(weight_kg)),
            "body_fat_pct": body_fat_pct,
            "note": note or "",
            "source_message": source_message,
        },
    )
    return entry
