import logging
from datetime import datetime
from typing import Optional, List

from django.utils import timezone

from workflow.services.ai import (
    AIExecutionService,
    AIRequest,
    AIResponseParser,
)

from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


ACTION_AI_PROMPT_VERSION = "action-extraction-v1"

@dataclass(frozen=True)
class AIActionExtractionResult:
    success: bool
    candidates: List[dict] = field(
        default_factory=list
    )
    error: Optional[str] = None
    provider: Optional[str] = None
    model: Optional[str] = None
    processing_mode: Optional[str] = None


SYSTEM_PROMPT = """
You are the Action Intelligence engine for One UCH.

Your job is to identify genuine work that a recipient or their
organization is expected to perform because of a business
communication.

An Action is a concrete piece of work such as:
- sending or preparing something
- reviewing something
- investigating or resolving something
- coordinating with another person or team
- confirming or providing information
- completing a required activity
- fulfilling a commitment or requested deliverable

Do not create Actions for:
- informational statements
- FYI messages
- newsletters or marketing messages
- acknowledgements
- already-completed work
- receipts or confirmations of completed work
- historical references
- quoted previous requests unless they remain clearly active
- email signatures or disclaimers

Precision is more important than recall.

If the message contains no genuine Action, return an empty
actions list.

Every proposed Action must include evidence containing the exact
words from the supplied message that justify the Action.

Do not invent owners, deadlines, facts, or evidence.
""".strip()


ACTION_RESPONSE_SCHEMA = {
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
Analyze this business communication.

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

Return an action_list.

For every action use:
- title: concise actionable title
- description: concrete work to perform
- priority: integer from 0 to 100
- owner_reference: person explicitly responsible, otherwise null
- due_date: ISO-8601 date/datetime only when explicitly stated
- confidence: number between 0 and 1
- metadata.evidence: exact supporting text from the message
- metadata.reason: short explanation

If nothing is actionable, return:
{{"actions": []}}
""".strip()


def _normalize_evidence(
    value,
) -> str:
    if not isinstance(value, str):
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

    return evidence.lower() in source


def _parse_due_date(
    value: Optional[str],
):
    if not value:
        return None

    if not isinstance(value, str):
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

    if timezone.is_naive(parsed):
        parsed = timezone.make_aware(
            parsed,
            timezone.get_current_timezone(),
        )

    return parsed


def extract_actions_with_ai_result(
    *,
    subject: str,
    body: str,
    sender: str = "",
    recipient: str = "",
    provider: str = "mock",
    model: Optional[str] = None,
    message_id: Optional[int] = None,
    reference_time=None,
) -> AIActionExtractionResult:
    
    """
    Return validated AI Action candidates.

    This function never creates ActionItem records.
    AI output remains advisory until the actions domain
    explicitly accepts it.
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
        response_type="action_list",
        response_schema=ACTION_RESPONSE_SCHEMA,
        metadata={
            "domain": "actions",
            "purpose": "semantic_action_extraction",
            "prompt_version":
                ACTION_AI_PROMPT_VERSION,
            "message_id": message_id,
        },
    )

    result = AIExecutionService.execute(
        request,
        provider=provider,
    )

    processing_mode = (
        (getattr(
            result,
            "metadata",
            None,
        ) or {}).get(
            "processing_mode"
        )
    )

    if not result.success:
        logger.warning(
            "AI Action extraction failed | "
            "message_id=%s provider=%s error=%s",
            message_id,
            provider,
            result.error,
        )

        return AIActionExtractionResult(
            success=False,
            candidates=[],
            error=result.error,
            provider=result.provider or provider,
            model=result.model or model,
            processing_mode=processing_mode,
        )

    try:
        parsed = AIResponseParser.parse(
            request,
            result,
        )
    except Exception as exc:
        logger.exception(
            "Unable to parse AI Action output | "
            "message_id=%s provider=%s",
            message_id,
            provider,
        )

        return AIActionExtractionResult(
            success=False,
            candidates=[],
            error=str(exc),
            provider=result.provider or provider,
            model=result.model or model,
            processing_mode=processing_mode,
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
                "Rejected AI Action without valid "
                "source evidence | message_id=%s "
                "title=%s",
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
                    recommendation.description.strip()
                    if isinstance(
                        recommendation.description,
                        str,
                    )
                    else ""
                ),
                "priority": priority,
                "owner_reference":
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
                    ACTION_AI_PROMPT_VERSION,
                "provider": result.provider,
                "model": result.model,
                "processing_mode":
                    processing_mode,
            }
        )

    return AIActionExtractionResult(
        success=True,
        candidates=candidates,
        error=None,
        provider=result.provider or provider,
        model=result.model or model,
        processing_mode=processing_mode,
    )

def extract_actions_with_ai(
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
    Backwards-compatible wrapper.

    Returns only validated Action candidate dictionaries.

    Use extract_actions_with_ai_result() when the caller
    must distinguish successful no-action results from
    provider/parser failures.
    """

    result = extract_actions_with_ai_result(
        subject=subject,
        body=body,
        sender=sender,
        recipient=recipient,
        provider=provider,
        model=model,
        message_id=message_id,
        reference_time=reference_time,
    )

    return result.candidates