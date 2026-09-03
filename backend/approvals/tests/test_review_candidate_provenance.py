from datetime import (
    datetime,
    timezone as dt_timezone,
)

from django.contrib.auth import (
    get_user_model,
)
from django.test import TestCase
from rest_framework.test import APIClient

from approvals.models import (
    ApprovalItem,
    AIApprovalCandidate,
    ApprovalReviewCandidateOccurrence,
)
from approvals.tasks import (
    _create_review_candidate,
)
from inbox.models import (
    Conversation,
    InboxMessage,
    Organization,
    OrganizationUser,
)
from knowledge.models import (
    KnowledgeEvidence,
)


User = get_user_model()


class ApprovalReviewCandidateProvenanceTests(
    TestCase
):

    def setUp(self):
        self.user = User.objects.create_user(
            email="approval-review-foundation@test.com",
            password="pass123",
        )

        self.organization = (
            Organization.objects.create(
                name="Approval Review Foundation",
                slug="approval-review-foundation",
            )
        )

        OrganizationUser.objects.create(
            user=self.user,
            organization=self.organization,
            role="owner",
        )

        self.client = APIClient()

        self.client.force_authenticate(
            user=self.user
        )

        self.item = {
            "title":
                "Approve annual renewal",
            "description":
                "Authorize annual renewal.",
            "priority":
                90,
            "confidence_score":
                95,
            "evidence":
                "Please approve the annual renewal.",
            "reason":
                "Explicit authorization request.",
        }

    def create_message(
        self,
        *,
        external_id,
        sender,
        minute,
        conversation=None,
    ):
        return InboxMessage.objects.create(
            user=self.user,
            organization=self.organization,
            platform="gmail",
            direction="inbound",
            conversation=conversation,
            external_message_id=external_id,
            sender=sender,
            recipients=self.user.email,
            subject="Annual renewal",
            body=(
                "Please approve the annual renewal."
            ),
            received_at=datetime(
                2026,
                9,
                3,
                11,
                minute,
                tzinfo=dt_timezone.utc,
            ),
        )

    def test_same_domain_same_request_is_one_candidate_with_history(
        self,
    ):
        first = self.create_message(
            external_id="approval-domain-1",
            sender="one@vendor-a.com",
            minute=1,
        )

        second = self.create_message(
            external_id="approval-domain-2",
            sender="two@vendor-a.com",
            minute=2,
        )

        first_candidate, first_created = (
            _create_review_candidate(
                msg=first,
                item=self.item,
                extraction_method=(
                    "deterministic"
                ),
            )
        )

        second_candidate, second_created = (
            _create_review_candidate(
                msg=second,
                item=self.item,
                extraction_method=(
                    "deterministic"
                ),
            )
        )

        self.assertTrue(
            first_created
        )

        self.assertFalse(
            second_created
        )

        self.assertEqual(
            first_candidate.id,
            second_candidate.id,
        )

        first_candidate.refresh_from_db()

        self.assertEqual(
            AIApprovalCandidate.objects.count(),
            1,
        )

        self.assertEqual(
            first_candidate.source_domain,
            "vendor-a.com",
        )

        self.assertEqual(
            first_candidate.occurrence_count,
            2,
        )

        self.assertEqual(
            ApprovalReviewCandidateOccurrence
            .objects
            .filter(
                candidate=first_candidate
            )
            .count(),
            2,
        )

    def test_same_request_different_domain_is_separate_candidate(
        self,
    ):
        first = self.create_message(
            external_id="approval-different-1",
            sender="person@vendor-a.com",
            minute=3,
        )

        second = self.create_message(
            external_id="approval-different-2",
            sender="person@vendor-b.com",
            minute=4,
        )

        _create_review_candidate(
            msg=first,
            item=self.item,
            extraction_method="deterministic",
        )

        _create_review_candidate(
            msg=second,
            item=self.item,
            extraction_method="deterministic",
        )

        self.assertEqual(
            AIApprovalCandidate.objects.count(),
            2,
        )

    def test_neutral_review_api_exposes_provenance_and_history(
        self,
    ):
        first = self.create_message(
            external_id="approval-neutral-1",
            sender="one@vendor-a.com",
            minute=5,
        )

        second = self.create_message(
            external_id="approval-neutral-2",
            sender="two@vendor-a.com",
            minute=6,
        )

        candidate, _ = (
            _create_review_candidate(
                msg=first,
                item=self.item,
                extraction_method="deterministic",
            )
        )

        _create_review_candidate(
            msg=second,
            item=self.item,
            extraction_method="deterministic",
        )

        response = self.client.get(
            "/api/approvals/review-candidates/"
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(
            len(response.data),
            1,
        )

        payload = response.data[0]

        self.assertEqual(
            payload["id"],
            candidate.id,
        )

        self.assertEqual(
            payload["extraction_method"],
            "deterministic",
        )

        self.assertEqual(
            payload["source_domain"],
            "vendor-a.com",
        )

        self.assertEqual(
            payload["occurrence_count"],
            2,
        )

        self.assertEqual(
            len(payload["history"]),
            2,
        )

    def test_deterministic_candidate_promotes_as_email_provenance(
        self,
    ):
        message = self.create_message(
            external_id="approval-promote-1",
            sender="person@vendor-a.com",
            minute=7,
        )

        candidate, _ = (
            _create_review_candidate(
                msg=message,
                item=self.item,
                extraction_method="deterministic",
            )
        )

        response = self.client.post(
            (
                "/api/approvals/review-candidates/"
                f"{candidate.id}/promote/"
            ),
            {},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        approval = ApprovalItem.objects.get()

        self.assertEqual(
            approval.source_type,
            "email",
        )

        evidence = KnowledgeEvidence.objects.get()

        self.assertEqual(
            evidence.metadata.get(
                "extraction_method"
            ),
            "deterministic",
        )

        self.assertEqual(
            evidence.metadata.get(
                "processing_mode"
            ),
            "deterministic",
        )


    def test_same_domain_same_request_across_methods_is_one_candidate(
        self,
    ):
        first = self.create_message(
            external_id="cross-method-approval-1",
            sender="one@vendor-a.com",
            minute=8,
        )

        second = self.create_message(
            external_id="cross-method-approval-2",
            sender="two@vendor-a.com",
            minute=9,
        )

        candidate, created = (
            _create_review_candidate(
                msg=first,
                item=self.item,
                extraction_method="deterministic",
            )
        )

        duplicate, duplicate_created = (
            _create_review_candidate(
                msg=second,
                item=self.item,
                extraction_method="ai",
            )
        )

        self.assertTrue(
            created
        )

        self.assertFalse(
            duplicate_created
        )

        self.assertEqual(
            candidate.id,
            duplicate.id,
        )

        candidate.refresh_from_db()

        self.assertEqual(
            candidate.extraction_method,
            "deterministic",
        )

        self.assertEqual(
            candidate.occurrence_count,
            2,
        )

        methods = set(
            candidate.occurrences.values_list(
                "extraction_method",
                flat=True,
            )
        )

        self.assertEqual(
            methods,
            {
                "deterministic",
                "ai",
            },
        )

    def test_shared_mail_domain_different_senders_are_not_merged(
        self,
    ):
        first = self.create_message(
            external_id="public-domain-approval-1",
            sender="alice@gmail.com",
            minute=10,
        )

        second = self.create_message(
            external_id="public-domain-approval-2",
            sender="bob@gmail.com",
            minute=11,
        )

        _create_review_candidate(
            msg=first,
            item=self.item,
            extraction_method="deterministic",
        )

        _create_review_candidate(
            msg=second,
            item=self.item,
            extraction_method="deterministic",
        )

        self.assertEqual(
            AIApprovalCandidate.objects.count(),
            2,
        )


    def test_promoted_same_conversation_repeat_stays_history_only(
        self,
    ):
        conversation = Conversation.objects.create(
            user=self.user,
            organization=self.organization,
            subject="Recurring approval request",
            conversation_key=(
                "pr3d7c-approval-same-conversation"
            ),
        )

        first = self.create_message(
            external_id="approval-cycle-same-1",
            sender="one@vendor-a.com",
            minute=12,
            conversation=conversation,
        )

        candidate, _ = (
            _create_review_candidate(
                msg=first,
                item=self.item,
                extraction_method="deterministic",
            )
        )

        response = self.client.post(
            (
                "/api/approvals/review-candidates/"
                f"{candidate.id}/promote/"
            ),
            {},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        candidate.refresh_from_db()

        self.assertEqual(
            candidate.status,
            "promoted",
        )

        second = self.create_message(
            external_id="approval-cycle-same-2",
            sender="two@vendor-a.com",
            minute=13,
            conversation=conversation,
        )

        repeated, created = (
            _create_review_candidate(
                msg=second,
                item=self.item,
                extraction_method="deterministic",
            )
        )

        self.assertFalse(
            created
        )

        self.assertEqual(
            repeated.id,
            candidate.id,
        )

        repeated.refresh_from_db()

        self.assertEqual(
            repeated.status,
            "promoted",
        )

        self.assertEqual(
            repeated.occurrence_count,
            2,
        )

        self.assertEqual(
            AIApprovalCandidate.objects.count(),
            1,
        )

        pending = self.client.get(
            "/api/approvals/review-candidates/"
        )

        self.assertEqual(
            len(pending.data),
            0,
        )

        history = self.client.get(
            (
                "/api/approvals/review-candidates/"
                "?scope=history"
            )
        )

        self.assertEqual(
            history.status_code,
            200,
        )

        self.assertEqual(
            len(history.data),
            1,
        )

        payload = history.data[0]

        self.assertEqual(
            payload["status"],
            "promoted",
        )

        self.assertTrue(
            payload[
                "post_decision_recurrence"
            ]
        )

        self.assertEqual(
            payload["occurrence_count"],
            2,
        )

        self.assertEqual(
            len(payload["history"]),
            2,
        )

    def test_promoted_new_conversation_starts_new_review_cycle(
        self,
    ):
        first_conversation = (
            Conversation.objects.create(
                user=self.user,
                organization=self.organization,
                subject="Old approval cycle",
                conversation_key=(
                    "pr3d7c-approval-cycle-old"
                ),
            )
        )

        second_conversation = (
            Conversation.objects.create(
                user=self.user,
                organization=self.organization,
                subject="New approval cycle",
                conversation_key=(
                    "pr3d7c-approval-cycle-new"
                ),
            )
        )

        first = self.create_message(
            external_id="approval-new-cycle-1",
            sender="one@vendor-a.com",
            minute=14,
            conversation=first_conversation,
        )

        old_candidate, _ = (
            _create_review_candidate(
                msg=first,
                item=self.item,
                extraction_method="deterministic",
            )
        )

        promote = self.client.post(
            (
                "/api/approvals/review-candidates/"
                f"{old_candidate.id}/promote/"
            ),
            {},
            format="json",
        )

        self.assertEqual(
            promote.status_code,
            200,
        )

        second = self.create_message(
            external_id="approval-new-cycle-2",
            sender="two@vendor-a.com",
            minute=15,
            conversation=second_conversation,
        )

        new_candidate, created = (
            _create_review_candidate(
                msg=second,
                item=self.item,
                extraction_method="deterministic",
            )
        )

        self.assertTrue(
            created
        )

        self.assertNotEqual(
            new_candidate.id,
            old_candidate.id,
        )

        self.assertEqual(
            new_candidate.status,
            "pending_review",
        )

        self.assertEqual(
            AIApprovalCandidate.objects.count(),
            2,
        )

        pending = self.client.get(
            "/api/approvals/review-candidates/"
        )

        self.assertEqual(
            len(pending.data),
            1,
        )

        self.assertEqual(
            pending.data[0]["id"],
            new_candidate.id,
        )

        history = self.client.get(
            (
                "/api/approvals/review-candidates/"
                "?scope=history"
            )
        )

        self.assertEqual(
            len(history.data),
            1,
        )

        self.assertEqual(
            history.data[0]["id"],
            old_candidate.id,
        )
