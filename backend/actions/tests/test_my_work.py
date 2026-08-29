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
    override_settings,
)

from rest_framework.test import (
    APIClient,
)

from actions.models import (
    ActionItem,
)
from actions.services.my_work import (
    MyWorkService,
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


User = get_user_model()


@override_settings(
    TIME_ZONE="UTC"
)
class MyWorkServiceTests(
    TestCase
):

    def setUp(self):
        self.owner = (
            User.objects
            .create_user(
                email=(
                    "owner@my-work.test"
                ),
                password="pass123",
            )
        )

        self.creator = (
            User.objects
            .create_user(
                email=(
                    "creator@my-work.test"
                ),
                password="pass123",
            )
        )

        self.other_user = (
            User.objects
            .create_user(
                email=(
                    "other@my-work.test"
                ),
                password="pass123",
            )
        )

        self.organization = (
            Organization.objects.create(
                name="My Work Org",
                slug="my-work-org",
            )
        )

        for user in (
            self.owner,
            self.creator,
            self.other_user,
        ):
            OrganizationUser.objects.create(
                user=user,
                organization=(
                    self.organization
                ),
                role="member",
            )

        self.other_organization = (
            Organization.objects.create(
                name=(
                    "Other My Work Org"
                ),
                slug=(
                    "other-my-work-org"
                ),
            )
        )

        self.now = datetime(
            2026,
            8,
            29,
            9,
            0,
            tzinfo=dt_timezone.utc,
        )

    def action(
        self,
        *,
        creator=None,
        owner=None,
        organization=None,
        status="open",
        due_at=None,
        priority=0,
        message=None,
        title="Owned action",
    ):
        return ActionItem.objects.create(
            user=(
                creator
                or self.creator
            ),
            organization=(
                organization
                or self.organization
            ),
            message=message,
            title=title,
            owner=(
                owner
                if owner is not None
                else self.owner
            ),
            due_date=due_at,
            priority=priority,
            status=status,
            source_type="email",
            confidence_score=90,
        )

    def approval(
        self,
        *,
        creator=None,
        assigned_to=None,
        organization=None,
        status="pending",
        due_at=None,
        priority=0,
        conversation=None,
        message=None,
        title="Owned approval",
    ):
        return ApprovalItem.objects.create(
            user=(
                creator
                or self.creator
            ),
            organization=(
                organization
                or self.organization
            ),
            conversation=conversation,
            message=message,
            title=title,
            assigned_to=(
                assigned_to
                if assigned_to is not None
                else self.owner
            ),
            status=status,
            due_date=due_at,
            priority=priority,
            source_type="email",
            confidence_score=90,
        )

    def test_action_assigned_to_me_appears_even_when_created_by_other(
        self,
    ):
        action = self.action(
            creator=self.creator,
            owner=self.owner,
        )

        items = MyWorkService.build(
            organization=(
                self.organization
            ),
            user=self.owner,
            now=self.now,
        )

        self.assertEqual(
            len(items),
            1,
        )

        self.assertEqual(
            items[0].work_id,
            f"action:{action.id}",
        )

        self.assertEqual(
            items[0].owner_id,
            self.owner.id,
        )

    def test_action_created_by_me_but_owned_by_other_is_excluded(
        self,
    ):
        self.action(
            creator=self.owner,
            owner=self.creator,
        )

        items = MyWorkService.build(
            organization=(
                self.organization
            ),
            user=self.owner,
            now=self.now,
        )

        self.assertEqual(
            items,
            [],
        )

    def test_approval_assigned_to_me_appears_even_when_created_by_other(
        self,
    ):
        approval = self.approval(
            creator=self.creator,
            assigned_to=self.owner,
        )

        items = MyWorkService.build(
            organization=(
                self.organization
            ),
            user=self.owner,
            now=self.now,
        )

        self.assertEqual(
            len(items),
            1,
        )

        self.assertEqual(
            items[0].work_id,
            (
                f"approval:"
                f"{approval.id}"
            ),
        )

        self.assertEqual(
            items[0].owner_id,
            self.owner.id,
        )

    def test_approval_created_by_me_but_assigned_to_other_is_excluded(
        self,
    ):
        self.approval(
            creator=self.owner,
            assigned_to=self.creator,
        )

        items = MyWorkService.build(
            organization=(
                self.organization
            ),
            user=self.owner,
            now=self.now,
        )

        self.assertEqual(
            items,
            [],
        )

    def test_only_active_action_states_are_in_my_work(
        self,
    ):
        for state in (
            "open",
            "in_progress",
            "waiting",
            "blocked",
            "completed",
            "cancelled",
            "ignored",
        ):
            self.action(
                owner=self.owner,
                status=state,
                title=(
                    f"Action {state}"
                ),
            )

        items = MyWorkService.build(
            organization=(
                self.organization
            ),
            user=self.owner,
            now=self.now,
        )

        states = {
            item.status
            for item in items
        }

        self.assertEqual(
            states,
            {
                "open",
                "in_progress",
                "waiting",
                "blocked",
            },
        )

    def test_pending_and_needs_info_approvals_are_current_work(
        self,
    ):
        for state in (
            "pending",
            "needs_info",
            "approved",
            "rejected",
            "ignored",
        ):
            self.approval(
                assigned_to=self.owner,
                status=state,
                title=(
                    f"Approval {state}"
                ),
            )

        items = MyWorkService.build(
            organization=(
                self.organization
            ),
            user=self.owner,
            now=self.now,
        )

        states = {
            item.status
            for item in items
        }

        self.assertEqual(
            states,
            {
                "pending",
                "needs_info",
            },
        )

    def test_summary_uses_current_owned_execution_state(
        self,
    ):
        self.action(
            owner=self.owner,
            status="blocked",
            due_at=(
                self.now
                - timedelta(
                    hours=1
                )
            ),
        )

        self.action(
            owner=self.owner,
            status="in_progress",
            due_at=(
                self.now
                + timedelta(
                    hours=1
                )
            ),
        )

        self.action(
            owner=self.owner,
            status="waiting",
            due_at=(
                self.now
                + timedelta(
                    days=1
                )
            ),
        )

        self.approval(
            assigned_to=self.owner,
            status="needs_info",
            due_at=None,
        )

        payload = (
            MyWorkService
            .build_payload(
                organization=(
                    self.organization
                ),
                user=self.owner,
                now=self.now,
            )
        )

        summary = (
            payload["summary"]
        )

        self.assertEqual(
            summary["total"],
            4,
        )

        self.assertEqual(
            summary["actions"],
            3,
        )

        self.assertEqual(
            summary["approvals"],
            1,
        )

        self.assertEqual(
            summary["overdue"],
            1,
        )

        self.assertEqual(
            summary["due_today"],
            1,
        )

        self.assertEqual(
            summary["blocked"],
            1,
        )

        self.assertEqual(
            summary["in_progress"],
            1,
        )

        self.assertEqual(
            summary["waiting"],
            1,
        )

        self.assertEqual(
            summary["needs_info"],
            1,
        )

        self.assertEqual(
            summary["no_due"],
            1,
        )

    def test_action_source_navigation_is_normalized(
        self,
    ):
        conversation = (
            Conversation.objects.create(
                user=self.creator,
                organization=(
                    self.organization
                ),
                conversation_key=(
                    "my-work-navigation"
                ),
                subject=(
                    "Architecture review"
                ),
            )
        )

        message = (
            InboxMessage.objects.create(
                user=self.creator,
                organization=(
                    self.organization
                ),
                conversation=conversation,
                platform="gmail",
                direction="inbound",
                external_message_id=(
                    "my-work-message"
                ),
                sender=(
                    "customer@example.com"
                ),
                recipients=(
                    self.creator.email
                ),
                subject=(
                    "Architecture review"
                ),
                body=(
                    "Please confirm architecture."
                ),
                received_at=self.now,
            )
        )

        action = self.action(
            owner=self.owner,
            message=message,
        )

        item = MyWorkService.build(
            organization=(
                self.organization
            ),
            user=self.owner,
            now=self.now,
        )[0]

        self.assertEqual(
            item.source_object_id,
            action.id,
        )

        self.assertEqual(
            item.conversation_id,
            conversation.id,
        )

        self.assertEqual(
            item.source_message_id,
            message.id,
        )

        self.assertEqual(
            item.open_url,
            (
                "/inbox?conversation="
                f"{conversation.id}"
            ),
        )

        self.assertEqual(
            item.execution_url,
            "/actions",
        )

    def test_approval_execution_url_is_normalized(
        self,
    ):
        approval = self.approval(
            assigned_to=self.owner,
        )

        item = MyWorkService.build(
            organization=(
                self.organization
            ),
            user=self.owner,
            now=self.now,
        )[0]

        self.assertEqual(
            item.source_object_id,
            approval.id,
        )

        self.assertEqual(
            item.execution_url,
            "/approvals",
        )

    def test_organization_isolation_is_enforced(
        self,
    ):
        self.action(
            owner=self.owner,
            organization=(
                self.other_organization
            ),
        )

        items = MyWorkService.build(
            organization=(
                self.organization
            ),
            user=self.owner,
            now=self.now,
        )

        self.assertEqual(
            items,
            [],
        )

    def test_items_are_ordered_by_execution_urgency(
        self,
    ):
        self.action(
            owner=self.owner,
            title="No due",
            due_at=None,
        )

        self.action(
            owner=self.owner,
            title="Upcoming",
            due_at=(
                self.now
                + timedelta(
                    days=1
                )
            ),
        )

        self.approval(
            assigned_to=self.owner,
            title="Due today",
            due_at=(
                self.now
                + timedelta(
                    hours=2
                )
            ),
        )

        self.action(
            owner=self.owner,
            title="Overdue",
            due_at=(
                self.now
                - timedelta(
                    hours=2
                )
            ),
        )

        items = MyWorkService.build(
            organization=(
                self.organization
            ),
            user=self.owner,
            now=self.now,
        )

        self.assertEqual(
            [
                item.due_state
                for item in items
            ],
            [
                "overdue",
                "due_today",
                "upcoming",
                "no_due",
            ],
        )


class MyWorkAPITests(
    TestCase
):

    def setUp(self):
        self.client = APIClient()

        self.user = (
            User.objects.create_user(
                email=(
                    "api-owner@my-work.test"
                ),
                password="pass123",
            )
        )

        self.organization = (
            Organization.objects.create(
                name="My Work API Org",
                slug="my-work-api-org",
            )
        )

        OrganizationUser.objects.create(
            user=self.user,
            organization=(
                self.organization
            ),
            role="member",
        )

    def test_my_work_api_requires_authentication(
        self,
    ):
        response = self.client.get(
            "/api/my-work/"
        )

        self.assertEqual(
            response.status_code,
            401,
        )

    def test_my_work_api_requires_membership(
        self,
    ):
        outsider = (
            User.objects.create_user(
                email=(
                    "outsider@my-work.test"
                ),
                password="pass123",
            )
        )

        self.client.force_authenticate(
            user=outsider
        )

        response = self.client.get(
            "/api/my-work/"
        )

        self.assertEqual(
            response.status_code,
            403,
        )

    def test_my_work_api_rejects_inactive_organization(
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
            "/api/my-work/"
        )

        self.assertEqual(
            response.status_code,
            403,
        )

    def test_my_work_api_returns_explicitly_owned_tenant_work(
        self,
    ):
        creator = (
            User.objects.create_user(
                email=(
                    "api-creator@my-work.test"
                ),
                password="pass123",
            )
        )

        OrganizationUser.objects.create(
            user=creator,
            organization=(
                self.organization
            ),
            role="member",
        )

        owned = (
            ActionItem.objects.create(
                user=creator,
                organization=(
                    self.organization
                ),
                title=(
                    "Owned by API user"
                ),
                owner=self.user,
                status="open",
                source_type="email",
                confidence_score=90,
            )
        )

        ActionItem.objects.create(
            user=self.user,
            organization=(
                self.organization
            ),
            title=(
                "Created by API user "
                "but owned elsewhere"
            ),
            owner=creator,
            status="open",
            source_type="email",
            confidence_score=90,
        )

        self.client.force_authenticate(
            user=self.user
        )

        response = self.client.get(
            "/api/my-work/"
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
                "user_id"
            ],
            self.user.id,
        )

        self.assertEqual(
            response.data[
                "summary"
            ][
                "total"
            ],
            1,
        )

        self.assertEqual(
            response.data[
                "items"
            ][0][
                "work_id"
            ],
            f"action:{owned.id}",
        )

        self.assertEqual(
            response.data[
                "items"
            ][0][
                "owner_id"
            ],
            self.user.id,
        )
