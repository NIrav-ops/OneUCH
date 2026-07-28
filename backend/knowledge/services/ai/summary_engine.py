from knowledge.services.ai.base_ai_engine import (
    BaseAIEngine,
)


class SummaryEngine(BaseAIEngine):

    provider = "rule_based"

    def summarize(
        self,
        text,
    ):

        if not text:
            return ""

        return text[:200]

    def recommend(self, context):
        return []

    def prioritize(self, context):
        return {}

    def detect_risk(self, context):
        return {}

    def detect_opportunity(self, context):
        return {}