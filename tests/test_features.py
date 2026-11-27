"""Goals, case notes, what-if lab, health score, ranks and page rendering."""
import pandas as pd

from src.analytics import extras, kpi, whatif
from src.data_processing import cleaner, loader
from pathlib import Path

SAMPLE = Path(__file__).resolve().parents[1] / "data" / "sample" / "sample_sales.csv"


def _ds(client):
    return client.post("/api/sample", json={"kind": "clean"}).json["dataset"]["id"]


def test_lab_and_auth_pages_render(client, anon):
    for url in ("/lab", "/dashboard", "/investigation", "/data", "/reports", "/profile"):
        assert client.get(url).status_code == 200, url
    for url, marker in (("/login", b"authForm"), ("/register", b"authForm")):
        assert marker in anon.get(url).data
    home_out = anon.get("/").data
    assert b"Create your free account" in home_out and b'id="upload"' not in home_out      # signed-out home has no upload box
    assert b'id="upload"' in client.get("/").data                                          # signed-in home does


def test_health_score_is_transparent_and_bounded():
    df, q = cleaner.clean(loader.load_file(SAMPLE))
    h = extras.health_score(df, kpi.monthly_summary(df), q["quality_score"])
    assert 0 <= h["score"] <= 100 and h["grade"] in {"Strong", "Healthy", "Watch closely", "At risk"}
    assert [p["name"] for p in h["parts"]] == ["Growth", "Profitability", "Stability", "Data quality"]
    assert sum(p["max"] for p in h["parts"]) == 100 and round(sum(p["points"] for p in h["parts"])) == h["score"]
    assert h["parts"][0]["points"] < 5            # the planted ~19% sales decline must hurt the growth score


def test_health_score_neutral_when_not_enough_history():
    df = pd.DataFrame({"order_date": pd.to_datetime(["2026-09-01", "2026-09-02"]), "sales": [100.0, 120.0], "profit": [10.0, 12.0]})
    df["month"] = "2026-09"
    h = extras.health_score(df, kpi.monthly_summary(df))
    assert h["parts"][0]["points"] == 15 and "two months" in h["parts"][0]["detail"]


def test_dashboard_returns_health(client):
    h = client.get(f"/api/dashboard?dataset={_ds(client)}").json["health"]
    assert "score" in h and len(h["parts"]) == 4


def test_whatif_math_and_limits():
    base = {"orders": 10, "sales": 100000.0, "profit": 10000.0, "margin": 10.0, "month_total_profit": 50000.0}
    same = whatif.simulate(base)
    assert same["delta_profit"] == 0
    up = whatif.simulate(base, order_change_pct=50)                       # +50% orders at same AOV and margin
    assert round(up["scenario"]["profit"]) == 15000 and round(up["pct_of_month_profit"], 1) == 10.0
    assert whatif.simulate(base, order_change_pct=9999)["inputs"]["order_change_pct"] == 500   # clamped, not trusted


def test_whatif_api_and_xp_only_on_commit(client):
    ds = _ds(client)
    seg = client.get(f"/api/whatif/segments?dataset={ds}").json["segments"][0]["name"]
    xp0 = client.get("/api/profile").json["stats"]["counts"]["whatif"]
    r = client.post("/api/whatif", json={"dataset": ds, "segment": seg, "order_change_pct": 20})
    assert r.status_code == 200 and r.json["scenario"]["orders"] > r.json["baseline"]["orders"]
    assert client.get("/api/profile").json["stats"]["counts"]["whatif"] == xp0            # slider drag: no XP
    client.post("/api/whatif", json={"dataset": ds, "segment": seg, "commit": True})
    assert client.get("/api/profile").json["stats"]["counts"]["whatif"] == xp0 + 1        # released: counts
    assert client.post("/api/whatif", json={"dataset": ds, "segment": "Nope · Nowhere"}).status_code == 422


def test_goals_crud_and_validation(client):
    ds = _ds(client)
    assert client.put("/api/goals", json={"dataset": ds, "metric": "profit", "amount": -5}).status_code == 422
    assert client.put("/api/goals", json={"dataset": ds, "metric": "revenue", "amount": 100}).status_code == 422
    assert client.put("/api/goals", json={"dataset": ds, "metric": "profit", "amount": "abc"}).status_code == 422
    assert client.put("/api/goals", json={"dataset": ds, "metric": "profit", "amount": 500000}).status_code == 200
    assert client.put("/api/goals", json={"dataset": ds, "metric": "profit", "amount": 600000}).status_code == 200   # upsert
    goals = client.get(f"/api/goals?dataset={ds}").json["goals"]
    assert len(goals) == 1 and goals[0]["target"] == 600000 and 0 <= goals[0]["pct"]
    client.delete("/api/goals", json={"dataset": ds, "metric": "profit"})
    assert client.get(f"/api/goals?dataset={ds}").json["goals"] == []


def test_notes_crud_privacy_and_limits(client, other):
    ds = _ds(client)
    assert client.post("/api/notes", json={"dataset": ds, "text": "   "}).status_code == 422
    assert client.post("/api/notes", json={"dataset": ds, "text": "x" * 501}).status_code == 422
    assert client.post("/api/notes", json={"dataset": ds, "text": "Ask the South team <b>about</b> discounts"}).status_code == 201
    notes = client.get(f"/api/notes?dataset={ds}").json["notes"]
    assert len(notes) == 1 and "<b>" in notes[0]["text"]                  # stored verbatim; the UI escapes it on display
    assert other.delete(f"/api/notes/{notes[0]['id']}").status_code == 404   # another user cannot delete it
    assert other.post("/api/notes", json={"dataset": ds, "text": "hi"}).status_code == 404
    assert client.delete(f"/api/notes/{notes[0]['id']}").status_code == 200


def test_ranks_and_badges_progress(client):
    s0 = client.get("/api/profile").json["stats"]
    assert s0["level"] == 1 and not any(b["earned"] for b in s0["badges"] if b["id"] == "first_case")
    _ds(client)
    s1 = client.get("/api/profile").json["stats"]
    assert s1["xp"] > s0["xp"] and any(b["id"] == "first_case" and b["earned"] for b in s1["badges"])


def test_front_end_escapes_user_text():
    """User-controlled strings (note text, names) must be rendered through esc() in the scripts that display them."""
    root = Path(__file__).resolve().parents[1] / "static" / "js"
    lab = (root / "lab.js").read_text(encoding="utf-8")
    assert "esc(n.text)" in lab and "esc(x.metric)" in lab
    assert "esc(" in (root / "profile.js").read_text(encoding="utf-8")
