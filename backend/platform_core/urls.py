from django.urls import path

from platform_core.views import (

    PlatformHealthAPIView,

    PlatformMetricsAPIView,

    PlatformConfigurationAPIView,

    PlatformJobsAPIView,

    PlatformSchedulerAPIView,

)

urlpatterns = [

    path(

        "health/",

        PlatformHealthAPIView.as_view(),

    ),

    path(

        "metrics/",

        PlatformMetricsAPIView.as_view(),

    ),

    path(

        "configuration/",

        PlatformConfigurationAPIView.as_view(),

    ),

    path(

        "jobs/",

        PlatformJobsAPIView.as_view(),

    ),

    path(

        "scheduler/",

        PlatformSchedulerAPIView.as_view(),

    ),

]