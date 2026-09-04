from django.utils import timezone

from inbox.models import (
    AuditLog,
    OrganizationUser,
)


def get_membership(
    user,
):

    try:

        return (
            user.organization_membership
        )

    except OrganizationUser.DoesNotExist:

        return None


def write_security_audit(
    *,
    user,
    action,
    metadata=None,
):

    membership = (
        get_membership(
            user
        )
    )

    organization = (
        membership.organization
        if membership
        else None
    )

    AuditLog.objects.create(
        user=user,
        organization=organization,
        action=action,
        metadata=(
            metadata
            or {}
        ),
    )


def record_authentication_success(
    *,
    user,
    method,
):

    now = timezone.now()

    user.__class__.objects.filter(
        pk=user.pk
    ).update(
        last_login=now,
        last_auth_method=method,
    )

    user.last_login = now
    user.last_auth_method = method

    # Deliberately retain only authentication
    # provenance here.
    #
    # Email address, mailbox address, content,
    # tokens and credentials are not copied
    # into audit metadata.

    write_security_audit(
        user=user,
        action="LOGIN",
        metadata={
            "auth_method": method,
        },
    )
