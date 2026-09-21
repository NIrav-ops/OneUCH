from django.conf import (
    settings,
)

from django.core.mail import (
    send_mail,
)

from accounts.models import (
    ExternalIdentity,
    REGISTRATION_STATUS_APPROVED,
    RegistrationRequest,
)


class RegistrationApprovalEmailError(
    Exception,
):
    pass


def registration_approval_email_available():

    if not getattr(
        settings,
        "REGISTRATION_APPROVAL_EMAIL_ENABLED",
        False,
    ):
        return False

    from_email = str(
        getattr(
            settings,
            "ONEUCH_APPROVAL_EMAIL_FROM",
            "",
        )
        or ""
    ).strip()

    signin_url = str(
        getattr(
            settings,
            "ONEUCH_APPROVAL_SIGNIN_URL",
            "",
        )
        or ""
    ).strip()

    backend = str(
        getattr(
            settings,
            "EMAIL_BACKEND",
            "",
        )
        or ""
    ).strip()

    if (
        not from_email
        or
        not signin_url
        or
        not backend
    ):
        return False

    if (
        backend
        ==
        "django.core.mail.backends.smtp.EmailBackend"
    ):

        host = str(
            getattr(
                settings,
                "EMAIL_HOST",
                "",
            )
            or ""
        ).strip()

        port = int(
            getattr(
                settings,
                "EMAIL_PORT",
                0,
            )
            or 0
        )

        if (
            not host
            or
            port <= 0
        ):
            return False

    if (
        bool(
            getattr(
                settings,
                "EMAIL_USE_TLS",
                False,
            )
        )
        and
        bool(
            getattr(
                settings,
                "EMAIL_USE_SSL",
                False,
            )
        )
    ):
        return False

    return True


def send_registration_approval_email(
    registration_public_id,
):

    if not (
        registration_approval_email_available()
    ):
        raise RegistrationApprovalEmailError(
            "Approval email is not configured."
        )

    registration = (
        RegistrationRequest.objects
        .select_related(
            "user",
            "organization",
        )
        .filter(
            public_id=str(
                registration_public_id
                or ""
            ).strip(),
            status=(
                REGISTRATION_STATUS_APPROVED
            ),
        )
        .first()
    )

    if registration is None:
        raise RegistrationApprovalEmailError(
            "Approved registration not found."
        )

    user = registration.user
    organization = (
        registration.organization
    )

    if (
        not user.is_active
        or
        not organization.is_active
    ):
        raise RegistrationApprovalEmailError(
            "Approved account is not active."
        )

    identity = (
        ExternalIdentity.objects
        .filter(
            user=user,
            provider=(
                registration.provider
            ),
        )
        .first()
    )

    if (
        identity is None
        or
        str(
            identity.email_at_binding
        ).strip().lower()
        !=
        str(
            user.email
        ).strip().lower()
    ):
        raise RegistrationApprovalEmailError(
            "Verified identity boundary failed."
        )

    first_name = (
        str(
            user.first_name
            or ""
        ).strip()
        or
        "there"
    )

    workspace_name = str(
        registration.organization_name
        or
        organization.name
        or ""
    ).strip()

    provider_label = (
        "Google"
        if registration.provider
        == "google"
        else "Microsoft"
    )

    signin_url = str(
        settings
        .ONEUCH_APPROVAL_SIGNIN_URL
    ).strip()

    subject = (
        "Your One UCH account is approved"
    )

    message = (
        f"Hi {first_name},\n\n"
        "Your One UCH account"
        +
        (
            f" for {workspace_name}"
            if workspace_name
            else ""
        )
        +
        " has been approved.\n\n"
        "You can now sign in using the same "
        f"{provider_label} identity you used "
        "during sign up.\n\n"
        "Sign in to One UCH:\n"
        f"{signin_url}\n\n"
        "Regards,\n"
        "One UCH Team"
    )

    sent_count = send_mail(
        subject=subject,
        message=message,
        from_email=(
            settings
            .ONEUCH_APPROVAL_EMAIL_FROM
        ),
        recipient_list=[
            user.email,
        ],
        fail_silently=False,
    )

    if sent_count != 1:
        raise RegistrationApprovalEmailError(
            "Approval email delivery was "
            "not accepted."
        )

    return {
        "status":
            "sent",

        "registration_id":
            registration.public_id,
    }
