from django.urls import path
from rest_framework.routers import DefaultRouter

from assistant.views import ParseExerciseView

from .views import ExerciseTypeViewSet, StepLogViewSet, WorkoutLogViewSet

router = DefaultRouter()
router.register("exercise-types", ExerciseTypeViewSet, basename="exercise-type")
router.register("workouts", WorkoutLogViewSet, basename="workout")
router.register("steps", StepLogViewSet, basename="step")

urlpatterns = [
    path("parse/", ParseExerciseView.as_view(), name="parse-exercise"),
    *router.urls,
]
