"""
Enterprise Permissions

These permissions are reusable across
the entire One UCH platform.
"""

from rest_framework.permissions import BasePermission


class EnterprisePermission(BasePermission):

    """
    Minimum requirement.

    User must be authenticated.
    """

    def has_permission(

        self,

        request,

        view,

    ):

        return bool(

            request.user

            and request.user.is_authenticated

        )


class AdminPermission(BasePermission):

    """
    Platform administrator.

    Future:

    Organization Owner

    Super Admin

    Global Admin
    """

    def has_permission(

        self,

        request,

        view,

    ):

        return bool(

            request.user

            and request.user.is_staff

        )


class ReadOnlyPermission(BasePermission):

    """
    Allows only GET requests.
    """

    SAFE_METHODS = (

        "GET",

        "HEAD",

        "OPTIONS",

    )

    def has_permission(

        self,

        request,

        view,

    ):

        return request.method in self.SAFE_METHODS


class OrganizationPermission(BasePermission):

    """
    Placeholder.

    Later this checks

    Organization

    Membership

    License

    Subscription

    RBAC
    """

    def has_permission(

        self,

        request,

        view,

    ):

        return bool(

            request.user

            and request.user.is_authenticated

        )