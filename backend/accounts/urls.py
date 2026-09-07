from django.urls import path

from .identity_views import (
    IdentityCallbackAPIView,
    IdentityExchangeAPIView,
    IdentityProvidersAPIView,
    IdentityStartAPIView,
)

from .views import (
    LoginAPIView,
    MeAPIView,
    SignupAPIView,
    StaffSignupRegistryAPIView,
)


urlpatterns = [
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
