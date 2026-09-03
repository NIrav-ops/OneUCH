from workflow.services.ai.governance.execution_policy import AIExecutionPolicy
from celery import shared_task
from django.conf import settings
from django.db.models import F
from django.utils import timezone

from inbox.models import InboxMessage

from actions.models import (
    ActionItem,
    AIActionCandidate,
    AIActionAnalysisState,
    ActionReviewCandidateOccurrence,
)

from actions.services.extractor import (
    extract_actions,
)

from actions.services.ai_extractor import (
    extract_actions_with_ai_result,
)

from actions.services.extraction_policy import (
    decide_ai_action,
)

from timeline.services import (
    create_timeline_event,
)

from actions.services.ai_retry_policy import (
    calculate_ai_retry,
    can_attempt_ai_analysis,
)

from actions.services.ai_account_policy import (
    is_ai_allowed_for_message,
)

from knowledge.services.intelligence_evidence_persistence import (
    persist_intelligence_evidence,
)

from workflow.services.review_candidate_identity import (
    build_candidate_fingerprint,
    is_shared_mail_domain,
    normalize_sender_email,
    normalize_source_domain,
)

def _create_action(
    *,
    msg,
    item,
    source_type="email",
):
    """
    Persist one confirmed Action.

    Confirmed Actions use the same ActionItem persistence
    path after governed promotion.
    """

    action_obj, created = (
        ActionItem.objects.get_or_create(
            message=msg,
            title=item["title"],
            defaults={
                "user": msg.user,
                "organization": msg.organization,
                "description": item.get(
                    "description",
                    "",
                ),
                "priority": item.get(
                    "priority",
                    0,
                ),
                "due_date": item.get(
                    "due_date"
                ),
                "confidence_score": item.get(
                    "confidence_score",
                    0,
                ),
                "source_type": source_type,
            },
        )
    )

    persist_intelligence_evidence(
        action_obj,
        evidence_text=(
            item.get(
                "evidence",
                "",
            )
        ),
        extraction_method=(
            "ai"
            if source_type == "ai"
            else "deterministic"
        ),
        processing_mode=(
            item.get(
                "processing_mode"
            )
            or (
                "unknown"
                if source_type == "ai"
                else "deterministic"
            )
        ),
        provider=(
            item.get(
                "provider"
            )
        ),
        model=(
            item.get(
                "model"
            )
        ),
        confidence=(
            item.get(
                "confidence_score",
                action_obj.confidence_score,
            )
        ),
    )

    if created and msg.conversation:
        create_timeline_event(
            conversation=msg.conversation,
            event_type="action_created",
            title="Action generated",
            details={
                "action_id": action_obj.id,
                "action_title": action_obj.title,
            },
        )

    return action_obj, created


def _create_review_candidate(
    *,
    msg,
    item,
    extraction_method,
):
    """
    Create or observe one governed Action review candidate.

    Dedupe is deliberately scoped to:
        user
        organization
        extraction method
        normalized sender domain
        conservative evidence fingerprint

    The same request from another domain remains independent.
    """

    title = item["title"]

    evidence = item.get(
        "evidence",
        "",
    )

    source_domain = (
        normalize_source_domain(
            msg.sender
        )
    )

    sender_identity = (
        normalize_sender_email(
            msg.sender
        )
    )

    fingerprint_identity = (
        sender_identity
        if is_shared_mail_domain(
            source_domain
        )
        else ""
    )

    fingerprint = (
        build_candidate_fingerprint(
            title=title,
            evidence=evidence,
            source_identity=(
                fingerprint_identity
            ),
        )
    )

    defaults = {
        "message": msg,
        "title": title,
        "description": item.get(
            "description",
            "",
        ),
        "owner_reference": (
            item.get(
                "owner_reference"
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
        "confidence_score": item.get(
            "confidence_score",
            0,
        ),
        "evidence": evidence,
        "reason": item.get(
            "reason",
            "",
        ),
        "provider": (
            item.get(
                "provider"
            )
            or ""
        ),
        "model": (
            item.get(
                "model"
            )
            or ""
        ),
        "extraction_method":
            extraction_method,
        "source_domain":
            source_domain,
        "candidate_fingerprint":
            fingerprint,
        "occurrence_count":
            1,
        "last_seen_at":
            msg.received_at,
    }

    if (
        source_domain
        and fingerprint
    ):
        candidate, created = (
            AIActionCandidate.objects
            .get_or_create(
                user=msg.user,
                organization=(
                    msg.organization
                ),
                source_domain=(
                    source_domain
                ),
                candidate_fingerprint=(
                    fingerprint
                ),
                defaults=defaults,
            )
        )
    else:
        candidate, created = (
            AIActionCandidate.objects
            .get_or_create(
                message=msg,
                title=title,
                defaults={
                    key: value
                    for key, value
                    in defaults.items()
                    if key not in {
                        "message",
                        "title",
                    }
                },
            )
        )

    occurrence, occurrence_created = (
        ActionReviewCandidateOccurrence
        .objects
        .get_or_create(
            candidate=candidate,
            message=msg,
            defaults={
                "extraction_method":
                    extraction_method,
                "source_domain":
                    source_domain,
                "observed_at":
                    msg.received_at,
            },
        )
    )

    if (
        occurrence_created
        and not created
    ):
        prior_occurrence_exists = (
            candidate
            .occurrences
            .exclude(
                pk=occurrence.pk
            )
            .exists()
        )

        if prior_occurrence_exists:
            (
                AIActionCandidate.objects
                .filter(
                    pk=candidate.pk
                )
                .update(
                    occurrence_count=(
                        F(
                            "occurrence_count"
                        )
                        + 1
                    )
                )
            )

    if (
        candidate.last_seen_at is None
        or
        msg.received_at
        > candidate.last_seen_at
    ):
        (
            AIActionCandidate.objects
            .filter(
                pk=candidate.pk
            )
            .update(
                last_seen_at=(
                    msg.received_at
                )
            )
        )

    candidate.refresh_from_db()

    return (
        candidate,
        created,
    )


def _create_ai_review_candidate(
    *,
    msg,
    item,
):
    """
    Backwards-compatible AI wrapper.

    AI remains one provenance type inside the governed
    review-candidate architecture.
    """

    return _create_review_candidate(
        msg=msg,
        item=item,
        extraction_method="ai",
    )

@shared_task
def analyze_new_messages(
    message_ids=None,
):

    messages = InboxMessage.objects.filter(
        action_analyzed=False,
        is_draft=False,
        direction="inbound",
    )

    if message_ids is not None:
        messages = messages.filter(
            id__in=message_ids
        )

    messages = messages.select_related(
        "conversation",
        "organization",
        "user",
    )

    processed_count = 0

    for msg in messages:

        subject = msg.subject or ""
        body = msg.body or ""

        # --------------------------------------------------
        # 1. Deterministic extraction stays authoritative.
        # --------------------------------------------------

        deterministic_actions = (
            extract_actions(
                subject,
                body,
                reference_time=msg.received_at,
            )
        )

        if deterministic_actions:

            for item in deterministic_actions:
                _create_action(
                    msg=msg,
                    item=item,
                    source_type="email",
                )

            msg.action_analyzed = True

            msg.save(
                update_fields=[
                    "action_analyzed"
                ]
            )

            processed_count += 1
            continue

        # --------------------------------------------------
        # 2. AI is feature-flagged.
        #
        # When disabled, preserve the existing deterministic
        # behavior exactly: no deterministic action means
        # the message is considered analyzed.
        # --------------------------------------------------

        if not settings.ACTION_AI_ENABLED:

            msg.action_analyzed = True

            msg.save(
                update_fields=[
                    "action_analyzed"
                ]
            )

            processed_count += 1
            continue

        if not is_ai_allowed_for_message(
            message=msg,
            allowed_account_ids=(
                settings
                .ACTION_AI_ALLOWED_ACCOUNT_IDS
            ),
        ):

            msg.action_analyzed = True

            msg.save(
                update_fields=[
                    "action_analyzed"
                ]
            )

            processed_count += 1
            continue

        # --------------------------------------------------
        # 2B. Global AI execution governance.
        #
        # A policy block is intentional and terminal for
        # this analysis pass. It must NOT create provider
        # retry state.
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

            msg.action_analyzed = True

            msg.save(
                update_fields=[
                    "action_analyzed"
                ]
            )

            processed_count += 1
            continue

        # --------------------------------------------------
        # 3. Semantic AI fallback.
        # --------------------------------------------------

        retry_state = (
            AIActionAnalysisState.objects.filter(
                message=msg,
            )
            .first()
        )

        if not can_attempt_ai_analysis(
            retry_state
        ):
            continue

        ai_result = (
            extract_actions_with_ai_result(
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
                    settings.ONEUCH_AI_PROVIDER
                ),
                model=(
                    settings.ONEUCH_AI_MODEL
                ),
                message_id=msg.id,
                reference_time=(
                    msg.received_at
                ),
            )
        )

        # --------------------------------------------------
        # 4. Provider/parser failure.
        #
        # Do NOT mark the message analyzed.
        # Leaving it pending allows a later controlled retry.
        # --------------------------------------------------

        if not ai_result.success:

            now = timezone.now()

            retry_state, _ = (
                AIActionAnalysisState
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
                    .ACTION_AI_MAX_ATTEMPTS
                ),
                base_seconds=(
                    settings
                    .ACTION_AI_RETRY_BASE_SECONDS
                ),
                max_seconds=(
                    settings
                    .ACTION_AI_RETRY_MAX_SECONDS
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

            retry_state.last_attempt_at = now

            retry_state.next_retry_at = (
                retry[
                    "next_retry_at"
                ]
            )

            retry_state.last_error = (
                ai_result.error
                or "Unknown AI extraction failure"
            )

            retry_state.provider = (
                ai_result.provider
                or settings.ONEUCH_AI_PROVIDER
            )

            retry_state.model = (
                ai_result.model
                or settings.ONEUCH_AI_MODEL
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

        AIActionAnalysisState.objects.filter(
            message=msg,
        ).delete()

        # --------------------------------------------------
        # 5. Apply review-only policy to every validated AI
        # candidate.
        #
        # AI output must never create ActionItem directly.
        # Human promotion from AIActionCandidate is the only
        # path from AI suggestion to confirmed Action.
        # --------------------------------------------------

        for item in ai_result.candidates:

            decision = decide_ai_action(
                confidence_score=item.get(
                    "confidence_score",
                    0,
                ),
                review_threshold=(
                    settings
                    .ACTION_AI_REVIEW_THRESHOLD
                ),
            )

            if (
                decision.decision
                == "review"
            ):
                _create_ai_review_candidate(
                    msg=msg,
                    item=item,
                )

            # "ignore" intentionally performs no write.

        # A successful AI evaluation, including an empty
        # candidate list, means semantic analysis completed.
        msg.action_analyzed = True

        msg.save(
            update_fields=[
                "action_analyzed"
            ]
        )

        processed_count += 1

    return processed_count
# Register dedicated Follow-up task with Celery autodiscovery.
from actions.followup_tasks import analyze_new_followups  # noqa: F401

# Register dedicated Expected Response task with Celery autodiscovery.
from actions.expected_response_tasks import analyze_new_expected_responses  # noqa: F401
