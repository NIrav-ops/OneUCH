"""
Enterprise Base Opportunity Engine
"""


class BaseOpportunityEngine:
    """
    Base class for every enterprise
    opportunity engine.
    """

    category = "base"

    def build(
        self,
        **kwargs,
    ):
        raise NotImplementedError