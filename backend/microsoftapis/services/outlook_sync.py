from datetime import timedelta
from email.utils import getaddresses

import requests

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.utils.dateparse import parse_datetime

from inbox.models import (
    Conversation,
    InboxMessage,
)

from inbox.services.conversation_cache import (
    invalidate_conversation_cache,
)

from inbox.services.sync_status import (
    update_sync_status,
)

from knowledge.services.message_processor import (
    MessageProcessor,
)

from microsoftapis.utils import (
    get_microsoft_access_token,
)

from platform_core.observability.logger import (
    get_logger,
    log_event,
)


logger = get_logger(
    "oneuch.runtime.outlook"
)


OUTLOOK_FOLDER_CONFIG = (
    {
        "graph_folder": "inbox",
        "local_folder": "inbox",
        "direction": "inbound",
        "timestamp_field": "receivedDateTime",
    },
    {
        "graph_folder": "sentitems",
        "local_folder": "sent",
        "direction": "outbound",
        "timestamp_field": "sentDateTime",
    },
)


def _email_address(value):
    return (
        (value or {})
        .get(
            "emailAddress",
            {},
        )
        .get(
            "address",
            "",
        )
        or ""
    )


def _graph_recipients(message):
    addresses = []

    for recipient in (
        message.get(
            "toRecipients",
            [],
        )
        or []
    ):
        address = _email_address(
            recipient
        )

        if address:
            addresses.append(
                address
            )

    return addresses


def _normalized_recipients(value):
    source = str(
        value or ""
    ).replace(
        ";",
        ",",
    )

    return {
        address.strip().lower()
        for _, address in getaddresses(
            [source]
        )
        if address
    }


def _extract_attachments(message):
    attachments = []

    if not message.get(
        "hasAttachments"
    ):
        return attachments

    for attachment in (
        message.get(
            "attachments",
            [],
        )
        or []
    ):
        if (
            attachment.get(
                "@odata.type"
            )
            !=
            "#microsoft.graph.fileAttachment"
        ):
            continue

        attachments.append(
            {
                "filename":
                    attachment.get(
                        "name"
                    ),

                "attachment_id":
                    attachment.get(
                        "id"
                    ),

                "mime_type":
                    attachment.get(
                        "contentType"
                    ),
            }
        )

    return attachments


def _message_timestamp(
    message,
    *,
    direction,
):
    if direction == "outbound":
        raw_value = (
            message.get(
                "sentDateTime"
            )
            or
            message.get(
                "receivedDateTime"
            )
        )
    else:
        raw_value = (
            message.get(
                "receivedDateTime"
            )
            or
            message.get(
                "sentDateTime"
            )
        )

    parsed = (
        parse_datetime(
            raw_value
        )
        if raw_value
        else None
    )

    if parsed is None:
        raise RuntimeError(
            "Microsoft Graph message "
            f"{message.get('id')} "
            "does not contain a valid timestamp."
        )

    return parsed


def _fetch_folder(
    *,
    access_token,
    graph_folder,
    limit,
):
    response = requests.get(
        (
            "https://graph.microsoft.com/"
            "v1.0/me/mailFolders/"
            f"{graph_folder}/messages"
        ),
        headers={
            "Authorization":
                f"Bearer {access_token}"
        },
        params={
            "$top":
                limit,

            "$select": (
                "id,"
                "subject,"
                "bodyPreview,"
                "conversationId,"
                "isRead,"
                "from,"
                "toRecipients,"
                "receivedDateTime,"
                "sentDateTime,"
                "hasAttachments"
            ),

            "$expand":
                "attachments",
        },
    )

    log_event(
        logger,
        "info",
        "outlook.graph.response",
        provider="outlook",
        folder=graph_folder,
        status_code=response.status_code,
    )

    if response.status_code != 200:
        raise RuntimeError(
            "Microsoft Graph Outlook sync "
            f"failed for {graph_folder} "
            f"with status "
            f"{response.status_code}: "
            f"{response.text[:500]}"
        )

    return (
        response.json()
        .get(
            "value",
            [],
        )
    )


def _find_local_outbound_candidate(
    *,
    user,
    email_account,
    subject,
    recipients,
    body_preview,
    sent_at,
):
    """
    Reconcile a Graph Sent Item with a message that One UCH
    already persisted at send/reply time.

    Matching is intentionally conservative:
    - same account
    - outbound Outlook message
    - provider id not yet known (sent/pending)
    - sent status
    - exact subject
    - same normalized recipients
    - near the Graph sent timestamp
    - compatible body preview

    If zero or multiple candidates match, no reconciliation
    is attempted. This avoids attaching a provider message to
    the wrong local business record.
    """

    lower_bound = (
        sent_at
        - timedelta(
            minutes=10
        )
    )

    upper_bound = (
        sent_at
        + timedelta(
            minutes=10
        )
    )

    graph_recipient_set = {
        value.lower()
        for value in recipients
        if value
    }

    candidates = (
        InboxMessage.objects
        .filter(
            user=user,
            email_account=email_account,
            platform="outlook",
            direction="outbound",
            external_message_id__in=[
                "sent",
                "pending",
            ],
            status="sent",
            subject=subject,
            received_at__gte=(
                lower_bound
            ),
            received_at__lte=(
                upper_bound
            ),
        )
        .order_by(
            "id"
        )
    )

    matches = []

    normalized_preview = (
        body_preview
        or ""
    ).strip()

    for candidate in candidates:
        if (
            _normalized_recipients(
                candidate.recipients
            )
            != graph_recipient_set
        ):
            continue

        local_body = (
            candidate.body
            or ""
        ).strip()

        if (
            normalized_preview
            and local_body
            and not (
                local_body.startswith(
                    normalized_preview
                )
                or normalized_preview.startswith(
                    local_body
                )
            )
        ):
            continue

        matches.append(
            candidate
        )

    if len(matches) == 1:
        return matches[0]

    return None


def _resolve_conversation(
    *,
    user,
    organization,
    email_account,
    thread_id,
    subject,
    local_message=None,
):
    conversation_key = (
        f"outlook_{thread_id}"
    )

    provider_conversation = (
        Conversation.objects
        .filter(
            user=user,
            conversation_key=(
                conversation_key
            ),
        )
        .first()
    )

    local_conversation = (
        local_message.conversation
        if (
            local_message
            and
            local_message.conversation_id
        )
        else None
    )

    # Existing provider-native conversation wins.
    if provider_conversation:
        return provider_conversation

    # A locally-created compose/reply conversation can become
    # the provider-native conversation once Graph gives us the
    # real conversationId.
    if local_conversation:
        local_conversation.conversation_key = (
            conversation_key
        )

        local_conversation.external_conversation_id = (
            thread_id
        )

        local_conversation.email_account = (
            email_account
        )

        if (
            local_conversation.organization_id
            is None
        ):
            local_conversation.organization = (
                organization
            )

        local_conversation.save(
            update_fields=[
                "conversation_key",
                "external_conversation_id",
                "email_account",
                "organization",
            ]
        )

        return local_conversation

    return (
        Conversation.objects.create(
            user=user,
            organization=organization,
            conversation_key=(
                conversation_key
            ),
            external_conversation_id=(
                thread_id
            ),
            subject=(
                subject
                or "No Subject"
            ),
            email_account=(
                email_account
            ),
        )
    )


def _update_conversation_if_newer(
    *,
    conversation,
    message,
):
    if (
        conversation.last_message_at
        is not None
        and
        message.received_at
        <
        conversation.last_message_at
    ):
        return

    conversation.last_message = (
        message
    )

    conversation.last_message_at = (
        message.received_at
    )

    conversation.last_message_preview = (
        message.body[:120]
        if message.body
        else "No preview"
    )

    conversation.subject = (
        message.subject
        or conversation.subject
    )

    conversation.save(
        update_fields=[
            "last_message",
            "last_message_at",
            "last_message_preview",
            "subject",
        ]
    )


def fetch_outlook_emails(
    *,
    user,
    email_account,
    limit=20,
):
    update_sync_status(
        user=user,
        platform="outlook",
        status="syncing",
        progress=0,
        error_message="",
    )

    try:
        access_token = (
            get_microsoft_access_token(
                user
            )
        )

        # Fetch both provider folders before persisting either.
        # If provider completeness cannot be established, the
        # sync is reported as failed rather than silently
        # claiming a complete Outlook view.
        folder_batches = []

        for config in (
            OUTLOOK_FOLDER_CONFIG
        ):
            messages = _fetch_folder(
                access_token=(
                    access_token
                ),
                graph_folder=(
                    config[
                        "graph_folder"
                    ]
                ),
                limit=limit,
            )

            folder_batches.append(
                (
                    config,
                    messages,
                )
            )

    except Exception as exc:
        update_sync_status(
            user=user,
            platform="outlook",
            status="failed",
            progress=0,
            error_message=str(exc),
        )

        raise

    organization = (
        user
        .organization_membership
        .organization
    )

    latest_message = None

    for (
        config,
        messages,
    ) in folder_batches:

        log_event(
            logger,
            "info",
            "outlook.folder.batch",
            provider="outlook",
            folder=config['graph_folder'],
            message_count=len(messages),
        )

        for graph_message in messages:

            external_id = (
                graph_message.get(
                    "id"
                )
            )

            thread_id = (
                graph_message.get(
                    "conversationId"
                )
            )

            if (
                not external_id
                or not thread_id
            ):
                raise RuntimeError(
                    "Microsoft Graph message "
                    "is missing id or "
                    "conversationId."
                )

            # Provider-id idempotency.
            existing = (
                InboxMessage.objects
                .filter(
                    external_message_id=(
                        external_id
                    ),
                    email_account=(
                        email_account
                    ),
                )
                .first()
            )

            if existing:
                continue

            direction = (
                config[
                    "direction"
                ]
            )

            subject = (
                graph_message.get(
                    "subject"
                )
                or "No Subject"
            )

            body_preview = (
                graph_message.get(
                    "bodyPreview",
                    "",
                )
                or ""
            )

            received_at = (
                _message_timestamp(
                    graph_message,
                    direction=direction,
                )
            )

            recipient_addresses = (
                _graph_recipients(
                    graph_message
                )
            )

            recipients = ", ".join(
                recipient_addresses
            )

            sender = _email_address(
                graph_message.get(
                    "from"
                )
            )

            if direction == "outbound":
                sender = (
                    sender
                    or
                    email_account.email_address
                )

            elif not recipients:
                recipients = (
                    email_account.email_address
                )

            local_candidate = None

            if direction == "outbound":
                local_candidate = (
                    _find_local_outbound_candidate(
                        user=user,
                        email_account=(
                            email_account
                        ),
                        subject=subject,
                        recipients=(
                            recipient_addresses
                        ),
                        body_preview=(
                            body_preview
                        ),
                        sent_at=(
                            received_at
                        ),
                    )
                )

            conversation = (
                _resolve_conversation(
                    user=user,
                    organization=(
                        organization
                    ),
                    email_account=(
                        email_account
                    ),
                    thread_id=(
                        thread_id
                    ),
                    subject=subject,
                    local_message=(
                        local_candidate
                    ),
                )
            )

            # Repair legacy/provider conversation account link.
            if (
                conversation.email_account_id
                is None
            ):
                conversation.email_account = (
                    email_account
                )

                conversation.save(
                    update_fields=[
                        "email_account",
                    ]
                )

            attachments = (
                _extract_attachments(
                    graph_message
                )
            )

            if local_candidate:
                message_obj = (
                    local_candidate
                )

                message_obj.conversation = (
                    conversation
                )

                message_obj.external_message_id = (
                    external_id
                )

                message_obj.external_conversation_id = (
                    thread_id
                )

                message_obj.folder = (
                    config[
                        "local_folder"
                    ]
                )

                message_obj.sender = (
                    sender
                )

                message_obj.recipients = (
                    recipients
                )

                message_obj.subject = (
                    subject
                )

                # Preserve the full body that One UCH already
                # stored. Graph bodyPreview is only a preview.
                if not message_obj.body:
                    message_obj.body = (
                        body_preview
                    )

                message_obj.received_at = (
                    received_at
                )

                message_obj.is_read = True

                message_obj.direction = (
                    "outbound"
                )

                message_obj.is_draft = (
                    False
                )

                message_obj.status = (
                    "sent"
                )

                if attachments:
                    message_obj.attachment_meta = (
                        attachments
                    )

                message_obj.save(
                    update_fields=[
                        "conversation",
                        "external_message_id",
                        "external_conversation_id",
                        "folder",
                        "sender",
                        "recipients",
                        "subject",
                        "body",
                        "received_at",
                        "is_read",
                        "direction",
                        "is_draft",
                        "status",
                        "attachment_meta",
                    ]
                )

            else:
                message_obj = (
                    InboxMessage.objects.create(
                        user=user,
                        organization=(
                            organization
                        ),
                        conversation=(
                            conversation
                        ),
                        platform="outlook",
                        folder=(
                            config[
                                "local_folder"
                            ]
                        ),
                        external_message_id=(
                            external_id
                        ),
                        external_conversation_id=(
                            thread_id
                        ),
                        sender=(
                            sender
                        ),
                        recipients=(
                            recipients
                        ),
                        subject=(
                            subject
                        ),
                        attachment_meta=(
                            attachments
                        ),
                        body=(
                            body_preview
                        ),
                        received_at=(
                            received_at
                        ),
                        is_read=(
                            graph_message.get(
                                "isRead",
                                direction
                                ==
                                "outbound",
                            )
                        ),
                        is_starred=False,
                        direction=(
                            direction
                        ),
                        is_draft=False,
                        email_account=(
                            email_account
                        ),
                    )
                )

            try:
                processor = (
                    MessageProcessor()
                )

                processor.process_message(
                    organization=(
                        organization
                    ),
                    message=(
                        message_obj
                    ),
                    sender=(
                        message_obj.sender
                    ),
                    subject=(
                        message_obj.subject
                    ),
                    body=(
                        message_obj.body
                    ),
                    source_channel=(
                        "outlook"
                    ),
                )

            except Exception as exc:
                log_event(
                    logger,
                    "warning",
                    "outlook.knowledge.failed",
                    provider="outlook",
                    message_id=message_obj.id,
                    error_type=type(exc).__name__,
                )

            _update_conversation_if_newer(
                conversation=(
                    conversation
                ),
                message=(
                    message_obj
                ),
            )

            invalidate_conversation_cache(
                user.id
            )

            if (
                latest_message is None
                or
                message_obj.received_at
                >
                latest_message.received_at
            ):
                latest_message = (
                    message_obj
                )

    update_sync_status(
        user=user,
        platform="outlook",
        status="success",
        progress=100,
        error_message="",
    )

    if latest_message:
        channel_layer = (
            get_channel_layer()
        )

        async_to_sync(
            channel_layer.group_send
        )(
            f"inbox_{user.id}",
            {
                "type":
                    "inbox_update",

                "data": {
                    "event":
                        "new_email",

                    "conversation_id":
                        (
                            latest_message
                            .conversation_id
                        ),

                    "subject":
                        latest_message.subject,

                    "sender":
                        latest_message.sender,

                    "preview":
                        (
                            latest_message
                            .body[:120]
                        ),

                    "received_at":
                        (
                            latest_message
                            .received_at
                            .isoformat()
                        ),

                    "platform":
                        "outlook",
                },
            },
        )

    log_event(
        logger,
        "info",
        "outlook.sync.completed",
        provider="outlook",
        folder_count=len(folder_batches),
    )
