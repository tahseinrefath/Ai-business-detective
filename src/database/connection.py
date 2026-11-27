"""Optional PostgreSQL connection. The app runs fine without it (file storage is the default)."""
import logging

log = logging.getLogger(__name__)


def get_connection(database_url: str):
    if not database_url:
        return None
    try:
        import psycopg
        return psycopg.connect(database_url, connect_timeout=3)
    except Exception as exc:
        log.warning("PostgreSQL unavailable (%s) - continuing with file storage.", type(exc).__name__)
        return None
