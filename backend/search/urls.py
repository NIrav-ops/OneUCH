from django.urls import path
from .views import UnifiedSearchAPIView

urlpatterns = [
    path("", UnifiedSearchAPIView.as_view(), name="unified-search"),
]