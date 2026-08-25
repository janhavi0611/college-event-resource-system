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
    ResourceRequirement,
    Allocation,
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


def check_resource_conflict(
    resource_type,
    quantity,
    start_datetime,
    end_datetime
):
    """
    Check whether enough active resources of the requested type
    are available during the requested time.

    Returns:
        (True, None) if enough resources are available.
        (False, reason) if there is a conflict.
    """

    # Find all active resources of the requested type.
    matching_resources = Resource.query.filter(
        Resource.resource_type == resource_type,
        Resource.is_active.is_(True)
    ).all()

    if len(matching_resources) < quantity:
        return (
            False,
            (
                f"Only {len(matching_resources)} active "
                f"{resource_type} resource(s) are available, "
                f"but {quantity} were requested."
            )
        )

    available_count = 0

    for resource in matching_resources:

        # Look for an active allocation that overlaps
        # with the requested time period.
        conflicting_allocation = Allocation.query.filter(
            Allocation.resource_id == resource.id,
            Allocation.status == "Active",
            Allocation.start_datetime < end_datetime,
            Allocation.end_datetime > start_datetime
        ).first()

        if conflicting_allocation is None:
            available_count += 1

    if available_count < quantity:
        return (
            False,
            (
                f"Only {available_count} {resource_type} "
                f"resource(s) are available for the requested "
                f"time period, but {quantity} were requested."
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

        # -------------------------------------------------
        # Validate event
        # -------------------------------------------------

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

        event = db.session.get(
            Event,
            event_id
        )

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

        # -------------------------------------------------
        # Validate date/time
        # -------------------------------------------------

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

        # -------------------------------------------------
        # Make sure request time is inside event time
        # -------------------------------------------------

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

        # -------------------------------------------------
        # Get resource requirement
        # -------------------------------------------------

        required_resource_type = request.form.get(
            "required_resource_type",
            ""
        ).strip()

        quantity_value = request.form.get(
            "quantity",
            ""
        ).strip()

        # -------------------------------------------------
        # Validate resource type
        # -------------------------------------------------

        if not required_resource_type:
            flash(
                "Please select a required resource type.",
                "error"
            )

            return render_template(
                "requests/create.html",
                events=events,
                resources=resources
            )

        # -------------------------------------------------
        # Validate quantity
        # -------------------------------------------------

        try:
            quantity = int(quantity_value)

        except ValueError:
            flash(
                "Quantity must be a valid number.",
                "error"
            )

            return render_template(
                "requests/create.html",
                events=events,
                resources=resources
            )

        if quantity <= 0:
            flash(
                "Quantity must be at least 1.",
                "error"
            )

            return render_template(
                "requests/create.html",
                events=events,
                resources=resources
            )

        # -------------------------------------------------
        # Check resource conflict
        # -------------------------------------------------

        conflict_free, conflict_reason = check_resource_conflict(
            required_resource_type,
            quantity,
            start_datetime,
            end_datetime
        )

        if not conflict_free:
            flash(
                conflict_reason,
                "error"
            )

            return render_template(
                "requests/create.html",
                events=events,
                resources=resources
            )

        # -------------------------------------------------
        # Create request + requirement
        # -------------------------------------------------

        resource_request = ResourceRequest(
            event_id=event.id,
            start_datetime=start_datetime,
            end_datetime=end_datetime,
            status="Pending"
        )

        db.session.add(resource_request)

        try:
            # Flush gives the request its database ID
            # without committing the transaction yet.
            db.session.flush()

            resource_requirement = ResourceRequirement(
                request_id=resource_request.id,
                resource_type=required_resource_type,
                quantity=quantity
            )

            db.session.add(resource_requirement)

            # Commit both records together.
            db.session.commit()

        except Exception:
            # If anything fails, neither record is saved.
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

        # -------------------------------------------------
        # Success
        # -------------------------------------------------

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