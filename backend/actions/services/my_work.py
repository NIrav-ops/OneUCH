from dataclasses import (
    asdict,
    dataclass,
)
from typing import Optional

from django.utils import timezone

from actions.models import (
    ActionItem,
)
from approvals.models import (
    ApprovalItem,
)


@dataclass(frozen=True)
class MyWorkItem:
    """
    One current piece of explicitly owned execution work.

    My Work never infers ownership. An item belongs here only
    when the authenticated user is explicitly stored as the
    Action owner or Approval assignee.
    """

    work_id: str
    work_type: str

    source_object_id: int

    organization_id: int

    conversation_id: Optional[int]
    source_message_id: Optional[int]

    title: str
    description: str

    status: str
    priority: int

    owner_id: int
    owner_email: str

    due_at: object
    due_state: str

    created_at: object
    updated_at: object

    open_url: Optional[str]
    execution_url: str

    def to_dict(self):
        return asdict(
            self
        )


class MyWorkService:
    """
    Read-only personal execution projection.

    Explicit ownership semantics:

        ActionItem.owner
            -> current user

        ApprovalItem.assigned_to
            -> current user

    Creator/message ownership is deliberately ignored when
    deciding whether work belongs to the current user.
    """

    TYPE_ACTION = "action"
    TYPE_APPROVAL = "approval"

    DUE_OVERDUE = "overdue"
    DUE_TODAY = "due_today"
    DUE_UPCOMING = "upcoming"
    DUE_NONE = "no_due"

    ACTIVE_ACTION_STATUSES = (
        "open",
        "in_progress",
        "waiting",
        "blocked",
    )

    ACTIVE_APPROVAL_STATUSES = (
        "pending",
        "needs_info",
    )

    DUE_STATE_ORDER = {
        DUE_OVERDUE: 0,
        DUE_TODAY: 1,
        DUE_UPCOMING: 2,
        DUE_NONE: 3,
    }

    @classmethod
    def build(
        cls,
        *,
        organization,
        user,
        now=None,
    ):
        effective_now = (
            now
            or timezone.now()
        )

        actions = (
            ActionItem.objects
            .filter(
                organization=organization,
                owner=user,
                status__in=(
                    cls.ACTIVE_ACTION_STATUSES
                ),
            )
            .select_related(
                "owner",
                "message__conversation",
            )
        )

        approvals = (
            ApprovalItem.objects
            .filter(
                organization=organization,
                assigned_to=user,
                status__in=(
                    cls.ACTIVE_APPROVAL_STATUSES
                ),
            )
            .select_related(
                "assigned_to",
                "conversation",
                "message__conversation",
            )
        )

        items = []

        for action in actions:
            conversation_id = None

            if (
                action.message is not None
                and
                action.message.conversation_id
            ):
                conversation_id = (
                    action.message.conversation_id
                )

            items.append(
                MyWorkItem(
                    work_id=(
                        f"action:{action.id}"
                    ),

                    work_type=(
                        cls.TYPE_ACTION
                    ),

                    source_object_id=(
                        action.id
                    ),

                    organization_id=(
                        action.organization_id
                    ),

                    conversation_id=(
                        conversation_id
                    ),

                    source_message_id=(
                        action.message_id
                    ),

                    title=(
                        action.title
                    ),

                    description=(
                        action.description
                        or ""
                    ),

                    status=(
                        action.status
                    ),

                    priority=int(
                        action.priority
                        or 0
                    ),

                    owner_id=(
                        action.owner_id
                    ),

                    owner_email=(
                        action.owner.email
                    ),

                    due_at=(
                        action.due_date
                    ),

                    due_state=(
                        cls._due_state(
                            action.due_date,
                            now=effective_now,
                        )
                    ),

                    created_at=(
                        action.created_at
                    ),

                    updated_at=(
                        action.updated_at
                    ),

                    open_url=(
                        cls._open_url(
                            conversation_id
                        )
                    ),

                    execution_url=(
                        "/actions"
                    ),
                )
            )

        for approval in approvals:
            conversation_id = (
                approval.conversation_id
            )

            if (
                conversation_id is None
                and
                approval.message is not None
            ):
                conversation_id = (
                    approval.message
                    .conversation_id
                )

            items.append(
                MyWorkItem(
                    work_id=(
                        f"approval:{approval.id}"
                    ),

                    work_type=(
                        cls.TYPE_APPROVAL
                    ),

                    source_object_id=(
                        approval.id
                    ),

                    organization_id=(
                        approval.organization_id
                    ),

                    conversation_id=(
                        conversation_id
                    ),

                    source_message_id=(
                        approval.message_id
                    ),

                    title=(
                        approval.title
                    ),

                    description=(
                        approval.description
                        or ""
                    ),

                    status=(
                        approval.status
                    ),

                    priority=int(
                        approval.priority
                        or 0
                    ),

                    owner_id=(
                        approval.assigned_to_id
                    ),

                    owner_email=(
                        approval.assigned_to.email
                    ),

                    due_at=(
                        approval.due_date
                    ),

                    due_state=(
                        cls._due_state(
                            approval.due_date,
                            now=effective_now,
                        )
                    ),

                    created_at=(
                        approval.created_at
                    ),

                    updated_at=(
                        approval.updated_at
                    ),

                    open_url=(
                        cls._open_url(
                            conversation_id
                        )
                    ),

                    execution_url=(
                        "/approvals"
                    ),
                )
            )

        return sorted(
            items,
            key=cls._sort_key,
        )

    @classmethod
    def summary(
        cls,
        items,
    ):
        return {
            "total": len(
                items
            ),

            "actions": sum(
                1
                for item in items
                if (
                    item.work_type
                    == cls.TYPE_ACTION
                )
            ),

            "approvals": sum(
                1
                for item in items
                if (
                    item.work_type
                    == cls.TYPE_APPROVAL
                )
            ),

            "overdue": sum(
                1
                for item in items
                if (
                    item.due_state
                    == cls.DUE_OVERDUE
                )
            ),

            "due_today": sum(
                1
                for item in items
                if (
                    item.due_state
                    == cls.DUE_TODAY
                )
            ),

            "in_progress": sum(
                1
                for item in items
                if (
                    item.status
                    == "in_progress"
                )
            ),

            "blocked": sum(
                1
                for item in items
                if (
                    item.status
                    == "blocked"
                )
            ),

            "waiting": sum(
                1
                for item in items
                if (
                    item.status
                    == "waiting"
                )
            ),

            "needs_info": sum(
                1
                for item in items
                if (
                    item.status
                    == "needs_info"
                )
            ),

            "no_due": sum(
                1
                for item in items
                if (
                    item.due_state
                    == cls.DUE_NONE
                )
            ),
        }

    @classmethod
    def build_payload(
        cls,
        *,
        organization,
        user,
        now=None,
    ):
        effective_now = (
            now
            or timezone.now()
        )

        items = cls.build(
            organization=organization,
            user=user,
            now=effective_now,
        )

        return {
            "generated_at": (
                effective_now
            ),

            "organization_id": (
                organization.id
            ),

            "user_id": (
                user.id
            ),

            "summary": (
                cls.summary(
                    items
                )
            ),

            "items": [
                item.to_dict()
                for item in items
            ],
        }

    @classmethod
    def _due_state(
        cls,
        due_at,
        *,
        now,
    ):
        if due_at is None:
            return cls.DUE_NONE

        if due_at < now:
            return cls.DUE_OVERDUE

        if (
            timezone.localdate(
                due_at
            )
            ==
            timezone.localdate(
                now
            )
        ):
            return cls.DUE_TODAY

        return cls.DUE_UPCOMING

    @staticmethod
    def _open_url(
        conversation_id,
    ):
        if conversation_id is None:
            return None

        return (
            "/inbox?conversation="
            f"{conversation_id}"
        )

    @classmethod
    def _sort_key(
        cls,
        item,
    ):
        due_value = (
            item.due_at.timestamp()
            if item.due_at is not None
            else float("inf")
        )

        created_value = (
            item.created_at.timestamp()
            if item.created_at is not None
            else float("inf")
        )

        return (
            cls.DUE_STATE_ORDER[
                item.due_state
            ],
            due_value,
            -int(
                item.priority
                or 0
            ),
            created_value,
            item.work_id,
        )
