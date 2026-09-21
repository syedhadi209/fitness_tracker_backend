"""Minimal OpenRouter chat-completions client."""

import httpx
from django.conf import settings


class OpenRouterError(RuntimeError):
    pass


def _error_from_response(response):
    """Turn an OpenRouter HTTP error into something safe to show in the app.

    The raw body can include key URLs and credit internals; we keep those out
    of the message returned to the client.
    """
    if response.status_code == 402:
        return (
            "OpenRouter doesn't have enough credits for this request. "
            "Add credits at https://openrouter.ai/settings/credits, or lower OPENROUTER_MAX_TOKENS."
        )
    try:
        body = response.json()
        message = (body.get("error") or {}).get("message")
        if message:
            return f"OpenRouter returned {response.status_code}: {message}"
    except ValueError:
        pass
    return f"OpenRouter returned {response.status_code}: {response.text[:300]}"


class OpenRouterClient:
    def __init__(self, api_key=None, model=None, base_url=None, timeout=None, max_tokens=None):
        self.api_key = api_key or settings.OPENROUTER_API_KEY
        self.model = model or settings.OPENROUTER_MODEL
        self.base_url = (base_url or settings.OPENROUTER_BASE_URL).rstrip("/")
        self.timeout = timeout or settings.OPENROUTER_TIMEOUT
        self.max_tokens = max_tokens if max_tokens is not None else settings.OPENROUTER_MAX_TOKENS

    def _headers(self):
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost:3000",
            "X-Title": "Relish",
        }

    def chat(self, messages, tools=None, tool_choice="auto", response_format=None):
        if not self.api_key:
            raise OpenRouterError(
                "OPENROUTER_API_KEY is not set; add it to backend/.env to use the assistant."
            )

        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": self.max_tokens,
        }
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = tool_choice
        if response_format:
            payload["response_format"] = response_format

        try:
            response = httpx.post(
                f"{self.base_url}/chat/completions",
                json=payload,
                headers=self._headers(),
                timeout=self.timeout,
            )
        except httpx.HTTPError as exc:
            raise OpenRouterError(f"OpenRouter request failed: {exc}") from exc

        if response.status_code >= 400:
            raise OpenRouterError(_error_from_response(response))

        return response.json()
