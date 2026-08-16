from workflow.services.functions import BuiltInFunctions


class FunctionRegistry:

    FUNCTIONS = {}

    @classmethod
    def register(cls, name, function):

        cls.FUNCTIONS[name] = function

    @classmethod
    def exists(cls, name):

        return name in cls.FUNCTIONS

    @classmethod
    def execute(cls, name, arguments):

        function = cls.FUNCTIONS.get(name)

        if function is None:
            raise ValueError(
                f"Unknown function '{name}'."
            )

        return function(*arguments)

    @classmethod
    def list_functions(cls):

        return sorted(cls.FUNCTIONS.keys())

from workflow.services.functions import BuiltInFunctions


FunctionRegistry.register(
    "uppercase",
    BuiltInFunctions.uppercase,
)

FunctionRegistry.register(
    "lowercase",
    BuiltInFunctions.lowercase,
)

FunctionRegistry.register(
    "title",
    BuiltInFunctions.title,
)

FunctionRegistry.register(
    "trim",
    BuiltInFunctions.trim,
)

FunctionRegistry.register(
    "concat",
    BuiltInFunctions.concat,
)

FunctionRegistry.register(
    "length",
    BuiltInFunctions.length,
)

FunctionRegistry.register(
    "uuid",
    BuiltInFunctions.uuid,
)

FunctionRegistry.register(
    "today",
    BuiltInFunctions.today,
)

FunctionRegistry.register(
    "now",
    BuiltInFunctions.now,
)

FunctionRegistry.register(
    "json_parse",
    BuiltInFunctions.json_parse,
)

FunctionRegistry.register(
    "json_stringify",
    BuiltInFunctions.json_stringify,
)