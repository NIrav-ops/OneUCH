from context.tests.base import EnterpriseBaseTestCase

from knowledge.services.communication_analytics import (
    CommunicationAnalyticsService,
)

from knowledge.services.channel_analytics import (
    ChannelAnalyticsService,
)

from knowledge.services.communication_trends import (
    CommunicationTrendService,
)

from knowledge.services.response_time_analytics import (
    ResponseTimeAnalyticsService,
)

from knowledge.services.communication_health import (
    CommunicationHealthService,
)

from inbox.models import InboxMessage
from django.utils import timezone
from datetime import timedelta


class CommunicationHealthTests(
    EnterpriseBaseTestCase,
):

    def setUp(self):

        super().setUp()

        InboxMessage.objects.create(
            user=self.user,
            organization=self.organization,
            conversation=self.conversation,
            platform="gmail",
            direction="outbound",
            external_message_id="reply1",
            sender="tester@example.com",
            recipients="john@example.com",
            subject="Reply",
            body="Reply",
            received_at=timezone.now() + timedelta(minutes=10),
        )

        self.analytics = CommunicationAnalyticsService()

        self.channels = ChannelAnalyticsService()

        self.trends = CommunicationTrendService()

        self.responses = ResponseTimeAnalyticsService()

        self.health = CommunicationHealthService()

    def test_score_exists(self):

        result = self.health.build(

            analytics=self.analytics.build(
                organization=self.organization,
            ),

            channels=self.channels.build(
                organization=self.organization,
            ),

            trends=self.trends.build(
                organization=self.organization,
            ),

            response_times=self.responses.build(
                organization=self.organization,
            ),
        )

        self.assertIn(
            "score",
            result,
        )

    def test_status(self):

        result = self.health.build(

            analytics=self.analytics.build(
                organization=self.organization,
            ),

            channels=self.channels.build(
                organization=self.organization,
            ),

            trends=self.trends.build(
                organization=self.organization,
            ),

            response_times=self.responses.build(
                organization=self.organization,
            ),
        )

        self.assertEqual(
            result["status"],
            "Healthy",
        )

    def test_score_positive(self):

        result = self.health.build(

            analytics=self.analytics.build(
                organization=self.organization,
            ),

            channels=self.channels.build(
                organization=self.organization,
            ),

            trends=self.trends.build(
                organization=self.organization,
            ),

            response_times=self.responses.build(
                organization=self.organization,
            ),
        )

        self.assertGreater(
            result["score"],
            0,
        )

    def test_reasons(self):

        result = self.health.build(

            analytics=self.analytics.build(
                organization=self.organization,
            ),

            channels=self.channels.build(
                organization=self.organization,
            ),

            trends=self.trends.build(
                organization=self.organization,
            ),

            response_times=self.responses.build(
                organization=self.organization,
            ),
        )

        self.assertGreater(
            len(result["reasons"]),
            0,
        )