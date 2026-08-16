from django.test import TestCase

from workflow.models import WorkflowTransition


class TransitionPriorityTests(TestCase):

    def test_default_priority(self):
        transition = WorkflowTransition(priority=100)
        self.assertEqual(transition.priority, 100)