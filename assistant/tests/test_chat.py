"""Tests for the conversational logging loop.

Every test drives the loop with canned OpenRouter responses, so nothing here
touches the network.
"""

import json
from datetime import date
from decimal import Decimal

from django.test import TestCase

from activity.models import WorkoutLog
from api.testing import FakeOpenRouter, make_user, text_response, tool_call_response
from assistant.chat import run_turn
from assistant.executor import execute
from assistant.models import ChatSession, Role, ToolInvocation
from nutrition.models import MealLog
from nutrition.services import create_meal
from progress.services import set_weight

DAY = "2026-09-21"

MEAL_ARGS = json.dumps(
    {
        "meal_type": "breakfast",
        "date": DAY,
        "items": [
            {
                "description": "2 eggs",
                "quantity": 2,
                "unit": "egg",
                "calories": 156,
                "protein_g": 12,
                "carbs_g": 1,
                "fat_g": 11,
            },
            {
                "description": "Toast",
                "quantity": 1,
                "unit": "slice",
                "calories": 90,
                "protein_g": 3,
                "carbs_g": 17,
                "fat_g": 1,
            },
        ],
    }
)


class ChatLoggingTests(TestCase):
    def setUp(self):
        self.user = make_user("chat@example.com")
        self.session = ChatSession.objects.create(user=self.user, title="Test")

    def test_meal_logged_by_chat_matches_one_logged_directly(self):
        client = FakeOpenRouter(
            [
                tool_call_response("log_meal", MEAL_ARGS),
                text_response("Logged breakfast: 246 kcal, 15g protein."),
            ]
        )
        result = run_turn(self.session, self.user, "had 2 eggs and toast", client=client)

        chat_meal = MealLog.objects.get(user=self.user)
        reference = create_meal(
            user=make_user("reference@example.com"),
            items=[
                {"description": "2 eggs", "quantity": 2, "unit": "egg", "calories": 156,
                 "protein_g": 12, "carbs_g": 1, "fat_g": 11},
                {"description": "Toast", "quantity": 1, "unit": "slice", "calories": 90,
                 "protein_g": 3, "carbs_g": 17, "fat_g": 1},
            ],
            meal_type="breakfast",
            date=date(2026, 9, 21),
        )

        self.assertEqual(chat_meal.meal_type, reference.meal_type)
        self.assertEqual(chat_meal.date, reference.date)
        self.assertEqual(
            [(i.description, i.calories, i.protein_g) for i in chat_meal.items.all()],
            [(i.description, i.calories, i.protein_g) for i in reference.items.all()],
        )
        self.assertEqual(result["reply"], "Logged breakfast: 246 kcal, 15g protein.")

    def test_logged_entry_is_linked_back_to_the_message(self):
        client = FakeOpenRouter(
            [tool_call_response("log_meal", MEAL_ARGS), text_response("Done.")]
        )
        run_turn(self.session, self.user, "had 2 eggs and toast", client=client)

        meal = MealLog.objects.get(user=self.user)
        self.assertIsNotNone(meal.source_message)
        self.assertEqual(meal.source_message.role, Role.ASSISTANT)

    def test_response_reports_affected_entries_for_the_ui(self):
        client = FakeOpenRouter(
            [tool_call_response("log_meal", MEAL_ARGS), text_response("Done.")]
        )
        result = run_turn(self.session, self.user, "had 2 eggs and toast", client=client)

        self.assertEqual(len(result["entries"]), 1)
        self.assertEqual(result["entries"][0]["entry_type"], "meal")
        self.assertEqual(result["entries"][0]["total_calories"], 246.0)

    def test_exercise_burn_is_computed_from_bodyweight_not_the_model(self):
        set_weight(self.user, 80, date=date(2026, 9, 21))
        args = json.dumps(
            {
                "description": "Running",
                "duration_minutes": 30,
                "met_value": 10,
                "date": DAY,
            }
        )
        client = FakeOpenRouter(
            [tool_call_response("log_exercise", args), text_response("Nice run.")]
        )
        run_turn(self.session, self.user, "ran for 30 minutes", client=client)

        workout = WorkoutLog.objects.get(user=self.user)
        # 10 MET x 80 kg x 0.5 h = 400 kcal
        self.assertEqual(workout.calories_burned, Decimal("400.0"))

    def test_set_rep_lift_does_not_use_an_invented_half_hour(self):
        set_weight(self.user, 80, date=date(2026, 9, 21))
        args = json.dumps(
            {
                "description": "Dumbbell Bench Press",
                "duration_minutes": 30,
                "met_value": 5.2,
                "sets": 3,
                "reps": 12,
                "load_kg": 10,
                "date": DAY,
            }
        )
        client = FakeOpenRouter(
            [tool_call_response("log_exercise", args), text_response("Logged.")]
        )
        run_turn(
            self.session,
            self.user,
            "i have done dumbell bench press with 10kg dumbbells 3sets 12 reps",
            client=client,
        )

        workout = WorkoutLog.objects.get(user=self.user)
        self.assertEqual(workout.duration_minutes, Decimal("6.0"))
        self.assertLess(workout.calories_burned, Decimal("50"))


class IdempotencyTests(TestCase):
    def setUp(self):
        self.user = make_user("idem@example.com")
        self.session = ChatSession.objects.create(user=self.user)

    def test_replaying_a_tool_call_id_does_not_log_twice(self):
        arguments = json.loads(MEAL_ARGS)

        first = execute(self.session, self.user, "call_abc", "log_meal", arguments)
        second = execute(self.session, self.user, "call_abc", "log_meal", arguments)

        self.assertEqual(MealLog.objects.filter(user=self.user).count(), 1)
        self.assertEqual(first["id"], second["id"])
        self.assertEqual(ToolInvocation.objects.filter(tool_call_id="call_abc").count(), 1)

    def test_distinct_tool_call_ids_do_log_twice(self):
        arguments = json.loads(MEAL_ARGS)

        execute(self.session, self.user, "call_one", "log_meal", arguments)
        execute(self.session, self.user, "call_two", "log_meal", arguments)

        self.assertEqual(MealLog.objects.filter(user=self.user).count(), 2)


class ToolOwnershipTests(TestCase):
    def setUp(self):
        self.alice = make_user("alice2@example.com")
        self.bob = make_user("bob2@example.com")
        self.session = ChatSession.objects.create(user=self.alice)
        self.bobs_meal = create_meal(
            user=self.bob,
            items=[{"description": "Steak", "calories": 500}],
            meal_type="dinner",
            date=date(2026, 9, 20),
        )

    def test_update_entry_cannot_touch_another_users_row(self):
        result = execute(
            self.session,
            self.alice,
            "call_x",
            "update_entry",
            {
                "entry_type": "meal",
                "entry_id": self.bobs_meal.id,
                "changes": {"meal_type": "snack"},
            },
        )

        self.assertIn("error", result)
        self.bobs_meal.refresh_from_db()
        self.assertEqual(self.bobs_meal.meal_type, "dinner")

    def test_delete_entry_cannot_remove_another_users_row(self):
        result = execute(
            self.session,
            self.alice,
            "call_y",
            "delete_entry",
            {"entry_type": "meal", "entry_id": self.bobs_meal.id},
        )

        self.assertIn("error", result)
        self.assertTrue(MealLog.objects.filter(pk=self.bobs_meal.id).exists())

    def test_failed_tool_call_is_not_recorded_as_executed(self):
        execute(
            self.session,
            self.alice,
            "call_z",
            "delete_entry",
            {"entry_type": "meal", "entry_id": self.bobs_meal.id},
        )
        self.assertFalse(ToolInvocation.objects.filter(tool_call_id="call_z").exists())

    def test_unknown_tool_name_is_reported_not_raised(self):
        result = execute(self.session, self.alice, "call_w", "drop_database", {})
        self.assertIn("error", result)
