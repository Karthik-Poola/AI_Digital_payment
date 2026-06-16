import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()


class Config:
    # ---- Database ----
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = os.getenv("DB_PORT", "3306")
    DB_USER = os.getenv("DB_USER", "root")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "Karthi%409390")
    DB_NAME = os.getenv("DB_NAME", "apexpay")

    SQLALCHEMY_DATABASE_URI = (
        f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_recycle": 280,
    }

    # ---- Security ----
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-jwt-secret-key")
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(
        minutes=int(os.getenv("JWT_ACCESS_TOKEN_EXPIRES_MIN", "60"))
    )
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(
        days=int(os.getenv("JWT_REFRESH_TOKEN_EXPIRES_DAYS", "30"))
    )

    # ---- ML ----
    FRAUD_MODEL_PATH = os.getenv("FRAUD_MODEL_PATH", "ML/fraud_detection_model.pkl")

    # ---- Gemini AI (for Monthly AI Analysis regeneration) ----
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

    # ---- Misc ----
    JSON_SORT_KEYS = False
