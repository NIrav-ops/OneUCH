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
