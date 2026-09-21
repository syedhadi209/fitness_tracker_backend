from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import DashboardView, HistoryView, WeightLogViewSet

router = DefaultRouter()
router.register("weights", WeightLogViewSet, basename="weight")

urlpatterns = [
    path("dashboard/", DashboardView.as_view(), name="dashboard"),
    path("history/", HistoryView.as_view(), name="history"),
    *router.urls,
]
