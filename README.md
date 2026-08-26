# CampusFlow — College Event Resource Allocation System

CampusFlow is a web application for coordinating college events and the shared resources that support them. Built with Flask, SQLAlchemy, SQLite, Jinja2, and Tailwind CSS, it helps a college manage venues and equipment such as auditoriums, laboratories, projectors, microphones, cameras, and computers without double booking.

The project focuses on reliable backend validation, clear allocation decisions, and atomic database transactions rather than complex user-interface features.

---

## Key Features

### Event management

- Create, view, edit, cancel, and filter events by status or date.
- Capture organizer, expected attendance, start/end date and time, and lifecycle status.
- Validate required fields, positive attendance, and valid event time ranges.
- Cancelling an event releases its active resource allocations and cancels any pending requests linked to it.

### Resource management

- Add and edit resources by name, type, optional capacity, and active status.
- Activate or deactivate resources without deleting historical allocation data.
- Exclude inactive resources from all availability and allocation decisions.

### Resource requests and approval

- Request one or more resource types and quantities for a selected event.
- Require request times to fall within the event schedule.
- Review each request as **Pending**, then approve and allocate it or reject it.
- Cancel allocated requests to immediately release the reserved resources.

### Availability, suitability, and conflicts

- Search active resources available during a selected time window and optionally filter by type.
- Validate resource type and attendance capacity before allocation.
- Prevent overlapping allocations on the backend while permitting back-to-back bookings.
- Suggest a suitable available alternative when a requested resource type cannot be fully allocated.

### Atomic allocation

Multi-resource requests use a single database transaction. The system identifies every required resource before creating any allocation. If even one requirement cannot be fulfilled, the transaction rolls back and no partial booking is created.

---

## Technology Stack

| Layer | Technology |
| --- | --- |
| Backend | Python 3.10+, Flask |
| Database | SQLite, SQLAlchemy, Flask-Migrate |
| Templates | HTML, Jinja2 |
| Styling | Tailwind CSS |
| Client-side behavior | Basic JavaScript |
| Version control | Git and GitHub |

---

## Installation and Local Setup

### Prerequisites

- Python 3.10 or later
- Git (optional, for cloning and version control)

### Run locally

1. Clone the repository and enter the project folder.

   ```bash
   git clone <repository-url>
   cd college-event-resource-system
   ```

2. Create and activate a virtual environment.

   ```powershell
   python -m venv venv
   .\venv\Scripts\Activate.ps1
   ```

   On macOS/Linux:

   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. Install dependencies.

   ```bash
   pip install -r requirements.txt
   ```

4. Apply database migrations.

   ```bash
   flask --app run.py db upgrade
   ```

5. Start the application.

   ```bash
   python run.py
   ```

6. Open `http://127.0.0.1:5000` in a browser.

The SQLite database is stored at `instance/app.db`. For a non-development secret key, copy `.env.example` to `.env` and replace the example value.

---

## How Conflict Detection Works

The application checks the `allocations` table on the backend before creating an active allocation. Two time ranges conflict only when both conditions are true:

```text
existing.start_datetime < requested.end_datetime
AND
existing.end_datetime > requested.start_datetime
```

This uses strict comparisons, so adjacent bookings are supported:

| Existing allocation | New request | Result |
| --- | --- | --- |
| 10:00 AM – 2:00 PM | 12:00 PM – 4:00 PM | Rejected: overlaps |
| 10:00 AM – 2:00 PM | 2:00 PM – 4:00 PM | Allowed: back-to-back |

Only allocations with an **Active** status are considered. Cancelled allocations remain in the database for record keeping but no longer block a resource.

---

## How Alternatives Are Selected

When a resource requirement cannot be fulfilled, CampusFlow looks for candidates that meet all of these conditions:

1. The resource is active.
2. Its type matches the requested type.
3. Its capacity is sufficient for the event when capacity applies.
4. It has no active overlapping allocation in the requested time range.

Candidates are ordered by resource name to keep suggestions predictable. The system presents a suitable alternative in the approval feedback when one is available.

---

## Design Decisions and Assumptions

- Each resource record represents one physical item or venue. Requesting a quantity of two therefore requires two suitable resource records.
- Capacity is used for space-like resources such as auditoriums and laboratories. A blank capacity means the resource has no attendance limit.
- All date/time values are handled as local campus time.
- There is no authentication in this assignment version; the same interface is used for organizers and administrators.
- Events, requests, and allocations are cancelled by status rather than deleted, preserving an audit trail.

---

## Project Structure

```text
college-event-resource-system/
├── app/
│   ├── __init__.py                 # Application factory and error handlers
│   ├── constants.py                # Resource type choices
│   ├── extensions.py               # SQLAlchemy and migration setup
│   ├── models/                     # Event, resource, request, and allocation models
│   ├── routes/
│   │   ├── dashboard.py            # Dashboard summary
│   │   ├── events.py               # Event management and cancellation
│   │   ├── resources.py            # Resource management and availability search
│   │   └── requests.py             # Requests, approval, conflicts, and allocations
│   └── templates/                  # Jinja2 pages styled with Tailwind CSS
├── migrations/                     # Flask-Migrate database migrations
├── .env.example                    # Environment variable example
├── requirements.txt                # Python dependencies
├── run.py                          # Application entry point
└── README.md
```

---

## License

Created for the College Event Resource Allocation System technical assignment.
