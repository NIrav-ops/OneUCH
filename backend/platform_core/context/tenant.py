"""
Enterprise Tenant Context

A Tenant represents the execution boundary
for an organization.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class TenantContext:

    id: Optional[int] = None

    organization_id: Optional[int] = None

    name: Optional[str] = None

    slug: Optional[str] = None

    is_active: bool = True

    metadata: Optional[dict] = None

from platform_core.context.organization import (
    OrganizationResolver,
)


class TenantResolver:

    @staticmethod
    def resolve(request):

        organization = OrganizationResolver.resolve(
            request,
        )

        if organization is None:
            return None

        return TenantContext(

            id=organization.id,

            organization_id=organization.id,

            name=organization.name,

            slug=organization.slug,

            is_active=organization.is_active,

            metadata={},

        )