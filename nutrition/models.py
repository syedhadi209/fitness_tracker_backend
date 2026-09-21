from django.conf import settings
from django.db import models


class FoodSource(models.TextChoices):
    MANUAL = "manual", "Manual entry"
    AI = "ai", "AI estimate"
    DATABASE = "database", "Food database"


class MealType(models.TextChoices):
    BREAKFAST = "breakfast", "Breakfast"
    LUNCH = "lunch", "Lunch"
    DINNER = "dinner", "Dinner"
    SNACK = "snack", "Snack"


class Food(models.Model):
    """A reusable food definition, cached so repeat entries need not re-hit the LLM."""

    name = models.CharField(max_length=200)
    brand = models.CharField(max_length=200, blank=True)
    serving_description = models.CharField(max_length=200, blank=True)
    serving_grams = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)

    calories = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    protein_g = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    carbs_g = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    fat_g = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    fiber_g = models.DecimalField(max_digits=8, decimal_places=2, default=0)

    source = models.CharField(max_length=20, choices=FoodSource.choices, default=FoodSource.MANUAL)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_foods",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["name"])]

    def __str__(self):
        return f"{self.brand} {self.name}".strip()


class MealLog(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="meal_logs"
    )
    date = models.DateField()
    meal_type = models.CharField(max_length=20, choices=MealType.choices, default=MealType.SNACK)

    raw_text = models.TextField(blank=True)
    source = models.CharField(max_length=20, choices=FoodSource.choices, default=FoodSource.MANUAL)
    source_message = models.ForeignKey(
        "assistant.ChatMessage",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="meal_logs",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-date", "-created_at"]
        indexes = [models.Index(fields=["user", "date"])]

    def __str__(self):
        return f"{self.user_id} {self.date} {self.meal_type}"

    @property
    def total_calories(self):
        return sum(item.calories for item in self.items.all())


class MealItem(models.Model):
    """A single food within a meal.

    Macros are snapshotted rather than read through `food`, so editing a Food row
    later cannot silently rewrite historical logs.
    """

    meal = models.ForeignKey(MealLog, on_delete=models.CASCADE, related_name="items")
    food = models.ForeignKey(
        Food, on_delete=models.SET_NULL, null=True, blank=True, related_name="meal_items"
    )

    description = models.CharField(max_length=300)
    quantity = models.DecimalField(max_digits=8, decimal_places=2, default=1)
    unit = models.CharField(max_length=50, blank=True)

    calories = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    protein_g = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    carbs_g = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    fat_g = models.DecimalField(max_digits=8, decimal_places=2, default=0)

    def __str__(self):
        return self.description
