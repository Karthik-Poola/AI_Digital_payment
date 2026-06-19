"""
Seed script for ApexPay.

Usage:
    python seed.py

This will:
  1. Create all tables (db.create_all()) -- run `flask db upgrade`
     instead if you're using migrations in production.
  2. Create a demo user (demo@securepay.io / Password123!) with data
     matching the frontend mockups: balance, transactions, cash flow,
     contacts, goals, insights, smart tips, and category breakdown.
"""

from datetime import datetime, timedelta, date

from app import create_app
from app.extensions import db
from app.models import (
    User,
    Account,
    Transaction,
    Contact,
    Goal,
    Insight,
    SmartTip,
    CategorySpend,
    CashFlowDaily,
)
from app.models.transaction import (
    DIRECTION_DEBIT,
    DIRECTION_CREDIT,
    STATUS_COMPLETED,
    STATUS_BLOCKED,
    STATUS_ACTION_REQUIRED,
    FRAUD_SAFE_LOW_RISK,
    FRAUD_SAFE_VERIFIED,
    FRAUD_SAFE_HISTORY,
    FRAUD_SUSPICIOUS,
    FRAUD_HIGH_RISK_BLOCKED,
)
from app.utils.region import get_currency_for_region

app = create_app()


def seed():
    with app.app_context():
        db.create_all()

        if User.query.filter_by(email="demo@securepay.io").first():
            print("Demo user already exists. Skipping seed.")
            return

        # ---------------------------------------------------
        # User
        # ---------------------------------------------------
        # Use default region/currency for demo (US/USD)
        # In production, this would be detected from the request
        demo_region = "US"
        demo_currency = get_currency_for_region(demo_region)
        
        user = User(
            full_name="Alex Carter",
            email="demo@securepay.io",
            phone="+1 (555) 123-4567",
            avatar_initials="AC",
            role_title="Enterprise Member",
            balance_cents=24_592_00,
            biometric_enabled=True,
            region=demo_region,
            currency=demo_currency,
        )
        user.set_password("Password123!")
        db.session.add(user)
        db.session.flush()

        # ---------------------------------------------------
        # Account
        # ---------------------------------------------------
        db.session.add(
            Account(
                user_id=user.id,
                account_name="Primary Checking",
                account_type="checking",
                balance_cents=user.balance_cents,
                currency=demo_currency,
                is_primary=True,
            )
        )

        # ---------------------------------------------------
        # Contacts (Quick Transfer + Transfer recent contacts)
        # ---------------------------------------------------
        contacts_data = [
            ("Sarah J.", "sarah.j@secure.io", "SJ", "#d5e0f8", "#0058be", None, False),
            ("Tech Corp", "billing@techcorp.com", "TC", "#1f2937", "#ffffff", "business", True),
            ("Vendor A", "vendora@secure.io", "VA", "#fde9d7", "#92400e", None, False),
            ("Michael R.", "michael.r@secure.io", "MR", "#545f73", "#ffffff", None, False),
            ("Emma J.", "emma.j@secure.io", "EJ", "#d5e0f8", "#0058be", None, False),
            ("David K.", "david.k@secure.io", "DK", "#2e3038", "#ffffff", None, False),
        ]
        now = datetime.utcnow()
        for i, (name, identifier, initials, bg, fg, icon, is_company) in enumerate(contacts_data):
            db.session.add(
                Contact(
                    user_id=user.id,
                    name=name,
                    identifier=identifier,
                    initials=initials,
                    avatar_color_bg=bg,
                    avatar_color_fg=fg,
                    icon=icon,
                    is_company=is_company,
                    last_used_at=now - timedelta(hours=i),
                )
            )

        # ---------------------------------------------------
        # Transactions (matches transactions.html mock rows)
        # ---------------------------------------------------
        transactions_data = [
            dict(
                recipient_name="TechNova Solutions Inc.",
                recipient_identifier="billing@technova.com",
                icon="storefront",
                category="Software Subscriptions",
                direction=DIRECTION_DEBIT,
                amount_cents=1_250_00,
                status=STATUS_COMPLETED,
                fraud_check=FRAUD_SAFE_LOW_RISK,
                fraud_score=0.08,
                occurred_at=datetime(2023, 10, 24, 14, 32),
            ),
            dict(
                recipient_name="Unknown Overseas Merchant",
                recipient_identifier="unknown@overseas.biz",
                icon="public",
                category="Uncategorized",
                direction=DIRECTION_DEBIT,
                amount_cents=485_20,
                status=STATUS_ACTION_REQUIRED,
                fraud_check=FRAUD_SUSPICIOUS,
                fraud_score=0.55,
                occurred_at=datetime(2023, 10, 23, 3, 15),
            ),
            dict(
                recipient_name="Chase Corporate Acc",
                recipient_identifier="acct-chase-corp",
                icon="account_balance",
                category="Internal Transfer",
                direction=DIRECTION_CREDIT,
                amount_cents=15_000_00,
                status=STATUS_COMPLETED,
                fraud_check=FRAUD_SAFE_VERIFIED,
                fraud_score=0.02,
                occurred_at=datetime(2023, 10, 21, 9, 0),
            ),
            dict(
                recipient_name="CryptoExchange Ltd.",
                recipient_identifier="payments@cryptoexchange.io",
                icon="error",
                category="Digital Assets",
                direction=DIRECTION_DEBIT,
                amount_cents=3_500_00,
                status=STATUS_BLOCKED,
                fraud_check=FRAUD_HIGH_RISK_BLOCKED,
                fraud_score=0.95,
                occurred_at=datetime(2023, 10, 20, 0, 0),
            ),
            dict(
                recipient_name="Delta Airlines",
                recipient_identifier="reservations@delta.com",
                icon="flight",
                category="Travel & Transit",
                direction=DIRECTION_DEBIT,
                amount_cents=845_50,
                status=STATUS_COMPLETED,
                fraud_check=FRAUD_SAFE_HISTORY,
                fraud_score=0.04,
                occurred_at=datetime(2023, 10, 18, 11, 45),
            ),
            # Extra rows for dashboard "Recent Activity"
            dict(
                recipient_name="Whole Foods Market",
                recipient_identifier="pos@wholefoods.com",
                icon="storefront",
                category="Groceries",
                direction=DIRECTION_DEBIT,
                amount_cents=142_50,
                status=STATUS_COMPLETED,
                fraud_check=FRAUD_SAFE_LOW_RISK,
                fraud_score=0.03,
                occurred_at=now - timedelta(hours=3),
            ),
            dict(
                recipient_name="Stripe Inc. Payout",
                recipient_identifier="payouts@stripe.com",
                icon="south",
                category="Income",
                direction=DIRECTION_CREDIT,
                amount_cents=3_250_00,
                status=STATUS_COMPLETED,
                fraud_check=FRAUD_SAFE_VERIFIED,
                fraud_score=0.01,
                occurred_at=now - timedelta(days=1, hours=2),
            ),
            dict(
                recipient_name="Netflix Subscription",
                recipient_identifier="billing@netflix.com",
                icon="smart_display",
                category="Entertainment",
                direction=DIRECTION_DEBIT,
                amount_cents=15_99,
                status=STATUS_COMPLETED,
                fraud_check=FRAUD_SAFE_LOW_RISK,
                fraud_score=0.02,
                occurred_at=now - timedelta(days=2),
            ),
        ]

        for tx in transactions_data:
            db.session.add(Transaction(user_id=user.id, currency=demo_currency, **tx))

        # ---------------------------------------------------
        # Cash flow (last 7 days) - matches dashboard bar chart
        # ---------------------------------------------------
        today = date.today()
        cashflow_pattern = [
            (30, 25), (35, 30), (28, 15), (50, 30), (65, 25), (45, 20), (0, 0)
        ]
        for i, (dark, light) in enumerate(cashflow_pattern):
            d = today - timedelta(days=6 - i)
            db.session.add(
                CashFlowDaily(
                    user_id=user.id,
                    date=d,
                    inflow_cents=light * 100,
                    outflow_cents=dark * 100,
                )
            )

        # ---------------------------------------------------
        # Goal (Emergency Fund)
        # ---------------------------------------------------
        db.session.add(
            Goal(
                user_id=user.id,
                name="Emergency Fund",
                target_cents=10_000_00,
                current_cents=5_200_00,
                target_date=date(2024, 12, 31),
                icon="savings",
                on_track=True,
            )
        )

        # ---------------------------------------------------
        # Insights (Monthly AI Analysis + AI Health Snippet)
        # ---------------------------------------------------
        db.session.add(
            Insight(
                user_id=user.id,
                type="monthly_analysis",
                title="Monthly AI Analysis",
                body=(
                    "Your spending on Dining Out increased by 15% ($240) this month "
                    "compared to your 3-month average. However, you successfully "
                    "reduced your Transportation costs by 8% ($45). Consider "
                    "reviewing your weekend restaurant expenses to stay on track "
                    "with your overall savings goal."
                ),
                is_new=True,
                cta_label="Review Dining Transactions",
                cta_link="/transactions",
            )
        )

        db.session.add(
            Insight(
                user_id=user.id,
                type="health_snippet",
                title="AI Health Snippet",
                body=(
                    "Your spending on Dining has decreased by 15% this month. "
                    "Keeping this trend could save you an estimated $240 by "
                    "month's end."
                ),
                is_new=True,
                cta_label="View Full Report",
                cta_link="/insights",
            )
        )

        # ---------------------------------------------------
        # Category breakdown (donut chart)
        # ---------------------------------------------------
        period = today.strftime("%Y-%m")
        category_data = [
            ("Housing", 45.0, "#0058be", 1_912_50),
            ("Food & Dining", 30.0, "#545f73", 1_275_00),
            ("Transport", 15.0, "#924700", 637_50),
            ("Other", 10.0, "#e1e2ec", 425_00),
        ]
        for cat, pct, color, amount_cents in category_data:
            db.session.add(
                CategorySpend(
                    user_id=user.id,
                    period=period,
                    category=cat,
                    amount_cents=amount_cents,
                    pct=pct,
                    color=color,
                )
            )

        # ---------------------------------------------------
        # Smart Tips
        # ---------------------------------------------------
        smart_tips_data = [
            dict(
                icon="subscriptions",
                icon_color="#F59E0B",
                icon_bg="#fef3c7",
                title="Subscription Alert",
                description="You have 3 unused streaming services costing $42/mo. Review them?",
            ),
            dict(
                icon="shopping_basket",
                icon_color="#0058be",
                icon_bg="#d5e0f8",
                title="Grocery Timing",
                description=(
                    "Shopping on Sundays instead of Wednesdays could save you an "
                    "average of 5% based on historical data."
                ),
            ),
            dict(
                icon="account_balance",
                icon_color="#10B981",
                icon_bg="#d1fae5",
                title="Auto-Save Opportunity",
                description=(
                    "Your checking balance is higher than usual. Sweep $200 to "
                    "High-Yield Savings?"
                ),
            ),
        ]
        for tip in smart_tips_data:
            db.session.add(SmartTip(user_id=user.id, **tip))

        db.session.commit()
        print("Seed complete!")
        print("  Email:    demo@securepay.io")
        print("  Password: Password123!")


if __name__ == "__main__":
    seed()
