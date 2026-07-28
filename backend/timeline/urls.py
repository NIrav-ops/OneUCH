from django.urls import path
from .views import ConversationTimelineAPIView

urlpatterns = [
    path(
        "conversation/<int:conversation_id>/",
        ConversationTimelineAPIView.as_view(),
    ),
]