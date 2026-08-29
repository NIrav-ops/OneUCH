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
    ExpectedResponseItem,
)

from inbox.models import (
    Conversation,
    InboxMessage,
    Organization,
    OrganizationUser,
)

from knowledge.services.waiting_for import (
    WaitingForService,
)


User = get_user_model()


@override_settings(
    TIME_ZONE="UTC"
)
class WaitingForServiceTests(
    TestCase
):

    def setUp(self):
        self.user = (
            User.objects.create_user(
                email=(
                    "waiting-owner@oneuch.test"
                ),
                password="pass123",
            )
        )

        self.organization = (
            Organization.objects.create(
                name="Waiting For Org",
                slug="waiting-for-org",
            )
        )

        self.other_organization = (
            Organization.objects.create(
                name="Other Waiting Org",
                slug="other-waiting-org",
            )
        )

        self.conversation = (
            Conversation.objects.create(
                user=self.user,
                organization=(
                    self.organization
                ),
                conversation_key=(
                    "waiting-for-thread"
                ),
                subject=(
                    "External response"
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
                    "other-waiting-thread"
                ),
                subject="Other tenant",
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

        self.counter = 0

    def message(
        self,
        *,
        conversation=None,
        organization=None,
        sender="vendor@example.com",
        direction="inbound",
        recipients=None,
        body="Vendor will confirm tomorrow.",
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

        if recipients is None:
            recipients = (
                self.user.email
                if direction == "inbound"
                else "vendor@example.com"
            )

        return InboxMessage.objects.create(
            user=self.user,
            organization=organization,
            conversation=conversation,
            platform="gmail",
            direction=direction,
            external_message_id=(
                "waiting-for-message-"
                f"{self.counter}"
            ),
            sender=sender,
            recipients=recipients,
            subject="Waiting For",
            body=body,
            received_at=(
                self.now
                - timedelta(
                    hours=2
                )
            ),
        )

    def expected_response(
        self,
        *,
        status="waiting",
        due_at=None,
        expected_from=(
            "vendor@example.com"
        ),
        organization=None,
        conversation=None,
        body=(
            "Vendor will confirm tomorrow."
        ),
    ):
        organization = (
            organization
            or self.organization
        )

        conversation = (
            conversation
            or self.conversation
        )

        source = self.message(
            organization=organization,
            conversation=conversation,
            sender=(
                "vendor@example.com"
            ),
            body=body,
        )

        return (
            ExpectedResponseItem
            .objects.create(
                user=self.user,
                organization=organization,
                conversation=conversation,
                source_message=source,
                expected_from=(
                    expected_from
                ),
                evidence_text=body,
                response_due_at=due_at,
                status=status,
            )
        )

    def test_waiting_expected_response_appears(
        self,
    ):
        item = self.expected_response(
            due_at=(
                self.now
                + timedelta(days=1)
            ),
        )

        results = (
            WaitingForService.build(
                organization=(
                    self.organization
                ),
                now=self.now,
            )
        )

        self.assertEqual(
            len(results),
            1,
        )

        result = results[0]

        self.assertEqual(
            result.waiting_id,
            f"waiting_for:{item.id}",
        )

        self.assertEqual(
            result.commitment_id,
            (
                "expected_response:"
                f"{item.id}"
            ),
        )

        self.assertEqual(
            result.counterparty,
            "vendor@example.com",
        )

        self.assertEqual(
            result.owner_id,
            self.user.id,
        )

        self.assertEqual(
            result.source_status,
            "waiting",
        )

        self.assertEqual(
            result.open_url,
            (
                "/inbox?conversation="
                f"{self.conversation.id}"
            ),
        )

        self.assertEqual(
            result.evidence[
                "evidence_quality"
            ],
            "exact",
        )

    def test_received_and_ignored_are_excluded(
        self,
    ):
        self.expected_response(
            status="received",
        )

        self.expected_response(
            status="ignored",
        )

        results = (
            WaitingForService.build(
                organization=(
                    self.organization
                ),
                now=self.now,
            )
        )

        self.assertEqual(
            results,
            [],
        )

    def test_internal_action_commitment_is_excluded(
        self,
    ):
        message = self.message(
            body=(
                "Please send final proposal."
            )
        )

        ActionItem.objects.create(
            user=self.user,
            organization=(
                self.organization
            ),
            message=message,
            title=(
                "Send final proposal"
            ),
            owner=self.user,
            due_date=(
                self.now
                + timedelta(days=1)
            ),
            status="open",
            source_type="email",
            confidence_score=90,
        )

        results = (
            WaitingForService.build(
                organization=(
                    self.organization
                ),
                now=self.now,
            )
        )

        self.assertEqual(
            results,
            [],
        )

    def test_due_states_are_server_derived(
        self,
    ):
        overdue = self.expected_response(
            due_at=(
                self.now
                - timedelta(hours=1)
            ),
            body="Overdue response.",
        )

        today = self.expected_response(
            due_at=(
                self.now
                + timedelta(hours=2)
            ),
            body="Response due today.",
        )

        upcoming = self.expected_response(
            due_at=(
                self.now
                + timedelta(days=2)
            ),
            body="Upcoming response.",
        )

        no_due = self.expected_response(
            due_at=None,
            body="Response with no due date.",
        )

        results = (
            WaitingForService.build(
                organization=(
                    self.organization
                ),
                now=self.now,
            )
        )

        states = {
            item.source_object_id:
                item.due_state
            for item in results
        }

        self.assertEqual(
            states[overdue.id],
            "overdue",
        )

        self.assertEqual(
            states[today.id],
            "due_today",
        )

        self.assertEqual(
            states[upcoming.id],
            "upcoming",
        )

        self.assertEqual(
            states[no_due.id],
            "no_due",
        )

    def test_summary_counts_due_states(
        self,
    ):
        self.expected_response(
            due_at=(
                self.now
                - timedelta(hours=1)
            ),
            body="Overdue.",
        )

        self.expected_response(
            due_at=(
                self.now
                + timedelta(hours=2)
            ),
            body="Today.",
        )

        self.expected_response(
            due_at=(
                self.now
                + timedelta(days=2)
            ),
            body="Upcoming.",
        )

        self.expected_response(
            due_at=None,
            body="No due.",
        )

        payload = (
            WaitingForService
            .build_payload(
                organization=(
                    self.organization
                ),
                now=self.now,
            )
        )

        self.assertEqual(
            payload["summary"],
            {
                "total": 4,
                "overdue": 1,
                "due_today": 1,
                "upcoming": 1,
                "no_due": 1,
            },
        )

    def test_ordering_prioritizes_due_state(
        self,
    ):
        no_due = self.expected_response(
            due_at=None,
            body="No due.",
        )

        upcoming = self.expected_response(
            due_at=(
                self.now
                + timedelta(days=2)
            ),
            body="Upcoming.",
        )

        today = self.expected_response(
            due_at=(
                self.now
                + timedelta(hours=3)
            ),
            body="Today.",
        )

        overdue = self.expected_response(
            due_at=(
                self.now
                - timedelta(hours=2)
            ),
            body="Overdue.",
        )

        results = (
            WaitingForService.build(
                organization=(
                    self.organization
                ),
                now=self.now,
            )
        )

        self.assertEqual(
            [
                item.source_object_id
                for item in results
            ],
            [
                overdue.id,
                today.id,
                upcoming.id,
                no_due.id,
            ],
        )

    def test_organization_isolation(
        self,
    ):
        self.expected_response(
            organization=(
                self.other_organization
            ),
            conversation=(
                self.other_conversation
            ),
            due_at=(
                self.now
                - timedelta(days=1)
            ),
        )

        results = (
            WaitingForService.build(
                organization=(
                    self.organization
                ),
                now=self.now,
            )
        )

        self.assertEqual(
            results,
            [],
        )


@override_settings(
    TIME_ZONE="UTC"
)
class WaitingForAPITests(
    TestCase
):

    def setUp(self):
        self.client = APIClient()

        self.user = (
            User.objects.create_user(
                email=(
                    "waiting-api@oneuch.test"
                ),
                password="pass123",
            )
        )

        self.organization = (
            Organization.objects.create(
                name="Waiting API Org",
                slug="waiting-api-org",
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
                    "waiting-api-thread"
                ),
                subject="Vendor response",
            )
        )

    def test_api_requires_authentication(
        self,
    ):
        response = self.client.get(
            "/api/knowledge/waiting-for/"
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
                    "waiting-outsider@oneuch.test"
                ),
                password="pass123",
            )
        )

        self.client.force_authenticate(
            user=outsider
        )

        response = self.client.get(
            "/api/knowledge/waiting-for/"
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
            "/api/knowledge/waiting-for/"
        )

        self.assertEqual(
            response.status_code,
            403,
        )

    def test_api_returns_only_active_external_waits(
        self,
    ):
        source = (
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
                    "waiting-api-message"
                ),
                sender=(
                    "vendor@example.com"
                ),
                recipients=(
                    self.user.email
                ),
                subject=(
                    "Vendor confirmation"
                ),
                body=(
                    "Vendor will confirm tomorrow."
                ),
                received_at=datetime(
                    2026,
                    8,
                    29,
                    8,
                    0,
                    tzinfo=dt_timezone.utc,
                ),
            )
        )

        waiting = (
            ExpectedResponseItem
            .objects.create(
                user=self.user,
                organization=(
                    self.organization
                ),
                conversation=(
                    self.conversation
                ),
                source_message=source,
                expected_from=(
                    "vendor@example.com"
                ),
                evidence_text=(
                    "Vendor will confirm tomorrow."
                ),
                response_due_at=datetime(
                    2026,
                    8,
                    30,
                    8,
                    0,
                    tzinfo=dt_timezone.utc,
                ),
                status="waiting",
            )
        )

        self.client.force_authenticate(
            user=self.user
        )

        response = self.client.get(
            "/api/knowledge/waiting-for/"
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

        self.assertEqual(
            response.data[
                "items"
            ][0][
                "source_object_id"
            ],
            waiting.id,
        )

        self.assertEqual(
            response.data[
                "items"
            ][0][
                "source_status"
            ],
            "waiting",
        )
