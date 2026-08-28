import hashlib
import json

from django.utils import timezone

from knowledge.models import (
    KnowledgeEvidence,
)
from knowledge.services.intelligence_evidence import (
    IntelligenceEvidence,
    IntelligenceEvidenceValidator,
)
from knowledge.services.intelligence_evidence_builders import (
    build_intelligence_evidence,
    intelligence_evidence_title,
)
from knowledge.services.repository import (
    KnowledgeRepository,
)


def _object_type(
    instance,
):
    from actions.models import (
        ActionItem,
        ExpectedResponseItem,
        FollowUpItem,
    )
    from approvals.models import (
        ApprovalItem,
    )

    if isinstance(
        instance,
        ActionItem,
    ):
        return "action"

    if isinstance(
        instance,
        ApprovalItem,
    ):
        return "approval"

    if isinstance(
        instance,
        ExpectedResponseItem,
    ):
        return "expected_response"

    if isinstance(
        instance,
        FollowUpItem,
    ):
        return "followup"

    raise ValueError(
        "Unsupported intelligence object."
    )


def _source_message(
    instance,
):
    object_type = _object_type(
        instance
    )

    if object_type in {
        "action",
        "approval",
    }:
        return instance.message

    if (
        object_type
        == "expected_response"
    ):
        return instance.source_message

    if object_type == "followup":
        return instance.last_message

    return None


def _knowledge_evidence_type(
    object_type,
):
    if object_type == "approval":
        return "APPROVAL"

    return "TASK"


def _hash_contract(
    contract,
):
    serialized = json.dumps(
        contract.to_dict(),
        sort_keys=True,
        separators=(
            ",",
            ":",
        ),
        ensure_ascii=False,
    )

    return hashlib.sha256(
        serialized.encode(
            "utf-8"
        )
    ).hexdigest()


def _current_due_at(
    instance,
):
    """
    Return the authoritative current deadline from the
    existing domain model.

    No duplicate commitment state is introduced.
    """

    from actions.models import (
        ActionItem,
        ExpectedResponseItem,
        FollowUpItem,
    )
    from approvals.models import (
        ApprovalItem,
    )

    if isinstance(
        instance,
        ActionItem,
    ):
        return instance.due_date

    if isinstance(
        instance,
        ApprovalItem,
    ):
        return instance.due_date

    if isinstance(
        instance,
        ExpectedResponseItem,
    ):
        return (
            instance.response_due_at
        )

    if isinstance(
        instance,
        FollowUpItem,
    ):
        return (
            instance.followup_due_at
        )

    return None


def _serialize_due_at(
    value,
):
    if value is None:
        return None

    return value.isoformat()


def _build_deadline_history(
    *,
    instance,
    title,
    source_message,
    deadline_source,
):
    """
    Carry forward deadline history across intelligence
    evidence rows.

    This handles both:

    - same-message Action deadline edits
    - ExpectedResponseItem source-message changes

    Historical rows created before this capability remain
    truthful: if no prior history exists, the currently
    known deadline becomes the first known value.
    """

    previous = (
        KnowledgeEvidence.objects
        .filter(
            organization_id=(
                instance.organization_id
            ),
            title=title,
            is_archived=False,
        )
        .order_by(
            "-updated_at",
            "-created_at",
            "-id",
        )
        .first()
    )

    history = []

    if previous is not None:
        metadata = (
            previous.metadata
            if isinstance(
                previous.metadata,
                dict,
            )
            else {}
        )

        previous_history = (
            metadata.get(
                "deadline_history"
            )
        )

        if isinstance(
            previous_history,
            list,
        ):
            history = [
                dict(item)
                for item
                in previous_history
                if isinstance(
                    item,
                    dict,
                )
            ]

    due_at = _serialize_due_at(
        _current_due_at(
            instance
        )
    )

    last_due_at = (
        history[-1].get(
            "due_at"
        )
        if history
        else object()
    )

    if (
        not history
        or last_due_at != due_at
    ):
        history.append(
            {
                "due_at":
                    due_at,

                "recorded_at":
                    timezone.now()
                    .isoformat(),

                "source":
                    (
                        deadline_source
                        or "system"
                    ),

                "source_message_id":
                    source_message.id,
            }
        )

    return history


def persist_intelligence_evidence(
    instance,
    *,
    evidence_text=None,
    extraction_method=None,
    processing_mode=None,
    provider=None,
    model=None,
    confidence=None,
    deadline_source="extraction",
):
    """
    Persist validated One UCH intelligence provenance in the
    existing KnowledgeEvidence model.

    Idempotency:
    the same business object + current source message updates
    one evidence row rather than creating duplicates.

    Historical source-message changes intentionally create a
    new evidence row, preserving the evidence trail.
    """

    base = (
        build_intelligence_evidence(
            instance
        )
    )

    source_message = (
        _source_message(
            instance
        )
    )

    # KnowledgeEvidence.message is mandatory. Business
    # objects with no communication source remain represented
    # only by the normalized contract.
    if source_message is None:
        return None

    object_type = (
        _object_type(
            instance
        )
    )

    supplied_text = (
        evidence_text
        if evidence_text is not None
        else base.evidence_text
    )

    supplied_text = (
        supplied_text
        or ""
    ).strip()

    method = (
        extraction_method
        or base.extraction_method
    )

    mode = (
        processing_mode
        or base.processing_mode
    )

    resolved_provider = (
        provider
        if provider is not None
        else base.provider
    )

    resolved_model = (
        model
        if model is not None
        else base.model
    )

    resolved_confidence = (
        int(confidence)
        if confidence is not None
        else base.confidence
    )

    evidence_quality = (
        "exact"
        if supplied_text
        else "source_only"
    )

    contract = IntelligenceEvidence(
        object_type=object_type,
        object_id=instance.id,
        organization_id=(
            instance.organization_id
        ),
        source_message_id=(
            source_message.id
        ),
        conversation_id=(
            source_message.conversation_id
        ),
        evidence_text=(
            supplied_text
        ),
        extraction_method=(
            method
        ),
        processing_mode=(
            mode
        ),
        provider=(
            resolved_provider
            or None
        ),
        model=(
            resolved_model
            or None
        ),
        confidence=(
            resolved_confidence
        ),
        evidence_quality=(
            evidence_quality
        ),
    )

    IntelligenceEvidenceValidator.validate(
        contract,
        source_message=(
            source_message
        ),
    )

    title = (
        intelligence_evidence_title(
            object_type,
            instance.id,
        )
    )

    deadline_history = (
        _build_deadline_history(
            instance=instance,
            title=title,
            source_message=(
                source_message
            ),
            deadline_source=(
                deadline_source
            ),
        )
    )

    metadata = {
        "intelligence_object_type":
            object_type,

        "intelligence_object_id":
            instance.id,

        "evidence_text":
            supplied_text,

        "extraction_method":
            method,

        "processing_mode":
            mode,

        "provider":
            resolved_provider
            or None,

        "model":
            resolved_model
            or None,

        "evidence_quality":
            evidence_quality,

        "deadline_history":
            deadline_history,
    }

    evidence_hash = (
        _hash_contract(
            contract
        )
    )

    evidence_type = (
        _knowledge_evidence_type(
            object_type
        )
    )

    repository = (
        KnowledgeRepository()
    )

    existing = (
        KnowledgeEvidence.objects
        .filter(
            organization_id=(
                instance.organization_id
            ),
            message_id=(
                source_message.id
            ),
            evidence_type=(
                evidence_type
            ),
            title=title,
            is_archived=False,
        )
        .first()
    )

    payload = {
        "conversation":
            source_message.conversation,

        "summary":
            supplied_text,

        "resolver_reason":
            (
                "One UCH intelligence "
                "evidence contract."
            ),

        "source_channel":
            (
                source_message.platform
                or "system"
            ),

        "resolver_version":
            "intelligence-1",

        "ai_provider":
            (
                resolved_provider
                or "none"
            ),

        "evidence_hash":
            evidence_hash,

        "confidence":
            resolved_confidence,

        "metadata":
            metadata,

        "is_active":
            True,

        "is_archived":
            False,
    }

    if existing is not None:
        return (
            repository.evidence.update(
                existing,
                **payload,
            )
        )

    return (
        repository.create_evidence(
            organization=(
                instance.organization
            ),
            business_object=None,
            person=None,
            conversation=(
                source_message.conversation
            ),
            message=source_message,
            evidence_type=(
                evidence_type
            ),
            title=title,
            summary=(
                supplied_text
            ),
            resolver_reason=(
                "One UCH intelligence "
                "evidence contract."
            ),
            source_channel=(
                source_message.platform
                or "system"
            ),
            resolver_version=(
                "intelligence-1"
            ),
            ai_provider=(
                resolved_provider
                or "none"
            ),
            evidence_hash=(
                evidence_hash
            ),
            confidence=(
                resolved_confidence
            ),
            metadata=metadata,
        )
    )
