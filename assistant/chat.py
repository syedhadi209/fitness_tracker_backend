"""The conversational logging loop.

A turn runs: build context, call the model, run any tool calls it asks for, feed
the results back, and repeat until the model replies with plain text.
"""

import json

from .context import build_system_prompt
from .executor import WRITE_TOOLS, execute
from .models import ChatMessage, Role
from .openrouter import OpenRouterClient
from .tools import ALL_TOOLS

MAX_TOOL_ROUNDS = 4


def _history_payload(session):
    """Replay stored messages in the shape OpenRouter expects."""
    payload = []
    for message in session.messages.all():
        if message.role == Role.TOOL:
            payload.append(
                {
                    "role": "tool",
                    "tool_call_id": message.tool_call_id,
                    "content": message.content,
                }
            )
        elif message.role == Role.ASSISTANT and message.tool_calls:
            payload.append(
                {
                    "role": "assistant",
                    "content": message.content or None,
                    "tool_calls": message.tool_calls,
                }
            )
        else:
            payload.append({"role": message.role, "content": message.content})
    return payload


def run_turn(session, user, user_message, client=None):
    """Process one user message, returning the reply and anything it changed."""
    client = client or OpenRouterClient()

    ChatMessage.objects.create(session=session, role=Role.USER, content=user_message)

    messages = [{"role": "system", "content": build_system_prompt(user)}]
    messages.extend(_history_payload(session))

    affected_entries = []

    for _ in range(MAX_TOOL_ROUNDS):
        response = client.chat(messages, tools=ALL_TOOLS)
        choice = response["choices"][0]["message"]
        tool_calls = choice.get("tool_calls") or []
        usage = response.get("usage") or {}

        assistant_message = ChatMessage.objects.create(
            session=session,
            role=Role.ASSISTANT,
            content=choice.get("content") or "",
            tool_calls=tool_calls or None,
            model=response.get("model", ""),
            prompt_tokens=usage.get("prompt_tokens"),
            completion_tokens=usage.get("completion_tokens"),
        )

        if not tool_calls:
            session.save(update_fields=["updated_at"])
            return {
                "reply": assistant_message.content,
                "message_id": assistant_message.id,
                "entries": affected_entries,
            }

        messages.append(
            {
                "role": "assistant",
                "content": choice.get("content") or None,
                "tool_calls": tool_calls,
            }
        )

        for call in tool_calls:
            function = call.get("function", {})
            name = function.get("name", "")
            try:
                arguments = json.loads(function.get("arguments") or "{}")
            except json.JSONDecodeError:
                arguments = {}

            result = execute(
                session=session,
                user=user,
                tool_call_id=call.get("id", ""),
                name=name,
                arguments=arguments,
                message=assistant_message,
            )

            if name in WRITE_TOOLS and isinstance(result, dict) and "error" not in result:
                affected_entries.append(result)

            serialized = json.dumps(result, default=str)
            ChatMessage.objects.create(
                session=session,
                role=Role.TOOL,
                content=serialized,
                tool_call_id=call.get("id", ""),
            )
            messages.append(
                {"role": "tool", "tool_call_id": call.get("id", ""), "content": serialized}
            )

    # Ran out of rounds; return whatever the model last said rather than looping.
    session.save(update_fields=["updated_at"])
    return {
        "reply": "I logged what I could, but got stuck working through that one. Mind rephrasing?",
        "message_id": None,
        "entries": affected_entries,
    }
