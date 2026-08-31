from django.db import models
from django.conf import settings
from email_accounts.models import EmailAccount

User = settings.AUTH_USER_MODEL

class Conversation(models.Model):

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="conversations",
    )

    organization = models.ForeignKey(
        "inbox.Organization",
        on_delete=models.CASCADE,
        related_name="conversations",
        null=True,
        blank=True
    )

    email_account = models.ForeignKey(
        "email_accounts.EmailAccount",
        on_delete=models.CASCADE,
        related_name="conversations",
        null=True,
        blank=True,
        db_index=True
    )

    subject = models.CharField(max_length=500, blank=True)

    conversation_key = models.CharField(
    max_length=500,
    unique=True,
    db_index=True,
    )

    last_message = models.ForeignKey(
    "InboxMessage",
    null=True,
    blank=True,
    on_delete=models.SET_NULL,
    related_name="+"
    )   

    last_message_at = models.DateTimeField(null=True,blank=True,db_index=True)
    last_message_preview = models.TextField(blank=True,null=True, default="")

    unread_count = models.IntegerField(default=0)

    external_conversation_id = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        db_index=True
    )

    search_index = models.TextField(blank=True, null=True, db_index=True)

    is_starred = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Conversation {self.id} - {self.subject}"

class InboxMessage(models.Model):
    PLATFORMS = (
        ("gmail", "Gmail"),
        ("outlook", "Outlook"),
        ("imap", "IMAP"),
        ("teams", "Microsoft Teams"),
    )

    DIRECTION = (
        ("inbound", "Inbound"),
        ("outbound", "Outbound"),
    )

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="inbox_messages",
    )
    
    organization = models.ForeignKey(
    "inbox.Organization",
    on_delete=models.CASCADE,
    related_name="messages",
    )
    
    email_account = models.ForeignKey(
    "email_accounts.EmailAccount",
    on_delete=models.SET_NULL,
    null=True,
    blank=True,
    related_name="messages",
    )

    folder = models.CharField(
    max_length=50,
    default="inbox",
    db_index=True,
    )

    platform = models.CharField(
        max_length=20,
        choices=PLATFORMS,
        db_index=True,
    )

    direction = models.CharField(
        max_length=20,
        choices=DIRECTION,
    )

    conversation = models.ForeignKey(
    Conversation,
    on_delete=models.CASCADE,
    related_name="messages",
    null=True,
    blank=True,
    )

    external_message_id = models.CharField(
        max_length=255,
        db_index=True,
        help_text="Message ID from external platform",
    )
    
    external_conversation_id = models.CharField(
        max_length=255,
        db_index=True,
        null=True,
        blank=True,
        help_text="Thread/Conversation ID from external platform"
    )

    in_reply_to = models.CharField(
        max_length=255,
        null=True,
        blank=True,
    )

    attachment_meta = models.JSONField(default=list, blank=True)

    sender = models.EmailField()

    # Existing flat recipient storage remains for backwards
    # compatibility with inbox/search/send code.
    recipients = models.TextField(
        help_text="To / CC recipients"
    )

    # Provider-normalized identity metadata used by recipient
    # intelligence, Reply All and future autocomplete.
    #
    # sender_meta:
    # {
    #     "name": "...",
    #     "email": "..."
    # }
    #
    # recipient_meta:
    # {
    #     "to": [...],
    #     "cc": [...],
    #     "bcc": [...],
    #     "reply_to": [...]
    # }
    sender_meta = models.JSONField(
        default=dict,
        blank=True,
    )

    recipient_meta = models.JSONField(
        default=dict,
        blank=True,
    )

    subject = models.CharField(max_length=500, blank=True)
    body = models.TextField(blank=True)

    received_at = models.DateTimeField()
    is_read = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    is_draft = models.BooleanField(default=False)

    is_starred = models.BooleanField(default=False)

    is_priority = models.BooleanField(default=False)
    priority_score = models.IntegerField(default=0)
    
    action_analyzed = models.BooleanField(default=False)
    approval_analyzed = models.BooleanField(default=False)
    followup_analyzed = models.BooleanField(default=False)
    expected_response_analyzed = models.BooleanField(default=False)

    STATUS_CHOICES = [
    ("queued", "Queued"),
    ("sent", "Sent"),
    ("failed", "Failed"),
    ]
    status = models.CharField(
    max_length=20,
    choices=STATUS_CHOICES,
    default="queued",
    )
    retry_count = models.IntegerField(default=0)
    last_attempt_at = models.DateTimeField(null=True, blank=True)
    error_reason = models.TextField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["user", "platform"]),
            models.Index(fields=["external_message_id"]),
            models.Index(fields=["received_at"]),
            models.Index(fields=["user", "is_draft"]),
            models.Index(fields=["email_account"]),
            models.Index(fields=["subject"]),
            models.Index(fields=["sender"])
        ]
        

    def __str__(self):
        return f"{self.platform} | {self.sender} | {self.subject[:30]}"


class Attachment(models.Model):
    message = models.ForeignKey(
        InboxMessage,
        on_delete=models.CASCADE,
        related_name="attachments",
    )

    file = models.FileField(upload_to="attachments/")
    filename = models.CharField(max_length=255)
    content_type = models.CharField(max_length=100)
    size = models.IntegerField()
    policy_violated = models.BooleanField(default=False)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.filename


class AttachmentAccessLog(models.Model):
    ACTION_CHOICES = (
        ("download", "Download"),
        ("preview", "Preview"),
    )

    attachment = models.ForeignKey(
        Attachment,
        on_delete=models.CASCADE,
        related_name="access_logs",
    )

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
    )

    action = models.CharField(
        max_length=20,
        choices=ACTION_CHOICES,
    )

    accessed_at = models.DateTimeField(auto_now_add=True)

    scan_status = models.CharField(
        max_length=20,
        default="pending",  # pending | clean | infected | failed
    )

    scanned_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.user} {self.action} {self.attachment.filename}"


class AttachmentPolicy(models.Model):
    name = models.CharField(max_length=100, default="Default Policy")
    allow_download = models.BooleanField(default=True)
    allow_preview = models.BooleanField(default=True)
    max_size_mb = models.IntegerField(default=25)

    def __str__(self):
        return self.name


class UserAttachmentPolicy(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="attachment_policy",
    )

    policy = models.ForeignKey(
        AttachmentPolicy,
        on_delete=models.PROTECT,
        related_name="users",
    )

    def __str__(self):
        return f"{self.user} → {self.policy}"

class Organization(models.Model):
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)

    attachment_policy = models.ForeignKey(
        "inbox.AttachmentPolicy",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="organizations",
    )

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class OrganizationUser(models.Model):
    ROLE_CHOICES = (
        ("owner", "Owner"),
        ("admin", "Admin"),
        ("member", "Member"),
        ("viewer", "Viewer"),
    )

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="organization_membership",
        
    )

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="users",
    )

    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default="member",
    )

    joined_at = models.DateTimeField(auto_now_add=True)

    def is_owner(self):
        return self.role == "owner"

    def is_admin(self):
        return self.role in ["owner", "admin"]

    def __str__(self):
        return f"{self.user} ({self.role}) → {self.organization}"

class AuditLog(models.Model):
    ACTION_CHOICES = (
        ("ATTACHMENT_DOWNLOAD", "Attachment Download"),
        ("ATTACHMENT_POLICY_UPDATE", "Attachment Policy Update"),
        ("LOGIN", "User Login"),
        ("LOGOUT", "User Logout"),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs",
    )

    organization = models.ForeignKey(
        "inbox.Organization",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs",
    )

    action = models.CharField(
        max_length=50,
        choices=ACTION_CHOICES,
        db_index=True,
    )

    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
    )

    metadata = models.JSONField(
        default=dict,
        blank=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.action} | {self.user} | {self.created_at}"

class UsageEvent(models.Model):
    """
    Raw usage events (append-only)
    """
    EVENT_TYPES = (
        ("ATTACHMENT_DOWNLOAD", "Attachment Download"),
        ("ATTACHMENT_PREVIEW", "Attachment Preview"),
        ("MESSAGE_VIEW", "Message View"),
    )

    organization = models.ForeignKey(
        "inbox.Organization",
        on_delete=models.CASCADE,
        related_name="usage_events",
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )

    event_type = models.CharField(
        max_length=50,
        choices=EVENT_TYPES,
    )

    metadata = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["organization", "event_type"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return f"{self.organization} | {self.event_type}"

class UsageSummary(models.Model):
    """
    Aggregated usage per organization per billing period
    """
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="usage_summaries",
    )

    period_start = models.DateField()
    period_end = models.DateField()

    attachment_downloads = models.PositiveIntegerField(default=0)
    attachment_previews = models.PositiveIntegerField(default=0)
    message_views = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("organization", "period_start", "period_end")

    def __str__(self):
        return f"{self.organization} | {self.period_start} → {self.period_end}"

class BillingPlan(models.Model):
    """
    Defines a SaaS plan
    """
    PLAN_TYPES = (
        ("free", "Free"),
        ("pro", "Pro"),
        ("enterprise", "Enterprise"),
    )

    name = models.CharField(max_length=100)
    code = models.CharField(max_length=50, unique=True)
    plan_type = models.CharField(
        max_length=20,
        choices=PLAN_TYPES,
        default="free",
    )

    price_monthly = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
    )

    # Usage limits (NULL = unlimited)
    max_attachment_downloads = models.PositiveIntegerField(null=True, blank=True)
    max_attachment_previews = models.PositiveIntegerField(null=True, blank=True)
    max_message_views = models.PositiveIntegerField(null=True, blank=True)

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class OrganizationSubscription(models.Model):
    """
    Subscription of an organization to a billing plan
    """
    organization = models.OneToOneField(
        Organization,
        on_delete=models.CASCADE,
        related_name="subscription",
    )

    plan = models.ForeignKey(
        BillingPlan,
        on_delete=models.PROTECT,
        related_name="subscriptions",
    )

    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.organization} → {self.plan}"

class Notification(models.Model):
    NOTIFICATION_TYPES = (
        ("info", "Info"),
        ("success", "Success"),
        ("warning", "Warning"),
        ("error", "Error"),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="inbox_notifications",
    )

    title = models.CharField(max_length=255)
    message = models.TextField()

    notification_type = models.CharField(
        max_length=20,
        choices=NOTIFICATION_TYPES,
        default="info",
    )

    is_read = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} ({self.notification_type})"

class InboxSyncStatus(models.Model):
    PLATFORM_CHOICES = (
        ("gmail", "Gmail"),
        ("outlook", "Outlook"),
        ("imap", "IMAP"),
        ("teams", "Microsoft Teams"),
    )

    STATUS_CHOICES = (
        ("idle", "Idle"),
        ("syncing", "Syncing"),
        ("success", "Success"),
        ("failed", "Failed"),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="sync_statuses",
    )

    platform = models.CharField(
        max_length=20,
        choices=PLATFORM_CHOICES,
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="idle",
    )

    progress = models.PositiveIntegerField(default=0)  # 0–100

    last_synced_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("user", "platform")

    def __str__(self):
        return f"{self.user} | {self.platform} | {self.status}"

class Draft(models.Model):

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )

    email_account = models.ForeignKey(
        "email_accounts.EmailAccount",
        on_delete=models.CASCADE
    )

    recipients = models.TextField(blank=True)
    subject = models.CharField(max_length=500, blank=True)
    body = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    is_sent = models.BooleanField(default=False)
