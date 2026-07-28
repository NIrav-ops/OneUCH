from django.db import models
from django.conf import settings
# Create your models here.

User = settings.AUTH_USER_MODEL

class AuditLog(models.Model):

    ACTIONS = (
        ('login', 'User Login'),
        ('logout', 'User Logout'),
        ('fetch_mail', 'Fetch Mail'),
        ('send_mail', 'Send Mail'),
        ('read_message', 'Read Message'),
        ('attachment_upload', 'Attachment Upload'),
        ('credential_expired', 'Credential Expired'),
        ('error', 'System Error'),
    )

    PLATFORMS = (
        ('gmail', 'Gmail'),
        ('outlook', 'Outlook'),
        ('imap', 'IMAP'),
        ('teams', 'Microsoft Teams'),
        ('system', 'System'),
    )

    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    action = models.CharField(
        max_length=50,
        choices=ACTIONS
    )

    platform = models.CharField(
        max_length=20,
        choices=PLATFORMS
    )

    description = models.TextField(
        help_text="Human readable log message"
    )

    metadata = models.JSONField(
        null=True,
        blank=True,
        help_text="Optional structured data (no message content)"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.action} - {self.platform} - {self.created_at}"
