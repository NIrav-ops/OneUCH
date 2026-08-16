from django.test import SimpleTestCase

from workflow.services.script_engine import ScriptEngine
from workflow.services.exceptions import ScriptExecutionException

class DummyContext:

    def __init__(self):

        self.values = {
            "customer_name": "john",
            "email": "john@example.com",
            "count": 5,
            "customer": {
                "name": "John Doe",
                "email": "john@example.com",
            },
        }

    def get(self, key, default=None):

        return self.values.get(key, default)

class ScriptEngineTests(SimpleTestCase):

    def setUp(self):

        self.engine = ScriptEngine(
            DummyContext(),
        )

    def test_uppercase(self):

        result = self.engine.execute(
            "uppercase(customer_name)"
        )

        self.assertEqual(
            result,
            "JOHN",
        )

    def test_lowercase(self):

        result = self.engine.execute(
            "lowercase(customer_name)"
        )

        self.assertEqual(
            result,
            "john",
        )

    def test_title(self):

        result = self.engine.execute(
            "title(customer_name)"
        )

        self.assertEqual(
            result,
            "John",
        )

    def test_trim(self):

        context = DummyContext()

        context.values["name"] = "  John  "

        result = ScriptEngine(
            context
        ).execute(
            "trim(name)"
        )

        self.assertEqual(
            result,
            "John",
        )

    def test_length(self):

        result = self.engine.execute(
            "length(customer_name)"
        )

        self.assertEqual(
            result,
            4,
        )

    def test_concat(self):

        result = self.engine.execute(
            "concat(customer_name,email)"
        )

        self.assertEqual(
            result,
            "johnjohn@example.com",
        )

    def test_uuid(self):

        result = self.engine.execute(
            "uuid()"
        )

        self.assertTrue(
            len(result) > 30
        )

    def test_today(self):

        result = self.engine.execute(
            "today()"
        )

        self.assertEqual(
            len(result),
            10,
        )

    def test_now(self):

        result = self.engine.execute(
            "now()"
        )

        self.assertIn(
            "T",
            result,
        )

    def test_now(self):

        result = self.engine.execute(
            "now()"
        )

        self.assertIn(
            "T",
            result,
        )

    def test_nested_variable(self):

        result = self.engine.execute(
            "uppercase(customer.name)"
        )

        self.assertEqual(
            result,
            "JOHN DOE",
        )

    def test_unknown_function(self):

        with self.assertRaises(
            ScriptExecutionException
        ):

            self.engine.execute(
                "invalid(customer_name)"
            )

    def test_empty_script(self):

        with self.assertRaises(
            ScriptExecutionException
        ):

            self.engine.execute("")

    def test_invalid_syntax(self):

        with self.assertRaises(
            ScriptExecutionException
        ):

            self.engine.execute(
                "uppercase"
            )

    def test_missing_variable(self):

        result = self.engine.execute(
            "uppercase(unknown_variable)"
        )

        self.assertEqual(
            result,
            "UNKNOWN_VARIABLE",
        )