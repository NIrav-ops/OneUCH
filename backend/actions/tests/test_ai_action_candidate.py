from datetime import datetime
from datetime import timezone as dt_timezone

from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.test import TestCase

from actions.models import AIActionCandidate
from inbox.models import InboxMessage
from inbox.models import Organization


User = get_user_model()


class AIActionCandidateTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            email="ai-candidate@test.com",
            password="pass123",
        )

        self.organization = Organization.objects.create(
            name="AI Candidate Test",
            slug="ai-candidate-test",
        )

        self.message = InboxMessage.objects.create(
            user=self.user,
            organization=self.organization,
            platform="gmail",
            direction="inbound",
            external_message_id="ai-candidate-001",
            sender="customer@example.com",
            recipients=self.user.email,
            subject="Deployment blocker",
            body=(
                "Can you coordinate internally "
                "and get this sorted?"
            ),
            received_at=datetime(
                2026,
                8,
                25,
                5,
                0,
                tzinfo=dt_timezone.utc,
            ),
            action_analyzed=False,
        )

    def test_candidate_can_be_persisted(
        self,
    ):
        candidate = (
            AIActionCandidate.objects.create(
                user=self.user,
                organization=self.organization,
                message=self.message,
                title=(
                    "Resolve deployment blocker"
                ),
                description=(
                    "Coordinate internally and "
                    "resolve the blocker."
                ),
                owner_reference="",
                priority=80,
                confidence_score=82,
                evidence=(
                    "coordinate internally "
                    "and get this sorted"
                ),
                reason=(
                    "The message requests "
                    "concrete work."
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
            82,
        )

        self.assertEqual(
            candidate.message,
            self.message,
        )

    def test_same_message_and_title_is_unique(
        self,
    ):
        defaults = {
            "user": self.user,
            "organization": self.organization,
            "message": self.message,
            "title": (
                "Resolve deployment blocker"
            ),
            "confidence_score": 82,
        }

        AIActionCandidate.objects.create(
            **defaults
        )

        with self.assertRaises(
            IntegrityError
        ):
            AIActionCandidate.objects.create(
                **defaults
            )
