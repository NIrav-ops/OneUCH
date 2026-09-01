from unittest.mock import (
    MagicMock,
    patch,
)

from django.contrib.auth import (
    get_user_model,
)

from django.test import (
    TestCase,
)

from django.utils import (
    timezone,
)

from rest_framework.test import (
    APITestCase,
)

from email_accounts.models import (
    EmailAccount,
)

from inbox.models import (
    Conversation,
    InboxMessage,
    Organization,
    OrganizationUser,
)

from inbox.services.mail_mutations import (
    set_conversation_read,
    set_message_read,
    set_message_star,
    trash_message,
)


User = get_user_model()


class MailMutationFixtureMixin:

    def build_fixture(
        self,
        *,
        provider="gmail",
        is_read=False,
        is_starred=False,
        folder="inbox",
        external_message_id="provider-message-1",
        external_conversation_id="provider-thread-1",
    ):
        self.user = (
            User.objects.create_user(
                email=(
                    "p3a-user@oneuch.test"
                ),
                password="pass123",
            )
        )


        self.organization = (
            Organization.objects.create(
                name="P3A Org",
                slug=(
                    "p3a-org-"
                    + provider
                    + "-"
                    + str(
                        Organization.objects.count()
                        + 1
                    )
                ),
            )
        )


        OrganizationUser.objects.create(
            user=self.user,
            organization=(
                self.organization
            ),
            role="member",
        )


        self.account = (
            EmailAccount.objects.create(
                user=self.user,
                account_type=provider,
                email_address=(
                    "p3a-"
                    + provider
                    + "@oneuch.test"
                ),
                credential_status="active",
                is_active=True,
            )
        )


        self.conversation = (
            Conversation.objects.create(
                user=self.user,
                organization=(
                    self.organization
                ),
                email_account=(
                    self.account
                ),
                subject="P3A",
                conversation_key=(
                    "p3a-"
                    + provider
                    + "-"
                    + str(
                        Conversation.objects.count()
                        + 1
                    )
                ),
                external_conversation_id=(
                    external_conversation_id
                ),
                unread_count=(
                    0
                    if is_read
                    else 1
                ),
                is_starred=(
                    is_starred
                ),
            )
        )


        self.message = (
            InboxMessage.objects.create(
                user=self.user,
                organization=(
                    self.organization
                ),
                email_account=(
                    self.account
                ),
                conversation=(
                    self.conversation
                ),
                platform=provider,
                direction="inbound",
                folder=folder,
                external_message_id=(
                    external_message_id
                ),
                external_conversation_id=(
                    external_conversation_id
                ),
                sender="customer@example.com",
                recipients=(
                    self.account
                    .email_address
                ),
                subject="P3A",
                body="Body",
                received_at=(
                    timezone.now()
                ),
                is_read=is_read,
                is_starred=(
                    is_starred
                ),
                status="sent",
            )
        )


class ProviderMutationServiceTests(
    MailMutationFixtureMixin,
    TestCase,
):

    @patch(
        "inbox.services.mail_mutations.build"
    )
    @patch(
        "inbox.services.mail_mutations."
        "get_gmail_credentials"
    )
    def test_gmail_message_read_and_unread_use_provider_message_id(
        self,
        mocked_credentials,
        mocked_build,
    ):
        self.build_fixture(
            provider="gmail",
            is_read=False,
        )


        service = (
            MagicMock()
        )

        mocked_build.return_value = (
            service
        )


        set_message_read(
            message=self.message,
            user=self.user,
            is_read=True,
        )


        (
            service.users
            .return_value
            .messages
            .return_value
            .modify
            .assert_called_with(
                userId="me",
                id="provider-message-1",
                body={
                    "removeLabelIds": [
                        "UNREAD"
                    ]
                },
            )
        )


        self.message.refresh_from_db()
        self.conversation.refresh_from_db()


        self.assertTrue(
            self.message.is_read
        )

        self.assertEqual(
            self.conversation.unread_count,
            0,
        )


        set_message_read(
            message=self.message,
            user=self.user,
            is_read=False,
        )


        second_call = (
            service.users
            .return_value
            .messages
            .return_value
            .modify
            .call_args
        )


        self.assertEqual(
            second_call.kwargs[
                "body"
            ],
            {
                "addLabelIds": [
                    "UNREAD"
                ]
            },
        )


        self.message.refresh_from_db()
        self.conversation.refresh_from_db()


        self.assertFalse(
            self.message.is_read
        )

        self.assertEqual(
            self.conversation.unread_count,
            1,
        )


    @patch(
        "inbox.services.mail_mutations."
        "requests.patch"
    )
    @patch(
        "inbox.services.mail_mutations."
        "get_microsoft_access_token",
        return_value="token",
    )
    def test_outlook_star_updates_graph_and_local_state(
        self,
        mocked_token,
        mocked_patch,
    ):
        self.build_fixture(
            provider="outlook",
            is_starred=False,
        )


        response = (
            MagicMock()
        )

        response.status_code = 200

        mocked_patch.return_value = (
            response
        )


        set_message_star(
            message=self.message,
            user=self.user,
            is_starred=True,
        )


        payload = (
            mocked_patch
            .call_args
            .kwargs[
                "json"
            ]
        )


        self.assertEqual(
            payload,
            {
                "flag": {
                    "flagStatus":
                        "flagged"
                }
            },
        )


        self.message.refresh_from_db()
        self.conversation.refresh_from_db()


        self.assertTrue(
            self.message.is_starred
        )

        self.assertTrue(
            self.conversation.is_starred
        )


    @patch(
        "inbox.services.mail_mutations."
        "requests.post"
    )
    @patch(
        "inbox.services.mail_mutations."
        "get_microsoft_access_token",
        return_value="token",
    )
    def test_outlook_trash_updates_provider_id_and_local_folder(
        self,
        mocked_token,
        mocked_post,
    ):
        self.build_fixture(
            provider="outlook",
        )


        response = (
            MagicMock()
        )

        response.status_code = 201

        response.json.return_value = {
            "id":
                "moved-message-id"
        }

        mocked_post.return_value = (
            response
        )


        trash_message(
            message=self.message,
            user=self.user,
        )


        self.message.refresh_from_db()


        self.assertEqual(
            self.message.folder,
            "trash",
        )

        self.assertEqual(
            self.message.external_message_id,
            "moved-message-id",
        )


        self.assertEqual(
            mocked_post
            .call_args
            .kwargs[
                "json"
            ],
            {
                "destinationId":
                    "deleteditems"
            },
        )


    @patch(
        "inbox.services.mail_mutations.build"
    )
    @patch(
        "inbox.services.mail_mutations."
        "get_gmail_credentials"
    )
    def test_gmail_conversation_read_uses_thread_mutation(
        self,
        mocked_credentials,
        mocked_build,
    ):
        self.build_fixture(
            provider="gmail",
            is_read=False,
        )


        second = (
            InboxMessage.objects.create(
                user=self.user,
                organization=(
                    self.organization
                ),
                email_account=(
                    self.account
                ),
                conversation=(
                    self.conversation
                ),
                platform="gmail",
                direction="inbound",
                folder="inbox",
                external_message_id=(
                    "provider-message-2"
                ),
                external_conversation_id=(
                    "provider-thread-1"
                ),
                sender="second@example.com",
                recipients=(
                    self.account
                    .email_address
                ),
                subject="P3A 2",
                body="Body",
                received_at=(
                    timezone.now()
                ),
                is_read=False,
                status="sent",
            )
        )


        service = (
            MagicMock()
        )

        mocked_build.return_value = (
            service
        )


        result = (
            set_conversation_read(
                conversation=(
                    self.conversation
                ),
                user=self.user,
                is_read=True,
            )
        )


        (
            service.users
            .return_value
            .threads
            .return_value
            .modify
            .assert_called_once_with(
                userId="me",
                id="provider-thread-1",
                body={
                    "removeLabelIds": [
                        "UNREAD"
                    ]
                },
            )
        )


        self.message.refresh_from_db()
        second.refresh_from_db()
        self.conversation.refresh_from_db()


        self.assertTrue(
            self.message.is_read
        )

        self.assertTrue(
            second.is_read
        )

        self.assertEqual(
            self.conversation.unread_count,
            0,
        )

        self.assertEqual(
            result[
                "updated"
            ],
            2,
        )


class MailMutationAPITests(
    MailMutationFixtureMixin,
    APITestCase,
):

    @patch(
        "inbox.services.mail_mutations.build"
    )
    @patch(
        "inbox.services.mail_mutations."
        "get_gmail_credentials"
    )
    def test_message_read_state_endpoint_supports_mark_unread(
        self,
        mocked_credentials,
        mocked_build,
    ):
        self.build_fixture(
            provider="gmail",
            is_read=True,
        )


        mocked_build.return_value = (
            MagicMock()
        )


        self.client.force_authenticate(
            user=self.user
        )


        response = (
            self.client.post(
                (
                    "/api/inbox/message/"
                    + str(
                        self.message.id
                    )
                    + "/read-state/"
                ),
                {
                    "is_read":
                        False
                },
                format="json",
            )
        )


        self.assertEqual(
            response.status_code,
            200,
        )


        self.message.refresh_from_db()


        self.assertFalse(
            self.message.is_read
        )


    def test_message_read_state_is_user_scoped(
        self,
    ):
        self.build_fixture(
            provider="gmail",
        )


        other = (
            User.objects.create_user(
                email=(
                    "other-p3a@oneuch.test"
                ),
                password="pass123",
            )
        )


        self.client.force_authenticate(
            user=other
        )


        response = (
            self.client.post(
                (
                    "/api/inbox/message/"
                    + str(
                        self.message.id
                    )
                    + "/read-state/"
                ),
                {
                    "is_read":
                        True
                },
                format="json",
            )
        )


        self.assertEqual(
            response.status_code,
            404,
        )


class IncrementalMutableRefreshTests(
    MailMutationFixtureMixin,
    TestCase,
):

    def test_gmail_incremental_existing_refreshes_read_and_star_without_reprocessing(
        self,
    ):
        self.build_fixture(
            provider="gmail",
            is_read=False,
            is_starred=False,
        )


        self.account.history_sync_completed_at = (
            timezone.now()
        )

        self.account.save(
            update_fields=[
                "history_sync_completed_at"
            ]
        )


        service = (
            MagicMock()
        )


        list_result = (
            MagicMock()
        )

        list_result.execute.return_value = {
            "messages": [
                {
                    "id":
                        self.message
                        .external_message_id
                }
            ]
        }


        get_result = (
            MagicMock()
        )

        get_result.execute.return_value = {
            "id":
                self.message
                .external_message_id,

            "threadId":
                self.conversation
                .external_conversation_id,

            "labelIds": [
                "INBOX",
                "STARRED",
            ],
        }


        (
            service.users
            .return_value
            .messages
            .return_value
            .list
            .return_value
        ) = list_result


        (
            service.users
            .return_value
            .messages
            .return_value
            .get
            .return_value
        ) = get_result


        with (
            patch(
                "googleapis.services.gmail_sync."
                "get_gmail_credentials",
                return_value=object(),
            ),
            patch(
                "googleapis.services.gmail_sync.build",
                return_value=service,
            ),
            patch(
                "googleapis.services.gmail_sync."
                "MessageProcessor"
            ) as processor,
            patch(
                "googleapis.services.gmail_sync."
                "get_channel_layer"
            ) as channel_layer,
        ):

            from googleapis.services.gmail_sync import (
                _fetch_gmail_emails_impl,
            )


            result = (
                _fetch_gmail_emails_impl(
                    user=self.user,
                    email_account=(
                        self.account
                    ),
                )
            )


        self.message.refresh_from_db()
        self.conversation.refresh_from_db()


        self.assertTrue(
            self.message.is_read
        )

        self.assertTrue(
            self.message.is_starred
        )

        self.assertEqual(
            result[
                "skipped"
            ],
            1,
        )

        self.assertEqual(
            result[
                "processed"
            ],
            0,
        )

        processor.assert_not_called()

        channel_layer.assert_not_called()


    def test_outlook_incremental_existing_refreshes_read_and_star_without_reprocessing(
        self,
    ):
        self.build_fixture(
            provider="outlook",
            is_read=False,
            is_starred=False,
        )


        self.account.history_sync_completed_at = (
            timezone.now()
        )

        self.account.save(
            update_fields=[
                "history_sync_completed_at"
            ]
        )


        graph_message = {
            "id":
                self.message
                .external_message_id,

            "conversationId":
                self.conversation
                .external_conversation_id,

            "subject":
                "P3A",

            "body": {
                "contentType":
                    "Text",

                "content":
                    "Body",
            },

            "bodyPreview":
                "Body",

            "receivedDateTime":
                timezone.now()
                .isoformat(),

            "sentDateTime":
                timezone.now()
                .isoformat(),

            "isRead":
                True,

            "from": {
                "emailAddress": {
                    "address":
                        "customer@example.com"
                }
            },

            "toRecipients": [
                {
                    "emailAddress": {
                        "address":
                            self.account
                            .email_address
                    }
                }
            ],

            "ccRecipients":
                [],

            "bccRecipients":
                [],

            "replyTo":
                [],

            "hasAttachments":
                False,

            "attachments":
                [],

            "flag": {
                "flagStatus":
                    "flagged"
            },
        }


        inbox_response = (
            MagicMock()
        )

        inbox_response.status_code = 200

        inbox_response.json.return_value = {
            "value": [
                graph_message
            ]
        }


        sent_response = (
            MagicMock()
        )

        sent_response.status_code = 200

        sent_response.json.return_value = {
            "value": []
        }


        def graph_get(
            url,
            **kwargs,
        ):
            if (
                "/mailFolders/inbox/"
                in url
            ):
                return inbox_response

            if (
                "/mailFolders/sentitems/"
                in url
            ):
                return sent_response

            raise AssertionError(
                "Unexpected Graph URL"
            )


        with (
            patch(
                "microsoftapis.services.outlook_sync."
                "get_microsoft_access_token",
                return_value="token",
            ),
            patch(
                "microsoftapis.services.outlook_sync."
                "requests.get",
                side_effect=graph_get,
            ),
            patch(
                "microsoftapis.services.outlook_sync."
                "MessageProcessor"
            ) as processor,
            patch(
                "microsoftapis.services.outlook_sync."
                "get_channel_layer"
            ) as channel_layer,
        ):

            from microsoftapis.services.outlook_sync import (
                fetch_outlook_emails,
            )


            result = (
                fetch_outlook_emails(
                    user=self.user,
                    email_account=(
                        self.account
                    ),
                )
            )


        self.message.refresh_from_db()


        self.assertTrue(
            self.message.is_read
        )

        self.assertTrue(
            self.message.is_starred
        )

        self.assertEqual(
            result[
                "skipped"
            ],
            1,
        )

        processor.assert_not_called()

        channel_layer.assert_not_called()
