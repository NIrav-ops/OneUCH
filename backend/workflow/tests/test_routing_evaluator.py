from django.test import SimpleTestCase

from workflow.services.routing import RoutingEvaluator


class RoutingEvaluatorTests(SimpleTestCase):

    def test_equal(self):

        self.assertTrue(
            RoutingEvaluator.evaluate(
                'priority == "high"',
                {
                    "priority": "high",
                },
            )
        )

    def test_not_equal(self):

        self.assertFalse(
            RoutingEvaluator.evaluate(
                'priority == "low"',
                {
                    "priority": "high",
                },
            )
        )

    def test_numeric(self):

        self.assertTrue(
            RoutingEvaluator.evaluate(
                "amount > 100",
                {
                    "amount": 500,
                },
            )
        )

    def test_boolean(self):

        self.assertTrue(
            RoutingEvaluator.evaluate(
                "approved == true",
                {
                    "approved": True,
                },
            )
        )

    def test_and(self):

        self.assertTrue(
            RoutingEvaluator.evaluate(
                'priority == "high" AND amount > 100',
                {
                    "priority": "high",
                    "amount": 1000,
                },
            )
        )

    def test_in(self):

        self.assertTrue(
            RoutingEvaluator.evaluate(
                'department in ["Finance","IT"]',
                {
                    "department": "Finance",
                },
            )
        )

    def test_empty_condition(self):

        self.assertTrue(
            RoutingEvaluator.evaluate(
                "",
                {},
            )
        )