from django.test import TestCase

from workflow.services.routing import RoutingEvaluator


class RuntimeRoutingTests(TestCase):

    def test_high_priority(self):

        self.assertTrue(
            RoutingEvaluator.evaluate(
                'priority == "high"',
                {
                    "priority": "high"
                }
            )
        )

    def test_default_route(self):

        self.assertTrue(
            RoutingEvaluator.evaluate(
                "",
                {}
            )
        )

    def test_amount_route(self):

        self.assertTrue(
            RoutingEvaluator.evaluate(
                "amount >= 1000",
                {
                    "amount": 2500
                }
            )
        )

    def test_department_route(self):

        self.assertTrue(
            RoutingEvaluator.evaluate(
                'department == "Finance"',
                {
                    "department": "Finance"
                }
            )
        )