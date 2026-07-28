"""
Enterprise Human Review Builder.

Transforms AI execution results and governance
decisions into immutable review contracts.

This module contains no persistence logic.
"""

from __future__ import annotations

from typing import Any
from typing import Dict

from workflow.services.ai.contracts import (
    AIRequest,
    AIResult,
)

from workflow.services.ai.governance import (
    AIGovernanceDecision,
)

from .contracts import (
    AIHumanReviewRequest,
)


class AIHumanReviewBuilder:
    """
    Factory responsible for creating enterprise
    review requests.

    A review request is generated only after
    AI Governance determines that human review
    is required.
    """

    @classmethod
    def build(
        cls,
        request: AIRequest,
        result: AIResult,
        governance: AIGovernanceDecision,
    ) -> AIHumanReviewRequest:

        return AIHumanReviewRequest(

            workflow_instance_id=request.metadata.get(
                "workflow_instance_id"
            ),

            workflow_node_id=request.metadata.get(
                "workflow_node_id"
            ),

            governance_outcome=governance.outcome,

            confidence=governance.confidence or 0.0,

            policy_name=governance.policy_name,

            reason=governance.reason or "",

            response_type=request.response_type,

            ai_output=result.output,

            metadata=cls._build_metadata(
                request=request,
                result=result,
                governance=governance,
            ),
        )

    @classmethod
    def _build_metadata(
        cls,
        request: AIRequest,
        result: AIResult,
        governance: AIGovernanceDecision,
    ) -> Dict[str, Any]:

        return {

            **(request.metadata or {}),

            "provider": result.provider,

            "model": result.model,

            "success": result.success,

            "prompt_tokens": result.prompt_tokens,

            "completion_tokens": result.completion_tokens,

            "total_tokens": result.total_tokens,

            "cost": result.cost,

            "execution_time": result.execution_time,

            "governance_policy":
                governance.policy_name,

            "governance_outcome":
                governance.outcome,

            "governance_requires_review":
                governance.requires_review,

            "governance_blocked":
                governance.blocked,
        }