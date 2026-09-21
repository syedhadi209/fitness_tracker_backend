# Fitness Tracker API

Django REST Framework backend: email/password auth, food and exercise logging with
LLM-assisted parsing via OpenRouter, step and weight tracking, and dashboard
aggregation.

## Setup

Requires a running PostgreSQL server.

```bash
createdb fitness_tracker

python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

cp .env.example .env   # then edit DATABASE_URL and OPENROUTER_API_KEY

python manage.py migrate
python manage.py runserver
```

Interactive API docs: [http://127.0.0.1:8000/api/docs/](http://127.0.0.1:8000/api/docs/)

## Apps

- `accounts` — custom email-login `User`, `Profile`, JWT auth
- `nutrition` — `Food`, `MealLog`, `MealItem`
- `activity` — `ExerciseType` (seeded MET values), `WorkoutLog`, `StepLog`
- `progress` — `WeightLog`, calorie math, dashboard and history aggregation
- `assistant` — OpenRouter client and the conversational logging tool loop

Each app exposes a `services.py`. Both the REST viewsets and the assistant's tool
executor write through those functions, so a meal logged by chat is identical to
one logged by a form.

## Endpoints

Auth (`/api/auth/`): `register/`, `login/`, `refresh/`, `me/`

Logging: `/api/nutrition/meals/`, `/api/nutrition/foods/`, `/api/activity/workouts/`,
`/api/activity/steps/`, `/api/activity/exercise-types/`, `/api/progress/weights/`

Aggregation: `/api/progress/dashboard/?date=`, `/api/progress/history/?start=&end=&metric=`

Assistant: `/api/assistant/chat/`, `/api/assistant/sessions/`,
`/api/nutrition/parse/`, `/api/activity/parse/`

## Conversational logging

`POST /api/assistant/chat/` accepts a message and an optional `session_id`. The model
is given tools (`log_meal`, `log_exercise`, `log_steps`, `log_weight`, `get_progress`,
`update_entry`, `delete_entry`) which the backend executes, then returns a reply plus
the ids of any entries created or changed.

Two invariants hold in `assistant/executor.py` regardless of what the model asks for:
rows are only ever looked up scoped to the requesting user, and execution is keyed by
OpenRouter's `tool_call_id` so a retry cannot log the same meal twice.

## Calorie math

`progress/calculations.py` holds the formulas, free of ORM access so they can be
unit-tested directly:

- BMR via Mifflin-St Jeor, TDEE as BMR times an activity factor
- Exercise burn as `MET x bodyweight x hours`
- Step burn from step count and bodyweight

Burn is always computed server-side from the user's most recent logged weight rather
than accepted from the client.

## Tests

```bash
python manage.py test
```
