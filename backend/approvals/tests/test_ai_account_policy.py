from types import SimpleNamespace

from django.test import SimpleTestCase

from approvals.services.ai_account_policy import (
    is_ai_allowed_for_message,
)


class ApprovalAIAccountPolicyTests(
    SimpleTestCase
):

    def test_allowed_account_is_enabled(
        self,
    ):
        message = SimpleNamespace(
            email_account_id=3,
        )

        self.assertTrue(
            is_ai_allowed_for_message(
                message=message,
                allowed_account_ids={
                    3,
                },
            )
        )

    def test_other_account_is_blocked(
        self,
    ):
        message = SimpleNamespace(
            email_account_id=4,
        )

        self.assertFalse(
            is_ai_allowed_for_message(
                message=message,
                allowed_account_ids={
                    3,
                },
            )
        )

    def test_empty_allowlist_blocks_ai(
        self,
    ):
        message = SimpleNamespace(
            email_account_id=3,
        )

        self.assertFalse(
            is_ai_allowed_for_message(
                message=message,
                allowed_account_ids=set(),
            )
        )

    def test_message_without_account_is_blocked(
        self,
    ):
        message = SimpleNamespace(
            email_account_id=None,
        )

        self.assertFalse(
            is_ai_allowed_for_message(
                message=message,
                allowed_account_ids={
                    3,
                },
            )
        )
