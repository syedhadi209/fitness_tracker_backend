from django.contrib import admin

from .models import WeightLog


@admin.register(WeightLog)
class WeightLogAdmin(admin.ModelAdmin):
    list_display = ["user", "date", "weight_kg", "body_fat_pct"]
    list_filter = ["date"]
