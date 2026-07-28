from django.contrib import admin
from .models import EmailAccount

# Register your models here.

@admin.register(EmailAccount)
class EmailAccountAdmin(admin.ModelAdmin):
    list_display = (
        'email_address',
        'account_type',
        'credential_status',
        'credential_expires_at',
        'last_verified_at',
        'is_active'
    )

    list_filter = (
        'account_type',
        'credential_status',
        'is_active',
    )

    search_fields = (
        'email_address',
    )