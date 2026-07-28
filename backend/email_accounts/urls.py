from django.urls import path
from .views import EmailAccountListAPIView, SendEmailAPIView

urlpatterns = [
    path('send/', SendEmailAPIView.as_view(), name='send-email'),
    path("email-accounts/", EmailAccountListAPIView.as_view()),
]
