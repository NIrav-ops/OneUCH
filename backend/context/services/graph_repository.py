from typing import Dict, List

from context.models import (
    BusinessObject,
    BusinessRelationship,
)

from context.exceptions import (
    GraphRepositoryError,
    BusinessObjectNotFound,
)

from context.services.base_graph_repository import (
    BaseGraphRepository,
)
from context.services.graph_cache_manager import (
    GraphCacheManager,
)

class GraphRepository(BaseGraphRepository):
    """
    Enterprise Graph Repository.

    Central abstraction layer for every graph query.

    Future responsibilities

    - Neighbour lookup
    - Multi-hop traversal
    - Customer 360
    - Vendor 360
    - Organization Graph
    - Graph AI
    """
    @staticmethod
    def _validate_business_object(
        business_object,
    ):
        """
        Validate repository input.
        """

        if business_object is None:

            raise BusinessObjectNotFound(
                "BusinessObject cannot be None."
            )

        return business_object
    
    # --------------------------------------------------
    # Cache Keys
    # --------------------------------------------------

    @staticmethod
    def _neighbors_cache_key(business_object):

        return f"graph_neighbors_{business_object.id}"

    @staticmethod
    def _statistics_cache_key():

        return "graph_statistics"

    @staticmethod
    def _object_count_cache_key():

        return "graph_object_count"

    @staticmethod
    def _relationship_count_cache_key():

        return "graph_relationship_count"
    # --------------------------------------------------
    # Business Objects
    # --------------------------------------------------

    @staticmethod
    def all_objects():

        return BusinessObject.objects.all()

    @staticmethod
    def get_object(pk):

        return BusinessObject.objects.filter(
            pk=pk
        ).first()

    # --------------------------------------------------
    # Relationships
    # --------------------------------------------------

    @staticmethod
    def all_relationships():

        return BusinessRelationship.objects.all()
    
    # --------------------------------------------------
    # Neighbour Queries
    # --------------------------------------------------

    @classmethod
    def outgoing_relationships(cls, business_object):

        business_object = cls._validate_business_object(
            business_object
        )

        return BusinessRelationship.objects.filter(
            source_object=business_object,
        ).select_related(
            "target_object",
        )

    @classmethod
    def incoming_relationships(cls, business_object):

        business_object = cls._validate_business_object(
            business_object
        )

        return BusinessRelationship.objects.filter(
            target_object=business_object,
        ).select_related(
            "source_object",
        )

    @classmethod
    def neighbors(
        cls,
        business_object: BusinessObject,
    ) -> List[BusinessObject]:
        """
        Return every directly connected BusinessObject.
        """

        business_object = cls._validate_business_object(
            business_object
        )

        cache_key = cls._neighbors_cache_key(
            business_object
        )

        cached = GraphCacheManager.get(cache_key)

        if cached is not None:

            return list(cached)

        try:

            neighbours = []

            # Outgoing
            for relationship in cls.outgoing_relationships(
                business_object
            ):

                neighbours.append(
                    relationship.target_object
                )

            # Incoming
            for relationship in cls.incoming_relationships(
                business_object
            ):

                neighbours.append(
                    relationship.source_object
                )

            unique = []

            for obj in neighbours:

                if obj not in unique:
                    unique.append(obj)

            GraphCacheManager.set(
                cache_key,
                list(unique),
            )

            return list(unique)

        except Exception as exc:

            raise GraphRepositoryError(
                str(exc)
            ) from exc
    
    @staticmethod
    def object_count()-> int:
        """
        Returns total Business Objects.
        """

        cache_key = GraphRepository._object_count_cache_key()

        cached = GraphCacheManager.get(cache_key)

        if cached is not None:

            return cached

        count = BusinessObject.objects.count()

        GraphCacheManager.set(
            cache_key,
            count,
        )

        return count


    @staticmethod
    def relationship_count() -> int:
        """
        Returns total Relationships.
        """

        cache_key = GraphRepository._relationship_count_cache_key()

        cached = GraphCacheManager.get(cache_key)

        if cached is not None:

            return cached

        count = BusinessRelationship.objects.count()

        GraphCacheManager.set(
            cache_key,
            count,
        )

        return count


    @staticmethod
    def graph_statistics() -> Dict[str, int]:
        """
        Enterprise graph statistics.
        """

        cache_key = GraphRepository._statistics_cache_key()

        cached = GraphCacheManager.get(cache_key)

        if cached is not None:

            return dict(cached)

        stats = {
            "objects": BusinessObject.objects.count(),
            "relationships": BusinessRelationship.objects.count(),
        }

        GraphCacheManager.set(
            cache_key,
            stats,
        )

        return dict(stats)
    
    @staticmethod
    def isolated_objects() -> List[BusinessObject]:
        """
        BusinessObjects having no relationships.
        """

        isolated = []

        for obj in BusinessObject.objects.all():

            outgoing = obj.outgoing_relationships.exists()

            incoming = obj.incoming_relationships.exists()

            if not outgoing and not incoming:

                isolated.append(obj)

        return list(isolated)