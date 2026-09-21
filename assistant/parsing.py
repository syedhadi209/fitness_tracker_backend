"""Non-chat parsing: turn a single line of text into a draft the user confirms.

Backs the quick-add box on the dashboard. Unlike the chat loop, nothing here
writes to the database; the client posts the result to the normal REST endpoint.
"""

import json

from .openrouter import OpenRouterClient

FOOD_SCHEMA = {
    "type": "json_schema",
    "json_schema": {
        "name": "parsed_meal",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "meal_type": {
                    "type": "string",
                    "enum": ["breakfast", "lunch", "dinner", "snack"],
                },
                "items": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "description": {"type": "string"},
                            "quantity": {"type": "number"},
                            "unit": {"type": "string"},
                            "calories": {"type": "number"},
                            "protein_g": {"type": "number"},
                            "carbs_g": {"type": "number"},
                            "fat_g": {"type": "number"},
                        },
                        "required": [
                            "description",
                            "quantity",
                            "unit",
                            "calories",
                            "protein_g",
                            "carbs_g",
                            "fat_g",
                        ],
                        "additionalProperties": False,
                    },
                },
            },
            "required": ["meal_type", "items"],
            "additionalProperties": False,
        },
    },
}

EXERCISE_SCHEMA = {
    "type": "json_schema",
    "json_schema": {
        "name": "parsed_exercise",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "description": {"type": "string"},
                "duration_minutes": {"type": "number"},
                "met_value": {"type": "number"},
            },
            "required": ["description", "duration_minutes", "met_value"],
            "additionalProperties": False,
        },
    },
}

FOOD_PROMPT = (
    "Break the user's description of a meal into individual foods and estimate the "
    "calories and macros for each, using realistic portion sizes. Respond with JSON only."
)

EXERCISE_PROMPT = (
    "Extract the exercise, its duration in minutes, and its MET value from the user's "
    "description. Estimate duration if it is implied rather than stated. Respond with JSON only."
)


def _parse(text, prompt, schema, client=None):
    client = client or OpenRouterClient()
    response = client.chat(
        messages=[{"role": "system", "content": prompt}, {"role": "user", "content": text}],
        response_format=schema,
    )
    content = response["choices"][0]["message"]["content"]
    return json.loads(content)


def parse_food(text, client=None):
    return _parse(text, FOOD_PROMPT, FOOD_SCHEMA, client)


def parse_exercise(text, client=None):
    return _parse(text, EXERCISE_PROMPT, EXERCISE_SCHEMA, client)
