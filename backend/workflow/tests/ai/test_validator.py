from django.test import SimpleTestCase

from workflow.services.ai.contracts import (
    AIRequest,
)

from workflow.services.ai.exceptions import (
    AIValidationError,
)

from workflow.services.ai.validator import (
    AIRequestValidator,
)


class AIRequestValidatorTests(SimpleTestCase):

    def test_valid_request(self):

        request = AIRequest(
            prompt="Summarize this email"
        )

        self.assertTrue(
            AIRequestValidator.validate(
                request
            )
        )

    def test_empty_prompt_rejected(self):

        request = AIRequest(
            prompt=""
        )

        with self.assertRaises(
            AIValidationError
        ):
            AIRequestValidator.validate(
                request
            )

    def test_whitespace_prompt_rejected(self):

        request = AIRequest(
            prompt="   "
        )

        with self.assertRaises(
            AIValidationError
        ):
            AIRequestValidator.validate(
                request
            )

    def test_invalid_temperature_rejected(self):

        request = AIRequest(
            prompt="Test",
            temperature=3.0,
        )

        with self.assertRaises(
            AIValidationError
        ):
            AIRequestValidator.validate(
                request
            )

    def test_invalid_max_tokens_rejected(self):

        request = AIRequest(
            prompt="Test",
            max_tokens=0,
        )

        with self.assertRaises(
            AIValidationError
        ):
            AIRequestValidator.validate(
                request
            )

    def test_invalid_response_type_rejected(self):

        request = AIRequest(
            prompt="Test",
            response_type="something_invalid",
        )

        with self.assertRaises(
            AIValidationError
        ):
            AIRequestValidator.validate(
                request
            )