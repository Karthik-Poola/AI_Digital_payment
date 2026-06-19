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
    "gemini-2.5-flash:generateContent"
)


class GeminiError(Exception):
    pass


def _build_prompt(context: dict) -> str:
    """
    Build the prompt sent to Gemini using the user's spending data.
    """
    categories = context.get("categories", [])
    total_spend = context.get("totalSpend", 0)

    category_lines = "\n".join(
        f"- {c['category']}: ${c['amount']:.2f} ({c['pct']}%)"
        for c in categories
    )

    return (
        "You are a friendly financial advisor AI inside a banking app called SecurePay.\n"
        "Analyze the user's monthly spending and write a short, encouraging insight.\n\n"
        "Rules:\n"
        "- Write exactly 2-3 sentences.\n"
        "- Mention the highest spending category by name and amount.\n"
        "- Suggest one specific saving opportunity or positive habit.\n"
        "- Use plain text only — no bullet points, no markdown, no asterisks.\n"
        "- Be warm, specific, and concise.\n\n"
        f"Total spend this month: ${total_spend:.2f}\n\n"
        "Spending breakdown:\n"
        f"{category_lines}\n\n"
        "Write the insight now:"
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
            "maxOutputTokens": 500,
        },
    }

    req = urllib.request.Request(
        GEMINI_API_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "X-goog-api-key": api_key,
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        try:
            error_body = e.read().decode("utf-8")
        except Exception:
            error_body = ""
        raise GeminiError(f"Gemini API error: {e.code} {e.reason} -- {error_body}")
    except urllib.error.URLError as e:
        raise GeminiError(f"Gemini API network error: {e.reason}")
    except Exception as e:
        raise GeminiError(f"Gemini API request failed: {e}")

    try:
        candidates = body.get("candidates", [])
        if not candidates:
            prompt_feedback = body.get("promptFeedback", {})
            block_reason = prompt_feedback.get("blockReason")
            if block_reason:
                raise GeminiError(f"Gemini blocked the prompt: {block_reason}")
            raise GeminiError(f"Gemini API returned no candidates. Full response: {body}")

        candidate = candidates[0]
        finish_reason = candidate.get("finishReason")

        parts = candidate.get("content", {}).get("parts", [])
        text = "".join(p.get("text", "") for p in parts).strip()

        if not text:
            raise GeminiError(
                f"Gemini API returned empty text (finishReason={finish_reason}). "
                f"Full candidate: {candidate}"
            )

        if finish_reason == "MAX_TOKENS":
            # We got partial text -- still usable, but flag it so you
            # know to raise maxOutputTokens if this happens often.
            text += " ..."

        if finish_reason == "SAFETY":
            raise GeminiError("Gemini blocked the response for safety reasons")

        return text
    except (KeyError, IndexError, AttributeError) as e:
        raise GeminiError(f"Unexpected Gemini API response shape: {e}. Full response: {body}")
