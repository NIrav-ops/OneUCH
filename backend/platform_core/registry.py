from platform_core.exceptions import (
    ServiceNotRegistered,
)


class ServiceRegistry:
    """
    Enterprise singleton registry.

    Responsible for holding
    every enterprise service.
    """

    _services = {}

    @classmethod
    def register(
        cls,
        name,
        service,
    ):

        cls._services[name] = service

    @classmethod
    def get(
        cls,
        name,
    ):

        if name not in cls._services:

            raise ServiceNotRegistered(
                f"{name} is not registered."
            )

        return cls._services[name]

    @classmethod
    def exists(
        cls,
        name,
    ):

        return name in cls._services

    @classmethod
    def clear(
        cls,
    ):

        cls._services.clear()

    @classmethod
    def count(
        cls,
    ):

        return len(
            cls._services,
        )

    @classmethod
    def services(
        cls,
    ):

        return dict(
            cls._services,
        )