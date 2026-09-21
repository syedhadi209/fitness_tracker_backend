from django.contrib import admin

from .models import ExerciseType, StepLog, WorkoutLog


@admin.register(ExerciseType)
class ExerciseTypeAdmin(admin.ModelAdmin):
    list_display = ["name", "category", "met_value"]
    list_filter = ["category"]
    search_fields = ["name"]


@admin.register(WorkoutLog)
class WorkoutLogAdmin(admin.ModelAdmin):
    list_display = ["user", "date", "description", "duration_minutes", "calories_burned"]
    list_filter = ["date", "source"]


@admin.register(StepLog)
class StepLogAdmin(admin.ModelAdmin):
    list_display = ["user", "date", "steps", "calories_burned"]
    list_filter = ["date"]
