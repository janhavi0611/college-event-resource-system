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


ALLOWED_RESOURCE_TYPES = {
    "Auditorium",
    "Laboratory",
    "Projector",
    "Microphone",
    "Camera",
    "Computer",
}


def check_resource_suitability(event, resource):
    """Check whether a resource can be used for the event."""

    if resource.capacity is not None:
        if event.expected_attendance > resource.capacity:
            return (
                False,
                f"{resource.name} has capacity {resource.capacity}, "
                f"but the event expects {event.expected_attendance} attendees."
            )

    return True, None


def resource_has_conflict(resource, start_datetime, end_datetime):
    """Check whether a resource is already booked during the requested time."""

    conflict = Allocation.query.filter(
        Allocation.resource_id == resource.id,
        Allocation.status == "Active",
        Allocation.start_datetime < end_datetime,
        Allocation.end_datetime > start_datetime
    ).first()

    return conflict is not None


def find_available_resources(
    event,
    resource_type,
    quantity,
    start_datetime,
    end_datetime,
    excluded_resource_ids=None
):
    """
    Find active, suitable and available physical resources.

    Resources are selected only if:
    - type matches
    - resource is active
    - capacity is sufficient
    - there is no overlapping allocation
    """

    if excluded_resource_ids is None:
        excluded_resource_ids = set()

    resources = Resource.query.filter(
        Resource.resource_type == resource_type,
        Resource.is_active.is_(True)
    ).order_by(
        Resource.name.asc()
    ).all()

    available = []

    for resource in resources:

        if resource.id in excluded_resource_ids:
            continue

        suitable, _ = check_resource_suitability(
            event,
            resource
        )

        if not suitable:
            continue

        if resource_has_conflict(
            resource,
            start_datetime,
            end_datetime
        ):
            continue

        available.append(resource)

        if len(available) >= quantity:
            break

    return available


def get_alternatives(
    event,
    resource_type,
    start_datetime,
    end_datetime,
    excluded_resource_ids=None
):
    """
    Find suitable alternatives of the requested resource type.
    """

    return find_available_resources(
        event=event,
        resource_type=resource_type,
        quantity=1,
        start_datetime=start_datetime,
        end_datetime=end_datetime,
        excluded_resource_ids=excluded_resource_ids
    )


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

    if request.method == "POST":

        # -------------------------------------------------
        # Event validation
        # -------------------------------------------------

        event_id_value = request.form.get(
            "event_id",
            ""
        ).strip()

        try:
            event_id = int(event_id_value)
        except ValueError:
            flash(
                "Please select a valid event.",
                "error"
            )

            return render_template(
                "requests/create.html",
                events=events
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
                events=events
            )

        if event.status in {"Cancelled", "Completed", "Rejected"}:
            flash(
                "Resources cannot be requested for a cancelled, completed, or rejected event.",
                "error"
            )
            return render_template(
                "requests/create.html",
                events=events
            )

        # -------------------------------------------------
        # Date/time validation
        # -------------------------------------------------

        start_value = request.form.get(
            "start_datetime",
            ""
        ).strip()

        end_value = request.form.get(
            "end_datetime",
            ""
        ).strip()

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
                events=events
            )

        if end_datetime <= start_datetime:
            flash(
                "End date/time must be after start date/time.",
                "error"
            )

            return render_template(
                "requests/create.html",
                events=events
            )

        # Request must stay within event time.

        if start_datetime < event.start_datetime:
            flash(
                "Request start time cannot be before the event starts.",
                "error"
            )

            return render_template(
                "requests/create.html",
                events=events
            )

        if end_datetime > event.end_datetime:
            flash(
                "Request end time cannot be after the event ends.",
                "error"
            )

            return render_template(
                "requests/create.html",
                events=events
            )

        # -------------------------------------------------
        # Resource requirements
        # -------------------------------------------------

        resource_types = request.form.getlist(
            "required_resource_type"
        )

        quantities = request.form.getlist(
            "quantity"
        )

        if not resource_types:
            flash(
                "Please add at least one resource requirement.",
                "error"
            )

            return render_template(
                "requests/create.html",
                events=events
            )

        if len(resource_types) != len(quantities):
            flash(
                "Invalid resource requirements.",
                "error"
            )

            return render_template(
                "requests/create.html",
                events=events
            )

        requirements_data = []

        for resource_type, quantity_value in zip(
            resource_types,
            quantities
        ):

            resource_type = resource_type.strip()

            if resource_type not in ALLOWED_RESOURCE_TYPES:
                flash(
                    f"Invalid resource type: {resource_type}.",
                    "error"
                )

                return render_template(
                    "requests/create.html",
                    events=events
                )

            try:
                quantity = int(quantity_value)
            except (TypeError, ValueError):
                flash(
                    "Resource quantity must be a valid number.",
                    "error"
                )

                return render_template(
                    "requests/create.html",
                    events=events
                )

            if quantity < 1:
                flash(
                    "Resource quantity must be at least 1.",
                    "error"
                )

                return render_template(
                    "requests/create.html",
                    events=events
                )

            requirements_data.append(
                {
                    "resource_type": resource_type,
                    "quantity": quantity
                }
            )

        # -------------------------------------------------
        # Create request
        # -------------------------------------------------

        resource_request = ResourceRequest(
            event_id=event.id,
            start_datetime=start_datetime,
            end_datetime=end_datetime,
            status="Pending"
        )

        try:

            db.session.add(resource_request)

            db.session.flush()

            for requirement_data in requirements_data:

                requirement = ResourceRequirement(
                    request_id=resource_request.id,
                    resource_type=requirement_data["resource_type"],
                    quantity=requirement_data["quantity"]
                )

                db.session.add(requirement)

            db.session.commit()

        except Exception:

            db.session.rollback()

            flash(
                "Unable to create the resource request.",
                "error"
            )

            return render_template(
                "requests/create.html",
                events=events
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
        events=events
    )


@requests_bp.route(
    "/<int:request_id>/approve",
    methods=["POST"]
)
def approve_request(request_id):

    resource_request = db.session.get(
        ResourceRequest,
        request_id
    )

    if resource_request is None:
        flash(
            "Resource request not found.",
            "error"
        )

        return redirect(
            url_for("requests.list_requests")
        )

    if resource_request.status != "Pending":
        flash(
            "Only pending requests can be approved.",
            "error"
        )

        return redirect(
            url_for("requests.list_requests")
        )

    event = resource_request.event

    try:

        # -------------------------------------------------
        # FIRST find ALL resources.
        #
        # Nothing is allocated until every requirement
        # can be satisfied.
        # -------------------------------------------------

        resources_to_allocate = []
        selected_resource_ids = set()

        for requirement in resource_request.requirements:

            available_resources = find_available_resources(
                event=event,
                resource_type=requirement.resource_type,
                quantity=requirement.quantity,
                start_datetime=resource_request.start_datetime,
                end_datetime=resource_request.end_datetime,
                excluded_resource_ids=selected_resource_ids
            )

            # Not enough resources of this type.

            if len(available_resources) < requirement.quantity:

                alternatives = get_alternatives(
                    event=event,
                    resource_type=requirement.resource_type,
                    start_datetime=resource_request.start_datetime,
                    end_datetime=resource_request.end_datetime,
                    excluded_resource_ids=selected_resource_ids
                )

                message = (
                    f"Not enough active {requirement.resource_type} "
                    f"resources are available. "
                    f"Requested: {requirement.quantity}, "
                    f"Available: {len(available_resources)}."
                )

                if alternatives:
                    message += (
                        f" Suggested alternative: "
                        f"{alternatives[0].name}."
                    )

                raise ValueError(message)

            # Keep track of every selected physical resource.

            for resource in available_resources:

                selected_resource_ids.add(
                    resource.id
                )

                resources_to_allocate.append(
                    resource
                )

        # -------------------------------------------------
        # ALL requirements are satisfied.
        # Now create the actual allocations.
        # -------------------------------------------------

        resource_request.status = "Approved"

        for resource in resources_to_allocate:

            request_item = ResourceRequestItem(
                request_id=resource_request.id,
                resource_id=resource.id
            )

            db.session.add(request_item)

            db.session.flush()

            allocation = Allocation(
                request_item_id=request_item.id,
                resource_id=resource.id,
                start_datetime=resource_request.start_datetime,
                end_datetime=resource_request.end_datetime,
                status="Active"
            )

            db.session.add(allocation)

        resource_request.status = "Allocated"

        db.session.commit()

    except ValueError as exc:

        db.session.rollback()

        flash(
            str(exc),
            "error"
        )

        return redirect(
            url_for("requests.list_requests")
        )

    except Exception:

        db.session.rollback()

        flash(
            "Unable to allocate the resource request.",
            "error"
        )

        return redirect(
            url_for("requests.list_requests")
        )

    flash(
        "Resource request approved and resources allocated successfully.",
        "success"
    )

    return redirect(
        url_for("requests.list_requests")
    )


@requests_bp.route(
    "/<int:request_id>/reject",
    methods=["POST"]
)
def reject_request(request_id):

    resource_request = db.session.get(
        ResourceRequest,
        request_id
    )

    if resource_request is None:

        flash(
            "Resource request not found.",
            "error"
        )

        return redirect(
            url_for("requests.list_requests")
        )

    if resource_request.status != "Pending":

        flash(
            "Only pending requests can be rejected.",
            "error"
        )

        return redirect(
            url_for("requests.list_requests")
        )

    resource_request.status = "Rejected"

    try:

        db.session.commit()

    except Exception:

        db.session.rollback()

        flash(
            "Unable to reject the resource request.",
            "error"
        )

        return redirect(
            url_for("requests.list_requests")
        )

    flash(
        "Resource request rejected.",
        "success"
    )

    return redirect(
        url_for("requests.list_requests")
    )


@requests_bp.route(
    "/<int:request_id>/cancel",
    methods=["POST"]
)
def cancel_request(request_id):

    resource_request = db.session.get(
        ResourceRequest,
        request_id
    )

    if resource_request is None:

        flash(
            "Resource request not found.",
            "error"
        )

        return redirect(
            url_for("requests.list_requests")
        )

    if resource_request.status != "Allocated":

        flash(
            "Only allocated requests can be cancelled.",
            "error"
        )

        return redirect(
            url_for("requests.list_requests")
        )

    try:

        # Release all allocations.

        for item in resource_request.items:

            if item.allocation is not None:
                item.allocation.status = "Cancelled"

        resource_request.status = "Cancelled"

        db.session.commit()

    except Exception:

        db.session.rollback()

        flash(
            "Unable to cancel the resource request.",
            "error"
        )

        return redirect(
            url_for("requests.list_requests")
        )

    flash(
        "Resource request cancelled and resources released.",
        "success"
    )

    return redirect(
        url_for("requests.list_requests")
    )
