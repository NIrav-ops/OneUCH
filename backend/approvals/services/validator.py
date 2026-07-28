from django.utils import timezone

from approvals.services.exceptions import InvalidApproval


class ApprovalValidator:

    @classmethod
    def validate_create(cls, data):

        required = [
            "organization",
            "title",
        ]

        for field in required:

            if not data.get(field):

                raise InvalidApproval(
                    f"{field} is required"
                )

        source_type = data.get(
            "source_type",
            "email",
        )

        if source_type == "email":

            if not data.get("message"):

                raise InvalidApproval(
                    "message is required for email approvals"
                )

            if not data.get("user"):

                raise InvalidApproval(
                    "user is required for email approvals"
                )

        elif source_type == "workflow":

            if not data.get("workflow_instance"):

                raise InvalidApproval(
                    "workflow_instance is required"
                )

        due_date = data.get("due_date")

        if due_date and due_date < timezone.now():

            raise InvalidApproval(
                "due_date cannot be in the past"
            )