from knowledge.models import (
    KnowledgeEvidence,
)

from knowledge.services.intelligence_evidence import (
    IntelligenceEvidence,
    IntelligenceEvidenceError,
    IntelligenceEvidenceValidator,
)


INTELLIGENCE_EVIDENCE_PREFIX = (
    "ONEUCH-INTELLIGENCE"
)


def intelligence_evidence_title(
    object_type,
    object_id,
):
    return (
        f"{INTELLIGENCE_EVIDENCE_PREFIX}:"
        f"{object_type}:{object_id}"
    )


def _require_saved(
    instance,
    *,
    object_name,
):
    if (
        instance is None
        or instance.pk is None
    ):
        raise IntelligenceEvidenceError(
            f"{object_name} must be saved "
            "before evidence can be built."
        )


def _source_type_provenance(
    source_type,
):
    normalized = (
        str(source_type or "")
        .strip()
        .lower()
    )

    if normalized == "ai":
        return {
            "extraction_method": "ai",
            "processing_mode": "unknown",
            "provider": None,
            "model": None,
        }

    if normalized == "email":
        return {
            "extraction_method":
                "deterministic",
            "processing_mode":
                "deterministic",
            "provider": None,
            "model": None,
        }

    if normalized == "manual":
        return {
            "extraction_method": "manual",
            "processing_mode": "unknown",
            "provider": None,
            "model": None,
        }

    return {
        "extraction_method": "system",
        "processing_mode": "unknown",
        "provider": None,
        "model": None,
    }


def _normalize_evidence_text(
    value,
):
    """
    Normalize evidence only for truthful source containment
    checks.

    This intentionally mirrors the strict validator's
    whitespace/case normalization without changing the
    validator itself.
    """
    return " ".join(
        str(
            value or ""
        ).split()
    ).lower()


def _source_contains_exact_text(
    *,
    source_message,
    evidence_text,
):
    """
    Return True only when legacy evidence text is actually
    present in the source communication.

    Historical ExpectedResponseItem.evidence_text values
    predate the strict IntelligenceEvidence contract and may
    contain extracted/paraphrased obligation text.

    Such text remains useful as the obligation itself, but
    must not be represented as a verbatim quote.
    """
    normalized_evidence = (
        _normalize_evidence_text(
            evidence_text
        )
    )

    if (
        source_message is None
        or
        not normalized_evidence
    ):
        return False

    source_text = (
        _normalize_evidence_text(
            " ".join(
                [
                    source_message.subject
                    or "",
                    source_message.body
                    or "",
                ]
            )
        )
    )

    return (
        normalized_evidence
        in source_text
    )


def _persisted_evidence(
    *,
    instance,
    object_type,
    source_message,
):
    """
    Return persisted intelligence evidence for the current
    source message when 05.2C has captured it.

    Historical objects without a persisted evidence record
    continue through the truthful fallback builders below.
    """

    if source_message is None:
        return None

    row = (
        KnowledgeEvidence.objects
        .filter(
            organization_id=(
                instance.organization_id
            ),
            message_id=(
                source_message.id
            ),
            title=(
                intelligence_evidence_title(
                    object_type,
                    instance.id,
                )
            ),
            is_active=True,
            is_archived=False,
        )
        .order_by(
            "-created_at"
        )
        .first()
    )

    if row is None:
        return None

    metadata = (
        row.metadata
        if isinstance(
            row.metadata,
            dict,
        )
        else {}
    )

    evidence_text = (
        metadata.get(
            "evidence_text"
        )
        or row.summary
        or ""
    ).strip()

    provider = (
        metadata.get(
            "provider"
        )
    )

    if (
        not provider
        and row.ai_provider
        and row.ai_provider != "none"
    ):
        provider = (
            row.ai_provider
        )

    evidence_quality = (
        metadata.get(
            "evidence_quality"
        )
        or (
            "exact"
            if evidence_text
            else "source_only"
        )
    )

    evidence = IntelligenceEvidence(
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
            evidence_text
        ),
        extraction_method=(
            metadata.get(
                "extraction_method"
            )
            or "system"
        ),
        processing_mode=(
            metadata.get(
                "processing_mode"
            )
            or "unknown"
        ),
        provider=provider,
        model=(
            metadata.get(
                "model"
            )
            or None
        ),
        confidence=int(
            row.confidence
            or 0
        ),
        evidence_quality=(
            evidence_quality
        ),
    )

    return (
        IntelligenceEvidenceValidator
        .validate(
            evidence,
            source_message=(
                source_message
            ),
        )
    )


def build_action_evidence(
    action,
):
    _require_saved(
        action,
        object_name="ActionItem",
    )

    source_message = (
        action.message
    )

    persisted = _persisted_evidence(
        instance=action,
        object_type="action",
        source_message=source_message,
    )

    if persisted is not None:
        return persisted

    provenance = (
        _source_type_provenance(
            action.source_type
        )
    )

    evidence = IntelligenceEvidence(
        object_type="action",
        object_id=action.id,
        organization_id=(
            action.organization_id
        ),
        source_message_id=(
            source_message.id
            if source_message is not None
            else None
        ),
        conversation_id=(
            source_message.conversation_id
            if source_message is not None
            else None
        ),
        evidence_text="",
        extraction_method=(
            provenance[
                "extraction_method"
            ]
        ),
        processing_mode=(
            provenance[
                "processing_mode"
            ]
        ),
        provider=(
            provenance["provider"]
        ),
        model=(
            provenance["model"]
        ),
        confidence=int(
            action.confidence_score
            or 0
        ),
        evidence_quality=(
            "source_only"
            if source_message is not None
            else "none"
        ),
    )

    return (
        IntelligenceEvidenceValidator
        .validate(
            evidence,
            source_message=(
                source_message
            ),
        )
    )


def build_approval_evidence(
    approval,
):
    _require_saved(
        approval,
        object_name="ApprovalItem",
    )

    source_message = (
        approval.message
    )

    persisted = _persisted_evidence(
        instance=approval,
        object_type="approval",
        source_message=source_message,
    )

    if persisted is not None:
        return persisted

    provenance = (
        _source_type_provenance(
            approval.source_type
        )
    )

    conversation_id = (
        source_message.conversation_id
        if source_message is not None
        else approval.conversation_id
    )

    evidence = IntelligenceEvidence(
        object_type="approval",
        object_id=approval.id,
        organization_id=(
            approval.organization_id
        ),
        source_message_id=(
            source_message.id
            if source_message is not None
            else None
        ),
        conversation_id=(
            conversation_id
        ),
        evidence_text="",
        extraction_method=(
            provenance[
                "extraction_method"
            ]
        ),
        processing_mode=(
            provenance[
                "processing_mode"
            ]
        ),
        provider=(
            provenance["provider"]
        ),
        model=(
            provenance["model"]
        ),
        confidence=int(
            approval.confidence_score
            or 0
        ),
        evidence_quality=(
            "source_only"
            if source_message is not None
            else "none"
        ),
    )

    return (
        IntelligenceEvidenceValidator
        .validate(
            evidence,
            source_message=(
                source_message
            ),
        )
    )


def build_expected_response_evidence(
    item,
):
    _require_saved(
        item,
        object_name=(
            "ExpectedResponseItem"
        ),
    )

    source_message = (
        item.source_message
    )

    persisted = _persisted_evidence(
        instance=item,
        object_type=(
            "expected_response"
        ),
        source_message=source_message,
    )

    if persisted is not None:
        return persisted

    legacy_evidence_text = (
        item.evidence_text
        or ""
    ).strip()

    exact_evidence = (
        _source_contains_exact_text(
            source_message=(
                source_message
            ),
            evidence_text=(
                legacy_evidence_text
            ),
        )
    )

    # Historical ExpectedResponseItem.evidence_text predates
    # the strict evidence contract. If it is not a verifiable
    # substring of the source message, preserve the source
    # linkage but do not fabricate an exact quotation.
    evidence_text = (
        legacy_evidence_text
        if exact_evidence
        else ""
    )

    evidence = IntelligenceEvidence(
        object_type=(
            "expected_response"
        ),
        object_id=item.id,
        organization_id=(
            item.organization_id
        ),
        source_message_id=(
            source_message.id
        ),
        conversation_id=(
            item.conversation_id
        ),
        evidence_text=(
            evidence_text
        ),
        extraction_method=(
            "deterministic"
        ),
        processing_mode=(
            "deterministic"
        ),
        provider=None,
        model=None,
        confidence=100,
        evidence_quality=(
            "exact"
            if exact_evidence
            else "source_only"
        ),
    )

    return (
        IntelligenceEvidenceValidator
        .validate(
            evidence,
            source_message=(
                source_message
            ),
        )
    )


def build_followup_evidence(
    item,
):
    _require_saved(
        item,
        object_name="FollowUpItem",
    )

    source_message = (
        item.last_message
    )

    persisted = _persisted_evidence(
        instance=item,
        object_type="followup",
        source_message=source_message,
    )

    if persisted is not None:
        return persisted

    evidence = IntelligenceEvidence(
        object_type="followup",
        object_id=item.id,
        organization_id=(
            item.organization_id
        ),
        source_message_id=(
            source_message.id
        ),
        conversation_id=(
            item.conversation_id
        ),
        evidence_text="",
        extraction_method=(
            "deterministic"
        ),
        processing_mode=(
            "deterministic"
        ),
        provider=None,
        model=None,
        confidence=100,
        evidence_quality=(
            "source_only"
        ),
    )

    return (
        IntelligenceEvidenceValidator
        .validate(
            evidence,
            source_message=(
                source_message
            ),
        )
    )


def build_intelligence_evidence(
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
        return build_action_evidence(
            instance
        )

    if isinstance(
        instance,
        ApprovalItem,
    ):
        return build_approval_evidence(
            instance
        )

    if isinstance(
        instance,
        ExpectedResponseItem,
    ):
        return (
            build_expected_response_evidence(
                instance
            )
        )

    if isinstance(
        instance,
        FollowUpItem,
    ):
        return build_followup_evidence(
            instance
        )

    raise IntelligenceEvidenceError(
        "Unsupported intelligence "
        f"object: {instance.__class__.__name__}"
    )
