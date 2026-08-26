from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
)

from app.constants import RESOURCE_TYPES
from app.extensions import db
from app.models import Resource
from app.models import Allocation


resources_bp = Blueprint(
    "resources",
    __name__,
    url_prefix="/resources"
)


@resources_bp.route("/")
def list_resources():

    status = request.args.get("status", "").strip().lower()

    query = Resource.query

    if status == "active":
        query = query.filter_by(is_active=True)

    elif status == "inactive":
        query = query.filter_by(is_active=False)

    resources = query.order_by(
        Resource.name.asc()
    ).all()

    return render_template(
        "resources/list.html",
        resources=resources,
        selected_status=status
    )

@resources_bp.route("/create", methods=["GET", "POST"])
def create_resource():

    if request.method == "POST":

        name = request.form.get("name", "").strip()

        resource_type = request.form.get(
            "resource_type",
            ""
        ).strip()

        capacity_value = request.form.get(
            "capacity",
            ""
        ).strip()

        if not name:
            flash(
                "Resource name is required.",
                "error"
            )
            return render_template(
                "resources/create.html",
                resource_types=RESOURCE_TYPES
            )

        if resource_type not in RESOURCE_TYPES:
            flash(
                "Invalid resource type.",
                "error"
            )
            return render_template(
                "resources/create.html",
                resource_types=RESOURCE_TYPES
            )

        capacity = None

        if capacity_value:

            try:
                capacity = int(capacity_value)

            except ValueError:
                flash(
                    "Capacity must be a valid number.",
                    "error"
                )

                return render_template(
                    "resources/create.html",
                    resource_types=RESOURCE_TYPES
                )

            if capacity <= 0:
                flash(
                    "Capacity must be greater than zero.",
                    "error"
                )

                return render_template(
                    "resources/create.html",
                    resource_types=RESOURCE_TYPES
                )

        resource = Resource(
            name=name,
            resource_type=resource_type,
            capacity=capacity,
            is_active=True,
        )

        db.session.add(resource)
        db.session.commit()

        flash(
            "Resource added successfully.",
            "success"
        )

        return redirect(
            url_for("resources.list_resources")
        )

    return render_template(
        "resources/create.html",
        resource_types=RESOURCE_TYPES
    )

@resources_bp.route("/<int:resource_id>/edit", methods=["GET", "POST"])
def edit_resource(resource_id):

    resource = db.get_or_404(Resource, resource_id)

    if request.method == "POST":

        name = request.form.get("name", "").strip()

        resource_type = request.form.get(
            "resource_type",
            ""
        ).strip()

        capacity_value = request.form.get(
            "capacity",
            ""
        ).strip()

        # Validate resource name
        if not name:
            flash(
                "Resource name is required.",
                "error"
            )

            return render_template(
                "resources/edit.html",
                resource=resource,
                resource_types=RESOURCE_TYPES
            )

        # Validate resource type
        if resource_type not in RESOURCE_TYPES:
            flash(
                "Invalid resource type.",
                "error"
            )

            return render_template(
                "resources/edit.html",
                resource=resource,
                resource_types=RESOURCE_TYPES
            )

        # Capacity is optional
        capacity = None

        if capacity_value:

            try:
                capacity = int(capacity_value)

            except ValueError:
                flash(
                    "Capacity must be a valid number.",
                    "error"
                )

                return render_template(
                    "resources/edit.html",
                    resource=resource,
                    resource_types=RESOURCE_TYPES
                )

            if capacity <= 0:
                flash(
                    "Capacity must be greater than zero.",
                    "error"
                )

                return render_template(
                    "resources/edit.html",
                    resource=resource,
                    resource_types=RESOURCE_TYPES
                )

        # Update the existing resource
        resource.name = name
        resource.resource_type = resource_type
        resource.capacity = capacity

        db.session.commit()

        flash(
            "Resource updated successfully.",
            "success"
        )

        return redirect(
            url_for("resources.list_resources")
        )

    return render_template(
        "resources/edit.html",
        resource=resource,
        resource_types=RESOURCE_TYPES
    )
@resources_bp.route("/<int:resource_id>/deactivate", methods=["POST"])
def deactivate_resource(resource_id):

    resource = db.get_or_404(Resource, resource_id)

    if not resource.is_active:
        flash(
            "Resource is already inactive.",
            "error"
        )

        return redirect(
            url_for("resources.list_resources")
        )

    resource.is_active = False

    db.session.commit()

    flash(
        "Resource deactivated successfully.",
        "success"
    )

    return redirect(
        url_for("resources.list_resources")
    )

@resources_bp.route("/<int:resource_id>/activate", methods=["POST"])
def activate_resource(resource_id):

    resource = db.get_or_404(Resource, resource_id)

    if resource.is_active:
        flash(
            "Resource is already active.",
            "error"
        )

        return redirect(
            url_for("resources.list_resources")
        )

    resource.is_active = True

    db.session.commit()

    flash(
        "Resource activated successfully.",
        "success"
    )

    return redirect(
        url_for("resources.list_resources")
    )


@resources_bp.route("/availability", methods=["GET"])
def availability():
    """Show active resources that are free for a selected time window."""
    start_value = request.args.get("start_datetime", "").strip()
    end_value = request.args.get("end_datetime", "").strip()
    resource_type = request.args.get("resource_type", "").strip()
    resources = []
    error = None

    if start_value or end_value:
        try:
            from datetime import datetime
            start_datetime = datetime.fromisoformat(start_value)
            end_datetime = datetime.fromisoformat(end_value)
            if end_datetime <= start_datetime:
                raise ValueError
            query = Resource.query.filter_by(is_active=True)
            if resource_type:
                query = query.filter_by(resource_type=resource_type)
            for resource in query.order_by(Resource.name.asc()).all():
                busy = Allocation.query.filter(
                    Allocation.resource_id == resource.id,
                    Allocation.status == "Active",
                    Allocation.start_datetime < end_datetime,
                    Allocation.end_datetime > start_datetime,
                ).first()
                if not busy:
                    resources.append(resource)
        except ValueError:
            error = "Enter a valid time range with an end time after the start time."

    return render_template("resources/availability.html", resources=resources,
                           resource_types=RESOURCE_TYPES, selected_type=resource_type,
                           start_value=start_value, end_value=end_value, error=error)
