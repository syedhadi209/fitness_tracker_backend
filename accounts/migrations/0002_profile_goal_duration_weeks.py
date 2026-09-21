from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="profile",
            name="goal_duration_weeks",
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
    ]
