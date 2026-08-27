import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional

from django.utils import timezone

from workflow.services.ai import (
    AIExecutionService,
    AIRequest,
    AIResponseParser,
)


logger = logging.getLogger(__name__)


APPROVAL_AI_PROMPT_VERSION = (
    "approval-extraction-v1"
)


@dataclass(frozen=True)
class AIApprovalExtractionResult:
    success: bool
    candidates: List[dict] = field(
        default_factory=list
    )
    error: Optional[str] = None
    provider: Optional[str] = None
    model: Optional[str] = None


SYSTEM_PROMPT = """
You are the Approval Intelligence engine for One UCH.

Your job is to identify genuine, currently active requests
for authorization, permission, approval, sign-off, go-ahead,
or a decision that allows business work to proceed.

An Approval exists when a recipient or their organization is
being asked to make an authorization or decision such as:
- approving a proposal, purchase, deployment, access, or change
- providing formal sign-off
- giving permission or authorization
- giving a go-ahead before work can proceed
- deciding whether an activity may proceed

Do NOT create an Approval for:
- informational statements
- FYI messages
- plain review requests that do not request authorization
- acknowledgements
- receipt confirmations
- already-approved or completed decisions
- historical approval references
- statements describing approval by another person or team
- conditional statements such as "if approved"
- quoted previous requests unless the request is clearly still active
- email signatures or disclaimers

Distinguish authorization from ordinary work.

Examples:
"Please review the proposal."
is NOT necessarily an Approval.

"Please approve the proposal."
IS an Approval.

"I confirm receipt."
is NOT an Approval.

"Can we proceed with production deployment?"
IS an Approval request.

Precision is more important than recall.

If there is no genuine active Approval request, return an
empty actions list.

Every proposed Approval must include evidence containing the
exact words from the supplied message that justify it.

Do not invent approvers, deadlines, facts, or evidence.
""".strip()


APPROVAL_RESPONSE_SCHEMA = {
    "type": "object",
    "required": [
        "actions",
    ],
    "additionalProperties": False,
    "properties": {
        "actions": {
            "type": "array",
            "items": {
                "type": "object",
                "required": [
                    "title",
                    "description",
                    "priority",
                    "owner_reference",
                    "due_date",
                    "confidence",
                    "metadata",
                ],
                "additionalProperties": False,
                "properties": {
                    "title": {
                        "type": "string",
                    },
                    "description": {
                        "type": "string",
                    },
                    "priority": {
                        "type": "integer",
                        "minimum": 0,
                        "maximum": 100,
                    },
                    "owner_reference": {
                        "type": [
                            "string",
                            "null",
                        ],
                    },
                    "due_date": {
                        "type": [
                            "string",
                            "null",
                        ],
                    },
                    "confidence": {
                        "type": "number",
                        "minimum": 0,
                        "maximum": 1,
                    },
                    "metadata": {
                        "type": "object",
                        "required": [
                            "evidence",
                            "reason",
                        ],
                        "additionalProperties": False,
                        "properties": {
                            "evidence": {
                                "type": "string",
                            },
                            "reason": {
                                "type": "string",
                            },
                        },
                    },
                },
            },
        },
    },
}


def _build_prompt(
    *,
    subject: str,
    body: str,
    sender: str = "",
    recipient: str = "",
    reference_time=None,
) -> str:

    if reference_time is None:
        reference_time = timezone.now()

    return f"""
Analyze this business communication for Approval requests.

Message reference datetime:
{reference_time.isoformat()}

Interpret relative deadlines such as tomorrow, today,
next Monday, EOD, and similar expressions relative to
this datetime.

Sender:
{sender or "Unknown"}

Recipient:
{recipient or "Unknown"}

Subject:
{subject or "(no subject)"}

Message:
{body or "(empty body)"}

Return an action_list where every entry represents one
Approval request.

For every Approval use:
- title: concise approval or authorization title
- description: what decision or authorization is required
- priority: integer from 0 to 100
- owner_reference: person explicitly asked to approve,
  authorize, sign off, or give the go-ahead; otherwise null
- due_date: ISO-8601 date/datetime only when explicitly stated
- confidence: number between 0 and 1
- metadata.evidence: exact supporting text from the message
- metadata.reason: short explanation of why authorization
  is currently required

If there is no active Approval request, return:
{{"actions": []}}
""".strip()


def _normalize_evidence(
    value,
) -> str:

    if not isinstance(
        value,
        str,
    ):
        return ""

    return " ".join(
        value.split()
    ).strip()


def _validate_evidence(
    evidence: str,
    *,
    subject: str,
    body: str,
) -> bool:

    if not evidence:
        return False

    source = " ".join(
        f"{subject} {body}".split()
    ).lower()

    return (
        evidence.lower()
        in source
    )


def _parse_due_date(
    value: Optional[str],
):

    if not value:
        return None

    if not isinstance(
        value,
        str,
    ):
        return None

    value = value.strip()

    try:
        parsed = datetime.fromisoformat(
            value.replace(
                "Z",
                "+00:00",
            )
        )

    except ValueError:

        try:
            parsed = datetime.strptime(
                value,
                "%Y-%m-%d",
            )

        except ValueError:
            return None

    if timezone.is_naive(
        parsed
    ):
        parsed = timezone.make_aware(
            parsed,
            timezone.get_current_timezone(),
        )

    return parsed


def extract_approvals_with_ai_result(
    *,
    subject: str,
    body: str,
    sender: str = "",
    recipient: str = "",
    provider: str = "mock",
    model: Optional[str] = None,
    message_id: Optional[int] = None,
    reference_time=None,
) -> AIApprovalExtractionResult:
    """
    Return validated semantic Approval candidates.

    This function performs no database writes.

    AI output remains advisory until the approvals domain
    explicitly applies policy to the candidate.
    """

    request = AIRequest(
        prompt=_build_prompt(
            subject=subject,
            body=body,
            sender=sender,
            recipient=recipient,
            reference_time=reference_time,
        ),
        system_prompt=SYSTEM_PROMPT,
        provider=provider,
        model=model,
        temperature=0.0,
        max_tokens=1000,

        # Reuse the generic structured-list contract
        # already supported by One UCH's AI framework.
        response_type="action_list",
        response_schema=(
            APPROVAL_RESPONSE_SCHEMA
        ),
        metadata={
            "domain": "approvals",
            "purpose":
                "semantic_approval_extraction",
            "prompt_version":
                APPROVAL_AI_PROMPT_VERSION,
            "message_id": message_id,
        },
    )

    result = AIExecutionService.execute(
        request,
        provider=provider,
    )

    if not result.success:

        logger.warning(
            "AI Approval extraction failed | "
            "message_id=%s provider=%s error=%s",
            message_id,
            provider,
            result.error,
        )

        return AIApprovalExtractionResult(
            success=False,
            candidates=[],
            error=result.error,
            provider=(
                result.provider
                or provider
            ),
            model=(
                result.model
                or model
            ),
        )

    try:
        parsed = AIResponseParser.parse(
            request,
            result,
        )

    except Exception as exc:

        logger.exception(
            "Unable to parse AI Approval output | "
            "message_id=%s provider=%s",
            message_id,
            provider,
        )

        return AIApprovalExtractionResult(
            success=False,
            candidates=[],
            error=str(exc),
            provider=(
                result.provider
                or provider
            ),
            model=(
                result.model
                or model
            ),
        )

    candidates = []

    for recommendation in parsed.actions:

        title = (
            recommendation.title.strip()
            if isinstance(
                recommendation.title,
                str,
            )
            else ""
        )

        if not title:
            continue

        try:
            confidence = float(
                recommendation.confidence
            )

        except (
            TypeError,
            ValueError,
        ):
            continue

        if (
            confidence < 0
            or confidence > 1
        ):
            continue

        metadata = (
            recommendation.metadata
            if isinstance(
                recommendation.metadata,
                dict,
            )
            else {}
        )

        evidence = _normalize_evidence(
            metadata.get(
                "evidence"
            )
        )

        if not _validate_evidence(
            evidence,
            subject=subject,
            body=body,
        ):

            logger.warning(
                "Rejected AI Approval without "
                "valid source evidence | "
                "message_id=%s title=%s",
                message_id,
                title,
            )

            continue

        try:
            priority = int(
                recommendation.priority
            )

        except (
            TypeError,
            ValueError,
        ):
            priority = 0

        priority = max(
            0,
            min(
                priority,
                100,
            ),
        )

        candidates.append(
            {
                "title": title,
                "description": (
                    recommendation
                    .description
                    .strip()
                    if isinstance(
                        recommendation.description,
                        str,
                    )
                    else ""
                ),
                "priority": priority,

                # Generic AI contract calls this
                # owner_reference. In the Approval
                # domain it means the person explicitly
                # asked to authorize the decision.
                "approver_reference":
                    recommendation.owner_reference,

                "due_date": _parse_due_date(
                    recommendation.due_date
                ),
                "confidence_score": round(
                    confidence * 100
                ),
                "evidence": evidence,
                "reason": metadata.get(
                    "reason",
                    "",
                ),
                "source_type": "email",
                "extraction_method": "ai",
                "prompt_version":
                    APPROVAL_AI_PROMPT_VERSION,
                "provider": result.provider,
                "model": result.model,
            }
        )

    return AIApprovalExtractionResult(
        success=True,
        candidates=candidates,
        error=None,
        provider=(
            result.provider
            or provider
        ),
        model=(
            result.model
            or model
        ),
    )


def extract_approvals_with_ai(
    *,
    subject: str,
    body: str,
    sender: str = "",
    recipient: str = "",
    provider: str = "mock",
    model: Optional[str] = None,
    message_id: Optional[int] = None,
    reference_time=None,
):
    """
    Backwards-compatible convenience wrapper.

    Returns only validated Approval candidate dictionaries.

    Use extract_approvals_with_ai_result() when the caller
    must distinguish a successful no-approval result from
    provider/parser failure.
    """

    result = (
        extract_approvals_with_ai_result(
            subject=subject,
            body=body,
            sender=sender,
            recipient=recipient,
            provider=provider,
            model=model,
            message_id=message_id,
            reference_time=reference_time,
        )
    )

    return result.candidates
