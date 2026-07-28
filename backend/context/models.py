from django.db import models

from inbox.models import Organization

class BusinessObjectType(models.Model):

    name = models.CharField(
        max_length=100,
        unique=True,
    )

    code = models.CharField(
        max_length=50,
        unique=True,
    )

    icon = models.CharField(
        max_length=50,
        blank=True,
    )

    color = models.CharField(
        max_length=20,
        default="#2563EB",
    )

    is_system = models.BooleanField(
        default=False,
    )

    is_active = models.BooleanField(
        default=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class BusinessObject(models.Model):

    organization = models.ForeignKey(
        "inbox.Organization",
        on_delete=models.CASCADE,
        related_name="business_objects",
    )

    object_type = models.ForeignKey(
        BusinessObjectType,
        on_delete=models.PROTECT,
        related_name="business_objects",
    )

    name = models.CharField(
        max_length=255,
    )

    code = models.CharField(
        max_length=100,
        blank=True,
    )

    description = models.TextField(
        blank=True,
    )

    owner = models.ForeignKey(
        "accounts.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="owned_business_objects",
    )

    status = models.CharField(
        max_length=50,
        default="active",
    )

    priority = models.IntegerField(
        default=50,
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

    def save(self, *args, **kwargs):

        super().save(*args, **kwargs)

        from context.services.business_object_cache import (
            BusinessObjectCache,
        )

        BusinessObjectCache.invalidate(
            self.organization,
        )

    def delete(self, *args, **kwargs):

        organization = self.organization

        super().delete(*args, **kwargs)

        from context.services.business_object_cache import (
            BusinessObjectCache,
        )

        BusinessObjectCache.invalidate(
            organization,
        )    

    class Meta:
        ordering = ["name"]
        indexes = [
            models.Index(fields=["organization"]),
            models.Index(fields=["name"]),
            models.Index(fields=["status"]),
        ]

    def __str__(self):
        return self.name


class BusinessObjectLink(models.Model):

    business_object = models.ForeignKey(
        BusinessObject,
        on_delete=models.CASCADE,
        related_name="links",
    )

    content_type = models.CharField(
        max_length=100,
    )

    object_id = models.PositiveIntegerField()

    relationship = models.CharField(
        max_length=50,
        default="related",
    )

    metadata = models.JSONField(
        default=dict,
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        indexes = [
            models.Index(fields=["content_type"]),
            models.Index(fields=["object_id"]),
        ]

    def __str__(self):
        return (
            f"{self.business_object} -> "
            f"{self.content_type}:{self.object_id}"
        )
# ============================================================
# Enterprise Identity Models
# ============================================================

class BusinessObjectDomain(models.Model):

    business_object = models.ForeignKey(
        BusinessObject,
        on_delete=models.CASCADE,
        related_name="domains",
    )

    domain = models.CharField(
        max_length=255,
    )

    is_primary = models.BooleanField(
        default=False,
    )

    is_verified = models.BooleanField(
        default=False,
    )

    source = models.CharField(
        max_length=50,
        default="manual",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = ["domain"]
        unique_together = [
            ("business_object", "domain")
        ]

    def __str__(self):
        return f"{self.business_object.name} - {self.domain}"


# ------------------------------------------------------------


class BusinessObjectContact(models.Model):

    business_object = models.ForeignKey(
        BusinessObject,
        on_delete=models.CASCADE,
        related_name="contacts",
    )

    name = models.CharField(
        max_length=255,
    )

    email = models.EmailField()

    designation = models.CharField(
        max_length=255,
        blank=True,
    )

    department = models.CharField(
        max_length=255,
        blank=True,
    )

    phone = models.CharField(
        max_length=50,
        blank=True,
    )

    is_primary = models.BooleanField(
        default=False,
    )

    is_verified = models.BooleanField(
        default=False,
    )

    source = models.CharField(
        max_length=50,
        default="manual",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = ["name"]
        unique_together = [
            ("business_object", "email")
        ]

    def __str__(self):
        return f"{self.name} ({self.email})"


# ------------------------------------------------------------


class BusinessObjectAlias(models.Model):

    business_object = models.ForeignKey(
        BusinessObject,
        on_delete=models.CASCADE,
        related_name="aliases",
    )

    alias = models.CharField(
        max_length=255,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = ["alias"]
        unique_together = [
            ("business_object", "alias")
        ]

    def __str__(self):
        return self.alias


# ------------------------------------------------------------


class BusinessObjectIdentifier(models.Model):

    IDENTIFIER_TYPES = (

        ("customer_id", "Customer ID"),

        ("vendor_id", "Vendor ID"),

        ("contract_id", "Contract ID"),

        ("crm_id", "CRM ID"),

        ("erp_id", "ERP ID"),

        ("gst", "GST"),

        ("pan", "PAN"),

        ("other", "Other"),

    )

    business_object = models.ForeignKey(
        BusinessObject,
        on_delete=models.CASCADE,
        related_name="identifiers",
    )

    identifier_type = models.CharField(
        max_length=50,
        choices=IDENTIFIER_TYPES,
    )

    value = models.CharField(
        max_length=255,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        unique_together = [
            (
                "business_object",
                "identifier_type",
                "value",
            )
        ]

    def __str__(self):
        return f"{self.identifier_type}: {self.value}"


# ------------------------------------------------------------


class BusinessObjectTag(models.Model):

    business_object = models.ForeignKey(
        BusinessObject,
        on_delete=models.CASCADE,
        related_name="tags",
    )

    name = models.CharField(
        max_length=100,
    )

    color = models.CharField(
        max_length=20,
        default="#2563EB",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = ["name"]
        unique_together = [
            ("business_object", "name")
        ]

    def __str__(self):
        return self.name    

# ============================================================
# Enterprise Business Relationship
# Commit 7.1
# ============================================================

class BusinessRelationship(models.Model):

    RELATIONSHIP_TYPES = (

        ("RELATED_TO", "Related To"),

        ("WORKS_FOR", "Works For"),

        ("EMPLOYED_BY", "Employed By"),

        ("CUSTOMER_OF", "Customer Of"),

        ("VENDOR_OF", "Vendor Of"),

        ("PARTNER_OF", "Partner Of"),

        ("OWNS", "Owns"),

        ("MANAGES", "Manages"),

        ("REPORTS_TO", "Reports To"),

        ("MEMBER_OF", "Member Of"),

        ("SUPPLIER_OF", "Supplier Of"),

        ("PARENT_OF", "Parent Of"),

        ("CHILD_OF", "Child Of"),

        ("CONTRACT_WITH", "Contract With"),

        ("PROJECT_FOR", "Project For"),

        ("ATTENDED", "Attended"),

        ("APPROVED_BY", "Approved By"),

        ("ASSIGNED_TO", "Assigned To"),

    )

    DIRECTION = (

        ("OUTGOING", "Outgoing"),

        ("INCOMING", "Incoming"),

        ("BIDIRECTIONAL", "Bidirectional"),

    )

    source_object = models.ForeignKey(
        BusinessObject,
        related_name="outgoing_relationships",
        on_delete=models.CASCADE,
    )

    target_object = models.ForeignKey(
        BusinessObject,
        related_name="incoming_relationships",
        on_delete=models.CASCADE,
    )

    relationship_type = models.CharField(
        max_length=50,
        choices=RELATIONSHIP_TYPES,
        default="RELATED_TO",
    )

    direction = models.CharField(
        max_length=20,
        choices=DIRECTION,
        default="BIDIRECTIONAL",
    )

    confidence = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=100,
    )

    evidence_count = models.PositiveIntegerField(
        default=1,
    )

    source = models.CharField(
        max_length=50,
        default="resolver",
    )

    metadata = models.JSONField(
        default=dict,
        blank=True,
    )

    last_verified = models.DateTimeField(
        null=True,
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

            "-confidence",

            "-updated_at",

        ]

        indexes = [

            models.Index(
                fields=[
                    "relationship_type",
                ]
            ),

            models.Index(
                fields=[
                    "source_object",
                ]
            ),

            models.Index(
                fields=[
                    "target_object",
                ]
            ),

            models.Index(
                fields=[
                    "confidence",
                ]
            ),

            models.Index(
                fields=[
                    "direction",
                ]
            ),

        ]

        constraints = [

            models.UniqueConstraint(

                fields=[

                    "source_object",

                    "target_object",

                    "relationship_type",

                ],

                name="unique_business_relationship",

            )

        ]

    def __str__(self):

        return (

            f"{self.source_object}"

            f" -> "

            f"{self.relationship_type}"

            f" -> "

            f"{self.target_object}"

        )

class Person(models.Model):
    """
    Enterprise Person Entity.

    Represents any human known to the organization.

    Future:
    - Employee
    - Customer
    - Vendor
    - Partner
    - Contact
    """

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="people",
    )

    email = models.EmailField(
        db_index=True,
    )

    full_name = models.CharField(
        max_length=255,
        blank=True,
    )

    job_title = models.CharField(
        max_length=255,
        blank=True,
    )

    company = models.CharField(
        max_length=255,
        blank=True,
    )

    is_internal = models.BooleanField(
        default=False,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:

        unique_together = (
            "organization",
            "email",
        )

    def __str__(self):
        return self.full_name or self.email