from django.urls import path
from ai.views import AISmartReplyAPIView
from ai.summary_views import AIConversationSummaryAPIView

urlpatterns = [
    path("reply/<int:conversation_id>/", AISmartReplyAPIView.as_view()),
    path("summary/<int:conversation_id>/", AIConversationSummaryAPIView.as_view()),
]
