"""
Enterprise Person Health Service
"""


class PersonHealthService:
    """
    Calculates the health of a Person.
    """

    def build(
        self,
        *,
        metrics,
        timeline,
    ):

        score = 0

        reasons = []

        if metrics["total_evidence"] > 0:
            score += 50
            reasons.append(
                "Communication history available"
            )

        if len(timeline) > 0:
            score += 50
            reasons.append(
                "Timeline activity available"
            )

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