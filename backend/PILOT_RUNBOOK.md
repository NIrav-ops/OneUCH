# One UCH - Pilot Runbook

## Objective

Start One UCH in a controlled pilot environment so selected
users can validate the product as real end users.

The goal of the pilot is product validation, not feature
completeness.

## 1. Production Pilot Topology

The authoritative hardened deployment topology is:

deployment/pilot/README.md

The pilot must use the deployment configuration defined there,
including:

- Nginx HTTPS termination
- Daphne ASGI
- PostgreSQL
- Redis
- a dedicated Celery worker
- exactly one Celery Beat process
- WebSocket proxy forwarding
- systemd process isolation

Do not use Django `runserver` as the pilot application server.

## 2. Backend Environment

Backend directory:

/opt/oneuch/backend

Create the pilot environment from:

backend/.env.pilot.example

Do not promote local-development defaults from `.env.example`.

Never commit the real `.env` file.

Install backend dependencies:

./venv/bin/python -m pip install -r requirements.txt

## 3. Database

Pilot deployment requires PostgreSQL.

Apply migrations:

./venv/bin/python manage.py migrate

Verify migration state:

./venv/bin/python manage.py makemigrations --check --dry-run

## 4. Static Files

Before the release gate:

./venv/bin/python manage.py collectstatic --noinput

`STATIC_ROOT` must contain collected files.

## 5. Infrastructure Release Gate

On the actual pilot application host run:

./venv/bin/python manage.py validate_pilot_environment

Then run:

./venv/bin/python manage.py verify_pilot_release

The release gate validates the hardened configuration and
runtime dependencies including:

- Django deployment security
- PostgreSQL
- Redis
- migrations
- static files
- ASGI wiring
- Celery broker/result wiring
- Channels Redis wiring
- Celery Beat scheduler configuration

Do not expose the pilot to users if either command fails.

## 6. Frontend Pilot Build

Frontend directory:

/opt/oneuch/frontend

Start from:

frontend/.env.pilot.example

Replace example hostnames with the actual public HTTPS/WSS
pilot endpoints before building.

Install dependencies:

npm install

Verify the production bundle:

npm run build

Do not use a frontend bundle containing localhost API or
WebSocket endpoints for the pilot.

## 7. Platform Health

Authenticated endpoint:

/api/platform/health/

Expected dependency state:

- database = Healthy
- redis = Healthy

A Degraded health result must be investigated before pilot
acceptance continues.

## 8. Pilot User Preparation

Create or select the pilot user.

The user must have:

- an active One UCH account
- membership in an active organization

The user then signs in through the real pilot frontend and
connects Gmail or Microsoft through the normal OAuth flow.

Do not place OAuth credentials or passwords in shell history,
scripts or source files.

## 9. Selected Pilot User Release Gate

After OAuth connection and the first mailbox synchronization,
run:

./venv/bin/python manage.py verify_pilot_user --email <pilot-user-email>

The selected-user gate requires:

- active user
- active organization membership
- active Gmail or Outlook account
- usable Google or Microsoft OAuth authorization
- at least one successful mailbox synchronization

No OAuth token value or mailbox content is printed by this
gate.

Do not continue real-user acceptance if this command fails.

## 10. End-User Acceptance Journey

The real pilot user must manually verify:

1. Sign in
2. Reach the dashboard
3. Connect Gmail or Microsoft
4. Complete the provider OAuth callback
5. Synchronize communication
6. View unified conversations
7. Open a conversation
8. Reply to a conversation
9. Compose and send a message
10. See extracted actions where applicable
11. See approvals and follow-ups where applicable
12. Complete or update work items
13. Log out and log back in
14. Retain synchronized state
15. Never access another organization's data
16. Receive understandable errors when something fails

Real Google/Microsoft authorization and message delivery must
be validated manually on the pilot host/account. Automated
tests must not pretend that mocked provider calls prove the
external provider journey.

## 11. Operational Observation

During pilot acceptance watch:

- structured One UCH runtime logs
- platform.health.checked events
- mailbox synchronization failures
- OAuth refresh/re-authentication state
- WebSocket connectivity
- worker and Beat process health

Never copy raw credentials, OAuth tokens, message bodies or
other sensitive communication content into issue reports.

## 12. Pilot Feedback

Capture:

- onboarding difficulty
- Gmail and Outlook connectivity
- sync reliability
- missing or duplicate messages
- inbox usability
- action extraction accuracy
- approval accuracy
- follow-up usefulness
- UI friction
- performance
- errors encountered
- expected features users could not find

For every blocking pilot issue capture the time, affected user,
provider and correlation/request identifier where available.
