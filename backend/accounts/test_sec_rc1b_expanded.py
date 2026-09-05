from uuid import uuid4
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone

from rest_framework.test import APIClient

from rest_framework_simplejwt.tokens import (
    RefreshToken,
)

from accounts.models import User

from actions.models import (
    ActionItem,
    AIActionCandidate,
    FollowUpItem,
)

from approvals.models import (
    ApprovalItem,
    AIApprovalCandidate,
)

from audit_logs.models import (
    AuditLog,
)

from inbox.models import (
    Conversation,
    InboxMessage,
    Organization,
    OrganizationUser,
    RecipientContact,
)

from notifications.models import (
    Notification,
)

from timeline.models import (
    TimelineEvent,
)


class SECRC1BExpandedAttackTests(
    TestCase
):
    """
    Expanded tenant-boundary attacks.

    Tenant A authenticates and attempts to
    observe or mutate rows belonging to
    Tenant B, including deliberately poisoned
    rows whose `user` points at A while
    `organization` points at B.

    No real provider or AI execution occurs.
    """

    PASSWORD = (
        "OneUCH!ExpandedTenant93471"
    )

    POISON = (
        "SEC-RC1B-POISON-94A17"
    )

    def setUp(
        self,
    ):

        self.client = APIClient()

        (
            self.user_a,
            self.org_a,
        ) = self._tenant(
            "tenant-a-expanded@example.test"
        )

        (
            self.user_b,
            self.org_b,
        ) = self._tenant(
            "tenant-b-expanded@example.test"
        )

        # ----------------------------------------------------
        # Clean Tenant A data
        # ----------------------------------------------------

        self.conv_a = self._conversation(
            user=self.user_a,
            organization=self.org_a,
            label="a",
        )

        self.msg_a = self._message(
            user=self.user_a,
            organization=self.org_a,
            conversation=self.conv_a,
            label="a",
            subject="Tenant A normal mail",
        )

        # ----------------------------------------------------
        # Genuine Tenant B data
        # ----------------------------------------------------

        self.conv_b = self._conversation(
            user=self.user_b,
            organization=self.org_b,
            label="b",
        )

        self.msg_b = self._message(
            user=self.user_b,
            organization=self.org_b,
            conversation=self.conv_b,
            label="b",
            subject="Tenant B confidential mail",
        )

        self.timeline_b = (
            TimelineEvent.objects.create(
                conversation=self.conv_b,
                event_type="message_received",
                title=(
                    "Tenant B private timeline"
                ),
                details={
                    "secret": (
                        "TENANT-B-TIMELINE"
                    ),
                },
            )
        )

        # ----------------------------------------------------
        # Poisoned rows:
        #
        # user = Tenant A
        # organization = Tenant B
        #
        # These simulate corrupted worker/import/migration
        # ownership metadata.
        # ----------------------------------------------------

        self.poison_conv = (
            self._conversation(
                user=self.user_a,
                organization=self.org_b,
                label="poison",
            )
        )

        self.poison_msg = (
            self._message(
                user=self.user_a,
                organization=self.org_b,
                conversation=(
                    self.poison_conv
                ),
                label="poison",
                subject=(
                    self.POISON
                    + " MESSAGE"
                ),
            )
        )

        self.poison_action = (
            ActionItem.objects.create(
                user=self.user_a,
                organization=self.org_b,
                owner=self.user_a,
                title=(
                    self.POISON
                    + " ACTION"
                ),
                description=(
                    "foreign workspace action"
                ),
                status="open",
            )
        )

        self.poison_approval = (
            ApprovalItem.objects.create(
                user=self.user_a,
                organization=self.org_b,
                assigned_to=self.user_a,
                title=(
                    self.POISON
                    + " APPROVAL"
                ),
                description=(
                    "foreign workspace approval"
                ),
                status="pending",
            )
        )

        self.poison_followup = (
            FollowUpItem.objects.create(
                user=self.user_a,
                organization=self.org_b,
                conversation=(
                    self.poison_conv
                ),
                last_message=(
                    self.poison_msg
                ),
                followup_due_at=(
                    timezone.now()
                ),
                status="pending",
            )
        )

        self.poison_notification = (
            Notification.objects.create(
                user=self.user_a,
                organization=self.org_b,
                type="system",
                title=(
                    self.POISON
                    + " NOTIFICATION"
                ),
                message=(
                    "foreign workspace notification"
                ),
            )
        )

        self.poison_timeline = (
            TimelineEvent.objects.create(
                conversation=(
                    self.poison_conv
                ),
                event_type=(
                    "action_created"
                ),
                title=(
                    self.POISON
                    + " TIMELINE"
                ),
                details={
                    "secret": self.POISON,
                },
            )
        )

        self.poison_contact = (
            RecipientContact.objects.create(
                user=self.user_a,
                organization=self.org_b,
                email=(
                    "recipient-poison@"
                    "foreign.test"
                ),
                normalized_email=(
                    "recipient-poison@"
                    "foreign.test"
                ),
                display_name=(
                    self.POISON
                    + " CONTACT"
                ),
                first_seen_at=(
                    timezone.now()
                ),
                last_seen_at=(
                    timezone.now()
                ),
            )
        )

        # ----------------------------------------------------
        # Review candidates genuinely owned by Tenant B.
        # ----------------------------------------------------

        self.action_candidate_b = (
            AIActionCandidate.objects.create(
                user=self.user_b,
                organization=self.org_b,
                message=self.msg_b,
                title=(
                    "Tenant B Action Review"
                ),
                description=(
                    "Tenant B candidate"
                ),
                evidence=(
                    "Tenant B evidence"
                ),
                status="pending_review",
            )
        )

        self.approval_candidate_b = (
            AIApprovalCandidate.objects.create(
                user=self.user_b,
                organization=self.org_b,
                message=self.msg_b,
                title=(
                    "Tenant B Approval Review"
                ),
                description=(
                    "Tenant B candidate"
                ),
                evidence=(
                    "Tenant B evidence"
                ),
                status="pending_review",
            )
        )

        # ----------------------------------------------------
        # Legacy audit subsystem carries user identity but no
        # organization field. Tenant A must not see B's rows.
        # ----------------------------------------------------

        self.audit_b = (
            AuditLog.objects.create(
                user=self.user_b,
                action="read_message",
                platform="gmail",
                description=(
                    "TENANT-B-AUDIT-SECRET"
                ),
                metadata={
                    "secret": (
                        "TENANT-B-AUDIT-SECRET"
                    ),
                },
            )
        )

        self._authenticate(
            self.user_a
        )

    # ========================================================
    # FIXTURE HELPERS
    # ========================================================

    def _tenant(
        self,
        email,
    ):

        user = (
            User.objects.create_user(
                email=email,
                password=self.PASSWORD,
            )
        )

        organization = (
            Organization.objects.create(
                name="Private Workspace",
                slug=(
                    "sec-rc1b-b3-"
                    + uuid4().hex
                ),
            )
        )

        OrganizationUser.objects.create(
            user=user,
            organization=organization,
            role="owner",
        )

        return (
            user,
            organization,
        )

    def _conversation(
        self,
        *,
        user,
        organization,
        label,
    ):

        return (
            Conversation.objects.create(
                user=user,
                organization=organization,
                subject=(
                    "B3 conversation "
                    + label
                ),
                conversation_key=(
                    "b3-"
                    + label
                    + "-"
                    + uuid4().hex
                ),
                last_message_at=(
                    timezone.now()
                ),
            )
        )

    def _message(
        self,
        *,
        user,
        organization,
        conversation,
        label,
        subject,
    ):

        return (
            InboxMessage.objects.create(
                user=user,
                organization=organization,
                platform="gmail",
                direction="inbound",
                conversation=conversation,
                external_message_id=(
                    "b3-msg-"
                    + label
                    + "-"
                    + uuid4().hex
                ),
                sender=(
                    label
                    + "@sender.test"
                ),
                recipients=(
                    label
                    + "@recipient.test"
                ),
                subject=subject,
                body=(
                    subject
                    + " BODY"
                ),
                received_at=(
                    timezone.now()
                ),
                status="sent",
                is_read=False,
            )
        )

    def _authenticate(
        self,
        user,
    ):

        token = (
            RefreshToken.for_user(
                user
            ).access_token
        )

        self.client.credentials(
            HTTP_AUTHORIZATION=(
                "Bearer "
                + str(token)
            )
        )

    # ========================================================
    # INBOX AGGREGATE VISIBILITY
    # ========================================================

    def test_inbox_list_excludes_poisoned_workspace_message(
        self,
    ):

        response = self.client.get(
            "/api/inbox/messages/"
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertNotIn(
            self.POISON,
            str(response.data),
        )

    def test_unified_inbox_excludes_poisoned_workspace_message(
        self,
    ):

        response = self.client.get(
            "/api/inbox/unified/"
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertNotIn(
            self.POISON,
            str(
                response.data.get(
                    "results",
                    [],
                )
            ),
        )

    def test_unified_conversations_exclude_poisoned_workspace(
        self,
    ):

        response = self.client.get(
            "/api/inbox/unified-conversations/"
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        results = (
            response.data.get(
                "results",
                [],
            )
        )

        conversation_ids = [
            item.get(
                "conversation_id"
            )
            for item in results
        ]

        self.assertNotIn(
            self.poison_conv.id,
            conversation_ids,
        )

        self.assertNotIn(
            self.POISON,
            str(
                results
            ),
        )

    def test_message_status_excludes_poisoned_workspace_message(
        self,
    ):

        response = self.client.get(
            (
                "/api/inbox/messages/"
                f"{self.poison_msg.id}/status/"
            )
        )

        self.assertEqual(
            response.status_code,
            404,
        )

    def test_mark_all_read_does_not_mutate_poisoned_workspace_message(
        self,
    ):

        self.poison_msg.is_read = False

        self.poison_msg.save(
            update_fields=[
                "is_read"
            ]
        )

        response = self.client.post(
            "/api/inbox/messages/mark-all-read/",
            {},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.poison_msg.refresh_from_db()

        self.assertFalse(
            self.poison_msg.is_read
        )

    # ========================================================
    # POISONED ACTION / APPROVAL MUTATIONS
    # ========================================================

    def test_poisoned_action_cannot_be_completed(
        self,
    ):

        response = self.client.post(
            (
                "/api/actions/"
                f"{self.poison_action.id}/"
                "complete/"
            ),
            {},
            format="json",
        )

        self.assertIn(
            response.status_code,
            (
                403,
                404,
            ),
        )

        self.poison_action.refresh_from_db()

        self.assertEqual(
            self.poison_action.status,
            "open",
        )

    def test_poisoned_action_cannot_be_updated(
        self,
    ):

        response = self.client.post(
            (
                "/api/actions/"
                f"{self.poison_action.id}/"
                "update/"
            ),
            {
                "priority": 99,
            },
            format="json",
        )

        self.assertIn(
            response.status_code,
            (
                403,
                404,
            ),
        )

        self.poison_action.refresh_from_db()

        self.assertNotEqual(
            self.poison_action.priority,
            99,
        )

    def test_poisoned_approval_cannot_be_approved(
        self,
    ):

        before_actions = (
            ActionItem.objects.count()
        )

        response = self.client.post(
            (
                "/api/approvals/"
                f"{self.poison_approval.id}/"
                "approve/"
            ),
            {
                "decision_notes": (
                    "cross-workspace attack"
                ),
            },
            format="json",
        )

        self.assertIn(
            response.status_code,
            (
                403,
                404,
            ),
        )

        self.poison_approval.refresh_from_db()

        self.assertEqual(
            self.poison_approval.status,
            "pending",
        )

        self.assertEqual(
            ActionItem.objects.count(),
            before_actions,
        )

    @patch(
        (
            "approvals.views."
            "send_approval_assignment_"
            "notification.delay"
        )
    )
    def test_poisoned_approval_cannot_be_assigned(
        self,
        mocked_delay,
    ):

        self.poison_approval.assigned_to = None

        self.poison_approval.save(
            update_fields=[
                "assigned_to"
            ]
        )

        response = self.client.post(
            (
                "/api/approvals/"
                f"{self.poison_approval.id}/"
                "assign/"
            ),
            {
                "assigned_to": (
                    self.user_a.id
                ),
            },
            format="json",
        )

        self.assertIn(
            response.status_code,
            (
                403,
                404,
            ),
        )

        self.poison_approval.refresh_from_db()

        self.assertIsNone(
            self.poison_approval.assigned_to_id
        )

        mocked_delay.assert_not_called()

    # ========================================================
    # FOLLOW-UP / WAITING WORK
    # ========================================================

    def test_followup_list_excludes_poisoned_workspace(
        self,
    ):

        response = self.client.get(
            "/api/actions/followups/"
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertNotIn(
            self.POISON,
            str(response.data),
        )

    def test_poisoned_followup_cannot_be_snoozed(
        self,
    ):

        before_due = (
            self.poison_followup
            .followup_due_at
        )

        response = self.client.post(
            (
                "/api/actions/followups/"
                f"{self.poison_followup.id}/"
                "snooze/"
            ),
            {
                "days": 7,
            },
            format="json",
        )

        self.assertIn(
            response.status_code,
            (
                403,
                404,
            ),
        )

        self.poison_followup.refresh_from_db()

        self.assertEqual(
            self.poison_followup.followup_due_at,
            before_due,
        )

    # ========================================================
    # NOTIFICATIONS
    # ========================================================

    def test_notification_list_excludes_poisoned_workspace(
        self,
    ):

        response = self.client.get(
            "/api/notifications/"
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertNotIn(
            self.POISON,
            str(response.data),
        )

    def test_poisoned_notification_cannot_be_marked_read(
        self,
    ):

        response = self.client.post(
            (
                "/api/notifications/"
                f"{self.poison_notification.id}/"
                "read/"
            ),
            {},
            format="json",
        )

        self.assertIn(
            response.status_code,
            (
                403,
                404,
            ),
        )

        self.poison_notification.refresh_from_db()

        self.assertFalse(
            self.poison_notification.is_read
        )

    # ========================================================
    # SEARCH / DASHBOARD AGGREGATES
    # ========================================================

    def test_unified_search_excludes_poisoned_workspace(
        self,
    ):

        response = self.client.get(
            "/api/search/",
            {
                "q": self.POISON,
            },
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        payload = {
            "results": (
                response.data[
                    "results"
                ]
            ),
            "grouped": (
                response.data[
                    "grouped"
                ]
            ),
        }

        self.assertNotIn(
            self.POISON,
            str(payload),
        )

    def test_dashboard_excludes_poisoned_workspace(
        self,
    ):

        response = self.client.get(
            "/api/dashboard/"
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        # Only the clean Tenant A message
        # belongs in the dashboard.
        self.assertEqual(
            response.data[
                "total_messages"
            ],
            1,
        )

        self.assertEqual(
            response.data[
                "assigned_actions"
            ],
            0,
        )

        self.assertEqual(
            response.data[
                "pending_approvals"
            ],
            0,
        )

        self.assertEqual(
            response.data[
                "pending_followups"
            ],
            0,
        )

        self.assertNotIn(
            self.POISON,
            str(
                response.data[
                    "recent_activity"
                ]
            ),
        )

    # ========================================================
    # TIMELINE DIRECT IDOR
    # ========================================================

    def test_tenant_a_cannot_read_tenant_b_timeline(
        self,
    ):

        response = self.client.get(
            (
                "/api/timeline/conversation/"
                f"{self.conv_b.id}/"
            )
        )

        self.assertIn(
            response.status_code,
            (
                403,
                404,
            ),
        )

        self.assertNotIn(
            "Tenant B private timeline",
            str(response.data),
        )

    # ========================================================
    # LEGACY AUDIT LOG ISOLATION
    # ========================================================

    def test_tenant_a_cannot_read_tenant_b_audit_logs(
        self,
    ):

        response = self.client.get(
            "/api/audit/"
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertNotIn(
            "TENANT-B-AUDIT-SECRET",
            str(response.data),
        )

    # ========================================================
    # EXPECTED-SAFE SECONDARY SURFACES
    # ========================================================

    def test_my_work_excludes_poisoned_workspace(
        self,
    ):

        response = self.client.get(
            "/api/my-work/"
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertNotIn(
            self.POISON,
            str(
                response.data.get(
                    "items",
                    [],
                )
            ),
        )

    def test_recipient_suggestions_exclude_poisoned_workspace(
        self,
    ):

        response = self.client.get(
            "/api/inbox/recipient-suggestions/",
            {
                "q": "recipient-poison",
            },
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertNotIn(
            "recipient-poison@foreign.test",
            str(response.data),
        )

        self.assertNotIn(
            self.POISON,
            str(response.data),
        )

    def test_action_team_members_do_not_expose_tenant_b(
        self,
    ):

        response = self.client.get(
            "/api/actions/team-members/"
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertNotIn(
            self.user_b.email,
            str(response.data),
        )

    def test_approval_team_members_do_not_expose_tenant_b(
        self,
    ):

        response = self.client.get(
            "/api/approvals/team-members/"
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertNotIn(
            self.user_b.email,
            str(response.data),
        )

    def test_action_review_list_excludes_tenant_b(
        self,
    ):

        response = self.client.get(
            "/api/actions/review-candidates/"
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertNotIn(
            "Tenant B Action Review",
            str(response.data),
        )

    def test_tenant_a_cannot_reject_tenant_b_action_candidate(
        self,
    ):

        response = self.client.post(
            (
                "/api/actions/review-candidates/"
                f"{self.action_candidate_b.id}/"
                "reject/"
            ),
            {},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            404,
        )

        self.action_candidate_b.refresh_from_db()

        self.assertEqual(
            self.action_candidate_b.status,
            "pending_review",
        )

    def test_approval_review_list_excludes_tenant_b(
        self,
    ):

        response = self.client.get(
            "/api/approvals/review-candidates/"
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertNotIn(
            "Tenant B Approval Review",
            str(response.data),
        )

    def test_tenant_a_cannot_reject_tenant_b_approval_candidate(
        self,
    ):

        response = self.client.post(
            (
                "/api/approvals/review-candidates/"
                f"{self.approval_candidate_b.id}/"
                "reject/"
            ),
            {},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            404,
        )

        self.approval_candidate_b.refresh_from_db()

        self.assertEqual(
            self.approval_candidate_b.status,
            "pending_review",
        )