"""
Database migration script to add region column to users and currency to accounts.
Run this after pulling the regional currency changes.
"""

from app import create_app
from app.extensions import db
from sqlalchemy import text

app = create_app()

def migrate():
    with app.app_context():
        try:
            # Add region column to users table if it doesn't exist
            with db.engine.connect() as conn:
                # Check if region column exists
                inspector = db.inspect(db.engine)
                user_columns = [col['name'] for col in inspector.get_columns('users')]
                
                if 'region' not in user_columns:
                    print("Adding 'region' column to users table...")
                    conn.execute(text("ALTER TABLE users ADD COLUMN region VARCHAR(2) DEFAULT 'US'"))
                    conn.commit()
                    print("✓ Added 'region' column")
                else:
                    print("✓ 'region' column already exists")
                
                # Check if accounts have currency set properly
                account_columns = [col['name'] for col in inspector.get_columns('accounts')]
                if 'currency' not in account_columns:
                    print("Adding 'currency' column to accounts table...")
                    conn.execute(text("ALTER TABLE accounts ADD COLUMN currency VARCHAR(3) DEFAULT 'USD'"))
                    conn.commit()
                    print("✓ Added 'currency' column to accounts")
                else:
                    print("✓ 'currency' column already exists in accounts")
                
            print("\n✓ Database migration completed successfully!")
            
        except Exception as e:
            print(f"✗ Migration error: {e}")
            print("\nIf the columns already exist, you can safely ignore this error.")
            print("\nAlternative: Delete the database and run seed.py again:")
            print("  1. Delete apexpay.db (if using SQLite) or DROP DATABASE apexpay; (if using MySQL)")
            print("  2. Run: python seed.py")

if __name__ == "__main__":
    migrate()
