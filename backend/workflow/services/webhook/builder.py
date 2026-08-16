from workflow.services.webhook.template_engine import (
    TemplateEngine,
)
class RequestBuilder:
    """
    Converts workflow configuration
    into an HTTP request.
    """

    def __init__(self, context):

        self.template = TemplateEngine(
            context
        )

    def build(self, configuration):

        return {

            "method": configuration.get(
                "method",
                "GET",
            ),

            "url": self.template.render(
                configuration["url"]
            ),

            "headers": self.template.render(
                configuration.get(
                    "headers",
                    {},
                )
            ),

            "params": self.template.render(
                configuration.get(
                    "params",
                    {},
                )
            ),

            "json": self.template.render(
                configuration.get(
                    "body",
                    None
                )
            ),

            "timeout": configuration.get(
                "timeout",
                30,
            ),
        }