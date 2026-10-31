import sqlite3

from flask import Blueprint, current_app, g, jsonify, redirect, render_template, request, send_file, session

from src import gamify
from src.auth import avatar as avatar_mod
from src.auth.security import (EMAIL_RE, avatar_path, hash_password, log_in, password_problem, safe_next, verify_password)
from src.database.db import get_db

bp = Blueprint("auth", __name__)
FIELDS = {"name": 60, "job_title": 80, "company": 80, "location": 80, "bio": 300}


def public_user(row) -> dict:
    p = avatar_path(row["id"])
    return {"id": row["id"], "name": row["name"], "email": row["email"], "job_title": row["job_title"], "company": row["company"],
            "location": row["location"], "bio": row["bio"], "created_at": row["created_at"],
            "has_avatar": p.exists(), "avatar_v": int(p.stat().st_mtime) if p.exists() else 0}


# ---------- pages ----------
@bp.get("/login")
def login_page():
    if g.user:
        return redirect(safe_next(request.args.get("next")))
    return render_template("auth.html", mode="login", page="auth", next_url=safe_next(request.args.get("next")))


@bp.get("/register")
def register_page():
    if g.user:
        return redirect("/dashboard")
    return render_template("auth.html", mode="register", page="auth", next_url="/dashboard")


@bp.get("/profile")
def profile_page():
    return render_template("profile.html", page="profile")


# ---------- auth API ----------
@bp.post("/api/auth/register")
def register():
    d = request.get_json(silent=True) or {}
    name, email, pw = str(d.get("name", "")).strip(), str(d.get("email", "")).strip().lower(), d.get("password", "")
    if not (2 <= len(name) <= FIELDS["name"]):
        return jsonify(error="Please enter your name (2-60 characters)."), 422
    if not EMAIL_RE.match(email):
        return jsonify(error="Please enter a valid email address."), 422
    problem = password_problem(pw)
    if problem:
        return jsonify(error=problem), 422
    db = get_db()
    try:
        cur = db.execute("INSERT INTO users (email, name, password_hash) VALUES (?, ?, ?)", (email, name, hash_password(pw)))
        db.commit()
    except sqlite3.IntegrityError:
        return jsonify(error="An account with this email already exists. Try signing in."), 409
    log_in(cur.lastrowid)
    return jsonify(ok=True, next=safe_next(d.get("next")))


@bp.post("/api/auth/login")
def login():
    d = request.get_json(silent=True) or {}
    email, pw = str(d.get("email", "")).strip().lower(), str(d.get("password", ""))
    throttle = current_app.login_throttle
    wait = throttle.blocked(email)
    if wait:
        return jsonify(error=f"Too many failed attempts. Try again in {wait // 60 + 1} minute(s)."), 429
    row = get_db().execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    if not row or not verify_password(row["password_hash"], pw):
        throttle.fail(email)
        return jsonify(error="Incorrect email or password."), 401          # same message either way (no user enumeration)
    throttle.clear(email)
    log_in(row["id"])
    return jsonify(ok=True, next=safe_next(d.get("next")))


@bp.post("/api/auth/logout")
def logout():
    session.clear()
    return jsonify(ok=True)


# ---------- profile API ----------
@bp.get("/api/profile")
def get_profile():
    return jsonify(user=public_user(g.user), stats=gamify.summary(g.user["id"]))


@bp.put("/api/profile")
def update_profile():
    d = request.get_json(silent=True) or {}
    vals = {k: str(d.get(k, g.user[k]) or "").strip() for k in FIELDS}
    if not (2 <= len(vals["name"]) <= FIELDS["name"]):
        return jsonify(error="Name must be 2-60 characters."), 422
    for k, limit in FIELDS.items():
        if len(vals[k]) > limit:
            return jsonify(error=f"{k.replace('_', ' ').title()} is too long (max {limit} characters)."), 422
    db = get_db()
    db.execute("UPDATE users SET name=?, job_title=?, company=?, location=?, bio=? WHERE id=?",
               (vals["name"], vals["job_title"], vals["company"], vals["location"], vals["bio"], g.user["id"]))
    db.commit()
    return jsonify(ok=True, user=public_user(db.execute("SELECT * FROM users WHERE id=?", (g.user["id"],)).fetchone()))


@bp.post("/api/profile/password")
def change_password():
    d = request.get_json(silent=True) or {}
    if not verify_password(g.user["password_hash"], str(d.get("current", ""))):
        return jsonify(error="Your current password is incorrect."), 403
    problem = password_problem(d.get("new", ""))
    if problem:
        return jsonify(error=problem), 422
    db = get_db()
    db.execute("UPDATE users SET password_hash=? WHERE id=?", (hash_password(d["new"]), g.user["id"]))
    db.commit()
    return jsonify(ok=True)


@bp.post("/api/profile/avatar")
def upload_avatar():
    f = request.files.get("avatar")
    if not f:
        return jsonify(error="Choose an image first."), 400
    try:
        png = avatar_mod.process(f.read(avatar_mod.MAX_BYTES + 1))
    except avatar_mod.AvatarError as e:
        return jsonify(error=str(e)), 422
    p = avatar_path(g.user["id"]); p.parent.mkdir(parents=True, exist_ok=True); p.write_bytes(png)
    return jsonify(ok=True, user=public_user(g.user))


@bp.delete("/api/profile/avatar")
def delete_avatar():
    avatar_path(g.user["id"]).unlink(missing_ok=True)
    return jsonify(ok=True, user=public_user(g.user))


@bp.get("/avatar/me")
def my_avatar():
    p = avatar_path(g.user["id"])
    if not p.exists():
        return ("", 404)
    resp = send_file(p, mimetype="image/png")
    resp.headers["Cache-Control"] = "private, max-age=0, must-revalidate"
    return resp


@bp.post("/api/profile/delete")
def delete_account():
    d = request.get_json(silent=True) or {}
    if not verify_password(g.user["password_hash"], str(d.get("password", ""))):
        return jsonify(error="Password is incorrect - account not deleted."), 403
    uid = g.user["id"]
    current_app.repo.delete_user_data(uid)
    avatar_path(uid).unlink(missing_ok=True)
    db = get_db(); db.execute("DELETE FROM users WHERE id=?", (uid,)); db.commit()
    session.clear()
    return jsonify(ok=True)
