"""
Backward compatibility.

Existing modules may still import AIRequest/AIResult
from workflow.services.ai.models.

The canonical definitions live in contracts.py.
"""

from workflow.services.ai.contracts import (
    AIRequest,
    AIResult,
)

__all__ = [
    "AIRequest",
    "AIResult",
]