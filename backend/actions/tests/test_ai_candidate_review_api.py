from datetime import (
    datetime,
    timezone as dt_timezone,
)

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from actions.models import (
    ActionItem,
    AIActionCandidate,
)
from inbox.models import (
    InboxMessage,
    Organization,
    OrganizationUser,
)
from knowledge.models import KnowledgeEvidence


User = get_user_model()


class AIActionCandidateReviewAPITests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            email="review-action@test.com",
            password="pass123",
        )

        self.organization = Organization.objects.create(
            name="Review Action Org",
            slug="review-action-org",
        )

        OrganizationUser.objects.create(
            user=self.user,
            organization=self.organization,
            role="owner",
        )

        self.message = InboxMessage.objects.create(
            user=self.user,
            organization=self.organization,
            platform="gmail",
            direction="inbound",
            external_message_id="review-action-message-1",
            sender="customer@example.com",
            recipients=self.user.email,
            subject="Deployment blocker",
            body=(
                "Please coordinate internally "
                "and resolve this blocker."
            ),
            received_at=datetime(
                2026,
                9,
                1,
                10,
                0,
                tzinfo=dt_timezone.utc,
            ),
        )

        self.candidate = AIActionCandidate.objects.create(
            user=self.user,
            organization=self.organization,
            message=self.message,
            title="Resolve deployment blocker",
            description=(
                "Coordinate internally and "
                "resolve the blocker."
            ),
            confidence_score=82,
            priority=80,
            evidence=(
                "Please coordinate internally "
                "and resolve this blocker."
            ),
            reason="Concrete work is requested.",
            provider="openai",
            model="gpt-5.6-luna",
        )

        self.client = APIClient()
        self.client.force_authenticate(
            user=self.user
        )

    def test_pending_candidate_list_is_tenant_scoped(self):
        response = self.client.get(
            "/api/actions/ai-candidates/"
        )

        self.assertEqual(
            response.status_code,
            200,
        )
        self.assertEqual(
            len(response.data),
            1,
        )
        self.assertEqual(
            response.data[0]["id"],
            self.candidate.id,
        )
        self.assertEqual(
            response.data[0]["status"],
            "pending_review",
        )

    def test_promote_candidate_creates_action_and_evidence(self):
        response = self.client.post(
            (
                "/api/actions/ai-candidates/"
                f"{self.candidate.id}/promote/"
            ),
            {},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.candidate.refresh_from_db()

        self.assertEqual(
            self.candidate.status,
            "promoted",
        )
        self.assertEqual(
            ActionItem.objects.count(),
            1,
        )

        action = ActionItem.objects.get()

        self.assertEqual(
            action.source_type,
            "ai",
        )
        self.assertEqual(
            action.message,
            self.message,
        )

        evidence = KnowledgeEvidence.objects.get()

        self.assertEqual(
            evidence.message,
            self.message,
        )
        self.assertEqual(
            evidence.metadata.get(
                "extraction_method"
            ),
            "ai",
        )
        self.assertEqual(
            evidence.metadata.get(
                "processing_mode"
            ),
            "unknown",
        )

    def test_repeated_promote_is_idempotent(self):
        path = (
            "/api/actions/ai-candidates/"
            f"{self.candidate.id}/promote/"
        )

        first = self.client.post(
            path,
            {},
            format="json",
        )
        second = self.client.post(
            path,
            {},
            format="json",
        )

        self.assertEqual(
            first.status_code,
            200,
        )
        self.assertEqual(
            second.status_code,
            200,
        )
        self.assertEqual(
            ActionItem.objects.count(),
            1,
        )
        self.assertEqual(
            KnowledgeEvidence.objects.count(),
            1,
        )

    def test_reject_candidate_creates_no_action(self):
        response = self.client.post(
            (
                "/api/actions/ai-candidates/"
                f"{self.candidate.id}/reject/"
            ),
            {},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.candidate.refresh_from_db()

        self.assertEqual(
            self.candidate.status,
            "rejected",
        )
        self.assertEqual(
            ActionItem.objects.count(),
            0,
        )
        self.assertEqual(
            KnowledgeEvidence.objects.count(),
            0,
        )

    def test_rejected_candidate_cannot_be_promoted(self):
        self.candidate.status = "rejected"
        self.candidate.save(
            update_fields=[
                "status",
                "updated_at",
            ]
        )

        response = self.client.post(
            (
                "/api/actions/ai-candidates/"
                f"{self.candidate.id}/promote/"
            ),
            {},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            409,
        )
        self.assertEqual(
            ActionItem.objects.count(),
            0,
        )

    def test_cross_tenant_candidate_returns_404(self):
        other_user = User.objects.create_user(
            email="other-action@test.com",
            password="pass123",
        )
        other_org = Organization.objects.create(
            name="Other Action Org",
            slug="other-action-org",
        )
        OrganizationUser.objects.create(
            user=other_user,
            organization=other_org,
            role="owner",
        )
        other_message = InboxMessage.objects.create(
            user=other_user,
            organization=other_org,
            platform="gmail",
            direction="inbound",
            external_message_id="other-action-message",
            sender="outside@example.com",
            recipients=other_user.email,
            subject="Other",
            body="Please resolve this.",
            received_at=datetime(
                2026,
                9,
                1,
                11,
                0,
                tzinfo=dt_timezone.utc,
            ),
        )
        other_candidate = AIActionCandidate.objects.create(
            user=other_user,
            organization=other_org,
            message=other_message,
            title="Other candidate",
            confidence_score=80,
            evidence="Please resolve this.",
        )

        response = self.client.post(
            (
                "/api/actions/ai-candidates/"
                f"{other_candidate.id}/promote/"
            ),
            {},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            404,
        )
        self.assertEqual(
            ActionItem.objects.count(),
            0,
        )
