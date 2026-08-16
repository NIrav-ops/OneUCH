from dataclasses import dataclass, field
from typing import Any


@dataclass
class ExecutionResult:
    """
    Standard execution result returned by all node executors.
    """

    success: bool

    outputs: dict = field(
        default_factory=dict,
    )

    message: str = ""

    metadata: dict = field(
        default_factory=dict,
    )

    next_token: bool = True

    error: Any = None