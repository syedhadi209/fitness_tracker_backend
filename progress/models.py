from django.conf import settings
from django.db import models


class WeightLog(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="weight_logs"
    )
    date = models.DateField()
    weight_kg = models.DecimalField(max_digits=5, decimal_places=2)
    body_fat_pct = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True)
    note = models.CharField(max_length=300, blank=True)

    source_message = models.ForeignKey(
        "assistant.ChatMessage",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="weight_logs",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-date"]
        constraints = [
            models.UniqueConstraint(fields=["user", "date"], name="unique_weight_per_user_day")
        ]

    def __str__(self):
        return f"{self.weight_kg}kg on {self.date}"
