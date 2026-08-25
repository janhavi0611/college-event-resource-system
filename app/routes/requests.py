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
from app.models import (
    Event,
    Resource,
    ResourceRequest,
    ResourceRequestItem,
)


requests_bp = Blueprint(
    "requests",
    __name__,
    url_prefix="/requests"
)


def check_resource_suitability(event, resource):
    """
    Check whether a resource is suitable for the event.

    Returns:
        (True, None) if the resource is suitable.
        (False, reason) if it is not suitable.
    """

    if resource.capacity is not None:

        if event.expected_attendance > resource.capacity:

            return (
                False,
                (
                    f"{resource.name} has capacity "
                    f"{resource.capacity}, but the event "
                    f"expects {event.expected_attendance} attendees."
                )
            )

    return True, None


@requests_bp.route("/")
def list_requests():

    requests = ResourceRequest.query.order_by(
        ResourceRequest.created_at.desc()
    ).all()

    return render_template(
        "requests/list.html",
        requests=requests
    )


@requests_bp.route("/create", methods=["GET", "POST"])
def create_request():

    events = Event.query.order_by(
        Event.start_datetime.asc()
    ).all()

    resources = Resource.query.filter_by(
        is_active=True
    ).order_by(
        Resource.name.asc()
    ).all()

    if request.method == "POST":

        event_id_value = request.form.get(
            "event_id",
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

        selected_resource_ids = request.form.getlist(
            "resource_ids"
        )

        # Make sure a valid event was selected

        try:
            event_id = int(event_id_value)

        except ValueError:
            flash(
                "Please select a valid event.",
                "error"
            )

            return render_template(
                "requests/create.html",
                events=events,
                resources=resources
            )

        event = db.session.get(Event, event_id)

        if event is None:
            flash(
                "Selected event does not exist.",
                "error"
            )

            return render_template(
                "requests/create.html",
                events=events,
                resources=resources
            )

        # At least one resource is required

        if not selected_resource_ids:
            flash(
                "Please select at least one resource.",
                "error"
            )

            return render_template(
                "requests/create.html",
                events=events,
                resources=resources
            )

        try:
            resource_ids = [
                int(resource_id)
                for resource_id in selected_resource_ids
            ]

        except ValueError:
            flash(
                "Invalid resource selection.",
                "error"
            )

            return render_template(
                "requests/create.html",
                events=events,
                resources=resources
            )

        # Prevent the same resource from being added twice

        resource_ids = list(set(resource_ids))

        selected_resources = Resource.query.filter(
            Resource.id.in_(resource_ids)
        ).all()

        if len(selected_resources) != len(resource_ids):
            flash(
                "One or more selected resources do not exist.",
                "error"
            )

            return render_template(
                "requests/create.html",
                events=events,
                resources=resources
            )

        # Inactive resources should not be part of a request

        inactive_resources = [
            resource
            for resource in selected_resources
            if not resource.is_active
        ]

        if inactive_resources:

            names = ", ".join(
                resource.name
                for resource in inactive_resources
            )

            flash(
                f"Inactive resources cannot be requested: {names}",
                "error"
            )

            return render_template(
                "requests/create.html",
                events=events,
                resources=resources
            )

        # Check whether the selected resources can handle the event

        unsuitable_resources = []

        for resource in selected_resources:

            suitable, reason = check_resource_suitability(
                event,
                resource
            )

            if not suitable:
                unsuitable_resources.append(reason)

        if unsuitable_resources:

            for reason in unsuitable_resources:
                flash(reason, "error")

            return render_template(
                "requests/create.html",
                events=events,
                resources=resources
            )

        # Convert the submitted date and time values

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
                "requests/create.html",
                events=events,
                resources=resources
            )

        if end_datetime <= start_datetime:
            flash(
                "End date/time must be after start date/time.",
                "error"
            )

            return render_template(
                "requests/create.html",
                events=events,
                resources=resources
            )

        # The requested time must fall within the event time

        if start_datetime < event.start_datetime:
            flash(
                "Request start time cannot be before the event starts.",
                "error"
            )

            return render_template(
                "requests/create.html",
                events=events,
                resources=resources
            )

        if end_datetime > event.end_datetime:
            flash(
                "Request end time cannot be after the event ends.",
                "error"
            )

            return render_template(
                "requests/create.html",
                events=events,
                resources=resources
            )

        # Create the request and link the selected resources to it

        resource_request = ResourceRequest(
            event_id=event.id,
            start_datetime=start_datetime,
            end_datetime=end_datetime,
            status="Pending"
        )

        db.session.add(resource_request)

        for resource in selected_resources:

            item = ResourceRequestItem(
                request=resource_request,
                resource=resource
            )

            db.session.add(item)

        try:
            db.session.commit()

        except Exception:
            db.session.rollback()

            flash(
                "Unable to create the resource request.",
                "error"
            )

            return render_template(
                "requests/create.html",
                events=events,
                resources=resources
            )

        flash(
            "Resource request created successfully.",
            "success"
        )

        return redirect(
            url_for("requests.list_requests")
        )

    return render_template(
        "requests/create.html",
        events=events,
        resources=resources
    )