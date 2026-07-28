from django.db import models
from django.conf import settings


class ApprovalItem(models.Model):
    STATUS_CHOICES = (
        ("pending", "Pending"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
        ("needs_info", "Needs Info"),
        ("ignored", "Ignored"),
    )

    SOURCE_TYPES = (
        ("email", "Email"),
        ("workflow", "Workflow"),
        ("manual", "Manual"),
        ("api", "API"),
        ("ai", "AI"),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="approval_items",
        null=True,
        blank=True,
    )

    organization = models.ForeignKey(
        "inbox.Organization",
        on_delete=models.CASCADE,
        related_name="approval_items",
    )

    message = models.ForeignKey(
        "inbox.InboxMessage",
        on_delete=models.CASCADE,
        related_name="approvals",
        null=True,
        blank=True,
    )

    conversation = models.ForeignKey(
        "inbox.Conversation",
        on_delete=models.CASCADE,
        related_name="approvals",
        null=True,
        blank=True,
    )

    title = models.CharField(max_length=500)
    description = models.TextField(blank=True)

    requested_by = models.EmailField(blank=True, null=True)

    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="assigned_approvals",
    )

    status = models.CharField(
    max_length=20,
    choices=STATUS_CHOICES,
    default="pending",
    )

    source_type = models.CharField(
        max_length=30,
        choices=SOURCE_TYPES,
        default="email",
        db_index=True,
    )

    due_date = models.DateTimeField(null=True, blank=True)

    confidence_score = models.IntegerField(default=0)

    priority = models.IntegerField(default=0,)

    decision_notes = models.TextField(blank=True)

    workflow_instance = models.ForeignKey(
        "workflow.WorkflowInstance",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="created_approvals",
    )

    workflow_node = models.ForeignKey(
        "workflow.WorkflowNode",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="created_approvals",
    )

# NEW FIELDS
    decision_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="approval_decisions",
    )

    decision_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    last_reminder_sent_at = models.DateTimeField(
        null=True,
        blank=True
    )

    approval_analyzed = models.BooleanField(default=False)

    action_created = models.BooleanField(
        default=False
    )

    escalation_level = models.IntegerField(
        default=0
    )

    def __str__(self):
        return self.title