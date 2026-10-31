"""Application configuration."""
import os
import secrets
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


def _secret() -> str:
    """Use SECRET_KEY from .env; otherwise create a random one once and keep it (so logins survive restarts)."""
    env = os.getenv("SECRET_KEY", "")
    if env and env != "change-me":
        return env
    f = BASE_DIR / "data" / ".secret_key"
    f.parent.mkdir(parents=True, exist_ok=True)
    if not f.exists():
        f.write_text(secrets.token_hex(32))
    return f.read_text().strip()


class Config:
    BASE_DIR = BASE_DIR
    SECRET_KEY = _secret()
    DB_PATH = BASE_DIR / "data" / "app.db"
    AVATAR_FOLDER = BASE_DIR / "data" / "avatars"
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    PERMANENT_SESSION_LIFETIME = 60 * 60 * 24 * 14  # 14 days
    UPLOAD_FOLDER = BASE_DIR / "uploads"
    PROCESSED_FOLDER = BASE_DIR / "data" / "processed"
    REPORT_FOLDER = BASE_DIR / "reports"
    SAMPLE_FOLDER = BASE_DIR / "data" / "sample"
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50 MB (Power BI / PDF files can be large)
    ALLOWED_EXTENSIONS = {"csv", "tsv", "txt", "xlsx", "xlsm", "xls", "ods", "json", "pdf", "pbix"}

    # Optional integrations
    DATABASE_URL = os.getenv("DATABASE_URL", "")
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
    LLM_MODEL = os.getenv("LLM_MODEL", "claude-sonnet-4-6")
