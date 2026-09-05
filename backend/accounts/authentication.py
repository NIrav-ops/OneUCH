from rest_framework.exceptions import (
    AuthenticationFailed,
)
from rest_framework_simplejwt.authentication import (
    JWTAuthentication,
)

from accounts.models import (
    AUTH_METHOD_LEGACY,
    AUTH_METHOD_WORK_EMAIL,
    User,
)
from inbox.models import (
    OrganizationUser,
)
from platform_core.context.context_manager import (
    ContextManager,
)
from platform_core.context.security import (
    SecurityContext,
)
from platform_core.context.tenant import (
    TenantContext,
)


GENERIC_LOGIN_ERROR = (
    "Invalid credentials."
)


def get_active_membership(
    user,
):

    try:

        membership = (
            OrganizationUser.objects
            .select_related(
                "organization"
            )
            .get(
                user=user
            )
        )

    except OrganizationUser.DoesNotExist:

        return None

    if not membership.organization.is_active:
        return None

    return membership


def authenticate_work_email(
    *,
    email,
    password,
):

    email = str(
        email or ""
    ).strip().lower()

    if not email or not password:
        return None

    user = (
        User.objects
        .filter(
            email__iexact=email
        )
        .first()
    )

    if user is None:
        return None

    if not user.is_active:
        return None

    # Password authentication is valid only
    # for explicit work-email identities and
    # pre-RC legacy identities.
    #
    # Future Google/Microsoft identity records
    # must never silently fall back to a local
    # password merely because one exists.

    if user.signup_method not in {
        AUTH_METHOD_LEGACY,
        AUTH_METHOD_WORK_EMAIL,
    }:
        return None

    if not user.check_password(
        password
    ):
        return None

    if get_active_membership(
        user
    ) is None:
        return None

    return user


class OneUCHJWTAuthentication(
    JWTAuthentication
):

    """
    A valid JWT is not sufficient on its own.

    Every authenticated customer request must
    still resolve to an active One UCH workspace.
    """

    def authenticate(
        self,
        request,
    ):

        result = super().authenticate(
            request
        )

        if result is None:
            return None

        user, token = result

        membership = (
            get_active_membership(
                user
            )
        )

        if membership is None:

            raise AuthenticationFailed(
                "Active workspace membership required."
            )

        organization = (
            membership.organization
        )

        request.oneuch_membership = (
            membership
        )

        request.oneuch_organization = (
            organization
        )

        request.oneuch_workspace_id = (
            organization.public_id
        )

        # RequestContextMiddleware runs before
        # DRF JWT authentication. Rebind the
        # context only after authoritative JWT
        # authentication succeeds.

        request_context = (
            ContextManager.current()
        )

        if request_context is not None:

            request_context.user = user

            request_context.organization = (
                organization
            )

            request_context.tenant = (
                TenantContext(
                    id=organization.id,
                    organization_id=(
                        organization.id
                    ),
                    name=organization.name,
                    slug=organization.slug,
                    is_active=(
                        organization.is_active
                    ),
                    metadata={},
                )
            )

            request_context.security = (
                SecurityContext(
                    user_id=user.id,
                    email=user.email,
                    role=user.role,
                    is_authenticated=True,
                    is_staff=user.is_staff,
                    is_superuser=(
                        user.is_superuser
                    ),
                    organization_id=(
                        organization.id
                    ),
                )
            )

        return (
            user,
            token,
        )
