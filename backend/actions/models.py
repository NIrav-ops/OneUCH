from django.db import models
from django.conf import settings
from inbox.models import InboxMessage, Organization


class ActionItem(models.Model):
    STATUS_CHOICES = (
        ("open", "Open"),
        ("in_progress", "In Progress"),
        ("waiting", "Waiting"),
        ("blocked", "Blocked"),
        ("completed", "Completed"),
        ("cancelled", "Cancelled"),
        ("ignored", "Ignored"),
    )

    SOURCE_TYPES = (
        ("email", "Email"),
        ("workflow", "Workflow"),
        ("approval", "Approval"),
        ("manual", "Manual"),
        ("api", "API"),
        ("ai", "AI"),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="action_items",
        null=True,
        blank=True,
    )

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="action_items",
    )

    message = models.ForeignKey(
        InboxMessage,
        on_delete=models.CASCADE,
        related_name="actions",
        null=True,
        blank=True,
    )

    title = models.CharField(max_length=500)
    description = models.TextField(blank=True)

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="assigned_actions",
    )

    due_date = models.DateTimeField(null=True, blank=True)
    priority = models.IntegerField(default=0)

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="open",
    )

    source_type = models.CharField(
        max_length=30,
        choices=SOURCE_TYPES,
        default="email",
        db_index=True,
    )

    last_reminder_sent_at = models.DateTimeField(
        null=True,
        blank=True
    )

    confidence_score = models.IntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True,blank=True,)

    source_approval = models.ForeignKey(
        "approvals.ApprovalItem",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="generated_actions",
    )

    workflow_instance = models.ForeignKey(
        "workflow.WorkflowInstance",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="generated_actions",
    )

    escalation_level = models.IntegerField(
    default=0
    )

    def __str__(self):
        return self.title
    
class FollowUpItem(models.Model):
    STATUS_CHOICES = (
        ("pending", "Pending"),
        ("completed", "Completed"),
        ("ignored", "Ignored"),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="followup_items",
    )

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="followup_items",
    )

    conversation = models.ForeignKey(
        "inbox.Conversation",
        on_delete=models.CASCADE,
        related_name="followups",
    )

    last_message = models.ForeignKey(
        InboxMessage,
        on_delete=models.CASCADE,
        related_name="followup_items",
    )

    followup_due_at = models.DateTimeField()

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="pending",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    last_reminder_sent_at = models.DateTimeField(
        null=True,
        blank=True
    )

    escalation_level = models.IntegerField(
        default=0
    )

    def __str__(self):
        return f"Follow-up for conversation {self.conversation_id}"