"""
Enterprise Ordering Framework

Provides safe ordering support for all
One UCH REST APIs.

Only explicitly allowed fields can be used
for ordering.
"""


class EnterpriseOrdering:

    """
    Base ordering backend.
    """

    parameter = "ordering"

    ordering_fields = []

    default_ordering = []

    def apply(
        self,
        queryset,
        request,
    ):

        ordering = request.query_params.get(
            self.parameter,
        )

        if not ordering:

            if self.default_ordering:

                return queryset.order_by(
                    *self.default_ordering,
                )

            return queryset

        fields = []

        for field in ordering.split(","):

            field = field.strip()

            if not field:
                continue

            descending = field.startswith("-")

            clean = field[1:] if descending else field

            if clean not in self.ordering_fields:
                continue

            if descending:
                fields.append(f"-{clean}")
            else:
                fields.append(clean)

        if fields:
            return queryset.order_by(*fields)

        if self.default_ordering:
            return queryset.order_by(
                *self.default_ordering,
            )

        return queryset