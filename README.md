# SecurePay — Full Stack (Flask + MySQL + Frontend)

A complete fintech demo app: HTML/CSS/JS frontend, Flask REST API,
MySQL database, a pluggable fraud-detection ML model, and Gemini-powered
"Monthly AI Analysis" insights.

## 1. Setup

```bash
cd securepay_backend
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

Create your MySQL database:

```sql
CREATE DATABASE securepay CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

Copy `.env.example` to `.env` and fill in your credentials:

```bash
cp .env.example .env
```

Edit `.env`:
- `DB_*` — your MySQL connection details
- `SECRET_KEY` / `JWT_SECRET_KEY` — any random strings
- `GEMINI_API_KEY` — your Gemini API key (for the "Refresh Insight"
  button on the Insights page). Get one at https://aistudio.google.com/apikey
- `FRAUD_MODEL_PATH` — defaults to `ML/fraud_detection_model.pkl`

## 2. Add your fraud detection model

Drop your trained model here:

```
apexpay_backend/ML/fraud_detection_model.pkl
```

See `ML/README.md` for the expected input/output interface. If the
file isn't present, the app automatically falls back to rule-based
fraud heuristics so everything still works end-to-end.

## 3. Create tables + seed demo data

```bash
python seed.py
```

This creates all MySQL tables and seeds a demo account:
- Email: `demo@apexpay.io`
- Password: `Password123!`

(Use `flask --app run.py db init/migrate/upgrade` instead if you want
proper migration history.)

## 4. Run the app

```bash
python run.py
```

This starts Flask on `http://localhost:5000` and:
- Serves the API at `http://localhost:5000/api/*`
- Serves the frontend (the `frontend/` folder) at `http://localhost:5000/`

Open `http://localhost:5000/login.html` (or `/index.html` for the
landing page), log in with the demo account above.

---

## Project Structure

```
apexpay_backend/
├── app/
│   ├── __init__.py            # App factory (API + static frontend serving)
│   ├── extensions.py          # db, migrate, jwt, cors instances
│   ├── models/
│   │   ├── user.py
│   │   ├── account.py
│   │   ├── transaction.py      # incl. note field, fraud check codes
│   │   ├── contact.py
│   │   ├── goal.py
│   │   ├── insight.py          # Insight, SmartTip, CategorySpend
│   │   └── cashflow.py
│   ├── routes/
│   │   ├── auth.py              # register/login/biometric/refresh
│   │   ├── dashboard.py         # /api/dashboard/summary
│   │   ├── transactions.py      # list/filter/paginate/export
│   │   ├── transfer.py          # contacts/lookup/precheck/execute
│   │   ├── insights.py          # insights + Gemini /generate
│   │   └── profile.py           # profile, password, biometric toggle
│   └── utils/
│       ├── fraud_check.py       # ML model integration point
│       └── gemini_service.py    # Gemini API for AI analysis
├── ML/
│   ├── README.md                # model interface documentation
│   └── fraud_detection_model.pkl   <- put your model here
├── frontend/                     # the HTML/CSS/JS app (served by Flask)
│   ├── index.html, login.html, register.html
│   ├── dashboard.html, transactions.html, transfer.html, insights.html
│   ├── profile.html
│   ├── css/  (global.css + one CSS file per page)
│   └── js/   (global.js + one JS file per page)
├── config.py
├── run.py
├── seed.py
├── requirements.txt
└── .env.example
```

---

## How the frontend talks to the backend

`frontend/js/global.js` is loaded on every page. It provides:

- `Api.get/post/put/patch(path, body)` — fetch wrapper that:
  - Adds `Authorization: Bearer <token>` automatically
  - Auto-refreshes the access token once on 401
  - Throws `ApiError` with `.status` / `.data` on failure
- `Auth` — stores `accessToken`, `refreshToken`, and `user` in
  `localStorage`; `Auth.logout()` clears everything and redirects to login.
- A page guard that redirects to `login.html` if not authenticated
  (skips `index.html`, `login.html`, `register.html`).
- Shared UI: avatar dropdown menu (Profile / Settings / Log Out),
  toast notifications (`showToast`), notification bell.

`API_BASE` auto-detects: if the frontend is served by Flask itself
(same origin), it uses `/api`. If opened separately, it falls back to
`http://localhost:5000/api`. Override anytime with:

```html
<script>window.APEXPAY_API_BASE = "https://your-api.example.com/api";</script>
<script src="js/global.js"></script>
```

---

## API Reference

All endpoints (except `/auth/register`, `/auth/login`,
`/auth/biometric-login`) require:
```
Authorization: Bearer <accessToken>
```

### Auth — /api/auth
| Method | Endpoint | Description |
|---|---|---|
| POST | /register | Body: fullName, email, phone, password. Seeds demo data for the new user. |
| POST | /login | Body: email, password. |
| POST | /biometric-login | Body: email. Requires biometricEnabled=true. |
| POST | /refresh | Requires refresh token in Authorization header. |
| GET | /me | Current user profile. |

### Dashboard — /api/dashboard
| Method | Endpoint | Description |
|---|---|---|
| GET | /summary | Balance, 7-day cash flow, AI health snippet, quick-transfer contacts, recent activity. |

### Transactions — /api/transactions
| Method | Endpoint | Description |
|---|---|---|
| GET | (root) | Query: search, range(7d/30d/90d/all), category, page, pageSize. |
| GET | /categories | Distinct categories. |
| GET | /<id> | Single transaction. |
| GET | /export | CSV download (same filters). |

### Transfer — /api/transfer
| Method | Endpoint | Description |
|---|---|---|
| GET | /contacts | Recent contacts (Step 1). |
| GET | /lookup?identifier= | Resolve email/phone/Apex ID to a recipient. |
| POST | /precheck | Body: recipientIdentifier, amount, isKnownRecipient, isInternalTransfer. Runs fraud model without moving money — drives the "Checking..." UI on Step 2. |
| POST | /execute | Body: recipientName, recipientIdentifier, recipientUserId, amount, note, saveContact. Runs fraud check + moves funds. |

### Insights — /api/insights
| Method | Endpoint | Description |
|---|---|---|
| GET | (root) | Monthly AI analysis, active goal, category breakdown, smart tips. |
| GET | /goals | All goals. |
| POST | /tips/<id>/dismiss | Dismiss a smart tip. |
| POST | /generate | Gemini-powered. Regenerates the Monthly AI Analysis from current category spend. Returns {generated: true, insight} on success, or {generated: false, reason, insight} if Gemini is unavailable. |

### Profile — /api/profile
| Method | Endpoint | Description |
|---|---|---|
| GET | (root) | Profile + accounts. |
| PUT/PATCH | (root) | Update fullName, phone, roleTitle. |
| PUT | /password | Body: currentPassword, newPassword. |
| PUT | /biometric | Body: enabled. |

### Health
| Method | Endpoint | Description |
|---|---|---|
| GET | /api/health | Service status + fraud model load status. |

---

## Plugging in your fraud detection model

1. Drop fraud_detection_model.pkl into ML/.
2. Check ML/README.md for the exact feature columns expected by
   app/utils/fraud_check.py::_build_feature_row(). Edit that
   function if your model was trained on different/ordered columns.
3. The service tries model.predict_proba(df) first (preferred — gives
   a 0-1 fraud probability), then model.predict(df), then falls back
   to a raw array if DataFrame input isn't accepted.
4. Tune THRESHOLD_HIGH_RISK / THRESHOLD_SUSPICIOUS in fraud_check.py
   once you've seen real score distributions.
5. Check /api/health to confirm the model loaded successfully.

Fraud result codes (drive badges in transactions.html /
transfer.html), defined in app/models/transaction.py:

- safe_low_risk -> "Safe - Low Risk"
- safe_verified -> "Safe - Verified Entity"
- safe_history -> "Safe - History Match"
- suspicious -> "Suspicious - Unusual Time"
- high_risk_blocked -> "High Risk - Blocked" (transfer is rejected)

---

## Plugging in the Gemini API

1. Get an API key from https://aistudio.google.com/apikey
2. Set GEMINI_API_KEY in .env
3. The "Refresh Insight" button on insights.html calls
   POST /api/insights/generate, which builds a prompt from the user's
   category spend (app/utils/gemini_service.py) and calls
   gemini-1.5-flash. The new analysis is saved as an Insight row and
   shown immediately.
4. If the key is missing or the call fails, the endpoint returns
   generated: false with a reason, and the frontend shows a toast
   while leaving the existing insight in place.

To use a different Gemini model, change GEMINI_API_URL in
gemini_service.py.
