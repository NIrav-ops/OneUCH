from django.contrib.auth import (
    get_user_model,
)

from django.test import (
    TestCase,
)

from django.utils import (
    timezone,
)

from inbox.models import (
    Organization,
    OrganizationUser,
    RecipientContact,
)

from context.models import (
    BusinessObject,
    BusinessObjectType,
    Person,
)

from context.services.communication_identity_bootstrap import (
    bootstrap_communication_identities,
    build_communication_identity_plan,
)

from knowledge.models import (
    BusinessIdentity,
)


User = get_user_model()


class CommunicationIdentityBootstrapTests(
    TestCase
):

    def setUp(self):
        self.user = (
            User.objects.create_user(
                email="identity-owner@oneuch.test",
                password="pass123",
            )
        )

        self.organization = (
            Organization.objects.create(
                name="Identity Bootstrap Org",
                slug="identity-bootstrap-org",
            )
        )

        OrganizationUser.objects.create(
            user=self.user,
            organization=self.organization,
            role="owner",
        )

    def contact(
        self,
        email,
        *,
        name="",
        message_count=1,
        sent_count=0,
        received_count=1,
    ):
        now = timezone.now()

        return RecipientContact.objects.create(
            user=self.user,
            organization=self.organization,
            email=email,
            normalized_email=email.lower(),
            display_name=name,
            first_seen_at=now,
            last_seen_at=now,
            message_count=message_count,
            sent_count=sent_count,
            received_count=received_count,
        )

    def test_machine_contact_is_not_person_candidate(self):
        self.contact(
            "no-reply@alpha.example",
            message_count=10,
            received_count=10,
        )

        self.contact(
            "alice@alpha.example",
            name="Alice",
            message_count=2,
            sent_count=1,
            received_count=1,
        )

        plan = (
            build_communication_identity_plan(
                user=self.user
            )
        )

        self.assertEqual(
            plan["summary"]["human_contacts"],
            1,
        )

        self.assertEqual(
            plan["summary"]["machine_contacts"],
            1,
        )

    def test_rule_a_qualifies_repeat_domain_with_sent_mail(self):
        self.contact(
            "alice@alpha.example",
            message_count=2,
            sent_count=1,
            received_count=1,
        )

        plan = (
            build_communication_identity_plan(
                user=self.user
            )
        )

        self.assertIn(
            "alpha.example",
            plan["qualified_domains"],
        )

        self.assertIn(
            "A_SENT_AND_REPEAT",
            plan[
                "qualification_rules"
            ][
                "alpha.example"
            ],
        )

    def test_rule_b_qualifies_multi_human_inbound_domain(self):
        self.contact(
            "alice@alpha.example",
            message_count=3,
            received_count=3,
        )

        self.contact(
            "bob@alpha.example",
            message_count=2,
            received_count=2,
        )

        plan = (
            build_communication_identity_plan(
                user=self.user
            )
        )

        self.assertIn(
            "alpha.example",
            plan["qualified_domains"],
        )

        self.assertIn(
            "B_MULTI_HUMAN_AND_VOLUME",
            plan[
                "qualification_rules"
            ][
                "alpha.example"
            ],
        )

    def test_single_human_domain_below_volume_does_not_qualify(self):
        self.contact(
            "person@newsletter.example",
            message_count=4,
            sent_count=0,
            received_count=4,
        )

        plan = (
            build_communication_identity_plan(
                user=self.user
            )
        )

        self.assertNotIn(
            "newsletter.example",
            plan["qualified_domains"],
        )


    def test_rule_c_qualifies_single_human_high_volume_domain(self):
        self.contact(
            "person@customer.example",
            message_count=5,
            sent_count=0,
            received_count=5,
        )

        plan = (
            build_communication_identity_plan(
                user=self.user
            )
        )

        self.assertIn(
            "customer.example",
            plan["qualified_domains"],
        )

        self.assertIn(
            "C_HUMAN_AND_VOLUME",
            plan[
                "qualification_rules"
            ][
                "customer.example"
            ],
        )

    def test_consumer_domain_never_qualifies_as_company(self):
        self.contact(
            "customer@gmail.com",
            message_count=20,
            sent_count=10,
            received_count=10,
        )

        plan = (
            build_communication_identity_plan(
                user=self.user
            )
        )

        self.assertNotIn(
            "gmail.com",
            plan["qualified_domains"],
        )

        self.assertEqual(
            plan["summary"]["human_contacts"],
            1,
        )

    def test_bootstrap_is_idempotent_and_governed(self):
        self.contact(
            "alice@alpha.example",
            name="Alice Example",
            message_count=3,
            received_count=3,
        )

        self.contact(
            "bob@alpha.example",
            name="Bob Example",
            message_count=2,
            received_count=2,
        )

        self.contact(
            "no-reply@alpha.example",
            message_count=10,
            received_count=10,
        )

        self.contact(
            "customer@gmail.com",
            name="Consumer Person",
            message_count=4,
            sent_count=2,
            received_count=2,
        )

        self.contact(
            "solo@solo.example",
            name="Solo Contact",
            message_count=4,
            received_count=4,
        )

        first = (
            bootstrap_communication_identities(
                user=self.user
            )
        )

        self.assertEqual(
            first["people_created"],
            4,
        )

        self.assertEqual(
            first["business_objects_created"],
            1,
        )

        self.assertEqual(
            first["domain_identities_created"],
            1,
        )

        self.assertEqual(
            first["email_identities_created"],
            2,
        )

        self.assertEqual(
            Person.objects.count(),
            4,
        )

        self.assertFalse(
            Person.objects.filter(
                email="no-reply@alpha.example"
            ).exists()
        )

        company = (
            BusinessObject.objects.get()
        )

        self.assertEqual(
            company.name,
            "alpha.example",
        )

        self.assertEqual(
            company.object_type.code,
            "COMPANY",
        )

        self.assertEqual(
            company.metadata[
                "identity_bootstrap"
            ][
                "lifecycle"
            ],
            "DISCOVERED",
        )

        identities = (
            BusinessIdentity.objects
            .filter(
                business_object=company
            )
        )

        self.assertEqual(
            identities.count(),
            3,
        )

        self.assertEqual(
            identities.filter(
                identity_type="DOMAIN"
            ).count(),
            1,
        )

        self.assertEqual(
            identities.filter(
                identity_type="EMAIL"
            ).count(),
            2,
        )

        self.assertEqual(
            identities.filter(
                lifecycle="DISCOVERED"
            ).count(),
            3,
        )

        alice = (
            Person.objects.get(
                email="alice@alpha.example"
            )
        )

        consumer = (
            Person.objects.get(
                email="customer@gmail.com"
            )
        )

        solo = (
            Person.objects.get(
                email="solo@solo.example"
            )
        )

        self.assertEqual(
            alice.company,
            "alpha.example",
        )

        self.assertEqual(
            consumer.company,
            "",
        )

        self.assertEqual(
            solo.company,
            "",
        )

        second = (
            bootstrap_communication_identities(
                user=self.user
            )
        )

        self.assertEqual(
            second["people_created"],
            0,
        )

        self.assertEqual(
            second["business_objects_created"],
            0,
        )

        self.assertEqual(
            second["domain_identities_created"],
            0,
        )

        self.assertEqual(
            second["email_identities_created"],
            0,
        )

        self.assertEqual(
            Person.objects.count(),
            4,
        )

        self.assertEqual(
            BusinessObject.objects.count(),
            1,
        )

        self.assertEqual(
            BusinessIdentity.objects.count(),
            3,
        )

    def test_bootstrap_is_tenant_scoped(self):
        self.contact(
            "alice@alpha.example",
            message_count=2,
            sent_count=1,
            received_count=1,
        )

        other_user = (
            User.objects.create_user(
                email="other-owner@oneuch.test",
                password="pass123",
            )
        )

        other_org = (
            Organization.objects.create(
                name="Other Org",
                slug="other-bootstrap-org",
            )
        )

        OrganizationUser.objects.create(
            user=other_user,
            organization=other_org,
            role="owner",
        )

        now = timezone.now()

        RecipientContact.objects.create(
            user=other_user,
            organization=other_org,
            email="private@other.example",
            normalized_email="private@other.example",
            display_name="Private",
            first_seen_at=now,
            last_seen_at=now,
            message_count=10,
            sent_count=5,
            received_count=5,
        )

        bootstrap_communication_identities(
            user=self.user
        )

        self.assertFalse(
            Person.objects.filter(
                organization=other_org
            ).exists()
        )

        self.assertFalse(
            BusinessObject.objects.filter(
                organization=other_org
            ).exists()
        )

    def test_company_type_is_system_type(self):
        self.contact(
            "alice@alpha.example",
            message_count=2,
            sent_count=1,
            received_count=1,
        )

        bootstrap_communication_identities(
            user=self.user
        )

        company_type = (
            BusinessObjectType.objects.get(
                code="COMPANY"
            )
        )

        self.assertEqual(
            company_type.name,
            "Company",
        )

        self.assertTrue(
            company_type.is_system
        )

        self.assertTrue(
            company_type.is_active
        )
