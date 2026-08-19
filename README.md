# OneFuture — Trainer Management & Session Tracking System

A Django web application for **OneFuture Foundation** trainers. Each trainer
belongs to **one school** and follows their school's **weekly timetable**
(the source of truth for regular classes). The trainer's dashboard derives
today's classes from the current day of week + the recurring timetable — no
daily manual assignment is needed.

Real setup (seeded): **BMC Bagurai School, Bhadrak** — trainer
**Jaychandra Dash**, Classes **3–8**, subject **Artificial Intelligence**, and
the actual 12-entry weekly timetable (Periods 4–7, Monday–Friday).

---

## Features

### For Trainers
- Secure login; trainers only ever see their own school's timetable and data
- **Today's Classes** on the dashboard — computed automatically from the
  recurring weekly timetable (e.g. Monday shows Class 7 · 12:30–1:15,
  Class 5 · 2:00–2:40, Class 8 · 3:20–4:00) plus any manual classes for today
- **My Weekly Timetable** — the actual period-grid format (Day × Period 4–7),
  responsive: table on desktop, vertical day cards on mobile
- **Upload Weekly Timetable** (.xlsx) with preview → confirm → import:
  - Parses cells like `7th — 12:30–1:15` into class, start and end time
  - The period number comes from the column header (`Period N` columns are
    detected dynamically)
  - Empty cells and `—` are ignored
  - No trainer name needed in the file — the timetable belongs to the
    logged-in trainer and their school
  - Re-importing **replaces** the weekly timetable without touching historical
    sessions, tasks or reports
- **Download Weekly Timetable Template** (.xlsx) matching the real structure,
  with an Instructions sheet
- **Assign Class** — one-off manual class for a specific date (labelled
  **Manual**); the recurring timetable is never modified
- **Delete rules**:
  - Manual class → deleted for that one date only
  - Recurring class → two explicit choices: *Remove for this date* (occurrence
    suppressed, weekly rule kept) or *Remove from weekly timetable* (confirmed
    before the recurring rule is deactivated)
- **Complete Session** — students present, what was taught, activity, notes;
  trainer, school, class, date, period and times are auto-filled; the
  **session number is computed by the backend** and never reset by timetable
  changes
- **Assign Task** from any class — class, date, period and times pre-filled
- Session history, personal report, profile, password change

### For Admins
- Admin dashboard with real totals and today's activity
- Manage schools, trainers (each assigned to exactly one school), classes,
  subjects and the timetable with automatic conflict detection
- View all sessions with filters; organization report with charts
- Full Django admin for power users

### Platform
- Mobile-first responsive UI (320px → 1440px+)
- PostgreSQL, WhiteNoise, Gunicorn, Render-ready

---

## Technology Stack

| Layer      | Technology                                        |
|------------|---------------------------------------------------|
| Backend    | Python 3.12, Django 5.1, Django ORM, PostgreSQL   |
| Excel      | openpyxl (import + template generation)           |
| Frontend   | Django Templates, Bootstrap 5, vanilla JS, HTMX, Chart.js |
| Production | Gunicorn, WhiteNoise, PostgreSQL, Render          |

---

## Local Installation

### Prerequisites
- Python 3.12+
- PostgreSQL (local instance)

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

### 4. Migrate & seed the actual data

```bash
python manage.py migrate
python manage.py seed_data
python manage.py import_august_data
```

`seed_data` loads only real data: the school (BMC Bagurai School), the trainer
(Jaychandra Dash), Classes 3–8, the Artificial Intelligence subject and the
actual 12-entry weekly timetable (Monday=3, Tuesday=2, Wednesday=3,
Thursday=2, Friday=2). **No mock tasks or sessions are created.** It refuses
to run when data already exists, so it is safe to re-run.

(`seed_demo_data` is kept as an alias of `seed_data`.)

`import_august_data` loads the real **August 2026 session records** from the
"August Month Details" monthly report (20 sessions: 10 class days across
Classes 3–8, with historical session numbers, student totals/present/absent
counts, lesson plans, location "Bhadrak" and timings preserved exactly as
written in the report). Office/NA rows never become sessions, multi-class
rows become one session per class, and the import is **idempotent** — it keys
records on (trainer, date, class, session number), never duplicates, and
never overwrites values edited manually after import.

### 5. Create an admin and run

```bash
python manage.py createsuperuser
python manage.py runserver
```

Open http://127.0.0.1:8000

| Role    | Username    | Password   |
|---------|-------------|------------|
| Admin   | (you create) | —         |
| Trainer | `jaychandra` | `Jay@123` |

> Local credentials only — change them before any production deployment.

---

## Running Tests

```bash
python manage.py test
```

110 tests cover authentication, role permissions and data isolation, session
numbering (including a true 10-thread concurrency test), timetable conflict
detection, task CRUD, session validation, the full weekly-timetable workflow:
Excel cell parsing, class/time extraction, empty-cell handling, per-day class
counts (3/2/3/2/2 = 12 total), today's classes, trainer data isolation, manual
assignment/deletion, recurring-delete safety, session survival across
timetable replacement, the absence of mock data, and the real August 2026
session import (20 sessions, NA rows skipped, per-class splitting, historical
numbers preserved, idempotent re-runs, monthly filtering and summary).

---

## Weekly Timetable (the source of truth)

The timetable is **recurring** — stored once per weekday/period, never one row
per week. Today's classes are:

```
Today's date → day of week → trainer's recurring timetable → today's classes
```

Actual weekly schedule (12 classes):

| Day       | P4            | P5            | P6            | P7            |
|-----------|---------------|---------------|---------------|---------------|
| Monday    | 7th 12:30–1:15 | —            | 5th 2:00–2:40 | 8th 3:20–4:00 |
| Tuesday   | —             | —             | 3rd 2:40–3:20 | 6th 3:20–4:00 |
| Wednesday | —             | 4th 2:00–2:40 | 8th 2:40–3:20 | 3rd 3:20–4:00 |
| Thursday  | —             | 7th 2:00–2:40 | —             | 5th 3:20–4:00 |
| Friday    | —             | —             | 4th 2:40–3:20 | 6th 3:20–4:00 |

Excel cells are written like `7th — 12:30–1:15`; separators `—`, `–`, `-`, `|`
are all accepted, and additional `Period N` columns are detected dynamically.

---

## Session Numbering Rule (documented business rule)

Session numbers are **always computed by the backend** — trainers never enter them.

- The next session number is `highest existing session number for (class, subject) + 1`.
- Numbering is **independent per class + subject** — never global.
- Deleting a session **does not renumber** history: if sessions 1–4 exist and
  session 3 is deleted, the next session is still **5**.
- Replacing the weekly timetable **never resets** session numbers.
- Concurrency is safe: the class row is locked (`select_for_update`) inside a
  transaction while the number is computed, which serializes number generation
  for that class.
- **Historical August 2026 records keep the session numbers written in the
  monthly report**, even when those numbers are non-sequential or repeated
  per class (there is deliberately no unique database constraint on
  `(school_class, subject, session_number)`). New sessions after the import
  continue from `highest number + 1`.

---

## Render Deployment

### Option A — Render Blueprint (recommended)

1. Push this repository to GitHub.
2. In Render: **New → Blueprint**, connect the repository.
3. `render.yaml` creates the PostgreSQL database and the web service
   automatically, wires `DATABASE_URL`, generates `SECRET_KEY` and sets
   `ALLOWED_HOSTS` / `CSRF_TRUSTED_ORIGINS`.

### Option B — Manual web service

1. Create a **PostgreSQL** database on Render; copy its `Internal Database URL`.
2. Create a **Web Service** from the repo:
   - Runtime: **Python 3**
   - Build Command: `./build.sh`
   - Start Command: `gunicorn config.wsgi:application --bind 0.0.0.0:$PORT --workers 2 --timeout 60`
3. Environment variables: `SECRET_KEY`, `DEBUG=False`, `DATABASE_URL`,
   `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`, `TIME_ZONE` (optional).

After deploying, run `python manage.py migrate` and `python manage.py seed_data`
on the production database, then create an admin account.

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
| `SITE_NAME`            | `OneFuture`                         | Application display name (changeable)        |

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `Database "trainerhub" does not exist` | Create it: `createdb trainerhub` |
| `Password authentication failed` | Fix `DATABASE_URL` credentials in `.env` |
| `relation ... does not exist` | Run `python manage.py migrate` |
| Tests fail with `test_trainerhub` locked | `psql -c "DROP DATABASE IF EXISTS test_trainerhub WITH (FORCE);"` |
| Upload says "could not find the timetable structure" | The file needs a `Day` column and `Period N` headers (see template) |

---

## Roadmap (future, not implemented)

Student-level attendance, parent accounts, notifications (email/WhatsApp),
performance analytics, REST API, monthly reports, multi-school support for a
single trainer, lesson plans.
