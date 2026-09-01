import base64

from urllib.parse import (
    quote,
)

import requests

from django.http import (
    HttpResponse,
)

from googleapiclient.discovery import (
    build,
)

from rest_framework.permissions import (
    IsAuthenticated,
)

from rest_framework.views import (
    APIView,
)

from googleapis.utils import (
    get_gmail_credentials,
)

from inbox.models import (
    InboxMessage,
)

from microsoftapis.utils import (
    get_microsoft_access_token,
)


class DownloadAttachmentAPIView(
    APIView
):
    permission_classes = [
        IsAuthenticated
    ]


    def _safe_filename(
        self,
        value,
    ):
        filename = (
            str(
                value
                or
                "attachment"
            )
            .replace(
                "\\",
                "/",
            )
            .split(
                "/"
            )[
                -1
            ]
            .replace(
                "\r",
                "",
            )
            .replace(
                "\n",
                "",
            )
            .strip()
        )


        return (
            filename
            or
            "attachment"
        )


    def _build_response(
        self,
        file_data,
        filename,
        content_type,
    ):
        safe_filename = (
            self._safe_filename(
                filename
            )
        )


        response = (
            HttpResponse(
                file_data,
                content_type=(
                    content_type
                    or
                    "application/octet-stream"
                ),
            )
        )


        response[
            "Content-Disposition"
        ] = (
            "attachment; filename*=UTF-8''"
            +
            quote(
                safe_filename
            )
        )


        response[
            "Content-Length"
        ] = str(
            len(
                file_data
            )
        )


        return response


    def _find_attachment_meta(
        self,
        message,
        attachment_id,
    ):
        target = (
            str(
                attachment_id
                or ""
            )
        )


        for item in (
            message.attachment_meta
            or []
        ):

            if not isinstance(
                item,
                dict,
            ):
                continue


            if (
                str(
                    item.get(
                        "attachment_id"
                    )
                    or ""
                )
                ==
                target
            ):

                return item


        return None


    def get(
        self,
        request,
        message_id,
        attachment_id,
    ):
        message = (
            InboxMessage.objects
            .select_related(
                "email_account",
                "organization",
            )
            .filter(
                id=message_id,
                user=request.user,
            )
            .first()
        )


        if message is None:

            return HttpResponse(
                "Message not found",
                status=404,
            )


        membership = (
            getattr(
                request.user,
                "organization_membership",
                None,
            )
        )


        if (
            message.organization_id
            and
            (
                membership is None
                or
                membership.organization_id
                !=
                message.organization_id
            )
        ):

            return HttpResponse(
                "Message not found",
                status=404,
            )


        meta = (
            self._find_attachment_meta(
                message,
                attachment_id,
            )
        )


        # Never allow arbitrary provider attachment IDs to be
        # fetched merely because the caller knows a message ID.
        if meta is None:

            return HttpResponse(
                "Attachment not found",
                status=404,
            )


        provider_message_id = (
            str(
                message.external_message_id
                or ""
            )
            .strip()
        )


        if provider_message_id in {
            "",
            "pending",
            "sent",
        }:

            return HttpResponse(
                "Provider message is not synchronized yet",
                status=409,
            )


        filename = (
            meta.get(
                "filename"
            )
            or
            "attachment"
        )


        content_type = (
            meta.get(
                "mime_type"
            )
            or
            "application/octet-stream"
        )


        try:

            # =================================================
            # GMAIL
            # =================================================

            if message.platform == "gmail":

                credentials = (
                    get_gmail_credentials(
                        request.user
                    )
                )


                service = (
                    build(
                        "gmail",
                        "v1",
                        credentials=(
                            credentials
                        ),
                    )
                )


                attachment = (
                    service
                    .users()
                    .messages()
                    .attachments()
                    .get(
                        userId="me",
                        messageId=(
                            provider_message_id
                        ),
                        id=(
                            attachment_id
                        ),
                    )
                    .execute()
                )


                data = (
                    attachment.get(
                        "data"
                    )
                )


                if not data:

                    return HttpResponse(
                        "Attachment content missing",
                        status=502,
                    )


                padding = (
                    "="
                    *
                    (
                        (
                            4
                            -
                            len(
                                data
                            )
                            %
                            4
                        )
                        %
                        4
                    )
                )


                file_data = (
                    base64
                    .urlsafe_b64decode(
                        (
                            data
                            +
                            padding
                        )
                        .encode(
                            "UTF-8"
                        )
                    )
                )


                return (
                    self._build_response(
                        file_data,
                        filename,
                        content_type,
                    )
                )


            # =================================================
            # MICROSOFT
            # =================================================

            if message.platform == "outlook":

                token = (
                    get_microsoft_access_token(
                        request.user
                    )
                )


                response = (
                    requests.get(
                        (
                            "https://graph.microsoft.com/"
                            "v1.0/me/messages/"
                            +
                            quote(
                                provider_message_id,
                                safe="",
                            )
                            +
                            "/attachments/"
                            +
                            quote(
                                str(
                                    attachment_id
                                ),
                                safe="",
                            )
                        ),
                        headers={
                            "Authorization":
                                f"Bearer {token}"
                        },
                        timeout=30,
                    )
                )


                if response.status_code != 200:

                    return HttpResponse(
                        "Attachment download failed",
                        status=(
                            response.status_code
                        ),
                    )


                attachment = (
                    response.json()
                )


                content_b64 = (
                    attachment.get(
                        "contentBytes"
                    )
                )


                if not content_b64:

                    return HttpResponse(
                        "Attachment content missing",
                        status=502,
                    )


                file_data = (
                    base64
                    .b64decode(
                        content_b64
                    )
                )


                return (
                    self._build_response(
                        file_data,
                        (
                            attachment.get(
                                "name"
                            )
                            or
                            filename
                        ),
                        (
                            attachment.get(
                                "contentType"
                            )
                            or
                            content_type
                        ),
                    )
                )


            return HttpResponse(
                "Unsupported platform",
                status=400,
            )


        except Exception:

            # Provider internals and tokens must never be
            # reflected to the browser.
            return HttpResponse(
                "Attachment download failed",
                status=502,
            )
