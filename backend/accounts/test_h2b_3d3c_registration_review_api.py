from django.test import TestCase

from django.utils import timezone

from rest_framework.test import (
    APIClient,
)

from accounts.models import (
    AUTH_METHOD_GOOGLE,
    REGISTRATION_STATUS_APPROVED,
    REGISTRATION_STATUS_PENDING,
    REGISTRATION_STATUS_REJECTED,
    ExternalIdentity,
    User,
)

from accounts.registration_service import (
    submit_registration_request,
)

from email_accounts.models import (
    EmailAccount,
)

from inbox.models import (
    AuditLog,
    Organization,
    OrganizationUser,
)

from oauth_tokens.models import (
    OAuthToken,
)


class H2B3D3CRegistrationReviewAPITests(
    TestCase,
):

    def setUp(
        self,
    ):
        self.client = APIClient()

        self.reviewer = (
            User.objects.create_user(
                email=(
                    "platform-d3c@oneuch.test"
                ),
                password=(
                    "OneUCH!D3CPlatform93471"
                ),
                is_active=True,
                is_staff=True,
                role="admin",
            )
        )

        workspace = (
            Organization.objects.create(
                name=(
                    "One UCH Platform Operations"
                ),
                slug=(
                    "oneuch-platform-d3c"
                ),
                is_active=True,
            )
        )

        OrganizationUser.objects.create(
            user=self.reviewer,
            organization=workspace,
            role="owner",
        )

        self.client.force_authenticate(
            user=self.reviewer
        )


    def make_registration(
        self,
        *,
        email=(
            "candidate-d3c@oneuch.test"
        ),
        subject=(
            "candidate-d3c-subject"
        ),
        organization_name=(
            "Candidate D3C Company"
        ),
    ):
        registration, created = (
            submit_registration_request(
                provider=(
                    AUTH_METHOD_GOOGLE
                ),
                issuer=(
                    "https://accounts.google.com"
                ),
                subject=subject,
                email=email,
                organization_name=(
                    organization_name
                ),
                privacy_notice_version=(
                    "privacy-2026-09"
                ),
                terms_version=(
                    "terms-2026-09"
                ),
                consent_recorded_at=(
                    timezone.now()
                ),
                requested_region=(
                    "ap-south-1"
                ),
            )
        )

        self.assertTrue(created)

        return registration


    def registry_url(self):
        return (
            "/api/auth/platform/"
            "registrations/"
        )


    def approve_url(
        self,
        registration,
    ):
        return (
            self.registry_url()
            + registration.public_id
            + "/approve/"
        )


    def reject_url(
        self,
        registration,
    ):
        return (
            self.registry_url()
            + registration.public_id
            + "/reject/"
        )


    def test_registry_defaults_to_pending(
        self,
    ):
        registration = (
            self.make_registration()
        )

        response = (
            self.client.get(
                self.registry_url()
            )
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(
            response.data[
                "status_filter"
            ],
            "pending",
        )

        self.assertEqual(
            response.data[
                "count"
            ],
            1,
        )

        item = (
            response.data[
                "registrations"
            ][0]
        )

        self.assertEqual(
            item[
                "registration_id"
            ],
            registration.public_id,
        )

        self.assertEqual(
            item["status"],
            REGISTRATION_STATUS_PENDING,
        )

        self.assertFalse(
            item[
                "user"
            ][
                "active"
            ]
        )

        self.assertFalse(
            item[
                "workspace"
            ][
                "active"
            ]
        )

        self.assertEqual(
            item[
                "consent"
            ][
                "privacy_notice_version"
            ],
            "privacy-2026-09",
        )

        audit = (
            AuditLog.objects
            .filter(
                user=self.reviewer,
                action=(
                    "SIGNUP_REGISTRY_VIEW"
                ),
            )
            .latest("id")
        )

        self.assertEqual(
            audit.metadata[
                "registry"
            ],
            "governed_registration",
        )

        self.assertNotIn(
            registration.user.email,
            str(
                audit.metadata
            ),
        )


    def test_invalid_filter_returns_400(
        self,
    ):
        response = self.client.get(
            self.registry_url(),
            {
                "status":
                    "deleted",
            },
        )

        self.assertEqual(
            response.status_code,
            400,
        )


    def test_approval_activates_account_and_tenant(
        self,
    ):
        registration = (
            self.make_registration()
        )

        response = self.client.post(
            self.approve_url(
                registration
            ),
            {},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        registration.refresh_from_db()

        registration.user.refresh_from_db()

        registration.organization.refresh_from_db()

        self.assertEqual(
            registration.status,
            REGISTRATION_STATUS_APPROVED,
        )

        self.assertTrue(
            registration.user.is_active
        )

        self.assertTrue(
            registration.organization.is_active
        )

        self.assertEqual(
            registration.reviewed_by,
            self.reviewer,
        )

        self.assertEqual(
            OAuthToken.objects.count(),
            0,
        )

        self.assertEqual(
            EmailAccount.objects.count(),
            0,
        )

        audit = AuditLog.objects.get(
            action=(
                "REGISTRATION_APPROVED"
            )
        )

        self.assertEqual(
            audit.user,
            self.reviewer,
        )


    def test_rejection_requires_reason_and_stays_inactive(
        self,
    ):
        registration = (
            self.make_registration()
        )

        missing = self.client.post(
            self.reject_url(
                registration
            ),
            {},
            format="json",
        )

        self.assertEqual(
            missing.status_code,
            400,
        )

        registration.refresh_from_db()

        self.assertEqual(
            registration.status,
            REGISTRATION_STATUS_PENDING,
        )

        response = self.client.post(
            self.reject_url(
                registration
            ),
            {
                "rejection_reason":
                    "Pilot request not approved.",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        registration.refresh_from_db()

        registration.user.refresh_from_db()

        registration.organization.refresh_from_db()

        self.assertEqual(
            registration.status,
            REGISTRATION_STATUS_REJECTED,
        )

        self.assertFalse(
            registration.user.is_active
        )

        self.assertFalse(
            registration.organization.is_active
        )

        self.assertTrue(
            ExternalIdentity.objects
            .filter(
                user=registration.user
            )
            .exists()
        )

        self.assertEqual(
            response.data[
                "review"
            ][
                "rejection_reason"
            ],
            "Pilot request not approved.",
        )


    def test_double_review_returns_conflict(
        self,
    ):
        registration = (
            self.make_registration()
        )

        first = self.client.post(
            self.approve_url(
                registration
            ),
            {},
            format="json",
        )

        second = self.client.post(
            self.approve_url(
                registration
            ),
            {},
            format="json",
        )

        reject = self.client.post(
            self.reject_url(
                registration
            ),
            {
                "rejection_reason":
                    "No transition.",
            },
            format="json",
        )

        self.assertEqual(
            first.status_code,
            200,
        )

        self.assertEqual(
            second.status_code,
            409,
        )

        self.assertEqual(
            reject.status_code,
            409,
        )


    def test_non_staff_is_forbidden(
        self,
    ):
        registration = (
            self.make_registration()
        )

        user = (
            User.objects.create_user(
                email=(
                    "ordinary-d3c@oneuch.test"
                ),
                password=(
                    "OneUCH!OrdinaryD3C93471"
                ),
                is_active=True,
                is_staff=False,
            )
        )

        workspace = (
            Organization.objects.create(
                name=(
                    "Ordinary D3C Workspace"
                ),
                slug=(
                    "ordinary-d3c-workspace"
                ),
                is_active=True,
            )
        )

        OrganizationUser.objects.create(
            user=user,
            organization=workspace,
            role="owner",
        )

        self.client.force_authenticate(
            user=user
        )

        self.assertEqual(
            self.client.get(
                self.registry_url()
            ).status_code,
            403,
        )

        self.assertEqual(
            self.client.post(
                self.approve_url(
                    registration
                ),
                {},
                format="json",
            ).status_code,
            403,
        )

        registration.refresh_from_db()

        self.assertEqual(
            registration.status,
            REGISTRATION_STATUS_PENDING,
        )


    def test_registry_filters_reviewed_states(
        self,
    ):
        approved = (
            self.make_registration(
                email=(
                    "approved-d3c@oneuch.test"
                ),
                subject=(
                    "approved-d3c-subject"
                ),
            )
        )

        rejected = (
            self.make_registration(
                email=(
                    "rejected-d3c@oneuch.test"
                ),
                subject=(
                    "rejected-d3c-subject"
                ),
            )
        )

        self.client.post(
            self.approve_url(
                approved
            ),
            {},
            format="json",
        )

        self.client.post(
            self.reject_url(
                rejected
            ),
            {
                "rejection_reason":
                    "Rejected for D3C.",
            },
            format="json",
        )

        approved_response = (
            self.client.get(
                self.registry_url(),
                {
                    "status":
                        "approved",
                },
            )
        )

        rejected_response = (
            self.client.get(
                self.registry_url(),
                {
                    "status":
                        "rejected",
                },
            )
        )

        all_response = (
            self.client.get(
                self.registry_url(),
                {
                    "status":
                        "all",
                },
            )
        )

        self.assertEqual(
            approved_response.data[
                "registrations"
            ][0][
                "registration_id"
            ],
            approved.public_id,
        )

        self.assertEqual(
            rejected_response.data[
                "registrations"
            ][0][
                "registration_id"
            ],
            rejected.public_id,
        )

        self.assertEqual(
            all_response.data[
                "count"
            ],
            2,
        )
