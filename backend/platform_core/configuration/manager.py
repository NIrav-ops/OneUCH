from platform_core.configuration.service import (
    ConfigurationService,
)


class ConfigurationManager:

    service = ConfigurationService()

    @classmethod
    def set(

        cls,

        key,

        value,

    ):

        cls.service.set(

            key,

            value,

        )

    @classmethod
    def get(

        cls,

        key,

        default=None,

    ):

        return cls.service.get(

            key,

            default,

        )