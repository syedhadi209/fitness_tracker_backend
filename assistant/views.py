from drf_spectacular.utils import extend_schema
from rest_framework import status, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView

from .chat import run_turn
from .models import ChatSession, Role
from .openrouter import OpenRouterError
from .parsing import parse_exercise, parse_food
from .serializers import (
    ChatMessageSerializer,
    ChatRequestSerializer,
    ChatResponseSerializer,
    ChatSessionSerializer,
    ParsedExerciseSerializer,
    ParsedMealSerializer,
    ParseRequestSerializer,
)


class ChatSessionViewSet(viewsets.ModelViewSet):
    serializer_class = ChatSessionSerializer
    queryset = ChatSession.objects.all()

    def get_queryset(self):
        return self.queryset.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


@extend_schema(responses=ChatMessageSerializer(many=True))
class ChatMessagesView(APIView):
    def get(self, request, session_id):
        session = ChatSession.objects.filter(pk=session_id, user=request.user).first()
        if session is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        messages = session.messages.exclude(role=Role.SYSTEM)
        return Response(ChatMessageSerializer(messages, many=True).data)


@extend_schema(request=ChatRequestSerializer, responses=ChatResponseSerializer)
class ChatView(APIView):
    """Conversational logging: one user message in, a reply plus affected entries out."""

    def post(self, request):
        serializer = ChatRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        session_id = data.get("session_id")
        if session_id:
            session = ChatSession.objects.filter(pk=session_id, user=request.user).first()
            if session is None:
                return Response(
                    {"detail": "Chat session not found."}, status=status.HTTP_404_NOT_FOUND
                )
        else:
            session = ChatSession.objects.create(
                user=request.user, title=data["message"][:60]
            )

        try:
            result = run_turn(session, request.user, data["message"])
        except OpenRouterError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)

        return Response({"session_id": session.id, **result})


class _ParseView(APIView):
    parser_function = None

    def post(self, request):
        serializer = ParseRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            draft = type(self).parser_function(serializer.validated_data["text"])
        except OpenRouterError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)
        except ValueError as exc:
            return Response(
                {"detail": f"Could not read the model's response: {exc}"},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        return Response(draft)


@extend_schema(request=ParseRequestSerializer, responses=ParsedMealSerializer)
class ParseFoodView(_ParseView):
    parser_function = staticmethod(parse_food)


@extend_schema(request=ParseRequestSerializer, responses=ParsedExerciseSerializer)
class ParseExerciseView(_ParseView):
    parser_function = staticmethod(parse_exercise)
