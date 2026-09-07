from uuid import uuid4

from django.contrib.auth.models import (
    AbstractBaseUser,
    PermissionsMixin,
)
from django.db import models
from django.db.models.functions import Lower
from django.utils import timezone

from .manager import UserManager


AUTH_METHOD_LEGACY = "legacy"
AUTH_METHOD_WORK_EMAIL = "work_email"
AUTH_METHOD_GOOGLE = "google"
AUTH_METHOD_MICROSOFT = "microsoft"

AUTH_METHOD_CHOICES = (
    (
        AUTH_METHOD_LEGACY,
        "Legacy",
    ),
    (
        AUTH_METHOD_WORK_EMAIL,
        "Work email",
    ),
    (
        AUTH_METHOD_GOOGLE,
        "Google",
    ),
    (
        AUTH_METHOD_MICROSOFT,
        "Microsoft",
    ),
)


def generate_user_public_id():
    return (
        "USR-"
        + uuid4().hex[:12].upper()
    )


class User(
    AbstractBaseUser,
    PermissionsMixin,
):

    email = models.EmailField(
        unique=True,
    )

    public_id = models.CharField(
        max_length=20,
        unique=True,
        default=generate_user_public_id,
        editable=False,
    )

    signup_method = models.CharField(
        max_length=20,
        choices=AUTH_METHOD_CHOICES,
        default=AUTH_METHOD_LEGACY,
    )

    last_auth_method = models.CharField(
        max_length=20,
        choices=AUTH_METHOD_CHOICES,
        blank=True,
        default="",
    )

    role = models.CharField(
        max_length=20,
        choices=[
            (
                "admin",
                "Admin",
            ),
            (
                "user",
                "User",
            ),
        ],
        default="user",
    )

    is_active = models.BooleanField(
        default=True,
    )

    is_staff = models.BooleanField(
        default=False,
    )

    is_superuser = models.BooleanField(
        default=False,
    )

    created_at = models.DateTimeField(
        default=timezone.now,
    )

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = UserManager()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                Lower("email"),
                name="accounts_user_email_ci_unique",
            ),
        ]

    def __str__(self):
        return self.email

IDENTITY_PROVIDER_CHOICES = (
    (
        AUTH_METHOD_GOOGLE,
        "Google",
    ),
    (
        AUTH_METHOD_MICROSOFT,
        "Microsoft",
    ),
)


class ExternalIdentity(
    models.Model,
):
    """
    Stable external identity binding.

    Provider access/refresh/ID tokens are deliberately
    never stored here. The binding contains only the
    provider identity coordinates required to prevent
    email-only account linking.
    """

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="external_identities",
    )

    provider = models.CharField(
        max_length=20,
        choices=IDENTITY_PROVIDER_CHOICES,
    )

    issuer = models.CharField(
        max_length=255,
    )

    subject = models.CharField(
        max_length=255,
    )

    email_at_binding = models.EmailField()

    created_at = models.DateTimeField(
        default=timezone.now,
    )

    last_authenticated_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "provider",
                    "issuer",
                    "subject",
                ],
                name="acct_identity_subject_uq",
            ),
            models.UniqueConstraint(
                fields=[
                    "user",
                    "provider",
                ],
                name="acct_identity_user_provider_uq",
            ),
        ]

    def __str__(self):
        return (
            f"{self.provider}:"
            f"{self.user_id}"
        )


class IdentityLoginGrant(
    models.Model,
):
    """
    One-time short-lived bridge between the provider
    callback and the existing One UCH JWT issuance path.

    Only a SHA-256 digest of the browser-visible grant is
    persisted. Provider tokens are never stored here.
    """

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="identity_login_grants",
    )

    provider = models.CharField(
        max_length=20,
        choices=IDENTITY_PROVIDER_CHOICES,
    )

    token_hash = models.CharField(
        max_length=64,
        unique=True,
    )

    expires_at = models.DateTimeField()

    used_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(
        default=timezone.now,
    )

    class Meta:
        indexes = [
            models.Index(
                fields=[
                    "expires_at",
                ],
                name="acct_grant_expires_idx",
            ),
        ]

    def __str__(self):
        return (
            f"{self.provider}:"
            f"{self.user_id}"
        )

BROWSER_SESSION_CLAIM = (
    "oneuch_browser_session"
)


class BrowserSession(
    models.Model,
):
    """
    Server authority for a browser authentication session.

    Access and refresh JWTs carry only this public session
    identifier. Revocation and refresh-generation authority
    remain server-side.

    No browser JWT, provider token, mailbox credential, or
    customer message content is stored here.
    """

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="browser_sessions",
    )

    public_id = models.UUIDField(
        default=uuid4,
        unique=True,
        editable=False,
    )

    current_refresh_jti = models.CharField(
        max_length=64,
    )

    expires_at = models.DateTimeField()

    revoked_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    revocation_reason = models.CharField(
        max_length=40,
        blank=True,
        default="",
    )

    created_at = models.DateTimeField(
        default=timezone.now,
    )

    last_rotated_at = models.DateTimeField(
        default=timezone.now,
    )

    class Meta:
        indexes = [
            models.Index(
                fields=[
                    "user",
                    "revoked_at",
                ],
                name=(
                    "acct_bsess_user_rev_idx"
                ),
            ),
            models.Index(
                fields=[
                    "expires_at",
                ],
                name=(
                    "acct_bsess_exp_idx"
                ),
            ),
        ]

    def __str__(self):
        return (
            f"{self.user_id}:"
            f"{self.public_id}"
        )
