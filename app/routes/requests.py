from collections import defaultdict
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
    end_datetime,
    excluded_resource_ids=None
):
    """
    Find suitable and available resources for a requirement.

    excluded_resource_ids prevents the same physical resource
    from being selected twice during one approval.
    """

    if excluded_resource_ids is None:
        excluded_resource_ids = set()

    matching_resources = Resource.query.filter(
        Resource.resource_type == resource_type,
        Resource.is_active.is_(True)
    ).order_by(
        Resource.name.asc()
    ).all()

    available_resources = []

    for resource in matching_resources:

        # Skip resources that were already selected

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

        available_resources.append(resource)

        if len(available_resources) == quantity:
            break

    return available_resources


def check_resource_conflict(
    event,
    resource_type,
    quantity,
    start_datetime,
    end_datetime
):
    """
    Check whether enough suitable and available resources
    exist for the requested requirement.
    """

    available_resources = find_available_resources(
        event,
        resource_type,
        quantity,
        start_datetime,
        end_datetime
    )

    if len(available_resources) < quantity:

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

        return (
            False,
            (
                f"Only {len(available_resources)} suitable and "
                f"available {resource_type} resource(s) exist "
                f"for the requested time, but {quantity} "
                f"were requested."
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

        # Check if the event is valid

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

        # Make sure the request stays inside the event time

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

        # Get all the resource requirements

        resource_type_values = request.form.getlist(
            "required_resource_type"
        )

        quantity_values = request.form.getlist(
            "quantity"
        )

        # Also support the [] form field names

        if not resource_type_values:
            resource_type_values = request.form.getlist(
                "required_resource_type[]"
            )

        if not quantity_values:
            quantity_values = request.form.getlist(
                "quantity[]"
            )

        # Make sure at least one requirement was added

        if not resource_type_values:
            flash(
                "Please add at least one resource requirement.",
                "error"
            )

            return render_template(
                "requests/create.html",
                events=events,
                resources=resources
            )

        if len(resource_type_values) != len(quantity_values):
            flash(
                "Each resource requirement must have a quantity.",
                "error"
            )

            return render_template(
                "requests/create.html",
                events=events,
                resources=resources
            )

        # Validate each requirement

        requirements = []

        aggregated_requirements = defaultdict(int)

        for resource_type_value, quantity_value in zip(
            resource_type_values,
            quantity_values
        ):

            resource_type = resource_type_value.strip()

            if resource_type not in ALLOWED_RESOURCE_TYPES:
                flash(
                    f"Invalid resource type: {resource_type}",
                    "error"
                )

                return render_template(
                    "requests/create.html",
                    events=events,
                    resources=resources
                )

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

            aggregated_requirements[resource_type] += quantity

        # Combine duplicate resource types into one requirement

        for resource_type, quantity in aggregated_requirements.items():

            requirements.append(
                {
                    "resource_type": resource_type,
                    "quantity": quantity
                }
            )

        # Check that every requirement can be fulfilled

        for requirement in requirements:

            conflict_free, conflict_reason = (
                check_resource_conflict(
                    event,
                    requirement["resource_type"],
                    requirement["quantity"],
                    start_datetime,
                    end_datetime
                )
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

        # Create the request and all its requirements

        resource_request = ResourceRequest(
            event_id=event.id,
            start_datetime=start_datetime,
            end_datetime=end_datetime,
            status="Pending"
        )

        db.session.add(resource_request)

        try:

            # Get the request ID before adding its requirements

            db.session.flush()

            for requirement in requirements:

                resource_requirement = ResourceRequirement(
                    request_id=resource_request.id,
                    resource_type=requirement["resource_type"],
                    quantity=requirement["quantity"]
                )

                db.session.add(
                    resource_requirement
                )

            # Save the request and requirements together

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

        # Find resources for every requirement first
        # Only allocate them if all requirements can be met

        resources_to_allocate = []

        selected_resource_ids = set()

        for requirement in resource_request.requirements:

            available_resources = find_available_resources(
                event,
                requirement.resource_type,
                requirement.quantity,
                resource_request.start_datetime,
                resource_request.end_datetime,
                excluded_resource_ids=selected_resource_ids
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

            selected_resource_ids.update(
                resource.id
                for resource in available_resources
            )

        # All requirements are satisfied, so create the allocations

        resource_request.status = "Approved"

        for resource in resources_to_allocate:

            request_item = ResourceRequestItem(
                request_id=resource_request.id,
                resource_id=resource.id
            )

            db.session.add(
                request_item
            )

            db.session.flush()

            allocation = Allocation(
                request_item_id=request_item.id,
                resource_id=resource.id,
                start_datetime=resource_request.start_datetime,
                end_datetime=resource_request.end_datetime,
                status="Active"
            )

            db.session.add(
                allocation
            )

        resource_request.status = "Allocated"

        # Save the allocations

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
        # Release all allocations belonging to this request.
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