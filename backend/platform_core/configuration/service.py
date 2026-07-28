from platform_core.configuration.repository import (
    ConfigurationRepository,
)


class ConfigurationService:

    def set(

        self,

        key,

        value,

    ):

        ConfigurationRepository.set(

            key,

            value,

        )

    def get(

        self,

        key,

        default=None,

    ):

        return ConfigurationRepository.get(

            key,

            default,

        )

    def all(

        self,

    ):

        return ConfigurationRepository.all()