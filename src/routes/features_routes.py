"""Goals, case notes and the what-if lab (all per-user)."""
import calendar

from flask import Blueprint, current_app, g, jsonify, request

from src import gamify
from src.analytics import trends, whatif
from src.database.db import get_db
from src.database.repository import DatasetNotFound
from src.utils import jsonable

bp = Blueprint("features", __name__)


def _owned(ds):
    """Return (df, meta) for a dataset the signed-in user owns."""
    repo, uid = current_app.repo, g.user["id"]
    return repo.load_dataset(ds, uid), repo.get_meta(ds, uid)


@bp.errorhandler(DatasetNotFound)
def _nf(_):
    return jsonify(error="Dataset not found."), 404


# ---------------- goals ----------------
@bp.get("/api/goals")
def goals_list():
    ds = request.args.get("dataset", "")
    df, _ = _owned(ds)
    latest = sorted(df["month"].unique())[-1]
    m = df[df["month"] == latest]
    last_day, month_len = int(m["order_date"].max().day), calendar.monthrange(*map(int, latest.split("-")))[1]
    days_left = max(month_len - last_day, 0)
    rows = get_db().execute("SELECT metric, amount FROM goals WHERE user_id=? AND dataset_id=?", (g.user["id"], ds)).fetchall()
    out = []
    for r in rows:
        actual = float(m[r["metric"]].sum())
        remaining = max(r["amount"] - actual, 0)
        out.append({"metric": r["metric"], "target": r["amount"], "actual": actual, "pct": actual / r["amount"] * 100,
                    "remaining": remaining, "days_left": days_left, "needed_per_day": (remaining / days_left) if days_left else None})
    return jsonify(jsonable({"month": latest, "goals": out}))


@bp.put("/api/goals")
def goals_set():
    d = request.get_json(silent=True) or {}
    ds, metric = str(d.get("dataset", "")), d.get("metric")
    _owned(ds)
    try:
        amount = float(d.get("amount"))
    except (TypeError, ValueError):
        return jsonify(error="Enter a target amount."), 422
    if metric not in ("sales", "profit") or not (0 < amount < 1e12):
        return jsonify(error="Choose sales or profit and enter a positive amount."), 422
    db = get_db()
    db.execute("INSERT INTO goals (user_id, dataset_id, metric, amount) VALUES (?,?,?,?) "
               "ON CONFLICT(user_id, dataset_id, metric) DO UPDATE SET amount=excluded.amount", (g.user["id"], ds, metric, amount))
    db.commit()
    gamify.record(g.user["id"], "goal")
    return jsonify(ok=True)


@bp.delete("/api/goals")
def goals_delete():
    d = request.get_json(silent=True) or {}
    _owned(str(d.get("dataset", "")))
    db = get_db()
    db.execute("DELETE FROM goals WHERE user_id=? AND dataset_id=? AND metric=?", (g.user["id"], d.get("dataset"), d.get("metric")))
    db.commit()
    return jsonify(ok=True)


# ---------------- case notes ----------------
@bp.get("/api/notes")
def notes_list():
    ds = request.args.get("dataset", ""); _owned(ds)
    rows = get_db().execute("SELECT id, text, created_at FROM notes WHERE user_id=? AND dataset_id=? ORDER BY id DESC",
                            (g.user["id"], ds)).fetchall()
    return jsonify(notes=[dict(r) for r in rows])


@bp.post("/api/notes")
def notes_add():
    d = request.get_json(silent=True) or {}
    ds, text = str(d.get("dataset", "")), str(d.get("text", "")).strip()
    _owned(ds)
    if not text or len(text) > 500:
        return jsonify(error="A note must be 1-500 characters."), 422
    db = get_db()
    count = db.execute("SELECT COUNT(*) FROM notes WHERE user_id=? AND dataset_id=?", (g.user["id"], ds)).fetchone()[0]
    if count >= 100:
        return jsonify(error="Note limit reached for this dataset (100)."), 422
    db.execute("INSERT INTO notes (user_id, dataset_id, text) VALUES (?,?,?)", (g.user["id"], ds, text))
    db.commit()
    gamify.record(g.user["id"], "note")
    return jsonify(ok=True), 201


@bp.delete("/api/notes/<int:note_id>")
def notes_delete(note_id):
    db = get_db()
    cur = db.execute("DELETE FROM notes WHERE id=? AND user_id=?", (note_id, g.user["id"]))   # can only delete your own
    db.commit()
    return jsonify(ok=True) if cur.rowcount else (jsonify(error="Note not found."), 404)


# ---------------- what-if lab ----------------
def _latest_pair(df):
    try:
        return trends.latest_two_months(df)
    except ValueError:
        months = sorted(df["month"].unique())
        return months[0], months[-1]


@bp.get("/api/whatif/segments")
def whatif_segments():
    df, _ = _owned(request.args.get("dataset", ""))
    prev, cur = _latest_pair(df)
    return jsonify(jsonable({"current": cur, "previous": prev, "segments": whatif.list_segments(df, cur, prev)[:12]}))


@bp.post("/api/whatif")
def whatif_run():
    d = request.get_json(silent=True) or {}
    df, _ = _owned(str(d.get("dataset", "")))
    prev, cur = _latest_pair(df)
    seg = str(d.get("segment", ""))
    try:
        base = whatif.baseline(df, cur, seg)
        res = whatif.simulate(base, d.get("order_change_pct", 0), d.get("price_change_pct", 0), d.get("margin_change_pts", 0))
        prev_orders = int(((df["month"] == prev) & ((df["product"] + " · " + df["region"]) == seg)).sum())
    except (ValueError, TypeError):
        return jsonify(error="Could not run that scenario - check the segment and numbers."), 422
    if d.get("commit") is True:                  # only count a scenario when the slider is released, not on every drag
        gamify.record(g.user["id"], "whatif")
    restore = ((prev_orders / base["orders"] - 1) * 100) if base["orders"] and prev_orders else None
    return jsonify(jsonable({"month": cur, "segment": seg, "baseline": base, "previous_orders": prev_orders,
                             "restore_order_change_pct": restore, **res}))
