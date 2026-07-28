from django.contrib import admin

from .models import (
    BusinessObjectType,
    BusinessObject,
    BusinessObjectLink,
    BusinessObjectDomain,
    BusinessObjectContact,
    BusinessObjectAlias,
    BusinessObjectIdentifier,
    BusinessObjectTag,
    BusinessRelationship,
)


admin.site.register(BusinessObjectType)

# ============================================================
# Enterprise Business Object Admin
# ============================================================

@admin.register(BusinessObject)
class BusinessObjectAdmin(admin.ModelAdmin):

    list_display = (

        "id",

        "name",

        "object_type",

        "organization",

        "status",

        "priority",

    )

    search_fields = (

        "name",

        "code",

        "description",

    )

    list_filter = (

        "object_type",

        "status",

        "organization",

    )

    ordering = (

        "name",

    )

admin.site.register(BusinessObjectLink)

admin.site.register(BusinessObjectDomain)

admin.site.register(BusinessObjectContact)

admin.site.register(BusinessObjectAlias)

admin.site.register(BusinessObjectIdentifier)

admin.site.register(BusinessObjectTag)

# ============================================================
# Enterprise Business Relationship Admin
# Commit 7.1
# ============================================================

@admin.register(BusinessRelationship)
class BusinessRelationshipAdmin(admin.ModelAdmin):

    @admin.display(description="Relationship")

    def relationship(self, obj):

        return (
            f"{obj.source_object.name}"
            " → "
            f"{obj.target_object.name}"
        )


    @admin.display(description="Strength")

    def strength(self, obj):

        if obj.confidence >= 90:
            return "★★★★★"

        if obj.confidence >= 75:
            return "★★★★"

        if obj.confidence >= 50:
            return "★★★"

        if obj.confidence >= 25:
            return "★★"

        return "★"

    list_display = (

        "id",

        "relationship",

        "relationship_type",

        "strength",

        "confidence",

        "evidence_count",

        "source",

        "last_verified",

    )

    list_filter = (

        "relationship_type",

        "direction",

        "source",

    )

    search_fields = (

        "source_object__name",

        "target_object__name",

        "relationship_type",

    )

    ordering = (

        "-confidence",

        "-updated_at",

    )

    readonly_fields = (

        "created_at",

        "updated_at",

        "last_verified",

    )

    autocomplete_fields = (

        "source_object",

        "target_object",

    )

    fieldsets = (

        (

            "Relationship",

            {

                "fields": (

                    "source_object",

                    "relationship_type",

                    "target_object",

                    "direction",

                )

            },

        ),

        (

            "Confidence",

            {

                "fields": (

                    "confidence",

                    "evidence_count",

                    "source",

                )

            },

        ),

        (

            "Metadata",

            {

                "fields": (

                    "metadata",

                )

            },

        ),

        (

            "Audit",

            {

                "fields": (

                    "created_at",

                    "updated_at",

                    "last_verified",

                )

            },

        ),

    )