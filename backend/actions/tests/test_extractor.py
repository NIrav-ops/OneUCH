from django.test import SimpleTestCase

from actions.services.extractor import extract_actions


class ActionExtractorTests(SimpleTestCase):

    def test_extracts_explicit_review_request(self):
        actions = extract_actions(
            "Contract review required",
            "Please review the attached contract and share your comments.",
        )

        self.assertTrue(
            any(
                action["title"] == "Review Required"
                for action in actions
            )
        )

    def test_extracts_explicit_quotation_request(self):
        actions = extract_actions(
            "Quotation required",
            "Please send the revised quotation for 250 users.",
        )

        self.assertTrue(
            any(
                action["title"] == "Send Quotation"
                for action in actions
            )
        )

    def test_does_not_create_action_for_payment_confirmation(self):
        actions = extract_actions(
            "Payment received",
            "Your payment has been received successfully. "
            "No further action is required.",
        )

        self.assertEqual(actions, [])

    def test_does_not_create_action_for_invoice_information(self):
        actions = extract_actions(
            "Invoice copy",
            "The invoice is attached for your records.",
        )

        self.assertEqual(actions, [])

    def test_does_not_create_action_for_generic_review_word(self):
        actions = extract_actions(
            "Weekly product review",
            "Here is our weekly review of product updates.",
        )

        self.assertEqual(actions, [])

    def test_does_not_create_action_for_generic_quote_word(self):
        actions = extract_actions(
            "Quote of the day",
            "Here is today's inspirational quote.",
        )

        self.assertEqual(actions, [])

    def test_non_actionable_message_returns_empty_list(self):
        actions = extract_actions(
            "Meeting completed",
            "Thanks everyone for joining today's meeting.",
        )

        self.assertEqual(actions, [])

    def test_action_contains_expected_metadata(self):
        actions = extract_actions(
            "Quotation request",
            "Kindly send the quotation for 100 licenses.",
        )

        self.assertEqual(len(actions), 1)

        action = actions[0]

        self.assertEqual(
            action["title"],
            "Send Quotation",
        )
        self.assertGreater(
            action["priority"],
            0,
        )
        self.assertGreater(
            action["confidence_score"],
            0,
        )

class EnterpriseActionPrecisionTests(SimpleTestCase):

    def test_po_attached_for_reference_is_not_action(self):
        actions = extract_actions(
            "PO attached",
            "Please find the purchase order attached "
            "for your reference.",
        )

        self.assertEqual(actions, [])

    def test_review_po_request_is_action(self):
        actions = extract_actions(
            "PO review",
            "Please review the attached purchase order "
            "and share your comments.",
        )

        self.assertTrue(
            any(
                item["title"] == "Review Required"
                for item in actions
            )
        )

    def test_invoice_generated_is_not_action(self):
        actions = extract_actions(
            "Invoice generated",
            "Invoice INV-2026-100 has been generated "
            "successfully.",
        )

        self.assertEqual(actions, [])

    def test_process_invoice_is_action(self):
        actions = extract_actions(
            "Invoice processing",
            "Kindly process the attached invoice.",
        )

        self.assertTrue(
            any(
                item["title"] == "Payment Action"
                for item in actions
            )
        )

    def test_vendor_quote_received_is_not_action(self):
        actions = extract_actions(
            "Vendor quotation received",
            "We have received the quotation "
            "from the vendor.",
        )

        self.assertEqual(actions, [])

    def test_prepare_and_share_quote_is_action(self):
        actions = extract_actions(
            "Customer quotation",
            "Kindly prepare and share the quotation "
            "with the customer.",
        )

        self.assertTrue(
            any(
                item["title"] == "Send Quotation"
                for item in actions
            )
        )

    def test_approval_completed_is_not_action(self):
        actions = extract_actions(
            "Approval completed",
            "The commercial proposal has already "
            "been approved.",
        )

        self.assertEqual(actions, [])

    def test_your_approval_required_is_action(self):
        actions = extract_actions(
            "Approval required",
            "Your approval is required before "
            "we proceed.",
        )

        self.assertTrue(
            any(
                item["title"] == "Approval Required"
                for item in actions
            )
        )

    def test_fyi_payment_update_is_not_action(self):
        actions = extract_actions(
            "FYI - Payment update",
            "Sharing the payment status for "
            "your information.",
        )

        self.assertEqual(actions, [])

    def test_payment_overdue_is_action(self):
        actions = extract_actions(
            "Payment overdue",
            "Payment is overdue and needs attention.",
        )

        self.assertTrue(
            any(
                item["title"] == "Payment Action"
                for item in actions
            )
        )

class ActionDueDateExtractionTests(SimpleTestCase):

    def setUp(self):
        from datetime import datetime, timezone as dt_timezone

        self.reference_time = datetime(
            2026,
            8,
            24,
            10,
            0,
            tzinfo=dt_timezone.utc,
        )

    def test_extracts_tomorrow_due_date(self):
        actions = extract_actions(
            "Quotation required",
            "Please send the revised quotation by tomorrow.",
            reference_time=self.reference_time,
        )

        self.assertEqual(len(actions), 1)
        self.assertIsNotNone(actions[0]["due_date"])
        self.assertEqual(
            actions[0]["due_date"].date().isoformat(),
            "2026-08-25",
        )

    def test_extracts_weekday_due_date(self):
        actions = extract_actions(
            "Contract review",
            "Please review the contract by Friday.",
            reference_time=self.reference_time,
        )

        self.assertEqual(len(actions), 1)
        self.assertIsNotNone(actions[0]["due_date"])
        self.assertEqual(
            actions[0]["due_date"].date().isoformat(),
            "2026-08-28",
        )

    def test_extracts_iso_due_date(self):
        actions = extract_actions(
            "Proposal review",
            "Please review the proposal by 2026-08-30.",
            reference_time=self.reference_time,
        )

        self.assertEqual(len(actions), 1)
        self.assertIsNotNone(actions[0]["due_date"])
        self.assertEqual(
            actions[0]["due_date"].date().isoformat(),
            "2026-08-30",
        )

    def test_action_without_deadline_has_no_due_date(self):
        actions = extract_actions(
            "Contract review",
            "Please review the attached contract.",
            reference_time=self.reference_time,
        )

        self.assertEqual(len(actions), 1)
        self.assertIsNone(actions[0]["due_date"])

    def test_non_actionable_date_reference_creates_no_action(self):
        actions = extract_actions(
            "Meeting summary",
            "Our customer meeting was held on Friday.",
            reference_time=self.reference_time,
        )

        self.assertEqual(actions, [])

