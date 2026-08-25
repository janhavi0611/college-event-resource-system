from datetime import datetime

from app.extensions import db


class Resource(db.Model):
    __tablename__ = "resources"

    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(db.String(150), nullable=False, unique=True)

    resource_type = db.Column(
        db.String(50),
        nullable=False
    )

    capacity = db.Column(
        db.Integer,
        nullable=True
    )

    is_active = db.Column(
        db.Boolean,
        nullable=False,
        default=True
    )

    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow
    )

    request_items = db.relationship(
    "ResourceRequestItem",
    back_populates="resource"
)

    allocations = db.relationship(
        "Allocation",
        back_populates="resource"
    )

    def __repr__(self):
        return f"<Resource {self.name}>"