from datetime import (
    datetime,
    timezone as dt_timezone,
)

from django.contrib.auth import (
    get_user_model,
)
from django.test import TestCase

from approvals.models import (
    ApprovalItem,
    AIApprovalCandidate,
)
from approvals.tasks import analyze_new_approvals
from inbox.models import (
    InboxMessage,
    Organization,
)


User = get_user_model()


class ApprovalAnalysisTaskTests(
    TestCase
):

    def setUp(self):
        self.user = User.objects.create_user(
            email="approval-task@test.com",
            password="pass123",
        )

        self.organization = (
            Organization.objects.create(
                name="Approval Task Test",
                slug="approval-task-test",
            )
        )

    def create_message(
        self,
        *,
        external_message_id,
        subject="",
        body="",
        direction="inbound",
        is_draft=False,
        approval_analyzed=False,
    ):
        return InboxMessage.objects.create(
            user=self.user,
            organization=self.organization,
            platform="gmail",
            direction=direction,
            external_message_id=(
                external_message_id
            ),
            sender="customer@example.com",
            recipients=self.user.email,
            subject=subject,
            body=body,
            received_at=datetime(
                2026,
                8,
                25,
                5,
                0,
                tzinfo=dt_timezone.utc,
            ),
            is_draft=is_draft,
            approval_analyzed=(
                approval_analyzed
            ),
        )

    def test_inbound_approval_is_routed_to_review(
        self,
    ):
        message = self.create_message(
            external_message_id=(
                "approval-worker-001"
            ),
            subject="Proposal approval",
            body=(
                "Please approve the attached "
                "commercial proposal."
            ),
        )

        processed = (
            analyze_new_approvals.run(
                message_ids=[
                    message.id
                ]
            )
        )

        self.assertEqual(
            processed,
            1,
        )

        self.assertFalse(
            ApprovalItem.objects.filter(
                message=message,
            ).exists()
        )

        candidate = AIApprovalCandidate.objects.get(
            message=message,
        )

        self.assertEqual(
            candidate.title,
            "Approval Required",
        )

        self.assertEqual(
            candidate.priority,
            90,
        )

        self.assertEqual(
            candidate.confidence_score,
            85,
        )

        self.assertEqual(
            candidate.extraction_method,
            "deterministic",
        )

        self.assertEqual(
            candidate.status,
            "pending_review",
        )

        self.assertIsNone(
            candidate.due_date
        )

        message.refresh_from_db()

        self.assertTrue(
            message.approval_analyzed
        )

    def test_outbound_message_is_not_analyzed(
        self,
    ):
        message = self.create_message(
            external_message_id=(
                "approval-outbound-001"
            ),
            body=(
                "Please approve the proposal."
            ),
            direction="outbound",
        )

        processed = (
            analyze_new_approvals.run(
                message_ids=[
                    message.id
                ]
            )
        )

        self.assertEqual(
            processed,
            0,
        )

        self.assertFalse(
            ApprovalItem.objects.filter(
                message=message,
            ).exists()
        )

        message.refresh_from_db()

        self.assertFalse(
            message.approval_analyzed
        )

    def test_draft_message_is_not_analyzed(
        self,
    ):
        message = self.create_message(
            external_message_id=(
                "approval-draft-001"
            ),
            body=(
                "Please approve the proposal."
            ),
            is_draft=True,
        )

        processed = (
            analyze_new_approvals.run(
                message_ids=[
                    message.id
                ]
            )
        )

        self.assertEqual(
            processed,
            0,
        )

        self.assertFalse(
            ApprovalItem.objects.filter(
                message=message,
            ).exists()
        )

        message.refresh_from_db()

        self.assertFalse(
            message.approval_analyzed
        )

    def test_targeted_analysis_only_processes_requested_message(
        self,
    ):
        target = self.create_message(
            external_message_id=(
                "approval-target-001"
            ),
            body=(
                "Please approve the proposal."
            ),
        )

        untouched = self.create_message(
            external_message_id=(
                "approval-untouched-001"
            ),
            body=(
                "Please approve the deployment."
            ),
        )

        processed = (
            analyze_new_approvals.run(
                message_ids=[
                    target.id
                ]
            )
        )

        self.assertEqual(
            processed,
            1,
        )

        self.assertFalse(
            ApprovalItem.objects.filter(
                message=target,
            ).exists()
        )

        self.assertTrue(
            AIApprovalCandidate.objects.filter(
                message=target,
                extraction_method="deterministic",
            ).exists()
        )

        self.assertFalse(
            AIApprovalCandidate.objects.filter(
                message=untouched,
            ).exists()
        )

        target.refresh_from_db()
        untouched.refresh_from_db()

        self.assertTrue(
            target.approval_analyzed
        )

        self.assertFalse(
            untouched.approval_analyzed
        )

    def test_reanalysis_does_not_duplicate_review_candidate(
        self,
    ):
        message = self.create_message(
            external_message_id=(
                "approval-dedupe-001"
            ),
            body=(
                "Please approve the proposal."
            ),
        )

        analyze_new_approvals.run(
            message_ids=[
                message.id
            ]
        )

        self.assertEqual(
            ApprovalItem.objects.filter(
                message=message,
            ).count(),
            0,
        )

        self.assertEqual(
            AIApprovalCandidate.objects.filter(
                message=message,
            ).count(),
            1,
        )

        candidate = AIApprovalCandidate.objects.get(
            message=message,
        )

        self.assertEqual(
            candidate.occurrence_count,
            1,
        )

        message.approval_analyzed = False

        message.save(
            update_fields=[
                "approval_analyzed"
            ]
        )

        analyze_new_approvals.run(
            message_ids=[
                message.id
            ]
        )

        self.assertEqual(
            ApprovalItem.objects.filter(
                message=message,
            ).count(),
            0,
        )

        self.assertEqual(
            AIApprovalCandidate.objects.filter(
                message=message,
            ).count(),
            1,
        )

        candidate.refresh_from_db()

        self.assertEqual(
            candidate.occurrence_count,
            1,
        )

    def test_non_approval_is_marked_analyzed(
        self,
    ):
        message = self.create_message(
            external_message_id=(
                "approval-none-001"
            ),
            subject="FYI",
            body=(
                "Sharing the deployment update "
                "for your information."
            ),
        )

        processed = (
            analyze_new_approvals.run(
                message_ids=[
                    message.id
                ]
            )
        )

        self.assertEqual(
            processed,
            1,
        )

        self.assertFalse(
            ApprovalItem.objects.filter(
                message=message,
            ).exists()
        )

        message.refresh_from_db()

        self.assertTrue(
            message.approval_analyzed
        )

    def test_completed_approval_does_not_create_new_approval(
        self,
    ):
        message = self.create_message(
            external_message_id=(
                "approval-completed-001"
            ),
            body=(
                "The approval was completed "
                "yesterday."
            ),
        )

        processed = (
            analyze_new_approvals.run(
                message_ids=[
                    message.id
                ]
            )
        )

        self.assertEqual(
            processed,
            1,
        )

        self.assertFalse(
            ApprovalItem.objects.filter(
                message=message,
            ).exists()
        )

        message.refresh_from_db()

        self.assertTrue(
            message.approval_analyzed
        )
