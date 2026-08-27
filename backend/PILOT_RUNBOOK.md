# One UCH - Pilot Runbook

## Objective

Start One UCH in a controlled environment so selected users can validate the product as real end users.

Pilot users should be able to:

- Sign in
- Connect Gmail or Microsoft
- Synchronize communication
- Use the unified inbox
- Open conversations
- Reply and send messages
- Work with actions, approvals and follow-ups
- Validate communication intelligence

## 1. Backend Setup

Backend directory:

D:\UnifiedMessenger\unified-comm-hub\backend

Install dependencies:

.\venv\Scripts\python.exe -m pip install -r requirements.txt

Create .env from .env.example and populate required secrets.

Never commit the real .env file.

## 2. Database

Local development uses SQLite by default.

Pilot deployment should use PostgreSQL with:

DJANGO_DB_ENGINE=postgresql
DB_NAME=oneuch
DB_USER=oneuch
DB_PASSWORD=<secret>
DB_HOST=127.0.0.1
DB_PORT=5432

Apply migrations:

.\venv\Scripts\python.exe manage.py migrate

Verify:

.\venv\Scripts\python.exe manage.py check

## 3. Redis

Configured through:

REDIS_URL=redis://127.0.0.1:6379/0

## 4. Backend API

Terminal 1:

.\venv\Scripts\python.exe manage.py runserver

Development URL:

http://127.0.0.1:8000/

## 5. Celery Worker

Terminal 2:

.\venv\Scripts\celery.exe -A backend worker -l info --pool=solo

Verify:

.\venv\Scripts\celery.exe -A backend inspect ping

Expected: pong

## 6. Celery Beat

Terminal 3:

.\venv\Scripts\celery.exe -A backend beat -l info

Scheduled responsibilities:

- Communication synchronization every 5 minutes
- OAuth token refresh every 10 minutes
- Overdue work scanning hourly
- Escalation processing hourly

## 7. Frontend

Frontend directory:

D:\UnifiedMessenger\unified-comm-hub\frontend

Install dependencies:

npm install

Start development frontend:

npm run dev

Verify production build:

npm run build

## 8. Platform Health

Authenticated endpoint:

/api/platform/health/

Expected dependencies:

- database = Healthy
- redis = Healthy

## 9. End-User Acceptance Journey

A pilot user must be able to:

1. Sign in
2. Reach the dashboard
3. Connect Gmail or Microsoft
4. Complete OAuth
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

## 10. Pilot Feedback

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

The goal of the pilot is product validation, not feature completeness.
