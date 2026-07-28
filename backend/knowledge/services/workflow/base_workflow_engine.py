"""
Enterprise Workflow Foundation
"""


class BaseWorkflowEngine:
    """
    Base class for every workflow engine.

    Future engines:

    - Task Intelligence
    - Approval Intelligence
    - Follow-up Intelligence
    - Escalation Engine
    - SLA Engine
    """

    category = "base"

    def build(
        self,
        **kwargs,
    ):
        raise NotImplementedError