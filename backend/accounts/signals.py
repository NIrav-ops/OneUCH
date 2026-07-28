from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings
from accounts.models import Organization
from inbox.models import AttachmentPolicy

User = settings.AUTH_USER_MODEL

@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_user_attachment_policy(sender, instance, created, **kwargs):
    if created:
        AttachmentPolicy.objects.create(
            user=instance,
            allowed_extensions=["pdf", "docx", "xlsx"]
        )
