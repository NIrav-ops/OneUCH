from django.test import TestCase

from workflow.services.builder.graph_validator import (
    WorkflowGraphValidator,
)


class WorkflowGraphValidatorTests(
    TestCase
):

    def setUp(self):

        self.validator = (
            WorkflowGraphValidator()
        )

        self.valid_graph = {

            "nodes": [
                {
                    "client_id": "node-1",
                    "name": "Start",
                    "node_type": "start",
                },
                {
                    "client_id": "node-2",
                    "name": "End",
                    "node_type": "end",
                },
            ],

            "transitions": [
                {
                    "source": "node-1",
                    "target": "node-2",
                }
            ],
        }

    def test_valid_graph(self):

        self.assertTrue(
            self.validator.validate(
                self.valid_graph
            )
        )

    def test_missing_nodes(self):

        graph = {
            "transitions": []
        }

        with self.assertRaises(
            ValueError
        ):

            self.validator.validate(
                graph
            )

    def test_empty_nodes(self):

        graph = {
            "nodes": [],
            "transitions": [],
        }

        with self.assertRaises(
            ValueError
        ):

            self.validator.validate(
                graph
            )

    def test_missing_transitions(self):

        graph = {
            "nodes": [
                {
                    "client_id": "node-1",
                    "name": "Start",
                    "node_type": "start",
                }
            ]
        }

        with self.assertRaises(
            ValueError
        ):

            self.validator.validate(
                graph
            )

    def test_duplicate_client_ids(self):

        graph = {
            "nodes": [
                {
                    "client_id": "node-1",
                    "name": "Start",
                    "node_type": "start",
                },
                {
                    "client_id": "node-1",
                    "name": "End",
                    "node_type": "end",
                },
            ],
            "transitions": [],
        }

        with self.assertRaises(
            ValueError
        ):

            self.validator.validate(
                graph
            )

    def test_invalid_node_type(self):

        graph = {
            "nodes": [
                {
                    "client_id": "node-1",
                    "name": "Invalid",
                    "node_type": "invalid",
                }
            ],
            "transitions": [],
        }

        with self.assertRaises(
            ValueError
        ):

            self.validator.validate(
                graph
            )

    def test_invalid_transition_source(self):

        graph = {
            "nodes": [
                {
                    "client_id": "node-1",
                    "name": "Start",
                    "node_type": "start",
                }
            ],
            "transitions": [
                {
                    "source": "missing",
                    "target": "node-1",
                }
            ],
        }

        with self.assertRaises(
            ValueError
        ):

            self.validator.validate(
                graph
            )

    def test_invalid_transition_target(self):

        graph = {
            "nodes": [
                {
                    "client_id": "node-1",
                    "name": "Start",
                    "node_type": "start",
                }
            ],
            "transitions": [
                {
                    "source": "node-1",
                    "target": "missing",
                }
            ],
        }

        with self.assertRaises(
            ValueError
        ):

            self.validator.validate(
                graph
            )