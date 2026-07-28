from context.models import BusinessRelationship


class RelationshipHealth:

    @staticmethod
    def summary():

        total = BusinessRelationship.objects.count()

        stale = BusinessRelationship.objects.filter(

            last_verified__isnull=True

        ).count()

        return {

            "relationships": total,

            "stale": stale,

            "healthy": total - stale,

        }