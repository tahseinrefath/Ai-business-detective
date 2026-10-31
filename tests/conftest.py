import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import create_app  # noqa: E402
from config import Config  # noqa: E402

PASSWORD = "Sup3rsecret"


class Api:
    """Thin wrapper over the Flask test client that adds the CSRF header like the real JS does."""

    def __init__(self, app):
        self.c = app.test_client()
        self.c.get("/login")                                    # creates the session + CSRF token

    def _kw(self, kw, csrf=True):
        headers = dict(kw.pop("headers", {}) or {})
        if csrf:
            with self.c.session_transaction() as s:
                token = s.get("csrf", "")
            if not token:                                     # e.g. right after sign-out: a real page load issues a new token
                self.c.get("/login")
                with self.c.session_transaction() as s:
                    token = s.get("csrf", "")
            headers["X-CSRF-Token"] = token
        kw["headers"] = headers
        return kw

    def get(self, url, **kw): return self.c.get(url, **self._kw(kw, False))
    def post(self, url, **kw): return self.c.post(url, **self._kw(kw))
    def put(self, url, **kw): return self.c.put(url, **self._kw(kw))
    def delete(self, url, **kw): return self.c.delete(url, **self._kw(kw))

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
    """A second, separate signed-in user."""
    api = Api(app)
    assert api.register("second@example.com", "Second User").status_code == 200
    return api
