from inbox.models import OrganizationUser


class OrganizationResolver:

    @staticmethod
    def resolve(request):
        """
        Resolve the organization associated with
        the currently authenticated user.
        """

        user = getattr(request, "user", None)

        if (
            user is None
            or not getattr(user, "is_authenticated", False)
        ):
            return None

        try:
            membership = user.organization_membership
            return membership.organization
        except OrganizationUser.DoesNotExist:
            return None