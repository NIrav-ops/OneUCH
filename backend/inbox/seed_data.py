from django.contrib.auth import get_user_model
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

    print("🔹 Seeding base data...")

    # 1️⃣ Create admin user
    user, _ = User.objects.get_or_create(
        email="admin@test.com",
        defaults={
            "is_staff": True,
            "is_superuser": True,
        },
    )
    user.set_password("admin123")
    user.save()

    # 2️⃣ Create organization
    policy, _ = AttachmentPolicy.objects.get_or_create(
        name="Default Org Policy",
        defaults={
            "max_size_mb": 25,
            "allow_download": True,
            "allow_preview": True,
        },
    )

    org, _ = Organization.objects.get_or_create(
        slug="default-org",
        defaults={
            "name": "Default Organization",
            "attachment_policy": policy,
        },
    )

    if not org.attachment_policy:
        org.attachment_policy = policy
        org.save()

    # 3️⃣ Link user to org as OWNER
    OrganizationUser.objects.get_or_create(
        user=user,
        organization=org,
        defaults={"role": "owner"},
    )

    # 4️⃣ Create sample inbox messages
    messages = []
    for i in range(1, 4):
        msg = InboxMessage.objects.create(
            user=user,
            organization=org,
            platform="gmail",
            direction="inbound",
            external_message_id=f"gmail-msg-{i}",
            sender="test@gmail.com",
            recipients="user@company.com",
            subject=f"Test Email {i}",
            body="This is a test email body",
            received_at=timezone.now(),
        )
        messages.append(msg)

    # 5️⃣ Attach a sample attachment to first message
    from django.core.files.base import ContentFile

    Attachment.objects.create(
        message=messages[0],
        filename="sample.txt",
        content_type="text/plain",
        size=1024,
        file=ContentFile(b"Sample attachment content", name="sample.txt"),
    )

    print("✅ Seed data created successfully")
    print("👉 Admin email: admin@test.com")
    print("👉 Password: admin123")
