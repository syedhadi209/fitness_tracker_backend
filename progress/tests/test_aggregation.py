from datetime import date
from decimal import Decimal

from django.test import TestCase

from activity.services import log_workout, set_steps
from api.testing import make_user
from nutrition.services import create_meal
from progress import aggregation
from progress.services import set_weight

DAY = date(2026, 9, 21)


class DashboardTests(TestCase):
    def setUp(self):
        self.user = make_user("dash@example.com")
        set_weight(self.user, 80, date=DAY)

        create_meal(
            user=self.user,
            items=[
                {"description": "Eggs", "calories": 200, "protein_g": 14, "carbs_g": 2, "fat_g": 14},
                {"description": "Toast", "calories": 150, "protein_g": 5, "carbs_g": 28, "fat_g": 2},
            ],
            meal_type="breakfast",
            date=DAY,
        )
        create_meal(
            user=self.user,
            items=[
                {"description": "Chicken rice", "calories": 600, "protein_g": 45, "carbs_g": 70, "fat_g": 12}
            ],
            meal_type="lunch",
            date=DAY,
        )
        log_workout(self.user, "Running (10 km/h)", duration_minutes=30, met_value=10, date=DAY)
        set_steps(self.user, 8000, date=DAY)

    def test_consumed_totals_sum_every_item_across_meals(self):
        consumed = aggregation.consumed_totals(self.user, DAY)
        self.assertEqual(consumed["calories"], Decimal("950"))
        self.assertEqual(consumed["protein_g"], Decimal("64"))
        self.assertEqual(consumed["carbs_g"], Decimal("100"))
        self.assertEqual(consumed["fat_g"], Decimal("28"))

    def test_burned_totals_combine_exercise_and_steps(self):
        burned = aggregation.burned_totals(self.user, DAY)
        # 10 MET x 80 kg x 0.5 h = 400 kcal
        self.assertEqual(burned["exercise"], Decimal("400.0"))
        self.assertEqual(burned["step_count"], 8000)
        self.assertGreater(burned["steps"], Decimal("0"))
        self.assertEqual(burned["total"], burned["exercise"] + burned["steps"])

    def test_net_calories_is_consumed_minus_burned(self):
        result = aggregation.dashboard(self.user, DAY)
        self.assertEqual(
            result["net_calories"], result["consumed"]["calories"] - result["burned"]["total"]
        )

    def test_dashboard_reports_the_days_weight(self):
        result = aggregation.dashboard(self.user, DAY)
        self.assertEqual(result["weight_kg"], Decimal("80.00"))

    def test_other_users_data_is_not_counted(self):
        stranger = make_user("stranger@example.com")
        create_meal(
            user=stranger,
            items=[{"description": "Cake", "calories": 900}],
            meal_type="snack",
            date=DAY,
        )
        self.assertEqual(aggregation.consumed_totals(self.user, DAY)["calories"], Decimal("950"))

    def test_empty_day_returns_zeros_rather_than_none(self):
        consumed = aggregation.consumed_totals(self.user, date(2026, 1, 1))
        self.assertEqual(consumed["calories"], Decimal("0"))


class HistoryTests(TestCase):
    def setUp(self):
        self.user = make_user("history@example.com")
        set_weight(self.user, 82, date=date(2026, 9, 19))
        set_weight(self.user, 81, date=date(2026, 9, 21))
        create_meal(
            user=self.user,
            items=[{"description": "Pasta", "calories": 700}],
            meal_type="dinner",
            date=date(2026, 9, 20),
        )

    def test_calorie_series_covers_every_day_in_range(self):
        series = aggregation.history(self.user, date(2026, 9, 19), date(2026, 9, 21))
        self.assertEqual([row["date"] for row in series], [
            date(2026, 9, 19),
            date(2026, 9, 20),
            date(2026, 9, 21),
        ])

    def test_days_without_entries_report_zero(self):
        series = aggregation.history(self.user, date(2026, 9, 19), date(2026, 9, 21))
        self.assertEqual(series[0]["consumed"], Decimal("0"))
        self.assertEqual(series[1]["consumed"], Decimal("700"))

    def test_weight_metric_returns_only_logged_days(self):
        series = aggregation.history(
            self.user, date(2026, 9, 19), date(2026, 9, 21), metric="weight"
        )
        self.assertEqual(len(series), 2)
        self.assertEqual(series[0]["weight_kg"], Decimal("82.00"))


class StepUpsertTests(TestCase):
    def setUp(self):
        self.user = make_user("steps@example.com")

    def test_logging_steps_twice_replaces_rather_than_duplicates(self):
        set_steps(self.user, 3000, date=DAY)
        set_steps(self.user, 7500, date=DAY)

        self.assertEqual(self.user.step_logs.count(), 1)
        self.assertEqual(self.user.step_logs.first().steps, 7500)

    def test_steps_without_weight_record_zero_burn(self):
        entry = set_steps(self.user, 10000, date=DAY)
        self.assertEqual(entry.calories_burned, Decimal("0"))

    def test_burn_scales_with_the_users_weight(self):
        set_weight(self.user, 60, date=DAY)
        light = set_steps(self.user, 10000, date=DAY).calories_burned

        set_weight(self.user, 100, date=DAY)
        heavy = set_steps(self.user, 10000, date=DAY).calories_burned

        self.assertGreater(heavy, light)


class TdeeRequiresWeightTests(TestCase):
    def test_profile_without_a_weigh_in_has_no_maintenance_calories(self):
        user = make_user("noweight@example.com")
        targets = aggregation.daily_targets(user, DAY)
        self.assertIsNone(targets["bmr"])
        self.assertIsNone(targets["calories"])
        self.assertIsNone(aggregation.dashboard(user, DAY)["weight_kg"])

    def test_logged_weight_produces_tdee(self):
        user = make_user("weighed@example.com")
        set_weight(user, 80, date=DAY)
        targets = aggregation.daily_targets(user, DAY)
        self.assertIsNotNone(targets["bmr"])
        self.assertIsNotNone(targets["calories"])
        self.assertGreater(targets["calories"], targets["bmr"])

    def test_explicit_calorie_target_still_applies_without_weight(self):
        user = make_user("manual@example.com", daily_calorie_target=2200)
        targets = aggregation.daily_targets(user, DAY)
        self.assertEqual(targets["calories"], 2200)
        self.assertIsNone(targets["bmr"])

    def test_workout_without_weight_records_zero_burn(self):
        user = make_user("noworkoutweight@example.com")
        workout = log_workout(user, "Running", duration_minutes=30, met_value=10, date=DAY)
        self.assertEqual(workout.calories_burned, Decimal("0"))


class GoalPaceTargetTests(TestCase):
    def test_lose_goal_with_timeline_lowers_calories_below_tdee(self):
        cut = make_user(
            "cut@example.com",
            goal="lose",
            target_weight_kg=72,
            goal_duration_weeks=16,
            activity_level="moderate",
        )
        hold = make_user("hold@example.com", activity_level="moderate")
        set_weight(cut, 80, date=DAY)
        set_weight(hold, 80, date=DAY)
        self.assertLess(
            aggregation.daily_targets(cut, DAY)["calories"],
            aggregation.daily_targets(hold, DAY)["calories"],
        )

    def test_maintain_ignores_target_and_timeline(self):
        user = make_user(
            "keep@example.com",
            goal="maintain",
            target_weight_kg=72,
            goal_duration_weeks=8,
            activity_level="moderate",
        )
        hold = make_user("keep2@example.com", activity_level="moderate")
        set_weight(user, 80, date=DAY)
        set_weight(hold, 80, date=DAY)
        self.assertEqual(
            aggregation.daily_targets(user, DAY)["calories"],
            aggregation.daily_targets(hold, DAY)["calories"],
        )
