from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models


class UserManager(BaseUserManager):
    """Manager for a user model that authenticates by email instead of username."""

    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError("Users must have an email address")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True")
        return self._create_user(email, password, **extra_fields)


class User(AbstractUser):
    username = None
    email = models.EmailField(unique=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = UserManager()

    def __str__(self):
        return self.email


class Sex(models.TextChoices):
    MALE = "male", "Male"
    FEMALE = "female", "Female"


class ActivityLevel(models.TextChoices):
    SEDENTARY = "sedentary", "Sedentary"
    LIGHT = "light", "Lightly active"
    MODERATE = "moderate", "Moderately active"
    ACTIVE = "active", "Very active"
    ATHLETE = "athlete", "Athlete"


class Goal(models.TextChoices):
    LOSE = "lose", "Lose weight"
    MAINTAIN = "maintain", "Maintain weight"
    GAIN = "gain", "Gain weight"


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")

    date_of_birth = models.DateField(null=True, blank=True)
    sex = models.CharField(max_length=10, choices=Sex.choices, blank=True)
    height_cm = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True)
    activity_level = models.CharField(
        max_length=20, choices=ActivityLevel.choices, default=ActivityLevel.SEDENTARY
    )
    goal = models.CharField(max_length=10, choices=Goal.choices, default=Goal.MAINTAIN)
    target_weight_kg = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True)

    # Null means "derive from TDEE" rather than "no target".
    daily_calorie_target = models.PositiveIntegerField(null=True, blank=True)
    daily_protein_target_g = models.PositiveIntegerField(null=True, blank=True)
    daily_carbs_target_g = models.PositiveIntegerField(null=True, blank=True)
    daily_fat_target_g = models.PositiveIntegerField(null=True, blank=True)

    timezone = models.CharField(max_length=64, default="UTC")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Profile<{self.user.email}>"

    @property
    def age(self):
        if not self.date_of_birth:
            return None
        from django.utils import timezone as dj_timezone

        today = dj_timezone.localdate()
        return (
            today.year
            - self.date_of_birth.year
            - ((today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day))
        )
