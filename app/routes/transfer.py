from datetime import datetime
from flask import Blueprint, jsonify, request, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity

from app.extensions import db
from app.models import User, Account, Contact, Transaction, CashFlowDaily
from app.models.transaction import (
    DIRECTION_DEBIT,
    DIRECTION_CREDIT,
    STATUS_COMPLETED,
    STATUS_BLOCKED,
    STATUS_ACTION_REQUIRED,
    FRAUD_HIGH_RISK_BLOCKED,
    FRAUD_SUSPICIOUS,
    FRAUD_LABELS,
)
from app.utils.fraud_check import run_fraud_check

transfer_bp = Blueprint("transfer", __name__, url_prefix="/api/transfer")


# ---------------------------------------------------------
# Step 1: Recipient — recent contacts + lookup
# ---------------------------------------------------------
@transfer_bp.route("/contacts", methods=["GET"])
@jwt_required()
def list_contacts():
    user_id = get_jwt_identity()
    contacts = (
        Contact.query.filter_by(user_id=user_id)
        .order_by(Contact.last_used_at.desc())
        .limit(10)
        .all()
    )
    return jsonify({"contacts": [c.to_dict() for c in contacts]}), 200


@transfer_bp.route("/lookup", methods=["GET"])
@jwt_required()
def lookup_recipient():
    """
    GET /api/transfer/lookup?identifier=jane@company.com

    Resolves an email/phone/Apex ID to a recipient.
    - If it matches an existing ApexPay user, returns their public profile.
    - If it matches a saved contact, returns that contact.
    - Otherwise returns a generic "external" recipient shape so the
      frontend can still proceed with a free-text recipient.
    """
    user_id = get_jwt_identity()
    identifier = (request.args.get("identifier") or "").strip().lower()

    if not identifier:
        return jsonify({"error": "identifier is required"}), 400

    # 1. Saved contact match
    contact = Contact.query.filter_by(user_id=user_id, identifier=identifier).first()
    if contact:
        return jsonify({"recipient": contact.to_dict(), "type": "contact"}), 200

    # 2. Existing ApexPay user (by email or phone)
    target_user = User.query.filter(
        (User.email == identifier) | (User.phone == identifier)
    ).first()
    if target_user and target_user.id != user_id:
        parts = target_user.full_name.split()
        initials = (parts[0][0] + parts[-1][0]).upper() if len(parts) > 1 else target_user.full_name[:2].upper()
        return jsonify(
            {
                "recipient": {
                    "name": target_user.full_name,
                    "identifier": target_user.email,
                    "initials": initials,
                    "bg": "#d5e0f8",
                    "color": "#0058be",
                    "icon": None,
                    "isCompany": False,
                    "userId": target_user.id,
                },
                "type": "internal_user",
            }
        ), 200

    # 3. Unknown / external recipient -- frontend supplies display name
    return jsonify(
        {
            "recipient": {
                "name": identifier,
                "identifier": identifier,
                "initials": identifier[:2].upper(),
                "bg": "#d5e0f8",
                "color": "#0058be",
                "icon": None,
                "isCompany": False,
                "userId": None,
            },
            "type": "external",
        }
    ), 200


# ---------------------------------------------------------
# Step 2 -> 3: Pre-flight fraud check (UX "Checking..." bar)
# ---------------------------------------------------------
@transfer_bp.route("/precheck", methods=["POST"])
@jwt_required()
def precheck_transfer():
    """
    POST /api/transfer/precheck
    {
      "recipientIdentifier": "sarah.j@apex.io",
      "amount": 2500.00,
      "isKnownRecipient": true,
      "isInternalTransfer": false
    }

    Runs the fraud model WITHOUT moving any money or writing
    any records. Used to drive the "Checking..." spinner on
    Step 2 before advancing to the Confirm step. If the result
    is high-risk, the frontend can warn the user before they
    reach Confirm.
    """
    user_id = get_jwt_identity()
    data = request.get_json(silent=True) or {}

    try:
        amount = float(data.get("amount", 0))
    except (TypeError, ValueError):
        return jsonify({"error": "Invalid amount"}), 400

    if amount <= 0:
        return jsonify({"error": "Amount must be greater than zero"}), 400

    is_known = bool(data.get("isKnownRecipient", False))
    is_internal = bool(data.get("isInternalTransfer", False))

    from sqlalchemy import func
    user = User.query.get_or_404(user_id)

    agg = (
        db.session.query(
            func.avg(Transaction.amount_cents), func.count(Transaction.id)
        )
        .filter(Transaction.user_id == user_id, Transaction.direction == DIRECTION_DEBIT)
        .first()
    )
    avg_cents, txn_count = agg if agg else (0, 0)
    user_avg_transaction = round((avg_cents or 0) / 100, 2)

    fraud_code, fraud_score = run_fraud_check(
        {
            "amount": amount,
            "is_known_recipient": is_known,
            "is_internal_transfer": is_internal,
            "hour_of_day": datetime.utcnow().hour,
            "day_of_month": datetime.utcnow().day % 30,
            "user_avg_transaction": user_avg_transaction,
            "user_transaction_count": txn_count or 0,
            "user_id": user_id,
            "sender_identifier": user.email,
            "recipient_identifier": data.get("recipientIdentifier"),
        },
        model_path=current_app.config.get("FRAUD_MODEL_PATH"),
    )

    label, badge_type, badge_icon = FRAUD_LABELS.get(
        fraud_code, FRAUD_LABELS[FRAUD_HIGH_RISK_BLOCKED]
    )

    return jsonify(
        {
            "fraudCheck": {
                "code": fraud_code,
                "label": label,
                "type": badge_type,
                "icon": badge_icon,
                "score": fraud_score,
            },
            "blocked": fraud_code == FRAUD_HIGH_RISK_BLOCKED,
        }
    ), 200


# ---------------------------------------------------------
# Step 3: Confirm & Send
# ---------------------------------------------------------
@transfer_bp.route("/execute", methods=["POST"])
@jwt_required()
def execute_transfer():
    """
    POST /api/transfer/execute
    {
      "recipientName": "Sarah J.",
      "recipientIdentifier": "sarah.j@apex.io",
      "recipientUserId": "<uuid or null>",   // set if internal_user
      "amount": 2500.00,
      "saveContact": true
    }

    Runs the fraud check, debits the sender, credits an internal
    recipient if applicable, records the transaction(s), and
    returns the result the 'Confirm' step displays.
    """
    user_id = get_jwt_identity()
    user = User.query.get_or_404(user_id)

    data = request.get_json(silent=True) or {}
    recipient_name = (data.get("recipientName") or "").strip()
    recipient_identifier = (data.get("recipientIdentifier") or "").strip()
    recipient_user_id = data.get("recipientUserId")
    save_contact = bool(data.get("saveContact", True))
    note = (data.get("note") or "").strip()[:255] or None

    try:
        amount = float(data.get("amount", 0))
    except (TypeError, ValueError):
        return jsonify({"error": "Invalid amount"}), 400

    if not recipient_name or not recipient_identifier:
        return jsonify({"error": "recipientName and recipientIdentifier are required"}), 400

    if amount <= 0:
        return jsonify({"error": "Amount must be greater than zero"}), 400

    if amount > 50000:
        return jsonify({"error": "Amount exceeds the maximum transfer limit of $50,000"}), 400

    amount_cents = int(round(amount * 100))

    if amount_cents > user.balance_cents:
        return jsonify({"error": "Insufficient balance"}), 400

    # ---- Determine recipient type ----
    is_known = (
        Contact.query.filter_by(user_id=user_id, identifier=recipient_identifier).first()
        is not None
    )
    is_internal = bool(recipient_user_id)

    # ---- Average transaction amount + count (for fraud context) ----
    from sqlalchemy import func
    agg = (
        db.session.query(
            func.avg(Transaction.amount_cents), func.count(Transaction.id)
        )
        .filter(Transaction.user_id == user_id, Transaction.direction == DIRECTION_DEBIT)
        .first()
    )
    avg_cents, txn_count = agg if agg else (0, 0)
    user_avg_transaction = round((avg_cents or 0) / 100, 2)

    # ---- Run fraud check ----
    fraud_code, fraud_score = run_fraud_check(
        {
            "amount": amount,
            "is_known_recipient": is_known,
            "is_internal_transfer": is_internal,
            "hour_of_day": datetime.utcnow().hour,
            "day_of_month": datetime.utcnow().day % 30,
            "user_avg_transaction": user_avg_transaction,
            "user_transaction_count": txn_count or 0,
            "user_id": user_id,
            "sender_identifier": user.email,
            "recipient_identifier": recipient_identifier,
        },
        model_path=current_app.config.get("FRAUD_MODEL_PATH"),
    )

    blocked = fraud_code == FRAUD_HIGH_RISK_BLOCKED
    status = STATUS_BLOCKED if blocked else STATUS_COMPLETED
    if fraud_code == FRAUD_SUSPICIOUS:
        status = STATUS_ACTION_REQUIRED

    # ---- Create sender-side transaction record ----
    sender_tx = Transaction(
        user_id=user_id,
        sender_id=user_id,
        recipient_id=recipient_user_id,
        recipient_name=recipient_name,
        recipient_identifier=recipient_identifier,
        icon="send",
        category="Transfer",
        direction=DIRECTION_DEBIT,
        amount_cents=amount_cents,
        note=note,
        status=status,
        fraud_check=fraud_code,
        fraud_score=fraud_score,
        occurred_at=datetime.utcnow(),
    )
    db.session.add(sender_tx)

    if not blocked:
        # Debit sender
        user.balance_cents -= amount_cents
        _bump_cashflow(user_id, outflow_cents=amount_cents)

        # Credit recipient if internal ApexPay user
        if is_internal:
            recipient_user = User.query.get(recipient_user_id)
            if recipient_user:
                recipient_user.balance_cents += amount_cents
                _bump_cashflow(recipient_user_id, inflow_cents=amount_cents)

                db.session.add(
                    Transaction(
                        user_id=recipient_user_id,
                        sender_id=user_id,
                        recipient_id=recipient_user_id,
                        recipient_name=user.full_name,
                        recipient_identifier=user.email,
                        icon="south",
                        category="Transfer Received",
                        direction=DIRECTION_CREDIT,
                        amount_cents=amount_cents,
                        status=STATUS_COMPLETED,
                        fraud_check=fraud_code,
                        fraud_score=fraud_score,
                        occurred_at=datetime.utcnow(),
                    )
                )

    # ---- Save/update contact ----
    if save_contact and not blocked:
        contact = Contact.query.filter_by(
            user_id=user_id, identifier=recipient_identifier
        ).first()
        if contact:
            contact.last_used_at = datetime.utcnow()
        else:
            initials = recipient_name[:2].upper() if recipient_name else "??"
            db.session.add(
                Contact(
                    user_id=user_id,
                    name=recipient_name,
                    identifier=recipient_identifier,
                    initials=initials,
                    avatar_color_bg="#d5e0f8",
                    avatar_color_fg="#0058be",
                    last_used_at=datetime.utcnow(),
                )
            )

    db.session.commit()

    label, badge_type, badge_icon = FRAUD_LABELS.get(fraud_code, FRAUD_LABELS[list(FRAUD_LABELS.keys())[0]])

    response = {
        "success": not blocked,
        "status": status,
        "transaction": sender_tx.to_dict(),
        "fraudCheck": {
            "code": fraud_code,
            "label": label,
            "type": badge_type,
            "icon": badge_icon,
            "score": fraud_score,
        },
        "newBalance": user.balance,
    }

    status_code = 200 if not blocked else 403
    return jsonify(response), status_code


def _bump_cashflow(user_id, inflow_cents=0, outflow_cents=0):
    today = datetime.utcnow().date()
    row = CashFlowDaily.query.filter_by(user_id=user_id, date=today).first()
    if not row:
        row = CashFlowDaily(user_id=user_id, date=today, inflow_cents=0, outflow_cents=0)
        db.session.add(row)
    row.inflow_cents += inflow_cents
    row.outflow_cents += outflow_cents
