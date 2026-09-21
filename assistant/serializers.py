from rest_framework import serializers

from .models import ChatMessage, ChatSession


class ChatMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatMessage
        fields = ["id", "role", "content", "tool_calls", "tool_call_id", "created_at"]


class ChatSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatSession
        fields = ["id", "title", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]


class ChatRequestSerializer(serializers.Serializer):
    message = serializers.CharField()
    session_id = serializers.IntegerField(required=False)


class ChatResponseSerializer(serializers.Serializer):
    session_id = serializers.IntegerField()
    reply = serializers.CharField()
    message_id = serializers.IntegerField(allow_null=True)
    entries = serializers.ListField(
        child=serializers.DictField(),
        help_text="Entries created or modified by this turn, for rendering editable cards.",
    )


class ParseRequestSerializer(serializers.Serializer):
    text = serializers.CharField()
    date = serializers.DateField(required=False)


class ParsedMealItemSerializer(serializers.Serializer):
    description = serializers.CharField()
    quantity = serializers.FloatField()
    unit = serializers.CharField()
    calories = serializers.FloatField()
    protein_g = serializers.FloatField()
    carbs_g = serializers.FloatField()
    fat_g = serializers.FloatField()


class ParsedMealSerializer(serializers.Serializer):
    meal_type = serializers.ChoiceField(choices=["breakfast", "lunch", "dinner", "snack"])
    items = ParsedMealItemSerializer(many=True)


class ParsedExerciseSerializer(serializers.Serializer):
    description = serializers.CharField()
    duration_minutes = serializers.FloatField()
    met_value = serializers.FloatField()
