from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class AIGovernancePolicy:
    """
    Immutable policy controlling how AI output may influence
    enterprise workflow execution.
    """

    allow_automation: bool = False

    minimum_confidence: float = 0.70

    automatic_execution_confidence: float = 0.90

    require_review_below: float = 0.90

    block_below: float = 0.50

    require_human_review: bool = False

    metadata: Dict[str, Any] = field(
        default_factory=dict
    )


@dataclass(frozen=True)
class AIGovernanceDecision:
    """
    Deterministic governance result.

    This object decides whether an AI result may proceed,
    requires human review, or must be blocked.
    """

    outcome: str

    allowed: bool
    requires_review: bool
    blocked: bool

    confidence: Optional[float] = None

    reason: Optional[str] = None

    policy_name: str = "default"

    metadata: Dict[str, Any] = field(
        default_factory=dict
    )

    @property
    def can_execute(self):
        return (
            self.allowed
            and not self.requires_review
            and not self.blocked
        )