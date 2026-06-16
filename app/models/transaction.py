import uuid
from datetime import datetime
from app.extensions import db


def gen_uuid():
    return str(uuid.uuid4())


# Fraud check result categories used by transactions.html
FRAUD_SAFE_LOW_RISK = "safe_low_risk"
FRAUD_SAFE_VERIFIED = "safe_verified"
FRAUD_SAFE_HISTORY = "safe_history"
FRAUD_SUSPICIOUS = "suspicious"
FRAUD_HIGH_RISK_BLOCKED = "high_risk_blocked"

FRAUD_LABELS = {
    FRAUD_SAFE_LOW_RISK: ("Safe - Low Risk", "success", "check_circle"),
    FRAUD_SAFE_VERIFIED: ("Safe - Verified Entity", "info", "shield"),
    FRAUD_SAFE_HISTORY: ("Safe - History Match", "info", "check_circle"),
    FRAUD_SUSPICIOUS: ("Suspicious - Unusual Time", "warning", "warning"),
    FRAUD_HIGH_RISK_BLOCKED: ("High Risk - Blocked", "danger", "gpp_bad"),
}

# Transaction direction
DIRECTION_DEBIT = "debit"    # money out
DIRECTION_CREDIT = "credit"  # money in

# Transaction status
STATUS_COMPLETED = "completed"
STATUS_PENDING = "pending"
STATUS_BLOCKED = "blocked"
STATUS_ACTION_REQUIRED = "action_required"


class Transaction(db.Model):
    __tablename__ = "transactions"

    id = db.Column(db.String(36), primary_key=True, default=gen_uuid)

    # Owner of this ledger entry (whose transaction history this appears in)
    user_id = db.Column(db.String(36), db.ForeignKey("users.id"), nullable=False, index=True)
    account_id = db.Column(db.String(36), db.ForeignKey("accounts.id"), nullable=True)

    # If this is a peer-to-peer transfer within ApexPay
    sender_id = db.Column(db.String(36), db.ForeignKey("users.id"), nullable=True)
    recipient_id = db.Column(db.String(36), db.ForeignKey("users.id"), nullable=True)

    # Display info (for both internal transfers and external merchants)
    recipient_name = db.Column(db.String(150), nullable=False)
    recipient_identifier = db.Column(db.String(150), nullable=True)  # email/phone/apex id
    icon = db.Column(db.String(50), default="receipt_long")

    category = db.Column(db.String(80), default="Uncategorized", index=True)
    direction = db.Column(db.String(10), default=DIRECTION_DEBIT)  # debit | credit
    amount_cents = db.Column(db.BigInteger, nullable=False)
    currency = db.Column(db.String(3), default="USD")
    note = db.Column(db.String(255), nullable=True)

    status = db.Column(db.String(30), default=STATUS_COMPLETED, index=True)

    # AI Fraud check
    fraud_check = db.Column(db.String(40), default=FRAUD_SAFE_LOW_RISK, index=True)
    fraud_score = db.Column(db.Float, nullable=True)  # raw model score 0-1

    occurred_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    @property
    def amount(self):
        return round(self.amount_cents / 100, 2)

    @property
    def signed_amount(self):
        amt = self.amount
        return amt if self.direction == DIRECTION_CREDIT else -amt

    def fraud_label_info(self):
        return FRAUD_LABELS.get(self.fraud_check, FRAUD_LABELS[FRAUD_SAFE_LOW_RISK])

    def to_dict(self):
        label, badge_type, badge_icon = self.fraud_label_info()
        return {
            "id": self.id,
            "recipientName": self.recipient_name,
            "recipientIdentifier": self.recipient_identifier,
            "icon": self.icon,
            "category": self.category,
            "direction": self.direction,
            "amount": self.amount,
            "signedAmount": self.signed_amount,
            "currency": self.currency,
            "note": self.note,
            "status": self.status,
            "fraudCheck": {
                "code": self.fraud_check,
                "label": label,
                "type": badge_type,
                "icon": badge_icon,
            },
            "fraudScore": self.fraud_score,
            "occurredAt": self.occurred_at.isoformat() if self.occurred_at else None,
        }

    def to_dashboard_dict(self):
        """Lighter shape used by dashboard recent-activity widget."""
        sign = "+" if self.direction == DIRECTION_CREDIT else "-"
        return {
            "id": self.id,
            "icon": self.icon,
            "name": self.recipient_name,
            "category": self.category,
            "amount": f"{sign}${self.amount:,.2f}",
            "isCredit": self.direction == DIRECTION_CREDIT,
            "occurredAt": self.occurred_at.isoformat() if self.occurred_at else None,
        }
