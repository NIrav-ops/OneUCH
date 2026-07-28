import logging
import time

from workflow.services.ai.contracts import (
    AIResult,
)

from workflow.services.ai.provider_router import (
    AIProviderRouter,
)

from workflow.services.ai.validator import (
    AIValidator,
)

from workflow.services.ai.output_validator import (
    AIOutputValidator,
)

from workflow.services.ai.exceptions import (
    AIOutputValidationError,
)


logger = logging.getLogger(__name__)


class AIExecutionService:

    @classmethod
    def execute(
        cls,
        request,
        provider="mock",
    ):

        # --------------------------------------------------
        # 1. Validate caller request
        # --------------------------------------------------

        AIValidator.validate(
            request
        )

        # --------------------------------------------------
        # 2. Resolve provider
        #
        # Provider routing errors remain explicit errors.
        # They are configuration/programming failures rather
        # than provider execution failures.
        # --------------------------------------------------

        engine = (
            AIProviderRouter.get_provider(
                provider
            )
        )

        started_at = (
            time.perf_counter()
        )

        try:

            # ----------------------------------------------
            # 3. Execute provider
            # ----------------------------------------------

            result = engine.execute(
                request
            )

            execution_time_ms = int(
                (
                    time.perf_counter()
                    - started_at
                )
                * 1000
            )

            # ----------------------------------------------
            # 4. Enforce normalized provider contract
            # ----------------------------------------------

            if not isinstance(
                result,
                AIResult,
            ):
                raise TypeError(
                    "AI provider must return AIResult."
                )

            if (
                result.execution_time_ms
                <= 0
            ):
                result.execution_time_ms = (
                    execution_time_ms
                )

            # ----------------------------------------------
            # 5. Validate provider output
            # ----------------------------------------------

            AIOutputValidator.validate(
                request=request,
                result=result,
            )

            logger.info(
                "AI execution completed | "
                "provider=%s model=%s success=%s",
                result.provider,
                result.model,
                result.success,
            )

            return result

        except AIOutputValidationError as exc:

            execution_time_ms = int(
                (
                    time.perf_counter()
                    - started_at
                )
                * 1000
            )

            logger.warning(
                "AI output validation failed | "
                "provider=%s model=%s error=%s",
                provider,
                request.model,
                exc,
            )

            return AIResult(
                success=False,
                output=None,
                provider=provider,
                model=request.model,
                execution_time_ms=(
                    execution_time_ms
                ),
                confidence=0.0,
                metadata={
                    "exception_type":
                        exc.__class__.__name__,

                    "failure_stage":
                        "output_validation",
                },
                error=str(exc),
            )

        except Exception as exc:

            execution_time_ms = int(
                (
                    time.perf_counter()
                    - started_at
                )
                * 1000
            )

            logger.exception(
                "AI execution failed | "
                "provider=%s model=%s",
                provider,
                request.model,
            )

            return AIResult(
                success=False,
                output=None,
                provider=provider,
                model=request.model,
                execution_time_ms=(
                    execution_time_ms
                ),
                confidence=0.0,
                metadata={
                    "exception_type":
                        exc.__class__.__name__,

                    "failure_stage":
                        "provider_execution",
                },
                error=str(exc),
            )