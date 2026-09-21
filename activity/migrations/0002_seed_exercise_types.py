from django.db import migrations

# Compendium of Physical Activities MET values, rounded to one decimal.
EXERCISES = [
    ("Walking (slow)", "cardio", "2.8"),
    ("Walking (brisk)", "cardio", "4.3"),
    ("Hiking", "cardio", "6.0"),
    ("Running (8 km/h)", "cardio", "8.3"),
    ("Running (10 km/h)", "cardio", "9.8"),
    ("Running (12 km/h)", "cardio", "11.8"),
    ("Cycling (leisure)", "cardio", "4.0"),
    ("Cycling (moderate)", "cardio", "8.0"),
    ("Cycling (vigorous)", "cardio", "10.0"),
    ("Swimming (leisure)", "cardio", "6.0"),
    ("Swimming (laps)", "cardio", "8.3"),
    ("Rowing machine", "cardio", "7.0"),
    ("Elliptical trainer", "cardio", "5.0"),
    ("Stair climbing", "cardio", "8.8"),
    ("Jump rope", "cardio", "12.3"),
    ("Weight training (light)", "strength", "3.5"),
    ("Weight training (vigorous)", "strength", "6.0"),
    ("Bodyweight circuit", "strength", "8.0"),
    ("CrossFit", "strength", "9.0"),
    ("Calisthenics", "strength", "8.0"),
    ("Yoga", "flexibility", "3.0"),
    ("Pilates", "flexibility", "3.8"),
    ("Stretching", "flexibility", "2.3"),
    ("Football", "sport", "7.0"),
    ("Basketball", "sport", "6.5"),
    ("Tennis", "sport", "7.3"),
    ("Badminton", "sport", "5.5"),
    ("Cricket", "sport", "4.8"),
    ("Boxing (bag work)", "sport", "7.8"),
    ("Martial arts", "sport", "10.3"),
    ("Dancing", "sport", "5.0"),
    ("Housework", "daily", "3.0"),
    ("Gardening", "daily", "3.8"),
]


def seed_exercise_types(apps, schema_editor):
    ExerciseType = apps.get_model("activity", "ExerciseType")
    ExerciseType.objects.bulk_create(
        [
            ExerciseType(name=name, category=category, met_value=met)
            for name, category, met in EXERCISES
        ],
        ignore_conflicts=True,
    )


def unseed_exercise_types(apps, schema_editor):
    ExerciseType = apps.get_model("activity", "ExerciseType")
    ExerciseType.objects.filter(name__in=[name for name, _, _ in EXERCISES]).delete()


class Migration(migrations.Migration):
    dependencies = [("activity", "0001_initial")]

    operations = [migrations.RunPython(seed_exercise_types, unseed_exercise_types)]
