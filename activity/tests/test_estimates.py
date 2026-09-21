from datetime import date
from decimal import Decimal

from django.test import TestCase

from activity.estimates import minutes_for_sets_reps, resolve_duration, resolve_strength_met
from activity.services import log_workout
from api.testing import make_user
from progress.services import set_weight

DAY = date(2026, 9, 21)


class SetRepDurationTests(TestCase):
    def test_three_by_twelve_is_about_six_minutes_not_thirty(self):
        # 36 reps × 5s + 2 rest intervals × 90s = 360s
        self.assertEqual(minutes_for_sets_reps(3, 12), Decimal("6.0"))

    def test_sets_and_reps_override_an_invented_thirty_minutes(self):
        duration = resolve_duration(
            "dumbbell bench press 3 sets 12 reps",
            duration_minutes=30,
            sets=3,
            reps=12,
            source="ai",
        )
        self.assertEqual(duration, Decimal("6.0"))

    def test_parses_sets_from_messy_user_text(self):
        duration = resolve_duration(
            "i have done dumbell bench press with 10kg dumbbells 3sets 12 reps",
            duration_minutes=30,
            source="ai",
        )
        self.assertEqual(duration, Decimal("6.0"))
        duration = resolve_duration("ran for 30 minutes", duration_minutes=30, source="ai")
        self.assertEqual(duration, Decimal("30"))


class StrengthBurnTests(TestCase):
    def setUp(self):
        self.user = make_user("lift@example.com")
        set_weight(self.user, 80, date=DAY)

    def test_three_by_twelve_bench_is_not_two_hundred_calories(self):
        workout = log_workout(
            self.user,
            "Dumbbell bench press",
            duration_minutes=30,
            met_value=5.2,
            date=DAY,
            source="ai",
            sets=3,
            reps=12,
        )
        # 3.5 MET × 80 kg × 0.1 h = 28 kcal
        self.assertEqual(workout.duration_minutes, Decimal("6.0"))
        self.assertEqual(workout.met_value, Decimal("3.5"))
        self.assertEqual(workout.calories_burned, Decimal("28.0"))
        self.assertLess(workout.calories_burned, Decimal("50"))

    def test_running_thirty_minutes_still_uses_the_stated_time(self):
        workout = log_workout(
            self.user,
            "Running (10 km/h)",
            duration_minutes=30,
            met_value=10,
            date=DAY,
            source="ai",
        )
        self.assertEqual(workout.calories_burned, Decimal("400.0"))

    def test_typical_lift_uses_light_strength_met(self):
        self.assertEqual(resolve_strength_met("bench press", 8, sets=3, reps=12), Decimal("3.5"))
