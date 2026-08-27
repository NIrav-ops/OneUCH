import os

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.utils import timezone

from inbox.models import (
    Organization,
    OrganizationUser,
    AttachmentPolicy,
    InboxMessage,
    Attachment,
)


def run():

    User = get_user_model()

    seed_admin_email = os.environ.get(
        "SEED_ADMIN_EMAIL",
        "admin@test.com",
    )

    seed_admin_password = os.environ.get(
        "SEED_ADMIN_PASSWORD"
    )

    if not seed_admin_password:

        raise RuntimeError(
            "SEED_ADMIN_PASSWORD must be set "
            "before running inbox.seed_data."
        )

    print(
        "Seeding local development data..."
    )

    # ---------------------------------------------------------
    # Admin user
    # ---------------------------------------------------------

    user, _ = User.objects.get_or_create(
        email=seed_admin_email,
        defaults={
            "is_staff": True,
            "is_superuser": True,
        },
    )

    user.is_staff = True
    user.is_superuser = True

    user.set_password(
        seed_admin_password
    )

    user.save()

    # ---------------------------------------------------------
    # Default attachment policy
    # ---------------------------------------------------------

    policy, _ = (
        AttachmentPolicy.objects.get_or_create(
            name="Default Org Policy",
            defaults={
                "max_size_mb": 25,
                "allow_download": True,
                "allow_preview": True,
            },
        )
    )

    # ---------------------------------------------------------
    # Default organization
    # ---------------------------------------------------------

    org, _ = Organization.objects.get_or_create(
        slug="default-org",
        defaults={
            "name": "Default Organization",
            "attachment_policy": policy,
        },
    )

    if not org.attachment_policy:

        org.attachment_policy = policy

        org.save(
            update_fields=[
                "attachment_policy",
            ]
        )

    # ---------------------------------------------------------
    # Organization membership
    # ---------------------------------------------------------

    OrganizationUser.objects.get_or_create(
        user=user,
        organization=org,
        defaults={
            "role": "owner",
        },
    )

    # ---------------------------------------------------------
    # Sample inbox messages
    # ---------------------------------------------------------

    messages = []

    for i in range(1, 4):

        msg = InboxMessage.objects.create(
            user=user,
            organization=org,
            platform="gmail",
            direction="inbound",
            external_message_id=(
                f"gmail-msg-{i}"
            ),
            sender="test@gmail.com",
            recipients="user@company.com",
            subject=f"Test Email {i}",
            body="This is a test email body",
            received_at=timezone.now(),
        )

        messages.append(
            msg
        )

    # ---------------------------------------------------------
    # Sample attachment
    # ---------------------------------------------------------

    Attachment.objects.create(
        message=messages[0],
        filename="sample.txt",
        content_type="text/plain",
        size=1024,
        file=ContentFile(
            b"Sample attachment content",
            name="sample.txt",
        ),
    )

    print(
        "Seed data created successfully."
    )

    print(
        f"Admin email: {seed_admin_email}"
    )

    print(
        "Admin password loaded from "
        "SEED_ADMIN_PASSWORD and was not printed."
    )
