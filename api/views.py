from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView


@extend_schema(
    responses=inline_serializer(
        name="HealthCheck",
        fields={
            "status": serializers.CharField(),
            "service": serializers.CharField(),
        },
    )
)
class HealthCheckView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        return Response({"status": "ok", "service": "fitness-tracker-api"})
