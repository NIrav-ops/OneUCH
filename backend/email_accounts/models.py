
from django.conf import settings

from django.core.exceptions import (
    ValidationError,
)

from django.db import models

from django.utils import timezone


User = settings.AUTH_USER_MODEL

_UNSET = object()


class EmailAccount(models.Model):

    ACCOUNT_TYPES = (
        (
            "imap",
            "IMAP / SMTP",
        ),
        (
            "gmail",
            "Gmail (OAuth)",
        ),
        (
            "outlook",
            "Outlook / Microsoft 365",
        ),
    )

    CREDENTIAL_STATUS = (
        (
            "active",
            "Active",
        ),
        (
            "expired",
            "Expired",
        ),
        (
            "reauth_required",
            "Re-authentication Required",
        ),
    )

    account_type = models.CharField(
        max_length=20,
        choices=ACCOUNT_TYPES,
    )

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="email_accounts",
    )

    organization = models.ForeignKey(
        "inbox.Organization",
        on_delete=models.CASCADE,
        related_name="email_accounts",
    )

    email_address = models.EmailField()

    credential_ciphertext = models.TextField(
        blank=True,
        null=True,
        editable=False,
        help_text=(
            "Encrypted generic mailbox credential."
        ),
    )

    last_synced_uids = models.JSONField(
        default=dict,
        blank=True,
        help_text=(
            "Last synced IMAP UID for incremental sync"
        ),
    )

    imap_server = models.CharField(
        max_length=255,
        blank=True,
        null=True,
    )

    imap_port = models.PositiveIntegerField(
        blank=True,
        null=True,
    )

    smtp_server = models.CharField(
        max_length=255,
        blank=True,
        null=True,
    )

    smtp_port = models.PositiveIntegerField(
        blank=True,
        null=True,
    )

    credential_status = models.CharField(
        max_length=20,
        choices=CREDENTIAL_STATUS,
        default="reauth_required",
    )

    credential_expires_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    last_verified_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    history_sync_completed_at = (
        models.DateTimeField(
            null=True,
            blank=True,
        )
    )

    signature_enabled = models.BooleanField(
        default=False,
    )

    signature_text = models.TextField(
        blank=True,
        default="",
    )

    is_active = models.BooleanField(
        default=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "organization",
                    "account_type",
                    "email_address",
                ],
                name=(
                    "uniq_mailbox_org_type_email"
                ),
            ),
        ]

    def __init__(
        self,
        *args,
        **kwargs,
    ):
        legacy_credential = (
            kwargs.pop(
                "smtp_password",
                _UNSET,
            )
        )

        super().__init__(
            *args,
            **kwargs,
        )

        if (
            legacy_credential
            is not
            _UNSET
        ):
            self.set_credential(
                legacy_credential
            )

    def _active_membership_organization_id(
        self,
    ):
        if not self.user_id:
            return None

        from inbox.models import (
            OrganizationUser,
        )

        return (
            OrganizationUser.objects
            .filter(
                user_id=self.user_id,
                organization__is_active=True,
            )
            .values_list(
                "organization_id",
                flat=True,
            )
            .first()
        )

    def save(
        self,
        *args,
        **kwargs,
    ):
        membership_org_id = (
            self
            ._active_membership_organization_id()
        )

        if membership_org_id is None:
            raise ValidationError(
                "Mailbox owner requires an "
                "active workspace membership."
            )

        if self.organization_id is None:
            self.organization_id = (
                membership_org_id
            )

        elif (
            self.organization_id
            !=
            membership_org_id
        ):
            raise ValidationError(
                "Mailbox workspace ownership mismatch."
            )

        super().save(
            *args,
            **kwargs,
        )

    def set_credential(
        self,
        plaintext,
    ):
        from email_accounts.services.credential_vault import (
            encrypt_credential,
        )

        self.credential_ciphertext = (
            encrypt_credential(
                plaintext
            )
        )

    def get_credential(
        self,
    ):
        from email_accounts.services.credential_vault import (
            decrypt_credential,
        )

        return decrypt_credential(
            self.credential_ciphertext
        )

    @property
    def smtp_password(
        self,
    ):
        return self.get_credential()

    @smtp_password.setter
    def smtp_password(
        self,
        value,
    ):
        self.set_credential(
            value
        )

    def is_credential_valid(
        self,
    ):
        if (
            self.credential_status
            !=
            "active"
        ):
            return False

        if (
            self.credential_expires_at
            and
            timezone.now()
            >
            self.credential_expires_at
        ):
            return False

        return True

    def __str__(
        self,
    ):
        return (
            f"{self.email_address} "
            f"({self.account_type})"
        )
