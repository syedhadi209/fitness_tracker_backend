"""Tool definitions advertised to the model, in OpenAI/OpenRouter function-calling format."""

_DATE_PROPERTY = {
    "type": "string",
    "description": "Date in YYYY-MM-DD. Defaults to today when omitted.",
}

LOG_MEAL = {
    "type": "function",
    "function": {
        "name": "log_meal",
        "description": "Log food the user ate, with estimated calories and macros per item.",
        "parameters": {
            "type": "object",
            "properties": {
                "meal_type": {
                    "type": "string",
                    "enum": ["breakfast", "lunch", "dinner", "snack"],
                },
                "date": _DATE_PROPERTY,
                "items": {
                    "type": "array",
                    "description": "One entry per distinct food.",
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
                        "required": ["description", "calories", "protein_g", "carbs_g", "fat_g"],
                    },
                },
            },
            "required": ["meal_type", "items"],
        },
    },
}

LOG_EXERCISE = {
    "type": "function",
    "function": {
        "name": "log_exercise",
        "description": (
            "Log a workout. Supply the MET value for the activity; the app computes "
            "calories burned from the user's bodyweight."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "description": {"type": "string"},
                "duration_minutes": {"type": "number"},
                "met_value": {
                    "type": "number",
                    "description": "Metabolic equivalent, e.g. 7.0 for running at moderate pace.",
                },
                "date": _DATE_PROPERTY,
            },
            "required": ["description", "duration_minutes", "met_value"],
        },
    },
}

LOG_STEPS = {
    "type": "function",
    "function": {
        "name": "log_steps",
        "description": "Set the user's step count for a day. Replaces any existing count.",
        "parameters": {
            "type": "object",
            "properties": {"steps": {"type": "integer"}, "date": _DATE_PROPERTY},
            "required": ["steps"],
        },
    },
}

LOG_WEIGHT = {
    "type": "function",
    "function": {
        "name": "log_weight",
        "description": "Record the user's bodyweight in kilograms.",
        "parameters": {
            "type": "object",
            "properties": {
                "weight_kg": {"type": "number"},
                "body_fat_pct": {"type": "number"},
                "date": _DATE_PROPERTY,
            },
            "required": ["weight_kg"],
        },
    },
}

GET_PROGRESS = {
    "type": "function",
    "function": {
        "name": "get_progress",
        "description": "Read the user's calorie, macro, step and weight history for a date range.",
        "parameters": {
            "type": "object",
            "properties": {
                "start_date": _DATE_PROPERTY,
                "end_date": _DATE_PROPERTY,
                "metric": {"type": "string", "enum": ["calories", "steps", "weight"]},
            },
        },
    },
}

UPDATE_ENTRY = {
    "type": "function",
    "function": {
        "name": "update_entry",
        "description": (
            "Amend an entry the user just logged, for example changing a quantity. "
            "Use an id from the recent entries in the system prompt."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "entry_type": {"type": "string", "enum": ["meal", "workout", "steps", "weight"]},
                "entry_id": {"type": "integer"},
                "changes": {
                    "type": "object",
                    "description": (
                        "Fields to change. For a meal, pass a full replacement `items` array."
                    ),
                },
            },
            "required": ["entry_type", "entry_id", "changes"],
        },
    },
}

DELETE_ENTRY = {
    "type": "function",
    "function": {
        "name": "delete_entry",
        "description": "Remove an entry the user says they logged by mistake.",
        "parameters": {
            "type": "object",
            "properties": {
                "entry_type": {"type": "string", "enum": ["meal", "workout", "steps", "weight"]},
                "entry_id": {"type": "integer"},
            },
            "required": ["entry_type", "entry_id"],
        },
    },
}

ALL_TOOLS = [
    LOG_MEAL,
    LOG_EXERCISE,
    LOG_STEPS,
    LOG_WEIGHT,
    GET_PROGRESS,
    UPDATE_ENTRY,
    DELETE_ENTRY,
]
