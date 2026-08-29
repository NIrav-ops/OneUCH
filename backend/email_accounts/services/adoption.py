from django.utils import timezone

from email_accounts.models import (
    EmailAccount,
)

from inbox.models import (
    InboxSyncStatus,
)

from oauth_tokens.models import (
    OAuthToken,
)


class MailAdoptionService:
    """
    Read-only user mailbox adoption projection.

    Existing OAuth and sync implementations remain authoritative.
    This service only explains their current state to the UI.

    OAuth EmailAccount.credential_status is intentionally NOT used
    as the primary Gmail/Outlook connection signal because the
    existing OAuth callbacks do not currently maintain that field.
    """

    PROVIDERS = (
        {
            "provider": "google",
            "account_type": "gmail",
            "platform": "gmail",
            "label": "Gmail",
            "connect_path": "/api/google/oauth/start/",
            "sync_path": "/api/google/oauth/sync/",
        },
        {
            "provider": "microsoft",
            "account_type": "outlook",
            "platform": "outlook",
            "label": "Microsoft 365 / Outlook",
            "connect_path": "/api/microsoft/oauth/start/",
            "sync_path": "/api/microsoft/oauth/sync/",
        },
    )

    STATUS_CONNECTED = "connected"
    STATUS_DISCONNECTED = "disconnected"
    STATUS_REAUTH_REQUIRED = "reauth_required"
    STATUS_ADMIN_DISABLED = "admin_disabled"

    @classmethod
    def build_payload(
        cls,
        *,
        user,
    ):
        providers = [
            cls._provider_status(
                user=user,
                config=config,
            )
            for config in cls.PROVIDERS
        ]

        return {
            "generated_at":
                timezone.now(),

            "summary":
                cls._summary(
                    providers
                ),

            "providers":
                providers,
        }

    @classmethod
    def _provider_status(
        cls,
        *,
        user,
        config,
    ):
        account = (
            EmailAccount.objects
            .filter(
                user=user,
                account_type=(
                    config[
                        "account_type"
                    ]
                ),
            )
            .order_by(
                "-is_active",
                "-id",
            )
            .first()
        )

        token = (
            OAuthToken.objects
            .filter(
                user=user,
                provider=(
                    config[
                        "provider"
                    ]
                ),
            )
            .order_by(
                "-is_active",
                "-updated_at",
                "-id",
            )
            .first()
        )

        sync = (
            InboxSyncStatus.objects
            .filter(
                user=user,
                platform=(
                    config[
                        "platform"
                    ]
                ),
            )
            .first()
        )

        connection_status = (
            cls._connection_status(
                account=account,
                token=token,
            )
        )

        token_expired = (
            bool(
                token
                and token.is_expired()
            )
        )

        refresh_available = (
            bool(
                token
                and token.refresh_token
            )
        )

        connected = (
            connection_status
            ==
            cls.STATUS_CONNECTED
        )

        attention_required = (
            connection_status
            in {
                cls.STATUS_REAUTH_REQUIRED,
                cls.STATUS_ADMIN_DISABLED,
            }
        )

        return {
            "provider":
                config[
                    "provider"
                ],

            "label":
                config[
                    "label"
                ],

            "account_type":
                config[
                    "account_type"
                ],

            "connection_status":
                connection_status,

            "connected":
                connected,

            "attention_required":
                attention_required,

            "account_id":
                (
                    account.id
                    if account
                    else None
                ),

            "email_address":
                (
                    account.email_address
                    if account
                    else None
                ),

            "account_active":
                bool(
                    account
                    and account.is_active
                ),

            "oauth_present":
                token is not None,

            "oauth_active":
                bool(
                    token
                    and token.is_active
                ),

            "admin_disabled":
                bool(
                    token
                    and token.disabled_by_admin
                ),

            "token_expired":
                token_expired,

            "refresh_available":
                refresh_available,

            "token_expires_at":
                (
                    token.expires_at
                    if token
                    else None
                ),

            "sync_status":
                (
                    sync.status
                    if sync
                    else "not_started"
                ),

            "sync_progress":
                (
                    sync.progress
                    if sync
                    else 0
                ),

            "last_synced_at":
                (
                    sync.last_synced_at
                    if sync
                    else None
                ),

            "sync_error":
                (
                    sync.error_message
                    if sync
                    else ""
                ),

            "connect_path":
                config[
                    "connect_path"
                ],

            "sync_path":
                config[
                    "sync_path"
                ],
        }

    @classmethod
    def _connection_status(
        cls,
        *,
        account,
        token,
    ):
        if (
            account is None
            and token is None
        ):
            return (
                cls.STATUS_DISCONNECTED
            )

        if (
            token is not None
            and token.disabled_by_admin
        ):
            return (
                cls.STATUS_ADMIN_DISABLED
            )

        if (
            account is None
            or not account.is_active
        ):
            return (
                cls.STATUS_REAUTH_REQUIRED
            )

        if (
            token is None
            or not token.is_active
        ):
            return (
                cls.STATUS_REAUTH_REQUIRED
            )

        if (
            token.is_expired()
            and not token.refresh_token
        ):
            return (
                cls.STATUS_REAUTH_REQUIRED
            )

        # An expired token with a refresh token is still a
        # connected mailbox because existing provider services
        # refresh it on demand.
        return (
            cls.STATUS_CONNECTED
        )

    @classmethod
    def _summary(
        cls,
        providers,
    ):
        return {
            "supported":
                len(
                    providers
                ),

            "connected":
                sum(
                    1
                    for item in providers
                    if item[
                        "connection_status"
                    ]
                    ==
                    cls.STATUS_CONNECTED
                ),

            "disconnected":
                sum(
                    1
                    for item in providers
                    if item[
                        "connection_status"
                    ]
                    ==
                    cls.STATUS_DISCONNECTED
                ),

            "attention_required":
                sum(
                    1
                    for item in providers
                    if item[
                        "attention_required"
                    ]
                ),

            "synced_once":
                sum(
                    1
                    for item in providers
                    if item[
                        "last_synced_at"
                    ]
                    is not None
                ),
        }
