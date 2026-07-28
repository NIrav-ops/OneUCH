from django.contrib import admin

from .models import (
    WorkflowDefinition,
    WorkflowNode,
    WorkflowTransition,
    WorkflowVariable,
    WorkflowInstance,
    WorkflowToken,
    WorkflowExecutionLog,
)

class WorkflowVariableInline(admin.TabularInline):
    model = WorkflowVariable
    extra = 0

    fields = (
        "name",
        "data_type",
        "required",
        "default_value",
    )

class WorkflowNodeInline(admin.TabularInline):
    model = WorkflowNode
    extra = 0

    fields = (
        "name",
        "node_type",
        "position_x",
        "position_y",
    )

    show_change_link = True

@admin.register(WorkflowDefinition)
class WorkflowDefinitionAdmin(admin.ModelAdmin):

    list_display = (
        "name",
        "organization",
        "version",
        "status",
        "created_at",
    )

    list_filter = (
        "status",
        "organization",
    )

    search_fields = (
        "name",
        "code",
    )

    readonly_fields = (
        "id",
        "created_at",
        "updated_at",
    )

    ordering = (
        "organization",
        "name",
        "-version",
    )

    inlines = [
        WorkflowVariableInline,
        WorkflowNodeInline,
    ]

@admin.register(WorkflowNode)
class WorkflowNodeAdmin(admin.ModelAdmin):

    list_display = (
        "name",
        "workflow",
        "node_type",
    )

    list_filter = (
        "node_type",
        "workflow",
    )

    search_fields = (
        "name",
        "workflow__name",
    )

    readonly_fields = (
        "id",
        "created_at",
    )

@admin.register(WorkflowTransition)
class WorkflowTransitionAdmin(admin.ModelAdmin):

    list_display = (
        "workflow",
        "source",
        "target",
        "condition",
    )

    list_filter = (
        "workflow",
    )

    search_fields = (
        "workflow__name",
        "source__name",
        "target__name",
    )

    readonly_fields = (
        "id",
        "created_at",
    )

@admin.register(WorkflowVariable)
class WorkflowVariableAdmin(admin.ModelAdmin):

    list_display = (
        "workflow",
        "name",
        "data_type",
        "required",
    )

    list_filter = (
        "data_type",
    )

    search_fields = (
        "workflow__name",
        "name",
    )

    readonly_fields = (
        "id",
    )
@admin.register(WorkflowInstance)
class WorkflowInstanceAdmin(admin.ModelAdmin):

    list_display = (
        "workflow",
        "status",
        "started_by",
        "started_at",
    )

    list_filter = (
        "status",
    )

    readonly_fields = (
        "started_at",
        "completed_at",
    )

@admin.register(WorkflowToken)
class WorkflowTokenAdmin(admin.ModelAdmin):

    list_display = (
        "instance",
        "node",
        "status",
    )

    list_filter = (
        "status",
    )

    readonly_fields = (
        "entered_at",
        "completed_at",
    )

@admin.register(WorkflowExecutionLog)
class WorkflowExecutionLogAdmin(admin.ModelAdmin):

    list_display = (
        "instance",
        "event",
        "created_at",
    )

    readonly_fields = (
        "created_at",
    )