from django.test import TestCase

from workflow.services.executors.action import (
    ActionNodeExecutor,
)


class ActionExecutorTests(TestCase):

    def test_action_executor_creates_action(self):

        #
        # Use the existing workflow fixtures already
        # used by your workflow tests.
        #

        ...