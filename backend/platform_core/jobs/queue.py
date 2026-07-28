from collections import deque


class JobQueue:

    _queue = deque()

    @classmethod
    def push(cls, job):

        cls._queue.append(job)

    @classmethod
    def pop(cls):

        if cls._queue:

            return cls._queue.popleft()

        return None

    @classmethod
    def size(cls):

        return len(cls._queue)

    @classmethod
    def clear(cls):

        cls._queue.clear()