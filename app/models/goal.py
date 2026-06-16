import uuid
from datetime import datetime
from app.extensions import db


def gen_uuid():
    return str(uuid.uuid4())


class Goal(db.Model):
    __tablename__ = "goals"

    id = db.Column(db.String(36), primary_key=True, default=gen_uuid)
    user_id = db.Column(db.String(36), db.ForeignKey("users.id"), nullable=False, index=True)

    name = db.Column(db.String(120), nullable=False)        # e.g. "Emergency Fund"
    target_cents = db.Column(db.BigInteger, nullable=False)  # e.g. 1000000 ($10,000)
    current_cents = db.Column(db.BigInteger, default=0)
    target_date = db.Column(db.Date, nullable=True)          # e.g. Dec 2024
    icon = db.Column(db.String(50), default="savings")
    is_active = db.Column(db.Boolean, default=True)
    on_track = db.Column(db.Boolean, default=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    @property
    def progress_pct(self):
        if not self.target_cents:
            return 0
        return round((self.current_cents / self.target_cents) * 100, 1)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "target": round(self.target_cents / 100, 2),
            "current": round(self.current_cents / 100, 2),
            "progressPct": self.progress_pct,
            "targetDate": self.target_date.isoformat() if self.target_date else None,
            "icon": self.icon,
            "onTrack": self.on_track,
        }
