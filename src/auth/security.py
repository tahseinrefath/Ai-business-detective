"""Authentication plumbing: passwords, sessions, CSRF, login throttling and default-deny route protection."""
import hmac
import re
import secrets
import time

from flask import g, jsonify, redirect, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from src.database.db import get_db

EMAIL_RE = re.compile(r"^[^@\s]{1,64}@[^@\s]+\.[^@\s]{2,}$")
PUBLIC_PATHS = {"/", "/login", "/register", "/api/auth/login", "/api/auth/register"}
MAX_FAILS, LOCK_SECONDS = 5, 300


def hash_password(pw: str) -> str:
    return generate_password_hash(pw)


def verify_password(hash_, pw: str) -> bool:
    return check_password_hash(hash_, pw)


def password_problem(pw: str):
    if not isinstance(pw, str) or len(pw) < 8:
        return "Password must be at least 8 characters."
    if len(pw) > 128:
        return "Password is too long (max 128 characters)."
    if not re.search(r"[A-Za-z]", pw) or not re.search(r"\d", pw):
        return "Password must contain at least one letter and one number."
    return None


def safe_next(url) -> str:
    """Only allow relative in-site redirects (prevents open-redirect attacks)."""
    if isinstance(url, str) and url.startswith("/") and not url.startswith("//") and "\\" not in url:
        return url
    return "/dashboard"


def csrf_token() -> str:
    if "csrf" not in session:
        session["csrf"] = secrets.token_hex(16)
    return session["csrf"]


class LoginThrottle:
    """After 5 wrong passwords for an email+IP, block further tries for 5 minutes."""

    def __init__(self):
        self.fails: dict[str, list[float]] = {}

    def _key(self, email):
        return f"{request.remote_addr}|{email.lower()}"

    def blocked(self, email) -> int:
        recent = [t for t in self.fails.get(self._key(email), []) if time.time() - t < LOCK_SECONDS]
        self.fails[self._key(email)] = recent
        return int(LOCK_SECONDS - (time.time() - recent[0])) if len(recent) >= MAX_FAILS else 0

    def fail(self, email):
        self.fails.setdefault(self._key(email), []).append(time.time())

    def clear(self, email):
        self.fails.pop(self._key(email), None)


def get_user_by_id(uid):
    return get_db().execute("SELECT * FROM users WHERE id = ?", (uid,)).fetchone() if uid else None


def log_in(user_id: int):
    session.clear()                       # new session id after login (prevents session fixation)
    session["uid"] = user_id
    session.permanent = True
    csrf_token()


def install_security(app):
    app.login_throttle = LoginThrottle()

    @app.before_request
    def _load_user():
        g.user = get_user_by_id(session.get("uid"))

    @app.before_request
    def _csrf():
        if request.method in ("POST", "PUT", "PATCH", "DELETE"):
            sent = request.headers.get("X-CSRF-Token", "")
            if not sent or not hmac.compare_digest(sent, session.get("csrf", "")):
                return jsonify(error="Security check failed. Please refresh the page and try again."), 403

    @app.before_request
    def _require_login():
        if g.user is not None or request.path in PUBLIC_PATHS or request.path.startswith("/static/"):
            return None
        if request.path.startswith("/api/"):
            return jsonify(error="Please sign in to continue.", login_required=True), 401
        return redirect(url_for("auth.login_page", next=request.full_path.rstrip("?")))

    @app.after_request
    def _headers(resp):
        resp.headers.setdefault("X-Content-Type-Options", "nosniff")
        resp.headers.setdefault("X-Frame-Options", "DENY")
        resp.headers.setdefault("Referrer-Policy", "same-origin")
        if g.get("user") is not None and not request.path.startswith("/static/"):
            resp.headers["Cache-Control"] = "no-store"
        return resp

    @app.context_processor
    def _inject():
        from src.gamify import summary
        user = g.get("user")
        me = None
        if user is not None:
            lv = summary(user["id"])
            parts = user["name"].split()
            me = {"id": user["id"], "name": user["name"], "email": user["email"], "level": lv["level"], "title": lv["title"],
                  "initials": ("".join(p[0] for p in parts[:2]) or "?").upper(), "has_avatar": avatar_path(user["id"]).exists(),
                  "avatar_v": int(avatar_path(user["id"]).stat().st_mtime) if avatar_path(user["id"]).exists() else 0}
        return {"csrf_token": csrf_token, "me": me}


def avatar_path(uid: int):
    from flask import current_app
    from pathlib import Path
    return Path(current_app.config["AVATAR_FOLDER"]) / f"{int(uid)}.png"
