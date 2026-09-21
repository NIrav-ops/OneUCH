from unittest.mock import patch

from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import (
    AUTH_METHOD_GOOGLE,
    REGISTRATION_STATUS_REJECTED,
    User,
)
from accounts.registration_service import submit_registration_request
from inbox.models import Organization, OrganizationUser


@override_settings(
    REGISTRATION_APPROVAL_EMAIL_ENABLED=True,
    ONEUCH_APPROVAL_EMAIL_FROM=(
        "One UCH <no-reply@notify.cyberllix.com>"
    ),
    ONEUCH_APPROVAL_SIGNIN_URL=(
        "https://app.cyberllix.com/login"
    ),
    EMAIL_BACKEND=(
        "django.core.mail.backends.locmem.EmailBackend"
    ),
)
class M2CRejectionNoEmailTests(TestCase):

    def setUp(self):
        self.client = APIClient()

        self.reviewer = User.objects.create_user(
            email="m2c-reviewer@oneuch.test",
            password="OneUCH!M2CReviewer93471",
            is_active=True,
            is_staff=True,
            role="admin",
        )

        workspace = Organization.objects.create(
            name="One UCH Platform Operations",
            slug="oneuch-platform-m2c-review",
            is_active=True,
        )

        OrganizationUser.objects.create(
            user=self.reviewer,
            organization=workspace,
            role="owner",
        )

        self.client.force_authenticate(
            user=self.reviewer
        )

    def test_rejection_never_queues_approval_email(self):
        registration, created = submit_registration_request(
            provider=AUTH_METHOD_GOOGLE,
            issuer="https://accounts.google.com",
            subject="m2c-reject-subject",
            email="m2c-reject@oneuch.test",
            organization_name="M2C Rejected Workspace",
            first_name="Rejected",
            last_name="Applicant",
            privacy_notice_version="privacy-test",
            terms_version="terms-test",
            consent_recorded_at=timezone.now(),
            requested_region="ap-south-1",
        )

        self.assertTrue(created)

        with patch(
            (
                "accounts.tasks."
                "send_registration_approval_email_task.delay"
            )
        ) as delivery:
            response = self.client.post(
                (
                    "/api/auth/platform/registrations/"
                    + registration.public_id
                    + "/reject/"
                ),
                {
                    "rejection_reason":
                        "Internal access review denied.",
                },
                format="json",
            )

        self.assertEqual(response.status_code, 200)

        registration.refresh_from_db()
        registration.user.refresh_from_db()
        registration.organization.refresh_from_db()

        self.assertEqual(
            registration.status,
            REGISTRATION_STATUS_REJECTED,
        )
        self.assertFalse(registration.user.is_active)
        self.assertFalse(registration.organization.is_active)
        delivery.assert_not_called()
