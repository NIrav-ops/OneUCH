from pathlib import Path
import importlib.util
import unittest


MODULE_PATH = (
    Path(__file__)
    .resolve()
    .with_name(
        "demo_rc1_story.py"
    )
)


SPEC = (
    importlib.util
    .spec_from_file_location(
        "demo_rc1_story",
        MODULE_PATH,
    )
)


story = (
    importlib.util
    .module_from_spec(
        SPEC
    )
)


SPEC.loader.exec_module(
    story
)


class DemoRC1StoryFoundationTests(
    unittest.TestCase
):

    def test_protected_main_cannot_be_story_target(
        self,
    ):
        with self.assertRaises(
            story.smoke.DemoSmokeError
        ):

            story.resolve_story_target(
                story.PROTECTED_DB
            )


    def test_canonical_demo_cannot_be_story_target(
        self,
    ):
        with self.assertRaises(
            story.smoke.DemoSmokeError
        ):

            story.resolve_story_target(
                story.CANONICAL_DEMO_DB
            )


    def test_g3_smoke_database_cannot_be_story_target(
        self,
    ):
        with self.assertRaises(
            story.DemoStoryError
        ):

            story.resolve_story_target(
                story.smoke.DEFAULT_SMOKE_DB
            )


    def test_story_target_must_remain_inside_demo_root(
        self,
    ):
        outside = (
            story.ROOT
            / "outside-story.sqlite3"
        )


        with self.assertRaises(
            story.smoke.DemoSmokeError
        ):

            story.resolve_story_target(
                outside
            )


    def test_story_fixture_count_contract_is_exact(
        self,
    ):
        self.assertEqual(
            story.EXPECTED_STORY_COUNTS,
            {
                "actions":
                    2,

                "approvals":
                    2,

                "workflows":
                    1,

                "workflow_nodes":
                    4,

                "workflow_transitions":
                    3,

                "my_work":
                    4,
            },
        )


    def test_workflow_graph_is_governed_without_ai_node(
        self,
    ):
        self.assertEqual(
            story.EXPECTED_WORKFLOW_NODE_TYPES,
            {
                "start",
                "approval",
                "action",
                "end",
            },
        )


        self.assertNotIn(
            "ai",
            story.EXPECTED_WORKFLOW_NODE_TYPES,
        )


    def test_story_read_surface_is_exact(
        self,
    ):
        self.assertEqual(
            story.STORY_READ_ENDPOINTS,
            {
                "actions":
                    "/api/actions/",

                "approvals":
                    "/api/approvals/",

                "my_work":
                    "/api/my-work/",

                "workflows":
                    "/api/workflow/definitions/",

                "dashboard":
                    "/api/dashboard/",

                "inbox":
                    "/api/inbox/unified/?page=1",
            },
        )


if __name__ == "__main__":
    unittest.main()
