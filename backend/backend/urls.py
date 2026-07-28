"""
URL configuration for backend project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.views import TokenRefreshView
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
)
from inbox.views.dashboard import InboxDashboardAPIView




urlpatterns = [
    path('admin/', admin.site.urls),

    path('api/inbox/', include('inbox.urls')),
    path("api/dashboard/",InboxDashboardAPIView.as_view(),),
    path('api/email/', include('email_accounts.urls')),
    path('api/audit/', include('audit_logs.urls')),
    path('api/auth/', include('accounts.urls')),
    path("api/conversations/", include("conversations.urls")),
    path("api/google/oauth/", include("googleapis.urls")),
    path("api/oauth/", include("oauth_tokens.urls")),
    path("api/microsoft/oauth/", include("microsoftapis.urls")),
    path("api/notifications/", include("notifications.urls")),
    path("api/search/", include("search.urls")),
    path("api/ai/", include("ai.urls")),
    path("api/", include("email_accounts.urls")),
    path("api/actions/",include("actions.urls")),
    path("api/approvals/", include("approvals.urls")),
    path("api/timeline/", include("timeline.urls")),
    path("api/knowledge/",include("knowledge.urls"),),
    path("api/context/",include("context.urls"),),
    path("api/platform/",include("platform_core.urls"),),
        
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT
    )


urlpatterns += [
    path("api/auth/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/auth/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
]

urlpatterns += [
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
]

urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

