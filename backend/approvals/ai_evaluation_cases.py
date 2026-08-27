from datetime import (
    datetime,
    timezone as dt_timezone,
)


REFERENCE_TIME = datetime(
    2026,
    8,
    25,
    5,
    0,
    tzinfo=dt_timezone.utc,
)


APPROVAL_AI_EVALUATION_CASES = [
    # --------------------------------------------------
    # Positive semantic approvals
    # --------------------------------------------------
    {
        "id": "P01",
        "subject": "Production deployment",
        "body": (
            "Rakesh, are you comfortable with us "
            "moving ahead with the production "
            "deployment before tomorrow?"
        ),
        "expected_approval": True,
        "expected_due_date": "2026-08-26",
    },
    {
        "id": "P02",
        "subject": "Migration go-ahead",
        "body": (
            "Need your go-ahead before we start "
            "the migration."
        ),
        "expected_approval": True,
        "expected_due_date": None,
    },
    {
        "id": "P03",
        "subject": "Firewall change",
        "body": (
            "Can you authorize this firewall "
            "change for production?"
        ),
        "expected_approval": True,
        "expected_due_date": None,
    },
    {
        "id": "P04",
        "subject": "Deployment tonight",
        "body": (
            "Would you be okay if we deploy this "
            "change tonight?"
        ),
        "expected_approval": True,
        "expected_due_date": None,
    },
    {
        "id": "P05",
        "subject": "Purchase request",
        "body": (
            "May we proceed with the purchase?"
        ),
        "expected_approval": True,
        "expected_due_date": None,
    },
    {
        "id": "P06",
        "subject": "Access authorization",
        "body": (
            "Can you authorize access for the "
            "implementation team?"
        ),
        "expected_approval": True,
        "expected_due_date": None,
    },
    {
        "id": "P07",
        "subject": "Change window",
        "body": (
            "We need a go-ahead before the change "
            "window opens tomorrow."
        ),
        "expected_approval": True,
        "expected_due_date": "2026-08-26",
    },
    {
        "id": "P08",
        "subject": "Final decision",
        "body": (
            "Can you confirm whether we are clear "
            "to proceed with production?"
        ),
        "expected_approval": True,
        "expected_due_date": None,
    },
    {
        "id": "P09",
        "subject": "Customer deployment",
        "body": (
            "Are we okay to proceed with the "
            "customer deployment on Monday?"
        ),
        "expected_approval": True,
        "expected_due_date": None,
    },
    {
        "id": "P10",
        "subject": "Commercial authorization",
        "body": (
            "Can you give us the green light to "
            "release the commercial today?"
        ),
        "expected_approval": True,
        "expected_due_date": "2026-08-25",
    },

    # --------------------------------------------------
    # Negative / non-approval cases
    # --------------------------------------------------
    {
        "id": "N01",
        "subject": "Review request",
        "body": (
            "Please review the migration plan "
            "and share your comments."
        ),
        "expected_approval": False,
        "expected_due_date": None,
    },
    {
        "id": "N02",
        "subject": "Receipt confirmation",
        "body": (
            "I confirm receipt of your email."
        ),
        "expected_approval": False,
        "expected_due_date": None,
    },
    {
        "id": "N03",
        "subject": "Approved yesterday",
        "body": (
            "Management already approved the "
            "production deployment yesterday."
        ),
        "expected_approval": False,
        "expected_due_date": None,
    },
    {
        "id": "N04",
        "subject": "Conditional deployment",
        "body": (
            "If approved, we can begin deployment "
            "tomorrow."
        ),
        "expected_approval": False,
        "expected_due_date": None,
    },
    {
        "id": "N05",
        "subject": "Approval status",
        "body": (
            "The customer is still waiting for "
            "management approval."
        ),
        "expected_approval": False,
        "expected_due_date": None,
    },
    {
        "id": "N06",
        "subject": "Another team approval",
        "body": (
            "Approval needs to come from the "
            "customer security team."
        ),
        "expected_approval": False,
        "expected_due_date": None,
    },
    {
        "id": "N07",
        "subject": "Completed request",
        "body": (
            "Previous message: Please approve the "
            "deployment. Current update: this was "
            "completed yesterday."
        ),
        "expected_approval": False,
        "expected_due_date": None,
    },
    {
        "id": "N08",
        "subject": "Information only",
        "body": (
            "For your information, the approval "
            "workflow is currently under review."
        ),
        "expected_approval": False,
        "expected_due_date": None,
    },
    {
        "id": "N09",
        "subject": "Approval recorded",
        "body": (
            "The approval has already been recorded "
            "in the portal."
        ),
        "expected_approval": False,
        "expected_due_date": None,
    },
    {
        "id": "N10",
        "subject": "Plain confirmation",
        "body": (
            "Please confirm the meeting time "
            "for tomorrow."
        ),
        "expected_approval": False,
        "expected_due_date": None,
    },

    # --------------------------------------------------
    # Ambiguous / adversarial cases
    # --------------------------------------------------
    {
        "id": "A01",
        "subject": "Moving ahead",
        "body": (
            "Are you comfortable with us moving "
            "ahead from here?"
        ),
        "expected_approval": True,
        "expected_due_date": None,
    },
    {
        "id": "A02",
        "subject": "Potential approval",
        "body": (
            "If the customer agrees, we may need "
            "your approval next week."
        ),
        "expected_approval": False,
        "expected_due_date": None,
    },
    {
        "id": "A03",
        "subject": "Historical approval",
        "body": (
            "Yesterday we asked for your go-ahead. "
            "The deployment is already complete."
        ),
        "expected_approval": False,
        "expected_due_date": None,
    },
    {
        "id": "A04",
        "subject": "Third-party authority",
        "body": (
            "The customer mentioned that their CFO "
            "may need to approve the commercial."
        ),
        "expected_approval": False,
        "expected_due_date": None,
    },
    {
        "id": "A05",
        "subject": "Authorization blocker",
        "body": (
            "We cannot proceed until you give us "
            "the green light."
        ),
        "expected_approval": True,
        "expected_due_date": None,
    },
    {
        "id": "A06",
        "subject": "Quoted approval completed",
        "body": (
            "Previous message: Can you authorize "
            "the production release? Current update: "
            "authorization was already provided."
        ),
        "expected_approval": False,
        "expected_due_date": None,
    },
    {
        "id": "A07",
        "subject": "No decision required",
        "body": (
            "Nothing is required from your side. "
            "We are waiting for internal approval."
        ),
        "expected_approval": False,
        "expected_due_date": None,
    },
    {
        "id": "A08",
        "subject": "Release decision",
        "body": (
            "We are ready to release this to "
            "production. Can we move ahead?"
        ),
        "expected_approval": True,
        "expected_due_date": None,
    },
]
