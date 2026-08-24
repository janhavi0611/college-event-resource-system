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


resources_bp = Blueprint(
    "resources",
    __name__,
    url_prefix="/resources"
)


@resources_bp.route("/")
def list_resources():

    resources = Resource.query.order_by(
        Resource.name.asc()
    ).all()

    return render_template(
        "resources/list.html",
        resources=resources
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