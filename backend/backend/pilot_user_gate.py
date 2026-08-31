
from django.utils import (
    timezone,
)


SUPPORTED_ACCOUNT_PROVIDERS = {
    "gmail": "google",
    "outlook": "microsoft",
}


def _token_is_usable(
    token,
):
    if token is None:
        return False

    if not token.is_active:
        return False

    if token.disabled_by_admin:
        return False

    if token.revoked_at is not None:
        return False

    if (
        token.expires_at
        <= timezone.now()
        and not token.refresh_token
    ):
        return False

    return True


def collect_pilot_user_errors(
    *,
    email,
    user_model,
    organization_user_model,
    email_account_model,
    oauth_token_model,
    sync_status_model,
):
    """
    Validate the selected real user's application readiness.

    This deliberately performs only read operations.

    No credential, token, message content or mailbox address
    is returned in validation errors.
    """

    errors = []

    normalized_email = str(
        email or ""
    ).strip()

    if not normalized_email:
        return [
            "Pilot user email is required."
        ]

    try:
        user = (
            user_model.objects.get(
                email__iexact=(
                    normalized_email
                )
            )
        )

    except user_model.DoesNotExist:
        return [
            "Selected pilot user does not exist."
        ]

    except user_model.MultipleObjectsReturned:
        return [
            "Selected pilot user identity is ambiguous."
        ]


    if not user.is_active:
        errors.append(
            "Selected pilot user must be active."
        )


    membership = (
        organization_user_model.objects
        .select_related(
            "organization"
        )
        .filter(
            user=user
        )
        .first()
    )


    if membership is None:

        errors.append(
            "Selected pilot user must have "
            "an organization membership."
        )

    elif not membership.organization.is_active:

        errors.append(
            "Selected pilot user's organization "
            "must be active."
        )


    accounts = list(
        email_account_model.objects
        .filter(
            user=user,
            is_active=True,
            account_type__in=(
                SUPPORTED_ACCOUNT_PROVIDERS.keys()
            ),
        )
        .order_by(
            "id"
        )
    )


    if not accounts:

        errors.append(
            "Selected pilot user must have at least "
            "one active Gmail or Outlook account."
        )

        return errors


    usable_platforms = []


    for account in accounts:

        provider = (
            SUPPORTED_ACCOUNT_PROVIDERS[
                account.account_type
            ]
        )

        tokens = (
            oauth_token_model.objects
            .filter(
                user=user,
                provider=provider,
            )
            .order_by(
                "-updated_at",
                "-id",
            )
        )


        usable_token = next(
            (
                token
                for token in tokens
                if _token_is_usable(
                    token
                )
            ),
            None,
        )


        if usable_token is not None:

            usable_platforms.append(
                account.account_type
            )


    if not usable_platforms:

        errors.append(
            "Selected pilot user must have a usable "
            "Google or Microsoft OAuth authorization."
        )

        return errors


    successful_sync_exists = (
        sync_status_model.objects
        .filter(
            user=user,
            platform__in=(
                usable_platforms
            ),
            status="success",
            last_synced_at__isnull=False,
        )
        .exists()
    )


    if not successful_sync_exists:

        errors.append(
            "Selected pilot user must complete at least "
            "one successful Gmail or Outlook synchronization."
        )


    return errors
