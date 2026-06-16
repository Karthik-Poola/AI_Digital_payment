import uuid
from datetime import datetime
from app.extensions import db


def gen_uuid():
    return str(uuid.uuid4())


class CashFlowDaily(db.Model):
    """
    One row per user per day, storing aggregated inflow/outflow.
    Powers the 'Cash Flow (Last 7 Days)' bar chart on dashboard.html.
    Typically (re)computed nightly from `transactions`, or by the ML pipeline.
    """
    __tablename__ = "cash_flow_daily"

    id = db.Column(db.String(36), primary_key=True, default=gen_uuid)
    user_id = db.Column(db.String(36), db.ForeignKey("users.id"), nullable=False, index=True)

    date = db.Column(db.Date, nullable=False, index=True)
    inflow_cents = db.Column(db.BigInteger, default=0)   # credit (income)
    outflow_cents = db.Column(db.BigInteger, default=0)  # debit (spend)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint("user_id", "date", name="uq_cashflow_user_date"),
    )

    def inflow(self):
        return round(self.inflow_cents / 100, 2)

    @property
    def outflow(self):
        return round(self.outflow_cents / 100, 2)

    def to_dict(self):
        return {
            "date": self.date.isoformat(),
            "inflow": self.inflow,
            "outflow": self.outflow,
        }

