from django.urls import path
from conversations.views import (
    ConversationListAPIView,
    ConversationDetailAPIView,
)

urlpatterns = [
    path("", ConversationListAPIView.as_view()),
]

from conversations.reply_views import ConversationReplyAPIView

urlpatterns += [
    path("<int:conversation_id>/reply/", ConversationReplyAPIView.as_view()),
]
from conversations.timeline_views import ConversationTimelineAPIView

urlpatterns +=[
    path("<int:conversation_id>/timeline/", ConversationTimelineAPIView.as_view()),
]