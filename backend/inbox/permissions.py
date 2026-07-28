from rest_framework.permissions import BasePermission


class IsOrganizationAdmin(BasePermission):
    """
    Allows access only to org admins or owners.
    """

    def has_permission(self, request, view):
        membership = getattr(request.user, "organization_membership", None)
        if not membership:
            return False
        return membership.is_admin()


class IsOrganizationOwner(BasePermission):
    """
    Allows access only to org owners.
    """

    def has_permission(self, request, view):
        membership = getattr(request.user, "organization_membership", None)
        if not membership:
            return False
        return membership.is_owner()
