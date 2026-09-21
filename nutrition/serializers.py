from rest_framework import serializers

from .models import Food, MealItem, MealLog
from .services import create_meal


class FoodSerializer(serializers.ModelSerializer):
    class Meta:
        model = Food
        fields = [
            "id",
            "name",
            "brand",
            "serving_description",
            "serving_grams",
            "calories",
            "protein_g",
            "carbs_g",
            "fat_g",
            "fiber_g",
            "source",
        ]
        read_only_fields = ["id", "source"]


class MealItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = MealItem
        fields = [
            "id",
            "food",
            "description",
            "quantity",
            "unit",
            "calories",
            "protein_g",
            "carbs_g",
            "fat_g",
        ]
        read_only_fields = ["id"]


class MealLogSerializer(serializers.ModelSerializer):
    items = MealItemSerializer(many=True)

    class Meta:
        model = MealLog
        fields = [
            "id",
            "date",
            "meal_type",
            "raw_text",
            "source",
            "source_message",
            "items",
            "created_at",
        ]
        read_only_fields = ["id", "source_message", "created_at"]

    def create(self, validated_data):
        items = validated_data.pop("items")
        return create_meal(
            user=validated_data["user"],
            items=[dict(item) for item in items],
            meal_type=validated_data.get("meal_type"),
            date=validated_data.get("date"),
            raw_text=validated_data.get("raw_text", ""),
            source=validated_data.get("source"),
        )

    def update(self, instance, validated_data):
        items = validated_data.pop("items", None)
        for field, value in validated_data.items():
            setattr(instance, field, value)
        instance.save()

        if items is not None:
            instance.items.all().delete()
            for item in items:
                MealItem.objects.create(meal=instance, **item)

        return instance
