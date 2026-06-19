from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity

from app.extensions import db
from app.models import User, Account
from app.utils.region import (
    REGION_CURRENCY_MAP,
    get_currency_for_region,
    get_region_name,
)

profile_bp = Blueprint("profile", __name__, url_prefix="/api/profile")


@profile_bp.route("", methods=["GET"])
@jwt_required()
def get_profile():
    user_id = get_jwt_identity()
    user = User.query.get_or_404(user_id)
    accounts = Account.query.filter_by(user_id=user_id).all()

    return jsonify(
        {
            "user": user.to_dict(),
            "accounts": [a.to_dict() for a in accounts],
        }
    ), 200


@profile_bp.route("", methods=["PUT", "PATCH"])
@jwt_required()
def update_profile():
    """
    Update editable profile fields: fullName, phone, roleTitle.
    Email changes are intentionally NOT allowed here (would need
    re-verification flow) — handle separately if needed.
    """
    user_id = get_jwt_identity()
    user = User.query.get_or_404(user_id)
    data = request.get_json(silent=True) or {}

    if "fullName" in data and data["fullName"].strip():
        user.full_name = data["fullName"].strip()
        parts = user.full_name.split()
        user.avatar_initials = (
            (parts[0][0] + parts[-1][0]).upper() if len(parts) > 1 else user.full_name[:2].upper()
        )

    if "phone" in data:
        user.phone = data["phone"].strip() or None

    if "roleTitle" in data:
        user.role_title = data["roleTitle"].strip() or user.role_title

    db.session.commit()

    return jsonify({"user": user.to_dict()}), 200


@profile_bp.route("/password", methods=["PUT"])
@jwt_required()
def change_password():
    user_id = get_jwt_identity()
    user = User.query.get_or_404(user_id)
    data = request.get_json(silent=True) or {}

    current_password = data.get("currentPassword") or ""
    new_password = data.get("newPassword") or ""

    if not user.check_password(current_password):
        return jsonify({"error": "Current password is incorrect"}), 401

    if len(new_password) < 8:
        return jsonify({"error": "New password must be at least 8 characters"}), 400

    user.set_password(new_password)
    db.session.commit()

    return jsonify({"success": True}), 200


@profile_bp.route("/biometric", methods=["PUT"])
@jwt_required()
def toggle_biometric():
    user_id = get_jwt_identity()
    user = User.query.get_or_404(user_id)
    data = request.get_json(silent=True) or {}

    user.biometric_enabled = bool(data.get("enabled", False))
    db.session.commit()

    return jsonify({"biometricEnabled": user.biometric_enabled}), 200


@profile_bp.route("/regions", methods=["GET"])
def get_available_regions():
    """Get list of available regions and their default currencies."""
    regions = []
    for code, info in REGION_CURRENCY_MAP.items():
        regions.append({
            "code": code,
            "name": info["name"],
            "currency": info["currency"],
            "symbol": info["symbol"],
        })
    return jsonify({"regions": sorted(regions, key=lambda x: x["name"])}), 200


@profile_bp.route("/region", methods=["GET"])
@jwt_required()
def get_user_region():
    """Get current user's region and currency settings."""
    user_id = get_jwt_identity()
    user = User.query.get_or_404(user_id)
    
    region_info = REGION_CURRENCY_MAP.get(user.region, {})
    return jsonify({
        "region": user.region,
        "regionName": get_region_name(user.region),
        "currency": user.currency,
        "symbol": region_info.get("symbol", user.currency),
    }), 200


@profile_bp.route("/region", methods=["PUT"])
@jwt_required()
def update_user_region():
    """Update user's region and associated currency."""
    user_id = get_jwt_identity()
    user = User.query.get_or_404(user_id)
    data = request.get_json(silent=True) or {}
    
    new_region = (data.get("region") or "").upper().strip()
    
    if not new_region or new_region not in REGION_CURRENCY_MAP:
        return jsonify({"error": "Invalid region code"}), 400
    
    user.region = new_region
    user.currency = get_currency_for_region(new_region)
    
    # Update all accounts to the new currency as well
    accounts = Account.query.filter_by(user_id=user_id).all()
    for account in accounts:
        account.currency = user.currency
    
    db.session.commit()
    
    region_info = REGION_CURRENCY_MAP.get(user.region, {})
    return jsonify({
        "region": user.region,
        "regionName": get_region_name(user.region),
        "currency": user.currency,
        "symbol": region_info.get("symbol", user.currency),
    }), 200
