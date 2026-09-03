from django.urls import path
from .views import (
    ActionListAPIView,
    FollowUpListAPIView,
    TeamMemberListAPIView,
    UpdateActionAPIView,
    CompleteActionAPIView,
    IgnoreActionAPIView,
    ReopenActionAPIView,
    SnoozeFollowUpAPIView,
    StartActionAPIView,
    UpdateActionStatusAPIView,
    AssignActionAPIView,
)

from .review_views import (
    AIActionCandidateListAPIView,
    PromoteAIActionCandidateAPIView,
    RejectAIActionCandidateAPIView,
)

urlpatterns = [
    path("", ActionListAPIView.as_view(), name="action-list"),
    path("followups/", FollowUpListAPIView.as_view(), name="followup-list"),
    path("team-members/", TeamMemberListAPIView.as_view(), name="team-member-list"),
    path("<int:action_id>/update/", UpdateActionAPIView.as_view(), name="update-action"),
    path("<int:action_id>/complete/", CompleteActionAPIView.as_view(), name="complete-action"),
    path("<int:action_id>/ignore/", IgnoreActionAPIView.as_view(), name="ignore-action"),
    path("<int:action_id>/reopen/", ReopenActionAPIView.as_view(), name="reopen-action"),
    path("followups/<int:followup_id>/snooze/", SnoozeFollowUpAPIView.as_view(), name="snooze-followup"),
    path("<int:action_id>/start/",StartActionAPIView.as_view(),name="start-action",),
    path("<int:action_id>/status/",UpdateActionStatusAPIView.as_view(),name="action-status",),
    path("<int:action_id>/assign/",AssignActionAPIView.as_view(),name="assign-action",),
    path(
        "review-candidates/",
        AIActionCandidateListAPIView.as_view(),
        name="action-review-candidate-list",
    ),
    path(
        "review-candidates/<int:candidate_id>/promote/",
        PromoteAIActionCandidateAPIView.as_view(),
        name="action-review-candidate-promote",
    ),
    path(
        "review-candidates/<int:candidate_id>/reject/",
        RejectAIActionCandidateAPIView.as_view(),
        name="action-review-candidate-reject",
    ),

    # Backwards-compatible PR3B AI aliases.
    path(
        "ai-candidates/",
        AIActionCandidateListAPIView.as_view(),
        name="ai-action-candidate-list",
    ),
    path(
        "ai-candidates/<int:candidate_id>/promote/",
        PromoteAIActionCandidateAPIView.as_view(),
        name="ai-action-candidate-promote",
    ),
    path(
        "ai-candidates/<int:candidate_id>/reject/",
        RejectAIActionCandidateAPIView.as_view(),
        name="ai-action-candidate-reject",
    ),
]
