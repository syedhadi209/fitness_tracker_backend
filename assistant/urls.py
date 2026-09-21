from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import ChatMessagesView, ChatSessionViewSet, ChatView

router = DefaultRouter()
router.register("sessions", ChatSessionViewSet, basename="chat-session")

urlpatterns = [
    path("chat/", ChatView.as_view(), name="chat"),
    path("sessions/<int:session_id>/messages/", ChatMessagesView.as_view(), name="chat-messages"),
    *router.urls,
]
