class DeadLetterQueue:

    _jobs = []

    @classmethod
    def add(cls, job):

        cls._jobs.append(job)

    @classmethod
    def all(cls):

        return list(cls._jobs)

    @classmethod
    def clear(cls):

        cls._jobs.clear()

    @classmethod
    def count(cls):

        return len(cls._jobs)