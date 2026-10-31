"""Data explorer (search / sort / page) and CSV exports."""
import io

import pandas as pd
from flask import Blueprint, Response, current_app, g, jsonify, request

from src.analytics.contribution import rank_contributors, rank_segments
from src.analytics.trends import compare_periods
from src.database.repository import DatasetNotFound
from src.utils import jsonable

bp = Blueprint("data", __name__)
SORTABLE = {"order_date", "product", "category", "region", "quantity", "sales", "profit", "discount_pct"}


def _load(ds):
    return current_app.repo.load_dataset(ds, g.user["id"])


@bp.get("/api/preview")
def preview():
    a = request.args
    try:
        df = _load(a.get("dataset", ""))
    except DatasetNotFound:
        return jsonify(error="Dataset not found."), 404
    q = (a.get("q") or "").strip().lower()[:60]
    if q:
        mask = df[["product", "category", "region"]].apply(lambda c: c.str.lower().str.contains(q, regex=False)).any(axis=1)
        df = df[mask]
    sort = a.get("sort") if a.get("sort") in SORTABLE else "order_date"
    df = df.sort_values(sort, ascending=a.get("dir") == "asc", na_position="last")
    size = min(max(int(a.get("size", 15) or 15), 5), 100)
    page = max(int(a.get("page", 1) or 1), 1)
    rows = df.iloc[(page - 1) * size: page * size].drop(columns=["month"]).copy()
    rows["order_date"] = rows["order_date"].dt.strftime("%Y-%m-%d")
    return jsonify(jsonable({"rows": rows.to_dict("records"), "total": int(len(df)), "page": page, "size": size,
                             "pages": max(1, -(-len(df) // size))}))


def _csv_response(df: pd.DataFrame, name: str) -> Response:
    buf = io.StringIO(); df.to_csv(buf, index=False)
    return Response(buf.getvalue(), mimetype="text/csv", headers={"Content-Disposition": f"attachment; filename={name}"})


@bp.get("/api/export/<ds>/clean.csv")
def export_clean(ds):
    try:
        df = _load(ds).drop(columns=["month"])
    except DatasetNotFound:
        return jsonify(error="Dataset not found."), 404
    df["order_date"] = df["order_date"].dt.strftime("%Y-%m-%d")
    return _csv_response(df, f"cleaned_{ds}.csv")


@bp.get("/api/export/<ds>/contributors.csv")
def export_contributors(ds):
    metric = request.args.get("metric", "profit")
    try:
        df = _load(ds)
        comp = compare_periods(df, metric, request.args.get("previous") or None, request.args.get("current") or None)
    except DatasetNotFound:
        return jsonify(error="Dataset not found."), 404
    except ValueError as e:
        return jsonify(error=str(e)), 422
    p, c, d = comp["previous_period"], comp["current_period"], comp["delta"]
    frames = []
    for dim in ("category", "product", "region"):
        f = pd.DataFrame(rank_contributors(df, p, c, metric, dim, d)); f.insert(0, "dimension", dim); frames.append(f)
    f = pd.DataFrame(rank_segments(df, p, c, metric, d, top=50)); f.insert(0, "dimension", "product x region"); frames.append(f)
    return _csv_response(pd.concat(frames), f"contributors_{metric}_{p}_to_{c}.csv")


@bp.get("/api/options")
def options():
    from src.analytics.filters import filter_options
    try:
        return jsonify(filter_options(_load(request.args.get("dataset", ""))))
    except DatasetNotFound:
        return jsonify(error="Dataset not found."), 404
