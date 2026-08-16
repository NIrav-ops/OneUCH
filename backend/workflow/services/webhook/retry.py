import time


class RetryPolicy:

    def execute(
        self,
        callback,
        retries=3,
        delay=1,
    ):

        last_exception = None

        for attempt in range(retries):

            try:

                return callback()

            except Exception as exc:

                last_exception = exc

                if attempt < retries - 1:

                    time.sleep(delay)

        raise last_exception