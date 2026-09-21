from rest_framework import serializers

from .models import WeightLog


class WeightLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = WeightLog
        fields = ["id", "date", "weight_kg", "body_fat_pct", "note", "source_message", "created_at"]
        read_only_fields = ["id", "source_message", "created_at"]


# The serializers below exist to document response shapes for the generated
# OpenAPI client; the views build their payloads through progress.aggregation.


class ConsumedTotalsSerializer(serializers.Serializer):
    calories = serializers.DecimalField(max_digits=10, decimal_places=2)
    protein_g = serializers.DecimalField(max_digits=10, decimal_places=2)
    carbs_g = serializers.DecimalField(max_digits=10, decimal_places=2)
    fat_g = serializers.DecimalField(max_digits=10, decimal_places=2)


class BurnedTotalsSerializer(serializers.Serializer):
    exercise = serializers.DecimalField(max_digits=10, decimal_places=2)
    steps = serializers.DecimalField(max_digits=10, decimal_places=2)
    step_count = serializers.IntegerField()
    total = serializers.DecimalField(max_digits=10, decimal_places=2)


class DailyTargetsSerializer(serializers.Serializer):
    calories = serializers.IntegerField(allow_null=True)
    protein_g = serializers.IntegerField(allow_null=True)
    carbs_g = serializers.IntegerField(allow_null=True)
    fat_g = serializers.IntegerField(allow_null=True)
    bmr = serializers.IntegerField(allow_null=True)


class DashboardSerializer(serializers.Serializer):
    date = serializers.DateField()
    consumed = ConsumedTotalsSerializer()
    burned = BurnedTotalsSerializer()
    net_calories = serializers.DecimalField(max_digits=10, decimal_places=2)
    targets = DailyTargetsSerializer()
    calories_remaining = serializers.DecimalField(
        max_digits=10, decimal_places=2, allow_null=True
    )
    weight_kg = serializers.DecimalField(max_digits=6, decimal_places=2)


class HistorySerializer(serializers.Serializer):
    start = serializers.DateField()
    end = serializers.DateField()
    metric = serializers.ChoiceField(choices=["calories", "steps", "weight"])
    results = serializers.ListField(child=serializers.DictField())
