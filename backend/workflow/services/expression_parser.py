class ExpressionParser:

    def parse(
        self,
        script,
    ):

        script = script.strip()

        if (
            "(" not in script
            or ")" not in script
            or not script.endswith(")")
        ):
            raise ValueError(
                "Invalid script expression."
            )

        function_name = script.split(
            "(",
            1,
        )[0].strip()

        argument_string = script[
            script.index("(")+1:
            script.rindex(")")
        ]

        arguments = []

        if argument_string.strip():

            arguments = [

                arg.strip()

                for arg in argument_string.split(",")

            ]

        return {

            "function": function_name,

            "arguments": arguments,

        }