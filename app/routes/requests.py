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
    """
    Check whether a resource is suitable for the event.

    Returns:
        (True, None) if suitable.
        (False, reason) if unsuitable.
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


def resource_has_conflict(
    resource,
    start_datetime,
    end_datetime
):
    """
    Check whether the resource is already allocated
    during the requested time.
    """

    conflicting_allocation = Allocation.query.filter(
        Allocation.resource_id == resource.id,
        Allocation.status == "Active",
        Allocation.start_datetime < end_datetime,
        Allocation.end_datetime > start_datetime
    ).first()

    return conflicting_allocation is not None


def find_available_resources(
    event,
    resource_type,
    quantity,
    start_datetime,
    end_datetime
):
    """
    Find suitable and available resources for a requirement.
    """

    matching_resources = Resource.query.filter(
        Resource.resource_type == resource_type,
        Resource.is_active.is_(True)
    ).order_by(
        Resource.name.asc()
    ).all()

    available_resources = []

    for resource in matching_resources:

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

        available_resources.append(resource)

        if len(available_resources) == quantity:
            break

    return available_resources


def check_resource_conflict(
    resource_type,
    quantity,
    start_datetime,
    end_datetime
):
    """
    Check whether enough active resources of the requested
    type are available during the requested time.
    """

    matching_resources = Resource.query.filter(
        Resource.resource_type == resource_type,
        Resource.is_active.is_(True)
    ).all()

    if len(matching_resources) < quantity:

        return (
            False,
            (
                f"Only {len(matching_resources)} active "
                f"{resource_type} resource(s) exist, "
                f"but {quantity} were requested."
            )
        )

    available_count = 0

    for resource in matching_resources:

        if not resource_has_conflict(
            resource,
            start_datetime,
            end_datetime
        ):
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

        # Check if the selected event is valid

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

        # Check the request dates

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

        # Make sure the request stays within the event time

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

        # Get the resource requirement

        required_resource_type = request.form.get(
            "required_resource_type",
            ""
        ).strip()

        quantity_value = request.form.get(
            "quantity",
            ""
        ).strip()

        # Check if the resource type is valid

        if required_resource_type not in ALLOWED_RESOURCE_TYPES:

            flash(
                "Invalid resource type selected.",
                "error"
            )

            return render_template(
                "requests/create.html",
                events=events,
                resources=resources
            )

        # Check if the quantity is valid

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

        # Make sure enough resources are available

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

        # Create the request and its requirement

        resource_request = ResourceRequest(
            event_id=event.id,
            start_datetime=start_datetime,
            end_datetime=end_datetime,
            status="Pending"
        )

        db.session.add(resource_request)

        try:
            db.session.flush()

            resource_requirement = ResourceRequirement(
                request_id=resource_request.id,
                resource_type=required_resource_type,
                quantity=quantity
            )

            db.session.add(resource_requirement)

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

        # Find resources for every requirement first.
        # Nothing is saved until all requirements can be satisfied.

        resources_to_allocate = []

        for requirement in resource_request.requirements:

            available_resources = find_available_resources(
                event,
                requirement.resource_type,
                requirement.quantity,
                resource_request.start_datetime,
                resource_request.end_datetime
            )

            if len(available_resources) < requirement.quantity:

                raise ValueError(
                    (
                        f"Not enough suitable and available "
                        f"{requirement.resource_type} resources "
                        f"are available for this request."
                    )
                )

            resources_to_allocate.extend(
                available_resources
            )

        # All requirements are satisfied, so create the allocations.

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

        # The allocation was successful.

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

    db.session.commit()

    flash(
        "Resource request rejected.",
        "success"
    )

    return redirect(
        url_for("requests.list_requests")
    )