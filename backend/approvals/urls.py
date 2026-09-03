from django.urls import path
from .views import (
    ApprovalListAPIView,
    PendingApprovalListAPIView,
    TeamMemberListAPIView,
    AssignApprovalAPIView,
    ApproveItemAPIView,
    RejectItemAPIView,
    NeedsInfoItemAPIView,
    IgnoreApprovalAPIView,
    ReopenApprovalAPIView,
)

from .review_views import (
    AIApprovalCandidateListAPIView,
    PromoteAIApprovalCandidateAPIView,
    RejectAIApprovalCandidateAPIView,
)

urlpatterns = [
    path("", ApprovalListAPIView.as_view(), name="approval-list"),
    path("pending/", PendingApprovalListAPIView.as_view(), name="pending-approval-list"),
    path("team-members/", TeamMemberListAPIView.as_view(), name="team-member-list"),
    path("<int:approval_id>/assign/", AssignApprovalAPIView.as_view(), name="assign-approval"),
    path("<int:approval_id>/approve/", ApproveItemAPIView.as_view(), name="approve-item"),
    path("<int:approval_id>/reject/", RejectItemAPIView.as_view(), name="reject-item"),
    path("<int:approval_id>/needs-info/", NeedsInfoItemAPIView.as_view(), name="needs-info-item"),
    path("<int:approval_id>/ignore/", IgnoreApprovalAPIView.as_view(), name="ignore-approval-item"),
    path("<int:approval_id>/reopen/", ReopenApprovalAPIView.as_view(), name="reopen-approval-item"),
    path(
        "review-candidates/",
        AIApprovalCandidateListAPIView.as_view(),
        name="approval-review-candidate-list",
    ),
    path(
        "review-candidates/<int:candidate_id>/promote/",
        PromoteAIApprovalCandidateAPIView.as_view(),
        name="approval-review-candidate-promote",
    ),
    path(
        "review-candidates/<int:candidate_id>/reject/",
        RejectAIApprovalCandidateAPIView.as_view(),
        name="approval-review-candidate-reject",
    ),

    # Backwards-compatible PR3B AI aliases.
    path(
        "ai-candidates/",
        AIApprovalCandidateListAPIView.as_view(),
        name="ai-approval-candidate-list",
    ),
    path(
        "ai-candidates/<int:candidate_id>/promote/",
        PromoteAIApprovalCandidateAPIView.as_view(),
        name="ai-approval-candidate-promote",
    ),
    path(
        "ai-candidates/<int:candidate_id>/reject/",
        RejectAIApprovalCandidateAPIView.as_view(),
        name="ai-approval-candidate-reject",
    ),
]
