import io

import pytest
from PIL import Image

from conftest import PASSWORD, Api


def _png(size=(400, 300), color=(200, 30, 90)):
    buf = io.BytesIO(); Image.new("RGB", size, color).save(buf, "PNG"); buf.seek(0); return buf


def test_pages_and_api_require_login(anon):
    assert anon.get("/").status_code == 200 and anon.get("/login").status_code == 200 and anon.get("/register").status_code == 200
    r = anon.get("/dashboard"); assert r.status_code == 302 and "/login" in r.headers["Location"]
    assert anon.get("/profile").status_code == 302
    r = anon.get("/api/datasets"); assert r.status_code == 401 and r.json["login_required"]
    assert anon.get("/static/css/style.css").status_code == 200          # static stays public


def test_register_validation_and_duplicates(anon):
    assert anon.register(name="A").status_code == 422                     # name too short
    assert anon.register(email="not-an-email").status_code == 422
    assert anon.register(password="short1").status_code == 422
    assert anon.register(password="allletters").status_code == 422        # needs a digit
    assert anon.register().status_code == 200
    again = Api(anon.app); r = again.register(email="TESTER@example.com")   # same email, different case
    assert r.status_code == 409


def test_login_logout_and_generic_error(client, app):
    client.post("/api/auth/logout")
    assert client.get("/api/profile").status_code == 401
    wrong = client.post("/api/auth/login", json={"email": "tester@example.com", "password": "nope12345"})
    nouser = client.post("/api/auth/login", json={"email": "ghost@example.com", "password": "nope12345"})
    assert wrong.status_code == nouser.status_code == 401 and wrong.json["error"] == nouser.json["error"]   # no user enumeration
    ok = client.post("/api/auth/login", json={"email": "tester@example.com", "password": PASSWORD, "next": "//evil.com"})
    assert ok.status_code == 200 and ok.json["next"] == "/dashboard"      # open redirect blocked
    assert client.get("/api/profile").json["user"]["email"] == "tester@example.com"


def test_login_throttle(anon):
    anon.register(); anon.post("/api/auth/logout")
    for _ in range(5):
        assert anon.post("/api/auth/login", json={"email": "tester@example.com", "password": "bad-pass-1"}).status_code == 401
    r = anon.post("/api/auth/login", json={"email": "tester@example.com", "password": PASSWORD})
    assert r.status_code == 429                                           # locked even with the right password


def test_csrf_required(client):
    raw = client.c.post("/api/auth/logout")                               # no header
    assert raw.status_code == 403
    bad = client.c.post("/api/auth/logout", headers={"X-CSRF-Token": "wrong"})
    assert bad.status_code == 403


def test_passwords_are_hashed(client, app):
    import sqlite3
    h = sqlite3.connect(app.state.config.DB_PATH).execute("SELECT password_hash FROM users").fetchone()[0]
    assert PASSWORD not in h and h.startswith(("scrypt:", "pbkdf2:"))


def test_edit_profile_and_change_password(client):
    r = client.put("/api/profile", json={"name": "New Name", "job_title": "Analyst", "company": "ACME", "location": "Bengaluru", "bio": "Hi"})
    assert r.status_code == 200 and r.json["user"]["job_title"] == "Analyst"
    assert client.put("/api/profile", json={"name": "X"}).status_code == 422
    assert client.put("/api/profile", json={"name": "Okay Name", "bio": "x" * 301}).status_code == 422
    assert client.post("/api/profile/password", json={"current": "wrong", "new": "Newpass123"}).status_code == 403
    assert client.post("/api/profile/password", json={"current": PASSWORD, "new": "weak"}).status_code == 422
    assert client.post("/api/profile/password", json={"current": PASSWORD, "new": "Newpass123"}).status_code == 200
    client.post("/api/auth/logout")
    assert client.post("/api/auth/login", json={"email": "tester@example.com", "password": "Newpass123"}).status_code == 200


def test_avatar_upload_validation_and_delete(client):
    r = client.post("/api/profile/avatar", data={"avatar": (_png(), "me.png")}, content_type="multipart/form-data")
    assert r.status_code == 200 and r.json["user"]["has_avatar"]
    img = Image.open(io.BytesIO(client.get("/avatar/me").data)); assert img.size == (256, 256)     # cropped square
    fake = client.post("/api/profile/avatar", data={"avatar": (io.BytesIO(b"<script>alert(1)</script>"), "x.png")}, content_type="multipart/form-data")
    assert fake.status_code == 422                                        # not really an image, despite .png name
    big = client.post("/api/profile/avatar", data={"avatar": (io.BytesIO(b"\x89PNG" + b"0" * (3 * 1024 * 1024 + 10)), "big.png")}, content_type="multipart/form-data")
    assert big.status_code == 422
    assert client.delete("/api/profile/avatar").json["user"]["has_avatar"] is False
    assert client.get("/avatar/me").status_code == 404


def test_datasets_are_private_between_users(client, other):
    ds = client.post("/api/sample", json={"kind": "clean"}).json["dataset"]["id"]
    assert client.get(f"/api/dashboard?dataset={ds}").status_code == 200
    for url in (f"/api/dashboard?dataset={ds}", f"/api/preview?dataset={ds}", f"/api/export/{ds}/clean.csv", f"/api/options?dataset={ds}",
                f"/api/goals?dataset={ds}", f"/api/notes?dataset={ds}", f"/api/whatif/segments?dataset={ds}"):
        assert other.get(url).status_code == 404, url
    assert other.post("/api/ask", json={"dataset": ds, "question": "why"}).status_code == 404
    assert other.post(f"/api/report/{ds}").status_code == 404
    assert other.get(f"/api/report/{ds}").status_code == 404
    assert other.get("/api/datasets").json == []


def test_delete_account_removes_everything(client, app):
    ds = client.post("/api/sample", json={"kind": "clean"}).json["dataset"]["id"]
    client.post(f"/api/report/{ds}")
    assert client.post("/api/profile/delete", json={"password": "wrong"}).status_code == 403
    assert client.post("/api/profile/delete", json={"password": PASSWORD}).status_code == 200
    assert list(app.state.config.PROCESSED_FOLDER.glob("*")) == [] and list(app.state.config.REPORT_FOLDER.glob("*")) == []
    assert client.get("/api/profile").status_code == 401


def test_session_endpoint_and_cors(anon, client):
    # Anonymous session check
    r = anon.get("/api/auth/session")
    assert r.status_code == 200
    assert r.json["authenticated"] is False and r.json["user"] is None
    assert len(r.json["csrf_token"]) > 0

    # Authenticated session check
    r_auth = client.get("/api/auth/session")
    assert r_auth.status_code == 200
    assert r_auth.json["authenticated"] is True and r_auth.json["user"]["email"] == "tester@example.com"
    assert r_auth.json["stats"]["level"] >= 1

    # CORS preflight OPTIONS request
    opt = anon.c.options("/api/auth/session", headers={"Origin": "https://example.netlify.app"})
    assert opt.status_code in (200, 204)
    assert opt.headers.get("Access-Control-Allow-Origin") == "https://example.netlify.app"
    assert "Origin" in opt.headers.get("Vary", "")
    assert "X-CSRF-Token" in opt.headers.get("Access-Control-Allow-Headers", "")
    assert anon.get("/api/health").json == {"status": "ok"}

    # FastAPI OpenAPI schema & docs available
    spec = anon.get("/openapi.json")
    assert spec.status_code == 200 and "/api/dashboard" in spec.json["paths"] and "/api/auth/session" in spec.json["paths"]
    assert anon.get("/docs").status_code == 200


def test_spa_csrf_rotation_and_cors_allowlist(app, anon):
    # 1. Fetch initial session CSRF token (like Next.js AuthProvider on mount)
    s0 = anon.c.get("/api/auth/session")
    t0 = s0.json()["csrf_token"]

    # 2. Register with initial token -> returns rotated token & user
    reg = anon.c.post(
        "/api/auth/register",
        json={"name": "SPA User", "email": "spa@example.com", "password": PASSWORD},
        headers={"X-CSRF-Token": t0},
    )
    assert reg.status_code == 200 and reg.json()["user"]["email"] == "spa@example.com"
    t1 = reg.json()["csrf_token"]
    assert t1 and t1 != t0

    # 3. Old token must now be rejected, rotated token must succeed
    assert anon.c.post("/api/auth/logout", headers={"X-CSRF-Token": t0}).status_code == 403
    assert anon.c.post("/api/auth/logout", headers={"X-CSRF-Token": t1}).status_code == 200

    # 4. Login returns a rotated token & user as well
    s1 = anon.c.get("/api/auth/session")
    login = anon.c.post(
        "/api/auth/login",
        json={"email": "spa@example.com", "password": PASSWORD},
        headers={"X-CSRF-Token": s1.json()["csrf_token"]},
    )
    assert login.status_code == 200 and login.json()["user"]["name"] == "SPA User"
    assert anon.c.post("/api/auth/logout", headers={"X-CSRF-Token": login.json()["csrf_token"]}).status_code == 200

    # 5. Restricted CORS_ORIGINS blocks unlisted origins
    app.state.config.CORS_ORIGINS = "https://allowed.netlify.app"
    ok_cors = anon.c.get("/api/health", headers={"Origin": "https://allowed.netlify.app"})
    bad_cors = anon.c.get("/api/health", headers={"Origin": "https://evil.example.com"})
    assert ok_cors.headers.get("Access-Control-Allow-Origin") == "https://allowed.netlify.app"
    assert bad_cors.headers.get("Access-Control-Allow-Origin") is None

