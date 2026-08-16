from workflow.services.webhook.builder import (
    RequestBuilder,
)

from workflow.services.webhook.transport import (
    HTTPTransport,
)

from workflow.services.webhook.parser import (
    ResponseParser,
)

from workflow.services.webhook.authentication import (
    AuthenticationProvider,
)

from workflow.services.webhook.retry import (
    RetryPolicy,
)


class WebhookService:

    def __init__(self, context):

        self.builder = RequestBuilder(
            context
        )

        self.transport = HTTPTransport()

        self.parser = ResponseParser()

        self.authentication = AuthenticationProvider()

        self.retry = RetryPolicy()

    def execute(
        self,
        configuration,
    ):

        request = self.builder.build(
            configuration
        )

        request = self.authentication.apply(
            request,
            configuration,
        )

        response = self.retry.execute(

            lambda: self.transport.send(
                **request
            ),

            retries=configuration.get(
                "retries",
                3,
            ),

            delay=configuration.get(
                "retry_delay",
                1,
            ),
        )

        return self.parser.parse(
            response
        )