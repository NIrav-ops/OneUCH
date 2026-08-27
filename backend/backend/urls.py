"""
URL configuration for backend project.

The `urlpatterns` list routes URLs to views.
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
)

from inbox.views.dashboard import (
    InboxDashboardAPIView,
)

from rest_framework.permissions import (
    AllowAny,
    IsAdminUser,
)

api_documentation_permissions = (
    [AllowAny]
    if settings.DEBUG
    else [IsAdminUser]
)

urlpatterns = [
    path(
        "admin/",
        admin.site.urls,
    ),

    # Inbox
    path(
        "api/inbox/",
        include("inbox.urls"),
    ),

    path(
        "api/dashboard/",
        InboxDashboardAPIView.as_view(),
    ),

    # Email / accounts / communication
    path(
        "api/email/",
        include("email_accounts.urls"),
    ),

    path(
        "api/audit/",
        include("audit_logs.urls"),
    ),

    path(
        "api/auth/",
        include("accounts.urls"),
    ),

    path(
        "api/conversations/",
        include("conversations.urls"),
    ),

    # OAuth / integrations
    path(
        "api/google/oauth/",
        include("googleapis.urls"),
    ),

    path(
        "api/oauth/",
        include("oauth_tokens.urls"),
    ),

    path(
        "api/microsoft/oauth/",
        include("microsoftapis.urls"),
    ),

    # Platform services
    path(
        "api/notifications/",
        include("notifications.urls"),
    ),

    path(
        "api/search/",
        include("search.urls"),
    ),

    path(
        "api/ai/",
        include("ai.urls"),
    ),

    path(
        "api/",
        include("email_accounts.urls"),
    ),

    # Operational intelligence
    path(
        "api/actions/",
        include("actions.urls"),
    ),

    path(
        "api/approvals/",
        include("approvals.urls"),
    ),

    path(
        "api/timeline/",
        include("timeline.urls"),
    ),

    # Knowledge / business context
    path(
        "api/knowledge/",
        include("knowledge.urls"),
    ),

    path(
        "api/context/",
        include("context.urls"),
    ),

    path(
        "api/platform/",
        include("platform_core.urls"),
    ),

    # Workflow & execution engine
    path(
        "api/workflow/",
        include("workflow.urls"),
    ),
]


# Media files in development
urlpatterns += static(
    settings.MEDIA_URL,
    document_root=settings.MEDIA_ROOT,
)

if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT,
    )


# JWT authentication
urlpatterns += [
    path(
        "api/auth/token/",
        TokenObtainPairView.as_view(),
        name="token_obtain_pair",
    ),

    path(
        "api/auth/token/refresh/",
        TokenRefreshView.as_view(),
        name="token_refresh",
    ),
]


# OpenAPI / Swagger
urlpatterns += [
    path(
        "api/schema/",
        SpectacularAPIView.as_view(
            permission_classes=api_documentation_permissions,
        ),
        name="schema",
    ),

    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(
            url_name="schema",
            permission_classes=api_documentation_permissions,
        ),
        name="swagger-ui",
    ),
]


# Static files
urlpatterns += static(
    settings.STATIC_URL,
    document_root=settings.STATIC_ROOT,
)