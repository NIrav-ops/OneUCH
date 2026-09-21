import json

from unittest.mock import (
    patch,
)

from django.test import (
    SimpleTestCase,
)

from googleapiclient.errors import (
    HttpError,
)

from httplib2 import (
    Response,
)

from googleapis.services.gmail_sync import (
    _execute_gmail_request,
    _gmail_sync_user_error,
    _is_retryable_gmail_http_error,
)


def gmail_http_error(
    *,
    status,
    reason,
):
    response = Response(
        {
            "status":
                str(status),

            "reason":
                "Test error",
        }
    )

    content = json.dumps(
        {
            "error": {
                "code":
                    status,

                "message":
                    "Provider test error",

                "errors": [
                    {
                        "domain":
                            "usageLimits",

                        "reason":
                            reason,

                        "message":
                            "Provider test error",
                    }
                ],
            }
        }
    ).encode(
        "utf-8"
    )

    return HttpError(
        response,
        content,
        uri=(
            "https://gmail.googleapis.com/"
            "gmail/v1/users/me/messages"
        ),
    )


class FakeRequest:

    def __init__(
        self,
        *results,
    ):
        self.results = list(
            results
        )

        self.call_count = 0


    def execute(
        self,
    ):
        self.call_count += 1

        result = self.results.pop(
            0
        )

        if isinstance(
            result,
            BaseException,
        ):
            raise result

        return result


class GmailRateLimitBackoffTests(
    SimpleTestCase,
):

    @patch(
        "googleapis.services.gmail_sync.random.uniform",
        return_value=0,
    )
    @patch(
        "googleapis.services.gmail_sync.time.sleep"
    )
    def test_rate_limit_403_retries_with_backoff(
        self,
        sleep_mock,
        _uniform_mock,
    ):
        error = gmail_http_error(
            status=403,
            reason="rateLimitExceeded",
        )

        request = FakeRequest(
            error,
            {
                "messages": [],
            },
        )

        result = (
            _execute_gmail_request(
                request,
                operation="messages.list",
                account_id=4,
            )
        )

        self.assertEqual(
            result,
            {
                "messages": [],
            },
        )

        self.assertEqual(
            request.call_count,
            2,
        )

        sleep_mock.assert_called_once_with(
            1
        )


    @patch(
        "googleapis.services.gmail_sync.random.uniform",
        return_value=0,
    )
    @patch(
        "googleapis.services.gmail_sync.time.sleep"
    )
    def test_429_retries_with_backoff(
        self,
        sleep_mock,
        _uniform_mock,
    ):
        error = gmail_http_error(
            status=429,
            reason="rateLimitExceeded",
        )

        request = FakeRequest(
            error,
            {
                "id": "message-1",
            },
        )

        result = (
            _execute_gmail_request(
                request,
                operation="messages.get",
                account_id=4,
            )
        )

        self.assertEqual(
            result["id"],
            "message-1",
        )

        self.assertEqual(
            request.call_count,
            2,
        )

        sleep_mock.assert_called_once_with(
            1
        )


    @patch(
        "googleapis.services.gmail_sync.time.sleep"
    )
    def test_non_retryable_403_fails_closed(
        self,
        sleep_mock,
    ):
        error = gmail_http_error(
            status=403,
            reason="insufficientPermissions",
        )

        request = FakeRequest(
            error,
        )

        with self.assertRaises(
            HttpError
        ):
            _execute_gmail_request(
                request,
                operation="messages.get",
                account_id=4,
            )

        self.assertEqual(
            request.call_count,
            1,
        )

        sleep_mock.assert_not_called()


    def test_rate_limit_error_is_retryable(
        self,
    ):
        error = gmail_http_error(
            status=403,
            reason="userRateLimitExceeded",
        )

        self.assertTrue(
            _is_retryable_gmail_http_error(
                error
            )
        )


    def test_customer_error_does_not_expose_provider_payload(
        self,
    ):
        error = gmail_http_error(
            status=403,
            reason="rateLimitExceeded",
        )

        message = (
            _gmail_sync_user_error(
                error
            )
        )

        self.assertEqual(
            message,
            (
                "Gmail temporarily rate limited synchronization. "
                "One UCH will retry automatically."
            ),
        )

        self.assertNotIn(
            "gmail.googleapis.com",
            message,
        )

        self.assertNotIn(
            "HttpError",
            message,
        )
