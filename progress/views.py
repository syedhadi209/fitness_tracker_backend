from datetime import datetime, timedelta

from django.utils import timezone
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.response import Response
from rest_framework.views import APIView

from api.mixins import UserScopedModelViewSet

from . import aggregation
from .models import WeightLog
from .serializers import DashboardSerializer, HistorySerializer, WeightLogSerializer


def _parse_date(value, default):
    if not value:
        return default
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return default


class WeightLogViewSet(UserScopedModelViewSet):
    serializer_class = WeightLogSerializer
    queryset = WeightLog.objects.all()


@extend_schema(
    responses=DashboardSerializer,
    parameters=[
        OpenApiParameter("date", OpenApiTypes.DATE, description="Defaults to today.")
    ],
)
class DashboardView(APIView):
    def get(self, request):
        date = _parse_date(request.query_params.get("date"), timezone.localdate())
        return Response(aggregation.dashboard(request.user, date))


@extend_schema(
    responses=HistorySerializer,
    parameters=[
        OpenApiParameter("start", OpenApiTypes.DATE, description="Defaults to 30 days ago."),
        OpenApiParameter("end", OpenApiTypes.DATE, description="Defaults to today."),
        OpenApiParameter("metric", OpenApiTypes.STR, enum=["calories", "steps", "weight"]),
    ],
)
class HistoryView(APIView):
    def get(self, request):
        end = _parse_date(request.query_params.get("end"), timezone.localdate())
        start = _parse_date(request.query_params.get("start"), end - timedelta(days=29))
        metric = request.query_params.get("metric", "calories")

        return Response(
            {
                "start": start,
                "end": end,
                "metric": metric,
                "results": aggregation.history(request.user, start, end, metric),
            }
        )
