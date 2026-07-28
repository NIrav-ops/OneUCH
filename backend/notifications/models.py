from django.db import models
from django.conf import settings


class Notification(models.Model):
    NOTIFICATION_TYPES = [
        ("new_email", "New Email"),
        ("reply_received", "Reply Received"),
        ("send_failed", "Send Failed"),
        ("send_retried", "Send Retried"),
        ("send_success", "Send Success"),

        ("approval_assigned", "Approval Assigned"),
        ("action_assigned", "Action Assigned"),

        ("overdue_action", "Overdue Action"),
        ("overdue_approval", "Overdue Approval"),
        ("overdue_followup", "Overdue Follow Up"),

        ("escalation_level_1", "Escalation Level 1"),
        ("escalation_level_2", "Escalation Level 2"),
        ("escalation_level_3", "Escalation Level 3"),

        ("system", "System"),
    ]

    CHANNEL_TYPES = (
        ("in_app", "In App"),
        ("email", "Email"),
        ("teams", "Microsoft Teams"),
        ("slack", "Slack"),
        ("whatsapp", "WhatsApp"),
        ("sms", "SMS"),
    )

    SOURCE_TYPES = (
        ("workflow", "Workflow"),
        ("email", "Email"),
        ("system", "System"),
        ("api", "API"),
        ("ai", "AI"),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
        null=True,
        blank=True,
    )

    organization = models.ForeignKey(
        "inbox.Organization",
        on_delete=models.CASCADE,
        related_name="notifications",
        null=True,
        blank=True,
    )

    type = models.CharField(
        max_length=30,
        choices=NOTIFICATION_TYPES
    )

    workflow_instance = models.ForeignKey(
        "workflow.WorkflowInstance",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="notifications",
    )

    workflow_node = models.ForeignKey(
        "workflow.WorkflowNode",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="notifications",
    )

    channel = models.CharField(
        max_length=20,
        choices=CHANNEL_TYPES,
        default="in_app",
    )

    source_type = models.CharField(
        max_length=20,
        choices=SOURCE_TYPES,
        default="system",
        db_index=True,
    )

    STATUS_CHOICES = (
        ("pending", "Pending"),
        ("sent", "Sent"),
        ("failed", "Failed"),
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="pending",
    )

    sent_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    metadata = models.JSONField(
        default=dict,
        blank=True,
    )

    title = models.CharField(max_length=255)
    message = models.TextField()

    is_read = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user} - {self.title}"
