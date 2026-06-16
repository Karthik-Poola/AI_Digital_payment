import csv
import io
from datetime import datetime, timedelta
from flask import Blueprint, jsonify, request, Response
from flask_jwt_extended import jwt_required, get_jwt_identity

from app.models import Transaction

transactions_bp = Blueprint("transactions", __name__, url_prefix="/api/transactions")


def _apply_filters(query, args):
    """Shared filter logic for list + export endpoints."""
    # Date range filter: "Last 7 Days" | "Last 30 Days" | "Last 90 Days" | "All Time"
    date_range = args.get("range", "30d")
    if date_range != "all":
        days_map = {"7d": 7, "30d": 30, "90d": 90}
        days = days_map.get(date_range, 30)
        cutoff = datetime.utcnow() - timedelta(days=days)
        query = query.filter(Transaction.occurred_at >= cutoff)

    # Category filter
    category = args.get("category")
    if category and category.lower() != "all":
        query = query.filter(Transaction.category == category)

    # Search by recipient name or category
    search = args.get("search", "").strip()
    if search:
        like = f"%{search}%"
        query = query.filter(
            db_or(Transaction.recipient_name.ilike(like), Transaction.category.ilike(like))
        )

    return query


def db_or(*conditions):
    from sqlalchemy import or_
    return or_(*conditions)


@transactions_bp.route("", methods=["GET"])
@jwt_required()
def list_transactions():
    """
    GET /api/transactions?search=&range=30d&category=All&page=1&pageSize=5

    Powers the Transaction History table, search box, date/category
    filters, and pagination shown in transactions.html.
    """
    user_id = get_jwt_identity()

    page = max(int(request.args.get("page", 1)), 1)
    page_size = min(max(int(request.args.get("pageSize", 5)), 1), 100)

    query = Transaction.query.filter_by(user_id=user_id)
    query = _apply_filters(query, request.args)
    query = query.order_by(Transaction.occurred_at.desc())

    total = query.count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()

    return jsonify(
        {
            "items": [t.to_dict() for t in items],
            "page": page,
            "pageSize": page_size,
            "total": total,
            "totalPages": (total + page_size - 1) // page_size if page_size else 0,
        }
    ), 200


@transactions_bp.route("/categories", methods=["GET"])
@jwt_required()
def list_categories():
    """Distinct categories for the 'All Categories' filter dropdown."""
    user_id = get_jwt_identity()
    rows = (
        Transaction.query.filter_by(user_id=user_id)
        .with_entities(Transaction.category)
        .distinct()
        .all()
    )
    categories = sorted({r[0] for r in rows if r[0]})
    return jsonify({"categories": categories}), 200


@transactions_bp.route("/<string:tx_id>", methods=["GET"])
@jwt_required()
def get_transaction(tx_id):
    user_id = get_jwt_identity()
    tx = Transaction.query.filter_by(id=tx_id, user_id=user_id).first_or_404()
    return jsonify({"transaction": tx.to_dict()}), 200


@transactions_bp.route("/export", methods=["GET"])
@jwt_required()
def export_csv():
    """
    GET /api/transactions/export?search=&range=30d&category=All

    Streams a CSV download — powers the 'Export CSV' button.
    """
    user_id = get_jwt_identity()

    query = Transaction.query.filter_by(user_id=user_id)
    query = _apply_filters(query, request.args)
    query = query.order_by(Transaction.occurred_at.desc())

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        ["Date", "Recipient", "Category", "Fraud Check", "Direction", "Amount", "Currency", "Status"]
    )

    for t in query.all():
        label, _, _ = t.fraud_label_info()
        writer.writerow(
            [
                t.occurred_at.strftime("%Y-%m-%d %H:%M") if t.occurred_at else "",
                t.recipient_name,
                t.category,
                label,
                t.direction,
                f"{t.amount:.2f}",
                t.currency,
                t.status,
            ]
        )

    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=transactions.csv"},
    )
