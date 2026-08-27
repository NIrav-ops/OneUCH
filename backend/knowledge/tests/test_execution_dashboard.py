from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from actions.models import (
    ActionItem,
    ExpectedResponseItem,
    FollowUpItem,
)
from approvals.models import ApprovalItem
from inbox.models import (
    Conversation,
    InboxMessage,
    Organization,
)

from knowledge.services.workflow.execution_dashboard import (
    ExecutionDashboardService,
)


User = get_user_model()


class ExecutionDashboardServiceTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            email="execution-dashboard@example.com",
            password="testpass123",
        )

        self.organization = Organization.objects.create(
            name="Execution Dashboard Org",
            slug="execution-dashboard-org",
        )

        self.other_organization = Organization.objects.create(
            name="Other Execution Dashboard Org",
            slug="other-execution-dashboard-org",
        )

        self.conversation = Conversation.objects.create(
            user=self.user,
            organization=self.organization,
            subject="Execution dashboard conversation",
            conversation_key="execution-dashboard-conversation",
        )

        self.other_conversation = Conversation.objects.create(
            user=self.user,
            organization=self.other_organization,
            subject="Other execution dashboard conversation",
            conversation_key="other-execution-dashboard-conversation",
        )

        now = timezone.now()

        self.message = InboxMessage.objects.create(
            user=self.user,
            organization=self.organization,
            conversation=self.conversation,
            platform="gmail",
            direction="inbound",
            external_message_id="execution-dashboard-message",
            sender="vendor@example.com",
            recipients=self.user.email,
            subject="Execution dashboard",
            body="Vendor will confirm tomorrow.",
            received_at=now,
        )

        self.other_message = InboxMessage.objects.create(
            user=self.user,
            organization=self.other_organization,
            conversation=self.other_conversation,
            platform="gmail",
            direction="inbound",
            external_message_id="other-execution-dashboard-message",
            sender="other@example.com",
            recipients=self.user.email,
            subject="Other execution dashboard",
            body="Please follow up tomorrow.",
            received_at=now,
        )

        self.service = ExecutionDashboardService()

    def test_empty_organization_returns_zero_dashboard(self):
        empty_org = Organization.objects.create(
            name="Empty Dashboard Org",
            slug="empty-dashboard-org",
        )

        result = self.service.build(
            organization=empty_org,
        )

        self.assertEqual(
            result,
            {
                "tasks": {
                    "total": 0,
                    "pending": 0,
                    "completed": 0,
                    "overdue": 0,
                },
                "followups": {
                    "required": 0,
                    "completed": 0,
                    "pending": 0,
                },
                "approvals": {
                    "pending": 0,
                    "approved": 0,
                    "rejected": 0,
                },
            },
        )

    def test_dashboard_combines_real_engine_counts(self):
        past = (
            timezone.now()
            - timedelta(days=1)
        )

        ActionItem.objects.create(
            organization=self.organization,
            title="Open overdue action",
            status="open",
            due_date=past,
        )

        ActionItem.objects.create(
            organization=self.organization,
            title="Completed action",
            status="completed",
        )

        ActionItem.objects.create(
            organization=self.organization,
            title="Ignored action",
            status="ignored",
        )

        ApprovalItem.objects.create(
            organization=self.organization,
            title="Pending approval",
            status="pending",
        )

        ApprovalItem.objects.create(
            organization=self.organization,
            title="Needs info approval",
            status="needs_info",
        )

        ApprovalItem.objects.create(
            organization=self.organization,
            title="Approved approval",
            status="approved",
        )

        ApprovalItem.objects.create(
            organization=self.organization,
            title="Rejected approval",
            status="rejected",
        )

        ApprovalItem.objects.create(
            organization=self.organization,
            title="Ignored approval",
            status="ignored",
        )

        FollowUpItem.objects.create(
            user=self.user,
            organization=self.organization,
            conversation=self.conversation,
            last_message=self.message,
            status="pending",
        )

        FollowUpItem.objects.create(
            user=self.user,
            organization=self.organization,
            conversation=self.conversation,
            last_message=self.message,
            status="completed",
        )

        FollowUpItem.objects.create(
            user=self.user,
            organization=self.organization,
            conversation=self.conversation,
            last_message=self.message,
            status="ignored",
        )

        ExpectedResponseItem.objects.create(
            user=self.user,
            organization=self.organization,
            conversation=self.conversation,
            source_message=self.message,
            status="waiting",
        )

        ExpectedResponseItem.objects.create(
            user=self.user,
            organization=self.organization,
            conversation=self.conversation,
            source_message=self.message,
            status="received",
        )

        ExpectedResponseItem.objects.create(
            user=self.user,
            organization=self.organization,
            conversation=self.conversation,
            source_message=self.message,
            status="ignored",
        )

        result = self.service.build(
            organization=self.organization,
        )

        self.assertEqual(
            result,
            {
                "tasks": {
                    "total": 3,
                    "pending": 1,
                    "completed": 1,
                    "overdue": 1,
                },
                "followups": {
                    "required": 6,
                    "completed": 2,
                    "pending": 2,
                },
                "approvals": {
                    "pending": 2,
                    "approved": 1,
                    "rejected": 1,
                },
            },
        )

    def test_dashboard_is_isolated_by_organization(self):
        ActionItem.objects.create(
            organization=self.organization,
            title="Primary action",
            status="open",
        )

        ApprovalItem.objects.create(
            organization=self.organization,
            title="Primary approval",
            status="approved",
        )

        FollowUpItem.objects.create(
            user=self.user,
            organization=self.organization,
            conversation=self.conversation,
            last_message=self.message,
            status="pending",
        )

        ExpectedResponseItem.objects.create(
            user=self.user,
            organization=self.organization,
            conversation=self.conversation,
            source_message=self.message,
            status="received",
        )

        ActionItem.objects.create(
            organization=self.other_organization,
            title="Other action",
            status="completed",
        )

        ApprovalItem.objects.create(
            organization=self.other_organization,
            title="Other approval",
            status="rejected",
        )

        FollowUpItem.objects.create(
            user=self.user,
            organization=self.other_organization,
            conversation=self.other_conversation,
            last_message=self.other_message,
            status="completed",
        )

        ExpectedResponseItem.objects.create(
            user=self.user,
            organization=self.other_organization,
            conversation=self.other_conversation,
            source_message=self.other_message,
            status="waiting",
        )

        result = self.service.build(
            organization=self.organization,
        )

        self.assertEqual(
            result,
            {
                "tasks": {
                    "total": 1,
                    "pending": 1,
                    "completed": 0,
                    "overdue": 0,
                },
                "followups": {
                    "required": 2,
                    "completed": 1,
                    "pending": 1,
                },
                "approvals": {
                    "pending": 0,
                    "approved": 1,
                    "rejected": 0,
                },
            },
        )
