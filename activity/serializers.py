from rest_framework import serializers

from .models import ExerciseType, StepLog, WorkoutLog
from .services import log_workout, set_steps


class ExerciseTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExerciseType
        fields = ["id", "name", "category", "met_value"]


class WorkoutLogSerializer(serializers.ModelSerializer):
    # Optional: falls back to the ExerciseType catalogue, then a moderate default.
    met_value = serializers.DecimalField(
        max_digits=5, decimal_places=2, required=False, allow_null=True
    )

    class Meta:
        model = WorkoutLog
        fields = [
            "id",
            "date",
            "exercise_type",
            "description",
            "duration_minutes",
            "met_value",
            "calories_burned",
            "raw_text",
            "source",
            "source_message",
            "created_at",
        ]
        # calories_burned is derived from bodyweight and MET, never client-supplied.
        read_only_fields = [
            "id",
            "exercise_type",
            "calories_burned",
            "source_message",
            "created_at",
        ]

    def create(self, validated_data):
        return log_workout(
            user=validated_data["user"],
            description=validated_data["description"],
            duration_minutes=validated_data["duration_minutes"],
            met_value=validated_data.get("met_value"),
            date=validated_data.get("date"),
            raw_text=validated_data.get("raw_text", ""),
            source=validated_data.get("source"),
        )


class StepLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = StepLog
        fields = ["id", "date", "steps", "calories_burned", "source", "source_message", "updated_at"]
        read_only_fields = ["id", "calories_burned", "source_message", "updated_at"]

    def create(self, validated_data):
        return set_steps(
            user=validated_data["user"],
            steps=validated_data["steps"],
            date=validated_data.get("date"),
            source=validated_data.get("source"),
        )
