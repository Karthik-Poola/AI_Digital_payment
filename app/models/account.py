import uuid
from datetime import datetime
from app.extensions import db


def gen_uuid():
    return str(uuid.uuid4())


class Account(db.Model):
    __tablename__ = "accounts"

    id = db.Column(db.String(36), primary_key=True, default=gen_uuid)
    user_id = db.Column(db.String(36), db.ForeignKey("users.id"), nullable=False, index=True)

    account_name = db.Column(db.String(80), nullable=False, default="Primary Checking")
    account_type = db.Column(db.String(30), default="checking")  # checking | savings
    balance_cents = db.Column(db.BigInteger, default=0, nullable=False)
    currency = db.Column(db.String(3), default="USD")
    is_primary = db.Column(db.Boolean, default=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    @property
    def balance(self):
        return round(self.balance_cents / 100, 2)

    def to_dict(self):
        return {
            "id": self.id,
            "accountName": self.account_name,
            "accountType": self.account_type,
            "balance": self.balance,
            "currency": self.currency,
            "isPrimary": self.is_primary,
        }
