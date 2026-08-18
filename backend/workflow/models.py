import uuid

from django.conf import settings
from django.db import models

from inbox.models import Organization


class WorkflowDefinition(models.Model):

    STATUS_DRAFT = "draft"
    STATUS_ACTIVE = "active"
    STATUS_DISABLED = "disabled"
    STATUS_ARCHIVED = "archived"

    STATUS_CHOICES = [
        (STATUS_DRAFT, "Draft"),
        (STATUS_ACTIVE, "Active"),
        (STATUS_DISABLED, "Disabled"),
        (STATUS_ARCHIVED, "Archived"),
    ]

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="workflow_definitions",
    )

    name = models.CharField(max_length=255)

    code = models.CharField(max_length=100)

    description = models.TextField(blank=True)

    version = models.PositiveIntegerField(default=1)

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_DRAFT,
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="created_workflows",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name", "version"]

        unique_together = [
            ("organization", "code", "version"),
        ]

    def __str__(self):
        return f"{self.name} v{self.version}"
    
class WorkflowNode(models.Model):

    START = "start"
    END = "end"
    ACTION = "action"
    APPROVAL = "approval"
    AI = "ai"
    CONDITION = "condition"
    WAIT = "wait"
    NOTIFICATION = "notification"
    WEBHOOK = "webhook"
    SCRIPT = "script"
    SUBWORKFLOW = "subworkflow"
    FORK = "fork"
    JOIN = "join"

    NODE_TYPES = [
        (START, "Start"),
        (END, "End"),
        (ACTION, "Action"),
        (APPROVAL, "Approval"),
        (AI, "AI"),
        (CONDITION, "Condition"),
        (WAIT, "Wait"),
        (NOTIFICATION, "Notification"),
        (WEBHOOK, "Webhook"),
        (SCRIPT, "Script"),
        (SUBWORKFLOW, "Sub Workflow"),
        (FORK, "Fork"),
        (JOIN, "Join"),
    ]

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    workflow = models.ForeignKey(
        WorkflowDefinition,
        on_delete=models.CASCADE,
        related_name="nodes",
    )

    name = models.CharField(max_length=255)

    node_type = models.CharField(
        max_length=30,
        choices=NODE_TYPES,
    )

    configuration = models.JSONField(
        default=dict,
        blank=True,
    )

    position_x = models.IntegerField(default=0)

    position_y = models.IntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.workflow.name} : {self.name}"
    
class WorkflowTransition(models.Model):

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    workflow = models.ForeignKey(
        WorkflowDefinition,
        on_delete=models.CASCADE,
        related_name="transitions",
    )

    source = models.ForeignKey(
        WorkflowNode,
        on_delete=models.CASCADE,
        related_name="outgoing",
    )

    target = models.ForeignKey(
        WorkflowNode,
        on_delete=models.CASCADE,
        related_name="incoming",
    )

    condition = models.CharField(
        max_length=255,
        blank=True,
    )

    priority = models.PositiveIntegerField(
        default=100,
        help_text="Lower numbers are evaluated first.",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = [
            "priority",
            "id",
        ]

    def __str__(self):
        return f"{self.source.name} → {self.target.name}"
    
class WorkflowVariable(models.Model):

    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    JSON = "json"

    VARIABLE_TYPES = [
        (STRING, "String"),
        (INTEGER, "Integer"),
        (FLOAT, "Float"),
        (BOOLEAN, "Boolean"),
        (JSON, "JSON"),
    ]

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    workflow = models.ForeignKey(
        WorkflowDefinition,
        on_delete=models.CASCADE,
        related_name="variables",
    )

    name = models.CharField(max_length=100)

    data_type = models.CharField(
        max_length=20,
        choices=VARIABLE_TYPES,
        default=STRING,
    )

    default_value = models.JSONField(
        null=True,
        blank=True,
    )

    required = models.BooleanField(default=False)

    class Meta:
        unique_together = [
            ("workflow", "name"),
        ]

    def __str__(self):
        return self.name

class WorkflowInstance(models.Model):

    STATUS_RUNNING = "running"
    STATUS_COMPLETED = "completed"
    STATUS_FAILED = "failed"
    STATUS_CANCELLED = "cancelled"

    STATUS_CHOICES = [
        (STATUS_RUNNING, "Running"),
        (STATUS_COMPLETED, "Completed"),
        (STATUS_FAILED, "Failed"),
        (STATUS_CANCELLED, "Cancelled"),
    ]

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    workflow = models.ForeignKey(
        WorkflowDefinition,
        on_delete=models.PROTECT,
        related_name="instances",
    )

    parent_instance = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="child_instances",
    )

    parent_token = models.ForeignKey(
        "WorkflowToken",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="spawned_instances",
    )

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="workflow_instances",
    )

    started_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="started_workflows",
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_RUNNING,
    )

    context = models.JSONField(
        default=dict,
        blank=True,
    )

    started_at = models.DateTimeField(
        auto_now_add=True,
    )

    completed_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    class Meta:
        ordering = [
            "-started_at",
        ]

    def __str__(self):
        return f"{self.workflow.name} ({self.status})"

class WorkflowToken(models.Model):

    STATUS_ACTIVE = "active"
    STATUS_COMPLETED = "completed"
    STATUS_WAITING = "waiting"

    STATUS_CHOICES = [
        (STATUS_ACTIVE, "Active"),
        (STATUS_COMPLETED, "Completed"),
        (STATUS_WAITING, "Waiting"),
    ]

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    instance = models.ForeignKey(
        WorkflowInstance,
        on_delete=models.CASCADE,
        related_name="tokens",
    )

    node = models.ForeignKey(
        WorkflowNode,
        on_delete=models.CASCADE,
        related_name="runtime_tokens",
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_ACTIVE,
    )

    entered_at = models.DateTimeField(
        auto_now_add=True,
    )

    completed_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    wait_until = models.DateTimeField(
        null=True,
        blank=True,
    )

    wait_reason = models.CharField(
        max_length=50,
        blank=True,
        default="",
    )

    wait_configuration = models.JSONField(
        default=dict,
        blank=True,
    )

    class Meta:
        ordering = [
            "entered_at",
        ]

    def __str__(self):
        return f"{self.node.name} ({self.status})"

class WorkflowExecutionLog(models.Model):

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    instance = models.ForeignKey(
        WorkflowInstance,
        on_delete=models.CASCADE,
        related_name="execution_logs",
    )

    node = models.ForeignKey(
        WorkflowNode,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )

    event = models.CharField(
        max_length=100,
    )

    details = models.JSONField(
        default=dict,
        blank=True,
    )

    sequence_number = models.PositiveBigIntegerField(
        null=True,
        blank=True,
    )

    previous_event_hash = models.CharField(
        max_length=64,
        null=True,
        blank=True,
    )

    event_hash = models.CharField(
        max_length=64,
        null=True,
        blank=True,
        unique=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:

        ordering = [
            "sequence_number",
            "created_at",
            "id",
        ]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "instance",
                    "sequence_number",
                ],
                name=(
                    "unique_execution_event_sequence"
                ),
            ),
        ]

        indexes = [
            models.Index(
                fields=[
                    "instance",
                    "sequence_number",
                ],
                name=(
                    "workflow_exec_instance_seq_idx"
                ),
            ),
        ]

    def __str__(self):

        return self.event