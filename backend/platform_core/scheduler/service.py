from platform_core.scheduler.repository import (
    ScheduleRepository,
)

from platform_core.scheduler.engine import (
    SchedulerEngine,
)


class SchedulerService:

    def register(
        self,
        schedule,
    ):

        ScheduleRepository.save(
            schedule,
        )

    def run_all(
        self,
    ):

        engine = SchedulerEngine()

        for schedule in ScheduleRepository.all():

            engine.run(
                schedule,
            )