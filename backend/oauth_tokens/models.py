from django.db import models
from django.conf import settings
from django.utils import timezone


class OAuthToken(models.Model):
    PROVIDER_CHOICES = [
        ("google", "Google"),
        ("microsoft", "Microsoft"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="oauth_tokens"
    )

    provider = models.CharField(
        max_length=50,
        choices=PROVIDER_CHOICES
    )

    access_token = models.TextField()
    refresh_token = models.TextField(null=True, blank=True)

    expires_at = models.DateTimeField()

    is_active = models.BooleanField(default=True)
    disabled_by_admin = models.BooleanField(default=False)
    revoked_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def is_expired(self):
        return timezone.now() >= self.expires_at

    def revoke(self):
        self.is_active = False
        self.revoked_at = timezone.now()
        self.save()

    def __str__(self):
        return f"{self.user} - {self.provider}"
