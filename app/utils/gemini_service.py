"""
Gemini AI service.

Used by POST /api/insights/generate to produce a fresh
"Monthly AI Analysis" narrative based on the user's recent
transaction/category data.

Requires GEMINI_API_KEY to be set in the environment. If it's
missing or the API call fails, callers should fall back to the
existing stored insight (handled in the route, not here).
"""

import os
import json
import urllib.request
import urllib.error

GEMINI_API_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "gemini-1.5-flash:generateContent"
)


class GeminiError(Exception):
    pass


def _build_prompt(context: dict) -> str:
    """
    Build the prompt sent to Gemini using the user's spending data.

    `context` keys:
      - categories: list of {category, amount, pct}
      - totalSpend: float
      - topCategory: str
      - previousAnalysis: str (optional, for variety)
    """
    categories = context.get("categories", [])
    total_spend = context.get("totalSpend", 0)

    category_lines = "\n".join(
        f"- {c['category']}: ${c['amount']:.2f} ({c['pct']}%)" for c in categories
    )

    return (
        "You are a financial analyst AI for ApexPay, a fintech app. "
        "Write a short, friendly 'Monthly AI Analysis' summary (max 60 words) "
        "for a user based on their spending breakdown below. "
        "Mention one category that increased or stands out, and one positive "
        "trend or saving opportunity. Be specific with numbers where possible. "
        "Do not use markdown formatting, just plain text in 2-3 sentences.\n\n"
        f"Total spend this month: ${total_spend:.2f}\n"
        f"Category breakdown:\n{category_lines}\n"
    )


def generate_monthly_analysis(context: dict) -> str:
    """
    Calls the Gemini API and returns a plain-text analysis string.
    Raises GeminiError on any failure (missing key, network error,
    unexpected response shape) so the caller can fall back gracefully.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise GeminiError("GEMINI_API_KEY is not configured")

    prompt = _build_prompt(context)

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.7,
            "maxOutputTokens": 200,
        },
    }

    req = urllib.request.Request(
        f"{GEMINI_API_URL}?key={api_key}",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raise GeminiError(f"Gemini API error: {e.code} {e.reason}")
    except urllib.error.URLError as e:
        raise GeminiError(f"Gemini API network error: {e.reason}")
    except Exception as e:
        raise GeminiError(f"Gemini API request failed: {e}")

    try:
        candidates = body.get("candidates", [])
        if not candidates:
            raise GeminiError("Gemini API returned no candidates")

        parts = candidates[0].get("content", {}).get("parts", [])
        text = "".join(p.get("text", "") for p in parts).strip()

        if not text:
            raise GeminiError("Gemini API returned empty text")

        return text
    except (KeyError, IndexError, AttributeError) as e:
        raise GeminiError(f"Unexpected Gemini API response shape: {e}")
