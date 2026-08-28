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
    UpdateActionAPIView,
)
from inbox.models import (
    Conversation,
    InboxMessage,
    Organization,
)

from knowledge.services.commitment_deadlines import (
    build_commitment_deadline_summary,
)
from knowledge.services.commitment_ledger import (
    CommitmentLedgerService,
)
from knowledge.services.intelligence_evidence_persistence import (
    persist_intelligence_evidence,
)


User = get_user_model()


class CommitmentDeadlineHistoryTests(
    TestCase
):

    def setUp(self):
        self.user = User.objects.create_user(
            email="deadline-owner@test.com",
            password="pass123",
        )

        self.organization = (
            Organization.objects.create(
                name="Deadline History Org",
                slug="deadline-history-org",
            )
        )

        self.conversation = (
            Conversation.objects.create(
                user=self.user,
                organization=self.organization,
                conversation_key=(
                    "deadline-history-thread"
                ),
                subject="Deadline",
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
        sender="customer@example.com",
    ):
        self.counter += 1

        return InboxMessage.objects.create(
            user=self.user,
            organization=self.organization,
            conversation=self.conversation,
            platform="gmail",
            direction="inbound",
            external_message_id=(
                "deadline-history-"
                f"{self.counter}"
            ),
            sender=sender,
            recipients=self.user.email,
            subject="Deadline",
            body=body,
            received_at=datetime(
                2026,
                8,
                28,
                6,
                self.counter,
                tzinfo=dt_timezone.utc,
            ),
        )

    def test_initial_action_deadline_becomes_original(
        self,
    ):
        due_at = datetime(
            2026,
            8,
            29,
            6,
            0,
            tzinfo=dt_timezone.utc,
        )

        msg = self.message(
            body=(
                "Please send revised pricing "
                "tomorrow."
            )
        )

        action = ActionItem.objects.create(
            user=self.user,
            organization=self.organization,
            message=msg,
            title="Send revised pricing",
            source_type="email",
            due_date=due_at,
            confidence_score=80,
        )

        persist_intelligence_evidence(
            action,
            evidence_text=(
                "Please send revised pricing "
                "tomorrow."
            ),
            extraction_method=(
                "deterministic"
            ),
            processing_mode=(
                "deterministic"
            ),
            confidence=80,
        )

        summary = (
            build_commitment_deadline_summary(
                action
            )
        )

        self.assertEqual(
            summary.original_due_at,
            due_at,
        )

        self.assertEqual(
            summary.current_due_at,
            due_at,
        )

        self.assertEqual(
            summary.change_count,
            0,
        )

    def test_manual_action_deadline_change_preserves_original(
        self,
    ):
        original_due = datetime(
            2026,
            8,
            29,
            6,
            0,
            tzinfo=dt_timezone.utc,
        )

        revised_due = datetime(
            2026,
            9,
            2,
            6,
            0,
            tzinfo=dt_timezone.utc,
        )

        msg = self.message(
            body=(
                "Please send revised pricing "
                "tomorrow."
            )
        )

        action = ActionItem.objects.create(
            user=self.user,
            organization=self.organization,
            message=msg,
            title="Send revised pricing",
            owner=self.user,
            source_type="email",
            due_date=original_due,
            confidence_score=80,
        )

        persist_intelligence_evidence(
            action,
            evidence_text=(
                "Please send revised pricing "
                "tomorrow."
            ),
            extraction_method=(
                "deterministic"
            ),
            processing_mode=(
                "deterministic"
            ),
            confidence=80,
        )

        request = self.factory.post(
            "/actions/update/",
            {
                "assigned_to": None,
                "due_date":
                    revised_due.isoformat(),
            },
            format="json",
        )

        force_authenticate(
            request,
            user=self.user,
        )

        response = (
            UpdateActionAPIView
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

        summary = (
            build_commitment_deadline_summary(
                action
            )
        )

        self.assertEqual(
            summary.original_due_at,
            original_due,
        )

        self.assertEqual(
            summary.current_due_at,
            revised_due,
        )

        self.assertEqual(
            summary.change_count,
            1,
        )

        entry = (
            CommitmentLedgerService.build(
                organization=(
                    self.organization
                )
            )[0]
        )

        self.assertEqual(
            entry.original_due_at,
            original_due,
        )

        self.assertEqual(
            entry.current_due_at,
            revised_due,
        )

        self.assertEqual(
            entry.deadline_change_count,
            1,
        )

    def test_same_deadline_does_not_create_false_change(
        self,
    ):
        due_at = datetime(
            2026,
            8,
            30,
            6,
            0,
            tzinfo=dt_timezone.utc,
        )

        msg = self.message(
            body="Please send quotation."
        )

        action = ActionItem.objects.create(
            user=self.user,
            organization=self.organization,
            message=msg,
            title="Send quotation",
            source_type="email",
            due_date=due_at,
            confidence_score=80,
        )

        for _ in range(2):
            persist_intelligence_evidence(
                action,
                evidence_text=(
                    "Please send quotation."
                ),
                extraction_method=(
                    "deterministic"
                ),
                processing_mode=(
                    "deterministic"
                ),
                confidence=80,
            )

        summary = (
            build_commitment_deadline_summary(
                action
            )
        )

        self.assertEqual(
            summary.change_count,
            0,
        )

        self.assertEqual(
            len(summary.history),
            1,
        )

    def test_expected_response_source_change_preserves_original_deadline(
        self,
    ):
        original_due = datetime(
            2026,
            8,
            29,
            0,
            0,
            tzinfo=dt_timezone.utc,
        )

        revised_due = datetime(
            2026,
            8,
            31,
            0,
            0,
            tzinfo=dt_timezone.utc,
        )

        first = self.message(
            sender="vendor@example.com",
            body=(
                "Vendor will confirm tomorrow."
            ),
        )

        item = (
            ExpectedResponseItem
            .objects.create(
                user=self.user,
                organization=self.organization,
                conversation=self.conversation,
                source_message=first,
                evidence_text=(
                    "Vendor will confirm tomorrow."
                ),
                response_due_at=(
                    original_due
                ),
                status="waiting",
            )
        )

        persist_intelligence_evidence(
            item,
            evidence_text=(
                "Vendor will confirm tomorrow."
            ),
            extraction_method=(
                "deterministic"
            ),
            processing_mode=(
                "deterministic"
            ),
            confidence=100,
        )

        second = self.message(
            sender="vendor@example.com",
            body=(
                "Vendor will confirm by Monday."
            ),
        )

        item.source_message = second
        item.evidence_text = (
            "Vendor will confirm by Monday."
        )
        item.response_due_at = (
            revised_due
        )

        item.save(
            update_fields=[
                "source_message",
                "evidence_text",
                "response_due_at",
                "updated_at",
            ]
        )

        persist_intelligence_evidence(
            item,
            evidence_text=(
                "Vendor will confirm by Monday."
            ),
            extraction_method=(
                "deterministic"
            ),
            processing_mode=(
                "deterministic"
            ),
            confidence=100,
        )

        summary = (
            build_commitment_deadline_summary(
                item
            )
        )

        self.assertEqual(
            summary.original_due_at,
            original_due,
        )

        self.assertEqual(
            summary.current_due_at,
            revised_due,
        )

        self.assertEqual(
            summary.change_count,
            1,
        )

        entry = (
            CommitmentLedgerService.build(
                organization=(
                    self.organization
                )
            )[0]
        )

        self.assertEqual(
            entry.direction,
            "THEY_OWE_US",
        )

        self.assertEqual(
            entry.original_due_at,
            original_due,
        )

        self.assertEqual(
            entry.current_due_at,
            revised_due,
        )

        self.assertEqual(
            entry.deadline_change_count,
            1,
        )

        self.assertEqual(
            entry.evidence[
                "evidence_text"
            ],
            (
                "Vendor will confirm by Monday."
            ),
        )
