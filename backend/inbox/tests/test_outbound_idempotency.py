import json


from unittest.mock import (
    MagicMock,
    patch,
)


from django.conf import (
    settings,
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
    APIClient,
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

from inbox.services.outbound_idempotency import (
    OutboundIdempotencyUnavailable,
    bind_outbound_message,
    build_outbound_fingerprint,
    claim_outbound_intent,
    get_outbound_intent_for_message,
    replay_outbound_intent,
)

from inbox.tasks import (
    send_email_task,
)


class FakeRedis:

    def __init__(
        self,
    ):

        self.values = {}


    def set(
        self,
        name,
        value,
        nx=False,
        ex=None,
    ):

        if (
            nx
            and
            name in self.values
        ):

            return False


        self.values[
            name
        ] = str(
            value
        )


        return True


    def get(
        self,
        name,
    ):

        return self.values.get(
            name
        )


    def delete(
        self,
        *names,
    ):

        removed = 0


        for name in names:

            if name in self.values:

                del self.values[
                    name
                ]

                removed += 1


        return removed


class OutboundIdempotencyTests(
    TestCase
):

    def setUp(
        self,
    ):

        User = get_user_model()


        self.user = (
            User.objects.create_user(
                email=(
                    "idempotency-user"
                    "@oneuch.local"
                ),
                password=(
                    "test-password-123"
                ),
            )
        )


        self.organization = (
            Organization.objects.create(
                name=(
                    "Idempotency Organization"
                ),
                slug=(
                    "idempotency-organization"
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


        self.gmail = (
            EmailAccount.objects.create(
                user=self.user,
                email_address=(
                    "idempotency-gmail"
                    "@oneuch.local"
                ),
                account_type="gmail",
                credential_status="active",
                is_active=True,
            )
        )


        self.client = APIClient()

        self.client.force_authenticate(
            user=self.user
        )


        self.redis = FakeRedis()


        self.redis_patch = (
            patch.object(
                settings,
                "REDIS_CLIENT",
                self.redis,
            )
        )


        self.redis_patch.start()


        self.addCleanup(
            self.redis_patch.stop
        )


    def make_inbound(
        self,
        *,
        key="reply-idempotency",
    ):

        conversation = (
            Conversation.objects.create(
                user=self.user,
                organization=(
                    self.organization
                ),
                email_account=(
                    self.gmail
                ),
                subject=(
                    "Customer question"
                ),
                conversation_key=key,
                external_conversation_id=(
                    "gmail-thread-"
                    +
                    key
                ),
            )
        )


        message = (
            InboxMessage.objects.create(
                user=self.user,
                organization=(
                    self.organization
                ),
                email_account=(
                    self.gmail
                ),
                conversation=(
                    conversation
                ),
                platform="gmail",
                folder="inbox",
                direction="inbound",
                external_message_id=(
                    "gmail-source-"
                    +
                    key
                ),
                external_conversation_id=(
                    "gmail-thread-"
                    +
                    key
                ),
                sender=(
                    "customer@example.com"
                ),
                sender_meta={
                    "name":
                        "Customer",

                    "email":
                        "customer@example.com",
                },
                recipients=(
                    self.gmail.email_address
                ),
                recipient_meta={
                    "to": [
                        {
                            "name":
                                "",

                            "email":
                                self.gmail.email_address,
                        }
                    ],

                    "cc":
                        [],

                    "bcc":
                        [],

                    "reply_to":
                        [],
                },
                subject=(
                    "Customer question"
                ),
                body=(
                    "Please respond."
                ),
                received_at=(
                    timezone.now()
                ),
                is_read=True,
                is_draft=False,
                status="sent",
            )
        )


        return (
            conversation,
            message,
        )


    def make_queued_reply(
        self,
        *,
        key,
        body="Queued reply",
    ):

        conversation, source = (
            self.make_inbound(
                key=key
            )
        )


        reply = (
            InboxMessage.objects.create(
                user=self.user,
                organization=(
                    self.organization
                ),
                email_account=(
                    self.gmail
                ),
                conversation=(
                    conversation
                ),
                platform="gmail",
                folder="outbox",
                direction="outbound",
                external_message_id=(
                    "pending"
                ),
                external_conversation_id=(
                    source
                    .external_conversation_id
                ),
                in_reply_to=(
                    source
                    .external_message_id
                ),
                sender=(
                    self.gmail
                    .email_address
                ),
                sender_meta={
                    "name":
                        "",

                    "email":
                        self.gmail
                        .email_address,
                },
                recipients=(
                    "customer@example.com"
                ),
                recipient_meta={
                    "to": [
                        {
                            "name":
                                "",

                            "email":
                                "customer@example.com",
                        }
                    ],

                    "cc":
                        [],

                    "bcc":
                        [],

                    "reply_to":
                        [],
                },
                subject=(
                    "Re: Customer question"
                ),
                body=body,
                received_at=(
                    timezone.now()
                ),
                is_read=True,
                is_draft=False,
                status="queued",
            )
        )


        return (
            source,
            reply,
        )


    def bind_reply_intent(
        self,
        *,
        reply,
        key,
    ):

        fingerprint = (
            build_outbound_fingerprint(
                operation="reply",
                payload={
                    "message_id":
                        reply.id
                },
            )
        )


        (
            intent,
            created,
        ) = (
            claim_outbound_intent(
                user_id=(
                    self.user.id
                ),
                idempotency_key=(
                    key
                ),
                operation="reply",
                fingerprint=(
                    fingerprint
                ),
            )
        )


        self.assertTrue(
            created
        )


        bind_outbound_message(
            user_id=(
                self.user.id
            ),
            idempotency_key=(
                key
            ),
            message_id=(
                reply.id
            ),
        )


        return intent


    @patch(
        "inbox.views.send_message."
        "async_to_sync",
        return_value=(
            lambda *args, **kwargs:
                None
        ),
    )
    @patch(
        "inbox.views.send_message."
        "get_channel_layer",
        return_value=MagicMock(),
    )
    @patch(
        "inbox.views.send_message."
        "get_gmail_credentials"
    )
    @patch(
        "inbox.views.send_message."
        "build"
    )
    def test_same_send_key_contacts_gmail_once(
        self,
        mocked_build,
        mocked_credentials,
        mocked_channel,
        mocked_async,
    ):

        service = MagicMock()


        (
            service.users
            .return_value
            .messages
            .return_value
            .send
            .return_value
            .execute
            .return_value
        ) = {
            "id":
                "gmail-provider-once"
        }


        mocked_build.return_value = (
            service
        )


        payload = {
            "to":
                "recipient@example.com",

            "subject":
                "Idempotent send",

            "body":
                "One semantic send",

            "account_id":
                self.gmail.id,
        }


        key = (
            "send-idempotency-0001"
        )


        first = self.client.post(
            "/api/inbox/send/",
            payload,
            format="json",
            HTTP_IDEMPOTENCY_KEY=(
                key
            ),
        )


        second = self.client.post(
            "/api/inbox/send/",
            payload,
            format="json",
            HTTP_IDEMPOTENCY_KEY=(
                key
            ),
        )


        self.assertEqual(
            first.status_code,
            200,
        )


        self.assertEqual(
            second.status_code,
            200,
        )


        self.assertTrue(
            second.data[
                "idempotent_replay"
            ]
        )


        self.assertEqual(
            first.data[
                "message_id"
            ],
            second.data[
                "message_id"
            ],
        )


        self.assertEqual(
            (
                service.users
                .return_value
                .messages
                .return_value
                .send
                .return_value
                .execute
                .call_count
            ),
            1,
        )


        self.assertEqual(
            InboxMessage.objects
            .filter(
                user=self.user,
                direction="outbound",
                subject=(
                    "Idempotent send"
                ),
            )
            .count(),
            1,
        )


    @patch(
        "inbox.views.send_message."
        "async_to_sync",
        return_value=(
            lambda *args, **kwargs:
                None
        ),
    )
    @patch(
        "inbox.views.send_message."
        "get_channel_layer",
        return_value=MagicMock(),
    )
    @patch(
        "inbox.views.send_message."
        "get_gmail_credentials"
    )
    @patch(
        "inbox.views.send_message."
        "build"
    )
    def test_same_key_with_changed_payload_is_rejected(
        self,
        mocked_build,
        mocked_credentials,
        mocked_channel,
        mocked_async,
    ):

        service = MagicMock()


        (
            service.users
            .return_value
            .messages
            .return_value
            .send
            .return_value
            .execute
            .return_value
        ) = {
            "id":
                "gmail-provider-original"
        }


        mocked_build.return_value = (
            service
        )


        key = (
            "send-idempotency-0002"
        )


        first = self.client.post(
            "/api/inbox/send/",
            {
                "to":
                    "recipient@example.com",

                "subject":
                    "Conflict send",

                "body":
                    "Original payload",

                "account_id":
                    self.gmail.id,
            },
            format="json",
            HTTP_IDEMPOTENCY_KEY=(
                key
            ),
        )


        second = self.client.post(
            "/api/inbox/send/",
            {
                "to":
                    "recipient@example.com",

                "subject":
                    "Conflict send",

                "body":
                    "Changed payload",

                "account_id":
                    self.gmail.id,
            },
            format="json",
            HTTP_IDEMPOTENCY_KEY=(
                key
            ),
        )


        self.assertEqual(
            first.status_code,
            200,
        )


        self.assertEqual(
            second.status_code,
            409,
        )


        self.assertIn(
            "different outbound message",
            second.data[
                "error"
            ],
        )


        self.assertEqual(
            (
                service.users
                .return_value
                .messages
                .return_value
                .send
                .return_value
                .execute
                .call_count
            ),
            1,
        )


    @patch(
        "inbox.views.reply."
        "send_email_task.delay"
    )
    def test_same_reply_key_creates_and_queues_once(
        self,
        mocked_delay,
    ):

        conversation, source = (
            self.make_inbound()
        )


        key = (
            "reply-idempotency-0001"
        )


        payload = {
            "body":
                "One reply only",

            "mode":
                "reply",
        }


        first = self.client.post(
            (
                "/api/inbox/conversations/"
                +
                str(
                    conversation.id
                )
                +
                "/reply/"
            ),
            payload,
            format="json",
            HTTP_IDEMPOTENCY_KEY=(
                key
            ),
        )


        second = self.client.post(
            (
                "/api/inbox/conversations/"
                +
                str(
                    conversation.id
                )
                +
                "/reply/"
            ),
            payload,
            format="json",
            HTTP_IDEMPOTENCY_KEY=(
                key
            ),
        )


        self.assertEqual(
            first.status_code,
            202,
        )


        self.assertEqual(
            second.status_code,
            202,
        )


        self.assertTrue(
            second.data[
                "idempotent_replay"
            ]
        )


        self.assertEqual(
            first.data[
                "message_id"
            ],
            second.data[
                "message_id"
            ],
        )


        mocked_delay.assert_called_once()


        self.assertEqual(
            InboxMessage.objects
            .filter(
                user=self.user,
                conversation=(
                    conversation
                ),
                direction="outbound",
            )
            .count(),
            1,
        )


    @patch(
        "inbox.views.reply."
        "send_email_task.delay"
    )
    def test_same_reply_key_with_changed_body_is_rejected(
        self,
        mocked_delay,
    ):

        conversation, source = (
            self.make_inbound(
                key=(
                    "reply-conflict"
                )
            )
        )


        key = (
            "reply-idempotency-conflict-0001"
        )


        first = self.client.post(
            (
                "/api/inbox/conversations/"
                +
                str(
                    conversation.id
                )
                +
                "/reply/"
            ),
            {
                "body":
                    "Original reply body",

                "mode":
                    "reply",
            },
            format="json",
            HTTP_IDEMPOTENCY_KEY=(
                key
            ),
        )


        second = self.client.post(
            (
                "/api/inbox/conversations/"
                +
                str(
                    conversation.id
                )
                +
                "/reply/"
            ),
            {
                "body":
                    "Changed reply body",

                "mode":
                    "reply",
            },
            format="json",
            HTTP_IDEMPOTENCY_KEY=(
                key
            ),
        )


        self.assertEqual(
            first.status_code,
            202,
        )


        self.assertEqual(
            second.status_code,
            409,
        )


        self.assertIn(
            "different outbound message",
            second.data[
                "error"
            ],
        )


        mocked_delay.assert_called_once()


        self.assertEqual(
            InboxMessage.objects
            .filter(
                user=self.user,
                conversation=(
                    conversation
                ),
                direction="outbound",
            )
            .count(),
            1,
        )


    @patch(
        "inbox.tasks."
        "send_gmail_reply"
    )
    def test_completed_provider_intent_repairs_retry_without_resend(
        self,
        mocked_gmail_reply,
    ):

        conversation, source = (
            self.make_inbound(
                key=(
                    "task-replay"
                )
            )
        )


        reply = (
            InboxMessage.objects.create(
                user=self.user,
                organization=(
                    self.organization
                ),
                email_account=(
                    self.gmail
                ),
                conversation=(
                    conversation
                ),
                platform="gmail",
                folder="outbox",
                direction="outbound",
                external_message_id=(
                    "pending"
                ),
                external_conversation_id=(
                    source
                    .external_conversation_id
                ),
                in_reply_to=(
                    source
                    .external_message_id
                ),
                sender=(
                    self.gmail
                    .email_address
                ),
                sender_meta={
                    "name":
                        "",

                    "email":
                        self.gmail.email_address,
                },
                recipients=(
                    "customer@example.com"
                ),
                recipient_meta={
                    "to": [
                        {
                            "name":
                                "",

                            "email":
                                "customer@example.com",
                        }
                    ],

                    "cc":
                        [],

                    "bcc":
                        [],

                    "reply_to":
                        [],
                },
                subject=(
                    "Re: Customer question"
                ),
                body=(
                    "Task replay body"
                ),
                received_at=(
                    timezone.now()
                ),
                is_read=True,
                is_draft=False,
                status="queued",
            )
        )


        key = (
            "reply-task-replay-0001"
        )


        fingerprint = (
            build_outbound_fingerprint(
                operation="reply",
                payload={
                    "message_id":
                        reply.id
                },
            )
        )


        (
            intent,
            created,
        ) = (
            claim_outbound_intent(
                user_id=(
                    self.user.id
                ),
                idempotency_key=(
                    key
                ),
                operation="reply",
                fingerprint=(
                    fingerprint
                ),
            )
        )


        self.assertTrue(
            created
        )


        bind_outbound_message(
            user_id=(
                self.user.id
            ),
            idempotency_key=(
                key
            ),
            message_id=(
                reply.id
            ),
        )


        mocked_gmail_reply.return_value = {
            "id":
                "gmail-reply-provider-once"
        }


        send_email_task.run(
            self.gmail.id,
            "customer@example.com",
            "Re: Customer question",
            "Task replay body",
            reply.id,
        )


        reply.refresh_from_db()


        self.assertEqual(
            reply.status,
            "sent",
        )


        self.assertEqual(
            reply.external_message_id,
            "gmail-reply-provider-once",
        )


        # Simulate the exact dangerous retry shape:
        # provider accepted, but local state is subsequently
        # observed as queued/pending again.
        reply.status = "queued"

        reply.folder = "outbox"

        reply.external_message_id = (
            "pending"
        )


        reply.save(
            update_fields=[
                "status",
                "folder",
                "external_message_id",
            ]
        )


        send_email_task.run(
            self.gmail.id,
            "customer@example.com",
            "Re: Customer question",
            "Task replay body",
            reply.id,
        )


        reply.refresh_from_db()


        self.assertEqual(
            mocked_gmail_reply.call_count,
            1,
        )


        self.assertEqual(
            reply.status,
            "sent",
        )


        self.assertEqual(
            reply.external_message_id,
            "gmail-reply-provider-once",
        )


    @patch(
        "inbox.tasks."
        "send_gmail_reply"
    )
    def test_duplicate_delivery_lock_blocks_parallel_task_replay(
        self,
        mocked_gmail_reply,
    ):

        conversation, source = (
            self.make_inbound(
                key=(
                    "parallel-task"
                )
            )
        )


        reply = (
            InboxMessage.objects.create(
                user=self.user,
                organization=(
                    self.organization
                ),
                email_account=(
                    self.gmail
                ),
                conversation=(
                    conversation
                ),
                platform="gmail",
                folder="outbox",
                direction="outbound",
                external_message_id="pending",
                external_conversation_id=(
                    source
                    .external_conversation_id
                ),
                in_reply_to=(
                    source
                    .external_message_id
                ),
                sender=(
                    self.gmail
                    .email_address
                ),
                recipients=(
                    "customer@example.com"
                ),
                recipient_meta={
                    "to": [
                        {
                            "name":
                                "",

                            "email":
                                "customer@example.com",
                        }
                    ],

                    "cc":
                        [],

                    "bcc":
                        [],

                    "reply_to":
                        [],
                },
                subject=(
                    "Re: Customer question"
                ),
                body=(
                    "Parallel task"
                ),
                received_at=(
                    timezone.now()
                ),
                is_read=True,
                is_draft=False,
                status="queued",
            )
        )


        key = (
            "parallel-task-lock-0001"
        )


        fingerprint = (
            build_outbound_fingerprint(
                operation="reply",
                payload={
                    "message_id":
                        reply.id
                },
            )
        )


        claim_outbound_intent(
            user_id=(
                self.user.id
            ),
            idempotency_key=(
                key
            ),
            operation="reply",
            fingerprint=(
                fingerprint
            ),
        )


        bind_outbound_message(
            user_id=(
                self.user.id
            ),
            idempotency_key=(
                key
            ),
            message_id=(
                reply.id
            ),
        )


        # Pre-create the provider-delivery lease exactly as a
        # concurrently executing worker would.
        self.redis.set(
            (
                "oneuch:outbound-delivery-lock:"
                +
                str(
                    self.user.id
                )
                +
                ":"
                +
                key
            ),
            "1",
            nx=True,
            ex=900,
        )


        result = (
            send_email_task.run(
                self.gmail.id,
                "customer@example.com",
                "Re: Customer question",
                "Parallel task",
                reply.id,
            )
        )


        self.assertEqual(
            result[
                "status"
            ],
            "duplicate_delivery_in_progress",
        )


        mocked_gmail_reply.assert_not_called()


    @patch(
        "inbox.tasks."
        "send_gmail_reply"
    )
    def test_provider_dispatch_exception_becomes_uncertain_without_retry(
        self,
        mocked_gmail_reply,
    ):

        source, reply = (
            self.make_queued_reply(
                key=(
                    "provider-uncertain"
                ),
                body=(
                    "Provider uncertainty body"
                ),
            )
        )


        key = (
            "provider-uncertain-0001"
        )


        self.bind_reply_intent(
            reply=reply,
            key=key,
        )


        mocked_gmail_reply.side_effect = (
            TimeoutError(
                "simulated provider response loss"
            )
        )


        first = (
            send_email_task.run(
                self.gmail.id,
                "customer@example.com",
                "Re: Customer question",
                reply.body,
                reply.id,
            )
        )


        self.assertEqual(
            first[
                "status"
            ],
            "delivery_uncertain",
        )


        reply.refresh_from_db()


        self.assertEqual(
            reply.status,
            "failed",
        )


        intent = (
            get_outbound_intent_for_message(
                user_id=(
                    self.user.id
                ),
                message_id=(
                    reply.id
                ),
            )
        )


        self.assertEqual(
            intent[
                "state"
            ],
            "delivery_uncertain",
        )


        replay_payload, replay_status = (
            replay_outbound_intent(
                intent
            )
        )


        self.assertEqual(
            replay_status,
            409,
        )


        self.assertEqual(
            replay_payload[
                "status"
            ],
            "delivery_uncertain",
        )


        # Even if the same Celery task is delivered again,
        # the provider must not be contacted twice.
        second = (
            send_email_task.run(
                self.gmail.id,
                "customer@example.com",
                "Re: Customer question",
                reply.body,
                reply.id,
            )
        )


        self.assertEqual(
            second[
                "status"
            ],
            "delivery_uncertain",
        )


        self.assertEqual(
            mocked_gmail_reply.call_count,
            1,
        )


    @patch(
        "inbox.tasks."
        "complete_outbound_intent"
    )
    @patch(
        "inbox.tasks."
        "send_gmail_reply"
    )
    def test_provider_success_with_redis_finalize_failure_never_resends(
        self,
        mocked_gmail_reply,
        mocked_complete,
    ):

        source, reply = (
            self.make_queued_reply(
                key=(
                    "finalize-degraded"
                ),
                body=(
                    "Finalize degraded body"
                ),
            )
        )


        key = (
            "finalize-degraded-0001"
        )


        self.bind_reply_intent(
            reply=reply,
            key=key,
        )


        mocked_gmail_reply.return_value = {
            "id":
                "gmail-provider-accepted-once"
        }


        mocked_complete.side_effect = (
            OutboundIdempotencyUnavailable(
                "simulated Redis finalize outage"
            )
        )


        first = (
            send_email_task.run(
                self.gmail.id,
                "customer@example.com",
                "Re: Customer question",
                reply.body,
                reply.id,
            )
        )


        self.assertEqual(
            first[
                "status"
            ],
            "sent_idempotency_finalize_degraded",
        )


        reply.refresh_from_db()


        self.assertEqual(
            reply.status,
            "sent",
        )


        self.assertEqual(
            reply.external_message_id,
            "gmail-provider-accepted-once",
        )


        # A task replay is now stopped by durable local Sent state
        # even though Redis finalization was unavailable.
        second = (
            send_email_task.run(
                self.gmail.id,
                "customer@example.com",
                "Re: Customer question",
                reply.body,
                reply.id,
            )
        )


        self.assertEqual(
            second[
                "status"
            ],
            "already_sent",
        )


        self.assertEqual(
            mocked_gmail_reply.call_count,
            1,
        )


    @patch(
        "inbox.views.send_message."
        "UnifiedSendMessageAPIView.send_with_data"
    )
    def test_draft_send_uses_stable_server_idempotency_key(
        self,
        mocked_send,
    ):

        conversation = (
            Conversation.objects.create(
                user=self.user,
                organization=(
                    self.organization
                ),
                email_account=(
                    self.gmail
                ),
                subject=(
                    "Draft send"
                ),
                conversation_key=(
                    "idempotent-draft-send"
                ),
            )
        )


        draft = (
            InboxMessage.objects.create(
                user=self.user,
                organization=(
                    self.organization
                ),
                email_account=(
                    self.gmail
                ),
                conversation=(
                    conversation
                ),
                platform="gmail",
                folder="draft",
                direction="outbound",
                external_message_id=(
                    "draft-local"
                ),
                sender=(
                    self.gmail.email_address
                ),
                recipients=(
                    "customer@example.com"
                ),
                recipient_meta={
                    "to": [
                        {
                            "name":
                                "",

                            "email":
                                "customer@example.com",
                        }
                    ],

                    "cc":
                        [],

                    "bcc":
                        [],

                    "reply_to":
                        [],
                },
                subject=(
                    "Draft send"
                ),
                body=(
                    "Draft body"
                ),
                received_at=(
                    timezone.now()
                ),
                is_read=True,
                is_draft=True,
                status="queued",
            )
        )


        mocked_send.return_value = (
            MagicMock(
                status_code=202,
                data={
                    "status":
                        "send_in_progress",

                    "idempotent_replay":
                        True,
                },
            )
        )


        response = self.client.post(
            (
                "/api/inbox/draft/send/"
                +
                str(
                    draft.id
                )
                +
                "/"
            ),
            {},
            format="json",
        )


        self.assertEqual(
            response.status_code,
            202,
        )


        self.assertTrue(
            InboxMessage.objects
            .filter(
                id=draft.id
            )
            .exists()
        )


        kwargs = (
            mocked_send
            .call_args
            .kwargs
        )


        self.assertEqual(
            kwargs[
                "idempotency_key"
            ],
            (
                "draft-send:"
                +
                str(
                    self.user.id
                )
                +
                ":"
                +
                str(
                    draft.id
                )
            ),
        )


        self.assertEqual(
            kwargs[
                "idempotency_operation"
            ],
            "draft_send",
        )

    @patch(
        "inbox.views.send_message."
        "async_to_sync",
        return_value=(
            lambda *args, **kwargs:
                None
        ),
    )
    @patch(
        "inbox.views.send_message."
        "get_channel_layer",
        return_value=MagicMock(),
    )
    @patch(
        "inbox.views.send_message."
        "get_gmail_credentials"
    )
    @patch(
        "inbox.views.send_message."
        "build"
    )
    def test_same_send_key_replays_after_conversation_key_reconciliation(
        self,
        mocked_build,
        mocked_credentials,
        mocked_channel,
        mocked_async,
    ):

        service = MagicMock()


        (
            service.users
            .return_value
            .messages
            .return_value
            .send
            .return_value
            .execute
            .return_value
        ) = {
            "id":
                "provider-reconciled-id"
        }


        mocked_build.return_value = (
            service
        )


        key = (
            "send-after-reconciliation-0001"
        )


        payload = {
            "to":
                "recipient@example.com",

            "cc":
                [],

            "bcc":
                [],

            "subject":
                "Provider reconciliation",

            "body":
                "Stable semantic compose",

            "account_id":
                self.gmail.id,
        }


        first = self.client.post(
            "/api/inbox/send/",
            payload,
            format="json",
            HTTP_IDEMPOTENCY_KEY=(
                key
            ),
        )


        self.assertEqual(
            first.status_code,
            200,
        )


        sent = (
            InboxMessage.objects
            .select_related(
                "conversation"
            )
            .get(
                id=(
                    first.data[
                        "message_id"
                    ]
                )
            )
        )


        original_conversation_id = (
            sent.conversation_id
        )


        # Reproduce provider reconciliation:
        # Outlook/Gmail may upgrade the locally generated
        # conversation key to a provider-native thread key.
        sent.conversation.conversation_key = (
            "outlook_provider_conversation_reconciled"
        )


        sent.conversation.external_conversation_id = (
            "provider-thread-0001"
        )


        sent.conversation.save(
            update_fields=[
                "conversation_key",
                "external_conversation_id",
            ]
        )


        conversation_count_before = (
            Conversation.objects.count()
        )


        replay = self.client.post(
            "/api/inbox/send/",
            payload,
            format="json",
            HTTP_IDEMPOTENCY_KEY=(
                key
            ),
        )


        self.assertEqual(
            replay.status_code,
            200,
        )


        self.assertTrue(
            replay.data[
                "idempotent_replay"
            ]
        )


        self.assertEqual(
            replay.data[
                "message_id"
            ],
            sent.id,
        )


        self.assertEqual(
            (
                service.users
                .return_value
                .messages
                .return_value
                .send
                .return_value
                .execute
                .call_count
            ),
            1,
        )


        self.assertEqual(
            Conversation.objects.count(),
            conversation_count_before,
        )


        sent.refresh_from_db()


        self.assertEqual(
            sent.conversation_id,
            original_conversation_id,
        )


        # Conflict protection must still work after provider
        # reconciliation.
        changed = dict(
            payload
        )


        changed[
            "body"
        ] = (
            "Changed semantic compose"
        )


        conflict = self.client.post(
            "/api/inbox/send/",
            changed,
            format="json",
            HTTP_IDEMPOTENCY_KEY=(
                key
            ),
        )


        self.assertEqual(
            conflict.status_code,
            409,
        )


        self.assertEqual(
            (
                service.users
                .return_value
                .messages
                .return_value
                .send
                .return_value
                .execute
                .call_count
            ),
            1,
        )


        self.assertEqual(
            Conversation.objects.count(),
            conversation_count_before,
        )
