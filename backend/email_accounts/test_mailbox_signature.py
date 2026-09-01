from django.contrib.auth import (
    get_user_model,
)

from rest_framework.test import (
    APITestCase,
)

from email_accounts.models import (
    EmailAccount,
)

from email_accounts.services.signatures import (
    apply_account_signature,
)

from inbox.models import (
    Organization,
    OrganizationUser,
)


User = get_user_model()


class MailboxSignatureTests(
    APITestCase
):

    def setUp(
        self,
    ):
        self.user = (
            User.objects.create_user(
                email="signature-user@oneuch.local",
                password="test-password-123",
            )
        )

        self.organization = (
            Organization.objects.create(
                name="Signature Organization",
                slug="signature-organization",
            )
        )

        OrganizationUser.objects.create(
            user=self.user,
            organization=self.organization,
            role="member",
        )

        self.gmail = (
            EmailAccount.objects.create(
                user=self.user,
                email_address="signature@gmail.com",
                account_type="gmail",
                credential_status="active",
                is_active=True,
            )
        )


    def url(
        self,
        account,
    ):
        return (
            "/api/email/mailbox-signature/"
            + str(
                account.id
            )
            + "/"
        )


    def test_signature_endpoint_requires_authentication(
        self,
    ):
        response = (
            self.client.get(
                self.url(
                    self.gmail
                )
            )
        )

        self.assertIn(
            response.status_code,
            {
                401,
                403,
            },
        )


    def test_user_cannot_access_another_users_mailbox_signature(
        self,
    ):
        other = (
            User.objects.create_user(
                email="other-signature@oneuch.local",
                password="test-password-123",
            )
        )

        other_account = (
            EmailAccount.objects.create(
                user=other,
                email_address="other@gmail.com",
                account_type="gmail",
                is_active=True,
            )
        )

        self.client.force_authenticate(
            user=self.user
        )

        response = (
            self.client.get(
                self.url(
                    other_account
                )
            )
        )

        self.assertEqual(
            response.status_code,
            404,
        )


    def test_cannot_enable_empty_signature(
        self,
    ):
        self.client.force_authenticate(
            user=self.user
        )

        response = (
            self.client.patch(
                self.url(
                    self.gmail
                ),
                {
                    "signature_enabled":
                        True,

                    "signature_text":
                        "   ",
                },
                format="json",
            )
        )

        self.assertEqual(
            response.status_code,
            400,
        )


    def test_signature_settings_are_user_scoped_and_projected(
        self,
    ):
        self.client.force_authenticate(
            user=self.user
        )

        response = (
            self.client.patch(
                self.url(
                    self.gmail
                ),
                {
                    "signature_enabled":
                        True,

                    "signature_text":
                        (
                            "Kind regards,\n"
                            "One UCH Pilot User"
                        ),
                },
                format="json",
            )
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.gmail.refresh_from_db()

        self.assertTrue(
            self.gmail.signature_enabled
        )

        self.assertEqual(
            self.gmail.signature_text,
            (
                "Kind regards,\n"
                "One UCH Pilot User"
            ),
        )

        adoption = (
            self.client.get(
                "/api/mail-adoption/"
            )
        )

        self.assertEqual(
            adoption.status_code,
            200,
        )

        google = next(
            item
            for item
            in adoption.data[
                "providers"
            ]
            if item[
                "provider"
            ]
            ==
            "google"
        )

        self.assertTrue(
            google[
                "signature_configured"
            ]
        )

        self.assertEqual(
            google[
                "signature_text"
            ],
            self.gmail.signature_text,
        )


    def test_signature_application_is_idempotent(
        self,
    ):
        self.gmail.signature_enabled = (
            True
        )

        self.gmail.signature_text = (
            "Regards,\nPilot"
        )

        self.gmail.save(
            update_fields=[
                "signature_enabled",
                "signature_text",
            ]
        )

        once = (
            apply_account_signature(
                account=self.gmail,
                body="Hello customer",
            )
        )

        twice = (
            apply_account_signature(
                account=self.gmail,
                body=once,
            )
        )

        self.assertEqual(
            once,
            twice,
        )

        self.assertEqual(
            once.count(
                "Regards,\nPilot"
            ),
            1,
        )
