from .base_repository import BaseRepository
from .validator import ActionValidator
from actions.models import ActionItem
from django.db import transaction


class ActionRepository(BaseRepository):

    model = ActionItem

    @classmethod
    @transaction.atomic
    def create_action(cls, **data):

        ActionValidator.validate_create(data)
        data.setdefault(
            "source_type",
            "email",
        )

        return cls.create(**data)

    @classmethod
    def assign_owner(cls, action, owner):

        return cls.update(
            action,
            owner=owner,
        )

    @classmethod
    def complete_action(cls, action):

        from django.utils import timezone

        return cls.update(
            action,
            status="completed",
            completed_at=timezone.now(),
        )

    @classmethod
    def cancel_action(cls, action):

        return cls.update(
            action,
            status="cancelled",
        )

    @classmethod
    def update_priority(cls, action, priority):

        return cls.update(
            action,
            priority=priority,
        )

    @classmethod
    def mark_waiting(cls, action):

        return cls.update(
            action,
            status="waiting",
        )

    @classmethod
    def mark_blocked(cls, action):

        return cls.update(
            action,
            status="blocked",
        )