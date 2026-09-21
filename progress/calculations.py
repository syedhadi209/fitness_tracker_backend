"""Calorie and energy-expenditure math.

Deliberately free of ORM access so each formula can be unit-tested directly.
All functions take and return Decimals.
"""

from decimal import Decimal

# Mifflin-St Jeor constants
_BMR_WEIGHT_COEFF = Decimal("10")
_BMR_HEIGHT_COEFF = Decimal("6.25")
_BMR_AGE_COEFF = Decimal("5")
_BMR_MALE_OFFSET = Decimal("5")
_BMR_FEMALE_OFFSET = Decimal("-161")

ACTIVITY_FACTORS = {
    "sedentary": Decimal("1.2"),
    "light": Decimal("1.375"),
    "moderate": Decimal("1.55"),
    "active": Decimal("1.725"),
    "athlete": Decimal("1.9"),
}

# Walking costs roughly 0.57 kcal per kg per km; an average stride of 0.762 m
# puts ~1312 steps in a kilometre.
_KCAL_PER_KG_PER_KM = Decimal("0.57")
_STEPS_PER_KM = Decimal("1312")

MINUTES_PER_HOUR = Decimal("60")


def _d(value):
    return value if isinstance(value, Decimal) else Decimal(str(value))


def bmr_mifflin_st_jeor(weight_kg, height_cm, age_years, sex):
    """Basal metabolic rate in kcal/day."""
    offset = _BMR_MALE_OFFSET if sex == "male" else _BMR_FEMALE_OFFSET
    return (
        _BMR_WEIGHT_COEFF * _d(weight_kg)
        + _BMR_HEIGHT_COEFF * _d(height_cm)
        - _BMR_AGE_COEFF * _d(age_years)
        + offset
    )


def tdee(bmr, activity_level):
    """Total daily energy expenditure: BMR scaled by a lifestyle activity factor."""
    factor = ACTIVITY_FACTORS.get(activity_level, ACTIVITY_FACTORS["sedentary"])
    return _d(bmr) * factor


def exercise_calories(met_value, weight_kg, duration_minutes):
    """Energy cost of a workout: MET x bodyweight x hours."""
    hours = _d(duration_minutes) / MINUTES_PER_HOUR
    return _d(met_value) * _d(weight_kg) * hours


def step_calories(steps, weight_kg):
    """Energy cost of walking a given number of steps at the user's bodyweight."""
    kilometres = _d(steps) / _STEPS_PER_KM
    return kilometres * _KCAL_PER_KG_PER_KM * _d(weight_kg)
