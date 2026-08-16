class ScriptParser:
    """
    Parses workflow script expressions.

    Commit 11.6.2 only validates
    and prepares expressions.

    Function execution is added
    in Commit 11.6.3.
    """

    def __init__(self, context):

        self.context = context

    def parse(self, script):

        script = script.strip()

        if not script:

            raise ValueError(
                "Script cannot be empty."
            )

        return script

    def execute(self, parsed_script):
        """
        Temporary implementation.

        Commit 11.6.3 replaces this
        with FunctionRegistry execution.
        """

        return parsed_script