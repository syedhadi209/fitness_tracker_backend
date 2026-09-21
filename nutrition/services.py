from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from .models import Food, FoodSource, MealItem, MealLog, MealType


def _dec(value, default="0"):
    if value is None:
        return Decimal(default)
    return Decimal(str(value))


@transaction.atomic
def create_meal(
    user,
    items,
    meal_type=MealType.SNACK,
    date=None,
    raw_text="",
    source=FoodSource.MANUAL,
    source_message=None,
):
    """Create a meal and its items.

    Single write path shared by the REST viewset and the assistant tool executor,
    so a meal logged by chat is indistinguishable from one logged by a form.

    Each item is a dict with `description` and optionally `quantity`, `unit`,
    `calories`, `protein_g`, `carbs_g`, `fat_g`, `food_id`.
    """
    # Callers may pass None for optional fields; fall back rather than writing null.
    source = source or FoodSource.MANUAL
    meal = MealLog.objects.create(
        user=user,
        date=date or timezone.localdate(),
        meal_type=meal_type or MealType.SNACK,
        raw_text=raw_text or "",
        source=source,
        source_message=source_message,
    )

    for item in items:
        food = None
        if item.get("food_id"):
            food = Food.objects.filter(pk=item["food_id"]).first()

        if food is None and source == FoodSource.AI:
            # Persist the estimate so the same food can be reused without another
            # LLM round trip, and so a food database can later supersede it.
            food = Food.objects.create(
                name=item["description"][:200],
                serving_description=item.get("unit", ""),
                calories=_dec(item.get("calories")),
                protein_g=_dec(item.get("protein_g")),
                carbs_g=_dec(item.get("carbs_g")),
                fat_g=_dec(item.get("fat_g")),
                source=FoodSource.AI,
                created_by=user,
            )

        MealItem.objects.create(
            meal=meal,
            food=food,
            description=item["description"],
            quantity=_dec(item.get("quantity"), "1"),
            unit=item.get("unit", ""),
            calories=_dec(item.get("calories")),
            protein_g=_dec(item.get("protein_g")),
            carbs_g=_dec(item.get("carbs_g")),
            fat_g=_dec(item.get("fat_g")),
        )

    return meal
