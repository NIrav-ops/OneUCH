from workflow.services.ai.governance.execution_policy import AIExecutionPolicy
from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail
from django.contrib.auth import get_user_model
from django.utils import timezone

from inbox.models import InboxMessage
from notifications.services import create_notification
from approvals.models import (
    ApprovalItem,
    AIApprovalCandidate,
    AIApprovalAnalysisState,
)
from timeline.services import create_timeline_event

from approvals.services.extractor import (
    extract_approvals,
)
from approvals.services.ai_extractor import (
    extract_approvals_with_ai_result,
)
from approvals.services.extraction_policy import (
    decide_ai_approval,
)
from approvals.services.ai_retry_policy import (
    calculate_ai_retry,
    can_attempt_ai_analysis,
)
from approvals.services.ai_account_policy import (
    is_ai_allowed_for_message,
)


User = get_user_model()



def _create_approval(
    *,
    msg,
    item,
    source_type="email",
):
    approval_obj, created = (
        ApprovalItem.objects.get_or_create(
            message=msg,
            title=item["title"],
            defaults={
                "user": msg.user,
                "organization": (
                    msg.organization
                ),
                "conversation": (
                    msg.conversation
                ),
                "description": item.get(
                    "description",
                    "",
                ),
                "requested_by": (
                    msg.sender
                ),
                "status": "pending",
                "source_type": source_type,
                "priority": item.get(
                    "priority",
                    0,
                ),
                "confidence_score": (
                    item.get(
                        "confidence_score",
                        0,
                    )
                ),
                "due_date": item.get(
                    "due_date"
                ),
            },
        )
    )

    if (
        created
        and msg.conversation
    ):
        create_timeline_event(
            conversation=(
                msg.conversation
            ),
            event_type=(
                "approval_created"
            ),
            title=(
                "Approval created"
            ),
            details={
                "approval_id": (
                    approval_obj.id
                ),
                "title": (
                    approval_obj.title
                ),
            },
        )

    return (
        approval_obj,
        created,
    )


def _create_ai_review_candidate(
    *,
    msg,
    item,
):
    return (
        AIApprovalCandidate.objects
        .get_or_create(
            message=msg,
            title=item["title"],
            defaults={
                "user": msg.user,
                "organization": (
                    msg.organization
                ),
                "description": item.get(
                    "description",
                    "",
                ),
                "approver_reference": (
                    item.get(
                        "approver_reference"
                    )
                    or ""
                ),
                "due_date": item.get(
                    "due_date"
                ),
                "priority": item.get(
                    "priority",
                    0,
                ),
                "confidence_score": (
                    item.get(
                        "confidence_score",
                        0,
                    )
                ),
                "evidence": item.get(
                    "evidence",
                    "",
                ),
                "reason": item.get(
                    "reason",
                    "",
                ),
                "provider": item.get(
                    "provider",
                    "",
                )
                or "",
                "model": item.get(
                    "model",
                    "",
                )
                or "",
            },
        )
    )


@shared_task
def analyze_new_approvals(
    message_ids=None,
):

    messages = InboxMessage.objects.filter(
        approval_analyzed=False,
        is_draft=False,
        direction="inbound",
    ).select_related(
        "conversation",
        "organization",
        "user",
        "email_account",
    )

    if message_ids is not None:
        messages = messages.filter(
            id__in=message_ids
        )

    processed_count = 0

    for msg in messages:

        subject = msg.subject or ""
        body = msg.body or ""

        # --------------------------------------------------
        # 1. Deterministic extraction always runs first.
        # --------------------------------------------------

        approvals = extract_approvals(
            subject,
            body,
        )

        if approvals:

            for item in approvals:
                _create_approval(
                    msg=msg,
                    item=item,
                    source_type="email",
                )

            msg.approval_analyzed = True

            msg.save(
                update_fields=[
                    "approval_analyzed"
                ]
            )

            processed_count += 1
            continue

        # --------------------------------------------------
        # 2. Preserve existing behavior when Approval AI is
        # disabled.
        # --------------------------------------------------

        if not settings.APPROVAL_AI_ENABLED:

            msg.approval_analyzed = True

            msg.save(
                update_fields=[
                    "approval_analyzed"
                ]
            )

            processed_count += 1
            continue

        # --------------------------------------------------
        # 3. AI fallback is restricted to explicitly
        # allow-listed connected accounts.
        # --------------------------------------------------

        if not is_ai_allowed_for_message(
            message=msg,
            allowed_account_ids=(
                settings
                .APPROVAL_AI_ALLOWED_ACCOUNT_IDS
            ),
        ):

            msg.approval_analyzed = True

            msg.save(
                update_fields=[
                    "approval_analyzed"
                ]
            )

            processed_count += 1
            continue

        # --------------------------------------------------
        # 3B. Global AI execution governance.
        #
        # Governance prohibition is intentional and must
        # not become a retryable provider failure.
        # --------------------------------------------------

        ai_execution_policy = (
            AIExecutionPolicy.evaluate(
                mode=getattr(
                    settings,
                    "ONEUCH_AI_MODE",
                    "cloud",
                ),
                provider=(
                    settings.ONEUCH_AI_PROVIDER
                ),
            )
        )

        if not ai_execution_policy.allowed:

            msg.approval_analyzed = True

            msg.save(
                update_fields=[
                    "approval_analyzed"
                ]
            )

            processed_count += 1
            continue

        # --------------------------------------------------
        # 4. Retry/cooldown gate.
        # --------------------------------------------------

        retry_state = (
            AIApprovalAnalysisState.objects
            .filter(
                message=msg,
            )
            .first()
        )

        if not can_attempt_ai_analysis(
            retry_state
        ):
            continue

        # --------------------------------------------------
        # 5. Semantic Approval extraction.
        # --------------------------------------------------

        ai_result = (
            extract_approvals_with_ai_result(
                subject=subject,
                body=body,
                sender=(
                    msg.sender
                    or ""
                ),
                recipient=(
                    msg.recipients
                    or ""
                ),
                provider=(
                    settings
                    .ONEUCH_AI_PROVIDER
                ),
                model=(
                    settings
                    .ONEUCH_AI_MODEL
                ),
                message_id=msg.id,
                reference_time=(
                    msg.received_at
                ),
            )
        )

        # --------------------------------------------------
        # 6. Failed provider/parser execution is retryable.
        # Message remains unanalyzed.
        # --------------------------------------------------

        if not ai_result.success:

            now = timezone.now()

            retry_state, _ = (
                AIApprovalAnalysisState
                .objects
                .get_or_create(
                    message=msg,
                    defaults={
                        "organization":
                            msg.organization,
                    },
                )
            )

            attempt_count = (
                retry_state.attempt_count
                + 1
            )

            retry = calculate_ai_retry(
                attempt_count=attempt_count,
                max_attempts=(
                    settings
                    .APPROVAL_AI_MAX_ATTEMPTS
                ),
                base_seconds=(
                    settings
                    .APPROVAL_AI_RETRY_BASE_SECONDS
                ),
                max_seconds=(
                    settings
                    .APPROVAL_AI_RETRY_MAX_SECONDS
                ),
                now=now,
            )

            retry_state.organization = (
                msg.organization
            )

            retry_state.attempt_count = (
                attempt_count
            )

            retry_state.status = (
                retry["status"]
            )

            retry_state.last_attempt_at = (
                now
            )

            retry_state.next_retry_at = (
                retry["next_retry_at"]
            )

            retry_state.last_error = (
                ai_result.error
                or ""
            )

            retry_state.provider = (
                ai_result.provider
                or settings.ONEUCH_AI_PROVIDER
                or ""
            )

            retry_state.model = (
                ai_result.model
                or settings.ONEUCH_AI_MODEL
                or ""
            )

            retry_state.save(
                update_fields=[
                    "organization",
                    "attempt_count",
                    "status",
                    "last_attempt_at",
                    "next_retry_at",
                    "last_error",
                    "provider",
                    "model",
                    "updated_at",
                ]
            )

            continue

        # --------------------------------------------------
        # 7. Successful AI execution clears previous retry
        # state, including successful "no approval".
        # --------------------------------------------------

        AIApprovalAnalysisState.objects.filter(
            message=msg,
        ).delete()

        # --------------------------------------------------
        # 8. Apply Approval-specific confidence policy.
        # --------------------------------------------------

        for item in ai_result.candidates:

            decision = decide_ai_approval(
                confidence_score=item.get(
                    "confidence_score",
                    0,
                ),
                auto_create_threshold=(
                    settings
                    .APPROVAL_AI_AUTO_CREATE_THRESHOLD
                ),
                review_threshold=(
                    settings
                    .APPROVAL_AI_REVIEW_THRESHOLD
                ),
            )

            if (
                decision.decision
                == "auto_create"
            ):
                _create_approval(
                    msg=msg,
                    item=item,
                    source_type="ai",
                )

            elif (
                decision.decision
                == "review"
            ):
                _create_ai_review_candidate(
                    msg=msg,
                    item=item,
                )

        # --------------------------------------------------
        # 9. Successful semantic analysis is final even when
        # it returns no Approval or only ignored candidates.
        # --------------------------------------------------

        msg.approval_analyzed = True

        msg.save(
            update_fields=[
                "approval_analyzed"
            ]
        )

        processed_count += 1

    return processed_count


@shared_task
def send_approval_assignment_notification(
    approval_id,
    assignee_id,
    assigned_by_id,
):

    try:

        approval = (
            ApprovalItem.objects
            .select_related(
                "organization"
            )
            .get(
                id=approval_id
            )
        )

        assignee = User.objects.get(
            id=assignee_id
        )

        assigned_by = User.objects.get(
            id=assigned_by_id
        )

    except Exception as exc:

        return {
            "status": "error",
            "error": str(exc),
        }

    subject = (
        f"New approval assigned: "
        f"{approval.title}"
    )

    message = (
        f"You have been assigned an approval in One UCH.\n\n"
        f"Title: {approval.title}\n"
        f"Organization: {approval.organization.name}\n"
        f"Requested by: {approval.requested_by or 'Unknown'}\n"
        f"Assigned by: {assigned_by.email}\n"
        f"Status: {approval.status}\n\n"
        f"Please review it in the Approval Center."
    )

    create_notification(
        user=assignee,
        type="approval_assigned",
        title=subject,
        message=message,
    )

    if assignee.email:

        send_mail(
            subject=subject,
            message=message,
            from_email=getattr(
                settings,
                "DEFAULT_FROM_EMAIL",
                None,
            ),
            recipient_list=[
                assignee.email
            ],
            fail_silently=True,
        )

    return {
        "status": "sent"
    }