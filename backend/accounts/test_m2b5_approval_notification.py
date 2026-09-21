from unittest.mock import (
    patch,
)

from django.core import (
    mail,
)

from django.test import (
    TestCase,
    override_settings,
)

from django.utils import (
    timezone,
)

from accounts.identity_service import (
    registration_public_configuration,
)

from accounts.models import (
    AUTH_METHOD_GOOGLE,
    REGISTRATION_STATUS_APPROVED,
    User,
)

from accounts.registration_notifications import (
    send_registration_approval_email,
)

from accounts.registration_service import (
    approve_registration_request,
    submit_registration_request,
)


EMAIL_SETTINGS = dict(
    EMAIL_BACKEND=(
        "django.core.mail.backends."
        "locmem.EmailBackend"
    ),
    REGISTRATION_APPROVAL_EMAIL_ENABLED=True,
    ONEUCH_APPROVAL_EMAIL_FROM=(
        "One UCH <no-reply@cyberllix.com>"
    ),
    ONEUCH_APPROVAL_SIGNIN_URL=(
        "https://app.cyberllix.com/login"
    ),
)


class M2B5ApprovalNotificationTests(
    TestCase,
):

    def setUp(self):

        self.reviewer = (
            User.objects.create_user(
                email=(
                    "approval-reviewer"
                    "@oneuch.test"
                ),
                password=(
                    "OneUCH!Approval93471"
                ),
                is_active=True,
                is_staff=True,
            )
        )


    def create_pending_registration(
        self,
        *,
        subject="approval-email-subject",
        email="approval-user@oneuch.test",
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
                    "Approval Email Workspace"
                ),
                privacy_notice_version=(
                    "privacy-test"
                ),
                terms_version=(
                    "terms-test"
                ),
                consent_recorded_at=(
                    timezone.now()
                ),
                requested_region=(
                    "ap-south-1"
                ),
                first_name="Approval",
                last_name="User",
                phone_number=(
                    "+91 99999 99999"
                ),
            )
        )

        self.assertTrue(
            created
        )

        return registration


    def create_approved_registration(
        self,
    ):

        registration = (
            self.create_pending_registration()
        )

        with override_settings(
            REGISTRATION_APPROVAL_EMAIL_ENABLED=False,
        ):

            registration = (
                approve_registration_request(
                    registration_public_id=(
                        registration.public_id
                    ),
                    reviewer=self.reviewer,
                )
            )

        return registration


    @override_settings(
        **EMAIL_SETTINGS
    )
    def test_email_is_minimized_and_identity_bound(
        self,
    ):

        registration = (
            self.create_approved_registration()
        )

        result = (
            send_registration_approval_email(
                registration.public_id
            )
        )

        self.assertEqual(
            result["status"],
            "sent",
        )

        self.assertEqual(
            len(
                mail.outbox
            ),
            1,
        )

        message = (
            mail.outbox[0]
        )

        self.assertEqual(
            message.to,
            [
                registration.user.email,
            ],
        )

        self.assertEqual(
            message.subject,
            (
                "Your One UCH account "
                "is approved"
            ),
        )

        self.assertIn(
            "Approval",
            message.body,
        )

        self.assertIn(
            "Approval Email Workspace",
            message.body,
        )

        self.assertIn(
            (
                "https://app.cyberllix.com/"
                "login"
            ),
            message.body,
        )

        self.assertNotIn(
            registration.user.phone_number,
            message.body,
        )

        self.assertNotIn(
            registration
            .privacy_notice_version,
            message.body,
        )

        self.assertNotIn(
            registration
            .terms_version,
            message.body,
        )

        identity = (
            registration
            .user
            .external_identities
            .get(
                provider="google"
            )
        )

        self.assertNotIn(
            identity.subject,
            message.body,
        )


    @override_settings(
        AUTH_IDENTITY_SIGNIN_ENABLED=True,
        AUTH_GOVERNED_REGISTRATION_ENABLED=True,
        ONEUCH_PRIVACY_NOTICE_VERSION=(
            "privacy-test"
        ),
        ONEUCH_TERMS_VERSION=(
            "terms-test"
        ),
        ONEUCH_REGION="ap-south-1",
        GOOGLE_IDENTITY_CLIENT_ID=(
            "synthetic-google"
        ),
        GOOGLE_IDENTITY_CLIENT_SECRET=(
            "synthetic-secret"
        ),
        GOOGLE_IDENTITY_REDIRECT_URI=(
            "https://api.oneuch.test/"
            "api/auth/identity/google/"
            "callback/"
        ),
        **EMAIL_SETTINGS,
    )
    def test_public_config_exposes_only_capability_boolean(
        self,
    ):

        payload = (
            registration_public_configuration()
        )

        self.assertTrue(
            payload[
                "approval_email_enabled"
            ]
        )

        serialized = str(
            payload
        ).lower()

        self.assertNotIn(
            "email_host",
            serialized,
        )

        self.assertNotIn(
            "no-reply@cyberllix.com",
            serialized,
        )


    @override_settings(
        **EMAIL_SETTINGS
    )
    def test_queue_failure_does_not_rollback_approval(
        self,
    ):

        registration = (
            self.create_pending_registration(
                subject=(
                    "queue-failure-subject"
                ),
                email=(
                    "queue-failure@oneuch.test"
                ),
            )
        )

        with patch(
            (
                "accounts.tasks."
                "send_registration_approval_email_task."
                "delay"
            ),
            side_effect=RuntimeError(
                "synthetic queue failure"
            ),
        ):

            with (
                self
                .captureOnCommitCallbacks(
                    execute=True
                )
            ):

                approved = (
                    approve_registration_request(
                        registration_public_id=(
                            registration.public_id
                        ),
                        reviewer=self.reviewer,
                    )
                )

        approved.refresh_from_db()
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
