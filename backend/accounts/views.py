from uuid import uuid4

from django.conf import settings
from django.contrib.auth.password_validation import (
    validate_password,
)
from django.core.exceptions import (
    ValidationError,
)
from django.core.validators import (
    validate_email,
)
from django.db import (
    IntegrityError,
    transaction,
)
from rest_framework import status
from rest_framework.exceptions import (
    NotFound,
)
from rest_framework.permissions import (
    AllowAny,
    IsAdminUser,
    IsAuthenticated,
)
from rest_framework.response import (
    Response,
)
from rest_framework.throttling import (
    ScopedRateThrottle,
)
from rest_framework.views import (
    APIView,
)
from rest_framework_simplejwt.tokens import (
    RefreshToken,
)

from accounts.authentication import (
    authenticate_work_email,
    get_active_membership,
)
from accounts.authentication_events import (
    get_membership,
    record_authentication_success,
    write_security_audit,
)
from accounts.models import (
    AUTH_METHOD_WORK_EMAIL,
    User,
)
from email_accounts.models import (
    EmailAccount,
)
from inbox.models import (
    Organization,
    OrganizationUser,
)


GENERIC_SIGNUP_ERROR = (
    "Unable to create account "
    "with supplied details."
)

GENERIC_LOGIN_ERROR = (
    "Invalid credentials."
)


PROVIDER_LABELS = {
    "gmail": "gmail",
    "outlook": "microsoft",
    "imap": "other_work_email",
}


def get_provider_map(
    user_ids,
):

    provider_map = {
        user_id: set()
        for user_id
        in user_ids
    }

    if not user_ids:
        return provider_map

    # Deliberately query only user ID and
    # provider category.
    #
    # EmailAccount.email_address and all
    # credential/configuration fields are
    # intentionally excluded.

    rows = (
        EmailAccount.objects
        .filter(
            user_id__in=user_ids,
            is_active=True,
        )
        .values_list(
            "user_id",
            "account_type",
        )
    )

    for (
        user_id,
        account_type,
    ) in rows:

        label = (
            PROVIDER_LABELS.get(
                account_type,
                "other_work_email",
            )
        )

        provider_map.setdefault(
            user_id,
            set(),
        ).add(
            label
        )

    return provider_map


def get_provider_labels(
    user,
):

    provider_map = (
        get_provider_map(
            [
                user.id
            ]
        )
    )

    return sorted(
        provider_map.get(
            user.id,
            set(),
        )
    )


def build_safe_identity_payload(
    *,
    user,
):

    membership = (
        get_active_membership(
            user
        )
    )

    workspace = (
        membership.organization
        if membership
        else None
    )

    providers = (
        get_provider_labels(
            user
        )
    )

    return {
        "user_id": (
            user.public_id
        ),
        "email": (
            user.email
        ),
        "workspace_id": (
            workspace.public_id
            if workspace
            else None
        ),
        "signup_method": (
            user.signup_method
        ),
        "last_auth_method": (
            user.last_auth_method
            or None
        ),
        "signed_up_at": (
            user.created_at.isoformat()
            if user.created_at
            else None
        ),
        "last_sign_in_at": (
            user.last_login.isoformat()
            if user.last_login
            else None
        ),
        "status": (
            "active"
            if (
                user.is_active
                and workspace is not None
                and workspace.is_active
            )
            else "disabled"
        ),
        "environment": (
            settings.ONEUCH_ENVIRONMENT
        ),
        "region": (
            settings.ONEUCH_REGION
        ),
        "mailbox_connected": (
            bool(
                providers
            )
        ),
        "mail_providers": (
            providers
        ),
    }


class SignupAPIView(
    APIView
):

    authentication_classes = []

    permission_classes = [
        AllowAny,
    ]

    throttle_classes = [
        ScopedRateThrottle,
    ]

    throttle_scope = "signup"

    def post(
        self,
        request,
    ):

        # Public signup remains fail-closed
        # until SEC-RC1B is GREEN.

        if not (
            settings
            .AUTH_SELF_SERVICE_SIGNUP_ENABLED
        ):

            raise NotFound()

        email = str(
            request.data.get(
                "email",
                "",
            )
        ).strip().lower()

        password = (
            request.data.get(
                "password"
            )
        )

        if (
            not email
            or not password
        ):

            return Response(
                {
                    "error": (
                        GENERIC_SIGNUP_ERROR
                    ),
                },
                status=(
                    status
                    .HTTP_400_BAD_REQUEST
                ),
            )

        try:

            validate_email(
                email
            )

        except ValidationError:

            return Response(
                {
                    "error": (
                        GENERIC_SIGNUP_ERROR
                    ),
                },
                status=(
                    status
                    .HTTP_400_BAD_REQUEST
                ),
            )

        if (
            User.objects
            .filter(
                email__iexact=email
            )
            .exists()
        ):

            return Response(
                {
                    "error": (
                        GENERIC_SIGNUP_ERROR
                    ),
                },
                status=(
                    status
                    .HTTP_400_BAD_REQUEST
                ),
            )

        candidate_user = (
            User(
                email=email
            )
        )

        try:

            validate_password(
                password,
                user=candidate_user,
            )

        except ValidationError:

            return Response(
                {
                    "error": (
                        "Password does not meet "
                        "security requirements."
                    ),
                },
                status=(
                    status
                    .HTTP_400_BAD_REQUEST
                ),
            )

        try:

            with transaction.atomic():

                user = (
                    User.objects
                    .create_user(
                        email=email,
                        password=password,
                        signup_method=(
                            AUTH_METHOD_WORK_EMAIL
                        ),
                    )
                )

                workspace = (
                    Organization.objects
                    .create(
                        name=(
                            "Private Workspace"
                        ),
                        slug=(
                            "workspace-"
                            + uuid4().hex
                        ),
                    )
                )

                OrganizationUser.objects.create(
                    user=user,
                    organization=workspace,
                    role="owner",
                )

                # Audit only the event provenance.
                # Do not duplicate email/content
                # into metadata.

                write_security_audit(
                    user=user,
                    action="SIGNUP",
                    metadata={
                        "signup_method": (
                            AUTH_METHOD_WORK_EMAIL
                        ),
                    },
                )

        except IntegrityError:

            return Response(
                {
                    "error": (
                        GENERIC_SIGNUP_ERROR
                    ),
                },
                status=(
                    status
                    .HTTP_400_BAD_REQUEST
                ),
            )

        # Registration and authentication
        # remain separate governed events.

        return Response(
            {
                "status": "created",
                "user": {
                    "id": (
                        user.public_id
                    ),
                    "email": (
                        user.email
                    ),
                },
                "workspace": {
                    "id": (
                        workspace.public_id
                    ),
                },
                "signup_method": (
                    AUTH_METHOD_WORK_EMAIL
                ),
            },
            status=(
                status.HTTP_201_CREATED
            ),
        )


class LoginAPIView(
    APIView
):

    authentication_classes = []

    permission_classes = [
        AllowAny,
    ]

    throttle_classes = [
        ScopedRateThrottle,
    ]

    throttle_scope = "login"

    def post(
        self,
        request,
    ):

        email = (
            request.data.get(
                "email"
            )
        )

        password = (
            request.data.get(
                "password"
            )
        )

        user = (
            authenticate_work_email(
                email=email,
                password=password,
            )
        )

        if user is None:

            return Response(
                {
                    "error": (
                        GENERIC_LOGIN_ERROR
                    ),
                },
                status=(
                    status
                    .HTTP_401_UNAUTHORIZED
                ),
            )

        record_authentication_success(
            user=user,
            method=(
                AUTH_METHOD_WORK_EMAIL
            ),
        )

        refresh = (
            RefreshToken.for_user(
                user
            )
        )

        return Response(
            {
                "access": str(
                    refresh.access_token
                ),
                "refresh": str(
                    refresh
                ),
            }
        )


class MeAPIView(
    APIView
):

    permission_classes = [
        IsAuthenticated,
    ]

    def get(
        self,
        request,
    ):

        return Response(
            build_safe_identity_payload(
                user=request.user
            )
        )


class StaffSignupRegistryAPIView(
    APIView
):

    """
    Minimal One UCH platform operations
    registry.

    This is intentionally NOT a mailbox or
    customer-content administration endpoint.
    """

    permission_classes = [
        IsAdminUser,
    ]

    def get(
        self,
        request,
    ):

        raw_limit = (
            request.query_params.get(
                "limit",
                "50",
            )
        )

        try:

            limit = int(
                raw_limit
            )

        except (
            TypeError,
            ValueError,
        ):

            limit = 50

        limit = max(
            1,
            min(
                limit,
                100,
            ),
        )

        users = list(
            User.objects
            .select_related(
                (
                    "organization_membership"
                    "__organization"
                )
            )
            .order_by(
                "-created_at"
            )[:limit]
        )

        user_ids = [
            user.id
            for user
            in users
        ]

        provider_map = (
            get_provider_map(
                user_ids
            )
        )

        result = []

        for user in users:

            membership = (
                get_membership(
                    user
                )
            )

            workspace = (
                membership.organization
                if membership
                else None
            )

            providers = sorted(
                provider_map.get(
                    user.id,
                    set(),
                )
            )

            account_active = bool(
                user.is_active
                and workspace is not None
                and workspace.is_active
            )

            result.append(
                {
                    "user_id": (
                        user.public_id
                    ),
                    "email": (
                        user.email
                    ),
                    "workspace_id": (
                        workspace.public_id
                        if workspace
                        else None
                    ),
                    "signup_method": (
                        user.signup_method
                    ),
                    "last_auth_method": (
                        user.last_auth_method
                        or None
                    ),
                    "signed_up_at": (
                        user.created_at.isoformat()
                        if user.created_at
                        else None
                    ),
                    "last_sign_in_at": (
                        user.last_login.isoformat()
                        if user.last_login
                        else None
                    ),
                    "status": (
                        "active"
                        if account_active
                        else "disabled"
                    ),
                    "environment": (
                        settings
                        .ONEUCH_ENVIRONMENT
                    ),
                    "region": (
                        settings
                        .ONEUCH_REGION
                    ),
                    "mailbox_connected": (
                        bool(
                            providers
                        )
                    ),
                    "mail_providers": (
                        providers
                    ),
                }
            )

        write_security_audit(
            user=request.user,
            action=(
                "SIGNUP_REGISTRY_VIEW"
            ),
            metadata={
                "returned_count": (
                    len(
                        result
                    )
                ),
            },
        )

        return Response(
            {
                "count": (
                    len(
                        result
                    )
                ),
                "users": (
                    result
                ),
            }
        )
