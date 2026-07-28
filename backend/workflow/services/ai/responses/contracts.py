from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class AIClassification:
    """
    Typed classification produced by AI.

    This is advisory output only. It does not directly trigger
    workflow execution.
    """

    label: str
    confidence: float = 1.0
    reasoning: Optional[str] = None
    metadata: Dict[str, Any] = field(
        default_factory=dict
    )


@dataclass(frozen=True)
class AISummary:
    """
    Typed summary generated from enterprise communication/context.
    """

    summary: str
    key_points: List[str] = field(
        default_factory=list
    )
    metadata: Dict[str, Any] = field(
        default_factory=dict
    )


@dataclass(frozen=True)
class AIDecision:
    """
    AI-generated business decision/recommendation.

    A decision is informational until a deterministic workflow
    policy explicitly acts on it.
    """

    decision: str
    confidence: float = 1.0
    reasoning: Optional[str] = None
    metadata: Dict[str, Any] = field(
        default_factory=dict
    )


@dataclass(frozen=True)
class AIActionRecommendation:
    """
    A proposed action identified by AI.

    This object is NOT an ActionItem and must not directly write
    to the actions application.
    """

    title: str
    description: str = ""

    priority: int = 0

    owner_reference: Optional[str] = None
    due_date: Optional[str] = None

    confidence: float = 1.0

    metadata: Dict[str, Any] = field(
        default_factory=dict
    )


@dataclass(frozen=True)
class AIActionList:
    """
    Collection of AI-generated action recommendations.
    """

    actions: List[AIActionRecommendation] = field(
        default_factory=list
    )

    metadata: Dict[str, Any] = field(
        default_factory=dict
    )


@dataclass(frozen=True)
class AIApprovalRecommendation:
    """
    Advisory AI recommendation for an approval.

    It deliberately does not represent an ApprovalItem or an
    executed approval decision.
    """

    recommendation: str

    confidence: float = 1.0

    reasoning: Optional[str] = None

    metadata: Dict[str, Any] = field(
        default_factory=dict
    )