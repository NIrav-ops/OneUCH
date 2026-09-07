import socket
import ssl

from unittest.mock import (
    patch,
)

from uuid import (
    uuid4,
)

from django.test import (
    TestCase,
)

from rest_framework.test import (
    APIClient,
)

from accounts.models import (
    User,
)

from email_accounts.models import (
    EmailAccount,
)

from email_accounts.services.imap_smtp import (
    fetch_imap_emails,
    send_via_smtp,
)

from email_accounts.services.mailbox_network_policy import (
    MailboxEndpointPolicyError,
    connect_validated_mailbox_endpoint,
    create_verified_tls_context,
    validate_mailbox_endpoint,
)

from inbox.models import (
    Organization,
    OrganizationUser,
)


class MailRC1C5AHostSecurityTests(
    TestCase
):
    PASSWORD = (
        "C5A-Login-Password-93471"
    )

    MAIL_CREDENTIAL = (
        "C5A-Synthetic-Mail-Credential-38721"
    )

    PUBLIC_IPV4 = (
        "8.8.8.8"
    )

    PRIVATE_IPV4 = (
        "10.20.30.40"
    )

    def setUp(
        self,
    ):
        self.user = (
            User.objects.create_user(
                email=(
                    "mail-c5a@oneuch.test"
                ),
                password=(
                    self.PASSWORD
                ),
            )
        )

        self.org = (
            Organization.objects.create(
                name="C5A Workspace",
                slug=(
                    "mail-c5a-"
                    + uuid4().hex
                ),
            )
        )

        OrganizationUser.objects.create(
            user=self.user,
            organization=self.org,
            role="owner",
        )

        self.client = (
            APIClient()
        )

        self.client.force_authenticate(
            user=self.user
        )

        self.url = (
            "/api/email/"
            "other-work-email/"
        )

    def public_dns(
        self,
        host,
        port,
        family=0,
        socktype=0,
        *args,
        **kwargs,
    ):
        return [
            (
                socket.AF_INET,
                socket.SOCK_STREAM,
                6,
                "",
                (
                    self.PUBLIC_IPV4,
                    int(port),
                ),
            )
        ]

    def private_dns(
        self,
        host,
        port,
        family=0,
        socktype=0,
        *args,
        **kwargs,
    ):
        return [
            (
                socket.AF_INET,
                socket.SOCK_STREAM,
                6,
                "",
                (
                    self.PRIVATE_IPV4,
                    int(port),
                ),
            )
        ]

    def payload(
        self,
        **overrides,
    ):
        value = {
            "email_address":
                "person@example.com",

            "imap_server":
                "imap.example.com",

            "imap_port":
                993,

            "smtp_server":
                "smtp.example.com",

            "smtp_port":
                465,

            "credential":
                self.MAIL_CREDENTIAL,
        }

        value.update(
            overrides
        )

        return value

    def create_imap_account(
        self,
        **overrides,
    ):
        values = {
            "user":
                self.user,

            "organization":
                self.org,

            "account_type":
                "imap",

            "email_address":
                "person@example.com",

            "imap_server":
                "imap.example.com",

            "imap_port":
                993,

            "smtp_server":
                "smtp.example.com",

            "smtp_port":
                465,

            "smtp_password":
                self.MAIL_CREDENTIAL,

            "credential_status":
                "active",

            "is_active":
                True,
        }

        values.update(
            overrides
        )

        return (
            EmailAccount.objects.create(
                **values
            )
        )

    # ========================================================
    # 1. Authentication boundary.
    # ========================================================

    def test_setup_requires_authentication(
        self,
    ):
        anonymous = (
            APIClient()
        )

        response = anonymous.post(
            self.url,
            self.payload(),
            format="json",
        )

        self.assertIn(
            response.status_code,
            {
                401,
                403,
            },
        )

    # ========================================================
    # 2. Active workspace boundary.
    # ========================================================

    def test_setup_requires_active_workspace(
        self,
    ):
        user = (
            User.objects.create_user(
                email=(
                    "no-workspace-c5a@oneuch.test"
                ),
                password=(
                    self.PASSWORD
                ),
            )
        )

        client = (
            APIClient()
        )

        client.force_authenticate(
            user=user
        )

        response = client.post(
            self.url,
            self.payload(),
            format="json",
        )

        self.assertEqual(
            response.status_code,
            403,
        )

        self.assertFalse(
            EmailAccount.objects.filter(
                user=user
            ).exists()
        )

    # ========================================================
    # 3. Secure storage + response redaction.
    # ========================================================

    @patch(
        "email_accounts.services."
        "mailbox_network_policy."
        "socket.getaddrinfo"
    )
    def test_setup_encrypts_credential_and_redacts_network_configuration(
        self,
        resolver,
    ):
        resolver.side_effect = (
            self.public_dns
        )

        response = self.client.post(
            self.url,
            self.payload(),
            format="json",
        )

        self.assertEqual(
            response.status_code,
            201,
        )

        account = (
            EmailAccount.objects.get(
                id=response.data[
                    "id"
                ]
            )
        )

        self.assertEqual(
            account.organization_id,
            self.org.id,
        )

        self.assertEqual(
            account.user_id,
            self.user.id,
        )

        self.assertEqual(
            account.account_type,
            "imap",
        )

        self.assertNotEqual(
            account.credential_ciphertext,
            self.MAIL_CREDENTIAL,
        )

        self.assertEqual(
            account.get_credential(),
            self.MAIL_CREDENTIAL,
        )

        self.assertEqual(
            account.credential_status,
            "active",
        )

        for forbidden in (
            "credential",
            "credential_ciphertext",
            "smtp_password",
            "imap_server",
            "imap_port",
            "smtp_server",
            "smtp_port",
        ):
            self.assertNotIn(
                forbidden,
                response.data,
            )

    # ========================================================
    # 4. Reconfiguration rotates secret without duplicates.
    # ========================================================

    @patch(
        "email_accounts.services."
        "mailbox_network_policy."
        "socket.getaddrinfo"
    )
    def test_setup_rotates_existing_mailbox_without_duplicate(
        self,
        resolver,
    ):
        resolver.side_effect = (
            self.public_dns
        )

        first = self.client.post(
            self.url,
            self.payload(),
            format="json",
        )

        second_credential = (
            "C5A-Rotated-Credential-44918"
        )

        second = self.client.post(
            self.url,
            self.payload(
                credential=(
                    second_credential
                )
            ),
            format="json",
        )

        self.assertEqual(
            first.status_code,
            201,
        )

        self.assertEqual(
            second.status_code,
            200,
        )

        self.assertEqual(
            first.data[
                "id"
            ],
            second.data[
                "id"
            ],
        )

        self.assertEqual(
            EmailAccount.objects.filter(
                user=self.user,
                organization=self.org,
                account_type="imap",
                email_address=(
                    "person@example.com"
                ),
            ).count(),
            1,
        )

        account = (
            EmailAccount.objects.get(
                id=second.data[
                    "id"
                ]
            )
        )

        self.assertEqual(
            account.get_credential(),
            second_credential,
        )

    # ========================================================
    # 5. Literal private-IP SSRF block.
    # ========================================================

    def test_setup_rejects_private_literal_imap_host(
        self,
    ):
        response = self.client.post(
            self.url,
            self.payload(
                imap_server=(
                    "127.0.0.1"
                )
            ),
            format="json",
        )

        self.assertEqual(
            response.status_code,
            400,
        )

        self.assertFalse(
            EmailAccount.objects.filter(
                user=self.user
            ).exists()
        )

    # ========================================================
    # 6. DNS-to-private SSRF block.
    # ========================================================

    @patch(
        "email_accounts.services."
        "mailbox_network_policy."
        "socket.getaddrinfo"
    )
    def test_setup_rejects_hostname_resolving_to_private_address(
        self,
        resolver,
    ):
        resolver.side_effect = (
            self.private_dns
        )

        response = self.client.post(
            self.url,
            self.payload(),
            format="json",
        )

        self.assertEqual(
            response.status_code,
            400,
        )

        self.assertIn(
            "non-public",
            str(
                response.data
            ),
        )

        self.assertFalse(
            EmailAccount.objects.filter(
                user=self.user
            ).exists()
        )

    # ========================================================
    # 7. URL/user-info injection must never become a hostname.
    # ========================================================

    def test_setup_rejects_url_and_userinfo_hosts(
        self,
    ):
        bad_hosts = [
            "https://imap.example.com",
            "user@imap.example.com",
            "imap.example.com/path",
        ]

        for host in bad_hosts:

            with self.subTest(
                host=host
            ):
                response = (
                    self.client.post(
                        self.url,
                        self.payload(
                            imap_server=host
                        ),
                        format="json",
                    )
                )

                self.assertEqual(
                    response.status_code,
                    400,
                )

    # ========================================================
    # 8. Current transport supports implicit TLS only.
    # ========================================================

    def test_setup_rejects_unsupported_transport_ports(
        self,
    ):
        response = self.client.post(
            self.url,
            self.payload(
                imap_port=143,
                smtp_port=587,
            ),
            format="json",
        )

        self.assertEqual(
            response.status_code,
            400,
        )

        self.assertFalse(
            EmailAccount.objects.filter(
                user=self.user
            ).exists()
        )

    # ========================================================
    # 9. Runtime IMAP revalidates before IMAP4_SSL.
    # ========================================================

    @patch(
        "email_accounts.services."
        "imap_smtp.async_to_sync"
    )
    @patch(
        "email_accounts.services."
        "imap_smtp.get_channel_layer"
    )
    @patch(
        "email_accounts.services."
        "imap_smtp.update_sync_status"
    )
    @patch(
        "email_accounts.services."
        "imap_smtp.imaplib.IMAP4_SSL"
    )
    @patch(
        "email_accounts.services."
        "mailbox_network_policy."
        "socket.getaddrinfo"
    )
    def test_imap_runtime_blocks_private_dns_before_socket(
        self,
        resolver,
        imap_socket,
        update_status,
        channel_layer,
        async_bridge,
    ):
        resolver.side_effect = (
            self.private_dns
        )

        async_bridge.return_value = (
            lambda *args, **kwargs:
                None
        )

        account = (
            self.create_imap_account()
        )

        with self.assertRaises(
            MailboxEndpointPolicyError
        ):
            fetch_imap_emails(
                user=self.user,
                email_account=account,
                password=(
                    self.MAIL_CREDENTIAL
                ),
            )

        imap_socket.assert_not_called()

    # ========================================================
    # 10. Runtime SMTP revalidates before SMTP_SSL.
    # ========================================================

    @patch(
        "email_accounts.services."
        "imap_smtp.smtplib.SMTP_SSL"
    )
    @patch(
        "email_accounts.services."
        "mailbox_network_policy."
        "socket.getaddrinfo"
    )
    def test_smtp_runtime_blocks_private_dns_before_socket(
        self,
        resolver,
        smtp_socket,
    ):
        resolver.side_effect = (
            self.private_dns
        )

        account = (
            self.create_imap_account()
        )

        with self.assertRaises(
            MailboxEndpointPolicyError
        ):
            send_via_smtp(
                email_account=account,
                to_email=(
                    "customer@example.com"
                ),
                subject="C5A",
                body="Do not send",
                password=(
                    self.MAIL_CREDENTIAL
                ),
            )

        smtp_socket.assert_not_called()

    # ========================================================
    # 11. A same-workspace row owned by another user cannot be
    # taken over by posting the same mailbox identity.
    # ========================================================

    @patch(
        "email_accounts.services."
        "mailbox_network_policy."
        "socket.getaddrinfo"
    )
    def test_setup_cannot_take_over_other_users_workspace_mailbox(
        self,
        resolver,
    ):
        resolver.side_effect = (
            self.public_dns
        )

        other = (
            User.objects.create_user(
                email=(
                    "other-c5a@oneuch.test"
                ),
                password=(
                    self.PASSWORD
                ),
            )
        )

        OrganizationUser.objects.create(
            user=other,
            organization=self.org,
            role="member",
        )

        existing = (
            EmailAccount.objects.create(
                user=other,
                organization=self.org,
                account_type="imap",
                email_address=(
                    "person@example.com"
                ),
                imap_server=(
                    "imap.example.com"
                ),
                imap_port=993,
                smtp_server=(
                    "smtp.example.com"
                ),
                smtp_port=465,
                smtp_password=(
                    "Other-User-Secret-93471"
                ),
                credential_status="active",
                is_active=True,
            )
        )

        response = self.client.post(
            self.url,
            self.payload(),
            format="json",
        )

        self.assertEqual(
            response.status_code,
            409,
        )

        existing.refresh_from_db()

        self.assertEqual(
            existing.user_id,
            other.id,
        )

        self.assertEqual(
            existing.get_credential(),
            "Other-User-Secret-93471",
        )


    # ========================================================
    # 12. Validated DNS answer is pinned into TCP connection.
    # There must be no second hostname lookup at connect time.
    # ========================================================

    @patch(
        "email_accounts.services."
        "mailbox_network_policy."
        "socket.create_connection"
    )
    def test_validated_connection_uses_pinned_public_ip(
        self,
        tcp_connect,
    ):
        sentinel = object()

        tcp_connect.return_value = (
            sentinel
        )

        endpoint = (
            validate_mailbox_endpoint(
                host=(
                    "imap.example.com"
                ),
                port=993,
                protocol="imap",
                resolver=(
                    self.public_dns
                ),
            )
        )

        result = (
            connect_validated_mailbox_endpoint(
                endpoint=endpoint
            )
        )

        self.assertIs(
            result,
            sentinel,
        )

        tcp_connect.assert_called_once_with(
            (
                self.PUBLIC_IPV4,
                993,
            )
        )

    # ========================================================
    # 13. Other Work Email TLS must enforce normal CA and
    # hostname certificate verification.
    # ========================================================

    def test_mailbox_tls_context_requires_certificate_verification(
        self,
    ):
        context = (
            create_verified_tls_context()
        )

        self.assertTrue(
            context.check_hostname
        )

        self.assertEqual(
            context.verify_mode,
            ssl.CERT_REQUIRED,
        )
