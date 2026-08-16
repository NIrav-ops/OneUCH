from django.utils import timezone


class WorkflowScheduler:

    """
    Determines whether a waiting token
    is ready to resume.
    """

    def is_ready(self, token):

        if token.wait_until is None:
            return True

        return timezone.now() >= token.wait_until