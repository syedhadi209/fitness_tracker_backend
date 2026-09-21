from decimal import Decimal

from django.test import TestCase

from progress.calculations import (
    bmr_mifflin_st_jeor,
    exercise_calories,
    step_calories,
    tdee,
)


class BmrTests(TestCase):
    def test_male_matches_mifflin_st_jeor(self):
        # 10(80) + 6.25(180) - 5(30) + 5 = 1780
        result = bmr_mifflin_st_jeor(80, 180, 30, "male")
        self.assertEqual(result, Decimal("1780"))

    def test_female_uses_lower_offset(self):
        # 10(65) + 6.25(165) - 5(30) - 161 = 1370.25
        result = bmr_mifflin_st_jeor(65, 165, 30, "female")
        self.assertEqual(result, Decimal("1370.25"))

    def test_female_is_lower_than_male_at_same_measurements(self):
        male = bmr_mifflin_st_jeor(70, 170, 30, "male")
        female = bmr_mifflin_st_jeor(70, 170, 30, "female")
        self.assertLess(female, male)


class TdeeTests(TestCase):
    def test_sedentary_factor(self):
        self.assertEqual(tdee(Decimal("1780"), "sedentary"), Decimal("2136.0"))

    def test_rises_with_activity_level(self):
        base = Decimal("1800")
        levels = ["sedentary", "light", "moderate", "active", "athlete"]
        values = [tdee(base, level) for level in levels]
        self.assertEqual(values, sorted(values))

    def test_unknown_level_falls_back_to_sedentary(self):
        self.assertEqual(tdee(Decimal("1800"), "nonsense"), tdee(Decimal("1800"), "sedentary"))


class ExerciseCalorieTests(TestCase):
    def test_met_times_weight_times_hours(self):
        # 8 MET x 70 kg x 0.5 h = 280 kcal
        self.assertEqual(exercise_calories(8, 70, 30), Decimal("280.0"))

    def test_scales_linearly_with_duration(self):
        half = exercise_calories(6, 70, 30)
        full = exercise_calories(6, 70, 60)
        self.assertEqual(full, half * 2)


class StepCalorieTests(TestCase):
    def test_ten_thousand_steps_is_in_a_sane_range(self):
        result = step_calories(10000, 70)
        self.assertGreater(result, Decimal("250"))
        self.assertLess(result, Decimal("400"))

    def test_zero_steps_burns_nothing(self):
        self.assertEqual(step_calories(0, 70), Decimal("0"))

    def test_heavier_user_burns_more(self):
        self.assertGreater(step_calories(8000, 95), step_calories(8000, 60))
