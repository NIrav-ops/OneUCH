from platform_core.jobs.executor import JobExecutor
from platform_core.jobs.queue import JobQueue


class JobService:

    def submit(self, job):

        JobQueue.push(job)

    def process(self):

        executor = JobExecutor()

        while JobQueue.size():

            job = JobQueue.pop()

            executor.execute(job)