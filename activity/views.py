from rest_framework import filters, viewsets

from api.mixins import UserScopedModelViewSet

from .models import ExerciseType, StepLog, WorkoutLog
from .serializers import ExerciseTypeSerializer, StepLogSerializer, WorkoutLogSerializer


class ExerciseTypeViewSet(viewsets.ReadOnlyModelViewSet):
    """Shared MET catalogue, read-only to clients."""

    serializer_class = ExerciseTypeSerializer
    queryset = ExerciseType.objects.all()
    filter_backends = [filters.SearchFilter]
    search_fields = ["name", "category"]


class WorkoutLogViewSet(UserScopedModelViewSet):
    serializer_class = WorkoutLogSerializer
    queryset = WorkoutLog.objects.all()

    def get_queryset(self):
        qs = super().get_queryset()
        date = self.request.query_params.get("date")
        if date:
            qs = qs.filter(date=date)
        return qs


class StepLogViewSet(UserScopedModelViewSet):
    serializer_class = StepLogSerializer
    queryset = StepLog.objects.all()

    def get_queryset(self):
        qs = super().get_queryset()
        date = self.request.query_params.get("date")
        if date:
            qs = qs.filter(date=date)
        return qs
