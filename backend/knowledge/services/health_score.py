"""
Enterprise Health Score Service
"""


class HealthScoreService:
    """
    Calculates the health of a BusinessObject.

    Current:
        Rule-based

    Future:
        AI / ML driven
    """

    def build(
        self,
        *,
        knowledge,
        metrics,
        relationships,
    ):

        score = 0
        reasons = []

# Verified knowledge
        if knowledge["fact_count"] > 0:
            score += 30
            reasons.append("Verified knowledge available")

        # Communication evidence
        if knowledge["evidence_count"] > 0:
            score += 20
            reasons.append("Communication evidence available")

        # Enterprise graph
        if relationships["count"] > 0:
            score += 25
            reasons.append("Connected to enterprise graph")

        # Recent activity
        if metrics["total_evidence"] > 0:
            score += 25
            reasons.append("Recent communication activity")

        score = min(score, 100)

        if score >= 80:
            status = "Healthy"
        elif score >= 50:
            status = "Moderate"
        else:
            status = "At Risk"

        return {
            "score": score,
            "status": status,
            "reasons": reasons,
        }