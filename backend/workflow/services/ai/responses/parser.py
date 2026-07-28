from workflow.services.ai.contracts import (
    AIRequest,
    AIResult,
)

from workflow.services.ai.exceptions import (
    AIResponseParsingError,
)

from workflow.services.ai.responses.contracts import (
    AIClassification,
    AISummary,
    AIDecision,
    AIActionRecommendation,
    AIActionList,
    AIApprovalRecommendation,
)


class AIResponseParser:
    """
    Converts validated provider-independent AI output into
    immutable enterprise response contracts.

    The parser does not execute business operations.
    """

    @classmethod
    def parse(
        cls,
        request: AIRequest,
        result: AIResult,
    ):

        if not result.success:
            raise AIResponseParsingError(
                "Cannot parse a failed AI result."
            )

        parsers = {
            "classification":
                cls._parse_classification,

            "summary":
                cls._parse_summary,

            "decision":
                cls._parse_decision,

            "action_list":
                cls._parse_action_list,

            "approval_recommendation":
                cls._parse_approval_recommendation,
        }

        parser = parsers.get(
            request.response_type
        )

        # Primitive response types remain primitive.
        if parser is None:

            if request.response_type in {
                "text",
                "json",
                "boolean",
                "number",
            }:
                return result.output

            raise AIResponseParsingError(
                "No response parser registered for "
                f"'{request.response_type}'."
            )

        try:
            return parser(
                result.output
            )

        except AIResponseParsingError:
            raise

        except (
            TypeError,
            ValueError,
            KeyError,
        ) as exc:

            raise AIResponseParsingError(
                "Unable to parse AI response "
                f"for '{request.response_type}': "
                f"{exc}"
            ) from exc

    @staticmethod
    def _parse_classification(
        output,
    ):

        return AIClassification(
            label=output["label"],
            confidence=float(
                output.get(
                    "confidence",
                    1.0,
                )
            ),
            reasoning=output.get(
                "reasoning"
            ),
            metadata=output.get(
                "metadata",
                {},
            ),
        )

    @staticmethod
    def _parse_summary(
        output,
    ):

        key_points = output.get(
            "key_points",
            [],
        )

        if not isinstance(
            key_points,
            list,
        ):
            raise AIResponseParsingError(
                "summary.key_points must be a list."
            )

        return AISummary(
            summary=output["summary"],
            key_points=key_points,
            metadata=output.get(
                "metadata",
                {},
            ),
        )

    @staticmethod
    def _parse_decision(
        output,
    ):

        return AIDecision(
            decision=output["decision"],
            confidence=float(
                output.get(
                    "confidence",
                    1.0,
                )
            ),
            reasoning=output.get(
                "reasoning"
            ),
            metadata=output.get(
                "metadata",
                {},
            ),
        )

    @staticmethod
    def _parse_action_list(
        output,
    ):

        actions = []

        for item in output[
            "actions"
        ]:

            actions.append(
                AIActionRecommendation(
                    title=item["title"],
                    description=item.get(
                        "description",
                        "",
                    ),
                    priority=int(
                        item.get(
                            "priority",
                            0,
                        )
                    ),
                    owner_reference=item.get(
                        "owner_reference"
                    ),
                    due_date=item.get(
                        "due_date"
                    ),
                    confidence=float(
                        item.get(
                            "confidence",
                            1.0,
                        )
                    ),
                    metadata=item.get(
                        "metadata",
                        {},
                    ),
                )
            )

        return AIActionList(
            actions=actions,
            metadata=output.get(
                "metadata",
                {},
            ),
        )

    @staticmethod
    def _parse_approval_recommendation(
        output,
    ):

        return AIApprovalRecommendation(
            recommendation=output[
                "recommendation"
            ],
            confidence=float(
                output.get(
                    "confidence",
                    1.0,
                )
            ),
            reasoning=output.get(
                "reasoning"
            ),
            metadata=output.get(
                "metadata",
                {},
            ),
        )