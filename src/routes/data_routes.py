"""Data explorer (search / sort / page) and CSV exports."""
import io

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse, Response
import pandas as pd

from src.analytics.contribution import rank_contributors, rank_segments
from src.analytics.filters import filter_options
from src.analytics.trends import compare_periods
from src.auth.security import require_user
from src.database.repository import DatasetNotFound
from src.utils import jsonable

router = APIRouter(tags=["data"])
SORTABLE = {"order_date", "product", "category", "region", "quantity", "sales", "profit", "discount_pct"}


def _load(request: Request, ds: str, uid: int):
    return request.app.state.repo.load_dataset(ds, uid)


@router.get("/api/preview")
def preview(
    request: Request,
    dataset: str = "",
    q: str = "",
    sort: str = "order_date",
    dir: str = "desc",
    page: int = 1,
    size: int = 15,
    user=Depends(require_user),
):
    try:
        df = _load(request, dataset, user["id"])
    except DatasetNotFound:
        return JSONResponse({"error": "Dataset not found."}, status_code=404)
    query = (q or "").strip().lower()[:60]
    if query:
        mask = df[["product", "category", "region"]].apply(lambda c: c.str.lower().str.contains(query, regex=False)).any(axis=1)
        df = df[mask]
    sort_col = sort if sort in SORTABLE else "order_date"
    df = df.sort_values(sort_col, ascending=(dir == "asc"), na_position="last")
    page_size = min(max(int(size or 15), 5), 100)
    page_num = max(int(page or 1), 1)
    rows = df.iloc[(page_num - 1) * page_size : page_num * page_size].drop(columns=["month"]).copy()
    rows["order_date"] = rows["order_date"].dt.strftime("%Y-%m-%d")
    return jsonable({
        "rows": rows.to_dict("records"),
        "total": int(len(df)),
        "page": page_num,
        "size": page_size,
        "pages": max(1, -(-len(df) // page_size)),
    })


def _csv_response(df: pd.DataFrame, name: str) -> Response:
    buf = io.StringIO()
    df.to_csv(buf, index=False)
    return Response(
        content=buf.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={name}"},
    )


@router.get("/api/export/{ds}/clean.csv", responses={200: {"content": {"text/csv": {}}}})
def export_clean(request: Request, ds: str, user=Depends(require_user)):
    try:
        df = _load(request, ds, user["id"]).drop(columns=["month"])
    except DatasetNotFound:
        return JSONResponse({"error": "Dataset not found."}, status_code=404)
    df["order_date"] = df["order_date"].dt.strftime("%Y-%m-%d")
    return _csv_response(df, f"cleaned_{ds}.csv")


@router.get("/api/export/{ds}/contributors.csv", responses={200: {"content": {"text/csv": {}}}})
def export_contributors(
    request: Request,
    ds: str,
    metric: str = "profit",
    previous: str | None = None,
    current: str | None = None,
    user=Depends(require_user),
):
    try:
        df = _load(request, ds, user["id"])
        comp = compare_periods(df, metric, previous or None, current or None)
    except DatasetNotFound:
        return JSONResponse({"error": "Dataset not found."}, status_code=404)
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=422)
    p, c, d = comp["previous_period"], comp["current_period"], comp["delta"]
    frames = []
    for dim in ("category", "product", "region"):
        f = pd.DataFrame(rank_contributors(df, p, c, metric, dim, d))
        f.insert(0, "dimension", dim)
        frames.append(f)
    f = pd.DataFrame(rank_segments(df, p, c, metric, d, top=50))
    f.insert(0, "dimension", "product x region")
    frames.append(f)
    return _csv_response(pd.concat(frames), f"contributors_{metric}_{p}_to_{c}.csv")


@router.get("/api/options")
def options(request: Request, dataset: str = "", user=Depends(require_user)):
    try:
        return filter_options(_load(request, dataset, user["id"]))
    except DatasetNotFound:
        return JSONResponse({"error": "Dataset not found."}, status_code=404)
