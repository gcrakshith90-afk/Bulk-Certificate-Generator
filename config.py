import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


class Config:
    """Base application configuration."""
    SECRET_KEY = os.getenv("SECRET_KEY", "certiflow-default-secret-key-change-in-production")
    
    # Database
    db_path = BASE_DIR / "certiflow.db"
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", f"sqlite:///{db_path}")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Security & Uploads
    MAX_CONTENT_LENGTH = int(os.getenv("MAX_CONTENT_LENGTH", 10 * 1024 * 1024))  # 10 MB
    MAX_RECIPIENTS_PER_JOB = int(os.getenv("MAX_RECIPIENTS_PER_JOB", 1000))
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = 7200  # 2 hours
    
    # File storage paths
    UPLOAD_FOLDER = BASE_DIR / os.getenv("UPLOAD_FOLDER", "uploads")
    GENERATED_CERTIFICATES_FOLDER = BASE_DIR / os.getenv("GENERATED_CERTIFICATES_FOLDER", "generated_certificates")
    TEMP_ZIPS_FOLDER = BASE_DIR / os.getenv("TEMP_ZIPS_FOLDER", "temp_zips")
    
    # Default admin credentials for initialization
    ADMIN_NAME = os.getenv("ADMIN_NAME", "CertiFlow Admin")
    ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@certiflow.local")
    ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "Admin@123456")

    # Session security
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = False  # Set to True in production HTTPS


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False
    SESSION_COOKIE_SECURE = True


class TestingConfig(Config):
    TESTING = True
    DEBUG = True
    WTF_CSRF_ENABLED = False
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024
    MAX_RECIPIENTS_PER_JOB = 200


config_by_name = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
    "default": DevelopmentConfig,
}
