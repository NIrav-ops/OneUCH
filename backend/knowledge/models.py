from django.db import models
from knowledge.services.identity_normalizer import IdentityNormalizer


class BusinessIdentity(models.Model):

    IDENTITY_TYPES = [

        ("DOMAIN", "Domain"),

        ("EMAIL", "Email"),

        ("PHONE", "Phone"),

        ("WEBSITE", "Website"),

        ("GST", "GST"),

        ("PAN", "PAN"),

        ("TAX", "Tax"),

        ("CRM", "CRM"),

        ("ERP", "ERP"),

        ("CUSTOMER_ID", "Customer ID"),

        ("VENDOR_ID", "Vendor ID"),

        ("EMPLOYEE_ID", "Employee ID"),

        ("ALIAS", "Alias"),

        ("CUSTOM", "Custom"),

    ]

    SOURCES = [

        ("manual", "Manual"),

        ("gmail", "Gmail"),

        ("outlook", "Outlook"),

        ("teams", "Teams"),

        ("slack", "Slack"),

        ("api", "API"),

        ("crm", "CRM"),

        ("erp", "ERP"),

        ("csv", "CSV"),

        ("ai", "AI"),

        ("discovery", "Discovery"),

    ]

    LIFECYCLE = [

        ("DISCOVERED", "Discovered"),

        ("SUGGESTED", "Suggested"),

        ("VERIFIED", "Verified"),

        ("TRUSTED", "Trusted"),

        ("ARCHIVED", "Archived"),

    ]

    business_object = models.ForeignKey(

        "context.BusinessObject",

        on_delete=models.CASCADE,

        related_name="identities",

    )

    identity_type = models.CharField(

        max_length=50,

        choices=IDENTITY_TYPES,

    )

    value = models.CharField(

        max_length=500,

    )

    normalized_value = models.CharField(

        max_length=500,

        db_index=True,

    )

    source = models.CharField(

        max_length=30,

        choices=SOURCES,

        default="manual",

    )

    lifecycle = models.CharField(

        max_length=20,

        choices=LIFECYCLE,

        default="DISCOVERED",

    )

    confidence_score = models.DecimalField(

        max_digits=5,

        decimal_places=2,

        default=100,

    )

    trust_score = models.DecimalField(

        max_digits=5,

        decimal_places=2,

        default=0,

    )

    is_primary = models.BooleanField(

        default=False,

    )

    metadata = models.JSONField(

        default=dict,

        blank=True,

    )

    created_at = models.DateTimeField(

        auto_now_add=True,

    )

    updated_at = models.DateTimeField(

        auto_now=True,

    )

    class Meta:

        ordering = [

            "business_object",

            "identity_type",

            "value",

        ]

        indexes = [

            models.Index(

                fields=[

                    "identity_type",

                    "normalized_value",

                ]

            ),

            models.Index(

                fields=[

                    "source",

                ]

            ),

            models.Index(

                fields=[

                    "lifecycle",

                ]

            ),

        ]

        constraints = [

            models.UniqueConstraint(

                fields=[

                    "business_object",

                    "identity_type",

                    "normalized_value",

                ],

                name="unique_business_identity",

            )

        ]

    def save(self, *args, **kwargs):

        self.normalized_value = IdentityNormalizer.normalize(

            self.identity_type,

            self.value,

        )
        super().save(*args, **kwargs)

    def __str__(self):

        return (

            f"{self.business_object.name}"

            f" - "

            f"{self.identity_type}"

            f": "

            f"{self.value}"

        )

# ============================================================
# Enterprise Knowledge Evidence
# ============================================================

class KnowledgeEvidence(models.Model):

    EVIDENCE_TYPES = [

        ("GENERAL", "General"),

        ("EMAIL", "Email"),

        ("MEETING", "Meeting"),

        ("TASK", "Task"),

        ("APPROVAL", "Approval"),

        ("PAYMENT", "Payment"),

        ("QUOTE", "Quotation"),

        ("CONTRACT", "Contract"),

        ("CUSTOMER", "Customer"),

        ("VENDOR", "Vendor"),

        ("LEGAL", "Legal"),

    ]


    organization = models.ForeignKey(
        "inbox.Organization",
        on_delete=models.CASCADE,
        related_name="knowledge_evidence",
    )


    business_object = models.ForeignKey(
        "context.BusinessObject",
        on_delete=models.SET_NULL,
        related_name="knowledge_evidence",
        null=True,
        blank=True,
    )

    person = models.ForeignKey(
        "context.Person",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="knowledge_evidence",
    )


    conversation = models.ForeignKey(
        "inbox.Conversation",
        on_delete=models.CASCADE,
        related_name="knowledge_evidence",
        null=True,
        blank=True,
    )


    message = models.ForeignKey(
        "inbox.InboxMessage",
        on_delete=models.CASCADE,
        related_name="knowledge_evidence",
    )


    evidence_type = models.CharField(
        max_length=50,
        choices=EVIDENCE_TYPES,
        default="GENERAL",
    )


    title = models.CharField(
        max_length=300,
    )


    summary = models.TextField(
        blank=True,
    )


    resolver_reason = models.TextField(
        blank=True,
    )

    source_channel = models.CharField(
        max_length=30,
        default="system",
    )

    resolver_version = models.CharField(
        max_length=20,
        default="1.0",
    )

    ai_provider = models.CharField(
        max_length=50,
        default="none",
    )

    evidence_hash = models.CharField(
        max_length=128,
        blank=True,
        db_index=True,
    )


    confidence = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=100,
    )


    metadata = models.JSONField(
        default=dict,
        blank=True,
    )


    is_active = models.BooleanField(
        default=True,
    )

    is_verified = models.BooleanField(
        default=False,
    )

    is_archived = models.BooleanField(
        default=False,
    )


    created_at = models.DateTimeField(
        auto_now_add=True,
    )


    updated_at = models.DateTimeField(
        auto_now=True,
    )


    class Meta:

        ordering = [
            "-created_at",
        ]

        indexes = [

            models.Index(
                fields=[
                    "organization",
                    "evidence_type",
                ]
            ),

            models.Index(
                fields=[
                    "business_object",
                    "evidence_type",
                ]
            ),

            models.Index(
                fields=[
                    "source_channel",
                ]
            ),

            models.Index(
                fields=[
                    "evidence_hash",
                ]
            ),

            models.Index(
                fields=[
                    "created_at",
                ]
            ),

            models.Index(
                fields=[
                    "is_active",
                    "is_archived",
                ]
            ),

            models.Index(
                fields=[
                    "conversation",
                ]
            ),

            models.Index(
                fields=[
                    "message",
                ]
            ),
        ]


    def __str__(self):

        return f"{self.evidence_type} : {self.title}"
    
# ============================================================
# Enterprise Knowledge Facts
# ============================================================

class KnowledgeFact(models.Model):

    FACT_STATUS = [

        ("ACTIVE", "Active"),

        ("INACTIVE", "Inactive"),

        ("SUPERSEDED", "Superseded"),

    ]


    organization = models.ForeignKey(
        "inbox.Organization",
        on_delete=models.CASCADE,
        related_name="knowledge_facts",
    )


    business_object = models.ForeignKey(
        "context.BusinessObject",
        on_delete=models.CASCADE,
        related_name="knowledge_facts",
    )


    primary_evidence = models.ForeignKey(
        KnowledgeEvidence,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="facts",
    )


    fact_key = models.CharField(
        max_length=150,
    )


    fact_value = models.TextField()

    fact_type = models.CharField(
        max_length=50,
        default="GENERAL",
    )

    source_channel = models.CharField(
        max_length=30,
        default="system",
    )


    confidence = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=100,
    )


    status = models.CharField(
        max_length=20,
        choices=FACT_STATUS,
        default="ACTIVE",
    )

    is_verified = models.BooleanField(
        default=False,
    )

    last_verified_at = models.DateTimeField(
        null=True,
        blank=True,
    )


    metadata = models.JSONField(
        default=dict,
        blank=True,
    )


    created_at = models.DateTimeField(
        auto_now_add=True,
    )


    updated_at = models.DateTimeField(
        auto_now=True,
    )


    class Meta:

        ordering = [
            "fact_key",
        ]

        indexes = [

            models.Index(
                fields=[
                    "organization",
                ]
            ),

            models.Index(
                fields=[
                    "business_object",
                ]
            ),

            models.Index(
                fields=[
                    "fact_key",
                ]
            ),

            models.Index(
                fields=[
                    "fact_type",
                ]
            ),

            models.Index(
                fields=[
                    "source_channel",
                ]
            ),

            models.Index(
                fields=[
                    "status",
                ]
            ),
        ]

        constraints = [

            models.UniqueConstraint(
                fields=[
                    "business_object",
                    "fact_key",
                ],
                name="unique_business_fact",
            )
        ]


    def __str__(self):

        return f"{self.business_object} : {self.fact_key}"

# ============================================================
# Enterprise Processing Job
# ============================================================

class KnowledgeJob(models.Model):

    JOB_TYPES = [

        ("BACKFILL", "Knowledge Backfill"),
        ("REINDEX", "Knowledge Reindex"),
        ("IMPORT", "Knowledge Import"),
        ("SYNC", "Knowledge Sync"),
    ]

    STATUS = [

        ("RUNNING", "Running"),
        ("COMPLETED", "Completed"),
        ("FAILED", "Failed"),
    ]

    organization = models.ForeignKey(
        "inbox.Organization",
        on_delete=models.CASCADE,
        related_name="knowledge_jobs",
        null=True,
        blank=True,
    )

    user = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    job_type = models.CharField(
        max_length=30,
        choices=JOB_TYPES,
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS,
        default="RUNNING",
    )

    processed = models.PositiveIntegerField(
        default=0,
    )

    skipped = models.PositiveIntegerField(
        default=0,
    )

    failed = models.PositiveIntegerField(
        default=0,
    )

    duration_seconds = models.FloatField(
        default=0,
    )

    metadata = models.JSONField(
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

        indexes = [

            models.Index(
                fields=[
                    "job_type",
                ]
            ),

            models.Index(
                fields=[
                    "status",
                ]
            ),

            models.Index(
                fields=[
                    "started_at",
                ]
            ),
        ]

    def __str__(self):

        return (
            f"{self.job_type} "
            f"({self.status}) "
            f"#{self.pk}"
        )