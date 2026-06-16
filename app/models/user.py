import uuid
import bcrypt
from datetime import datetime
from app.extensions import db


def gen_uuid():
    return str(uuid.uuid4())


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.String(36), primary_key=True, default=gen_uuid)
    full_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False, index=True)
    phone = db.Column(db.String(30), nullable=True)
    password_hash = db.Column(db.String(255), nullable=False)

    # Profile
    avatar_initials = db.Column(db.String(4), default="AC")
    role_title = db.Column(db.String(80), default="Member")

    # Account balances (kept in cents to avoid float issues)
    balance_cents = db.Column(db.BigInteger, default=0, nullable=False)
    currency = db.Column(db.String(3), default="USD")

    # Security / status
    is_active = db.Column(db.Boolean, default=True)
    biometric_enabled = db.Column(db.Boolean, default=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    accounts = db.relationship("Account", backref="user", lazy=True, cascade="all, delete-orphan")
    sent_transfers = db.relationship(
        "Transaction",
        foreign_keys="Transaction.sender_id",
        backref="sender",
        lazy=True,
    )
    received_transfers = db.relationship(
        "Transaction",
        foreign_keys="Transaction.recipient_id",
        backref="recipient",
        lazy=True,
    )
    goals = db.relationship("Goal", backref="user", lazy=True, cascade="all, delete-orphan")
    contacts = db.relationship("Contact", backref="owner", lazy=True, cascade="all, delete-orphan")
    insights = db.relationship("Insight", backref="user", lazy=True, cascade="all, delete-orphan")

    # ---- Password helpers ----
    def set_password(self, raw_password: str):
        self.password_hash = bcrypt.hashpw(
            raw_password.encode("utf-8"), bcrypt.gensalt()
        ).decode("utf-8")

    def check_password(self, raw_password: str) -> bool:
        return bcrypt.checkpw(
            raw_password.encode("utf-8"), self.password_hash.encode("utf-8")
        )

    @property
    def balance(self):
        return round(self.balance_cents / 100, 2)

    def to_dict(self, include_balance=True):
        data = {
            "id": self.id,
            "fullName": self.full_name,
            "email": self.email,
            "phone": self.phone,
            "avatarInitials": self.avatar_initials,
            "roleTitle": self.role_title,
            "currency": self.currency,
            "biometricEnabled": self.biometric_enabled,
            "createdAt": self.created_at.isoformat() if self.created_at else None,
        }
        if include_balance:
            data["balance"] = self.balance
        return data
