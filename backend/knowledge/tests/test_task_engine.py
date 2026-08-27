from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from actions.models import ActionItem
from inbox.models import Organization

from knowledge.services.workflow.task_engine import (
    TaskEngine,
)


class TaskEngineTests(TestCase):

    def setUp(self):
        self.organization = Organization.objects.create(
            name="Task Engine Org",
            slug="task-engine-org",
        )

        self.other_organization = (
            Organization.objects.create(
                name="Other Task Org",
                slug="other-task-org",
            )
        )

        self.engine = TaskEngine()

    def create_action(
        self,
        *,
        organization=None,
        status="open",
        due_date=None,
        title=None,
    ):
        if organization is None:
            organization = self.organization

        if title is None:
            title = (
                f"Action "
                f"{ActionItem.objects.count() + 1}"
            )

        return ActionItem.objects.create(
            organization=organization,
            title=title,
            status=status,
            due_date=due_date,
        )

    def test_empty_organization_returns_zero_counts(self):
        result = self.engine.build(
            organization=self.organization,
        )

        self.assertEqual(
            result,
            {
                "total": 0,
                "pending": 0,
                "completed": 0,
                "overdue": 0,
            },
        )

    def test_task_status_counts_are_mapped_correctly(self):
        now = timezone.now()

        self.create_action(
            status="open",
            due_date=(
                now - timedelta(days=1)
            ),
        )

        self.create_action(
            status="in_progress",
            due_date=(
                now + timedelta(days=1)
            ),
        )

        self.create_action(
            status="waiting",
            due_date=(
                now - timedelta(hours=2)
            ),
        )

        self.create_action(
            status="blocked",
            due_date=None,
        )

        self.create_action(
            status="completed",
            due_date=(
                now - timedelta(days=3)
            ),
        )

        self.create_action(
            status="cancelled",
            due_date=(
                now - timedelta(days=3)
            ),
        )

        self.create_action(
            status="ignored",
            due_date=(
                now - timedelta(days=3)
            ),
        )

        result = self.engine.build(
            organization=self.organization,
        )

        self.assertEqual(
            result["total"],
            7,
        )

        self.assertEqual(
            result["pending"],
            4,
        )

        self.assertEqual(
            result["completed"],
            1,
        )

        self.assertEqual(
            result["overdue"],
            2,
        )

    def test_terminal_items_are_not_overdue(self):
        past = (
            timezone.now()
            - timedelta(days=5)
        )

        self.create_action(
            status="completed",
            due_date=past,
        )

        self.create_action(
            status="cancelled",
            due_date=past,
        )

        self.create_action(
            status="ignored",
            due_date=past,
        )

        result = self.engine.build(
            organization=self.organization,
        )

        self.assertEqual(
            result["total"],
            3,
        )

        self.assertEqual(
            result["pending"],
            0,
        )

        self.assertEqual(
            result["completed"],
            1,
        )

        self.assertEqual(
            result["overdue"],
            0,
        )

    def test_counts_are_isolated_by_organization(self):
        past = (
            timezone.now()
            - timedelta(days=1)
        )

        self.create_action(
            organization=self.organization,
            status="open",
            due_date=past,
        )

        self.create_action(
            organization=self.other_organization,
            status="open",
            due_date=past,
        )

        self.create_action(
            organization=self.other_organization,
            status="completed",
        )

        result = self.engine.build(
            organization=self.organization,
        )

        self.assertEqual(
            result,
            {
                "total": 1,
                "pending": 1,
                "completed": 0,
                "overdue": 1,
            },
        )
