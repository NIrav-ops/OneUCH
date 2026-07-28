from django.test import SimpleTestCase

from workflow.services.ai.contracts import (
    AIRequest,
    AIResult,
)

from workflow.services.ai.exceptions import (
    AIResponseParsingError,
)

from workflow.services.ai.responses import (
    AIResponseParser,
    AIClassification,
    AISummary,
    AIDecision,
    AIActionList,
    AIApprovalRecommendation,
)


class AIResponseParserTests(
    SimpleTestCase
):

    def _parse(
        self,
        response_type,
        output,
    ):

        request = AIRequest(
            prompt="Test",
            response_type=response_type,
        )

        result = AIResult(
            success=True,
            output=output,
            provider="mock",
        )

        return AIResponseParser.parse(
            request,
            result,
        )

    def test_parse_text(self):

        result = self._parse(
            "text",
            "Hello",
        )

        self.assertEqual(
            result,
            "Hello",
        )

    def test_parse_classification(self):

        result = self._parse(
            "classification",
            {
                "label": "finance",
                "confidence": 0.95,
                "reasoning":
                    "Invoice detected",
            },
        )

        self.assertIsInstance(
            result,
            AIClassification,
        )

        self.assertEqual(
            result.label,
            "finance",
        )

    def test_parse_summary(self):

        result = self._parse(
            "summary",
            {
                "summary":
                    "Invoice requires review.",
                "key_points": [
                    "Payment requested",
                ],
            },
        )

        self.assertIsInstance(
            result,
            AISummary,
        )

    def test_parse_decision(self):

        result = self._parse(
            "decision",
            {
                "decision":
                    "review_required",
                "confidence": 0.8,
            },
        )

        self.assertIsInstance(
            result,
            AIDecision,
        )

    def test_parse_action_list(self):

        result = self._parse(
            "action_list",
            {
                "actions": [
                    {
                        "title":
                            "Review invoice",
                        "description":
                            "Validate amount",
                        "priority": 80,
                        "confidence": 0.9,
                    }
                ]
            },
        )

        self.assertIsInstance(
            result,
            AIActionList,
        )

        self.assertEqual(
            len(result.actions),
            1,
        )

        self.assertEqual(
            result.actions[0].title,
            "Review invoice",
        )

    def test_parse_approval_recommendation(
        self,
    ):

        result = self._parse(
            "approval_recommendation",
            {
                "recommendation":
                    "review",
                "confidence": 0.75,
                "reasoning":
                    "Policy check required",
            },
        )

        self.assertIsInstance(
            result,
            AIApprovalRecommendation,
        )

    def test_failed_result_rejected(self):

        request = AIRequest(
            prompt="Test",
            response_type="summary",
        )

        result = AIResult(
            success=False,
            output=None,
            provider="mock",
            error="Provider failure",
        )

        with self.assertRaises(
            AIResponseParsingError
        ):
            AIResponseParser.parse(
                request,
                result,
            )

    def test_invalid_summary_key_points_rejected(
        self,
    ):

        with self.assertRaises(
            AIResponseParsingError
        ):
            self._parse(
                "summary",
                {
                    "summary": "Test",
                    "key_points":
                        "not-a-list",
                },
            )

    def test_parser_does_not_create_business_objects(
        self,
    ):

        result = self._parse(
            "action_list",
            {
                "actions": [
                    {
                        "title":
                            "Approve payment",
                    }
                ]
            },
        )

        self.assertIsInstance(
            result,
            AIActionList,
        )

        self.assertFalse(
            hasattr(
                result.actions[0],
                "save",
            )
        )