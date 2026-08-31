# One UCH Pilot Runtime Topology

This directory defines the reference process topology for the
One UCH real-user pilot.

The reference deployment assumes a systemd-based Linux host
with Nginx terminating HTTPS. A different hosting platform may
be used only if it preserves the same process boundaries and
security properties.


## Required process topology

Public traffic must terminate at an HTTPS reverse proxy.

The Django application itself runs through Daphne ASGI on:

    127.0.0.1:8000

Daphne must not be exposed directly to the public Internet.

The required long-running application processes are:

    oneuch-asgi
    oneuch-celery-worker
    oneuch-celery-beat

Redis must be reachable by:

    Celery worker
    Celery beat
    Django Channels
    synchronization locks

PostgreSQL is the pilot database.


## Important scheduler rule

Run exactly ONE Celery Beat process.

Multiple Beat instances can enqueue duplicate scheduled work,
including mailbox synchronization and intelligence jobs.


## Reference filesystem

The service templates assume:

    /opt/oneuch
        backend/
        frontend/

Python virtual environment:

    /opt/oneuch/backend/venv

Backend environment:

    /opt/oneuch/backend/.env

Service account:

    oneuch


## Before starting application services

From:

    /opt/oneuch/backend

run:

    ./venv/bin/python manage.py validate_pilot_environment
    ./venv/bin/python manage.py migrate
    ./venv/bin/python manage.py collectstatic --noinput
    ./venv/bin/python manage.py check

The pilot environment validator must pass before any One UCH
application service starts.


## Install systemd units

Copy:

    deployment/pilot/systemd/oneuch-asgi.service
    deployment/pilot/systemd/oneuch-celery-worker.service
    deployment/pilot/systemd/oneuch-celery-beat.service

to:

    /etc/systemd/system/

Then:

    sudo systemctl daemon-reload

    sudo systemctl enable oneuch-asgi
    sudo systemctl enable oneuch-celery-worker
    sudo systemctl enable oneuch-celery-beat


## Start order

Confirm PostgreSQL and Redis are reachable first.

Then:

    sudo systemctl start oneuch-asgi
    sudo systemctl start oneuch-celery-worker
    sudo systemctl start oneuch-celery-beat


## Verify process state

Run:

    sudo systemctl status oneuch-asgi
    sudo systemctl status oneuch-celery-worker
    sudo systemctl status oneuch-celery-beat

and:

    sudo journalctl -u oneuch-asgi -n 100 --no-pager
    sudo journalctl -u oneuch-celery-worker -n 100 --no-pager
    sudo journalctl -u oneuch-celery-beat -n 100 --no-pager


## Reverse proxy

Use:

    deployment/pilot/nginx/oneuch-api.conf.example

as the reference backend proxy configuration.

Replace:

    api.oneuch.example

and the certificate paths with the real pilot values.

Before reload:

    sudo nginx -t

Then:

    sudo systemctl reload nginx


## WebSocket requirement

The reverse proxy must preserve:

    Upgrade
    Connection
    Sec-WebSocket-Protocol

The Sec-WebSocket-Protocol forwarding is required by the
MVP-07.4C WebSocket authentication transport.


## HTTPS forwarding requirement

Nginx sends:

    X-Forwarded-Proto: https

Django already trusts this through:

    SECURE_PROXY_SSL_HEADER =
        ("HTTP_X_FORWARDED_PROTO", "https")


## Frontend

Build the frontend using the pilot build environment:

    frontend/.env.pilot.example

Vite variables are embedded at build time.

The final deployed frontend must use:

    https://

for API traffic and:

    wss://

for WebSocket traffic.


## Rollback principle

Application code rollback and database rollback are separate
operations.

Do not reverse migrations automatically during an application
rollback unless the specific migration has been reviewed as
safe to reverse.

For a code-only rollback:

    git checkout <previous-known-good-commit>

then rebuild/restart only the affected application processes.


## Pilot release rule

Do not expose pilot users until the final MVP-07.5 deployment
security gate has passed on the actual pilot host.

## Final pilot security gate

After the pilot environment is configured, PostgreSQL and
Redis are reachable, migrations are applied, and static files
have been collected, run:

    cd /opt/oneuch/backend

    ./venv/bin/python manage.py verify_pilot_release

The command must end with:

    PASS - One UCH pilot release security gate is green.

Do not expose real pilot users if this command fails.


The final gate verifies:

    pilot environment policy
    Django deployment security checks
    PostgreSQL runtime connectivity
    unapplied migration state
    Redis connectivity
    Celery / Channels Redis wiring
    ASGI runtime configuration
    django-celery-beat scheduler configuration
    collected static assets


After the application processes start, also verify:

    sudo systemctl is-active oneuch-asgi
    sudo systemctl is-active oneuch-celery-worker
    sudo systemctl is-active oneuch-celery-beat

and validate Nginx before reload:

    sudo nginx -t


Exactly one Celery Beat service must be active.


The release gate does not replace connector end-to-end testing.
Real Gmail, Microsoft and IMAP/SMTP pilot smoke tests belong to
the later real-user pilot release gate.
