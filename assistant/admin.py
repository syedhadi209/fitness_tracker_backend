from django.contrib import admin

from .models import ChatMessage, ChatSession, ToolInvocation


class ChatMessageInline(admin.TabularInline):
    model = ChatMessage
    extra = 0
    readonly_fields = ["role", "content", "tool_calls", "tool_call_id", "created_at"]


@admin.register(ChatSession)
class ChatSessionAdmin(admin.ModelAdmin):
    list_display = ["id", "user", "title", "updated_at"]
    inlines = [ChatMessageInline]


@admin.register(ToolInvocation)
class ToolInvocationAdmin(admin.ModelAdmin):
    list_display = ["name", "tool_call_id", "created_at"]
    list_filter = ["name"]
