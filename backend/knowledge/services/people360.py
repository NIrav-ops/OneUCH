"""
Enterprise People360 Service
"""

from knowledge.services.person_timeline import (
    PersonTimelineService,
)

from knowledge.services.person_metrics import (
    PersonMetricsService,
)

from knowledge.services.person_health import (
    PersonHealthService,
)


class People360Service:
    """
    Enterprise Person 360 Profile.
    """

    def __init__(self):

        self.timeline = (
            PersonTimelineService()
        )

        self.metrics = (
            PersonMetricsService()
        )

        self.health = (
            PersonHealthService()
        )

    def build(
        self,
        *,
        person,
    ):

        timeline = self.timeline.build(
            person=person,
        )

        metrics = self.metrics.build(
            person=person,
        )

        health = self.health.build(
            metrics=metrics,
            timeline=timeline,
        )

        return {

            "person": {
                "id": person.id,
                "email": person.email,
                "full_name": person.full_name,
                "company": person.company,
                "job_title": person.job_title,
                "is_internal": person.is_internal,
            },

            "timeline": timeline,

            "metrics": metrics,

            "health": health,

        }