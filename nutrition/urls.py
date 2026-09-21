from django.urls import path
from rest_framework.routers import DefaultRouter

from assistant.views import ParseFoodView

from .views import FoodViewSet, MealLogViewSet

router = DefaultRouter()
router.register("foods", FoodViewSet, basename="food")
router.register("meals", MealLogViewSet, basename="meal")

urlpatterns = [
    path("parse/", ParseFoodView.as_view(), name="parse-food"),
    *router.urls,
]
