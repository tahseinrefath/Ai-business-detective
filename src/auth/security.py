"""Authentication plumbing: passwords, sessions, CSRF, login throttling, CORS, and route protection for FastAPI."""
from contextvars import ContextVar
import hmac
from pathlib import Path
import re
import secrets
import time
from urllib.parse import quote

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from werkzeug.security import check_password_hash, generate_password_hash

from src.database.db import enter_request_db, exit_request_db, get_db

EMAIL_RE = re.compile(r"^[^@\s]{1,64}@[^@\s]+\.[^@\s]{2,}$")
PUBLIC_PATHS = {
    "/",
    "/login",
    "/register",
    "/api/auth/login",
    "/api/auth/register",
    "/api/auth/session",
    "/api/health",
    "/docs",
    "/redoc",
    "/openapi.json",
}
MAX_FAILS, LOCK_SECONDS = 5, 300

_avatar_dir_ctx: ContextVar[Path | None] = ContextVar("_avatar_dir", default=None)
_default_avatar_dir: Path | None = None


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


def csrf_token(request: Request) -> str:
    if "csrf" not in request.session:
        request.session["csrf"] = secrets.token_hex(16)
    return request.session["csrf"]


class LoginThrottle:
    """After 5 wrong passwords for an email+IP, block further tries for 5 minutes."""

    def __init__(self):
        self.fails: dict[str, list[float]] = {}

    def _client_ip(self, request: Request) -> str:
        fwd = request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
        if fwd:
            return fwd
        return request.client.host if request.client else "unknown"

    def _key(self, request: Request, email: str) -> str:
        return f"{self._client_ip(request)}|{email.lower()}"

    def blocked(self, request: Request, email: str) -> int:
        key = self._key(request, email)
        recent = [t for t in self.fails.get(key, []) if time.time() - t < LOCK_SECONDS]
        self.fails[key] = recent
        return int(LOCK_SECONDS - (time.time() - recent[0])) if len(recent) >= MAX_FAILS else 0

    def fail(self, request: Request, email: str):
        self.fails.setdefault(self._key(request, email), []).append(time.time())

    def clear(self, request: Request, email: str):
        self.fails.pop(self._key(request, email), None)


def get_user_by_id(uid):
    return get_db().execute("SELECT * FROM users WHERE id = ?", (uid,)).fetchone() if uid else None


def log_in(request: Request, user_id: int):
    request.session.clear()                  # new session state after login (prevents session fixation)
    request.session["uid"] = user_id
    csrf_token(request)


def avatar_path(uid: int) -> Path:
    base = _avatar_dir_ctx.get() or _default_avatar_dir
    if base is None:
        raise RuntimeError("Avatar folder is not initialized.")
    return Path(base) / f"{int(uid)}.png"


def current_user(request: Request):
    """FastAPI dependency returning the authenticated SQLite user row (or None)."""
    return getattr(request.state, "user", None)


def require_user(request: Request):
    """FastAPI dependency enforcing an authenticated user."""
    user = getattr(request.state, "user", None)
    if user is None:
        raise HTTPException(status_code=401, detail={"error": "Please sign in to continue.", "login_required": True})
    return user


def _apply_cors_headers(request: Request, resp):
    """Attach CORS headers when the request Origin is allowed by CORS_ORIGINS."""
    origin = request.headers.get("Origin")
    if not origin:
        return resp
    cfg = str(getattr(request.app.state.config, "CORS_ORIGINS", "*")).strip()
    allowed = {o.strip() for o in cfg.split(",") if o.strip()}
    if cfg == "*" or "*" in allowed or origin in allowed:
        resp.headers["Access-Control-Allow-Origin"] = origin
        resp.headers["Access-Control-Allow-Credentials"] = "true"
        resp.headers["Access-Control-Allow-Headers"] = "Content-Type, X-CSRF-Token, Authorization"
        resp.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS, PATCH"
        vary = resp.headers.get("Vary", "")
        if "Origin" not in vary:
            resp.headers["Vary"] = f"{vary}, Origin".strip(", ")
    return resp


def _template_url_for(request: Request, name: str, **params) -> str:
    """Adapter supporting both Starlette `path=` and legacy Flask `filename=` in Jinja templates."""
    if name == "static" and "filename" in params and "path" not in params:
        params["path"] = params.pop("filename")
    return str(request.url_for(name, **params))


def create_templates(templates_dir: Path) -> Jinja2Templates:
    tpl = Jinja2Templates(directory=str(templates_dir))
    return tpl


def render_template(request: Request, name: str, **context):
    """Render a Jinja2 template with `me`, `csrf_token`, and Flask-compatible `url_for`."""
    from src.gamify import summary

    user = getattr(request.state, "user", None)
    me = None
    if user is not None:
        lv = summary(user["id"])
        parts = user["name"].split()
        av = avatar_path(user["id"])
        me = {
            "id": user["id"],
            "name": user["name"],
            "email": user["email"],
            "level": lv["level"],
            "title": lv["title"],
            "initials": ("".join(p[0] for p in parts[:2]) or "?").upper(),
            "has_avatar": av.exists(),
            "avatar_v": int(av.stat().st_mtime) if av.exists() else 0,
        }

    ctx = {
        "request": request,
        "me": me,
        "csrf_token": lambda: csrf_token(request),
        "url_for": lambda route_name, **kw: _template_url_for(request, route_name, **kw),
        **context,
    }
    return request.app.state.templates.TemplateResponse(request, name, ctx)


def install_security(app):
    """Register request DB lifecycle, payload limit, CORS, CSRF, auth guard, and security headers."""
    global _default_avatar_dir
    cfg = app.state.config
    _default_avatar_dir = Path(cfg.AVATAR_FOLDER)
    app.state.login_throttle = LoginThrottle()

    @app.middleware("http")
    async def _security_middleware(request: Request, call_next):
        db_tokens = enter_request_db(app.state.db_path)
        av_token = _avatar_dir_ctx.set(Path(cfg.AVATAR_FOLDER))
        try:
            # 1. Payload size check (Content-Length)
            max_bytes = int(getattr(cfg, "MAX_CONTENT_LENGTH", 50 * 1024 * 1024))
            content_len = request.headers.get("Content-Length")
            if content_len and content_len.isdigit() and int(content_len) > max_bytes:
                return _apply_cors_headers(
                    request, JSONResponse(status_code=413, content={"error": "File too large (max 50 MB)."})
                )

            # 2. CORS preflight
            if request.method == "OPTIONS":
                resp = JSONResponse(status_code=204, content=None)
                return _apply_cors_headers(request, resp)

            # 3. Load authenticated user from signed session
            request.state.user = get_user_by_id(request.session.get("uid"))

            # 4. CSRF validation on mutating requests
            if request.method in ("POST", "PUT", "PATCH", "DELETE"):
                sent = request.headers.get("X-CSRF-Token", "")
                expected = request.session.get("csrf", "")
                if not sent or not expected or not hmac.compare_digest(sent, expected):
                    return _apply_cors_headers(
                        request,
                        JSONResponse(
                            status_code=403,
                            content={"error": "Security check failed. Please refresh the page and try again."},
                        ),
                    )

            # 5. Default-deny route protection
            path = request.url.path
            is_public = path in PUBLIC_PATHS or path.startswith("/static/")
            if request.state.user is None and not is_public:
                if path.startswith("/api/"):
                    return _apply_cors_headers(
                        request,
                        JSONResponse(
                            status_code=401,
                            content={"error": "Please sign in to continue.", "login_required": True},
                        ),
                    )
                full_next = path + (f"?{request.url.query}" if request.url.query else "")
                return RedirectResponse(url=f"/login?next={quote(full_next)}", status_code=302)

            # 6. Dispatch request
            resp = await call_next(request)

            # 7. Attach CORS + security headers
            _apply_cors_headers(request, resp)
            resp.headers.setdefault("X-Content-Type-Options", "nosniff")
            resp.headers.setdefault("X-Frame-Options", "DENY")
            resp.headers.setdefault("Referrer-Policy", "same-origin")
            if request.state.user is not None and not path.startswith("/static/"):
                resp.headers["Cache-Control"] = "no-store"
            return resp
        finally:
            _avatar_dir_ctx.reset(av_token)
            exit_request_db(*db_tokens)
