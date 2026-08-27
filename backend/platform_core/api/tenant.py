from django.http import Http404


def get_request_organization(request):
    """
    Return the authenticated user's active organization.

    Tenant identity is always derived from the authenticated
    user's membership and never trusted from client input.
    """

    user = getattr(
        request,
        "user",
        None,
    )

    if (
        user is None
        or not getattr(
            user,
            "is_authenticated",
            False,
        )
    ):
        return None

    try:
        membership = (
            user.organization_membership
        )
    except Exception:
        return None

    organization = getattr(
        membership,
        "organization",
        None,
    )

    if (
        organization is None
        or not organization.is_active
    ):
        return None

    return organization


def get_user_organization_or_404(
    request,
):
    """
    Return the authenticated user's organization.

    Deliberately returns 404 when organization membership
    does not exist so tenant information is not disclosed.
    """

    organization = (
        get_request_organization(
            request
        )
    )

    if organization is None:
        raise Http404(
            "Organization not found."
        )

    return organization


def get_scoped_organization_or_404(
    request,
    organization_id,
):
    """
    Allow access only when the requested organization
    matches the authenticated user's organization.
    """

    organization = (
        get_user_organization_or_404(
            request
        )
    )

    if (
        str(organization.id)
        != str(organization_id)
    ):
        raise Http404(
            "Organization not found."
        )

    return organization
