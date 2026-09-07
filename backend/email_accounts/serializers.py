from rest_framework import (
    serializers,
)

from email_accounts.services.mailbox_network_policy import (
    MailboxEndpointPolicyError,
    validate_mailbox_endpoint,
)


class SendEmailSerializer(
    serializers.Serializer
):
    to_emails = serializers.ListField(
        child=serializers.EmailField()
    )

    subject = serializers.CharField()

    body = serializers.CharField()

    password = serializers.CharField(
        write_only=True
    )


class OtherWorkEmailSetupSerializer(
    serializers.Serializer
):
    email_address = serializers.EmailField()

    imap_server = serializers.CharField(
        max_length=255,
    )

    imap_port = serializers.IntegerField(
        default=993,
    )

    smtp_server = serializers.CharField(
        max_length=255,
    )

    smtp_port = serializers.IntegerField(
        default=465,
    )

    credential = serializers.CharField(
        write_only=True,
        trim_whitespace=False,
        allow_blank=False,
        max_length=4096,
    )

    def validate(
        self,
        attrs,
    ):
        try:
            imap_endpoint = (
                validate_mailbox_endpoint(
                    host=attrs[
                        "imap_server"
                    ],
                    port=attrs[
                        "imap_port"
                    ],
                    protocol="imap",
                )
            )

            smtp_endpoint = (
                validate_mailbox_endpoint(
                    host=attrs[
                        "smtp_server"
                    ],
                    port=attrs[
                        "smtp_port"
                    ],
                    protocol="smtp",
                )
            )

        except MailboxEndpointPolicyError as exc:
            raise serializers.ValidationError(
                {
                    "endpoint":
                        str(
                            exc
                        )
                }
            ) from exc

        attrs[
            "email_address"
        ] = (
            str(
                attrs[
                    "email_address"
                ]
            )
            .strip()
            .lower()
        )

        attrs[
            "imap_server"
        ] = (
            imap_endpoint.host
        )

        attrs[
            "imap_port"
        ] = (
            imap_endpoint.port
        )

        attrs[
            "smtp_server"
        ] = (
            smtp_endpoint.host
        )

        attrs[
            "smtp_port"
        ] = (
            smtp_endpoint.port
        )

        return attrs
