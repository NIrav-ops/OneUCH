from django.urls import path

from .views import (
    LoginAPIView,
    MeAPIView,
    SignupAPIView,
    StaffSignupRegistryAPIView,
)


urlpatterns = [
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
