from django.test import SimpleTestCase

from workflow.services.execution.events import (
    WorkflowExecutionEventService,
)


class WorkflowExecutionFailureSanitizationTests(
    SimpleTestCase
):

    def test_authorization_token_is_redacted(self):

        message = (
            "Authorization token SECRET-TOKEN-123"
        )

        sanitized = (
            WorkflowExecutionEventService
            .sanitize_error_message(
                message
            )
        )

        self.assertNotIn(
            "SECRET-TOKEN-123",
            sanitized,
        )

        self.assertIn(
            "[REDACTED]",
            sanitized,
        )

    def test_bearer_token_is_redacted(self):

        message = (
            "Bearer eyJhbGciOiSECRET123"
        )

        sanitized = (
            WorkflowExecutionEventService
            .sanitize_error_message(
                message
            )
        )

        self.assertNotIn(
            "eyJhbGciOiSECRET123",
            sanitized,
        )

    def test_api_key_is_redacted(self):

        message = (
            "api_key=SUPER-SECRET-123"
        )

        sanitized = (
            WorkflowExecutionEventService
            .sanitize_error_message(
                message
            )
        )

        self.assertNotIn(
            "SUPER-SECRET-123",
            sanitized,
        )

    def test_normal_operational_error_is_preserved(self):

        message = (
            "Provider unavailable"
        )

        sanitized = (
            WorkflowExecutionEventService
            .sanitize_error_message(
                message
            )
        )

        self.assertEqual(
            sanitized,
            message,
        )