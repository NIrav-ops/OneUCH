from django.test import TestCase

from approvals.models import ApprovalItem
from inbox.models import Organization

from knowledge.services.workflow.approval_engine import (
    ApprovalEngine,
)


class ApprovalEngineTests(TestCase):

    def setUp(self):
        self.organization = Organization.objects.create(
            name="Approval Engine Org",
            slug="approval-engine-org",
        )

        self.other_organization = (
            Organization.objects.create(
                name="Other Approval Org",
                slug="other-approval-org",
            )
        )

        self.engine = ApprovalEngine()

    def create_approval(
        self,
        *,
        organization=None,
        status="pending",
        title=None,
    ):
        if organization is None:
            organization = self.organization

        if title is None:
            title = (
                f"Approval "
                f"{ApprovalItem.objects.count() + 1}"
            )

        return ApprovalItem.objects.create(
            organization=organization,
            title=title,
            status=status,
        )

    def test_empty_organization_returns_zero_counts(self):
        result = self.engine.build(
            organization=self.organization,
        )

        self.assertEqual(
            result,
            {
                "pending": 0,
                "approved": 0,
                "rejected": 0,
            },
        )

    def test_approval_status_counts_are_mapped_correctly(self):
        self.create_approval(
            status="pending",
        )

        self.create_approval(
            status="needs_info",
        )

        self.create_approval(
            status="approved",
        )

        self.create_approval(
            status="rejected",
        )

        self.create_approval(
            status="ignored",
        )

        result = self.engine.build(
            organization=self.organization,
        )

        self.assertEqual(
            result["pending"],
            2,
        )

        self.assertEqual(
            result["approved"],
            1,
        )

        self.assertEqual(
            result["rejected"],
            1,
        )

    def test_ignored_is_not_counted_in_decision_buckets(self):
        self.create_approval(
            status="ignored",
        )

        result = self.engine.build(
            organization=self.organization,
        )

        self.assertEqual(
            result,
            {
                "pending": 0,
                "approved": 0,
                "rejected": 0,
            },
        )

    def test_counts_are_isolated_by_organization(self):
        self.create_approval(
            organization=self.organization,
            status="pending",
        )

        self.create_approval(
            organization=self.other_organization,
            status="pending",
        )

        self.create_approval(
            organization=self.other_organization,
            status="approved",
        )

        self.create_approval(
            organization=self.other_organization,
            status="rejected",
        )

        result = self.engine.build(
            organization=self.organization,
        )

        self.assertEqual(
            result,
            {
                "pending": 1,
                "approved": 0,
                "rejected": 0,
            },
        )
