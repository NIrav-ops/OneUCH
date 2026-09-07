from django.core.exceptions import (
    ValidationError,
)
from django.utils import (
    timezone,
)

from rest_framework.exceptions import (
    AuthenticationFailed,
)
from rest_framework_simplejwt.authentication import (
    JWTAuthentication,
)

from accounts.models import (
    AUTH_METHOD_LEGACY,
    AUTH_METHOD_WORK_EMAIL,
    BROWSER_SESSION_CLAIM,
    BrowserSession,
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


def get_active_browser_session(
    user,
    token,
):
    """
    Legacy/API JWTs without a browser-session claim retain
    the existing One UCH authentication contract.

    Browser access JWTs are additionally bound to an active
    server BrowserSession record, providing immediate logout
    and reuse-revocation enforcement.
    """

    session_id = str(
        token.payload.get(
            BROWSER_SESSION_CLAIM
        )
        or ""
    ).strip()

    if not session_id:
        return None

    try:
        session = (
            BrowserSession.objects
            .filter(
                public_id=session_id,
                user=user,
                revoked_at__isnull=True,
                expires_at__gt=(
                    timezone.now()
                ),
            )
            .first()
        )

    except (
        ValidationError,
        TypeError,
        ValueError,
    ) as exc:

        raise AuthenticationFailed(
            "Browser session is no longer active."
        ) from exc


    if session is None:
        raise AuthenticationFailed(
            "Browser session is no longer active."
        )


    return session


class OneUCHJWTAuthentication(
    JWTAuthentication
):

    """
    A valid JWT is not sufficient on its own.

    Every authenticated customer request must still resolve
    to an active One UCH workspace.

    Browser access JWTs additionally require a live
    server-side BrowserSession record.
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


        browser_session = (
            get_active_browser_session(
                user,
                token,
            )
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

        if browser_session is not None:
            request.oneuch_browser_session = (
                browser_session
            )


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
