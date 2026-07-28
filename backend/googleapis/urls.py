
from django.urls import path
from .views import GmailConversationPreviewAPIView
from .views import GmailBulkActionAPIView, GmailConversationPreviewAPIView, GmailSyncAPIView, GmailMarkReadAPIView, GmailBulkConversationActionAPIView, google_oauth_start, google_oauth_callback

urlpatterns = [
    path("start/", google_oauth_start),
    path("callback/", google_oauth_callback),
    path("conversations/",GmailConversationPreviewAPIView.as_view()),
    path("gmail/conversations/bulk/",GmailBulkActionAPIView.as_view()),
    path("sync/", GmailSyncAPIView.as_view()),
    path("mark-read/", GmailMarkReadAPIView.as_view()),
    path("bulk-action/", GmailBulkConversationActionAPIView.as_view()),
]