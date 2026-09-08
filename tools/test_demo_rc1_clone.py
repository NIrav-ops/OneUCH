from pathlib import Path
import importlib.util
import sqlite3
import tempfile
import unittest


MODULE_PATH = (
    Path(__file__)
    .resolve()
    .with_name(
        "demo_rc1_clone.py"
    )
)


SPEC = (
    importlib.util
    .spec_from_file_location(
        "demo_rc1_clone",
        MODULE_PATH,
    )
)


demo = (
    importlib.util
    .module_from_spec(
        SPEC
    )
)


SPEC.loader.exec_module(
    demo
)


class DemoRC1CloneFoundationTests(
    unittest.TestCase
):

    def setUp(
        self,
    ):
        demo.DEMO_ROOT.mkdir(
            parents=True,
            exist_ok=True,
        )


    def test_protected_main_cannot_be_demo_target(
        self,
    ):
        with self.assertRaises(
            demo.DemoCloneError
        ):

            demo.resolve_demo_target(
                demo.PROTECTED_DB
            )


    def test_target_must_remain_inside_demo_artifact_root(
        self,
    ):
        outside = (
            demo.ROOT
            / "outside-demo.sqlite3"
        )


        with self.assertRaises(
            demo.DemoCloneError
        ):

            demo.resolve_demo_target(
                outside
            )


    def test_backup_preserves_source_and_rows(
        self,
    ):
        with tempfile.TemporaryDirectory() as temp:

            source = (
                Path(temp)
                / "source.sqlite3"
            )

            target = (
                demo.DEMO_ROOT
                / "unit-backup.sqlite3"
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
                demo.sha256_file(
                    source
                )
            )


            original_protected = (
                demo.PROTECTED_DB
            )


            try:

                demo.PROTECTED_DB = (
                    source
                )

                demo.backup_sqlite(
                    source,
                    target,
                    replace=True,
                )

            finally:

                demo.PROTECTED_DB = (
                    original_protected
                )


            self.assertEqual(
                demo.sha256_file(
                    source
                ),
                source_hash,
            )


            target_connection = (
                sqlite3.connect(
                    str(
                        target
                    )
                )
            )


            try:

                count = (
                    target_connection
                    .execute(
                        "SELECT COUNT(*) FROM sample"
                    )
                    .fetchone()[0]
                )

            finally:

                target_connection.close()


            self.assertEqual(
                count,
                2,
            )


            if target.exists():
                target.unlink()


    def test_child_environments_enforce_migrate_before_enable(
        self,
    ):
        target = (
            demo.DEMO_ROOT
            / "environment-test.sqlite3"
        )


        migration_environment = (
            demo.build_clone_environment(
                target,
                browser_session_enabled=False,
                base_environment={
                    "KEEP_ME":
                        "yes",
                },
            )
        )


        runtime_environment = (
            demo.build_clone_environment(
                target,
                browser_session_enabled=True,
                base_environment={
                    "KEEP_ME":
                        "yes",
                },
            )
        )


        self.assertEqual(
            migration_environment[
                "DJANGO_DB_ENGINE"
            ],
            "sqlite",
        )

        self.assertEqual(
            Path(
                migration_environment[
                    "ONEUCH_SQLITE_PATH"
                ]
            ).resolve(),
            target.resolve(),
        )

        self.assertEqual(
            migration_environment[
                "AUTH_BROWSER_SESSION_ENABLED"
            ],
            "false",
        )

        self.assertEqual(
            runtime_environment[
                "AUTH_BROWSER_SESSION_ENABLED"
            ],
            "true",
        )

        self.assertEqual(
            runtime_environment[
                "CORS_ALLOW_CREDENTIALS"
            ],
            "true",
        )

        self.assertEqual(
            runtime_environment[
                "KEEP_ME"
            ],
            "yes",
        )


    def test_clone_contract_verifies_migrations_and_data(
        self,
    ):
        target = (
            demo.DEMO_ROOT
            / "contract-test.sqlite3"
        )


        if target.exists():
            target.unlink()


        connection = sqlite3.connect(
            str(
                target
            )
        )


        try:

            connection.execute(
                """
                CREATE TABLE django_migrations (
                    id INTEGER PRIMARY KEY,
                    app TEXT NOT NULL,
                    name TEXT NOT NULL,
                    applied TEXT
                )
                """
            )


            for migration in (
                demo.REQUIRED_ACCOUNTS_MIGRATIONS
            ):

                connection.execute(
                    """
                    INSERT INTO django_migrations(
                        app,
                        name,
                        applied
                    )
                    VALUES(
                        'accounts',
                        ?,
                        '2026-09-08'
                    )
                    """,
                    (
                        migration,
                    ),
                )


            for table in (
                demo.CORE_TABLES.values()
            ):

                connection.execute(
                    (
                        'CREATE TABLE "'
                        + table
                        + '" (id INTEGER PRIMARY KEY)'
                    )
                )

                connection.execute(
                    (
                        'INSERT INTO "'
                        + table
                        + '"(id) VALUES (1)'
                    )
                )


            connection.execute(
                """
                CREATE TABLE accounts_browsersession (
                    id INTEGER PRIMARY KEY
                )
                """
            )


            connection.commit()

        finally:

            connection.close()


        inventory = (
            demo.verify_clone_contract(
                target,
                expected_inventory={
                    label:
                        1

                    for label
                    in demo.CORE_TABLES
                },
            )
        )


        self.assertEqual(
            inventory[
                "messages"
            ],
            1,
        )


        if target.exists():
            target.unlink()


if __name__ == "__main__":
    unittest.main()
