import logging

from django.db import transaction

from .exceptions import RepositoryError


logger = logging.getLogger(__name__)


class BaseRepository:
    """
    Enterprise base repository.

    All repositories inherit this class.

    Provides:

        - transaction handling
        - logging
        - common CRUD
        - future cache hooks
    """

    model = None

    def __init__(self):

        if self.model is None:
            raise NotImplementedError(
                "Repository model is not configured."
            )

    # ---------------------------------------------------------
    # Create
    # ---------------------------------------------------------

    @transaction.atomic
    def create(self, **kwargs):

        try:

            obj = self.model.objects.create(**kwargs)

            logger.info(
                "%s created (%s)",
                self.model.__name__,
                obj.pk,
            )

            return obj

        except Exception as exc:

            logger.exception(exc)

            raise RepositoryError(str(exc))

    # ---------------------------------------------------------
    # Update
    # ---------------------------------------------------------

    @transaction.atomic
    def update(self, instance, **kwargs):

        try:

            for field, value in kwargs.items():
                setattr(instance, field, value)

            instance.save()

            logger.info(
                "%s updated (%s)",
                self.model.__name__,
                instance.pk,
            )

            return instance

        except Exception as exc:

            logger.exception(exc)

            raise RepositoryError(str(exc))

    # ---------------------------------------------------------
    # Delete
    # ---------------------------------------------------------

    @transaction.atomic
    def delete(self, instance):

        try:

            pk = instance.pk

            instance.delete()

            logger.info(
                "%s deleted (%s)",
                self.model.__name__,
                pk,
            )

        except Exception as exc:

            logger.exception(exc)

            raise RepositoryError(str(exc))

    # ---------------------------------------------------------
    # Get
    # ---------------------------------------------------------

    def get(self, **filters):

        return self.model.objects.filter(
            **filters
        ).first()

    # ---------------------------------------------------------
    # Filter
    # ---------------------------------------------------------

    def filter(self, **filters):

        return self.model.objects.filter(
            **filters
        )

    # ---------------------------------------------------------
    # Exists
    # ---------------------------------------------------------

    def exists(self, **filters):

        return self.model.objects.filter(
            **filters
        ).exists()

    # ---------------------------------------------------------
    # Count
    # ---------------------------------------------------------

    def count(self, **filters):

        return self.model.objects.filter(
            **filters
        ).count()