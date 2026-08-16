from workflow.services.runtime_state import (
    RuntimeState,
)


class RuntimeController:

    def __init__(self):

        self.state = RuntimeState.CREATED

    def start(self):

        self.state = RuntimeState.RUNNING

    def wait(self):

        self.state = RuntimeState.WAITING

    def suspend(self):

        self.state = RuntimeState.SUSPENDED

    def complete(self):

        self.state = RuntimeState.COMPLETED

    def fail(self):

        self.state = RuntimeState.FAILED

    def cancel(self):

        self.state = RuntimeState.CANCELLED

    @property
    def is_running(self):

        return self.state == RuntimeState.RUNNING

    @property
    def is_waiting(self):

        return self.state == RuntimeState.WAITING

    @property
    def is_suspended(self):

        return self.state == RuntimeState.SUSPENDED

    @property
    def is_failed(self):

        return self.state == RuntimeState.FAILED

    @property
    def is_completed(self):

        return self.state == RuntimeState.COMPLETED

    @property
    def is_cancelled(self):

        return self.state == RuntimeState.CANCELLED