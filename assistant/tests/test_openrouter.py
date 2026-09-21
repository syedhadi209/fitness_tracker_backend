import json
from unittest.mock import patch

import httpx
from django.test import TestCase, override_settings

from assistant.openrouter import OpenRouterClient, OpenRouterError
from assistant.parsing import parse_food


class OpenRouterClientTests(TestCase):
    @override_settings(OPENROUTER_API_KEY="")
    def test_missing_api_key_raises_a_clear_error(self):
        with self.assertRaises(OpenRouterError) as ctx:
            OpenRouterClient().chat([{"role": "user", "content": "hi"}])
        self.assertIn("OPENROUTER_API_KEY", str(ctx.exception))

    @override_settings(OPENROUTER_API_KEY="test-key")
    @patch("assistant.openrouter.httpx.post")
    def test_sends_bearer_token_and_model(self, mock_post):
        mock_post.return_value = httpx.Response(
            200, json={"choices": [{"message": {"content": "hi"}}]}
        )
        OpenRouterClient(model="test/model").chat([{"role": "user", "content": "hi"}])

        _, kwargs = mock_post.call_args
        self.assertEqual(kwargs["headers"]["Authorization"], "Bearer test-key")
        self.assertEqual(kwargs["json"]["model"], "test/model")

    @override_settings(OPENROUTER_API_KEY="test-key")
    @patch("assistant.openrouter.httpx.post")
    def test_http_error_becomes_openrouter_error(self, mock_post):
        mock_post.return_value = httpx.Response(429, text="rate limited")
        with self.assertRaises(OpenRouterError):
            OpenRouterClient().chat([{"role": "user", "content": "hi"}])

    @override_settings(OPENROUTER_API_KEY="test-key")
    @patch("assistant.openrouter.httpx.post", side_effect=httpx.ConnectError("boom"))
    def test_network_failure_becomes_openrouter_error(self, _mock_post):
        with self.assertRaises(OpenRouterError):
            OpenRouterClient().chat([{"role": "user", "content": "hi"}])


class ParsingTests(TestCase):
    def test_parse_food_returns_the_models_structured_draft(self):
        draft = {
            "meal_type": "lunch",
            "items": [
                {
                    "description": "Chicken sandwich",
                    "quantity": 1,
                    "unit": "sandwich",
                    "calories": 450,
                    "protein_g": 30,
                    "carbs_g": 45,
                    "fat_g": 15,
                }
            ],
        }

        class Client:
            def chat(self, messages, tools=None, tool_choice="auto", response_format=None):
                assert response_format is not None, "parsing must request structured output"
                return {"choices": [{"message": {"content": json.dumps(draft)}}]}

        self.assertEqual(parse_food("chicken sandwich", client=Client()), draft)
