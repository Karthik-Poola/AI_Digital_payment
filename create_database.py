"""
Create the securepay database using SQLAlchemy
"""

import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

# MySQL connection details
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "3306")
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")

try:
    # Connect to MySQL server without a database
    connection_string = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/"
    engine = create_engine(connection_string)
    
    with engine.connect() as conn:
        # Create database
        conn.execute(text("CREATE DATABASE IF NOT EXISTS securepay CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"))
        conn.commit()
        print("✓ Database 'securepay' created successfully!")
    
    engine.dispose()
    
except Exception as e:
    print(f"✗ Error: {e}")
    print("\nYou may need to:")
    print("1. Check that MySQL is running")
    print("2. Verify the password in .env file")
    print("3. Manually create the database:")
    print("   mysql -u root -p")
    print("   mysql> CREATE DATABASE securepay CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
