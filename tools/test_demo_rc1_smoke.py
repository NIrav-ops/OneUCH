from pathlib import Path
import importlib.util
import sqlite3
import tempfile
import unittest


MODULE_PATH = (
    Path(__file__)
    .resolve()
    .with_name(
        "demo_rc1_smoke.py"
    )
)


SPEC = (
    importlib.util
    .spec_from_file_location(
        "demo_rc1_smoke",
        MODULE_PATH,
    )
)


smoke = (
    importlib.util
    .module_from_spec(
        SPEC
    )
)


SPEC.loader.exec_module(
    smoke
)


class DemoRC1SmokeToolTests(
    unittest.TestCase
):

    def setUp(
        self,
    ):
        smoke.DEMO_ROOT.mkdir(
            parents=True,
            exist_ok=True,
        )


    def test_protected_main_cannot_be_smoke_target(
        self,
    ):
        with self.assertRaises(
            smoke.DemoSmokeError
        ):

            smoke.resolve_smoke_target(
                smoke.PROTECTED_DB
            )


    def test_canonical_demo_cannot_be_smoke_target(
        self,
    ):
        with self.assertRaises(
            smoke.DemoSmokeError
        ):

            smoke.resolve_smoke_target(
                smoke.CANONICAL_DEMO_DB
            )


    def test_smoke_target_cannot_escape_demo_root(
        self,
    ):
        outside = (
            smoke.ROOT
            / "outside-smoke.sqlite3"
        )


        with self.assertRaises(
            smoke.DemoSmokeError
        ):

            smoke.resolve_smoke_target(
                outside
            )


    def test_runtime_environment_targets_smoke_and_enables_browser_session(
        self,
    ):
        target = (
            smoke.DEMO_ROOT
            / "environment-test.sqlite3"
        )


        environment = (
            smoke.build_runtime_environment(
                target,
                base_environment={
                    "KEEP_ME":
                        "yes",
                },
            )
        )


        self.assertEqual(
            environment[
                "DJANGO_DB_ENGINE"
            ],
            "sqlite",
        )

        self.assertEqual(
            Path(
                environment[
                    "ONEUCH_SQLITE_PATH"
                ]
            ).resolve(),
            target.resolve(),
        )

        self.assertEqual(
            environment[
                "AUTH_BROWSER_SESSION_ENABLED"
            ],
            "true",
        )

        self.assertEqual(
            environment[
                "DJANGO_DEBUG"
            ],
            "true",
        )

        self.assertEqual(
            environment[
                "KEEP_ME"
            ],
            "yes",
        )


    def test_demo_endpoint_inventory_is_read_only_surface(
        self,
    ):
        paths = {
            path

            for _label, path
            in smoke.READ_ONLY_DEMO_ENDPOINTS
        }


        expected = {
            "/api/dashboard/",
            "/api/inbox/unified/?page=1",
            (
                "/api/inbox/"
                "unified-conversations/"
                "?folder=inbox&page=1&page_size=5"
            ),
            "/api/email/email-accounts/",
            "/api/inbox/sync-status/",
            "/api/actions/",
            "/api/approvals/",
            "/api/my-work/",
            "/api/notifications/",
            "/api/search/?q=",
            "/api/workflow/definitions/",
        }


        self.assertEqual(
            paths,
            expected,
        )


    def test_canonical_copy_preserves_source_hash_and_rows(
        self,
    ):
        with tempfile.TemporaryDirectory() as temp:

            source = (
                Path(temp)
                / "canonical.sqlite3"
            )


            target = (
                smoke.DEMO_ROOT
                / "unit-smoke-copy.sqlite3"
            )


            if target.exists():
                target.unlink()


            connection = sqlite3.connect(
                str(
                    source
                )
            )


            try:

                connection.execute(
                    """
                    CREATE TABLE sample (
                        id INTEGER PRIMARY KEY,
                        value TEXT NOT NULL
                    )
                    """
                )

                connection.execute(
                    """
                    INSERT INTO sample(value)
                    VALUES ('one'), ('two')
                    """
                )

                connection.commit()

            finally:

                connection.close()


            source_hash = (
                smoke.sha256_file(
                    source
                )
            )


            original_canonical = (
                smoke.CANONICAL_DEMO_DB
            )

            original_verify = (
                smoke.verify_canonical_demo
            )


            try:

                smoke.CANONICAL_DEMO_DB = (
                    source
                )


                smoke.verify_canonical_demo = (
                    lambda path=None:
                        source.resolve()
                )


                smoke.copy_canonical_to_smoke(
                    target,
                    replace=True,
                )


            finally:

                smoke.CANONICAL_DEMO_DB = (
                    original_canonical
                )

                smoke.verify_canonical_demo = (
                    original_verify
                )


            self.assertEqual(
                smoke.sha256_file(
                    source
                ),
                source_hash,
            )


            connection = sqlite3.connect(
                str(
                    target
                )
            )


            try:

                count = int(
                    connection.execute(
                        "SELECT COUNT(*) FROM sample"
                    ).fetchone()[0]
                )

            finally:

                connection.close()


            self.assertEqual(
                count,
                2,
            )


            if target.exists():
                target.unlink()


if __name__ == "__main__":
    unittest.main()
