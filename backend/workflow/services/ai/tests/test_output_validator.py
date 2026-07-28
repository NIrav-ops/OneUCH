from django.test import SimpleTestCase

from workflow.services.ai.contracts import (
    AIRequest,
    AIResult,
)

from workflow.services.ai.output_validator import (
    AIOutputValidator,
)

from workflow.services.ai.exceptions import (
    AIOutputValidationError,
)


class AIOutputValidatorTests(
    SimpleTestCase
):

    def _validate(
        self,
        response_type,
        output,
        response_schema=None,
    ):

        request = AIRequest(
            prompt="Test",
            response_type=response_type,
            response_schema=response_schema,
        )

        result = AIResult(
            success=True,
            output=output,
            provider="mock",
        )

        return AIOutputValidator.validate(
            request,
            result,
        )

    def test_text(self):

        self.assertTrue(
            self._validate(
                "text",
                "Hello",
            )
        )

    def test_invalid_text(self):

        with self.assertRaises(
            AIOutputValidationError
        ):
            self._validate(
                "text",
                {"text": "Hello"},
            )

    def test_json(self):

        self.assertTrue(
            self._validate(
                "json",
                {
                    "value": 1,
                },
            )
        )

    def test_boolean(self):

        self.assertTrue(
            self._validate(
                "boolean",
                True,
            )
        )

    def test_invalid_boolean(self):

        with self.assertRaises(
            AIOutputValidationError
        ):
            self._validate(
                "boolean",
                "true",
            )

    def test_number(self):

        self.assertTrue(
            self._validate(
                "number",
                42,
            )
        )

    def test_boolean_not_accepted_as_number(
        self,
    ):

        with self.assertRaises(
            AIOutputValidationError
        ):
            self._validate(
                "number",
                True,
            )

    def test_classification(self):

        self.assertTrue(
            self._validate(
                "classification",
                {
                    "label": "finance",
                    "confidence": 0.95,
                },
            )
        )

    def test_invalid_classification_confidence(
        self,
    ):

        with self.assertRaises(
            AIOutputValidationError
        ):
            self._validate(
                "classification",
                {
                    "label": "finance",
                    "confidence": 1.5,
                },
            )

    def test_summary(self):

        self.assertTrue(
            self._validate(
                "summary",
                {
                    "summary":
                        "Communication summary",
                },
            )
        )

    def test_decision(self):

        self.assertTrue(
            self._validate(
                "decision",
                {
                    "decision":
                        "review_required",
                },
            )
        )

    def test_action_list(self):

        self.assertTrue(
            self._validate(
                "action_list",
                {
                    "actions": [
                        {
                            "title":
                                "Review invoice"
                        }
                    ],
                },
            )
        )

    def test_invalid_action_list(self):

        with self.assertRaises(
            AIOutputValidationError
        ):
            self._validate(
                "action_list",
                {
                    "actions":
                        "Review invoice"
                },
            )

    def test_approval_recommendation(
        self,
    ):

        self.assertTrue(
            self._validate(
                "approval_recommendation",
                {
                    "recommendation":
                        "approve"
                },
            )
        )

    def test_required_schema_fields(
        self,
    ):

        self.assertTrue(
            self._validate(
                "json",
                {
                    "decision": "approve",
                    "reason": "Within policy",
                },
                response_schema={
                    "required": [
                        "decision",
                        "reason",
                    ]
                },
            )
        )

    def test_missing_required_schema_field(
        self,
    ):

        with self.assertRaises(
            AIOutputValidationError
        ):
            self._validate(
                "json",
                {
                    "decision":
                        "approve",
                },
                response_schema={
                    "required": [
                        "decision",
                        "reason",
                    ]
                },
            )