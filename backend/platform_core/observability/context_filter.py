import logging

from platform_core.context import get_request_context


class RequestContextFilter(logging.Filter):
    """
    Inject RequestContext information into every log record.
    """

    def filter(self, record):

        context = get_request_context()

        if context:

            record.request_id = context.request_id
            record.correlation_id = context.correlation_id

            record.organization_id = (
                context.organization.id
                if context.organization
                else None
            )

            record.tenant_id = (
                context.tenant.id
                if context.tenant
                else None
            )

            record.user_id = (
                context.user.id
                if context.user
                else None
            )

            record.request_path = context.path
            record.request_method = context.method

        else:

            record.request_id = "-"

            record.correlation_id = "-"

            record.organization_id = "-"

            record.tenant_id = "-"

            record.user_id = "-"

            record.request_path = "-"

            record.request_method = "-"

        return True