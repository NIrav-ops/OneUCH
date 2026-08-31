from django.urls import path

# ===============================
# MESSAGE VIEWS
# ===============================
from inbox.views.inbox_list import InboxListAPIView
from inbox.views.inbox_detail import InboxMessageDetailAPIView
from inbox.views.mark_all_read import MarkAllReadAPIView
from inbox.views.message_status import (
    MessageStatusAPIView,
    BulkMessageStatusAPIView,
)
from inbox.views.search import MessageSearchAPIView
from inbox.views.star import ToggleStarAPIView
from inbox.views.delete import DeleteMessageAPIView

# ===============================
# ATTACHMENT VIEWS
# ===============================
from inbox.views.attachment_download import AttachmentDownloadAPIView
from inbox.views.attachment_preview import AttachmentPreviewAPIView
from inbox.admin_views import UpdateAttachmentPolicyAPIView
from .views_attachment import DownloadAttachmentAPIView

# ===============================
# CONVERSATION VIEWS
# ===============================
from inbox.views.conversations import ConversationListAPIView
from inbox.views.conversation_detail import ConversationDetailAPIView
from inbox.views.send_message import UnifiedSendMessageAPIView
from inbox.views.conversation_actions import (
    MarkConversationReadAPIView,
    DeleteConversationAPIView,
    ToggleConversationStarAPIView,
)
from inbox.views.conversation_bulk import (
    BulkMarkConversationReadAPIView,
    BulkToggleConversationStarAPIView,
)

# ===============================
# UNIFIED INBOX
# ===============================

from inbox.views.unified_inbox import (
    UnifiedInboxAPIView,
    UnifiedConversationInboxAPIView,
)

# ===============================
# DRAFTS
# ===============================
from inbox.views.draft import DraftSaveAPIView, DraftListAPIView
from inbox.views.send_draft import SendDraftAPIView
from inbox.views.reply import ReplyConversationAPIView

# ===============================
# DASHBOARD / BILLING / META
# ===============================
from inbox.views.dashboard import InboxDashboardAPIView
from inbox.views.notifications_list import NotificationListAPIView
from inbox.views.sync_status import InboxSyncStatusAPIView
from inbox.views.recipient_suggestions import RecipientSuggestionAPIView
from inbox.views.payment_create_order import CreatePaymentOrderAPIView


urlpatterns = [

    # ==========================================================
    # 🔹 MESSAGES (Single Message Operations)
    # ==========================================================
    path("messages/", InboxListAPIView.as_view(), name="inbox-messages"),
    path("messages/<int:message_id>/", InboxMessageDetailAPIView.as_view(), name="inbox-message-detail"),
    path("messages/<int:message_id>/status/", MessageStatusAPIView.as_view(), name="message-status"),
    path("messages/status/bulk/", BulkMessageStatusAPIView.as_view(), name="bulk-message-status"),
    path("messages/mark-all-read/", MarkAllReadAPIView.as_view()),
    path("message/<int:message_id>/toggle-star/", ToggleStarAPIView.as_view()),
    path("message/<int:message_id>/delete/", DeleteMessageAPIView.as_view()),
    


    # ==========================================================
    # 🔹 ATTACHMENTS
    # ==========================================================
        path("admin/attachment-policy/", UpdateAttachmentPolicyAPIView.as_view(), name="update-attachment-policy"),
        path("attachments/<int:message_id>/<str:attachment_id>/",DownloadAttachmentAPIView.as_view()),


    # ==========================================================
    # 🔹 CONVERSATION BULK ACTIONS (⚠ MUST COME BEFORE DYNAMIC)
    # ==========================================================
    path("conversation/bulk-mark-read/", BulkMarkConversationReadAPIView.as_view()),
    path("conversation/bulk-toggle-star/", BulkToggleConversationStarAPIView.as_view()),


    # ==========================================================
    # 🔹 CONVERSATION SINGLE ACTIONS
    # ==========================================================
    path("conversation/<str:conversation_id>/mark-read/", MarkConversationReadAPIView.as_view()),
    path("conversation/<str:conversation_id>/toggle-star/", ToggleConversationStarAPIView.as_view()),
    path("conversation/<str:conversation_id>/delete/", DeleteConversationAPIView.as_view()),

    # ==========================================================
    # 🔹 CONVERSATION LIST
    # ==========================================================
    path("conversations/", ConversationListAPIView.as_view()),
    path("conversations/<int:conversation_id>/", ConversationDetailAPIView.as_view()),
    path("conversations/<int:conversation_id>/reply/", ReplyConversationAPIView.as_view()),
    path("send/", UnifiedSendMessageAPIView.as_view()),

    # ==========================================================
    # 🔹 UNIFIED INBOX
    # ==========================================================
    path("unified/", UnifiedInboxAPIView.as_view(), name="unified-inbox"),
    path("unified-conversations/", UnifiedConversationInboxAPIView.as_view(), name="unified-conversations"),
    path("search/", MessageSearchAPIView.as_view()),
    path(
        "recipient-suggestions/",
        RecipientSuggestionAPIView.as_view(),
        name="recipient-suggestions",
    ),


    # ==========================================================
    # 🔹 DRAFTS
    # ==========================================================
    path("draft/save/", DraftSaveAPIView.as_view(), name="draft-save"),
    path("draft/list/", DraftListAPIView.as_view(), name="draft-list"),
    path("draft/send/<int:draft_id>/", SendDraftAPIView.as_view(), name="draft-send"),


    # ==========================================================
    # 🔹 DASHBOARD / BILLING / META
    # ==========================================================
    path("dashboard/", InboxDashboardAPIView.as_view()),
    path("notifications/", NotificationListAPIView.as_view()),
    path("sync-status/", InboxSyncStatusAPIView.as_view()),
    path("billing/create-order/", CreatePaymentOrderAPIView.as_view()),
]
