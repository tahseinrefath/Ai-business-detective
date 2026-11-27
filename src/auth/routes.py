import sqlite3

from fastapi import APIRouter, Body, Depends, File, Query, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse, Response

from src import gamify
from src.auth import avatar as avatar_mod
from src.auth.security import (
    EMAIL_RE,
    avatar_path,
    csrf_token,
    hash_password,
    log_in,
    password_problem,
    render_template,
    require_user,
    safe_next,
    verify_password,
)
from src.database.db import get_db
from src.schemas import (
    DeleteAccountRequest,
    HealthResponse,
    LoginRequest,
    PasswordChangeRequest,
    ProfileUpdateRequest,
    RegisterRequest,
)

router = APIRouter(tags=["auth", "profile"])
FIELDS = {"name": 60, "job_title": 80, "company": 80, "location": 80, "bio": 300}


def public_user(row) -> dict:
    p = avatar_path(row["id"])
    return {
        "id": row["id"],
        "name": row["name"],
        "email": row["email"],
        "job_title": row["job_title"],
        "company": row["company"],
        "location": row["location"],
        "bio": row["bio"],
        "created_at": row["created_at"],
        "has_avatar": p.exists(),
        "avatar_v": int(p.stat().st_mtime) if p.exists() else 0,
    }


# ---------- HTML pages ----------
@router.get("/login", include_in_schema=False)
def login_page(request: Request, next: str | None = Query(default=None)):
    if getattr(request.state, "user", None):
        return RedirectResponse(url=safe_next(next), status_code=302)
    return render_template(request, "auth.html", mode="login", page="auth", next_url=safe_next(next))


@router.get("/register", include_in_schema=False)
def register_page(request: Request):
    if getattr(request.state, "user", None):
        return RedirectResponse(url="/dashboard", status_code=302)
    return render_template(request, "auth.html", mode="register", page="auth", next_url="/dashboard")


@router.get("/profile", include_in_schema=False)
def profile_page(request: Request):
    return render_template(request, "profile.html", page="profile")


# ---------- auth API ----------
@router.post("/api/auth/register")
def register(request: Request, d: RegisterRequest = Body(default_factory=RegisterRequest)):
    name = str(d.name or "").strip()
    email = str(d.email or "").strip().lower()
    pw = d.password
    if not (2 <= len(name) <= FIELDS["name"]):
        return JSONResponse({"error": "Please enter your name (2-60 characters)."}, status_code=422)
    if not EMAIL_RE.match(email):
        return JSONResponse({"error": "Please enter a valid email address."}, status_code=422)
    problem = password_problem(pw)
    if problem:
        return JSONResponse({"error": problem}, status_code=422)
    db = get_db()
    try:
        cur = db.execute("INSERT INTO users (email, name, password_hash) VALUES (?, ?, ?)", (email, name, hash_password(pw)))
        db.commit()
    except sqlite3.IntegrityError:
        return JSONResponse({"error": "An account with this email already exists. Try signing in."}, status_code=409)
    log_in(request, cur.lastrowid)
    user_row = db.execute("SELECT * FROM users WHERE id = ?", (cur.lastrowid,)).fetchone()
    return {"ok": True, "next": safe_next(d.next), "csrf_token": csrf_token(request), "user": public_user(user_row)}


@router.post("/api/auth/login")
def login(request: Request, d: LoginRequest = Body(default_factory=LoginRequest)):
    email = str(d.email or "").strip().lower()
    pw = str(d.password or "")
    throttle = request.app.state.login_throttle
    wait = throttle.blocked(request, email)
    if wait:
        return JSONResponse({"error": f"Too many failed attempts. Try again in {wait // 60 + 1} minute(s)."}, status_code=429)
    row = get_db().execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    if not row or not verify_password(row["password_hash"], pw):
        throttle.fail(request, email)
        return JSONResponse({"error": "Incorrect email or password."}, status_code=401)
    throttle.clear(request, email)
    log_in(request, row["id"])
    return {"ok": True, "next": safe_next(d.next), "csrf_token": csrf_token(request), "user": public_user(row)}


@router.post("/api/auth/logout")
def logout(request: Request):
    request.session.clear()
    return {"ok": True}


@router.get("/api/auth/session")
def session_info(request: Request):
    u = getattr(request.state, "user", None)
    user = public_user(u) if u is not None else None
    stats = gamify.summary(u["id"]) if u is not None else None
    return {
        "csrf_token": csrf_token(request),
        "authenticated": u is not None,
        "user": user,
        "stats": stats,
    }


@router.get("/api/health", response_model=HealthResponse)
def health():
    return {"status": "ok"}


# ---------- profile API ----------
@router.get("/api/profile")
def get_profile(user=Depends(require_user)):
    return {"user": public_user(user), "stats": gamify.summary(user["id"])}


@router.put("/api/profile")
def update_profile(d: ProfileUpdateRequest = Body(default_factory=ProfileUpdateRequest), user=Depends(require_user)):
    payload = d.model_dump()
    vals = {k: str((user[k] if payload.get(k) is None else payload[k]) or "").strip() for k in FIELDS}
    if not (2 <= len(vals["name"]) <= FIELDS["name"]):
        return JSONResponse({"error": "Name must be 2-60 characters."}, status_code=422)
    for k, limit in FIELDS.items():
        if len(vals[k]) > limit:
            return JSONResponse({"error": f"{k.replace('_', ' ').title()} is too long (max {limit} characters)."}, status_code=422)
    db = get_db()
    db.execute(
        "UPDATE users SET name=?, job_title=?, company=?, location=?, bio=? WHERE id=?",
        (vals["name"], vals["job_title"], vals["company"], vals["location"], vals["bio"], user["id"]),
    )
    db.commit()
    updated = db.execute("SELECT * FROM users WHERE id=?", (user["id"],)).fetchone()
    return {"ok": True, "user": public_user(updated)}


@router.post("/api/profile/password")
def change_password(d: PasswordChangeRequest = Body(default_factory=PasswordChangeRequest), user=Depends(require_user)):
    if not verify_password(user["password_hash"], str(d.current or "")):
        return JSONResponse({"error": "Your current password is incorrect."}, status_code=403)
    problem = password_problem(d.new)
    if problem:
        return JSONResponse({"error": problem}, status_code=422)
    db = get_db()
    db.execute("UPDATE users SET password_hash=? WHERE id=?", (hash_password(d.new), user["id"]))
    db.commit()
    return {"ok": True}


@router.post("/api/profile/avatar")
async def upload_avatar(avatar: UploadFile | None = File(default=None), user=Depends(require_user)):
    if not avatar:
        return JSONResponse({"error": "Choose an image first."}, status_code=400)
    raw = await avatar.read(avatar_mod.MAX_BYTES + 1)
    try:
        png = avatar_mod.process(raw)
    except avatar_mod.AvatarError as e:
        return JSONResponse({"error": str(e)}, status_code=422)
    p = avatar_path(user["id"])
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(png)
    return {"ok": True, "user": public_user(user)}


@router.delete("/api/profile/avatar")
def delete_avatar(user=Depends(require_user)):
    avatar_path(user["id"]).unlink(missing_ok=True)
    return {"ok": True, "user": public_user(user)}


@router.get("/avatar/me", responses={200: {"content": {"image/png": {}}}})
def my_avatar(user=Depends(require_user)):
    p = avatar_path(user["id"])
    if not p.exists():
        return Response(status_code=404)
    return FileResponse(p, media_type="image/png", headers={"Cache-Control": "private, max-age=0, must-revalidate"})


@router.post("/api/profile/delete")
def delete_account(
    request: Request,
    d: DeleteAccountRequest = Body(default_factory=DeleteAccountRequest),
    user=Depends(require_user),
):
    if not verify_password(user["password_hash"], str(d.password or "")):
        return JSONResponse({"error": "Password is incorrect - account not deleted."}, status_code=403)
    uid = user["id"]
    request.app.state.repo.delete_user_data(uid)
    avatar_path(uid).unlink(missing_ok=True)
    db = get_db()
    db.execute("DELETE FROM users WHERE id=?", (uid,))
    db.commit()
    request.session.clear()
    return {"ok": True}
