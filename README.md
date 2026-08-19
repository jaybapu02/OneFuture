# TrainerHub — Trainer Management & Session Tracking System

A production-ready Django web application for training organizations to manage
**trainers**, **timetables**, **class tasks**, and **post-class session reports**.

Trainers log in and instantly see today's classes, complete a class report in
about 30 seconds (students present + what was taught), assign themselves tasks,
and review their session history. Admins manage trainers, classes, subjects and
the weekly timetable, and monitor activity through dashboards and reports.

---

## Features

### For Trainers
- Secure login with role-based access (trainers only see their own data)
- Dashboard with greeting, today's summary, today's timetable and tasks
- **Today's timetable** with Upcoming / Current / Completed status (current class highlighted)
- **Weekly timetable** view with week navigation and today highlighted
- **Task management**: assign a task from any timetable entry (class, subject,
  date and times pre-filled), edit, delete, mark complete (one-click via HTMX)
- **Complete Session** workflow: students present, what was taught, activity,
  optional notes — everything else is automatic
- **Automatic session numbers** — never entered manually
- Session history with filters (date range, class, subject) and pagination
- Session details and the ability to edit your own reports
- Personal report: totals, average attendance, classes handled, topics covered, sessions-over-time chart
- Profile and password change

### For Admins
- Admin dashboard: totals, today's activity, pending reports at a glance
- Manage trainers (create / edit / activate / deactivate)
- Manage classes (create / edit / activate / deactivate)
- Manage subjects (create / edit / activate / deactivate)
- Manage the timetable with **automatic conflict detection**
  (same trainer double-booked, or same class with two trainers at an overlapping time)
- View all sessions across all trainers with filters
- Organization report with charts (sessions by trainer, by class, over time)
- Full Django admin interface for power users

### Platform
- Mobile-first responsive UI (works at 320px → 1440px+)
- Professional light theme, Bootstrap 5, Bootstrap Icons, Chart.js (reports only), minimal HTMX
- Friendly 403 / 404 / 500 error pages and empty states everywhere
- PostgreSQL persistence, WhiteNoise static serving, Gunicorn, Render-ready

---

## Technology Stack

| Layer      | Technology                                        |
|------------|---------------------------------------------------|
| Backend    | Python 3.12, Django 5.1, Django ORM, PostgreSQL   |
| Frontend   | Django Templates, Bootstrap 5, vanilla JS, HTMX, Chart.js |
| Production | Gunicorn, WhiteNoise, PostgreSQL, Render          |

---

## Project Structure

```
OneFuture/
├── manage.py
├── requirements.txt
├── build.sh                  # Render build script
├── render.yaml               # Optional Render blueprint
├── .env.example              # Template for environment variables
├── .gitignore
├── .python-version
├── config/                   # Project settings package
│   ├── settings.py
│   ├── urls.py
│   ├── wsgi.py
│   └── context_processors.py
├── accounts/                 # Login/logout, password change, dashboards, permissions
├── trainers/                 # TrainerProfile model + admin CRUD + seed command
├── classes/                  # SchoolClass + Subject models + admin CRUD
├── timetable/                # Timetable model, conflict validation, weekly views
├── tasks/                    # Task model + trainer task management
├── sessions/                 # Session model, automatic numbering, reports
├── reports/                  # Trainer & admin report views with charts
├── templates/                # Base templates, partials, per-app pages
└── static/                   # Theme CSS + small JS
```

---

## Local Installation

### Prerequisites
- Python 3.12+
- PostgreSQL (local instance) — e.g. `brew install postgresql`, `apt install postgresql`, or the Windows installer

### 1. Clone & set up the environment

```bash
git clone <your-repo-url>
cd OneFuture
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Create the PostgreSQL database

```bash
createdb trainerhub
# or: CREATE DATABASE trainerhub; (psql)
```

### 3. Configure environment variables

```bash
cp .env.example .env
```

Edit `.env`:

```ini
SECRET_KEY=generate-a-long-random-secret
DEBUG=True
DATABASE_URL=postgres://postgres:postgres@localhost:5432/trainerhub
ALLOWED_HOSTS=localhost,127.0.0.1
```

Generate a secret key with:

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

### 4. Migrate & seed demo data

```bash
python manage.py migrate
python manage.py seed_demo_data
```

The seed command creates demo data (see below). It refuses to run when data
already exists, so it is safe to re-run.

### 5. Run

```bash
python manage.py runserver
```

Open http://127.0.0.1:8000

### Demo login credentials

| Role    | Username | Password   |
|---------|----------|------------|
| Admin   | `admin`  | `Admin@123` |
| Trainer | `jay`    | `Jay@123`  |
| Trainer | `priya`  | `Priya@123`|
| Trainer | `rahul`  | `Rahul@123`|

> Demo credentials are for local development only. Change them (or create new
> users) before any production deployment.

---

## Running Tests

```bash
python manage.py test
```

52 tests cover authentication, role permissions and data isolation, session
numbering (including a true 10-thread concurrency test), timetable conflict
detection, task CRUD, and session validation.

---

## Session Numbering Rule (documented business rule)

Session numbers are **always computed by the backend** — trainers never enter them.

- The next session number is `highest existing session number for (class, subject) + 1`.
- Numbering is **independent per class + subject** — never global.
- Deleting a session **does not renumber** history: if sessions 1–4 exist and
  session 3 is deleted, the next session is still **5**.
- Concurrency is safe: the class row is locked (`select_for_update`) inside a
  transaction while the number is computed, and the database constraint
  `(school_class, subject, session_number)` is a backstop against duplicates.

---

## Render Deployment

### Option A — Render Blueprint (recommended)

1. Push this repository to GitHub.
2. In Render: **New → Blueprint**, connect the repository.
3. `render.yaml` creates the PostgreSQL database and the web service
   automatically, wires `DATABASE_URL`, generates `SECRET_KEY` and sets
   `ALLOWED_HOSTS` / `CSRF_TRUSTED_ORIGINS` from the service URL.

### Option B — Manual web service

1. Create a **PostgreSQL** database on Render; copy its `Internal Database URL`.
2. Create a **Web Service** from the repo:
   - Runtime: **Python 3**
   - Build Command: `./build.sh`
   - Start Command: `gunicorn config.wsgi:application --bind 0.0.0.0:$PORT --workers 2 --timeout 60`
3. Environment variables:
   - `SECRET_KEY` — long random string (use Render's "Generate" button)
   - `DEBUG` → `False`
   - `DATABASE_URL` → your Render PostgreSQL connection string
   - `ALLOWED_HOSTS` → `your-app.onrender.com`
   - `CSRF_TRUSTED_ORIGINS` → `https://your-app.onrender.com`
   - `TIME_ZONE` (optional, default `Asia/Kolkata`)

`build.sh` installs dependencies, runs migrations and collects static files.
Static files are served by WhiteNoise — no separate static host needed.

### After deploying

Create an admin account on the production database:

```bash
# Run inside the Render shell
python manage.py createsuperuser
```

> **Never** run `seed_demo_data` in production unless you want demo accounts live.

---

## Configuration Reference

| Variable               | Default                             | Description                                  |
|------------------------|-------------------------------------|----------------------------------------------|
| `SECRET_KEY`           | dev-only value                      | Django secret key (required in production)   |
| `DEBUG`                | `True`                              | Set `False` in production                    |
| `DATABASE_URL`         | local PostgreSQL `trainerhub`       | Full PostgreSQL connection URL               |
| `ALLOWED_HOSTS`        | `*`                                 | Comma-separated hostnames                    |
| `CSRF_TRUSTED_ORIGINS` | empty                                | Comma-separated origins (incl. scheme)       |
| `TIME_ZONE`            | `Asia/Kolkata`                      | Organization timezone                        |
| `SITE_NAME`            | `TrainerHub`                        | Application display name (changeable)        |
| `SECURE_SSL_REDIRECT`  | `True` (prod)                       | Redirect HTTP → HTTPS                        |
| `SESSION_COOKIE_SECURE`| `True` (prod)                       | Secure session cookie                        |
| `CSRF_COOKIE_SECURE`   | `True` (prod)                       | Secure CSRF cookie                           |
| `SECURE_HSTS`          | `True` (prod)                       | HSTS headers                                 |

Secrets are never committed: `.env` is git-ignored and only `.env.example` is
checked in. In production `DEBUG=False` also enables secure cookies, HSTS and
the hashed-manifest static storage.

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `Database "trainerhub" does not exist` | Create it: `createdb trainerhub` |
| `Password authentication failed` | Fix `DATABASE_URL` credentials in `.env` |
| `Invalid HTTP_HOST header` | Add your hostname to `ALLOWED_HOSTS` |
| Missing static files in production | Run `python manage.py collectstatic --noinput` (build.sh does this) |
| `relation ... does not exist` | Run `python manage.py migrate` |
| Tests fail with `test_trainerhub` locked | `psql -c "DROP DATABASE IF EXISTS test_trainerhub WITH (FORCE);"` |
| Timezone shows wrong date | Set `TIME_ZONE` to your organization's timezone |

---

## Roadmap (future, not implemented)

Student-level attendance, parent accounts, notifications (email/WhatsApp),
performance analytics, Excel/PDF exports, monthly reports, REST API,
multi-organization / multi-branch support, lesson plans. The architecture
(separate apps, session numbering service, index-friendly models) is designed
so these can be added without rework.

---

## Screenshots

*Screenshots will be added here once captured.*

---

## License

Internal application — no license specified.