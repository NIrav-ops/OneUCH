from rest_framework import status

from rest_framework.permissions import (
    IsAdminUser,
)

from rest_framework.response import (
    Response,
)

from rest_framework.views import (
    APIView,
)

from accounts.authentication_events import (
    write_security_audit,
)

from accounts.models import (
    REGISTRATION_STATUS_APPROVED,
    REGISTRATION_STATUS_PENDING,
    REGISTRATION_STATUS_REJECTED,
    RegistrationRequest,
)

from accounts.registration_service import (
    RegistrationLifecycleError,
    RegistrationNotFoundError,
    RegistrationReviewAuthorizationError,
    RegistrationTransitionError,
    approve_registration_request,
    reject_registration_request,
)


REGISTRATION_STATUS_FILTERS = {
    REGISTRATION_STATUS_PENDING,
    REGISTRATION_STATUS_APPROVED,
    REGISTRATION_STATUS_REJECTED,
    "all",
}


GENERIC_REVIEW_ERROR = (
    "Unable to process registration review."
)

GENERIC_FILTER_ERROR = (
    "Invalid registration registry filter."
)


def _iso(value):
    return (
        value.isoformat()
        if value
        else None
    )


def build_safe_registration_payload(
    registration,
):
    reviewer = (
        registration.reviewed_by
    )

    return {
        "registration_id":
            registration.public_id,

        "status":
            registration.status,

        "provider":
            registration.provider,

        "organization_name":
            registration.organization_name,

        "user": {
            "user_id":
                registration.user.public_id,

            "email":
                registration.user.email,

            "active":
                bool(
                    registration.user.is_active
                ),
        },

        "workspace": {
            "workspace_id":
                registration.organization.public_id,

            "active":
                bool(
                    registration.organization.is_active
                ),
        },

        "submitted_at":
            _iso(
                registration.submitted_at
            ),

        "consent": {
            "privacy_notice_version":
                registration.privacy_notice_version,

            "terms_version":
                registration.terms_version,

            "recorded_at":
                _iso(
                    registration.consent_recorded_at
                ),

            "requested_region":
                (
                    registration.requested_region
                    or None
                ),
        },

        "review": {
            "reviewed_at":
                _iso(
                    registration.reviewed_at
                ),

            "reviewed_by":
                (
                    reviewer.public_id
                    if reviewer
                    else None
                ),

            "rejection_reason":
                (
                    registration.rejection_reason
                    if (
                        registration.status
                        ==
                        REGISTRATION_STATUS_REJECTED
                    )
                    else None
                ),
        },
    }


class PlatformRegistrationAPIView(
    APIView,
):

    permission_classes = [
        IsAdminUser,
    ]


class PlatformRegistrationRegistryAPIView(
    PlatformRegistrationAPIView,
):

    def get(
        self,
        request,
    ):
        status_filter = str(
            request.query_params.get(
                "status",
                REGISTRATION_STATUS_PENDING,
            )
            or
            REGISTRATION_STATUS_PENDING
        ).strip().lower()


        if (
            status_filter
            not in
            REGISTRATION_STATUS_FILTERS
        ):
            return Response(
                {
                    "error":
                        GENERIC_FILTER_ERROR,
                },
                status=(
                    status
                    .HTTP_400_BAD_REQUEST
                ),
            )


        try:
            limit = int(
                request.query_params.get(
                    "limit",
                    "50",
                )
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


        queryset = (
            RegistrationRequest.objects
            .select_related(
                "user",
                "organization",
                "reviewed_by",
            )
            .order_by(
                "-submitted_at"
            )
        )


        if (
            status_filter
            != "all"
        ):
            queryset = (
                queryset.filter(
                    status=status_filter
                )
            )


        registrations = list(
            queryset[:limit]
        )


        result = [
            build_safe_registration_payload(
                item
            )
            for item in registrations
        ]


        write_security_audit(
            user=request.user,
            action=(
                "SIGNUP_REGISTRY_VIEW"
            ),
            metadata={
                "registry":
                    "governed_registration",

                "status_filter":
                    status_filter,

                "returned_count":
                    len(result),
            },
        )


        return Response(
            {
                "status_filter":
                    status_filter,

                "count":
                    len(result),

                "registrations":
                    result,
            }
        )


class PlatformRegistrationApproveAPIView(
    PlatformRegistrationAPIView,
):

    def post(
        self,
        request,
        registration_id,
    ):
        try:

            registration = (
                approve_registration_request(
                    registration_public_id=(
                        registration_id
                    ),
                    reviewer=request.user,
                )
            )


        except RegistrationNotFoundError:

            return Response(
                {
                    "error":
                        GENERIC_REVIEW_ERROR,
                },
                status=(
                    status.HTTP_404_NOT_FOUND
                ),
            )


        except RegistrationTransitionError:

            return Response(
                {
                    "error":
                        GENERIC_REVIEW_ERROR,
                },
                status=(
                    status.HTTP_409_CONFLICT
                ),
            )


        except (
            RegistrationReviewAuthorizationError
        ):

            return Response(
                {
                    "error":
                        GENERIC_REVIEW_ERROR,
                },
                status=(
                    status.HTTP_403_FORBIDDEN
                ),
            )


        except RegistrationLifecycleError:

            return Response(
                {
                    "error":
                        GENERIC_REVIEW_ERROR,
                },
                status=(
                    status.HTTP_400_BAD_REQUEST
                ),
            )


        registration.refresh_from_db()


        return Response(
            build_safe_registration_payload(
                registration
            )
        )


class PlatformRegistrationRejectAPIView(
    PlatformRegistrationAPIView,
):

    def post(
        self,
        request,
        registration_id,
    ):
        reason = str(
            request.data.get(
                "rejection_reason"
            )
            or ""
        ).strip()


        if (
            not reason
            or
            len(reason) > 1000
        ):
            return Response(
                {
                    "error":
                        GENERIC_REVIEW_ERROR,
                },
                status=(
                    status.HTTP_400_BAD_REQUEST
                ),
            )


        try:

            registration = (
                reject_registration_request(
                    registration_public_id=(
                        registration_id
                    ),
                    reviewer=request.user,
                    rejection_reason=reason,
                )
            )


        except RegistrationNotFoundError:

            return Response(
                {
                    "error":
                        GENERIC_REVIEW_ERROR,
                },
                status=(
                    status.HTTP_404_NOT_FOUND
                ),
            )


        except RegistrationTransitionError:

            return Response(
                {
                    "error":
                        GENERIC_REVIEW_ERROR,
                },
                status=(
                    status.HTTP_409_CONFLICT
                ),
            )


        except (
            RegistrationReviewAuthorizationError
        ):

            return Response(
                {
                    "error":
                        GENERIC_REVIEW_ERROR,
                },
                status=(
                    status.HTTP_403_FORBIDDEN
                ),
            )


        except RegistrationLifecycleError:

            return Response(
                {
                    "error":
                        GENERIC_REVIEW_ERROR,
                },
                status=(
                    status.HTTP_400_BAD_REQUEST
                ),
            )


        registration.refresh_from_db()


        return Response(
            build_safe_registration_payload(
                registration
            )
        )
