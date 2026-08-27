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


ACTION_AI_EVALUATION_CASES = [
    {
        "id": "P01",
        "subject": "Deployment blocker",
        "body": (
            "Abhishek, can you coordinate with the "
            "infrastructure team and get the firewall "
            "access sorted before tomorrow's deployment?"
        ),
        "expected_action": True,
        "expected_due_date": "2026-08-26",
    },
    {
        "id": "P02",
        "subject": "Customer meeting",
        "body": (
            "Can you take care of this before EOD? "
            "The customer needs the updated access list."
        ),
        "expected_action": True,
        "expected_due_date": None,
    },
    {
        "id": "P03",
        "subject": "Migration readiness",
        "body": (
            "Need this closed before the customer "
            "meeting tomorrow."
        ),
        "expected_action": True,
        "expected_due_date": "2026-08-26",
    },
    {
        "id": "P04",
        "subject": "Finance coordination",
        "body": (
            "Coordinate with finance and get this sorted."
        ),
        "expected_action": True,
        "expected_due_date": None,
    },
    {
        "id": "P05",
        "subject": "New joiners",
        "body": (
            "Arrange access for the new team members "
            "before Monday."
        ),
        "expected_action": True,
        "expected_due_date": "2026-08-31",
    },
    {
        "id": "P06",
        "subject": "Server information",
        "body": (
            "Ensure the server details are shared "
            "with Dipankar."
        ),
        "expected_action": True,
        "expected_due_date": None,
    },
    {
        "id": "P07",
        "subject": "Migration completion",
        "body": (
            "Get the migration completed before Monday."
        ),
        "expected_action": True,
        "expected_due_date": "2026-08-31",
    },
    {
        "id": "P08",
        "subject": "Completion confirmation",
        "body": (
            "Can someone confirm whether this has "
            "been done?"
        ),
        "expected_action": True,
        "expected_due_date": None,
    },
    {
        "id": "P09",
        "subject": "OEM issue",
        "body": (
            "Work with the OEM and resolve this."
        ),
        "expected_action": True,
        "expected_due_date": None,
    },
    {
        "id": "P10",
        "subject": "Urgent customer item",
        "body": (
            "This needs your attention today. "
            "Please ensure the customer gets access."
        ),
        "expected_action": True,
        "expected_due_date": "2026-08-25",
    },

    {
        "id": "N01",
        "subject": "Payment update",
        "body": (
            "Payment received successfully. "
            "Thank you."
        ),
        "expected_action": False,
        "expected_due_date": None,
    },
    {
        "id": "N02",
        "subject": "Approval status",
        "body": (
            "The approval was completed yesterday."
        ),
        "expected_action": False,
        "expected_due_date": None,
    },
    {
        "id": "N03",
        "subject": "Quotation received",
        "body": (
            "We have received the revised quotation."
        ),
        "expected_action": False,
        "expected_due_date": None,
    },
    {
        "id": "N04",
        "subject": "Invoice notification",
        "body": (
            "Invoice generated successfully."
        ),
        "expected_action": False,
        "expected_due_date": None,
    },
    {
        "id": "N05",
        "subject": "Weekly newsletter",
        "body": (
            "Here is our weekly technology newsletter "
            "with the latest industry updates."
        ),
        "expected_action": False,
        "expected_due_date": None,
    },
    {
        "id": "N06",
        "subject": "Status update",
        "body": (
            "For your information, migration is "
            "currently 80 percent complete."
        ),
        "expected_action": False,
        "expected_due_date": None,
    },
    {
        "id": "N07",
        "subject": "Historical review",
        "body": (
            "I reviewed the contract yesterday and "
            "shared my comments."
        ),
        "expected_action": False,
        "expected_due_date": None,
    },
    {
        "id": "N08",
        "subject": "Completed request",
        "body": (
            "The requested access has already been "
            "provided to all users."
        ),
        "expected_action": False,
        "expected_due_date": None,
    },
    {
        "id": "N09",
        "subject": "Out of office",
        "body": (
            "I am currently out of office and will "
            "return next week."
        ),
        "expected_action": False,
        "expected_due_date": None,
    },
    {
        "id": "N10",
        "subject": "Automated receipt",
        "body": (
            "This is an automated confirmation that "
            "your request was received."
        ),
        "expected_action": False,
        "expected_due_date": None,
    },
        {
        "id": "A01",
        "subject": "Revised commercial",
        "body": (
            "We are still waiting on the revised "
            "commercial from your side."
        ),
        "expected_action": True,
        "expected_due_date": None,
    },
    {
        "id": "A02",
        "subject": "Possible migration",
        "body": (
            "If the customer confirms tomorrow, "
            "we may need to start the migration "
            "next week."
        ),
        "expected_action": False,
        "expected_due_date": None,
    },
    {
        "id": "A03",
        "subject": "Previous request",
        "body": (
            "Yesterday I asked you to share the "
            "server list. Thanks, this has now "
            "been completed."
        ),
        "expected_action": False,
        "expected_due_date": None,
    },
    {
        "id": "A04",
        "subject": "Customer discussion",
        "body": (
            "The customer mentioned that someone "
            "may need to verify the firewall rules."
        ),
        "expected_action": False,
        "expected_due_date": None,
    },
    {
        "id": "A05",
        "subject": "Access issue",
        "body": (
            "We still cannot access the portal. "
            "Could you check what is blocking us?"
        ),
        "expected_action": True,
        "expected_due_date": None,
    },
    {
        "id": "A06",
        "subject": "Quoted request completed",
        "body": (
            "Previous message: Please provide the "
            "license details by Monday. "
            "Current update: The license details "
            "were already shared this morning."
        ),
        "expected_action": False,
        "expected_due_date": None,
    },
    {
        "id": "A07",
        "subject": "Pending confirmation",
        "body": (
            "Not sure whether anything is required "
            "from our side at this stage. We are "
            "waiting for the customer's confirmation."
        ),
        "expected_action": False,
        "expected_due_date": None,
    },
    {
        "id": "A08",
        "subject": "Production issue",
        "body": (
            "This is affecting production. Please "
            "work with the application team and "
            "figure out what is causing it."
        ),
        "expected_action": True,
        "expected_due_date": None,
    },
]
