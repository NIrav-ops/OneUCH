from workflow.services.executors.base import (
    BaseNodeExecutor,
)

from workflow.services.ai import (
    AIRequest,
    AIExecutionService,
    PromptBuilder,
    AIContextBuilder,
    AIGovernanceEngine,
)

from workflow.services.ai.review import (
    AIHumanReviewBuilder,
)

class AINodeExecutor(BaseNodeExecutor):
    """
    Enterprise workflow AI node executor.

    Responsibilities:
    - Build governed enterprise AI context.
    - Build the final prompt.
    - Execute the configured AI provider.
    - Evaluate the result through AI governance.
    - Store normalized execution and governance state
      in the workflow runtime context.

    This executor does NOT directly perform business actions,
    approvals, payments, sends, or other side effects.
    """

    DEFAULT_PROVIDER = "mock"
    DEFAULT_GOVERNANCE_POLICY = "default"

    def execute(self):

        node = self.token.node
        instance = self.token.instance

        configuration = (
            node.configuration or {}
        )

        task_prompt = configuration.get(
            "prompt",
            f"Process workflow node: {node.name}",
        )

        provider = configuration.get(
            "provider",
            self.DEFAULT_PROVIDER,
        )

        model = configuration.get(
            "model"
        )

        temperature = configuration.get(
            "temperature",
            0.0,
        )

        max_tokens = configuration.get(
            "max_tokens",
            1000,
        )

        response_type = configuration.get(
            "response_type",
            "text",
        )

        response_schema = configuration.get(
            "response_schema"
        )

        governance_policy = configuration.get(
            "governance_policy",
            self.DEFAULT_GOVERNANCE_POLICY,
        )

        fail_on_error = configuration.get(
            "fail_on_error",
            True,
        )

        business_object = self.context.get(
            "business_object"
        )

        include_runtime_context = configuration.get(
            "include_runtime_context",
            True,
        )

        runtime_context = (
            self.context.serialize()
            if include_runtime_context
            else {}
        )

        enterprise_context = AIContextBuilder.build(
            workflow_instance=instance,
            business_object=business_object,
            runtime_context=runtime_context,
        )

        prompt = PromptBuilder.build(
            task_prompt=task_prompt,
            context=enterprise_context,
        )

        request = AIRequest(
            prompt=prompt,
            provider=provider,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            response_type=response_type,
            response_schema=response_schema,
            context=enterprise_context,
            metadata={
                "workflow_instance_id": str(
                    instance.id
                ),
                "workflow_id": str(
                    instance.workflow_id
                ),
                "workflow_node_id": str(
                    node.id
                ),
                "workflow_node_name":
                    node.name,
                "governance_policy":
                    governance_policy,
            },
        )

        result = AIExecutionService.execute(
            request=request,
            provider=provider,
        )

        governance = (
            AIGovernanceEngine.evaluate(
                request=request,
                result=result,
                policy_name=governance_policy,
            )
        )

        review_request = None

        if (
            result.success
            and governance.requires_review
        ):
            review_request = (
                AIHumanReviewBuilder.build(
                    request=request,
                    result=result,
                    governance=governance,
                )
            )

        output = {
            "node": node.name,
            "node_id": str(node.id),

            "processed": result.success,
            "success": result.success,

            "output": result.output,

            "provider": result.provider,
            "model": result.model,

            "response_type":
                response_type,

            "prompt_tokens":
                result.prompt_tokens,

            "completion_tokens":
                result.completion_tokens,

            "total_tokens":
                result.total_tokens,

            "execution_time":
                result.execution_time,

            "cost":
                result.cost,

            "confidence":
                result.confidence,

            "error":
                result.error,

            "metadata":
                result.metadata,

            "governance": {
                "outcome":
                    governance.outcome,

                "allowed":
                    governance.allowed,

                "requires_review":
                    governance.requires_review,

                "blocked":
                    governance.blocked,

                "can_execute":
                    governance.can_execute,

                "confidence":
                    governance.confidence,

                "reason":
                    governance.reason,

                "policy_name":
                    governance.policy_name,
            },
            "review": (
                review_request.serialize()
                if review_request
                else None
            ),
        }

        ai_results = self.context.get(
            "ai_results",
            [],
        )

        ai_results.append(
            output
        )

        self.context.set(
            "ai_results",
            ai_results,
        )

        self.context.set(
            "last_ai_result",
            output,
        )

        governance_output = {
            "node": node.name,
            "node_id": str(node.id),

            "outcome":
                governance.outcome,

            "allowed":
                governance.allowed,

            "requires_review":
                governance.requires_review,

            "blocked":
                governance.blocked,

            "can_execute":
                governance.can_execute,

            "confidence":
                governance.confidence,

            "reason":
                governance.reason,

            "policy_name":
                governance.policy_name,
        }

        self.context.set(
            "ai_governance",
            governance_output,
        )

        self.context.set(
            "ai_requires_review",
            governance.requires_review,
        )

        self.context.set(
            "ai_blocked",
            governance.blocked,
        )

        if review_request is not None:

            serialized_review = (
                review_request.serialize()
            )

            pending_reviews = (
                self.context.get(
                    "ai_pending_reviews",
                    [],
                )
            )

            pending_reviews.append(
                serialized_review
            )

            self.context.set(
                "ai_pending_reviews",
                pending_reviews,
            )

            self.context.set(
                "ai_pending_review",
                serialized_review,
            )

            self.context.set(
                "ai_review_pending",
                True,
            )

            self.context.suspend(
                reason="AI_HUMAN_REVIEW",
                metadata={
                    "review_id":
                        str(
                            review_request.review_id
                        ),

                    "workflow_node_id":
                        str(node.id),

                    "governance_policy":
                        governance.policy_name,

                    "governance_outcome":
                        governance.outcome,
                },
            )

        else:

            self.context.set(
                "ai_pending_review",
                None,
            )

            self.context.set(
                "ai_review_pending",
                False,
            )        

        if not result.success:

            self.context.set(
                "ai_failed",
                True,
            )

            if fail_on_error:
                return False

        else:

            self.context.set(
                "ai_failed",
                False,
            )

        return True