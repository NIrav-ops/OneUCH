from datetime import (
    datetime,
    timezone as dt_timezone,
)

from django.contrib.auth import (
    get_user_model,
)
from django.db import IntegrityError
from django.test import TestCase

from approvals.models import (
    AIApprovalCandidate,
)
from inbox.models import (
    InboxMessage,
    Organization,
)


User = get_user_model()


class AIApprovalCandidateTests(
    TestCase
):

    def setUp(self):
        self.user = User.objects.create_user(
            email=(
                "approval-candidate@test.com"
            ),
            password="pass123",
        )

        self.organization = (
            Organization.objects.create(
                name=(
                    "Approval Candidate Test"
                ),
                slug=(
                    "approval-candidate-test"
                ),
            )
        )

        self.message = (
            InboxMessage.objects.create(
                user=self.user,
                organization=(
                    self.organization
                ),
                platform="gmail",
                direction="inbound",
                external_message_id=(
                    "approval-ai-candidate-001"
                ),
                sender=(
                    "customer@example.com"
                ),
                recipients=(
                    self.user.email
                ),
                subject=(
                    "Production authorization"
                ),
                body=(
                    "Are you comfortable with us "
                    "moving ahead?"
                ),
                received_at=datetime(
                    2026,
                    8,
                    25,
                    5,
                    0,
                    tzinfo=(
                        dt_timezone.utc
                    ),
                ),
            )
        )

    def test_candidate_is_persisted(
        self,
    ):
        candidate = (
            AIApprovalCandidate.objects.create(
                user=self.user,
                organization=(
                    self.organization
                ),
                message=self.message,
                title=(
                    "Authorize production"
                ),
                description=(
                    "Provide authorization "
                    "to proceed."
                ),
                approver_reference=(
                    "Rakesh"
                ),
                priority=90,
                confidence_score=90,
                evidence=(
                    "Are you comfortable with us "
                    "moving ahead?"
                ),
                reason=(
                    "Authorization is requested."
                ),
                provider="openai",
                model="gpt-5.6-luna",
            )
        )

        self.assertEqual(
            candidate.status,
            "pending_review",
        )

        self.assertEqual(
            candidate.confidence_score,
            90,
        )

        self.assertEqual(
            candidate.approver_reference,
            "Rakesh",
        )

    def test_same_message_and_title_is_unique(
        self,
    ):
        data = {
            "user": self.user,
            "organization":
                self.organization,
            "message": self.message,
            "title":
                "Authorize production",
            "confidence_score": 90,
        }

        AIApprovalCandidate.objects.create(
            **data
        )

        with self.assertRaises(
            IntegrityError
        ):
            AIApprovalCandidate.objects.create(
                **data
            )
