from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class AIRequest:
    """
    Provider-independent request contract.

    Workflow services and future AI consumers should create this
    object instead of passing provider-specific dictionaries.
    """

    prompt: str

    system_prompt: Optional[str] = None

    provider: Optional[str] = None
    model: Optional[str] = None

    temperature: float = 0.0
    max_tokens: Optional[int] = 1000

    response_type: str = "text"

    response_schema: Optional[Dict[str, Any]] = None

    variables: Dict[str, Any] = field(
        default_factory=dict
    )

    context: Dict[str, Any] = field(
        default_factory=dict
    )

    metadata: Dict[str, Any] = field(
        default_factory=dict
    )

@dataclass
class AIResult:

    success: bool

    output: Any = None

    provider: Optional[str] = None
    model: Optional[str] = "default"

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0

    # Enterprise fields
    execution_time_ms: int = 0
    cost: float = 0.0

    # Backward compatibility
    confidence: float = 1.0

    metadata: Dict[str, Any] = field(default_factory=dict)

    error: Optional[str] = None

    @property
    def execution_time(self):
        """
        Backward compatibility with older workflow executor.
        Returns execution time in seconds.
        """
        return self.execution_time_ms / 1000

    @property
    def failed(self):
        return not self.success

    @property
    def has_usage(self):
        return self.total_tokens > 0

    @property
    def execution_time_seconds(self):
        return self.execution_time_ms / 1000