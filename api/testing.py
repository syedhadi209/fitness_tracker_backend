"""Shared test helpers."""

from datetime import date

from django.contrib.auth import get_user_model

from accounts.models import Profile

User = get_user_model()


def make_user(email="user@example.com", password="test-pass-9184", **profile_kwargs):
    user = User.objects.create_user(email=email, password=password)
    Profile.objects.create(
        user=user,
        height_cm=profile_kwargs.pop("height_cm", 175),
        sex=profile_kwargs.pop("sex", "male"),
        date_of_birth=profile_kwargs.pop("date_of_birth", date(1995, 1, 1)),
        **profile_kwargs,
    )
    return user


def authenticate(client, user):
    """Attach a JWT for `user` to an APIClient."""
    from rest_framework_simplejwt.tokens import RefreshToken

    token = RefreshToken.for_user(user).access_token
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    return client


class FakeOpenRouter:
    """Replays canned OpenRouter responses so tests never hit the network."""

    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def chat(self, messages, tools=None, tool_choice="auto", response_format=None):
        self.calls.append(messages)
        if not self.responses:
            raise AssertionError("FakeOpenRouter ran out of canned responses")
        return self.responses.pop(0)


def tool_call_response(name, arguments_json, call_id="call_1", model="test/model"):
    return {
        "model": model,
        "choices": [
            {
                "message": {
                    "content": None,
                    "tool_calls": [
                        {
                            "id": call_id,
                            "type": "function",
                            "function": {"name": name, "arguments": arguments_json},
                        }
                    ],
                }
            }
        ],
        "usage": {"prompt_tokens": 10, "completion_tokens": 5},
    }


def text_response(content, model="test/model"):
    return {
        "model": model,
        "choices": [{"message": {"content": content}}],
        "usage": {"prompt_tokens": 10, "completion_tokens": 5},
    }
