from datetime import (
    datetime,
    timedelta,
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

from approvals.models import (
    ApprovalItem,
)

from inbox.models import (
    Conversation,
    InboxMessage,
    Organization,
    OrganizationUser,
)

from knowledge.services.decisions import (
    DecisionsService,
)

from knowledge.services.intelligence_evidence_persistence import (
    persist_intelligence_evidence,
)


User = get_user_model()


class DecisionsServiceTests(
    TestCase
):

    def setUp(self):
        self.user = (
            User.objects.create_user(
                email=(
                    "decision-owner@oneuch.test"
                ),
                password="pass123",
            )
        )

        self.organization = (
            Organization.objects.create(
                name="Decision Org",
                slug="decision-org",
            )
        )

        self.other_organization = (
            Organization.objects.create(
                name="Other Decision Org",
                slug="other-decision-org",
            )
        )

        self.conversation = (
            Conversation.objects.create(
                user=self.user,
                organization=(
                    self.organization
                ),
                conversation_key=(
                    "decision-thread"
                ),
                subject=(
                    "Decision request"
                ),
            )
        )

        self.other_conversation = (
            Conversation.objects.create(
                user=self.user,
                organization=(
                    self.other_organization
                ),
                conversation_key=(
                    "other-decision-thread"
                ),
                subject="Other decision",
            )
        )

        self.base_time = datetime(
            2026,
            8,
            29,
            10,
            0,
            tzinfo=dt_timezone.utc,
        )

        self.counter = 0

    def message(
        self,
        *,
        organization=None,
        conversation=None,
        body=(
            "Please approve the enterprise renewal."
        ),
    ):
        self.counter += 1

        organization = (
            organization
            or self.organization
        )

        conversation = (
            conversation
            or self.conversation
        )

        return InboxMessage.objects.create(
            user=self.user,
            organization=organization,
            conversation=conversation,
            platform="gmail",
            direction="inbound",
            external_message_id=(
                "decision-message-"
                f"{self.counter}"
            ),
            sender=(
                "requester@example.com"
            ),
            recipients=self.user.email,
            subject="Approval requested",
            body=body,
            received_at=self.base_time,
        )

    def approval(
        self,
        *,
        status="approved",
        decision_at=None,
        notes="",
        organization=None,
        conversation=None,
        message=True,
        source_type="email",
        title="Approve enterprise renewal",
    ):
        organization = (
            organization
            or self.organization
        )

        conversation = (
            conversation
            or self.conversation
        )

        source_message = (
            self.message(
                organization=organization,
                conversation=conversation,
            )
            if message
            else None
        )

        return ApprovalItem.objects.create(
            user=self.user,
            organization=organization,
            message=source_message,
            conversation=conversation,
            title=title,
            description=(
                "Review and decide whether "
                "the renewal may proceed."
            ),
            requested_by=(
                "requester@example.com"
            ),
            assigned_to=self.user,
            status=status,
            source_type=source_type,
            confidence_score=92,
            decision_notes=notes,
            decision_by=(
                self.user
                if status
                in {
                    "approved",
                    "rejected",
                }
                else None
            ),
            decision_at=(
                decision_at
                if status
                in {
                    "approved",
                    "rejected",
                }
                else None
            ),
        )

    def test_approved_and_rejected_are_decisions(
        self,
    ):
        approved = self.approval(
            status="approved",
            decision_at=self.base_time,
            title="Approve renewal",
        )

        rejected = self.approval(
            status="rejected",
            decision_at=(
                self.base_time
                + timedelta(minutes=5)
            ),
            title="Reject exception",
        )

        items = DecisionsService.build(
            organization=(
                self.organization
            )
        )

        self.assertEqual(
            {
                item.approval_id
                for item in items
            },
            {
                approved.id,
                rejected.id,
            },
        )

        self.assertEqual(
            {
                item.outcome
                for item in items
            },
            {
                "approved",
                "rejected",
            },
        )

    def test_non_final_approval_states_are_excluded(
        self,
    ):
        self.approval(
            status="pending",
            title="Pending",
        )

        self.approval(
            status="needs_info",
            title="Needs Info",
        )

        self.approval(
            status="ignored",
            title="Ignored",
        )

        items = DecisionsService.build(
            organization=(
                self.organization
            )
        )

        self.assertEqual(
            items,
            [],
        )

    def test_decision_metadata_is_preserved(
        self,
    ):
        decision_at = (
            self.base_time
            + timedelta(hours=1)
        )

        approval = self.approval(
            status="approved",
            decision_at=decision_at,
            notes=(
                "Approved within the "
                "agreed commercial ceiling."
            ),
        )

        item = DecisionsService.build(
            organization=(
                self.organization
            )
        )[0]

        self.assertEqual(
            item.approval_id,
            approval.id,
        )

        self.assertEqual(
            item.decision_by_id,
            self.user.id,
        )

        self.assertEqual(
            item.decision_by_email,
            self.user.email,
        )

        self.assertEqual(
            item.decision_at,
            decision_at,
        )

        self.assertEqual(
            item.decision_notes,
            (
                "Approved within the "
                "agreed commercial ceiling."
            ),
        )

        self.assertEqual(
            item.requested_by,
            "requester@example.com",
        )

    def test_exact_request_evidence_is_reused(
        self,
    ):
        approval = self.approval(
            status="approved",
            decision_at=self.base_time,
        )

        evidence_text = (
            "Please approve the enterprise renewal."
        )

        persist_intelligence_evidence(
            approval,
            evidence_text=evidence_text,
            extraction_method=(
                "deterministic"
            ),
            processing_mode=(
                "deterministic"
            ),
            confidence=92,
        )

        item = DecisionsService.build(
            organization=(
                self.organization
            )
        )[0]

        self.assertEqual(
            item.request_evidence[
                "evidence_quality"
            ],
            "exact",
        )

        self.assertEqual(
            item.request_evidence[
                "evidence_text"
            ],
            evidence_text,
        )

        self.assertEqual(
            item.request_evidence[
                "object_type"
            ],
            "approval",
        )

    def test_manual_decision_without_message_is_truthful(
        self,
    ):
        approval = self.approval(
            status="rejected",
            decision_at=self.base_time,
            message=False,
            source_type="manual",
        )

        item = DecisionsService.build(
            organization=(
                self.organization
            )
        )[0]

        self.assertEqual(
            item.approval_id,
            approval.id,
        )

        self.assertIsNone(
            item.source_message_id
        )

        self.assertEqual(
            item.request_evidence[
                "evidence_quality"
            ],
            "none",
        )

        self.assertEqual(
            item.request_evidence[
                "extraction_method"
            ],
            "manual",
        )

        self.assertEqual(
            item.open_url,
            (
                "/inbox?conversation="
                f"{self.conversation.id}"
            ),
        )

    def test_organization_isolation(
        self,
    ):
        self.approval(
            status="approved",
            decision_at=self.base_time,
            organization=(
                self.other_organization
            ),
            conversation=(
                self.other_conversation
            ),
        )

        items = DecisionsService.build(
            organization=(
                self.organization
            )
        )

        self.assertEqual(
            items,
            [],
        )

    def test_newest_decision_is_first(
        self,
    ):
        older = self.approval(
            status="approved",
            decision_at=self.base_time,
            title="Older",
        )

        newer = self.approval(
            status="rejected",
            decision_at=(
                self.base_time
                + timedelta(hours=2)
            ),
            title="Newer",
        )

        items = DecisionsService.build(
            organization=(
                self.organization
            )
        )

        self.assertEqual(
            [
                item.approval_id
                for item in items
            ],
            [
                newer.id,
                older.id,
            ],
        )

    def test_summary_counts_decisions(
        self,
    ):
        approved = self.approval(
            status="approved",
            decision_at=self.base_time,
            notes="Approved.",
            title="Approved",
        )

        self.approval(
            status="rejected",
            decision_at=(
                self.base_time
                + timedelta(minutes=5)
            ),
            notes="",
            title="Rejected",
        )

        persist_intelligence_evidence(
            approved,
            evidence_text=(
                "Please approve the "
                "enterprise renewal."
            ),
            extraction_method=(
                "deterministic"
            ),
            processing_mode=(
                "deterministic"
            ),
            confidence=92,
        )

        payload = (
            DecisionsService
            .build_payload(
                organization=(
                    self.organization
                )
            )
        )

        self.assertEqual(
            payload["summary"],
            {
                "total": 2,
                "approved": 1,
                "rejected": 1,
                "with_notes": 1,
                "exact_request_evidence": 1,
            },
        )


class DecisionsAPITests(
    TestCase
):

    def setUp(self):
        self.client = APIClient()

        self.user = (
            User.objects.create_user(
                email=(
                    "decision-api@oneuch.test"
                ),
                password="pass123",
            )
        )

        self.organization = (
            Organization.objects.create(
                name="Decision API Org",
                slug="decision-api-org",
            )
        )

        OrganizationUser.objects.create(
            user=self.user,
            organization=(
                self.organization
            ),
            role="member",
        )

        self.conversation = (
            Conversation.objects.create(
                user=self.user,
                organization=(
                    self.organization
                ),
                conversation_key=(
                    "decision-api-thread"
                ),
                subject="Decision API",
            )
        )

    def test_api_requires_authentication(
        self,
    ):
        response = self.client.get(
            "/api/knowledge/decisions/"
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
                    "decision-outsider@oneuch.test"
                ),
                password="pass123",
            )
        )

        self.client.force_authenticate(
            user=outsider
        )

        response = self.client.get(
            "/api/knowledge/decisions/"
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
            "/api/knowledge/decisions/"
        )

        self.assertEqual(
            response.status_code,
            403,
        )

    def test_api_returns_tenant_decisions(
        self,
    ):
        message = (
            InboxMessage.objects.create(
                user=self.user,
                organization=(
                    self.organization
                ),
                conversation=(
                    self.conversation
                ),
                platform="gmail",
                direction="inbound",
                external_message_id=(
                    "decision-api-message"
                ),
                sender=(
                    "requester@example.com"
                ),
                recipients=(
                    self.user.email
                ),
                subject="Approval requested",
                body=(
                    "Please approve the "
                    "production deployment."
                ),
                received_at=(
                    self.base_time()
                ),
            )
        )

        decision_at = (
            self.base_time()
            + timedelta(minutes=10)
        )

        approval = (
            ApprovalItem.objects.create(
                user=self.user,
                organization=(
                    self.organization
                ),
                message=message,
                conversation=(
                    self.conversation
                ),
                title=(
                    "Approve production deployment"
                ),
                description=(
                    "Production deployment "
                    "authorization."
                ),
                requested_by=(
                    "requester@example.com"
                ),
                assigned_to=self.user,
                status="approved",
                source_type="email",
                confidence_score=90,
                decision_notes=(
                    "Approved after review."
                ),
                decision_by=self.user,
                decision_at=decision_at,
            )
        )

        self.client.force_authenticate(
            user=self.user
        )

        response = self.client.get(
            "/api/knowledge/decisions/"
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

        item = (
            response.data[
                "items"
            ][0]
        )

        self.assertEqual(
            item[
                "approval_id"
            ],
            approval.id,
        )

        self.assertEqual(
            item[
                "outcome"
            ],
            "approved",
        )

        self.assertEqual(
            item[
                "decision_by_email"
            ],
            self.user.email,
        )

    @staticmethod
    def base_time():
        return datetime(
            2026,
            8,
            29,
            12,
            0,
            tzinfo=dt_timezone.utc,
        )
