from django.contrib import admin

from .models import (
    BusinessIdentity,
    KnowledgeEvidence,
    KnowledgeFact,
    KnowledgeJob,
)


# ============================================================
# Business Identity
# ============================================================

@admin.register(BusinessIdentity)
class BusinessIdentityAdmin(admin.ModelAdmin):

    list_display = (
        "business_object",
        "identity_type",
        "value",
        "source",
        "lifecycle",
        "confidence_score",
        "trust_score",
        "is_primary",
    )

    search_fields = (
        "value",
        "normalized_value",
        "business_object__name",
    )

    list_filter = (
        "identity_type",
        "source",
        "lifecycle",
        "is_primary",
    )

    ordering = (
        "business_object",
        "identity_type",
    )


# ============================================================
# Knowledge Evidence
# ============================================================

@admin.register(KnowledgeEvidence)
class KnowledgeEvidenceAdmin(admin.ModelAdmin):

    list_display = (
        "title",
        "organization",
        "business_object",
        "evidence_type",
        "confidence",
        "is_active",
        "created_at",
    )

    search_fields = (
        "title",
        "summary",
        "resolver_reason",
        "business_object__name",
    )

    list_filter = (
        "evidence_type",
        "is_active",
        "organization",
        "created_at",
    )

    raw_id_fields = (
        "organization",
        "business_object",
        "conversation",
        "message",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
    )

    ordering = (
        "-created_at",
    )


# ============================================================
# Knowledge Facts
# ============================================================

@admin.register(KnowledgeFact)
class KnowledgeFactAdmin(admin.ModelAdmin):

    list_display = (
        "fact_key",
        "business_object",
        "organization",
        "confidence",
        "status",
        "updated_at",
    )

    search_fields = (
        "fact_key",
        "fact_value",
        "business_object__name",
    )

    list_filter = (
        "status",
        "organization",
    )

    raw_id_fields = (
        "organization",
        "business_object",
        "primary_evidence",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
    )

    ordering = (
        "fact_key",
    )

@admin.register(KnowledgeJob)
class KnowledgeJobAdmin(admin.ModelAdmin):

    list_display = (

        "id",
        "job_type",
        "status",
        "processed",
        "skipped",
        "failed",
        "duration_seconds",
        "started_at",
        "completed_at",

    )

    list_filter = (

        "job_type",
        "status",

    )

    search_fields = (

        "id",

    )

    readonly_fields = (

        "started_at",
        "completed_at",

    )