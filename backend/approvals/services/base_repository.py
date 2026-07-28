import logging

logger = logging.getLogger(__name__)


class BaseRepository:

    model = None

    @classmethod
    def create(cls, **kwargs):

        obj = cls.model.objects.create(**kwargs)

        logger.info(
            "%s created (%s)",
            cls.model.__name__,
            obj.pk,
        )

        return obj

    @classmethod
    def save(cls, instance):

        instance.save()

        logger.info(
            "%s updated (%s)",
            cls.model.__name__,
            instance.pk,
        )

        return instance