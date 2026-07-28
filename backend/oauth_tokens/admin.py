from django.contrib import admin
from .models import OAuthToken

# Register your models here.

@admin.register(OAuthToken)
class OAuthTokenAdmin(admin.ModelAdmin):
    list_display = ('user', 'provider', 'expires_at', 'is_active')
    list_filter = ('provider', 'is_active')

