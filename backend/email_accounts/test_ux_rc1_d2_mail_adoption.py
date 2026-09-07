from unittest.mock import (
    patch,
)

from django.contrib.auth import (
    get_user_model,
)

from django.test import (
    TestCase,
)

from rest_framework.test import (
    APIClient,
)

from email_accounts.models import (
    EmailAccount,
)

from email_accounts.services.adoption import (
    MailAdoptionService,
)

from inbox.models import (
    Organization,
    OrganizationUser,
)


User = get_user_model()


class UXRC1D2MailAdoptionTests(
    TestCase
):

    def setUp(self):
        self.client = APIClient()

        self.user = (
            User.objects.create_user(
                email=(
                    "ux-d2@oneuch.test"
                ),
                password="pass123",
            )
        )

        self.organization = (
            Organization.objects.create(
                name="UX D2 Workspace",
                slug="ux-d2-workspace",
            )
        )

        OrganizationUser.objects.create(
            user=self.user,
            organization=(
                self.organization
            ),
            role="owner",
        )

    def imap_account(
        self,
        *,
        user=None,
        organization=None,
        credential_status="active",
        with_credential=True,
        is_active=True,
        email="work@oneuch.test",
    ):
        user = (
            user
            or self.user
        )

        organization = (
            organization
            or self.organization
        )

        account = EmailAccount(
            user=user,
            organization=organization,
            account_type="imap",
            email_address=email,
            imap_server=(
                "imap.example.test"
            ),
            imap_port=993,
            smtp_server=(
                "smtp.example.test"
            ),
            smtp_port=465,
            credential_status=(
                credential_status
            ),
            is_active=is_active,
        )

        if with_credential:
            account.set_credential(
                "synthetic-d2-secret"
            )

        account.save()

        return account

    def provider(
        self,
        payload,
        name,
    ):
        return next(
            item
            for item in payload[
                "providers"
            ]
            if (
                item["provider"]
                ==
                name
            )
        )

    def test_adoption_registry_contains_three_auth_modes(
        self,
    ):
        payload = (
            MailAdoptionService
            .build_payload(
                user=self.user,
                organization=(
                    self.organization
                ),
            )
        )

        self.assertEqual(
            payload[
                "summary"
            ][
                "supported"
            ],
            3,
        )

        self.assertEqual(
            {
                item["provider"]
                for item in payload[
                    "providers"
                ]
            },
            {
                "google",
                "microsoft",
                "imap",
            },
        )

        imap = self.provider(
            payload,
            "imap",
        )

        self.assertEqual(
            imap["auth_mode"],
            "credential",
        )

        self.assertEqual(
            imap["setup_path"],
            (
                "/api/email/"
                "other-work-email/"
            ),
        )

        self.assertIsNone(
            imap["sync_path"]
        )

    def test_active_imap_credential_projects_connected_without_oauth(
        self,
    ):
        account = (
            self.imap_account()
        )

        payload = (
            MailAdoptionService
            .build_payload(
                user=self.user,
                organization=(
                    self.organization
                ),
            )
        )

        imap = self.provider(
            payload,
            "imap",
        )

        self.assertEqual(
            imap[
                "connection_status"
            ],
            "connected",
        )

        self.assertTrue(
            imap["connected"]
        )

        self.assertFalse(
            imap["oauth_present"]
        )

        self.assertFalse(
            imap["oauth_active"]
        )

        self.assertEqual(
            imap[
                "credential_status"
            ],
            "active",
        )

        self.assertEqual(
            imap[
                "sync_path"
            ],
            (
                "/api/email/"
                "other-work-email/"
                f"{account.id}/sync/"
            ),
        )

        self.assertNotIn(
            "credential",
            imap,
        )

        self.assertNotIn(
            "credential_ciphertext",
            imap,
        )

    def test_invalid_imap_credential_projects_attention_required(
        self,
    ):
        self.imap_account(
            credential_status=(
                "reauth_required"
            ),
        )

        payload = (
            MailAdoptionService
            .build_payload(
                user=self.user,
                organization=(
                    self.organization
                ),
            )
        )

        imap = self.provider(
            payload,
            "imap",
        )

        self.assertEqual(
            imap[
                "connection_status"
            ],
            "reauth_required",
        )

        self.assertTrue(
            imap[
                "attention_required"
            ]
        )

    def test_imap_sync_endpoint_requires_authentication(
        self,
    ):
        account = (
            self.imap_account()
        )

        response = (
            self.client.post(
                (
                    "/api/email/"
                    "other-work-email/"
                    f"{account.id}/sync/"
                ),
                {},
                format="json",
            )
        )

        self.assertEqual(
            response.status_code,
            401,
        )

    @patch(
        "inbox.tasks."
        "sync_email_account.delay"
    )
    def test_imap_sync_queues_exact_owned_mailbox(
        self,
        queue,
    ):
        account = (
            self.imap_account()
        )

        self.client.force_authenticate(
            user=self.user
        )

        response = (
            self.client.post(
                (
                    "/api/email/"
                    "other-work-email/"
                    f"{account.id}/sync/"
                ),
                {},
                format="json",
            )
        )

        self.assertEqual(
            response.status_code,
            202,
        )

        self.assertEqual(
            response.data[
                "status"
            ],
            "sync_queued",
        )

        queue.assert_called_once_with(
            account.id
        )

    @patch(
        "inbox.tasks."
        "sync_email_account.delay"
    )
    def test_imap_sync_cannot_target_other_workspace_mailbox(
        self,
        queue,
    ):
        other = (
            User.objects.create_user(
                email=(
                    "ux-d2-other@oneuch.test"
                ),
                password="pass123",
            )
        )

        other_org = (
            Organization.objects.create(
                name=(
                    "UX D2 Other Workspace"
                ),
                slug=(
                    "ux-d2-other-workspace"
                ),
            )
        )

        OrganizationUser.objects.create(
            user=other,
            organization=other_org,
            role="owner",
        )

        account = (
            self.imap_account(
                user=other,
                organization=other_org,
                email=(
                    "other@oneuch.test"
                ),
            )
        )

        self.client.force_authenticate(
            user=self.user
        )

        response = (
            self.client.post(
                (
                    "/api/email/"
                    "other-work-email/"
                    f"{account.id}/sync/"
                ),
                {},
                format="json",
            )
        )

        self.assertEqual(
            response.status_code,
            404,
        )

        queue.assert_not_called()

    @patch(
        "inbox.tasks."
        "sync_email_account.delay"
    )
    def test_imap_sync_blocks_invalid_credential(
        self,
        queue,
    ):
        account = (
            self.imap_account(
                credential_status=(
                    "reauth_required"
                ),
            )
        )

        self.client.force_authenticate(
            user=self.user
        )

        response = (
            self.client.post(
                (
                    "/api/email/"
                    "other-work-email/"
                    f"{account.id}/sync/"
                ),
                {},
                format="json",
            )
        )

        self.assertEqual(
            response.status_code,
            409,
        )

        self.assertEqual(
            response.data[
                "status"
            ],
            "reauth_required",
        )

        queue.assert_not_called()

    @patch(
        "inbox.tasks."
        "sync_email_account.delay"
    )
    def test_imap_sync_blocks_missing_encrypted_credential(
        self,
        queue,
    ):
        account = (
            self.imap_account(
                with_credential=False,
                credential_status="active",
            )
        )

        self.client.force_authenticate(
            user=self.user
        )

        response = (
            self.client.post(
                (
                    "/api/email/"
                    "other-work-email/"
                    f"{account.id}/sync/"
                ),
                {},
                format="json",
            )
        )

        self.assertEqual(
            response.status_code,
            409,
        )

        queue.assert_not_called()
