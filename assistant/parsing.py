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
    "Extract the exercise. If the user gave sets and reps, put those in the JSON and "
    "estimate duration from the work plus rest (about 5 seconds per rep and 90 seconds "
    "between sets) — never default to 30 minutes for a few sets. Use MET 3.5 for "
    "typical lifting. Only use a stated duration when the user said how long."
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
    from activity.estimates import (
        is_strength,
        parse_sets_reps,
        resolve_duration,
        resolve_strength_met,
    )

    draft = _parse(text, EXERCISE_PROMPT, EXERCISE_SCHEMA, client)
    sets, reps = parse_sets_reps(text)
    draft["duration_minutes"] = float(
        resolve_duration(
            text,
            draft.get("duration_minutes"),
            sets=sets,
            reps=reps,
            source="ai",
        )
    )
    if is_strength(text) or (sets and reps):
        draft["met_value"] = float(
            resolve_strength_met(text, draft.get("met_value"), sets=sets, reps=reps)
        )
    if sets and reps:
        draft["sets"] = sets
        draft["reps"] = reps
    return draft
