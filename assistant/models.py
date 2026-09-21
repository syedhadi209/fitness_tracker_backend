from django.conf import settings
from django.db import models


class ChatSession(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="chat_sessions"
    )
    title = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self):
        return self.title or f"Session {self.pk}"


class Role(models.TextChoices):
    USER = "user", "User"
    ASSISTANT = "assistant", "Assistant"
    TOOL = "tool", "Tool"
    SYSTEM = "system", "System"


class ChatMessage(models.Model):
    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name="messages")
    role = models.CharField(max_length=20, choices=Role.choices)
    content = models.TextField(blank=True)

    # Raw OpenRouter payloads, kept so a bad estimate can be traced back later.
    tool_calls = models.JSONField(null=True, blank=True)
    tool_call_id = models.CharField(max_length=128, blank=True)

    model = models.CharField(max_length=120, blank=True)
    prompt_tokens = models.PositiveIntegerField(null=True, blank=True)
    completion_tokens = models.PositiveIntegerField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "id"]
        indexes = [models.Index(fields=["session", "created_at"])]

    def __str__(self):
        return f"{self.role}: {self.content[:50]}"


class ToolInvocation(models.Model):
    """Executed tool calls, keyed by OpenRouter's tool_call_id.

    The unique constraint is what makes execution idempotent: a retried request or
    a double-tapped send button cannot log the same meal twice.
    """

    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name="tool_calls")
    tool_call_id = models.CharField(max_length=128, unique=True)
    name = models.CharField(max_length=80)
    arguments = models.JSONField(default=dict)
    result = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.tool_call_id})"
