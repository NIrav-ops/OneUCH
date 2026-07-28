from django.contrib import admin
from inbox.models import AuditLog
from inbox.models import (
    Conversation,
    InboxSyncStatus,
    InboxMessage,
    Attachment,
    AttachmentAccessLog,
    AttachmentPolicy,
    UserAttachmentPolicy,
)

admin.site.register(Conversation)
admin.site.register(InboxSyncStatus)

@admin.register(InboxMessage)
class InboxMessageAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "platform",
        "direction",
        "sender",
        "subject",
        "received_at",
        "is_read",
    )
    list_filter = ("platform", "direction", "is_read")
    search_fields = ("sender", "subject", "external_message_id")
    ordering = ("-received_at",)


@admin.register(Attachment)
class AttachmentAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "filename",
        "content_type",
        "size",
        "uploaded_at",
    )
    search_fields = ("filename",)
    ordering = ("-uploaded_at",)


@admin.register(AttachmentAccessLog)
class AttachmentAccessLogAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "attachment",
        "action",
        "accessed_at",
        "scan_status",
    )
    list_filter = ("action", "scan_status")
    ordering = ("-accessed_at",)


@admin.register(AttachmentPolicy)
class AttachmentPolicyAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "allow_download",
        "allow_preview",
        "max_size_mb",
    )
    list_filter = ("allow_download", "allow_preview")
    search_fields = ("name",)


@admin.register(UserAttachmentPolicy)
class UserAttachmentPolicyAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "policy",
    )
    search_fields = ("user__username", "policy__name")

@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "action",
        "user",
        "organization",
        "ip_address",
        "created_at",
    )

    list_filter = ("action", "organization")
    search_fields = ("user__email", "action")
    ordering = ("-created_at",)

    readonly_fields = (
        "user",
        "organization",
        "action",
        "ip_address",
        "metadata",
        "created_at",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
