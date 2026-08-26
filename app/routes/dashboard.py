from flask import Blueprint, render_template

from app.models import (
    Event,
    Resource,
    ResourceRequest,
    Allocation,
)

dashboard_bp = Blueprint(
    "dashboard",
    __name__,
    url_prefix="/dashboard"
)


@dashboard_bp.route("/")
def dashboard():

    total_events = Event.query.count()
    total_resources = Resource.query.count()
    total_requests = ResourceRequest.query.count()

    active_resources = Resource.query.filter_by(
        is_active=True
    ).count()

    inactive_resources = Resource.query.filter_by(
        is_active=False
    ).count()

    pending_requests = ResourceRequest.query.filter_by(
        status="Pending"
    ).count()

    allocated_requests = ResourceRequest.query.filter_by(
        status="Allocated"
    ).count()

    rejected_requests = ResourceRequest.query.filter_by(
        status="Rejected"
    ).count()

    cancelled_requests = ResourceRequest.query.filter_by(
        status="Cancelled"
    ).count()

    upcoming_events = Event.query.order_by(
        Event.start_datetime.asc()
    ).limit(5).all()

    return render_template(
        "dashboard.html",
        total_events=total_events,
        total_resources=total_resources,
        total_requests=total_requests,
        active_resources=active_resources,
        inactive_resources=inactive_resources,
        pending_requests=pending_requests,
        allocated_requests=allocated_requests,
        rejected_requests=rejected_requests,
        cancelled_requests=cancelled_requests,
        upcoming_events=upcoming_events,
    )