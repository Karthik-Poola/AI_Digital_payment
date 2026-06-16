from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime

from app.extensions import db
from app.models import Insight, Goal, CategorySpend, SmartTip
from app.utils.gemini_service import generate_monthly_analysis, GeminiError

insights_bp = Blueprint("insights", __name__, url_prefix="/api/insights")


@insights_bp.route("", methods=["GET"])
@jwt_required()
def get_insights():
    """
    GET /api/insights

    Single endpoint that returns everything insights.html needs:
    - Monthly AI Analysis card
    - Active Goal card
    - Category breakdown (donut chart)
    - Smart Tips list
    """
    user_id = get_jwt_identity()

    # ---- Monthly AI Analysis (latest "monthly_analysis" insight) ----
    monthly_analysis = (
        Insight.query.filter_by(user_id=user_id, type="monthly_analysis")
        .order_by(Insight.generated_at.desc())
        .first()
    )

    # ---- Active Goal (first active goal) ----
    goal = (
        Goal.query.filter_by(user_id=user_id, is_active=True)
        .order_by(Goal.created_at.desc())
        .first()
    )

    # ---- Category breakdown for current month ----
    period = datetime.utcnow().strftime("%Y-%m")
    categories = (
        CategorySpend.query.filter_by(user_id=user_id, period=period)
        .order_by(CategorySpend.pct.desc())
        .all()
    )
    total_spend_cents = sum(c.amount_cents for c in categories)

    # ---- Smart tips (not dismissed) ----
    tips = (
        SmartTip.query.filter_by(user_id=user_id, is_dismissed=False)
        .order_by(SmartTip.created_at.desc())
        .limit(5)
        .all()
    )

    return jsonify(
        {
            "monthlyAnalysis": monthly_analysis.to_dict() if monthly_analysis else None,
            "activeGoal": goal.to_dict() if goal else None,
            "categoryBreakdown": {
                "totalSpend": round(total_spend_cents / 100, 2),
                "categories": [c.to_dict() for c in categories],
            },
            "smartTips": [t.to_dict() for t in tips],
        }
    ), 200


# ---------------------------------------------------------
# Goals management
# ---------------------------------------------------------
@insights_bp.route("/goals", methods=["GET"])
@jwt_required()
def list_goals():
    user_id = get_jwt_identity()
    goals = Goal.query.filter_by(user_id=user_id).order_by(Goal.created_at.desc()).all()
    return jsonify({"goals": [g.to_dict() for g in goals]}), 200


# ---------------------------------------------------------
# Smart tips management
# ---------------------------------------------------------
@insights_bp.route("/tips/<string:tip_id>/dismiss", methods=["POST"])
@jwt_required()
def dismiss_tip(tip_id):
    user_id = get_jwt_identity()
    tip = SmartTip.query.filter_by(id=tip_id, user_id=user_id).first_or_404()
    tip.is_dismissed = True

    from app.extensions import db
    db.session.commit()

    return jsonify({"success": True}), 200


# ---------------------------------------------------------
# Gemini-powered "Refresh Insight" button
# ---------------------------------------------------------
@insights_bp.route("/generate", methods=["POST"])
@jwt_required()
def generate_analysis():
    """
    POST /api/insights/generate

    Regenerates the 'Monthly AI Analysis' card using the Gemini API,
    based on the user's current category breakdown. On success, saves
    a new Insight row (so it persists / shows up on next dashboard
    load too) and returns it. On failure (e.g. missing API key,
    network error), returns the existing stored insight unchanged
    with a `generated: false` flag so the frontend can show a
    friendly message instead of erroring out.
    """
    user_id = get_jwt_identity()

    period = datetime.utcnow().strftime("%Y-%m")
    categories = (
        CategorySpend.query.filter_by(user_id=user_id, period=period)
        .order_by(CategorySpend.pct.desc())
        .all()
    )
    total_spend_cents = sum(c.amount_cents for c in categories)

    existing = (
        Insight.query.filter_by(user_id=user_id, type="monthly_analysis")
        .order_by(Insight.generated_at.desc())
        .first()
    )

    if not categories:
        return jsonify(
            {
                "generated": False,
                "reason": "No spending data available yet for this month.",
                "insight": existing.to_dict() if existing else None,
            }
        ), 200

    context = {
        "totalSpend": round(total_spend_cents / 100, 2),
        "categories": [
            {"category": c.category, "amount": round(c.amount_cents / 100, 2), "pct": c.pct}
            for c in categories
        ],
    }

    try:
        body_text = generate_monthly_analysis(context)
    except GeminiError as e:
        return jsonify(
            {
                "generated": False,
                "reason": str(e),
                "insight": existing.to_dict() if existing else None,
            }
        ), 200

    new_insight = Insight(
        user_id=user_id,
        type="monthly_analysis",
        title="Monthly AI Analysis",
        body=body_text,
        is_new=True,
        cta_label="Review Transactions",
        cta_link="/transactions",
    )
    db.session.add(new_insight)
    db.session.commit()

    return jsonify({"generated": True, "insight": new_insight.to_dict()}), 200
