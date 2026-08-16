from workflow.services.executors.base import BaseNodeExecutor
from workflow.services.script_engine import ScriptEngine


class ScriptNodeExecutor(BaseNodeExecutor):
    """
    Executes a Script workflow node.

    The executor itself remains intentionally lightweight.
    All parsing and execution logic is delegated to ScriptEngine.
    """

    def execute(self):

        configuration = self.token.node.configuration or {}

        script = configuration.get("script")

        output_variable = configuration.get(
            "output",
            "script_result",
        )

        result = ScriptEngine(
            context=self.context,
        ).execute(
            script=script,
        )

        outputs = self.context.get(
            "script_outputs",
            [],
        )

        outputs.append(
            {
                "node": self.token.node.name,
                "script": script,
                "output_variable": output_variable,
                "result": result,
            }
        )

        self.context.set(
            "script_outputs",
            outputs,
        )

        self.context.set(
            output_variable,
            result,
        )

        return True