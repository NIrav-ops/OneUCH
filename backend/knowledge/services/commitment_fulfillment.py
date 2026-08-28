from dataclasses import (
    asdict,
    dataclass,
)
from typing import Optional

from actions.models import (
    ActionItem,
    ExpectedResponseItem,
)
from actions.services.reply_text import (
    extract_new_reply_text,
)
from timeline.models import TimelineEvent


@dataclass(frozen=True)
class CommitmentFulfillment:
    """
    Read-only normalized fulfillment evidence.

    Important distinction:

    manual_attestation
        A user marked work complete.
        This proves the status transition, not delivery.

    message_confirmed
        A real communication message fulfilled the
        obligation.

    status_only
        Historical completed state exists but stronger
        provenance was never persisted.
    """

    method: str
    quality: str

    fulfilled_at: object

    source_message_id: Optional[int]
    evidence_text: str

    actor_user_id: Optional[int]
    actor_email: Optional[str]

    def to_dict(self):
        return asdict(
            self
        )


def _empty():
    return CommitmentFulfillment(
        method="none",
        quality="none",
        fulfilled_at=None,
        source_message_id=None,
        evidence_text="",
        actor_user_id=None,
        actor_email=None,
    )


def _action_completion_event(
    action,
):
    """
    Find the latest completion attestation for this exact
    ActionItem.

    TimelineEvent is already the canonical conversation
    event trail; no duplicate fulfillment table is needed.
    """

    if (
        action.message_id is None
        or action.message is None
        or action.message.conversation_id
        is None
    ):
        return None

    events = (
        TimelineEvent.objects
        .filter(
            conversation_id=(
                action.message
                .conversation_id
            ),
            event_type=(
                "action_completed"
            ),
        )
        .order_by(
            "-event_at",
            "-created_at",
            "-id",
        )
    )

    for event in events:
        details = (
            event.details
            if isinstance(
                event.details,
                dict,
            )
            else {}
        )

        try:
            event_action_id = int(
                details.get(
                    "action_id"
                )
            )
        except (
            TypeError,
            ValueError,
        ):
            continue

        if event_action_id == action.id:
            return event

    return None


def build_action_fulfillment(
    action,
):
    """
    Completed ActionItem means One UCH has a completion
    state.

    If an action_completed TimelineEvent exists, expose it
    as a manual attestation.

    Never claim the original request email is proof that the
    work was actually delivered.
    """

    if action.status != "completed":
        return _empty()

    event = (
        _action_completion_event(
            action
        )
    )

    if event is None:
        return CommitmentFulfillment(
            method="status_only",
            quality="status_only",
            fulfilled_at=(
                action.completed_at
            ),
            source_message_id=None,
            evidence_text="",
            actor_user_id=None,
            actor_email=None,
        )

    details = (
        event.details
        if isinstance(
            event.details,
            dict,
        )
        else {}
    )

    actor_user_id = (
        details.get(
            "completed_by_user_id"
        )
    )

    try:
        actor_user_id = (
            int(actor_user_id)
            if actor_user_id
            is not None
            else None
        )
    except (
        TypeError,
        ValueError,
    ):
        actor_user_id = None

    actor_email = (
        str(
            details.get(
                "completed_by"
            )
            or ""
        )
        .strip()
        .lower()
        or None
    )

    return CommitmentFulfillment(
        method="manual_attestation",
        quality="attested",
        fulfilled_at=(
            action.completed_at
            or event.event_at
            or event.created_at
        ),
        source_message_id=None,
        evidence_text="",
        actor_user_id=(
            actor_user_id
        ),
        actor_email=(
            actor_email
        ),
    )


def build_expected_response_fulfillment(
    item,
):
    """
    ExpectedResponseItem has stronger fulfillment evidence:
    the inbound response message itself.

    When resolved_by_message is available, the fulfillment
    is communication-confirmed.
    """

    if item.status != "received":
        return _empty()

    message = (
        item.resolved_by_message
    )

    if message is None:
        return CommitmentFulfillment(
            method="status_only",
            quality="status_only",
            fulfilled_at=(
                item.resolved_at
            ),
            source_message_id=None,
            evidence_text="",
            actor_user_id=None,
            actor_email=None,
        )

    reply_text = (
        extract_new_reply_text(
            message.body
            or ""
        )
        .strip()
    )

    if not reply_text:
        reply_text = (
            message.subject
            or ""
        ).strip()

    return CommitmentFulfillment(
        method="message_confirmed",
        quality="message_confirmed",
        fulfilled_at=(
            item.resolved_at
            or message.received_at
        ),
        source_message_id=(
            message.id
        ),
        evidence_text=(
            reply_text
        ),
        actor_user_id=None,
        actor_email=None,
    )


def build_commitment_fulfillment(
    instance,
):
    if isinstance(
        instance,
        ActionItem,
    ):
        return build_action_fulfillment(
            instance
        )

    if isinstance(
        instance,
        ExpectedResponseItem,
    ):
        return (
            build_expected_response_fulfillment(
                instance
            )
        )

    raise ValueError(
        "Unsupported commitment object."
    )
