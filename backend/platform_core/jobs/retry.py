class RetryPolicy:

    MAX_RETRIES = 3

    @classmethod
    def should_retry(cls, job):

        return job.retries < cls.MAX_RETRIES