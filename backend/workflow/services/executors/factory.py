from workflow.services.executors.registry import (
    ExecutorRegistry,
)


class ExecutorFactory:

    @classmethod
    def get_executor(
        cls,
        node_type,
    ):

        return ExecutorRegistry.get_executor(
            node_type
        )