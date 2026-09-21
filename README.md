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

# Local development only (auto-reload). Do not use this in production.
python manage.py runserver

# Production-style process (Gunicorn). This is what Docker and Railway run.
gunicorn config.wsgi:application --config gunicorn.conf.py
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

## Docker

```bash
docker build -t fitness-tracker-api .
docker run --env-file .env -p 8000:8000 fitness-tracker-api
```

The container runs migrations, collects static files, then serves with **Gunicorn**
(`gunicorn.conf.py`) on `$PORT` (default 8000). Django's `runserver` is never used
in the image. A `Procfile` is included so a Nixpacks/PaaS deploy also starts Gunicorn
instead of the development server.

## Railway

This repo is the service root. Railway will pick up `Dockerfile` and `railway.json`.

1. New project → Deploy from GitHub → `syedhadi209/fitness_tracker_backend`.
2. Add a **PostgreSQL** plugin so Railway injects `DATABASE_URL`.
3. Generate a public domain (Settings → Networking). `RAILWAY_PUBLIC_DOMAIN` is then added to `ALLOWED_HOSTS` automatically.
4. Set variables:

| Variable | Value |
|----------|--------|
| `SECRET_KEY` | long random string |
| `DEBUG` | `False` |
| `CORS_ALLOWED_ORIGINS` | your frontend origin, e.g. `https://your-app.vercel.app` |
| `OPENROUTER_API_KEY` | OpenRouter key |
| `OPENROUTER_MODEL` | `openai/gpt-4o-mini` (or any OpenRouter model) |

`PORT` and `DATABASE_URL` are provided by Railway. Leave `SECURE_SSL_REDIRECT` unset (Railway terminates TLS and health-checks over HTTP).

Health check: `GET /api/health/`.
