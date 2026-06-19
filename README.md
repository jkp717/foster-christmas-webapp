# Holiday Hope Tree

A web application for the Holiday Hope Tree program, which connects sponsors
with foster children in Pulaski County so every child receives Christmas gifts.
The public site lets foster parents register children and lets community members
sign up to sponsor them; a secured admin area lets staff manage families,
sponsors, gifts, and gift fulfillment, and archive each season's data when it
ends.

Built with Flask, Flask-Admin, and SQLAlchemy on top of SQLite.

---

## Table of contents

- [Features](#features)
- [Tech stack](#tech-stack)
- [Project layout](#project-layout)
- [Getting started](#getting-started)
- [Configuration](#configuration)
- [Running the app](#running-the-app)
- [Admin area](#admin-area)
- [Command-line tools](#command-line-tools)
- [Seasonal archiving](#seasonal-archiving)
- [Tests](#tests)
- [Deployment](#deployment)

---

## Features

**Public site**

- Foster-parent and child registration, with a configurable signup window
  (open/closed plus an optional deadline).
- Sponsor registration and sponsor "wishlist" requests.
- On-site donations via PayPal and Authorize.Net (Accept Hosted).
- Informational pages (about, privacy, get-involved, gift pickup details).

**Admin area** (`/admin`, sign-in required)

- Manage Parents, Children, Gifts, Sponsors, Sponsor Requests, and Gift
  Fulfillment, plus the reference lists (gender, ethnicity, shoe/clothing sizes,
  DHS office, church) used by the registration forms.
- Site Settings screen controls the signup window and the gift-pickup
  date/time shown on the public site.
- Two shared logins: a full **admin** account, and an optional **read-only**
  account that can view everything and edit only comment/note fields (it cannot
  create or delete records).
- Read-only **archive** views for every prior season's data, listed alongside
  their live counterparts.

**Security**

- Login-gated admin (Flask-Login), CSRF protection (Flask-WTF), rate limiting on
  public forms and the login route (Flask-Limiter), parameterized SQL, an
  ownership check on child records, and hardened session cookies. See
  [`SECURITY_UPDATE.md`](SECURITY_UPDATE.md) for details.

---

## Tech stack

- **Python** / **Flask** (application framework)
- **Flask-Admin** (admin UI and the public registration views)
- **SQLAlchemy** + **Flask-SQLAlchemy** (ORM)
- **SQLite** (database)
- **Flask-Login**, **Flask-WTF**, **Flask-Limiter** (auth, CSRF, rate limiting)
- **WTForms** / **SQLAlchemy-Utils** (forms, phone-number field)
- **pytest** (tests)

---

## Project layout

```
foster-christmas-webapp/
├── cli.py                 # management commands + app entry point (FlaskGroup)
├── config.py              # Config/DevConfig/ProdConfig + reference-data seed
├── setup.py
├── requirements.txt       # application dependencies
├── requirements-dev.txt   # test-only dependencies (pytest)
├── .env.example           # copy to .env and fill in
├── SECURITY_UPDATE.md      # security/deployment notes
├── webapp/
│   ├── __init__.py        # create_app(): wiring, extensions, admin setup
│   ├── models.py          # SQLAlchemy models (live + *_archive tables)
│   ├── views.py           # public + admin views
│   ├── auth.py            # login, roles, access control
│   ├── authnet.py         # Authorize.Net Accept Hosted integration
│   ├── formfields.py      # custom form fields
│   ├── util.py            # formatters, filters, helpers
│   ├── config.py          # app-level constants + db_defaults
│   ├── static/            # css / assets
│   └── templates/         # Jinja templates (main/ and admin/)
└── tests/                 # pytest suite (see tests/README.md)
```

---

## Getting started

Requires Python 3.10+.

```bash
# 1. Clone, then create and activate a virtual environment
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Create your environment file
cp .env.example .env        # Windows: copy .env.example .env
#    then edit .env (at minimum set SECRET_KEY and an admin password hash)

# 4. Generate an admin password hash and paste it into .env
python cli.py create-admin-hash

# 5. Run
python cli.py run
```

On first run the app creates the SQLite database and seeds the reference tables
(gender, ethnicity, sizes, etc.) automatically. The site is then available at
http://127.0.0.1:5000/ and the admin at http://127.0.0.1:5000/admin.

---

## Configuration

All configuration comes from a git-ignored `.env` file in the project root,
loaded automatically at startup. Copy `.env.example` to `.env` and fill it in;
that file documents every setting. The essentials:

| Variable | Purpose |
|----------|---------|
| `SECRET_KEY` | Signs session cookies and CSRF tokens. **Required in production.** Generate with `python -c "import secrets; print(secrets.token_hex(32))"`. |
| `ADMIN_USERNAME` / `ADMIN_PASSWORD_HASH` | The admin login. Store only the hash (from `create-admin-hash`), never the plaintext. |
| `READONLY_USERNAME` / `READONLY_PASSWORD_HASH` | Optional read-only login. Leave the hash blank to disable. |
| `DATABASE_PATH` | Where the SQLite file lives. In production, point this **outside** the code checkout so deploys can't delete data. Defaults to `./instance/webapp2.db`. |
| `DATABASE_URL` | Advanced: a full SQLAlchemy URL that overrides `DATABASE_PATH` (e.g. Postgres). |
| `AUTHNET_*` | Authorize.Net Accept Hosted credentials and sandbox/live toggle. |
| `PAYPAL_*` | PayPal donation settings. |

`config.py` selects `DevConfig` by default and `ProdConfig` in production;
`ProdConfig` refuses to start without a real `SECRET_KEY`.

---

## Running the app

The project uses Flask's CLI via a `FlaskGroup` in `cli.py`, so management
commands and the dev server run through `python cli.py`:

```bash
python cli.py run            # development server
python cli.py run --help     # host/port/reload options
```

For production, serve the app with a WSGI server (e.g. gunicorn) and a reverse
proxy. See [Deployment](#deployment).

---

## Admin area

Visit `/admin` and sign in. The admin menu is organized by area:

- **Parents** — Current, Archive
- **Children** — Current, Archive, Gift Fulfillment, Gift Fulfillment Archive
- **Gifts** — Current, Archive
- **Sponsors** — Registered, Registered Archive, Requests, Requests Archive
- **Form Options** — the reference lists used by the registration forms
- **Settings** — Site Settings (signup window, gift-pickup date/time)

Archive views are **read-only for everyone**, including full admins. The
read-only login can view all of the above but may only edit comment/note
fields.

---

## Command-line tools

All commands run as `python cli.py <command>`:

| Command | What it does |
|---------|--------------|
| `run` | Start the development server. |
| `create-admin-hash` | Prompt for a password (hidden) and print a hash to paste into `.env`. Used for both the admin and read-only accounts. |
| `archive-season` | Archive the current season and wipe the live tables for a new season. See below. |
| `rebuild-archive-tables` | Drop and recreate the archive tables to match the current schema. **Only safe when the archive tables are empty** — it refuses if they contain data. |
| `db-create-all` | Create any missing tables (idempotent). |

Run any command with `--help` for its options.

---

## Seasonal archiving

At the end of a season, `archive-season` moves the current data into the
`*_archive` tables and clears the live tables so the next season starts fresh:

```bash
python cli.py archive-season          # shows counts, asks for confirmation
python cli.py archive-season --yes    # skip the confirmation prompt
```

What it does, in one transaction:

- Copies Sponsors, Parents, Children, Gifts, Gift Fulfillment, and Sponsor
  Requests into their archive tables, stamping an `archive_date` and a season
  `archive_year`.
- Remaps parent/sponsor foreign keys to the new archive records, and links
  archived gifts/fulfillment to the correct season's child via a composite
  `(child_id, archive_year)` key — so the same `child_id` can recur in
  different seasons without collision.
- Then deletes the live records. Reference tables and Site Settings are **never**
  touched.

> **Back up the database file before running `archive-season`.** It deletes the
> live season's data after copying it. Doing a trial run on a copy first is
> recommended.

---

## Tests

A pytest suite lives in `tests/` and runs against a throwaway temp-file SQLite
database (created and deleted per test, fully isolated).

```bash
pip install -r requirements-dev.txt
pytest                      # run everything
pytest -v                   # verbose
pytest -k archive           # only tests matching "archive"
```

Coverage spans models, authentication, security (role permissions, archive
read-only enforcement, CSRF, the child-record ownership check), public-page
rendering and the signup gate, admin/archive views, and the season-archive
routine. See [`tests/README.md`](tests/README.md) for the layout and how to add
tests for new models or endpoints.

---

## Deployment

Production runs on a Linux host with the database stored outside the code
checkout (so a redeploy can never delete it). The high-level steps:

1. Pull the latest code into the deploy directory.
2. Install/upgrade dependencies: `pip install -r requirements.txt`.
3. Ensure `.env` is present with a real `SECRET_KEY`, the admin password hash,
   and a `DATABASE_PATH` pointing outside the checkout.
4. Restart the WSGI service (e.g. gunicorn behind nginx).
5. After a schema change to the archive tables, run the appropriate migration
   step before using the affected admin views.

[`SECURITY_UPDATE.md`](SECURITY_UPDATE.md) covers the security-related
deployment steps (admin login setup, removing any old nginx basic-auth on
`/admin`, cookie settings) in more detail.

> Update database structure changes carefully: the app creates **missing**
> tables automatically but never alters existing ones, so column changes to
> tables that already hold data require a deliberate migration rather than a
> drop-and-recreate.
