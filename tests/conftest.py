import sys
from pathlib import Path

from fastapi.testclient import TestClient
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import create_app  # noqa: E402
from config import Config  # noqa: E402

PASSWORD = "Sup3rsecret"


class _Resp:
    """Compatibility wrapper exposing `.json` and `.data` over Starlette/httpx TestClient responses."""

    def __init__(self, r):
        self._r = r
        self.status_code = r.status_code
        self.headers = r.headers
        self.data = r.content

    @property
    def json(self):
        try:
            return self._r.json()
        except Exception:
            return None


class Api:
    """Thin wrapper over FastAPI TestClient that manages session cookies and X-CSRF-Token like the real frontend."""

    def __init__(self, app):
        self.app = app
        self.c = TestClient(app, follow_redirects=False)
        self._csrf = ""
        self._refresh_csrf()

    def _refresh_csrf(self):
        r = self.c.get("/api/auth/session")
        if r.status_code == 200:
            self._csrf = r.json().get("csrf_token", "")

    def _kw(self, kw, csrf=True):
        headers = dict(kw.pop("headers", {}) or {})
        content_type = kw.pop("content_type", None)
        if content_type == "multipart/form-data" and "data" in kw:
            raw_data = kw.pop("data") or {}
            files = {}
            form = {}
            for k, v in raw_data.items():
                if isinstance(v, tuple) and len(v) == 2:
                    buf, filename = v
                    files[k] = (filename, buf)
                else:
                    form[k] = v
            if files:
                kw["files"] = files
            if form:
                kw["data"] = form
        if csrf:
            if not self._csrf:
                self._refresh_csrf()
            headers["X-CSRF-Token"] = self._csrf
        kw["headers"] = headers
        return kw

    def _call(self, method: str, url: str, csrf: bool, **kw):
        res = self.c.request(method.upper(), url, **self._kw(kw, csrf=csrf))
        try:
            payload = res.json()
            if isinstance(payload, dict) and payload.get("csrf_token"):
                self._csrf = payload["csrf_token"]
        except Exception:
            pass
        if url in ("/api/auth/logout", "/api/profile/delete") and res.status_code == 200:
            self._csrf = ""
        return _Resp(res)

    def get(self, url, **kw): return self._call("get", url, False, **kw)
    def post(self, url, **kw): return self._call("post", url, True, **kw)
    def put(self, url, **kw): return self._call("put", url, True, **kw)
    def delete(self, url, **kw): return self._call("delete", url, True, **kw)

    def register(self, email="tester@example.com", name="Test User", password=PASSWORD):
        return self.post("/api/auth/register", json={"name": name, "email": email, "password": password})


@pytest.fixture()
def app(tmp_path):
    class T(Config):
        TESTING = True
        PROCESSED_FOLDER = tmp_path / "p"
        REPORT_FOLDER = tmp_path / "r"
        UPLOAD_FOLDER = tmp_path / "u"
        AVATAR_FOLDER = tmp_path / "a"
        DB_PATH = tmp_path / "test.db"
        SECRET_KEY = "test-secret"
        ANTHROPIC_API_KEY = ""
    return create_app(T)


@pytest.fixture()
def anon(app):
    return Api(app)


@pytest.fixture()
def client(app):
    api = Api(app)
    assert api.register().status_code == 200
    return api


@pytest.fixture()
def other(app):
    api = Api(app)
    assert api.register(email="other@example.com", name="Other User").status_code == 200
    return api
