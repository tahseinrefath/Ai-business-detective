"""Goals, case notes and the what-if lab (all per-user)."""
import calendar

from fastapi import APIRouter, Body, Depends, Request
from fastapi.responses import JSONResponse

from src import gamify
from src.analytics import trends, whatif
from src.auth.security import require_user
from src.database.db import get_db
from src.database.repository import DatasetNotFound
from src.schemas import GoalDeleteRequest, GoalSetRequest, NoteCreateRequest, WhatIfRequest
from src.utils import jsonable

router = APIRouter(tags=["lab"])


def _owned(request: Request, uid: int, ds: str):
    """Return (df, meta) for a dataset the signed-in user owns."""
    repo = request.app.state.repo
    return repo.load_dataset(ds, uid), repo.get_meta(ds, uid)


# ---------------- goals ----------------
@router.get("/api/goals")
def goals_list(request: Request, dataset: str = "", user=Depends(require_user)):
    try:
        df, _ = _owned(request, user["id"], dataset)
    except DatasetNotFound:
        return JSONResponse({"error": "Dataset not found."}, status_code=404)
    latest = sorted(df["month"].unique())[-1]
    m = df[df["month"] == latest]
    last_day = int(m["order_date"].max().day)
    month_len = calendar.monthrange(*map(int, latest.split("-")))[1]
    days_left = max(month_len - last_day, 0)
    rows = get_db().execute(
        "SELECT metric, amount FROM goals WHERE user_id=? AND dataset_id=?",
        (user["id"], dataset),
    ).fetchall()
    out = []
    for r in rows:
        actual = float(m[r["metric"]].sum())
        remaining = max(r["amount"] - actual, 0)
        out.append({
            "metric": r["metric"],
            "target": r["amount"],
            "actual": actual,
            "pct": actual / r["amount"] * 100,
            "remaining": remaining,
            "days_left": days_left,
            "needed_per_day": (remaining / days_left) if days_left else None,
        })
    return jsonable({"month": latest, "goals": out})


@router.put("/api/goals")
def goals_set(
    request: Request,
    d: GoalSetRequest = Body(default_factory=GoalSetRequest),
    user=Depends(require_user),
):
    ds = str(d.dataset or "")
    try:
        _owned(request, user["id"], ds)
    except DatasetNotFound:
        return JSONResponse({"error": "Dataset not found."}, status_code=404)
    try:
        amount = float(d.amount)
    except (TypeError, ValueError):
        return JSONResponse({"error": "Enter a target amount."}, status_code=422)
    if d.metric not in ("sales", "profit") or not (0 < amount < 1e12):
        return JSONResponse({"error": "Choose sales or profit and enter a positive amount."}, status_code=422)
    db = get_db()
    db.execute(
        "INSERT INTO goals (user_id, dataset_id, metric, amount) VALUES (?,?,?,?) "
        "ON CONFLICT(user_id, dataset_id, metric) DO UPDATE SET amount=excluded.amount",
        (user["id"], ds, d.metric, amount),
    )
    db.commit()
    gamify.record(user["id"], "goal")
    return {"ok": True}


@router.delete("/api/goals")
def goals_delete(
    request: Request,
    dataset: str | None = None,
    metric: str | None = None,
    d: GoalDeleteRequest | None = Body(default=None),
    user=Depends(require_user),
):
    ds = str((d.dataset if d and d.dataset else dataset) or "")
    met = (d.metric if d and d.metric is not None else metric)
    try:
        _owned(request, user["id"], ds)
    except DatasetNotFound:
        return JSONResponse({"error": "Dataset not found."}, status_code=404)
    db = get_db()
    db.execute("DELETE FROM goals WHERE user_id=? AND dataset_id=? AND metric=?", (user["id"], ds, met))
    db.commit()
    return {"ok": True}


# ---------------- case notes ----------------
@router.get("/api/notes")
def notes_list(request: Request, dataset: str = "", user=Depends(require_user)):
    try:
        _owned(request, user["id"], dataset)
    except DatasetNotFound:
        return JSONResponse({"error": "Dataset not found."}, status_code=404)
    rows = get_db().execute(
        "SELECT id, text, created_at FROM notes WHERE user_id=? AND dataset_id=? ORDER BY id DESC",
        (user["id"], dataset),
    ).fetchall()
    return {"notes": [dict(r) for r in rows]}


@router.post("/api/notes", status_code=201)
def notes_add(
    request: Request,
    d: NoteCreateRequest = Body(default_factory=NoteCreateRequest),
    user=Depends(require_user),
):
    ds = str(d.dataset or "")
    text = str(d.text or "").strip()
    try:
        _owned(request, user["id"], ds)
    except DatasetNotFound:
        return JSONResponse({"error": "Dataset not found."}, status_code=404)
    if not text or len(text) > 500:
        return JSONResponse({"error": "A note must be 1-500 characters."}, status_code=422)
    db = get_db()
    count = db.execute("SELECT COUNT(*) FROM notes WHERE user_id=? AND dataset_id=?", (user["id"], ds)).fetchone()[0]
    if count >= 100:
        return JSONResponse({"error": "Note limit reached for this dataset (100)."}, status_code=422)
    db.execute("INSERT INTO notes (user_id, dataset_id, text) VALUES (?,?,?)", (user["id"], ds, text))
    db.commit()
    gamify.record(user["id"], "note")
    return JSONResponse({"ok": True}, status_code=201)


@router.delete("/api/notes/{note_id}")
def notes_delete(note_id: int, user=Depends(require_user)):
    db = get_db()
    cur = db.execute("DELETE FROM notes WHERE id=? AND user_id=?", (note_id, user["id"]))   # can only delete your own
    db.commit()
    return {"ok": True} if cur.rowcount else JSONResponse({"error": "Note not found."}, status_code=404)


# ---------------- what-if lab ----------------
def _latest_pair(df):
    try:
        return trends.latest_two_months(df)
    except ValueError:
        months = sorted(df["month"].unique())
        return months[0], months[-1]


@router.get("/api/whatif/segments")
def whatif_segments(request: Request, dataset: str = "", user=Depends(require_user)):
    try:
        df, _ = _owned(request, user["id"], dataset)
    except DatasetNotFound:
        return JSONResponse({"error": "Dataset not found."}, status_code=404)
    prev, cur = _latest_pair(df)
    return jsonable({"current": cur, "previous": prev, "segments": whatif.list_segments(df, cur, prev)[:12]})


@router.post("/api/whatif")
def whatif_run(
    request: Request,
    d: WhatIfRequest = Body(default_factory=WhatIfRequest),
    user=Depends(require_user),
):
    try:
        df, _ = _owned(request, user["id"], str(d.dataset or ""))
    except DatasetNotFound:
        return JSONResponse({"error": "Dataset not found."}, status_code=404)
    prev, cur = _latest_pair(df)
    seg = str(d.segment or "")
    try:
        base = whatif.baseline(df, cur, seg)
        res = whatif.simulate(base, d.order_change_pct, d.price_change_pct, d.margin_change_pts)
        prev_orders = int(((df["month"] == prev) & ((df["product"] + " · " + df["region"]) == seg)).sum())
    except (ValueError, TypeError):
        return JSONResponse({"error": "Could not run that scenario - check the segment and numbers."}, status_code=422)
    if d.commit is True:                  # only count a scenario when the slider is released, not on every drag
        gamify.record(user["id"], "whatif")
    restore = ((prev_orders / base["orders"] - 1) * 100) if base["orders"] and prev_orders else None
    return jsonable({
        "month": cur,
        "segment": seg,
        "baseline": base,
        "previous_orders": prev_orders,
        "restore_order_change_pct": restore,
        **res,
    })
