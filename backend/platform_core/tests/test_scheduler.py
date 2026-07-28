from django.test import TestCase

from platform_core.scheduler.schedule import (
    Schedule,
)

from platform_core.scheduler.repository import (
    ScheduleRepository,
)

from platform_core.scheduler.service import (
    SchedulerService,
)

from platform_core.jobs.queue import (
    JobQueue,
)


class SchedulerTests(TestCase):

    def tearDown(self):

        ScheduleRepository.clear()

        JobQueue.clear()

    def test_register(self):

        schedule = Schedule(

            id="1",

            name="Daily Sync",

            interval=60,

            job_name="gmail_sync",

            payload={},

        )

        SchedulerService().register(
            schedule,
        )

        self.assertEqual(

            ScheduleRepository.count(),

            1,

        )

    def test_scheduler(self):

        schedule = Schedule(

            id="1",

            name="Daily Sync",

            interval=60,

            job_name="gmail_sync",

            payload={},

        )

        service = SchedulerService()

        service.register(
            schedule,
        )

        service.run_all()

        self.assertEqual(

            JobQueue.size(),

            1,

        )

    def test_disabled(self):

        schedule = Schedule(

            id="1",

            name="Disabled",

            interval=60,

            job_name="sync",

            payload={},

            enabled=False,

        )

        service = SchedulerService()

        service.register(
            schedule,
        )

        service.run_all()

        self.assertEqual(

            JobQueue.size(),

            0,

        )

    def test_repository_empty(self):

        self.assertEqual(

            ScheduleRepository.count(),

            0,

        )