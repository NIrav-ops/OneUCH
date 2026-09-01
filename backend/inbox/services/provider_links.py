from urllib.parse import (
    quote,
)


class ProviderLinkError(
    ValueError
):
    pass


LOCAL_ONLY_PROVIDER_IDS = {
    "",
    "pending",
    "sent",
}


def provider_open_url(
    message,
):
    account = (
        message.email_account
    )


    if account is None:

        raise ProviderLinkError(
            "Message is not linked to a connected mailbox."
        )


    provider = (
        account.account_type
    )


    if provider == "gmail":

        thread_id = (
            str(
                message.external_conversation_id
                or
                (
                    message.conversation
                    .external_conversation_id
                    if message.conversation_id
                    else ""
                )
                or
                message.external_message_id
                or ""
            )
            .strip()
        )


        if (
            not thread_id
            or
            thread_id
            in
            LOCAL_ONLY_PROVIDER_IDS
        ):

            raise ProviderLinkError(
                "Gmail provider link is not available yet."
            )


        email_address = (
            str(
                account.email_address
                or ""
            )
            .strip()
        )


        return (
            "https://mail.google.com/mail/"
            "?authuser="
            +
            quote(
                email_address,
                safe="",
            )
            +
            "#all/"
            +
            quote(
                thread_id,
                safe="",
            )
        )


    if provider == "outlook":

        message_id = (
            str(
                message.external_message_id
                or ""
            )
            .strip()
        )


        if (
            not message_id
            or
            message_id
            in
            LOCAL_ONLY_PROVIDER_IDS
        ):

            raise ProviderLinkError(
                "Outlook provider link is not available until "
                "the sent message is synchronized."
            )


        return (
            "https://outlook.office.com/"
            "mail/deeplink/read/"
            +
            quote(
                message_id,
                safe="",
            )
        )


    raise ProviderLinkError(
        "Open in Provider is available for Gmail "
        "and Microsoft 365 mailboxes."
    )
