from platform_core.registry import (
    ServiceRegistry,
)


class PlatformMetrics:

    def build(
        self,
    ):

        return {

            "services":

                ServiceRegistry.count(),

            "loaded":

                list(
                    ServiceRegistry.services().keys()
                ),

        }