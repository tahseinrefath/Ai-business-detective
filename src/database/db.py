"""SQLite for accounts, goals, case notes and activity (built into Python - nothing to install)."""
from contextvars import ContextVar
from pathlib import Path
import sqlite3

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    job_title TEXT NOT NULL DEFAULT '', company TEXT NOT NULL DEFAULT '',
    location TEXT NOT NULL DEFAULT '', bio TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    kind TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_events_user ON events(user_id, kind);
CREATE TABLE IF NOT EXISTS goals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    dataset_id TEXT NOT NULL, metric TEXT NOT NULL, amount REAL NOT NULL,
    UNIQUE (user_id, dataset_id, metric)
);
CREATE TABLE IF NOT EXISTS notes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    dataset_id TEXT NOT NULL, text TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
"""

_db_path_ctx: ContextVar[Path | None] = ContextVar("_db_path", default=None)
_db_conn_ctx: ContextVar[sqlite3.Connection | None] = ContextVar("_db_conn", default=None)
_default_db_path: Path | None = None


def enter_request_db(db_path: Path):
    """Bind the active request's SQLite path to contextvars."""
    return _db_path_ctx.set(db_path), _db_conn_ctx.set(None)


def exit_request_db(path_token, conn_token):
    """Close any SQLite connection opened during the request and reset contextvars."""
    conn = _db_conn_ctx.get()
    if conn is not None:
        conn.close()
    _db_conn_ctx.reset(conn_token)
    _db_path_ctx.reset(path_token)


def get_db() -> sqlite3.Connection:
    """Return a per-request SQLite connection with row factory and foreign keys enabled."""
    conn = _db_conn_ctx.get()
    if conn is None:
        path = _db_path_ctx.get() or _default_db_path
        if path is None:
            raise RuntimeError("Database path is not initialized.")
        conn = sqlite3.connect(path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        _db_conn_ctx.set(conn)
    return conn


def init_db(app):
    """Create database directory and tables; store path on app.state."""
    global _default_db_path
    path = Path(app.state.config.DB_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    app.state.db_path = path
    _default_db_path = path
    con = sqlite3.connect(path)
    con.executescript(SCHEMA)
    con.commit()
    con.close()
