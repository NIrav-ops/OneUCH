from datetime import (
    datetime,
    timezone as dt_timezone,
)

from django.test import SimpleTestCase

from actions.services.extractor import (
    detect_followup,
)


REFERENCE_TIME = datetime(
    2026,
    8,
    26,
    5,
    0,
    tzinfo=dt_timezone.utc,
)


class FollowUpExtractorTests(
    SimpleTestCase
):

    def test_explicit_follow_up_tomorrow(
        self,
    ):
        result = detect_followup(
            "Vendor update",
            (
                "Please follow up with the vendor "
                "tomorrow."
            ),
            reference_time=REFERENCE_TIME,
        )

        self.assertIsNotNone(
            result
        )

        self.assertEqual(
            result[
                "followup_due_at"
            ].date().isoformat(),
            "2026-08-27",
        )

    def test_follow_up_by_friday(
        self,
    ):
        result = detect_followup(
            "Commercial",
            (
                "Please follow up with finance "
                "by Friday."
            ),
            reference_time=REFERENCE_TIME,
        )

        self.assertIsNotNone(
            result
        )

        self.assertEqual(
            result[
                "followup_due_at"
            ].date().isoformat(),
            "2026-08-28",
        )

    def test_reconnect_next_monday(
        self,
    ):
        result = detect_followup(
            "Customer discussion",
            (
                "Let's reconnect next Monday."
            ),
            reference_time=REFERENCE_TIME,
        )

        self.assertIsNotNone(
            result
        )

        self.assertEqual(
            result[
                "followup_due_at"
            ].date().isoformat(),
            "2026-08-31",
        )

    def test_explicit_follow_up_without_date(
        self,
    ):
        result = detect_followup(
            "Vendor response",
            (
                "Please follow up with the vendor."
            ),
            reference_time=REFERENCE_TIME,
        )

        self.assertIsNotNone(
            result
        )

        self.assertIsNone(
            result[
                "followup_due_at"
            ]
        )

    def test_waiting_alone_is_not_follow_up(
        self,
    ):
        result = detect_followup(
            "Status update",
            (
                "We are waiting for the customer "
                "response."
            ),
            reference_time=REFERENCE_TIME,
        )

        self.assertIsNone(
            result
        )

    def test_pending_alone_is_not_follow_up(
        self,
    ):
        result = detect_followup(
            "Pending item",
            (
                "The request is currently pending."
            ),
            reference_time=REFERENCE_TIME,
        )

        self.assertIsNone(
            result
        )

    def test_response_word_is_not_follow_up(
        self,
    ):
        result = detect_followup(
            "Response received",
            (
                "We received the customer's "
                "response today."
            ),
            reference_time=REFERENCE_TIME,
        )

        self.assertIsNone(
            result
        )

    def test_reply_word_is_not_follow_up(
        self,
    ):
        result = detect_followup(
            "Reply received",
            (
                "Thank you for your reply."
            ),
            reference_time=REFERENCE_TIME,
        )

        self.assertIsNone(
            result
        )

    def test_thanks_for_follow_up_is_not_new_follow_up(
        self,
    ):
        result = detect_followup(
            "Re: commercial",
            (
                "Thanks for the follow-up. "
                "We have received the quotation."
            ),
            reference_time=REFERENCE_TIME,
        )

        self.assertIsNone(
            result
        )

    def test_completed_follow_up_is_not_new_follow_up(
        self,
    ):
        result = detect_followup(
            "Completed",
            (
                "We followed up yesterday and "
                "the issue is now resolved."
            ),
            reference_time=REFERENCE_TIME,
        )

        self.assertIsNone(
            result
        )

    def test_marketing_follow_up_is_not_follow_up(
        self,
    ):
        result = detect_followup(
            "Follow-up webinar",
            (
                "Join our follow-up webinar "
                "tomorrow."
            ),
            reference_time=REFERENCE_TIME,
        )

        self.assertIsNone(
            result
        )

    def test_plain_review_is_not_follow_up(
        self,
    ):
        result = detect_followup(
            "Review document",
            (
                "Please review the document "
                "and share your comments."
            ),
            reference_time=REFERENCE_TIME,
        )

        self.assertIsNone(
            result
        )
