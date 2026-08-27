from celery import shared_task

from inbox.models import InboxMessage

from actions.models import ExpectedResponseItem
from actions.expected_response_resolution import (
    resolve_expected_responses_for_message,
)
from actions.services.expected_response_extractor import (
    detect_expected_response,
)
from actions.services.reply_text import (
    extract_new_reply_text,
)


@shared_task
def analyze_new_expected_responses(
    message_ids=None,
):
    """
    Analyze messages for expected-response lifecycle.

    Lifecycle rules:

    1. Drafts are excluded.

    2. A new explicit commitment in a conversation updates
       the existing active waiting obligation instead of
       creating another active waiting row.

    3. A later inbound message that is not itself a new
       expected-response commitment may resolve existing
       waiting obligations.

    4. Outbound messages never resolve a waiting obligation.

    5. Outbound messages create expected-response state only
       when they explicitly request a later response.

    6. Every processed eligible message is marked analyzed.
    """

    messages = InboxMessage.objects.filter(
        expected_response_analyzed=False,
        is_draft=False,
    )

    if message_ids is not None:
        messages = messages.filter(
            id__in=message_ids
        )

    messages = messages.select_related(
        "conversation",
        "organization",
        "user",
    ).order_by(
        "received_at",
        "id",
    )

    processed_count = 0

    for msg in messages:
        subject = msg.subject or ""
        body = msg.body or ""

        analysis_body = extract_new_reply_text(
            body
        )

        result = detect_expected_response(
            subject,
            analysis_body,
            reference_time=msg.received_at,
        )

        should_create = False

        if result and msg.conversation_id:
            normalized = (
                f"{subject} {analysis_body}"
            ).lower()

            if msg.direction == "inbound":
                should_create = True

            elif msg.direction == "outbound":
                should_create = any(
                    marker in normalized
                    for marker in (
                        "please let me know",
                        "kindly let me know",
                        "let us know",
                    )
                )

        # --------------------------------------------------
        # Resolution
        #
        # A message carrying a fresh commitment should update
        # the existing wait rather than resolve it first.
        #
        # Only a later inbound non-commitment message is
        # eligible to close existing waiting state.
        # --------------------------------------------------

        if (
            msg.direction == "inbound"
            and not should_create
        ):
            resolve_expected_responses_for_message(
                msg
            )

        # --------------------------------------------------
        # Persistence
        #
        # At most one active waiting ExpectedResponseItem is
        # maintained per conversation at application level.
        # --------------------------------------------------

        if should_create:
            existing = (
                ExpectedResponseItem.objects
                .filter(
                    conversation_id=(
                        msg.conversation_id
                    ),
                    status="waiting",
                )
                .order_by(
                    "-created_at"
                )
                .first()
            )

            if existing:
                existing.source_message = msg
                existing.user = msg.user
                existing.organization = (
                    msg.organization
                )

                new_expected_from = (
                    result.get(
                        "expected_from"
                    )
                )

                if new_expected_from:
                    existing.expected_from = (
                        new_expected_from
                    )

                existing.evidence_text = (
                    result.get(
                        "evidence_text"
                    )
                    or ""
                )

                new_due_at = (
                    result.get(
                        "response_due_at"
                    )
                )

                if new_due_at is not None:
                    existing.response_due_at = (
                        new_due_at
                    )

                existing.save(
                    update_fields=[
                        "source_message",
                        "user",
                        "organization",
                        "expected_from",
                        "evidence_text",
                        "response_due_at",
                        "updated_at",
                    ]
                )

            else:
                ExpectedResponseItem.objects.create(
                    user=msg.user,
                    organization=(
                        msg.organization
                    ),
                    conversation=(
                        msg.conversation
                    ),
                    source_message=msg,
                    expected_from=(
                        result.get(
                            "expected_from"
                        )
                    ),
                    evidence_text=(
                        result.get(
                            "evidence_text"
                        )
                        or ""
                    ),
                    response_due_at=(
                        result.get(
                            "response_due_at"
                        )
                    ),
                    status="waiting",
                )

        msg.expected_response_analyzed = True

        msg.save(
            update_fields=[
                "expected_response_analyzed"
            ]
        )

        processed_count += 1

    return processed_count
