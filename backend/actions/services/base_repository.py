import logging

logger = logging.getLogger(__name__)


class BaseRepository:
    """
    Base repository providing common CRUD operations.
    """

    model = None

    @classmethod
    def get(cls, **filters):
        return cls.model.objects.get(**filters)

    @classmethod
    def filter(cls, **filters):
        return cls.model.objects.filter(**filters)

    @classmethod
    def create(cls, **data):
        obj = cls.model.objects.create(**data)
        logger.info("%s created (%s)", cls.model.__name__, obj.pk)
        return obj

    @classmethod
    def update(cls, instance, **data):
        for key, value in data.items():
            setattr(instance, key, value)

        instance.save()
        logger.info("%s updated (%s)", cls.model.__name__, instance.pk)
        return instance

    @classmethod
    def delete(cls, instance):
        pk = instance.pk
        instance.delete()
        logger.info("%s deleted (%s)", cls.model.__name__, pk)