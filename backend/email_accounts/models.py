from django.db import models
from django.conf import settings
from django.utils import timezone

# Create your models here.

User = settings.AUTH_USER_MODEL


class EmailAccount(models.Model):

    ACCOUNT_TYPES = (
        ('imap', 'IMAP / POP3'),
        ('gmail', 'Gmail (OAuth)'),
        ('outlook', 'Outlook / Microsoft 365'),
    )

    account_type = models.CharField(
    max_length=20,
    choices=ACCOUNT_TYPES,
    )   

    CREDENTIAL_STATUS = (
        ('active', 'Active'),
        ('expired', 'Expired'),
        ('reauth_required', 'Re-authentication Required'),
    )

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='email_accounts'
    )

    email_address = models.EmailField()

    smtp_password = models.CharField(
    max_length=255,
    blank=True,
    null=True,
    help_text="App password for SMTP (temporary, Phase 1 only)"
    )

    last_synced_uids = models.JSONField(
    default=dict,
    blank=True,
    help_text="Last synced IMAP UID for incremental sync"
    )


    # IMAP / SMTP settings (used only when account_type = imap)
    imap_server = models.CharField(max_length=255, blank=True, null=True)
    imap_port = models.PositiveIntegerField(blank=True, null=True)
    smtp_server = models.CharField(max_length=255, blank=True, null=True)
    smtp_port = models.PositiveIntegerField(blank=True, null=True)

    # Credential lifecycle
    credential_status = models.CharField(
        max_length=20,
        choices=CREDENTIAL_STATUS,
        default='reauth_required'
    )

    credential_expires_at = models.DateTimeField(
        null=True,
        blank=True
    )

    last_verified_at = models.DateTimeField(
        null=True,
        blank=True
    )

    # Marks completion of the bounded initial historical
    # mailbox import. Until this is populated, provider sync
    # continues using the full initial-history window so a
    # partial first import remains safely retryable.
    history_sync_completed_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    # One UCH-managed deterministic outbound signature.
    #
    # Provider-native Gmail / Outlook client signatures are
    # intentionally not assumed by the API send path.
    signature_enabled = models.BooleanField(
        default=False,
    )

    signature_text = models.TextField(
        blank=True,
        default="",
    )

    is_active = models.BooleanField(
        default=True
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def is_credential_valid(self):
        if self.credential_status != 'active':
            return False
        if self.credential_expires_at and timezone.now() > self.credential_expires_at:
            return False
        return True

    def __str__(self):
        return f"{self.email_address} ({self.account_type})"
