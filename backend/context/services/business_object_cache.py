from context.models import BusinessObject


class BusinessObjectCache:
    """
    Simple in-process cache for BusinessObjects.

    This cache lives for the lifetime of the current
    process and avoids repeated database lookups during
    message processing.
    """

    _cache = {}

    @classmethod
    def get_objects(cls, organization):

        org_id = organization.id

        if org_id not in cls._cache:

            cls._cache[org_id] = list(
                BusinessObject.objects.filter(
                    organization=organization,
                    status="active",
                )
            )

        return cls._cache[org_id]

    @classmethod
    def invalidate(cls, organization):

        cls._cache.pop(
            organization.id,
            None,
        )

    @classmethod
    def clear(cls):

        cls._cache.clear()