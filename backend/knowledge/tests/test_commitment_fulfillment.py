from datetime import (
    datetime,
    timezone as dt_timezone,
)

from django.contrib.auth import (
    get_user_model,
)
from django.test import TestCase

from rest_framework.test import (
    APIRequestFactory,
    force_authenticate,
)

from actions.models import (
    ActionItem,
    ExpectedResponseItem,
)
from actions.views import (
    CompleteActionAPIView,
    ReopenActionAPIView,
    UpdateActionStatusAPIView,
)
from inbox.models import (
    Conversation,
    InboxMessage,
    Organization,
)
from knowledge.services.commitment_fulfillment import (
    build_action_fulfillment,
    build_expected_response_fulfillment,
)
from knowledge.services.commitment_ledger import (
    CommitmentLedgerService,
)
from timeline.models import (
    TimelineEvent,
)


User = get_user_model()


class CommitmentFulfillmentTests(
    TestCase
):

    def setUp(self):
        self.user = User.objects.create_user(
            email="fulfillment-owner@test.com",
            password="pass123",
        )

        self.organization = (
            Organization.objects.create(
                name="Fulfillment Org",
                slug="fulfillment-org",
            )
        )

        self.conversation = (
            Conversation.objects.create(
                user=self.user,
                organization=self.organization,
                conversation_key=(
                    "fulfillment-thread"
                ),
                subject="Fulfillment",
            )
        )

        self.factory = (
            APIRequestFactory()
        )

        self.counter = 0

    def message(
        self,
        *,
        body,
        direction="inbound",
        sender=None,
        recipients=None,
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
                else "customer@example.com"
            )

        return InboxMessage.objects.create(
            user=self.user,
            organization=self.organization,
            conversation=self.conversation,
            platform="gmail",
            direction=direction,
            external_message_id=(
                "fulfillment-"
                f"{self.counter}"
            ),
            sender=sender,
            recipients=recipients,
            subject="Fulfillment",
            body=body,
            received_at=datetime(
                2026,
                8,
                28,
                8,
                self.counter,
                tzinfo=dt_timezone.utc,
            ),
        )

    def action(
        self,
    ):
        msg = self.message(
            body=(
                "Please send the revised "
                "quotation tomorrow."
            )
        )

        return ActionItem.objects.create(
            user=self.user,
            organization=self.organization,
            message=msg,
            title="Send revised quotation",
            owner=self.user,
            source_type="email",
            confidence_score=80,
        )

    def test_pending_action_has_no_fulfillment(
        self,
    ):
        action = self.action()

        result = (
            build_action_fulfillment(
                action
            )
        )

        self.assertEqual(
            result.method,
            "none",
        )

        self.assertEqual(
            result.quality,
            "none",
        )

    def test_complete_endpoint_records_manual_attestation(
        self,
    ):
        action = self.action()

        request = self.factory.post(
            "/actions/complete/",
            {},
            format="json",
        )

        force_authenticate(
            request,
            user=self.user,
        )

        response = (
            CompleteActionAPIView
            .as_view()(
                request,
                action_id=action.id,
            )
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        action.refresh_from_db()

        self.assertEqual(
            action.status,
            "completed",
        )

        self.assertIsNotNone(
            action.completed_at
        )

        self.assertEqual(
            TimelineEvent.objects.filter(
                conversation=(
                    self.conversation
                ),
                event_type=(
                    "action_completed"
                ),
            ).count(),
            1,
        )

        result = (
            build_action_fulfillment(
                action
            )
        )

        self.assertEqual(
            result.method,
            "manual_attestation",
        )

        self.assertEqual(
            result.quality,
            "attested",
        )

        self.assertEqual(
            result.actor_user_id,
            self.user.id,
        )

        self.assertEqual(
            result.actor_email,
            self.user.email,
        )

        self.assertIsNone(
            result.source_message_id
        )

        entry = (
            CommitmentLedgerService.build(
                organization=(
                    self.organization
                )
            )[0]
        )

        self.assertEqual(
            entry.fulfillment[
                "method"
            ],
            "manual_attestation",
        )

    def test_complete_endpoint_is_idempotent(
        self,
    ):
        action = self.action()

        for _ in range(2):
            request = self.factory.post(
                "/actions/complete/",
                {},
                format="json",
            )

            force_authenticate(
                request,
                user=self.user,
            )

            CompleteActionAPIView.as_view()(
                request,
                action_id=action.id,
            )

        self.assertEqual(
            TimelineEvent.objects.filter(
                conversation=(
                    self.conversation
                ),
                event_type=(
                    "action_completed"
                ),
            ).count(),
            1,
        )

    def test_status_endpoint_records_same_completion_contract(
        self,
    ):
        action = self.action()

        request = self.factory.post(
            "/actions/status/",
            {
                "status": "completed",
            },
            format="json",
        )

        force_authenticate(
            request,
            user=self.user,
        )

        response = (
            UpdateActionStatusAPIView
            .as_view()(
                request,
                action_id=action.id,
            )
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        action.refresh_from_db()

        result = (
            build_action_fulfillment(
                action
            )
        )

        self.assertEqual(
            result.method,
            "manual_attestation",
        )

        self.assertEqual(
            result.actor_user_id,
            self.user.id,
        )

    def test_reopen_clears_current_fulfillment_state(
        self,
    ):
        action = self.action()

        complete = self.factory.post(
            "/actions/complete/",
            {},
            format="json",
        )

        force_authenticate(
            complete,
            user=self.user,
        )

        CompleteActionAPIView.as_view()(
            complete,
            action_id=action.id,
        )

        reopen = self.factory.post(
            "/actions/reopen/",
            {},
            format="json",
        )

        force_authenticate(
            reopen,
            user=self.user,
        )

        ReopenActionAPIView.as_view()(
            reopen,
            action_id=action.id,
        )

        action.refresh_from_db()

        self.assertEqual(
            action.status,
            "open",
        )

        self.assertIsNone(
            action.completed_at
        )

        result = (
            build_action_fulfillment(
                action
            )
        )

        self.assertEqual(
            result.method,
            "none",
        )

    def test_received_expected_response_has_message_proof(
        self,
    ):
        source = self.message(
            sender="vendor@example.com",
            body=(
                "Vendor will confirm tomorrow."
            ),
        )

        reply = self.message(
            sender="vendor@example.com",
            body=(
                "Here is the confirmation."
            ),
        )

        item = (
            ExpectedResponseItem.objects
            .create(
                user=self.user,
                organization=self.organization,
                conversation=self.conversation,
                source_message=source,
                expected_from=(
                    "vendor@example.com"
                ),
                evidence_text=(
                    "Vendor will confirm tomorrow."
                ),
                status="received",
                resolved_by_message=reply,
                resolved_at=(
                    reply.received_at
                ),
            )
        )

        result = (
            build_expected_response_fulfillment(
                item
            )
        )

        self.assertEqual(
            result.method,
            "message_confirmed",
        )

        self.assertEqual(
            result.quality,
            "message_confirmed",
        )

        self.assertEqual(
            result.source_message_id,
            reply.id,
        )

        self.assertEqual(
            result.evidence_text,
            "Here is the confirmation.",
        )

        entry = (
            CommitmentLedgerService.build(
                organization=(
                    self.organization
                )
            )[0]
        )

        self.assertEqual(
            entry.fulfillment[
                "source_message_id"
            ],
            reply.id,
        )

    def test_quoted_history_is_removed_from_fulfillment_text(
        self,
    ):
        source = self.message(
            sender="vendor@example.com",
            body=(
                "Vendor will confirm tomorrow."
            ),
        )

        reply = self.message(
            sender="vendor@example.com",
            body=(
                "Here is the confirmation.\n\n"
                "On Wed, Aug 26, 2026 at "
                "5:54 PM sender@example.com "
                "wrote:\n"
                "Vendor will confirm tomorrow."
            ),
        )

        item = (
            ExpectedResponseItem.objects
            .create(
                user=self.user,
                organization=self.organization,
                conversation=self.conversation,
                source_message=source,
                evidence_text=(
                    "Vendor will confirm tomorrow."
                ),
                status="received",
                resolved_by_message=reply,
                resolved_at=(
                    reply.received_at
                ),
            )
        )

        result = (
            build_expected_response_fulfillment(
                item
            )
        )

        self.assertEqual(
            result.evidence_text,
            "Here is the confirmation.",
        )

    def test_waiting_expected_response_has_no_fulfillment(
        self,
    ):
        source = self.message(
            sender="vendor@example.com",
            body=(
                "Vendor will confirm tomorrow."
            ),
        )

        item = (
            ExpectedResponseItem.objects
            .create(
                user=self.user,
                organization=self.organization,
                conversation=self.conversation,
                source_message=source,
                evidence_text=(
                    "Vendor will confirm tomorrow."
                ),
                status="waiting",
            )
        )

        result = (
            build_expected_response_fulfillment(
                item
            )
        )

        self.assertEqual(
            result.method,
            "none",
        )
