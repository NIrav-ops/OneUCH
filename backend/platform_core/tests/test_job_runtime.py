from django.test import TestCase

from platform_core.jobs.job import BackgroundJob
from platform_core.jobs.queue import JobQueue
from platform_core.jobs.repository import JobRepository
from platform_core.jobs.service import JobService


class JobRuntimeTests(TestCase):

    def tearDown(self):

        JobQueue.clear()
        JobRepository.clear()

    def test_submit_job(self):

        job = BackgroundJob(
            id="1",
            name="sync",
            payload={},
        )

        JobService().submit(job)

        self.assertEqual(
            JobQueue.size(),
            1,
        )

    def test_process_job(self):

        job = BackgroundJob(
            id="1",
            name="sync",
            payload={},
        )

        service = JobService()

        service.submit(job)

        service.process()

        self.assertEqual(
            JobRepository.count(),
            1,
        )

    def test_queue_empty(self):

        self.assertEqual(
            JobQueue.size(),
            0,
        )

    def test_repository_empty(self):

        self.assertEqual(
            JobRepository.count(),
            0,
        )