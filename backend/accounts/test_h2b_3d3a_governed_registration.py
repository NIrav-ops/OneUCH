from django.test import (
    TestCase,
)

from django.utils import (
    timezone,
)

from accounts.authentication import (
    get_active_membership,
)

from accounts.identity_service import (
    IdentityAuthenticationError,
    IdentityClaims,
    bind_identity_claims,
)

from accounts.models import (
    AUTH_METHOD_GOOGLE,
    AUTH_METHOD_MICROSOFT,
    AUTH_METHOD_WORK_EMAIL,
    ExternalIdentity,
    REGISTRATION_STATUS_APPROVED,
    REGISTRATION_STATUS_PENDING,
    REGISTRATION_STATUS_REJECTED,
    RegistrationRequest,
    User,
)

from accounts.registration_service import (
    RegistrationConflictError,
    RegistrationReviewAuthorizationError,
    RegistrationTransitionError,
    RegistrationValidationError,
    approve_registration_request,
    reject_registration_request,
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


class H2B3D3AGovernedRegistrationTests(
    TestCase,
):

    def setUp(
        self,
    ):
        self.reviewer = (
            User.objects
            .create_user(
                email=(
                    "platform-reviewer@oneuch.test"
                ),
                password=(
                    "OneUCH!PlatformReview93471"
                ),
                is_active=True,
                is_staff=True,
                role="admin",
            )
        )


    def submit_google(
        self,
        *,
        email=(
            "new-company@oneuch.test"
        ),
        issuer=(
            "https://accounts.google.com"
        ),
        subject=(
            "google-registration-subject"
        ),
        organization_name=(
            "New Company"
        ),
    ):
        return (
            submit_registration_request(
                provider=(
                    AUTH_METHOD_GOOGLE
                ),
                issuer=issuer,
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


    def claims_for(
        self,
        registration,
    ):
        binding = (
            ExternalIdentity.objects
            .get(
                user=(
                    registration.user
                ),
                provider=(
                    registration.provider
                ),
            )
        )

        return IdentityClaims(
            provider=(
                registration.provider
            ),
            issuer=(
                binding.issuer
            ),
            subject=(
                binding.subject
            ),
            email=(
                registration.user.email
            ),
        )


    def test_pending_registration_is_fail_closed(
        self,
    ):
        (
            registration,
            created,
        ) = self.submit_google()


        self.assertTrue(
            created
        )

        self.assertEqual(
            registration.status,
            REGISTRATION_STATUS_PENDING,
        )


        user = registration.user

        organization = (
            registration.organization
        )


        self.assertFalse(
            user.is_active
        )

        self.assertFalse(
            organization.is_active
        )

        self.assertFalse(
            user.has_usable_password()
        )

        self.assertEqual(
            user.signup_method,
            AUTH_METHOD_GOOGLE,
        )


        membership = (
            OrganizationUser.objects
            .get(
                user=user
            )
        )


        self.assertEqual(
            membership.organization,
            organization,
        )

        self.assertEqual(
            membership.role,
            "owner",
        )


        self.assertIsNone(
            get_active_membership(
                user
            )
        )


        binding = (
            ExternalIdentity.objects
            .get(
                user=user
            )
        )


        self.assertEqual(
            binding.provider,
            AUTH_METHOD_GOOGLE,
        )

        self.assertEqual(
            binding.email_at_binding,
            user.email,
        )


        self.assertEqual(
            OAuthToken.objects.count(),
            0,
        )

        self.assertEqual(
            EmailAccount.objects.count(),
            0,
        )


        with self.assertRaises(
            IdentityAuthenticationError
        ):
            bind_identity_claims(
                self.claims_for(
                    registration
                )
            )


        audit = (
            AuditLog.objects
            .get(
                action=(
                    "REGISTRATION_REQUESTED"
                )
            )
        )


        self.assertEqual(
            audit.user,
            user,
        )

        self.assertEqual(
            audit.organization,
            organization,
        )

        self.assertNotIn(
            user.email,
            str(
                audit.metadata
            ),
        )


    def test_registration_captures_compliance_evidence(
        self,
    ):
        (
            registration,
            _,
        ) = self.submit_google()


        self.assertEqual(
            registration.organization_name,
            "New Company",
        )

        self.assertEqual(
            registration.privacy_notice_version,
            "privacy-2026-09",
        )

        self.assertEqual(
            registration.terms_version,
            "terms-2026-09",
        )

        self.assertEqual(
            registration.requested_region,
            "ap-south-1",
        )

        self.assertIsNotNone(
            registration.consent_recorded_at
        )

        self.assertIsNotNone(
            registration.submitted_at
        )

        self.assertIsNone(
            registration.reviewed_at
        )

        self.assertIsNone(
            registration.reviewed_by
        )


    def test_exact_identity_resubmission_is_idempotent(
        self,
    ):
        (
            first,
            first_created,
        ) = self.submit_google()


        counts = {
            "users":
                User.objects.count(),

            "organizations":
                Organization.objects.count(),

            "memberships":
                OrganizationUser.objects.count(),

            "identities":
                ExternalIdentity.objects.count(),

            "registrations":
                RegistrationRequest.objects.count(),
        }


        (
            second,
            second_created,
        ) = self.submit_google()


        self.assertTrue(
            first_created
        )

        self.assertFalse(
            second_created
        )

        self.assertEqual(
            first.id,
            second.id,
        )


        self.assertEqual(
            User.objects.count(),
            counts["users"],
        )

        self.assertEqual(
            Organization.objects.count(),
            counts["organizations"],
        )

        self.assertEqual(
            OrganizationUser.objects.count(),
            counts["memberships"],
        )

        self.assertEqual(
            ExternalIdentity.objects.count(),
            counts["identities"],
        )

        self.assertEqual(
            RegistrationRequest.objects.count(),
            counts["registrations"],
        )


    def test_existing_email_is_never_auto_linked(
        self,
    ):
        existing = (
            User.objects
            .create_user(
                email=(
                    "collision@oneuch.test"
                ),
                password=(
                    "OneUCH!Collision93471"
                ),
                signup_method=(
                    AUTH_METHOD_WORK_EMAIL
                ),
            )
        )


        with self.assertRaises(
            RegistrationConflictError
        ):
            self.submit_google(
                email=(
                    existing.email
                ),
                subject=(
                    "new-google-subject"
                ),
            )


        self.assertFalse(
            ExternalIdentity.objects
            .filter(
                user=existing
            )
            .exists()
        )


    def test_consent_and_terms_are_required(
        self,
    ):
        with self.assertRaises(
            RegistrationValidationError
        ):
            submit_registration_request(
                provider=(
                    AUTH_METHOD_GOOGLE
                ),
                issuer=(
                    "https://accounts.google.com"
                ),
                subject=(
                    "invalid-consent-subject"
                ),
                email=(
                    "invalid-consent@oneuch.test"
                ),
                organization_name=(
                    "Invalid Consent"
                ),
                privacy_notice_version="",
                terms_version=(
                    "terms-2026-09"
                ),
                consent_recorded_at=(
                    timezone.now()
                ),
            )


    def test_unsupported_provider_is_rejected(
        self,
    ):
        with self.assertRaises(
            RegistrationValidationError
        ):
            submit_registration_request(
                provider="work_email",
                issuer="local",
                subject="local",
                email=(
                    "local@oneuch.test"
                ),
                organization_name=(
                    "Local"
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
            )


    def test_non_staff_cannot_approve_registration(
        self,
    ):
        (
            registration,
            _,
        ) = self.submit_google()


        ordinary_user = (
            User.objects
            .create_user(
                email=(
                    "ordinary-reviewer@oneuch.test"
                ),
                password=(
                    "OneUCH!Ordinary93471"
                ),
                is_active=True,
            )
        )


        with self.assertRaises(
            RegistrationReviewAuthorizationError
        ):
            approve_registration_request(
                registration_public_id=(
                    registration.public_id
                ),
                reviewer=(
                    ordinary_user
                ),
            )


        registration.refresh_from_db()

        registration.user.refresh_from_db()

        registration.organization.refresh_from_db()


        self.assertEqual(
            registration.status,
            REGISTRATION_STATUS_PENDING,
        )

        self.assertFalse(
            registration.user.is_active
        )

        self.assertFalse(
            registration.organization.is_active
        )


    def test_platform_approval_activates_user_and_workspace_atomically(
        self,
    ):
        (
            registration,
            _,
        ) = self.submit_google()


        approved = (
            approve_registration_request(
                registration_public_id=(
                    registration.public_id
                ),
                reviewer=(
                    self.reviewer
                ),
            )
        )


        approved.user.refresh_from_db()

        approved.organization.refresh_from_db()


        self.assertEqual(
            approved.status,
            REGISTRATION_STATUS_APPROVED,
        )

        self.assertTrue(
            approved.user.is_active
        )

        self.assertTrue(
            approved.organization.is_active
        )

        self.assertEqual(
            approved.reviewed_by,
            self.reviewer,
        )

        self.assertIsNotNone(
            approved.reviewed_at
        )


        self.assertIsNotNone(
            get_active_membership(
                approved.user
            )
        )


        bound_user = (
            bind_identity_claims(
                self.claims_for(
                    approved
                )
            )
        )


        self.assertEqual(
            bound_user.id,
            approved.user.id,
        )


        audit = (
            AuditLog.objects
            .get(
                action=(
                    "REGISTRATION_APPROVED"
                )
            )
        )


        self.assertEqual(
            audit.user,
            self.reviewer,
        )

        self.assertEqual(
            audit.organization,
            approved.organization,
        )


    def test_rejection_remains_fail_closed_and_retains_identity(
        self,
    ):
        (
            registration,
            _,
        ) = self.submit_google()


        rejected = (
            reject_registration_request(
                registration_public_id=(
                    registration.public_id
                ),
                reviewer=(
                    self.reviewer
                ),
                rejection_reason=(
                    "Pilot access not approved."
                ),
            )
        )


        rejected.user.refresh_from_db()

        rejected.organization.refresh_from_db()


        self.assertEqual(
            rejected.status,
            REGISTRATION_STATUS_REJECTED,
        )

        self.assertFalse(
            rejected.user.is_active
        )

        self.assertFalse(
            rejected.organization.is_active
        )

        self.assertEqual(
            rejected.rejection_reason,
            "Pilot access not approved.",
        )


        self.assertTrue(
            ExternalIdentity.objects
            .filter(
                user=rejected.user,
                provider=(
                    rejected.provider
                ),
            )
            .exists()
        )


        with self.assertRaises(
            IdentityAuthenticationError
        ):
            bind_identity_claims(
                self.claims_for(
                    rejected
                )
            )


        audit = (
            AuditLog.objects
            .get(
                action=(
                    "REGISTRATION_REJECTED"
                )
            )
        )


        self.assertEqual(
            audit.user,
            self.reviewer,
        )


    def test_reviewed_registration_cannot_transition_again(
        self,
    ):
        (
            approved,
            _,
        ) = self.submit_google(
            email=(
                "approved-once@oneuch.test"
            ),
            subject=(
                "approved-once-subject"
            ),
        )


        approve_registration_request(
            registration_public_id=(
                approved.public_id
            ),
            reviewer=(
                self.reviewer
            ),
        )


        with self.assertRaises(
            RegistrationTransitionError
        ):
            reject_registration_request(
                registration_public_id=(
                    approved.public_id
                ),
                reviewer=(
                    self.reviewer
                ),
            )


        (
            rejected,
            _,
        ) = (
            submit_registration_request(
                provider=(
                    AUTH_METHOD_MICROSOFT
                ),
                issuer=(
                    "https://login.microsoftonline.com/"
                    "tenant-d3a/v2.0"
                ),
                subject=(
                    "rejected-once-subject"
                ),
                email=(
                    "rejected-once@oneuch.test"
                ),
                organization_name=(
                    "Rejected Once"
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
            )
        )


        reject_registration_request(
            registration_public_id=(
                rejected.public_id
            ),
            reviewer=(
                self.reviewer
            ),
        )


        with self.assertRaises(
            RegistrationTransitionError
        ):
            approve_registration_request(
                registration_public_id=(
                    rejected.public_id
                ),
                reviewer=(
                    self.reviewer
                ),
            )


    def test_corrupt_pending_identity_cannot_be_approved(
        self,
    ):
        (
            registration,
            _,
        ) = self.submit_google(
            email=(
                "broken-binding@oneuch.test"
            ),
            subject=(
                "broken-binding-subject"
            ),
        )


        ExternalIdentity.objects.filter(
            user=(
                registration.user
            )
        ).delete()


        with self.assertRaises(
            RegistrationTransitionError
        ):
            approve_registration_request(
                registration_public_id=(
                    registration.public_id
                ),
                reviewer=(
                    self.reviewer
                ),
            )


        registration.user.refresh_from_db()

        registration.organization.refresh_from_db()


        self.assertFalse(
            registration.user.is_active
        )

        self.assertFalse(
            registration.organization.is_active
        )


    def test_registration_audit_actions_are_declared(
        self,
    ):
        choices = dict(
            AuditLog.ACTION_CHOICES
        )


        self.assertIn(
            "REGISTRATION_REQUESTED",
            choices,
        )

        self.assertIn(
            "REGISTRATION_APPROVED",
            choices,
        )

        self.assertIn(
            "REGISTRATION_REJECTED",
            choices,
        )
