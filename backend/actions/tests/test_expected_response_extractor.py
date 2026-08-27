from datetime import datetime, timezone as dt_timezone

from django.test import SimpleTestCase

from actions.services.expected_response_extractor import (
    detect_expected_response,
)


REFERENCE_TIME = datetime(
    2026,
    8,
    26,
    8,
    0,
    tzinfo=dt_timezone.utc,
)


class ExpectedResponseExtractorTests(SimpleTestCase):

    def test_we_will_send_by_friday(self):
        result = detect_expected_response(
            "Revised quotation",
            "We will send the revised quotation by Friday.",
            reference_time=REFERENCE_TIME,
        )

        self.assertIsNotNone(result)
        self.assertEqual(
            result["response_due_at"].date().isoformat(),
            "2026-08-28",
        )

    def test_vendor_will_confirm_tomorrow(self):
        result = detect_expected_response(
            "Vendor confirmation",
            "Vendor will confirm tomorrow.",
            reference_time=REFERENCE_TIME,
        )

        self.assertIsNotNone(result)
        self.assertEqual(
            result["response_due_at"].date().isoformat(),
            "2026-08-27",
        )

    def test_customer_will_get_back_next_monday(self):
        result = detect_expected_response(
            "Customer update",
            "Customer will get back to us next Monday.",
            reference_time=REFERENCE_TIME,
        )

        self.assertIsNotNone(result)
        self.assertEqual(
            result["response_due_at"].date().isoformat(),
            "2026-08-31",
        )

    def test_explicit_expected_response_without_date(self):
        result = detect_expected_response(
            "Approval update",
            "Please let me know once approved.",
            reference_time=REFERENCE_TIME,
        )

        self.assertIsNotNone(result)
        self.assertIsNone(
            result["response_due_at"]
        )

    def test_waiting_statement_alone_is_not_expected_response(self):
        result = detect_expected_response(
            "Status",
            "We are waiting for the customer.",
            reference_time=REFERENCE_TIME,
        )

        self.assertIsNone(result)

    def test_pending_statement_is_not_expected_response(self):
        result = detect_expected_response(
            "Pending",
            "The request is pending internally.",
            reference_time=REFERENCE_TIME,
        )

        self.assertIsNone(result)

    def test_received_response_is_not_expected_response(self):
        result = detect_expected_response(
            "Response received",
            "Thanks for the response.",
            reference_time=REFERENCE_TIME,
        )

        self.assertIsNone(result)

    def test_historical_commitment_is_not_expected_response(self):
        result = detect_expected_response(
            "Quotation",
            "We sent the quotation yesterday.",
            reference_time=REFERENCE_TIME,
        )

        self.assertIsNone(result)

    def test_explicit_followup_is_not_expected_response(self):
        result = detect_expected_response(
            "Vendor follow-up",
            "Please follow up with the vendor tomorrow.",
            reference_time=REFERENCE_TIME,
        )

        self.assertIsNone(result)

    def test_plain_request_is_not_expected_response(self):
        result = detect_expected_response(
            "Review",
            "Please review the document.",
            reference_time=REFERENCE_TIME,
        )

        self.assertIsNone(result)


