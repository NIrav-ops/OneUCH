from platform_core.scheduler.service import (
    SchedulerService,
)


class SchedulerRunner:

    def run(self):

        SchedulerService().run_all()