from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class NodeExecutionOutcome:
    """
    Immutable execution result returned by every workflow executor.
    """

    CONTINUE = "continue"
    WAIT = "wait"
    SUSPEND = "suspend"
    FAILED = "failed"
    RETRY = "retry"

    status: str

    reason: Optional[str] = None

    metadata: Optional[dict] = None

    @property
    def should_continue(self):

        return self.status == self.CONTINUE

    @property
    def should_wait(self):

        return self.status == self.WAIT

    @property
    def should_suspend(self):

        return self.status == self.SUSPEND

    @property
    def failed(self):

        return self.status == self.FAILED

    @property
    def retry(self):

        return self.status == self.RETRY