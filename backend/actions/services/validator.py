from django.utils import timezone
from actions.exceptions import InvalidAction

class ActionValidator:

    @staticmethod
    def validate_create(data):

        required = [
            "organization",
            "title",
        ]

        source_type = data.get(
            "source_type",
            "email",
        )

        if source_type == "email":

            if not data.get("message"):
                raise InvalidAction(
                    "message is required for email actions"
                )

            if not data.get("user"):
                raise InvalidAction(
                    "user is required for email actions"
                )

        elif source_type == "workflow":

            if not data.get("workflow_instance"):
                raise InvalidAction(
                    "workflow_instance required"
                )

        for field in required:
            if field not in data or data[field] is None:
                raise InvalidAction(f"{field} is required")

        priority = data.get("priority", 0)

        if priority < 0 or priority > 100:
            raise InvalidAction(
                "priority must be between 0 and 100"
            )

        due_date = data.get("due_date")

        if due_date and due_date < timezone.now():
            raise InvalidAction(
                "due_date cannot be in the past"
            )

        return True