from django.db import models


class TimelineEvent(models.Model):

    EVENT_TYPES = (
        ("message_received", "Message Received"),
        ("action_created", "Action Created"),
        ("action_completed", "Action Completed"),
        ("approval_created", "Approval Created"),
        ("approval_approved", "Approval Approved"),
        ("approval_rejected", "Approval Rejected"),
        ("followup_created", "Follow Up Created"),
        ("followup_completed", "Follow Up Completed"),
        ("notification_sent", "Notification Sent"),
        ("escalated", "Escalated"),
    )

    conversation = models.ForeignKey(
        "inbox.Conversation",
        on_delete=models.CASCADE,
        related_name="timeline_events",
    )

    event_type = models.CharField(
        max_length=50,
        choices=EVENT_TYPES,
    )

    title = models.CharField(max_length=500)

    details = models.JSONField(
        default=dict,
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    event_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title