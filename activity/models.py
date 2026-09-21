from django.conf import settings
from django.db import models


class EntrySource(models.TextChoices):
    MANUAL = "manual", "Manual entry"
    AI = "ai", "AI estimate"


class ExerciseType(models.Model):
    """Catalogue of exercises with their MET (metabolic equivalent) values."""

    name = models.CharField(max_length=120, unique=True)
    category = models.CharField(max_length=60, blank=True)
    met_value = models.DecimalField(max_digits=5, decimal_places=2)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class WorkoutLog(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="workout_logs"
    )
    date = models.DateField()

    exercise_type = models.ForeignKey(
        ExerciseType, on_delete=models.SET_NULL, null=True, blank=True, related_name="workouts"
    )
    description = models.CharField(max_length=300)
    duration_minutes = models.DecimalField(max_digits=6, decimal_places=1)
    met_value = models.DecimalField(max_digits=5, decimal_places=2)
    calories_burned = models.DecimalField(max_digits=8, decimal_places=2, default=0)

    raw_text = models.TextField(blank=True)
    source = models.CharField(max_length=20, choices=EntrySource.choices, default=EntrySource.MANUAL)
    source_message = models.ForeignKey(
        "assistant.ChatMessage",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="workout_logs",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date", "-created_at"]
        indexes = [models.Index(fields=["user", "date"])]

    def __str__(self):
        return f"{self.description} ({self.date})"


class StepLog(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="step_logs"
    )
    date = models.DateField()
    steps = models.PositiveIntegerField(default=0)
    calories_burned = models.DecimalField(max_digits=8, decimal_places=2, default=0)

    source = models.CharField(max_length=20, choices=EntrySource.choices, default=EntrySource.MANUAL)
    source_message = models.ForeignKey(
        "assistant.ChatMessage",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="step_logs",
    )

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-date"]
        constraints = [
            models.UniqueConstraint(fields=["user", "date"], name="unique_steps_per_user_day")
        ]

    def __str__(self):
        return f"{self.steps} steps on {self.date}"
