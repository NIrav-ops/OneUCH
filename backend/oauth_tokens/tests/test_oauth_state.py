from django.core import signing
from django.test import SimpleTestCase

from oauth_tokens.oauth_state import (
    OAuthStateError,
    create_oauth_state,
    resolve_oauth_state,
)


class OAuthStateTests(SimpleTestCase):

    def test_state_round_trip(self):
        state = create_oauth_state(
            user_id=42,
            provider="google",
        )

        result = resolve_oauth_state(
            state=state,
            provider="google",
        )

        self.assertEqual(
            result["user_id"],
            42,
        )

        self.assertEqual(
            result["provider"],
            "google",
        )

    def test_state_rejects_wrong_provider(self):
        state = create_oauth_state(
            user_id=42,
            provider="google",
        )

        with self.assertRaises(
            OAuthStateError
        ):
            resolve_oauth_state(
                state=state,
                provider="microsoft",
            )

    def test_state_rejects_tampering(self):
        state = create_oauth_state(
            user_id=42,
            provider="google",
        )

        tampered = state + "tampered"

        with self.assertRaises(
            OAuthStateError
        ):
            resolve_oauth_state(
                state=tampered,
                provider="google",
            )

    def test_state_rejects_invalid_provider(self):
        with self.assertRaises(
            OAuthStateError
        ):
            create_oauth_state(
                user_id=42,
                provider="unsupported",
            )

    def test_state_rejects_missing_user(self):
        with self.assertRaises(
            OAuthStateError
        ):
            create_oauth_state(
                user_id=None,
                provider="google",
            )

    def test_state_rejects_expired_token(self):
        state = create_oauth_state(
            user_id=42,
            provider="google",
        )

        with self.assertRaises(
            OAuthStateError
        ):
            resolve_oauth_state(
                state=state,
                provider="google",
                max_age=-1,
            )