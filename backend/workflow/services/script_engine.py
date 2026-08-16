import logging
import time

from workflow.services.expression_parser import ExpressionParser
from workflow.services.variable_resolver import VariableResolver
from workflow.services.function_registry import FunctionRegistry
from workflow.services.exceptions import ScriptExecutionException

logger = logging.getLogger(__name__)


class ScriptEngine:

    def __init__(self, context):

        self.context = context

        self.parser = ExpressionParser()

        self.resolver = VariableResolver(context)

    def execute(self, script):

        started = time.monotonic()

        try:

            parsed = self.parser.parse(script)

            arguments = self.resolver.resolve_all(
                parsed["arguments"]
            )

            result = FunctionRegistry.execute(
                parsed["function"],
                arguments,
            )

            logger.debug(
                "Workflow script executed successfully."
            )

            return result

        except Exception as exc:

            logger.exception(
                "Workflow script execution failed."
            )

            raise ScriptExecutionException(
                str(exc)
            ) from exc

        finally:

            elapsed = time.monotonic() - started

            logger.debug(
                "Script execution time %.4f seconds",
                elapsed,
            )