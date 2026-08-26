# College Event Resource Allocation System

CampusFlow is a Flask application for managing college events and the shared resources they need: auditoriums, laboratories, projectors, microphones, cameras, and computers.

## Features

- Create, edit, cancel, filter, and view events with all required statuses.
- Add, edit, activate, and deactivate physical resources.
- Submit multi-resource requests within an event's time window.
- Approve or reject pending requests; approval creates allocations only when every requested resource is available.
- Prevent overlapping bookings on the backend. A booking ending at exactly the next booking's start is allowed.
- Validate active status, resource type, capacity, quantities, attendance, dates, and required fields.
- Release bookings when either an allocation or its event is cancelled.
- Search for active resources available in a selected date/time range.
- Suggest the first suitable available resource of the requested type when a request cannot be fully fulfilled.

## Install and run

Use Python 3.10 or later.

```bash
python -m venv .venv
.venv\\Scripts\\activate
pip install -r requirements.txt
flask --app run.py db upgrade
python run.py
```

Open `http://127.0.0.1:5000`. The SQLite database is created at `instance/app.db`.

For a non-development secret key, copy `.env.example` to `.env` and set a unique value.

## Database and migrations

The project uses Flask-SQLAlchemy and Flask-Migrate. Migration files are included in `migrations/`. Run `flask --app run.py db upgrade` after a fresh clone or whenever new migrations are added.

## Conflict detection

An allocation conflicts if both intervals overlap:

```text
existing.start < requested.end AND existing.end > requested.start
```

Only active allocations are considered. This deliberately permits back-to-back bookings: 10:00–14:00 followed by 14:00–16:00.

## Alternatives and allocation rule

Candidates are selected only when they are active, have the requested resource type, satisfy event attendance where capacity applies, and have no conflict in the requested time range. They are ordered by name so suggestions are predictable.

During approval, the application first finds a complete set of resources for every requirement. It creates allocations only after every requirement has passed. The database session is rolled back if anything fails, so a multi-resource request can never be partially allocated.

## Assumptions

- Capacity is only meaningful for space-like resources; blank capacity means no attendance constraint.
- A request must fall entirely within its event time.
- This assignment version has no authentication; resource administration and approval are available to the user running the app.
- Deploy only with `debug=False` and a secure environment-provided `SECRET_KEY`.
