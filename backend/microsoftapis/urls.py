from django.urls import path
from microsoftapis.views import MicrosoftOAuthStart, MicrosoftOAuthCallback

urlpatterns = [
    path("start/", MicrosoftOAuthStart.as_view()),
    path("callback/", MicrosoftOAuthCallback.as_view()),
]

from .views import OutlookSyncAPIView

urlpatterns += [
    path("sync/", OutlookSyncAPIView.as_view()),
]