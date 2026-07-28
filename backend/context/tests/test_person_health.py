from context.tests.base import (
    EnterpriseBaseTestCase,
)

from context.models import Person

from knowledge.services.person_metrics import (
    PersonMetricsService,
)

from knowledge.services.person_timeline import (
    PersonTimelineService,
)

from knowledge.services.person_health import (
    PersonHealthService,
)


class PersonHealthTests(
    EnterpriseBaseTestCase,
):

    def setUp(self):

        super().setUp()

        self.person = Person.objects.create(
            organization=self.organization,
            email="john@example.com",
            full_name="John Smith",
        )

        self.evidence.person = self.person
        self.evidence.save()

        self.metrics = (
            PersonMetricsService()
        )

        self.timeline = (
            PersonTimelineService()
        )

        self.service = (
            PersonHealthService()
        )

    def test_score_exists(self):

        metrics = self.metrics.build(
            person=self.person,
        )

        timeline = self.timeline.build(
            person=self.person,
        )

        result = self.service.build(
            metrics=metrics,
            timeline=timeline,
        )

        self.assertIn(
            "score",
            result,
        )

    def test_status(self):

        metrics = self.metrics.build(
            person=self.person,
        )

        timeline = self.timeline.build(
            person=self.person,
        )

        result = self.service.build(
            metrics=metrics,
            timeline=timeline,
        )

        self.assertEqual(
            result["status"],
            "Healthy",
        )

    def test_reasons(self):

        metrics = self.metrics.build(
            person=self.person,
        )

        timeline = self.timeline.build(
            person=self.person,
        )

        result = self.service.build(
            metrics=metrics,
            timeline=timeline,
        )

        self.assertGreater(
            len(result["reasons"]),
            0,
        )

    def test_score_positive(self):

        metrics = self.metrics.build(
            person=self.person,
        )

        timeline = self.timeline.build(
            person=self.person,
        )

        result = self.service.build(
            metrics=metrics,
            timeline=timeline,
        )

        self.assertGreater(
            result["score"],
            0,
        )