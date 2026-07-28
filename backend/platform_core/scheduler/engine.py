import uuid

from platform_core.jobs.job import (
    BackgroundJob,
)

from platform_core.jobs.service import (
    JobService,
)


class SchedulerEngine:

    def run(
        self,
        schedule,
    ):

        if not schedule.enabled:

            return False

        job = BackgroundJob(

            id=str(
                uuid.uuid4(),
            ),

            name=schedule.job_name,

            payload=schedule.payload,

        )

        JobService().submit(
            job,
        )

        return True