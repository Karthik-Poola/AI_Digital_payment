from datetime import datetime, timedelta
from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from app.models import User, Transaction, Contact, CashFlowDaily, Insight
from app.models.transaction import DIRECTION_CREDIT

dashboard_bp = Blueprint("dashboard", __name__, url_prefix="/api/dashboard")


@dashboard_bp.route("/summary", methods=["GET"])
@jwt_required()
def summary():
    """
    Single endpoint that returns everything dashboard.html needs:
    - greeting/user info + balance
    - cash flow (last 7 days)
    - AI health snippet
    - quick transfer contacts
    - recent activity
    """
    user_id = get_jwt_identity()
    user = User.query.get_or_404(user_id)

    # ---- Cash flow: last 7 days ----
    today = datetime.utcnow().date()
    start_date = today - timedelta(days=6)

    rows = (
        CashFlowDaily.query.filter(
            CashFlowDaily.user_id == user_id,
            CashFlowDaily.date >= start_date,
            CashFlowDaily.date <= today,
        )
        .order_by(CashFlowDaily.date.asc())
        .all()
    )
    rows_by_date = {r.date: r for r in rows}

    cash_flow = []
    for i in range(7):
        d = start_date + timedelta(days=i)
        row = rows_by_date.get(d)
        cash_flow.append(
            {
                "date": d.isoformat(),
                "day": d.strftime("%a"),  # Mon, Tue, ...
                "inflow": row.inflow if row else 0,
                "outflow": row.outflow if row else 0,
            }
        )

    # ---- AI Health Snippet (latest) ----
    snippet = (
        Insight.query.filter_by(user_id=user_id, type="health_snippet")
        .order_by(Insight.generated_at.desc())
        .first()
    )

    # ---- Quick transfer contacts (5 most recently used) ----
    contacts = (
        Contact.query.filter_by(user_id=user_id)
        .order_by(Contact.last_used_at.desc())
        .limit(5)
        .all()
    )

    # ---- Recent activity (4 most recent transactions) ----
    recent = (
        Transaction.query.filter_by(user_id=user_id)
        .order_by(Transaction.occurred_at.desc())
        .limit(4)
        .all()
    )

    # ---- 30-day % balance change (vs same point last period) ----
    pct_change = _balance_change_pct(user_id)

    return jsonify(
        {
            "user": {
                "fullName": user.full_name,
                "avatarInitials": user.avatar_initials,
            },
            "balance": user.balance,
            "currency": user.currency,
            "balanceChangePct": pct_change,
            "cashFlow": cash_flow,
            "aiHealthSnippet": snippet.to_dict() if snippet else None,
            "quickTransferContacts": [c.to_dict() for c in contacts],
            "recentActivity": [t.to_dashboard_dict() for t in recent],
        }
    ), 200


def _balance_change_pct(user_id):
    """Rough 30-day net change as a percentage of current balance."""
    cutoff = datetime.utcnow() - timedelta(days=30)
    txns = Transaction.query.filter(
        Transaction.user_id == user_id, Transaction.occurred_at >= cutoff
    ).all()

    if not txns:
        return 0.0

    net_cents = sum(
        t.amount_cents if t.direction == DIRECTION_CREDIT else -t.amount_cents
        for t in txns
    )

    user = User.query.get(user_id)
    prior_balance = user.balance_cents - net_cents
    if prior_balance <= 0:
        return 0.0

    return round((net_cents / prior_balance) * 100, 1)
