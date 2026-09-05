from urllib.parse import (
    quote,
)

import requests

from googleapiclient.discovery import (
    build,
)

from googleapis.utils import (
    get_gmail_credentials,
)

from microsoftapis.utils import (
    get_microsoft_access_token,
)


SUPPORTED_MUTATION_PROVIDERS = {
    "gmail",
    "outlook",
}

LOCAL_ONLY_PROVIDER_IDS = {
    "",
    "sent",
    "pending",
}


class MailMutationError(
    RuntimeError
):
    pass


def refresh_conversation_local_state(
    conversation,
):
    """
    Recompute conversation mutable truth from materialized
    non-draft, non-trash messages.

    This is deliberately local-only and is used after a provider
    mutation succeeds or an incremental provider sync refreshes
    an existing message.
    """

    if conversation is None:
        return


    active_messages = (
        conversation.messages
        .filter(
            user=conversation.user,
            organization=conversation.organization,
            is_draft=False,
        )
        .exclude(
            folder="trash"
        )
    )


    unread_count = (
        active_messages
        .filter(
            direction="inbound",
            is_read=False,
        )
        .count()
    )


    is_starred = (
        active_messages
        .filter(
            is_starred=True
        )
        .exists()
    )


    changed = []


    if (
        conversation.unread_count
        !=
        unread_count
    ):
        conversation.unread_count = (
            unread_count
        )

        changed.append(
            "unread_count"
        )


    if (
        conversation.is_starred
        !=
        is_starred
    ):
        conversation.is_starred = (
            is_starred
        )

        changed.append(
            "is_starred"
        )


    if changed:

        conversation.save(
            update_fields=changed
        )


def _message_account(
    *,
    message,
    user,
):
    account = (
        message.email_account
    )


    if account is None:

        raise MailMutationError(
            "Message has no connected mailbox."
        )


    if account.user_id != user.id:

        raise MailMutationError(
            "Message mailbox ownership mismatch."
        )


    if not account.is_active:

        raise MailMutationError(
            "Message mailbox is inactive."
        )


    if (
        account.account_type
        not in
        SUPPORTED_MUTATION_PROVIDERS
    ):

        raise MailMutationError(
            "Provider mutation is not supported "
            "for this mailbox type."
        )


    return account


def _provider_message_id(
    message,
):
    provider_id = (
        str(
            message.external_message_id
            or ""
        )
        .strip()
    )


    if (
        not provider_id
        or
        provider_id in LOCAL_ONLY_PROVIDER_IDS
        or
        provider_id.startswith(
            "draft-"
        )
    ):

        raise MailMutationError(
            "Provider message identity is not available yet."
        )


    return provider_id


def _gmail_service(
    user,
):
    credentials = (
        get_gmail_credentials(
            user
        )
    )


    return build(
        "gmail",
        "v1",
        credentials=credentials,
    )


def _graph_headers(
    user,
):
    token = (
        get_microsoft_access_token(
            user
        )
    )


    return {
        "Authorization":
            f"Bearer {token}",

        "Content-Type":
            "application/json",
    }


def _graph_message_url(
    provider_id,
):
    return (
        "https://graph.microsoft.com/"
        "v1.0/me/messages/"
        +
        quote(
            provider_id,
            safe="",
        )
    )


def _require_graph_success(
    response,
    *,
    operation,
):
    status_code = int(
        response.status_code
    )


    if (
        status_code < 200
        or
        status_code >= 300
    ):

        raise MailMutationError(
            "Microsoft Graph "
            + operation
            + " failed with status "
            + str(
                status_code
            )
            + "."
        )


def _gmail_modify_message(
    *,
    user,
    provider_id,
    add_labels=None,
    remove_labels=None,
):
    body = {}


    if add_labels:
        body[
            "addLabelIds"
        ] = list(
            add_labels
        )


    if remove_labels:
        body[
            "removeLabelIds"
        ] = list(
            remove_labels
        )


    try:

        (
            _gmail_service(
                user
            )
            .users()
            .messages()
            .modify(
                userId="me",
                id=provider_id,
                body=body,
            )
            .execute()
        )

    except Exception as exc:

        raise MailMutationError(
            "Gmail message mutation failed."
        ) from exc


def _gmail_modify_thread(
    *,
    user,
    thread_id,
    add_labels=None,
    remove_labels=None,
):
    body = {}


    if add_labels:
        body[
            "addLabelIds"
        ] = list(
            add_labels
        )


    if remove_labels:
        body[
            "removeLabelIds"
        ] = list(
            remove_labels
        )


    try:

        (
            _gmail_service(
                user
            )
            .users()
            .threads()
            .modify(
                userId="me",
                id=thread_id,
                body=body,
            )
            .execute()
        )

    except Exception as exc:

        raise MailMutationError(
            "Gmail conversation mutation failed."
        ) from exc


def _gmail_trash_message(
    *,
    user,
    provider_id,
):
    try:

        (
            _gmail_service(
                user
            )
            .users()
            .messages()
            .trash(
                userId="me",
                id=provider_id,
            )
            .execute()
        )

    except Exception as exc:

        raise MailMutationError(
            "Gmail trash mutation failed."
        ) from exc


def _gmail_trash_thread(
    *,
    user,
    thread_id,
):
    try:

        (
            _gmail_service(
                user
            )
            .users()
            .threads()
            .trash(
                userId="me",
                id=thread_id,
            )
            .execute()
        )

    except Exception as exc:

        raise MailMutationError(
            "Gmail conversation trash mutation failed."
        ) from exc


def _outlook_patch_message(
    *,
    user,
    provider_id,
    payload,
):
    response = (
        requests.patch(
            _graph_message_url(
                provider_id
            ),
            headers=(
                _graph_headers(
                    user
                )
            ),
            json=payload,
            timeout=30,
        )
    )


    _require_graph_success(
        response,
        operation="message update",
    )


def _outlook_trash_message(
    *,
    user,
    provider_id,
):
    response = (
        requests.post(
            (
                _graph_message_url(
                    provider_id
                )
                + "/move"
            ),
            headers=(
                _graph_headers(
                    user
                )
            ),
            json={
                "destinationId":
                    "deleteditems"
            },
            timeout=30,
        )
    )


    _require_graph_success(
        response,
        operation="message move",
    )


    try:
        data = (
            response.json()
        )
    except Exception:
        data = {}


    if not isinstance(
        data,
        dict,
    ):
        return None


    return (
        data.get(
            "id"
        )
    )


def set_message_read(
    *,
    message,
    user,
    is_read,
):
    if not isinstance(
        is_read,
        bool,
    ):

        raise MailMutationError(
            "is_read must be boolean."
        )


    account = (
        _message_account(
            message=message,
            user=user,
        )
    )


    provider_id = (
        _provider_message_id(
            message
        )
    )


    if account.account_type == "gmail":

        if is_read:

            _gmail_modify_message(
                user=user,
                provider_id=provider_id,
                remove_labels=[
                    "UNREAD"
                ],
            )

        else:

            _gmail_modify_message(
                user=user,
                provider_id=provider_id,
                add_labels=[
                    "UNREAD"
                ],
            )


    elif account.account_type == "outlook":

        _outlook_patch_message(
            user=user,
            provider_id=provider_id,
            payload={
                "isRead":
                    is_read
            },
        )


    message.is_read = (
        is_read
    )

    message.save(
        update_fields=[
            "is_read"
        ]
    )


    refresh_conversation_local_state(
        message.conversation
    )


    return message


def set_message_star(
    *,
    message,
    user,
    is_starred,
):
    if not isinstance(
        is_starred,
        bool,
    ):

        raise MailMutationError(
            "is_starred must be boolean."
        )


    account = (
        _message_account(
            message=message,
            user=user,
        )
    )


    provider_id = (
        _provider_message_id(
            message
        )
    )


    if account.account_type == "gmail":

        if is_starred:

            _gmail_modify_message(
                user=user,
                provider_id=provider_id,
                add_labels=[
                    "STARRED"
                ],
            )

        else:

            _gmail_modify_message(
                user=user,
                provider_id=provider_id,
                remove_labels=[
                    "STARRED"
                ],
            )


    elif account.account_type == "outlook":

        _outlook_patch_message(
            user=user,
            provider_id=provider_id,
            payload={
                "flag": {
                    "flagStatus":
                        (
                            "flagged"
                            if is_starred
                            else "notFlagged"
                        )
                }
            },
        )


    message.is_starred = (
        is_starred
    )

    message.save(
        update_fields=[
            "is_starred"
        ]
    )


    refresh_conversation_local_state(
        message.conversation
    )


    return message


def trash_message(
    *,
    message,
    user,
):
    account = (
        _message_account(
            message=message,
            user=user,
        )
    )


    provider_id = (
        _provider_message_id(
            message
        )
    )


    replacement_provider_id = (
        None
    )


    if account.account_type == "gmail":

        _gmail_trash_message(
            user=user,
            provider_id=provider_id,
        )


    elif account.account_type == "outlook":

        replacement_provider_id = (
            _outlook_trash_message(
                user=user,
                provider_id=provider_id,
            )
        )


    update_fields = [
        "folder"
    ]


    message.folder = (
        "trash"
    )


    if replacement_provider_id:

        message.external_message_id = (
            replacement_provider_id
        )

        update_fields.append(
            "external_message_id"
        )


    message.save(
        update_fields=update_fields
    )


    refresh_conversation_local_state(
        message.conversation
    )


    return message


def _conversation_messages(
    *,
    conversation,
):
    return list(
        conversation.messages
        .select_related(
            "email_account"
        )
        .filter(
            user=conversation.user,
            organization=conversation.organization,
            is_draft=False,
        )
        .exclude(
            folder="trash"
        )
        .order_by(
            "id"
        )
    )


def _conversation_account(
    *,
    conversation,
    messages,
    user,
):
    if not messages:

        raise MailMutationError(
            "Conversation has no provider messages."
        )


    account_ids = {
        message.email_account_id
        for message
        in messages
    }


    if (
        None in account_ids
        or
        len(
            account_ids
        ) != 1
    ):

        raise MailMutationError(
            "Conversation mailbox identity is ambiguous."
        )


    account = (
        messages[
            0
        ].email_account
    )


    if (
        account is None
        or
        account.user_id != user.id
        or
        not account.is_active
    ):

        raise MailMutationError(
            "Conversation mailbox is invalid."
        )


    if (
        conversation.email_account_id
        and
        conversation.email_account_id
        !=
        account.id
    ):

        raise MailMutationError(
            "Conversation mailbox ownership mismatch."
        )


    if (
        account.account_type
        not in
        SUPPORTED_MUTATION_PROVIDERS
    ):

        raise MailMutationError(
            "Provider mutation is not supported "
            "for this conversation."
        )


    return account


def set_conversation_read(
    *,
    conversation,
    user,
    is_read,
):
    if not isinstance(
        is_read,
        bool,
    ):

        raise MailMutationError(
            "is_read must be boolean."
        )


    messages = (
        _conversation_messages(
            conversation=conversation
        )
    )


    account = (
        _conversation_account(
            conversation=conversation,
            messages=messages,
            user=user,
        )
    )


    if (
        account.account_type
        ==
        "gmail"
        and
        conversation.external_conversation_id
    ):

        if is_read:

            _gmail_modify_thread(
                user=user,
                thread_id=(
                    conversation
                    .external_conversation_id
                ),
                remove_labels=[
                    "UNREAD"
                ],
            )

        else:

            _gmail_modify_thread(
                user=user,
                thread_id=(
                    conversation
                    .external_conversation_id
                ),
                add_labels=[
                    "UNREAD"
                ],
            )


        for message in messages:
            message.is_read = (
                is_read
            )


        type(
            messages[0]
        ).objects.filter(
            id__in=[
                message.id
                for message
                in messages
            ]
        ).update(
            is_read=is_read
        )


        refresh_conversation_local_state(
            conversation
        )


        return {
            "updated":
                len(
                    messages
                ),

            "errors":
                [],
        }


    updated = 0

    errors = []


    for message in messages:

        try:

            set_message_read(
                message=message,
                user=user,
                is_read=is_read,
            )

            updated += 1

        except MailMutationError as exc:

            errors.append(
                {
                    "message_id":
                        message.id,

                    "error":
                        str(exc),
                }
            )


    refresh_conversation_local_state(
        conversation
    )


    return {
        "updated":
            updated,

        "errors":
            errors,
    }


def set_conversation_star(
    *,
    conversation,
    user,
    is_starred,
):
    if not isinstance(
        is_starred,
        bool,
    ):

        raise MailMutationError(
            "is_starred must be boolean."
        )


    messages = (
        _conversation_messages(
            conversation=conversation
        )
    )


    account = (
        _conversation_account(
            conversation=conversation,
            messages=messages,
            user=user,
        )
    )


    if (
        account.account_type
        ==
        "gmail"
        and
        conversation.external_conversation_id
    ):

        if is_starred:

            _gmail_modify_thread(
                user=user,
                thread_id=(
                    conversation
                    .external_conversation_id
                ),
                add_labels=[
                    "STARRED"
                ],
            )

        else:

            _gmail_modify_thread(
                user=user,
                thread_id=(
                    conversation
                    .external_conversation_id
                ),
                remove_labels=[
                    "STARRED"
                ],
            )


        type(
            messages[0]
        ).objects.filter(
            id__in=[
                message.id
                for message
                in messages
            ]
        ).update(
            is_starred=is_starred
        )


        refresh_conversation_local_state(
            conversation
        )


        return {
            "updated":
                len(
                    messages
                ),

            "errors":
                [],
        }


    updated = 0

    errors = []


    for message in messages:

        try:

            set_message_star(
                message=message,
                user=user,
                is_starred=is_starred,
            )

            updated += 1

        except MailMutationError as exc:

            errors.append(
                {
                    "message_id":
                        message.id,

                    "error":
                        str(exc),
                }
            )


    refresh_conversation_local_state(
        conversation
    )


    return {
        "updated":
            updated,

        "errors":
            errors,
    }


def trash_conversation(
    *,
    conversation,
    user,
):
    messages = (
        _conversation_messages(
            conversation=conversation
        )
    )


    account = (
        _conversation_account(
            conversation=conversation,
            messages=messages,
            user=user,
        )
    )


    if (
        account.account_type
        ==
        "gmail"
        and
        conversation.external_conversation_id
    ):

        _gmail_trash_thread(
            user=user,
            thread_id=(
                conversation
                .external_conversation_id
            ),
        )


        type(
            messages[0]
        ).objects.filter(
            id__in=[
                message.id
                for message
                in messages
            ]
        ).update(
            folder="trash"
        )


        refresh_conversation_local_state(
            conversation
        )


        return {
            "updated":
                len(
                    messages
                ),

            "errors":
                [],
        }


    updated = 0

    errors = []


    for message in messages:

        try:

            trash_message(
                message=message,
                user=user,
            )

            updated += 1

        except MailMutationError as exc:

            errors.append(
                {
                    "message_id":
                        message.id,

                    "error":
                        str(exc),
                }
            )


    refresh_conversation_local_state(
        conversation
    )


    return {
        "updated":
            updated,

        "errors":
            errors,
    }
