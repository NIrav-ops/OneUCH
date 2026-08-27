from django.contrib.auth import get_user_model

from rest_framework.test import APITestCase

from email_accounts.models import EmailAccount
from inbox.models import (
    InboxMessage,
    Organization,
    OrganizationUser,
)


class DraftSaveAPITests(APITestCase):

    def setUp(self):
        User = get_user_model()

        self.user = User.objects.create_user(
            email="admin@test.local",
            password="test-password-123",
        )

        self.organization = Organization.objects.create(
            name="Draft Save Test Organization",
            slug="draft-save-test-organization",
        )

        OrganizationUser.objects.create(
            user=self.user,
            organization=self.organization,
            role="member",
        )

        self.gmail_account = EmailAccount.objects.create(
            user=self.user,
            email_address="gmail-user@example.com",
            account_type="gmail",
            credential_status="active",
            is_active=True,
        )

        self.outlook_account = EmailAccount.objects.create(
            user=self.user,
            email_address="outlook-user@example.com",
            account_type="outlook",
            credential_status="active",
            is_active=True,
        )

        self.url = "/api/inbox/draft/save/"

    def test_saved_draft_uses_selected_account_as_sender(self):
        self.client.force_authenticate(
            user=self.user
        )

        response = self.client.post(
            self.url,
            {
                "subject": "Outlook draft",
                "body": "Draft body",
                "recipients": "customer@example.com",
                "account_id": self.outlook_account.id,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        draft = InboxMessage.objects.get(
            id=response.data["draft_id"]
        )

        self.assertEqual(
            draft.email_account,
            self.outlook_account,
        )

        self.assertEqual(
            draft.platform,
            "outlook",
        )

        self.assertEqual(
            draft.sender,
            "outlook-user@example.com",
        )

        self.assertNotEqual(
            draft.sender,
            self.user.email,
        )

        self.assertTrue(
            draft.is_draft
        )

        self.assertEqual(
            draft.status,
            "queued",
        )
