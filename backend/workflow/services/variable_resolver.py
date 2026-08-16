from click import argument


class VariableResolver:

    def __init__(
        self,
        context,
    ):

        self.context = context

    def resolve(self, argument):

        parts = argument.split(".")

        value = self.context.get(parts[0])

        if value is None:
            return argument

        for part in parts[1:]:

            if isinstance(value, dict):
                value = value.get(part)
            else:
                return argument

            if value is None:
                return argument

        return value

    def resolve_all(
        self,
        arguments,
    ):

        return [

            self.resolve(arg)

            for arg in arguments

        ]