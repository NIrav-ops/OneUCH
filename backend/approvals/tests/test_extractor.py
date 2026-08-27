from django.test import SimpleTestCase

from approvals.services.extractor import (
    extract_approvals,
)


class ApprovalExtractorTests(
    SimpleTestCase
):

    def assertApproval(
        self,
        *,
        subject="",
        body="",
    ):
        result = extract_approvals(
            subject,
            body,
        )

        self.assertEqual(
            len(result),
            1,
        )

        return result[0]

    def assertNoApproval(
        self,
        *,
        subject="",
        body="",
    ):
        result = extract_approvals(
            subject,
            body,
        )

        self.assertEqual(
            result,
            [],
        )

    def test_please_approve_is_approval(
        self,
    ):
        item = self.assertApproval(
            body=(
                "Please approve the attached "
                "commercial proposal."
            ),
        )

        self.assertEqual(
            item["title"],
            "Approval Required",
        )

    def test_approval_required_is_approval(
        self,
    ):
        self.assertApproval(
            body=(
                "Management approval is required "
                "before deployment."
            ),
        )

    def test_need_your_approval_is_approval(
        self,
    ):
        self.assertApproval(
            body=(
                "We need your approval to proceed."
            ),
        )

    def test_sign_off_request_is_approval(
        self,
    ):
        item = self.assertApproval(
            body=(
                "Kindly sign off on the final "
                "implementation plan."
            ),
        )

        self.assertEqual(
            item["title"],
            "Sign Off Required",
        )

    def test_can_we_proceed_is_approval(
        self,
    ):
        item = self.assertApproval(
            body=(
                "Can we proceed with the production "
                "deployment?"
            ),
        )

        self.assertEqual(
            item["title"],
            "Proceed Approval",
        )

    def test_completed_approval_is_not_new_approval(
        self,
    ):
        self.assertNoApproval(
            body=(
                "The approval was completed "
                "yesterday."
            ),
        )

    def test_already_approved_is_not_new_approval(
        self,
    ):
        self.assertNoApproval(
            body=(
                "The customer already approved "
                "the proposal."
            ),
        )

    def test_confirm_receipt_is_not_approval(
        self,
    ):
        self.assertNoApproval(
            body=(
                "I confirm receipt of your email."
            ),
        )

    def test_plain_review_request_is_not_approval(
        self,
    ):
        self.assertNoApproval(
            body=(
                "Please review the attached "
                "contract."
            ),
        )

    def test_permission_already_granted_is_not_approval(
        self,
    ):
        self.assertNoApproval(
            body=(
                "Permission was already granted "
                "to the engineering team."
            ),
        )

    def test_historical_approval_request_is_not_new_approval(
        self,
    ):
        self.assertNoApproval(
            body=(
                "Yesterday I asked you to approve "
                "the proposal. It has now been "
                "completed."
            ),
        )

    def test_no_deadline_does_not_invent_due_date(
        self,
    ):
        item = self.assertApproval(
            body=(
                "Please approve the proposal."
            ),
        )

        self.assertIsNone(
            item["due_date"]
        )
