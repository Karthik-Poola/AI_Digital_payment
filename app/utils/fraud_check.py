"""
Fraud-check service.

Wired to a RandomForestClassifier trained on the IEEE-CIS fraud
detection dataset (Kaggle). The model and its LabelEncoders are
loaded from:

    ML/fraud_detection_model.pkl
    ML/label_encoders.pkl

Trained feature order (must match exactly):
    TransactionAmt, addr1, addr2, dist1, dist2, card1, card2, card3,
    card4, card5, card6, ProductCD, P_emaildomain, R_emaildomain,
    DeviceType, DeviceInfo, id_30, id_31, id_33, Hour, Day,
    email_match, transaction_count_card1, avg_amt_card1

ApexPay's transfer form only naturally provides a few of these
(TransactionAmt, Hour, Day, and an approximation of email_match /
transaction_count_card1 / avg_amt_card1 from our own transaction
history). The rest (card1-6, addr1/2, dist1/2, ProductCD, device
info, id_30/31/33) have no equivalent in a P2P transfer flow, so
they're filled with neutral placeholder values below. This means
the model will run, but predictions will be most reliable for the
signals we *do* have real data for (amount, timing, recipient
familiarity). Extend `_build_feature_row()` if you wire up more
inputs (e.g. capturing device/browser info client-side).

If either .pkl is missing, or prediction fails for any reason, this
module falls back to simple rule-based heuristics so the transfer
flow keeps working end-to-end.
"""

import os
import logging
from datetime import datetime
from typing import Optional

from app.models.transaction import (
    FRAUD_SAFE_LOW_RISK,
    FRAUD_SAFE_VERIFIED,
    FRAUD_SAFE_HISTORY,
    FRAUD_SUSPICIOUS,
    FRAUD_HIGH_RISK_BLOCKED,
)

logger = logging.getLogger(__name__)

_model = None
_encoders = None
_model_load_attempted = False
_model_load_error = None

# Thresholds for mapping a fraud probability score -> category.
# Tune these once you've seen the model's real score distribution
# against ApexPay-shaped inputs (placeholders make raw scores less
# reliable than they were on the original Kaggle test set).
THRESHOLD_HIGH_RISK = 0.80
THRESHOLD_SUSPICIOUS = 0.45

# Exact training feature order -- DO NOT reorder without retraining.
FEATURE_ORDER = [
    "TransactionAmt",
    "addr1",
    "addr2",
    "dist1",
    "dist2",
    "card1",
    "card2",
    "card3",
    "card4",
    "card5",
    "card6",
    "ProductCD",
    "P_emaildomain",
    "R_emaildomain",
    "DeviceType",
    "DeviceInfo",
    "id_30",
    "id_31",
    "id_33",
    "Hour",
    "Day",
    "email_match",
    "transaction_count_card1",
    "avg_amt_card1",
]

# Columns that were LabelEncoder-fit during training (object dtype).
CATEGORICAL_COLUMNS = [
    "card4",
    "card6",
    "ProductCD",
    "P_emaildomain",
    "R_emaildomain",
    "DeviceType",
    "DeviceInfo",
    "id_30",
    "id_31",
    "id_33",
]

# Neutral placeholder values for fields ApexPay's transfer form has
# no real equivalent for. These keep the feature row well-formed
# without injecting misleading signal.
PLACEHOLDER_DEFAULTS = {
    "addr1": 0.0,
    "addr2": 0.0,
    "dist1": 0.0,
    "dist2": 0.0,
    "card1": 0.0,
    "card2": 0.0,
    "card3": 0.0,
    "card4": "Unknown",
    "card5": 0.0,
    "card6": "Unknown",
    "ProductCD": "Unknown",
    "DeviceType": "Unknown",
    "DeviceInfo": "Unknown",
    "id_30": "Unknown",
    "id_31": "Unknown",
    "id_33": "Unknown",
}


def _model_path_to_encoders_path(model_path: str) -> str:
    """label_encoders.pkl is expected next to fraud_detection_model.pkl."""
    return os.path.join(os.path.dirname(model_path), "label_encoders.pkl")


def _try_load_model(model_path: str):
    """
    Load both the RandomForest model and its LabelEncoders.
    Returns the model, or None if either file is missing / fails to
    load (expected until both .pkl files are placed in ML/).
    """
    global _model, _encoders, _model_load_attempted, _model_load_error
    _model_load_attempted = True

    if not model_path or not os.path.exists(model_path):
        _model_load_error = f"Model file not found at: {model_path}"
        logger.warning(_model_load_error)
        return None

    encoders_path = _model_path_to_encoders_path(model_path)

    try:
        import joblib
        _model = joblib.load(model_path)
        logger.info("Fraud model loaded from %s", model_path)
    except Exception as e:
        _model_load_error = f"Failed to load model from {model_path}: {e}"
        logger.error(_model_load_error)
        _model = None
        return None

    if os.path.exists(encoders_path):
        try:
            import joblib
            _encoders = joblib.load(encoders_path)
            logger.info("Label encoders loaded from %s", encoders_path)
        except Exception as e:
            logger.error("Failed to load label_encoders.pkl: %s", e)
            _encoders = None
    else:
        logger.warning(
            "label_encoders.pkl not found at %s -- categorical columns "
            "will use fallback encoding (0).",
            encoders_path,
        )
        _encoders = None

    return _model


def _encode_categorical(col: str, value: str) -> int:
    """
    Apply the saved LabelEncoder for `col`, if available.
    Unseen categories (e.g. "Unknown" wasn't in the training data,
    or a real value that never appeared in training) fall back to 0
    rather than raising, since sklearn's LabelEncoder.transform()
    throws on unseen labels.
    """
    if _encoders and col in _encoders:
        le = _encoders[col]
        try:
            return int(le.transform([str(value)])[0])
        except ValueError:
            # Unseen label -- fall back to the encoder's "Unknown"
            # class if it was present during training, else 0.
            classes = list(le.classes_)
            if "Unknown" in classes:
                return int(le.transform(["Unknown"])[0])
            return 0
    return 0


def _build_feature_row(context: dict) -> dict:
    """
    Build the exact 24-feature row the model expects, using real
    ApexPay data where we have it and neutral placeholders elsewhere.

    `context` (from routes) contains:
      - amount: float
      - is_known_recipient: bool
      - is_internal_transfer: bool
      - hour_of_day: int
      - day_of_month: int (optional, defaults to today's day-of-month % 30)
      - user_avg_transaction: float
      - recipient_identifier: str (used to approximate email_match)
      - sender_identifier: str (optional, sender's own email)
    """
    amount = float(context.get("amount", 0.0))
    hour = int(context.get("hour_of_day", datetime.utcnow().hour))
    day = int(context.get("day_of_month", datetime.utcnow().day % 30))
    user_avg = float(context.get("user_avg_transaction", 0.0))
    is_known = bool(context.get("is_known_recipient", False))

    sender_domain = _extract_domain(context.get("sender_identifier"))
    recipient_domain = _extract_domain(context.get("recipient_identifier"))
    email_match = int(
        bool(sender_domain) and bool(recipient_domain) and sender_domain == recipient_domain
    )

    raw = dict(PLACEHOLDER_DEFAULTS)
    raw.update(
        {
            "TransactionAmt": amount,
            "P_emaildomain": sender_domain or "Unknown",
            "R_emaildomain": recipient_domain or "Unknown",
            "Hour": hour,
            "Day": day,
            "email_match": email_match,
            # Use the sender's known transaction count/avg as a stand-in
            # for the Kaggle "per-card1" aggregates -- same intent
            # (how typical is this amount/frequency for this user).
            "transaction_count_card1": float(context.get("user_transaction_count", 0.0)),
            "avg_amt_card1": user_avg,
        }
    )

    # Encode categoricals using the saved encoders; numeric columns
    # pass through as-is.
    encoded = {}
    for col in FEATURE_ORDER:
        if col in CATEGORICAL_COLUMNS:
            encoded[col] = _encode_categorical(col, raw[col])
        else:
            encoded[col] = raw[col]

    return encoded


def _extract_domain(identifier: Optional[str]) -> Optional[str]:
    if not identifier or "@" not in identifier:
        return None
    return identifier.split("@")[-1].strip().lower() or None


def _score_to_fraud_code(score: float, context: dict) -> str:
    """Map a fraud probability (0-1) to one of the FRAUD_* codes."""
    if score >= THRESHOLD_HIGH_RISK:
        return FRAUD_HIGH_RISK_BLOCKED
    if score >= THRESHOLD_SUSPICIOUS:
        return FRAUD_SUSPICIOUS

    if context.get("is_known_recipient"):
        return FRAUD_SAFE_HISTORY
    if context.get("is_internal_transfer"):
        return FRAUD_SAFE_VERIFIED
    return FRAUD_SAFE_LOW_RISK


def _predict_with_model(context: dict):
    """
    Run the loaded RandomForest model on the given context.
    Returns (fraud_code, fraud_score) or None if prediction failed
    (caller falls back to rule-based heuristics in that case).
    """
    if _model is None:
        return None

    try:
        features = _build_feature_row(context)
        row = [features[col] for col in FEATURE_ORDER]

        if hasattr(_model, "predict_proba"):
            score = float(_model.predict_proba([row])[0][1])
        elif hasattr(_model, "predict"):
            score = float(_model.predict([row])[0])
        else:
            logger.error("Loaded model has neither predict_proba nor predict")
            return None
    except Exception as e:
        logger.error("Fraud model prediction failed: %s", e)
        return None

    score = max(0.0, min(1.0, score))
    fraud_code = _score_to_fraud_code(score, context)
    return fraud_code, score


def _rule_based_fallback(context: dict):
    """
    Heuristic fallback used when the ML model isn't available or
    prediction fails. Mirrors the categories shown in the frontend.
    """
    amount = context.get("amount", 0.0)
    hour = context.get("hour_of_day", datetime.utcnow().hour)
    is_known = context.get("is_known_recipient", False)
    is_internal = context.get("is_internal_transfer", False)

    if amount >= 3000 and not is_known and (hour < 6 or hour >= 23):
        return FRAUD_HIGH_RISK_BLOCKED, 0.92

    if not is_known and (hour < 5 or hour >= 23):
        return FRAUD_SUSPICIOUS, 0.55

    if is_internal:
        return FRAUD_SAFE_VERIFIED, 0.05

    if is_known:
        return FRAUD_SAFE_HISTORY, 0.03

    return FRAUD_SAFE_LOW_RISK, 0.08


def run_fraud_check(context: dict, model_path: Optional[str] = None):
    """
    Main entry point. Returns (fraud_code, fraud_score).

    Tries the ML model first (if available), falls back to
    rule-based heuristics otherwise.
    """
    if not _model_load_attempted:
        _try_load_model(model_path)

    if _model is not None:
        result = _predict_with_model(context)
        if result is not None:
            return result

    return _rule_based_fallback(context)


def get_model_status() -> dict:
    """Used by /api/health to check model + encoder load status."""
    return {
        "loaded": _model is not None,
        "encodersLoaded": _encoders is not None,
        "loadAttempted": _model_load_attempted,
        "error": _model_load_error,
    }
