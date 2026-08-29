from datetime import (
    datetime,
    timezone as dt_timezone,
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

from actions.models import (
    ActionItem,
    ExpectedResponseItem,
)

from inbox.models import (
    Conversation,
    InboxMessage,
    Organization,
    OrganizationUser,
)

from knowledge.services.commitments import (
    CommitmentsService,
)


User = get_user_model()


class CommitmentsServiceTests(
    TestCase
):

    def setUp(self):
        self.user = (
            User.objects.create_user(
                email=(
                    "commitments@oneuch.test"
                ),
                password="pass123",
            )
        )

        self.organization = (
            Organization.objects.create(
                name="Commitments Org",
                slug="commitments-org",
            )
        )

        self.other_organization = (
            Organization.objects.create(
                name="Other Commitments Org",
                slug="other-commitments-org",
            )
        )

        self.conversation = (
            Conversation.objects.create(
                user=self.user,
                organization=(
                    self.organization
                ),
                conversation_key=(
                    "commitments-thread"
                ),
                subject="Commercial commitments",
            )
        )

        self.counter = 0

    def message(
        self,
        *,
        direction="inbound",
        sender=None,
        recipients=None,
        body="Commitment evidence",
    ):
        self.counter += 1

        if sender is None:
            sender = (
                "customer@example.com"
                if direction == "inbound"
                else self.user.email
            )

        if recipients is None:
            recipients = (
                self.user.email
                if direction == "inbound"
                else "vendor@example.com"
            )

        return InboxMessage.objects.create(
            user=self.user,
            organization=(
                self.organization
            ),
            conversation=(
                self.conversation
            ),
            platform="gmail",
            direction=direction,
            external_message_id=(
                "commitments-message-"
                f"{self.counter}"
            ),
            sender=sender,
            recipients=recipients,
            subject="Commitment",
            body=body,
            received_at=datetime(
                2026,
                8,
                29,
                8,
                self.counter,
                tzinfo=dt_timezone.utc,
            ),
        )

    def test_summary_counts_direction_and_status(
        self,
    ):
        action_message = self.message(
            body=(
                "Please send revised pricing."
            )
        )

        ActionItem.objects.create(
            user=self.user,
            organization=(
                self.organization
            ),
            message=action_message,
            title="Send revised pricing",
            owner=self.user,
            source_type="email",
            status="open",
            confidence_score=90,
        )

        expected_message = self.message(
            sender="vendor@example.com",
            body=(
                "We will confirm approval tomorrow."
            ),
        )

        ExpectedResponseItem.objects.create(
            user=self.user,
            organization=(
                self.organization
            ),
            conversation=(
                self.conversation
            ),
            source_message=(
                expected_message
            ),
            expected_from=(
                "vendor@example.com"
            ),
            evidence_text=(
                "We will confirm approval tomorrow."
            ),
            status="received",
            resolved_at=datetime(
                2026,
                8,
                29,
                9,
                0,
                tzinfo=dt_timezone.utc,
            ),
        )

        payload = (
            CommitmentsService
            .build_payload(
                organization=(
                    self.organization
                )
            )
        )

        summary = payload[
            "summary"
        ]

        self.assertEqual(
            summary["total"],
            2,
        )

        self.assertEqual(
            summary["pending"],
            1,
        )

        self.assertEqual(
            summary["fulfilled"],
            1,
        )

        self.assertEqual(
            summary["we_owe_them"],
            1,
        )

        self.assertEqual(
            summary["they_owe_us"],
            1,
        )

    def test_manual_action_is_not_promoted_to_commitment(
        self,
    ):
        message = self.message()

        ActionItem.objects.create(
            user=self.user,
            organization=(
                self.organization
            ),
            message=message,
            title="Internal manual task",
            owner=self.user,
            source_type="manual",
            status="open",
            confidence_score=100,
        )

        payload = (
            CommitmentsService
            .build_payload(
                organization=(
                    self.organization
                )
            )
        )

        self.assertEqual(
            payload["items"],
            [],
        )

        self.assertEqual(
            payload["summary"]["total"],
            0,
        )

    def test_payload_preserves_frozen_ledger_fields(
        self,
    ):
        message = self.message(
            body=(
                "Please provide final proposal."
            )
        )

        action = ActionItem.objects.create(
            user=self.user,
            organization=(
                self.organization
            ),
            message=message,
            title="Provide final proposal",
            owner=self.user,
            source_type="email",
            status="open",
            confidence_score=90,
        )

        payload = (
            CommitmentsService
            .build_payload(
                organization=(
                    self.organization
                )
            )
        )

        item = payload[
            "items"
        ][0]

        self.assertEqual(
            item["commitment_id"],
            f"action:{action.id}",
        )

        self.assertEqual(
            item["direction"],
            "WE_OWE_THEM",
        )

        self.assertEqual(
            item["source_object_type"],
            "action",
        )

        self.assertEqual(
            item["status"],
            "pending",
        )

        self.assertIn(
            "evidence",
            item,
        )

        self.assertIn(
            "fulfillment",
            item,
        )

        self.assertIn(
            "original_due_at",
            item,
        )

        self.assertIn(
            "current_due_at",
            item,
        )

    def test_organization_isolation_is_preserved(
        self,
    ):
        message = self.message()

        ActionItem.objects.create(
            user=self.user,
            organization=(
                self.organization
            ),
            message=message,
            title="Tenant commitment",
            owner=self.user,
            source_type="email",
            status="open",
            confidence_score=90,
        )

        payload = (
            CommitmentsService
            .build_payload(
                organization=(
                    self.other_organization
                )
            )
        )

        self.assertEqual(
            payload["items"],
            [],
        )


class CommitmentsAPITests(
    TestCase
):

    def setUp(self):
        self.client = APIClient()

        self.user = (
            User.objects.create_user(
                email=(
                    "commitments-api@oneuch.test"
                ),
                password="pass123",
            )
        )

        self.organization = (
            Organization.objects.create(
                name="Commitments API Org",
                slug="commitments-api-org",
            )
        )

        OrganizationUser.objects.create(
            user=self.user,
            organization=(
                self.organization
            ),
            role="member",
        )

    def test_api_requires_authentication(
        self,
    ):
        response = self.client.get(
            "/api/knowledge/commitments/"
        )

        self.assertEqual(
            response.status_code,
            401,
        )

    def test_api_requires_active_membership(
        self,
    ):
        outsider = (
            User.objects.create_user(
                email=(
                    "commitments-outsider@oneuch.test"
                ),
                password="pass123",
            )
        )

        self.client.force_authenticate(
            user=outsider
        )

        response = self.client.get(
            "/api/knowledge/commitments/"
        )

        self.assertEqual(
            response.status_code,
            403,
        )

    def test_api_rejects_inactive_organization(
        self,
    ):
        self.organization.is_active = False

        self.organization.save(
            update_fields=[
                "is_active"
            ]
        )

        self.client.force_authenticate(
            user=self.user
        )

        response = self.client.get(
            "/api/knowledge/commitments/"
        )

        self.assertEqual(
            response.status_code,
            403,
        )

    def test_api_returns_tenant_scoped_ledger_payload(
        self,
    ):
        conversation = (
            Conversation.objects.create(
                user=self.user,
                organization=(
                    self.organization
                ),
                conversation_key=(
                    "commitments-api-thread"
                ),
                subject="Pricing",
            )
        )

        message = (
            InboxMessage.objects.create(
                user=self.user,
                organization=(
                    self.organization
                ),
                conversation=conversation,
                platform="gmail",
                direction="inbound",
                external_message_id=(
                    "commitments-api-message"
                ),
                sender=(
                    "customer@example.com"
                ),
                recipients=(
                    self.user.email
                ),
                subject="Pricing",
                body=(
                    "Please send revised pricing."
                ),
                received_at=datetime(
                    2026,
                    8,
                    29,
                    9,
                    0,
                    tzinfo=dt_timezone.utc,
                ),
            )
        )

        action = (
            ActionItem.objects.create(
                user=self.user,
                organization=(
                    self.organization
                ),
                message=message,
                title=(
                    "Send revised pricing"
                ),
                owner=self.user,
                source_type="email",
                status="open",
                confidence_score=90,
            )
        )

        self.client.force_authenticate(
            user=self.user
        )

        response = self.client.get(
            "/api/knowledge/commitments/"
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(
            response.data[
                "organization_id"
            ],
            self.organization.id,
        )

        self.assertEqual(
            response.data[
                "summary"
            ][
                "total"
            ],
            1,
        )

        self.assertEqual(
            response.data[
                "items"
            ][0][
                "commitment_id"
            ],
            f"action:{action.id}",
        )

        self.assertEqual(
            response.data[
                "items"
            ][0][
                "direction"
            ],
            "WE_OWE_THEM",
        )
