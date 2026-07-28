from django.urls import path
from oauth_tokens.admin_views import (
    AdminDisableOAuthAPIView,
    AdminEnableOAuthAPIView,
)

urlpatterns = [
    path("admin/disable/<int:token_id>/", AdminDisableOAuthAPIView.as_view()),
    path("admin/enable/<int:token_id>/", AdminEnableOAuthAPIView.as_view()),
]
