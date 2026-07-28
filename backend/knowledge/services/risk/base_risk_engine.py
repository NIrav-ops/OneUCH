"""
Enterprise Base Risk Engine
"""


class BaseRiskEngine:
    """
    Base class for every enterprise
    risk engine.
    """

    category = "base"

    def build(
        self,
        **kwargs,
    ):
        raise NotImplementedError