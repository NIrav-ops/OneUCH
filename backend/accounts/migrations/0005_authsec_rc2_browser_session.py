import django.db.models.deletion
import django.utils.timezone
import uuid

from django.db import (
    migrations,
    models,
)


class Migration(
    migrations.Migration,
):

    dependencies = [
        (
            "accounts",
            "0004_auth_rc1b_identity_signin",
        ),
    ]

    operations = [
        migrations.CreateModel(
            name="BrowserSession",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "public_id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        unique=True,
                    ),
                ),
                (
                    "current_refresh_jti",
                    models.CharField(
                        max_length=64,
                    ),
                ),
                (
                    "expires_at",
                    models.DateTimeField(),
                ),
                (
                    "revoked_at",
                    models.DateTimeField(
                        blank=True,
                        null=True,
                    ),
                ),
                (
                    "revocation_reason",
                    models.CharField(
                        blank=True,
                        default="",
                        max_length=40,
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(
                        default=(
                            django.utils
                            .timezone.now
                        ),
                    ),
                ),
                (
                    "last_rotated_at",
                    models.DateTimeField(
                        default=(
                            django.utils
                            .timezone.now
                        ),
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=(
                            django.db.models
                            .deletion.CASCADE
                        ),
                        related_name=(
                            "browser_sessions"
                        ),
                        to="accounts.user",
                    ),
                ),
            ],
            options={
                "indexes": [
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
                ],
            },
        ),
    ]
