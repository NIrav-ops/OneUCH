from django.urls import path

from .identity_views import (
    IdentityCallbackAPIView,
    IdentityExchangeAPIView,
    IdentityProvidersAPIView,
    IdentityStartAPIView,
)

from .session_views import (
    BrowserSessionBootstrapAPIView,
    BrowserSessionCsrfAPIView,
    BrowserSessionIdentityExchangeAPIView,
    BrowserSessionLoginAPIView,
    BrowserSessionRefreshAPIView,
)

from .views import (
    LoginAPIView,
    MeAPIView,
    SignupAPIView,
    StaffSignupRegistryAPIView,
)


urlpatterns = [
    path(
        "session/csrf/",
        BrowserSessionCsrfAPIView.as_view(),
        name="browser-session-csrf",
    ),
    path(
        "session/login/",
        BrowserSessionLoginAPIView.as_view(),
        name="browser-session-login",
    ),
    path(
        "session/identity/exchange/",
        BrowserSessionIdentityExchangeAPIView.as_view(),
        name="browser-session-identity-exchange",
    ),
    path(
        "session/refresh/",
        BrowserSessionRefreshAPIView.as_view(),
        name="browser-session-refresh",
    ),
    path(
        "session/bootstrap/",
        BrowserSessionBootstrapAPIView.as_view(),
        name="browser-session-bootstrap",
    ),
    path(
        "identity/providers/",
        IdentityProvidersAPIView.as_view(),
        name="identity-providers",
    ),
    path(
        "identity/exchange/",
        IdentityExchangeAPIView.as_view(),
        name="identity-exchange",
    ),
    path(
        "identity/<str:provider>/start/",
        IdentityStartAPIView.as_view(),
        name="identity-start",
    ),
    path(
        "identity/<str:provider>/callback/",
        IdentityCallbackAPIView.as_view(),
        name="identity-callback",
    ),
    path(
        "signup/",
        SignupAPIView.as_view(),
        name="signup",
    ),
    path(
        "login/",
        LoginAPIView.as_view(),
        name="login",
    ),
    path(
        "me/",
        MeAPIView.as_view(),
        name="me",
    ),
    path(
        "platform/signup-registry/",
        StaffSignupRegistryAPIView.as_view(),
        name="signup-registry",
    ),
]
