"""
Enterprise Security Context
"""

from dataclasses import dataclass
from typing import Optional
from inbox.models import OrganizationUser


@dataclass
class SecurityContext:

    user_id: Optional[int] = None

    email: Optional[str] = None

    role: Optional[str] = None

    is_authenticated: bool = False

    is_staff: bool = False

    is_superuser: bool = False

    organization_id: Optional[int] = None

class SecurityResolver:

    @staticmethod
    def resolve(request):

        user = getattr(
            request,
            "user",
            None,
        )

        if (
            user is None
            or not getattr(
                user,
                "is_authenticated",
                False,
            )
        ):
            return SecurityContext()

        try:
            membership = user.organization_membership
        except OrganizationUser.DoesNotExist:
            membership = None

        return SecurityContext(

            user_id=user.id,

            email=user.email,

            role=user.role,

            is_authenticated=True,

            is_staff=user.is_staff,

            is_superuser=user.is_superuser,

            organization_id=(
                membership.organization_id
                if membership
                else None
            ),

        )
    
