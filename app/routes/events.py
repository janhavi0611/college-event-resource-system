from datetime import datetime

from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
)

from app.extensions import db
from app.models import Event


events_bp = Blueprint("events", __name__, url_prefix="/events")


@events_bp.route("/")
def list_events():

    status = request.args.get("status", "").strip()
    date_value = request.args.get("date", "").strip()

    query = Event.query

    # Filter by status
    if status:
        query = query.filter_by(status=status)

    # Filter by date
    selected_date = None

    if date_value:

        try:
            selected_date = datetime.strptime(
                date_value,
                "%Y-%m-%d"
            ).date()

            start_of_day = datetime.combine(
                selected_date,
                datetime.min.time()
            )

            end_of_day = datetime.combine(
                selected_date,
                datetime.max.time()
            )

            query = query.filter(
                Event.start_datetime >= start_of_day,
                Event.start_datetime <= end_of_day
            )

        except ValueError:

            flash(
                "Invalid date filter.",
                "error"
            )

    # Get events
    events = query.order_by(
        Event.start_datetime.asc()
    ).all()

    return render_template(
        "events/list.html",
        events=events,
        selected_status=status,
        selected_date=date_value
    )


@events_bp.route("/create", methods=["GET", "POST"])
def create_event():

    if request.method == "POST":

        name = request.form.get("name", "").strip()
        organizer = request.form.get("organizer", "").strip()

        attendance_value = request.form.get(
            "expected_attendance",
            ""
        ).strip()

        start_value = request.form.get(
            "start_datetime",
            ""
        ).strip()

        end_value = request.form.get(
            "end_datetime",
            ""
        ).strip()

        if not name or not organizer:

            flash(
                "Event name and organizer are required.",
                "error"
            )

            return render_template(
                "events/create.html"
            )

        try:

            expected_attendance = int(
                attendance_value
            )

        except ValueError:

            flash(
                "Attendance must be a valid number.",
                "error"
            )

            return render_template(
                "events/create.html"
            )

        if expected_attendance <= 0:

            flash(
                "Expected attendance must be greater than zero.",
                "error"
            )

            return render_template(
                "events/create.html"
            )

        try:

            start_datetime = datetime.fromisoformat(
                start_value
            )

            end_datetime = datetime.fromisoformat(
                end_value
            )

        except ValueError:

            flash(
                "Please enter valid start and end dates.",
                "error"
            )

            return render_template(
                "events/create.html"
            )

        if end_datetime <= start_datetime:

            flash(
                "End date/time must be after start date/time.",
                "error"
            )

            return render_template(
                "events/create.html"
            )

        event = Event(
            name=name,
            organizer=organizer,
            expected_attendance=expected_attendance,
            start_datetime=start_datetime,
            end_datetime=end_datetime,
            status="Draft",
        )

        db.session.add(event)
        db.session.commit()

        flash(
            "Event created successfully.",
            "success"
        )

        return redirect(
            url_for("events.list_events")
        )

    return render_template(
        "events/create.html"
    )


@events_bp.route(
    "/<int:event_id>/edit",
    methods=["GET", "POST"]
)
def edit_event(event_id):

    event = db.get_or_404(
        Event,
        event_id
    )

    if request.method == "POST":

        name = request.form.get(
            "name",
            ""
        ).strip()

        organizer = request.form.get(
            "organizer",
            ""
        ).strip()

        attendance_value = request.form.get(
            "expected_attendance",
            ""
        ).strip()

        start_value = request.form.get(
            "start_datetime",
            ""
        ).strip()

        end_value = request.form.get(
            "end_datetime",
            ""
        ).strip()

        if not name or not organizer:

            flash(
                "Event name and organizer are required.",
                "error"
            )

            return render_template(
                "events/edit.html",
                event=event
            )

        try:

            expected_attendance = int(
                attendance_value
            )

        except ValueError:

            flash(
                "Attendance must be a valid number.",
                "error"
            )

            return render_template(
                "events/edit.html",
                event=event
            )

        if expected_attendance <= 0:

            flash(
                "Expected attendance must be greater than zero.",
                "error"
            )

            return render_template(
                "events/edit.html",
                event=event
            )

        try:

            start_datetime = datetime.fromisoformat(
                start_value
            )

            end_datetime = datetime.fromisoformat(
                end_value
            )

        except ValueError:

            flash(
                "Please enter valid start and end dates.",
                "error"
            )

            return render_template(
                "events/edit.html",
                event=event
            )

        if end_datetime <= start_datetime:

            flash(
                "End date/time must be after start date/time.",
                "error"
            )

            return render_template(
                "events/edit.html",
                event=event
            )

        event.name = name
        event.organizer = organizer
        event.expected_attendance = expected_attendance
        event.start_datetime = start_datetime
        event.end_datetime = end_datetime

        db.session.commit()

        flash(
            "Event updated successfully.",
            "success"
        )

        return redirect(
            url_for("events.list_events")
        )

    return render_template(
        "events/edit.html",
        event=event
    )


@events_bp.route(
    "/<int:event_id>/cancel",
    methods=["POST"]
)
def cancel_event(event_id):

    event = db.get_or_404(
        Event,
        event_id
    )

    if event.status == "Cancelled":

        flash(
            "Event is already cancelled.",
            "error"
        )

        return redirect(
            url_for("events.list_events")
        )

    if event.status == "Completed":

        flash(
            "A completed event cannot be cancelled.",
            "error"
        )

        return redirect(
            url_for("events.list_events")
        )

    event.status = "Cancelled"

    db.session.commit()

    flash(
        "Event cancelled successfully.",
        "success"
    )

    return redirect(
        url_for("events.list_events")
    )