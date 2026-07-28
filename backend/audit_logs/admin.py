from django.contrib import admin
from .models import AuditLog

# Register your models here.

@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = (
        'created_at',
        'user',
        'action',
        'platform',
    )
    list_filter = ('action', 'platform')
    search_fields = ('description',)
    readonly_fields = (
        'user',
        'action',
        'platform',
        'description',
        'metadata',
        'created_at',
    )

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
