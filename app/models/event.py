from datetime import datetime

from app.extensions import db


class Event(db.Model):
    __tablename__ = "events"

    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(db.String(150), nullable=False)
    organizer = db.Column(db.String(150), nullable=False)

    expected_attendance = db.Column(db.Integer, nullable=False)

    start_datetime = db.Column(db.DateTime, nullable=False)
    end_datetime = db.Column(db.DateTime, nullable=False)

    status = db.Column(
        db.String(20),
        nullable=False,
        default="Draft"
    )

    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow
    )
    resource_requests = db.relationship(
    "ResourceRequest",
    back_populates="event",
    cascade="all, delete-orphan"
)

    def __repr__(self):
        return f"<Event {self.name}>"