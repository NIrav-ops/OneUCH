from platform_core.jobs.repository import JobRepository


class JobExecutor:

    def execute(self, job):

        JobRepository.save(job)

        return True