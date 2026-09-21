from django.db.models import Q
from rest_framework import filters, viewsets

from api.mixins import UserScopedModelViewSet

from .models import Food, MealLog
from .serializers import FoodSerializer, MealLogSerializer


class FoodViewSet(viewsets.ModelViewSet):
    """Foods are a shared lookup table, not per-user data.

    Reads span the global catalogue plus the user's own entries; writes are always
    attributed to the requesting user.
    """

    serializer_class = FoodSerializer
    queryset = Food.objects.all()
    filter_backends = [filters.SearchFilter]
    search_fields = ["name", "brand"]

    def get_queryset(self):
        return self.queryset.filter(
            Q(created_by__isnull=True) | Q(created_by=self.request.user)
        )

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class MealLogViewSet(UserScopedModelViewSet):
    serializer_class = MealLogSerializer
    queryset = MealLog.objects.prefetch_related("items")

    def get_queryset(self):
        qs = super().get_queryset()
        date = self.request.query_params.get("date")
        if date:
            qs = qs.filter(date=date)
        return qs
