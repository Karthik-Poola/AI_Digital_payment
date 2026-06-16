import uuid
from datetime import datetime
from app.extensions import db


def gen_uuid():
    return str(uuid.uuid4())


class Contact(db.Model):
    __tablename__ = "contacts"

    id = db.Column(db.String(36), primary_key=True, default=gen_uuid)
    user_id = db.Column(db.String(36), db.ForeignKey("users.id"), nullable=False, index=True)

    name = db.Column(db.String(120), nullable=False)
    identifier = db.Column(db.String(150), nullable=False)  # email / phone / apex id
    initials = db.Column(db.String(4), default="??")
    avatar_color_bg = db.Column(db.String(20), default="#d5e0f8")
    avatar_color_fg = db.Column(db.String(20), default="#0058be")
    icon = db.Column(db.String(50), nullable=True)  # e.g. "business" for companies
    is_company = db.Column(db.Boolean, default=False)

    last_used_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "identifier": self.identifier,
            "initials": self.initials,
            "bg": self.avatar_color_bg,
            "color": self.avatar_color_fg,
            "icon": self.icon,
            "isCompany": self.is_company,
            "lastUsedAt": self.last_used_at.isoformat() if self.last_used_at else None,
        }
