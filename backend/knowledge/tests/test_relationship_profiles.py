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

from actions.models import (
    ActionItem,
    ExpectedResponseItem,
)

from approvals.models import (
    ApprovalItem,
)

from context.models import (
    Person,
)

from inbox.models import (
    Conversation,
    InboxMessage,
    Organization,
    OrganizationUser,
)

from knowledge.services.relationship_profiles import (
    RelationshipProfilesService,
)


User = get_user_model()


class RelationshipProfilesServiceTests(
    TestCase
):

    def setUp(self):
        self.user = (
            User.objects.create_user(
                email=(
                    "relationship-owner@oneuch.test"
                ),
                password="pass123",
            )
        )

        self.organization = (
            Organization.objects.create(
                name="Relationship Org",
                slug="relationship-org",
            )
        )

        OrganizationUser.objects.create(
            user=self.user,
            organization=(
                self.organization
            ),
            role="member",
        )

        self.other_user = (
            User.objects.create_user(
                email=(
                    "other-owner@oneuch.test"
                ),
                password="pass123",
            )
        )

        self.other_organization = (
            Organization.objects.create(
                name="Other Relationship Org",
                slug="other-relationship-org",
            )
        )

        OrganizationUser.objects.create(
            user=self.other_user,
            organization=(
                self.other_organization
            ),
            role="member",
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

    def conversation(
        self,
        *,
        organization=None,
        user=None,
        subject="Relationship thread",
    ):
        self.counter += 1

        organization = (
            organization
            or self.organization
        )

        user = (
            user
            or self.user
        )

        return Conversation.objects.create(
            user=user,
            organization=organization,
            conversation_key=(
                "relationship-conversation-"
                f"{self.counter}"
            ),
            subject=subject,
        )

    def message(
        self,
        *,
        direction,
        sender,
        recipients,
        organization=None,
        user=None,
        conversation=None,
        subject="Relationship message",
        received_at=None,
    ):
        organization = (
            organization
            or self.organization
        )

        user = (
            user
            or self.user
        )

        conversation = (
            conversation
            or self.conversation(
                organization=organization,
                user=user,
                subject=subject,
            )
        )

        self.counter += 1

        return InboxMessage.objects.create(
            user=user,
            organization=organization,
            conversation=conversation,
            platform="gmail",
            direction=direction,
            external_message_id=(
                "relationship-message-"
                f"{self.counter}"
            ),
            sender=sender,
            recipients=recipients,
            subject=subject,
            body=(
                "Relationship communication."
            ),
            received_at=(
                received_at
                or self.base_time
            ),
        )

    def profile(
        self,
        email,
    ):
        payload = (
            RelationshipProfilesService
            .build_profile(
                organization=(
                    self.organization
                ),
                email=email,
            )
        )

        self.assertIsNotNone(
            payload
        )

        return payload

    def test_inbound_message_discovers_external_profile_without_person(
        self,
    ):
        self.message(
            direction="inbound",
            sender="vendor@example.com",
            recipients=self.user.email,
        )

        payload = (
            RelationshipProfilesService
            .build_index(
                organization=(
                    self.organization
                )
            )
        )

        self.assertEqual(
            len(
                payload["profiles"]
            ),
            1,
        )

        profile = (
            payload[
                "profiles"
            ][0]
        )

        self.assertEqual(
            profile["email"],
            "vendor@example.com",
        )

        self.assertIsNone(
            profile["person_id"]
        )

        self.assertEqual(
            profile[
                "communication_total"
            ],
            1,
        )

        self.assertEqual(
            profile[
                "inbound_count"
            ],
            1,
        )

    def test_outbound_recipients_discover_external_profiles(
        self,
    ):
        self.message(
            direction="outbound",
            sender=self.user.email,
            recipients=(
                "Customer <customer@example.com>; "
                "Partner <partner@example.com>"
            ),
        )

        payload = (
            RelationshipProfilesService
            .build_index(
                organization=(
                    self.organization
                )
            )
        )

        emails = {
            item["email"]
            for item
            in payload["profiles"]
        }

        self.assertEqual(
            emails,
            {
                "customer@example.com",
                "partner@example.com",
            },
        )

    def test_internal_organization_users_are_excluded(
        self,
    ):
        teammate = (
            User.objects.create_user(
                email=(
                    "teammate@oneuch.test"
                ),
                password="pass123",
            )
        )

        OrganizationUser.objects.create(
            user=teammate,
            organization=(
                self.organization
            ),
            role="member",
        )

        self.message(
            direction="outbound",
            sender=self.user.email,
            recipients=(
                "teammate@oneuch.test, "
                "customer@example.com"
            ),
        )

        payload = (
            RelationshipProfilesService
            .build_index(
                organization=(
                    self.organization
                )
            )
        )

        emails = {
            item["email"]
            for item
            in payload["profiles"]
        }

        self.assertEqual(
            emails,
            {
                "customer@example.com"
            },
        )

    def test_person_enriches_profile_but_is_not_required(
        self,
    ):
        person = (
            Person.objects.create(
                organization=(
                    self.organization
                ),
                email=(
                    "contact@example.com"
                ),
                full_name=(
                    "Asha Mehta"
                ),
                company=(
                    "Example Industries"
                ),
                job_title=(
                    "Procurement Director"
                ),
                is_internal=False,
            )
        )

        payload = self.profile(
            "CONTACT@EXAMPLE.COM"
        )

        profile = (
            payload[
                "profile"
            ]
        )

        self.assertEqual(
            profile[
                "person_id"
            ],
            person.id,
        )

        self.assertEqual(
            profile[
                "full_name"
            ],
            "Asha Mehta",
        )

        self.assertEqual(
            profile[
                "company"
            ],
            "Example Industries",
        )

        self.assertEqual(
            profile[
                "job_title"
            ],
            "Procurement Director",
        )

    def test_person_only_external_profile_appears(
        self,
    ):
        Person.objects.create(
            organization=(
                self.organization
            ),
            email=(
                "known@example.com"
            ),
            full_name=(
                "Known Contact"
            ),
            is_internal=False,
        )

        payload = (
            RelationshipProfilesService
            .build_index(
                organization=(
                    self.organization
                )
            )
        )

        self.assertEqual(
            payload[
                "profiles"
            ][0][
                "email"
            ],
            "known@example.com",
        )

        self.assertEqual(
            payload[
                "profiles"
            ][0][
                "communication_total"
            ],
            0,
        )

    def test_commitments_waits_and_decisions_are_aggregated(
        self,
    ):
        conversation = (
            self.conversation(
                subject=(
                    "Commercial accountability"
                )
            )
        )

        message = self.message(
            direction="inbound",
            sender=(
                "customer@example.com"
            ),
            recipients=(
                self.user.email
            ),
            conversation=conversation,
            subject=(
                "Commercial accountability"
            ),
        )

        ActionItem.objects.create(
            user=self.user,
            organization=(
                self.organization
            ),
            message=message,
            title=(
                "Send revised proposal"
            ),
            description=(
                "Send revised commercial proposal."
            ),
            owner=self.user,
            status="open",
            source_type="email",
            confidence_score=90,
        )

        ExpectedResponseItem.objects.create(
            user=self.user,
            organization=(
                self.organization
            ),
            conversation=conversation,
            source_message=message,
            expected_from=(
                "customer@example.com"
            ),
            evidence_text=(
                "Relationship communication."
            ),
            status="waiting",
        )

        ApprovalItem.objects.create(
            user=self.user,
            organization=(
                self.organization
            ),
            message=message,
            conversation=conversation,
            title=(
                "Commercial exception"
            ),
            description=(
                "Approve commercial exception."
            ),
            requested_by=(
                "customer@example.com"
            ),
            assigned_to=self.user,
            status="approved",
            source_type="email",
            confidence_score=90,
            decision_notes=(
                "Approved."
            ),
            decision_by=self.user,
            decision_at=self.base_time,
        )

        payload = self.profile(
            "customer@example.com"
        )

        profile = (
            payload[
                "profile"
            ]
        )

        self.assertEqual(
            profile[
                "pending_commitments"
            ],
            2,
        )

        self.assertEqual(
            profile[
                "we_owe_them_pending"
            ],
            1,
        )

        self.assertEqual(
            profile[
                "they_owe_us_pending"
            ],
            1,
        )

        self.assertEqual(
            profile[
                "active_waits"
            ],
            1,
        )

        self.assertEqual(
            profile[
                "decisions"
            ],
            1,
        )

        self.assertEqual(
            profile[
                "approved_decisions"
            ],
            1,
        )

        self.assertEqual(
            len(
                payload[
                    "commitments"
                ]
            ),
            2,
        )

        self.assertEqual(
            len(
                payload[
                    "waiting_for"
                ]
            ),
            1,
        )

        self.assertEqual(
            len(
                payload[
                    "decisions"
                ]
            ),
            1,
        )

    def test_recent_communications_are_newest_first(
        self,
    ):
        conversation = (
            self.conversation()
        )

        older = self.message(
            direction="inbound",
            sender=(
                "contact@example.com"
            ),
            recipients=(
                self.user.email
            ),
            conversation=conversation,
            subject="Older",
            received_at=(
                self.base_time
            ),
        )

        newer = self.message(
            direction="outbound",
            sender=(
                self.user.email
            ),
            recipients=(
                "contact@example.com"
            ),
            conversation=conversation,
            subject="Newer",
            received_at=(
                self.base_time
                + timedelta(hours=2)
            ),
        )

        payload = self.profile(
            "contact@example.com"
        )

        recent = (
            payload[
                "recent_communications"
            ]
        )

        self.assertEqual(
            [
                item[
                    "message_id"
                ]
                for item
                in recent
            ],
            [
                newer.id,
                older.id,
            ],
        )

        self.assertEqual(
            payload[
                "profile"
            ][
                "last_interaction_at"
            ],
            newer.received_at,
        )

    def test_open_url_uses_latest_conversation(
        self,
    ):
        message = self.message(
            direction="inbound",
            sender=(
                "contact@example.com"
            ),
            recipients=(
                self.user.email
            ),
        )

        payload = self.profile(
            "contact@example.com"
        )

        self.assertEqual(
            payload[
                "profile"
            ][
                "open_url"
            ],
            (
                "/inbox?conversation="
                f"{message.conversation_id}"
            ),
        )

    def test_other_organization_is_isolated(
        self,
    ):
        self.message(
            direction="inbound",
            sender=(
                "other-contact@example.com"
            ),
            recipients=(
                self.other_user.email
            ),
            organization=(
                self.other_organization
            ),
            user=self.other_user,
        )

        payload = (
            RelationshipProfilesService
            .build_index(
                organization=(
                    self.organization
                )
            )
        )

        self.assertEqual(
            payload[
                "profiles"
            ],
            [],
        )

    def test_index_summary_counts_profiles(
        self,
    ):
        self.message(
            direction="inbound",
            sender=(
                "active@example.com"
            ),
            recipients=(
                self.user.email
            ),
        )

        Person.objects.create(
            organization=(
                self.organization
            ),
            email=(
                "known@example.com"
            ),
            is_internal=False,
        )

        payload = (
            RelationshipProfilesService
            .build_index(
                organization=(
                    self.organization
                )
            )
        )

        self.assertEqual(
            payload[
                "summary"
            ][
                "total_profiles"
            ],
            2,
        )

        self.assertEqual(
            payload[
                "summary"
            ][
                "with_communication_history"
            ],
            1,
        )

    def test_unknown_profile_returns_none(
        self,
    ):
        payload = (
            RelationshipProfilesService
            .build_profile(
                organization=(
                    self.organization
                ),
                email=(
                    "missing@example.com"
                ),
            )
        )

        self.assertIsNone(
            payload
        )


class RelationshipProfilesAPITests(
    TestCase
):

    def setUp(self):
        self.client = APIClient()

        self.user = (
            User.objects.create_user(
                email=(
                    "relationship-api@oneuch.test"
                ),
                password="pass123",
            )
        )

        self.organization = (
            Organization.objects.create(
                name=(
                    "Relationship API Org"
                ),
                slug=(
                    "relationship-api-org"
                ),
            )
        )

        OrganizationUser.objects.create(
            user=self.user,
            organization=(
                self.organization
            ),
            role="member",
        )

        Person.objects.create(
            organization=(
                self.organization
            ),
            email=(
                "customer@example.com"
            ),
            full_name=(
                "Customer Contact"
            ),
            is_internal=False,
        )

    def test_api_requires_authentication(
        self,
    ):
        response = self.client.get(
            "/api/knowledge/relationships/"
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
                    "relationship-outsider@oneuch.test"
                ),
                password="pass123",
            )
        )

        self.client.force_authenticate(
            user=outsider
        )

        response = self.client.get(
            "/api/knowledge/relationships/"
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
            "/api/knowledge/relationships/"
        )

        self.assertEqual(
            response.status_code,
            403,
        )

    def test_api_returns_relationship_index(
        self,
    ):
        self.client.force_authenticate(
            user=self.user
        )

        response = self.client.get(
            "/api/knowledge/relationships/"
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
                "total_profiles"
            ],
            1,
        )

        self.assertEqual(
            response.data[
                "profiles"
            ][0][
                "email"
            ],
            "customer@example.com",
        )

    def test_api_returns_one_profile_by_email(
        self,
    ):
        self.client.force_authenticate(
            user=self.user
        )

        response = self.client.get(
            (
                "/api/knowledge/"
                "relationships/"
                "?email=customer@example.com"
            )
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(
            response.data[
                "profile"
            ][
                "email"
            ],
            "customer@example.com",
        )

    def test_api_unknown_profile_is_404(
        self,
    ):
        self.client.force_authenticate(
            user=self.user
        )

        response = self.client.get(
            (
                "/api/knowledge/"
                "relationships/"
                "?email=missing@example.com"
            )
        )

        self.assertEqual(
            response.status_code,
            404,
        )
