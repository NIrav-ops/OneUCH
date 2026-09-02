from django.contrib.auth import (
    get_user_model,
)

from django.test import (
    TestCase,
    override_settings,
)

from django.utils import (
    timezone,
)

from inbox.models import (
    Conversation,
    InboxMessage,
    Organization,
    OrganizationUser,
)

from context.models import (
    BusinessObject,
    BusinessObjectType,
)

from context.services.business_object_cache import (
    BusinessObjectCache,
)

from knowledge.models import (
    BusinessIdentity,
    KnowledgeEvidence,
    KnowledgeJob,
)

from knowledge.services.backfill_service import (
    KnowledgeBackfillService,
)

from knowledge.services.message_processor import (
    MessageProcessor,
)


User = get_user_model()


class KnowledgeBackfillReadinessTests(
    TestCase
):

    def setUp(
        self,
    ):

        BusinessObjectCache.clear()

        self.user = (
            User.objects.create_user(
                email=(
                    "owner@oneuch.test"
                ),
                password="pass123",
            )
        )

        self.organization = (
            Organization.objects.create(
                name="Backfill Test Org",
                slug="backfill-test-org",
            )
        )

        OrganizationUser.objects.create(
            user=self.user,
            organization=(
                self.organization
            ),
            role="owner",
        )

        self.object_type = (
            BusinessObjectType.objects.create(
                name="Company",
                code="COMPANY",
                is_system=True,
            )
        )

        self.alpha = (
            BusinessObject.objects.create(
                organization=(
                    self.organization
                ),
                object_type=(
                    self.object_type
                ),
                name="alpha.example",
                status="active",
            )
        )

        self.beta = (
            BusinessObject.objects.create(
                organization=(
                    self.organization
                ),
                object_type=(
                    self.object_type
                ),
                name="beta.example",
                status="active",
            )
        )

        for obj, domain, email in (
            (
                self.alpha,
                "alpha.example",
                "alice@alpha.example",
            ),
            (
                self.beta,
                "beta.example",
                "bob@beta.example",
            ),
        ):

            BusinessIdentity.objects.create(
                business_object=obj,
                identity_type="DOMAIN",
                value=domain,
                normalized_value=domain,
                source="discovery",
                lifecycle="DISCOVERED",
            )

            BusinessIdentity.objects.create(
                business_object=obj,
                identity_type="EMAIL",
                value=email,
                normalized_value=email,
                source="discovery",
                lifecycle="DISCOVERED",
            )

        self.conversation = (
            Conversation.objects.create(
                user=self.user,
                organization=(
                    self.organization
                ),
                conversation_key=(
                    "backfill-readiness"
                ),
                subject="Backfill",
            )
        )

        self.counter = 0

        self.processor = (
            MessageProcessor()
        )


    def tearDown(
        self,
    ):

        BusinessObjectCache.clear()

        super().tearDown()


    def message(
        self,
        *,
        direction,
        sender,
        recipients,
        subject,
        body="Body",
        is_draft=False,
    ):

        self.counter += 1

        return (
            InboxMessage.objects.create(
                user=self.user,
                organization=(
                    self.organization
                ),
                conversation=(
                    self.conversation
                ),
                platform="gmail",
                direction=direction,
                folder=(
                    "sent"
                    if direction
                    ==
                    "outbound"
                    else "inbox"
                ),
                external_message_id=(
                    "backfill-"
                    +
                    str(
                        self.counter
                    )
                ),
                sender=sender,
                recipients=recipients,
                subject=subject,
                body=body,
                received_at=(
                    timezone.now()
                ),
                is_draft=(
                    is_draft
                ),
            )
        )


    def test_outbound_single_company_resolves_from_recipient(
        self,
    ):

        message = (
            self.message(
                direction="outbound",
                sender=self.user.email,
                recipients=(
                    "alice@alpha.example"
                ),
                subject=(
                    "Outbound Alpha"
                ),
            )
        )

        result = (
            self.processor
            .resolve_message(
                organization=(
                    self.organization
                ),
                message=message,
                sender=message.sender,
                subject=message.subject,
                body=message.body,
            )
        )

        self.assertTrue(
            result[
                "matched"
            ]
        )

        self.assertFalse(
            result[
                "ambiguous"
            ]
        )

        self.assertEqual(
            result[
                "resolution_mode"
            ],
            "outbound_recipient",
        )

        self.assertEqual(
            result[
                "best_match"
            ][
                "business_object"
            ],
            self.alpha,
        )


    def test_multi_company_outbound_is_fail_closed(
        self,
    ):

        message = (
            self.message(
                direction="outbound",
                sender=self.user.email,
                recipients=(
                    "alice@alpha.example, "
                    "bob@beta.example"
                ),
                subject=(
                    "Multi-company"
                ),
            )
        )

        result = (
            self.processor
            .process_message(
                organization=(
                    self.organization
                ),
                message=message,
                sender=message.sender,
                subject=message.subject,
                body=message.body,
                source_channel="gmail",
            )
        )

        self.assertFalse(
            result[
                "matched"
            ]
        )

        self.assertTrue(
            result[
                "ambiguous"
            ]
        )

        self.assertEqual(
            KnowledgeEvidence.objects.count(),
            0,
        )


    def _build_preview_fixture(
        self,
    ):

        self.message(
            direction="inbound",
            sender="alice@alpha.example",
            recipients=self.user.email,
            subject="Inbound Alpha",
        )

        self.message(
            direction="outbound",
            sender=self.user.email,
            recipients="alice@alpha.example",
            subject="Outbound Alpha",
        )

        self.message(
            direction="inbound",
            sender="unknown@unknown.example",
            recipients=self.user.email,
            subject="Unknown",
        )

        self.message(
            direction="inbound",
            sender="alice@alpha.example",
            recipients=self.user.email,
            subject="Draft",
            is_draft=True,
        )


    def test_preview_is_read_only_and_excludes_drafts(
        self,
    ):

        self._build_preview_fixture()

        service = (
            KnowledgeBackfillService()
        )

        result = (
            service.preview(
                organization=(
                    self.organization
                ),
                user=self.user,
            )
        )

        self.assertEqual(
            result[
                "total"
            ],
            3,
        )

        self.assertEqual(
            result[
                "matched"
            ],
            2,
        )

        self.assertEqual(
            result[
                "unmatched"
            ],
            1,
        )

        self.assertEqual(
            result[
                "ambiguous"
            ],
            0,
        )

        self.assertEqual(
            result[
                "coverage_rate"
            ],
            66.67,
        )

        self.assertEqual(
            KnowledgeEvidence.objects.count(),
            0,
        )

        self.assertEqual(
            KnowledgeJob.objects.count(),
            0,
        )


    @override_settings(
        KNOWLEDGE_JOB_CHECKPOINT_INTERVAL=1
    )
    def test_real_service_checkpoint_and_metrics(
        self,
    ):

        self._build_preview_fixture()

        service = (
            KnowledgeBackfillService()
        )

        result = (
            service.process(
                organization=(
                    self.organization
                ),
                user=self.user,
            )
        )

        self.assertEqual(
            result[
                "total"
            ],
            3,
        )

        self.assertEqual(
            result[
                "processed"
            ],
            3,
        )

        self.assertEqual(
            result[
                "matched"
            ],
            2,
        )

        self.assertEqual(
            result[
                "unmatched"
            ],
            1,
        )

        self.assertEqual(
            result[
                "ambiguous"
            ],
            0,
        )

        self.assertEqual(
            result[
                "failed"
            ],
            0,
        )

        self.assertEqual(
            result[
                "coverage_rate"
            ],
            66.67,
        )

        self.assertEqual(
            result[
                "job_status"
            ],
            "COMPLETED",
        )

        self.assertEqual(
            KnowledgeEvidence.objects.count(),
            2,
        )

        job = (
            KnowledgeJob.objects.get()
        )

        self.assertEqual(
            job.status,
            "COMPLETED",
        )

        self.assertEqual(
            job.processed,
            3,
        )

        self.assertEqual(
            job.metadata[
                "matched"
            ],
            2,
        )

        self.assertEqual(
            job.metadata[
                "unmatched"
            ],
            1,
        )

        self.assertEqual(
            job.metadata[
                "coverage_rate"
            ],
            66.67,
        )
