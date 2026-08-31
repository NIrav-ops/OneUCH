from pathlib import (
    Path,
)

from django.test import (
    SimpleTestCase,
)


REPO_ROOT = (
    Path(__file__)
    .resolve()
    .parents[2]
)

PILOT_ROOT = (
    REPO_ROOT
    / "deployment"
    / "pilot"
)

SYSTEMD_ROOT = (
    PILOT_ROOT
    / "systemd"
)

NGINX_ROOT = (
    PILOT_ROOT
    / "nginx"
)


class PilotProcessTopologyTests(
    SimpleTestCase
):

    def read(
        self,
        path,
    ):
        return path.read_text(
            encoding="utf-8"
        )


    def test_asgi_service_uses_daphne_loopback_and_validator(
        self,
    ):
        content = self.read(
            SYSTEMD_ROOT
            / "oneuch-asgi.service"
        )

        self.assertIn(
            "validate_pilot_environment",
            content,
        )

        self.assertIn(
            "/daphne",
            content,
        )

        self.assertIn(
            "-b 127.0.0.1",
            content,
        )

        self.assertIn(
            "-p 8000",
            content,
        )

        self.assertIn(
            "backend.asgi:application",
            content,
        )

        self.assertNotIn(
            "runserver",
            content,
        )


    def test_worker_is_separate_prefork_celery_process(
        self,
    ):
        content = self.read(
            SYSTEMD_ROOT
            / "oneuch-celery-worker.service"
        )

        self.assertIn(
            "validate_pilot_environment",
            content,
        )

        self.assertIn(
            "/celery",
            content,
        )

        self.assertIn(
            "-A backend",
            content,
        )

        self.assertIn(
            "worker",
            content,
        )

        self.assertIn(
            "--pool=prefork",
            content,
        )

        self.assertNotIn(
            " beat ",
            content,
        )


    def test_beat_is_dedicated_database_scheduler_process(
        self,
    ):
        content = self.read(
            SYSTEMD_ROOT
            / "oneuch-celery-beat.service"
        )

        self.assertIn(
            "validate_pilot_environment",
            content,
        )

        self.assertIn(
            "-A backend",
            content,
        )

        self.assertIn(
            "beat",
            content,
        )

        self.assertIn(
            "django_celery_beat.schedulers:"
            "DatabaseScheduler",
            content,
        )

        self.assertNotIn(
            "worker",
            content,
        )


    def test_nginx_terminates_https_and_preserves_websocket_protocol(
        self,
    ):
        content = self.read(
            NGINX_ROOT
            / "oneuch-api.conf.example"
        )

        self.assertIn(
            "listen 443 ssl",
            content,
        )

        self.assertIn(
            "server 127.0.0.1:8000",
            content,
        )

        self.assertIn(
            "location /ws/",
            content,
        )

        self.assertIn(
            "proxy_set_header Upgrade",
            content,
        )

        self.assertIn(
            "proxy_set_header Connection",
            content,
        )

        self.assertIn(
            "proxy_set_header Sec-WebSocket-Protocol",
            content,
        )

        self.assertIn(
            "X-Forwarded-Proto https",
            content,
        )


    def test_runbook_requires_single_beat_and_pilot_validation(
        self,
    ):
        content = self.read(
            PILOT_ROOT
            / "README.md"
        )

        self.assertIn(
            "exactly ONE Celery Beat",
            content,
        )

        self.assertIn(
            "validate_pilot_environment",
            content,
        )

        self.assertIn(
            "Daphne",
            content,
        )

        self.assertIn(
            "PostgreSQL",
            content,
        )

        self.assertIn(
            "Redis",
            content,
        )

        self.assertIn(
            "Sec-WebSocket-Protocol",
            content,
        )
