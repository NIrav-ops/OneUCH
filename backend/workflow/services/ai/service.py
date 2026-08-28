import logging
import time

from django.conf import settings

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

from workflow.services.ai.governance.execution_policy import (
    AIExecutionPolicy,
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
        # 1. Validate caller request locally.
        # --------------------------------------------------

        AIValidator.validate(
            request
        )

        # --------------------------------------------------
        # 2. PRE-EXECUTION GOVERNANCE
        #
        # deterministic_only fails closed before provider
        # resolution.
        #
        # For AI-enabled modes preserve the existing
        # ProviderNotFound hardening contract.
        # --------------------------------------------------

        ai_mode = str(
            getattr(
                settings,
                "ONEUCH_AI_MODE",
                "cloud",
            )
            or ""
        ).strip().lower()

        if (
            ai_mode
            != AIExecutionPolicy.MODE_DETERMINISTIC_ONLY
            and provider
            not in AIProviderRouter.PROVIDERS
        ):
            AIProviderRouter.get_provider(
                provider
            )

        execution_policy = (
            AIExecutionPolicy.evaluate(
                mode=ai_mode,
                provider=provider,
            )
        )

        if not execution_policy.allowed:

            logger.warning(
                "AI execution blocked by governance | "
                "mode=%s provider=%s reason=%s",
                execution_policy.mode,
                execution_policy.provider,
                execution_policy.reason,
            )

            return AIResult(
                success=False,
                output=None,
                provider=provider,
                model=request.model,
                execution_time_ms=0,
                confidence=0.0,
                metadata={
                    "failure_stage":
                        "execution_governance",

                    "retryable":
                        False,

                    # Canonical provenance field used by
                    # future Evidence Contract.
                    "processing_mode":
                        execution_policy.mode,

                    # Backward-compatible alias.
                    "governance_mode":
                        execution_policy.mode,

                    "governance_allowed":
                        False,

                    "governance_provider":
                        execution_policy.provider,

                    "governance_reason":
                        execution_policy.reason,
                },
                error=(
                    execution_policy.reason
                ),
            )

        # --------------------------------------------------
        # 3. Resolve permitted provider.
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
            # 4. Execute provider.
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
            # 5. Enforce normalized provider contract.
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
            # 6. Validate provider output.
            # ----------------------------------------------

            AIOutputValidator.validate(
                request=request,
                result=result,
            )

            # ----------------------------------------------
            # 7. Attach processing provenance.
            #
            # Preserve provider-specific metadata while
            # adding One UCH governance metadata.
            # ----------------------------------------------

            result.metadata = dict(
                result.metadata or {}
            )

            result.metadata.update(
                {
                    "processing_mode":
                        execution_policy.mode,

                    "governance_allowed":
                        True,

                    "governance_provider":
                        execution_policy.provider,

                    "governance_reason":
                        execution_policy.reason,
                }
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

                    "processing_mode":
                        execution_policy.mode,

                    "governance_allowed":
                        True,

                    "governance_provider":
                        execution_policy.provider,

                    "governance_reason":
                        execution_policy.reason,
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

                    "processing_mode":
                        execution_policy.mode,

                    "governance_allowed":
                        True,

                    "governance_provider":
                        execution_policy.provider,

                    "governance_reason":
                        execution_policy.reason,
                },
                error=str(exc),
            )
