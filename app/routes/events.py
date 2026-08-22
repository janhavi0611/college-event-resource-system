from datetime import datetime

from flask import Blueprint, render_template, request, redirect, url_for, flash

from app.extensions import db
from app.models import Event


events_bp = Blueprint("events", __name__, url_prefix="/events")


@events_bp.route("/")
def list_events():
    events = Event.query.order_by(Event.start_datetime.asc()).all()

    return render_template(
        "events/list.html",
        events=events
    )


@events_bp.route("/create", methods=["GET", "POST"])
def create_event():

    if request.method == "POST":

        name = request.form.get("name", "").strip()
        organizer = request.form.get("organizer", "").strip()
        attendance_value = request.form.get("expected_attendance", "").strip()
        start_value = request.form.get("start_datetime", "").strip()
        end_value = request.form.get("end_datetime", "").strip()

        if not name or not organizer:
            flash("Event name and organizer are required.", "error")
            return render_template("events/create.html")

        try:
            expected_attendance = int(attendance_value)
        except ValueError:
            flash("Attendance must be a valid number.", "error")
            return render_template("events/create.html")

        if expected_attendance <= 0:
            flash("Expected attendance must be greater than zero.", "error")
            return render_template("events/create.html")

        try:
            start_datetime = datetime.fromisoformat(start_value)
            end_datetime = datetime.fromisoformat(end_value)
        except ValueError:
            flash("Please enter valid start and end dates.", "error")
            return render_template("events/create.html")

        if end_datetime <= start_datetime:
            flash("End date/time must be after start date/time.", "error")
            return render_template("events/create.html")

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

        flash("Event created successfully.", "success")

        return redirect(url_for("events.list_events"))

    return render_template("events/create.html")