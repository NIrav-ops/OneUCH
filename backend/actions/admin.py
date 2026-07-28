from django.contrib import admin
from .models import ActionItem, FollowUpItem

# Register your models here.

admin.site.register(ActionItem)
admin.site.register(FollowUpItem)