from platform_core.registry import (
    ServiceRegistry,
)


class PlatformHealth:

    def build(
        self,
    ):

        return {

            "status": "healthy",

            "registered_services":
                ServiceRegistry.count(),

        }