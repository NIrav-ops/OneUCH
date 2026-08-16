from django.test import TestCase

from workflow.services.routing import RoutingEvaluator


class IntelligentRoutingTests(TestCase):

    def test_high_priority_route(self):

        variables = {
            "priority": "high",
        }

        self.assertTrue(
            RoutingEvaluator.evaluate(
                'priority == "high"',
                variables,
            )
        )

    def test_low_priority_route(self):

        variables = {
            "priority": "low",
        }

        self.assertTrue(
            RoutingEvaluator.evaluate(
                'priority == "low"',
                variables,
            )
        )

    def test_department_route(self):

        variables = {
            "department": "Finance",
        }

        self.assertTrue(
            RoutingEvaluator.evaluate(
                'department == "Finance"',
                variables,
            )
        )

    def test_amount_route(self):

        variables = {
            "amount": 20000,
        }

        self.assertTrue(
            RoutingEvaluator.evaluate(
                "amount >= 10000",
                variables,
            )
        )

    def test_default_route(self):

        self.assertTrue(
            RoutingEvaluator.evaluate(
                "",
                {},
            )
        )

    def test_boolean_route(self):

        variables = {
            "approved": True,
        }

        self.assertTrue(
            RoutingEvaluator.evaluate(
                "approved == true",
                variables,
            )
        )

    def test_and_route(self):

        variables = {
            "priority": "high",
            "amount": 9000,
        }

        self.assertTrue(
            RoutingEvaluator.evaluate(
                'priority == "high" AND amount > 5000',
                variables,
            )
        )

    def test_or_route(self):

        variables = {
            "department": "IT",
            "priority": "medium",
        }

        self.assertTrue(
            RoutingEvaluator.evaluate(
                'department == "Finance" OR department == "IT"',
                variables,
            )
        )

    def test_not_route(self):

        variables = {
            "approved": False,
        }

        self.assertTrue(
            RoutingEvaluator.evaluate(
                "NOT approved",
                variables,
            )
        )

    def test_in_route(self):

        variables = {
            "sender": "CEO",
        }

        self.assertTrue(
            RoutingEvaluator.evaluate(
                'sender in ["CEO","CFO"]',
                variables,
            )
        )