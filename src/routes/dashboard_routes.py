from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse

from src.analytics import extras, kpi
from src.analytics.filters import apply_filters, filter_options
from src.auth.security import render_template, require_user
from src.database.repository import DatasetNotFound
from src.utils import jsonable

router = APIRouter(tags=["dashboard"])


@router.get("/", include_in_schema=False)
def index(request: Request):
    return render_template(request, "index.html", page="home")


@router.get("/dashboard", include_in_schema=False)
def dashboard(request: Request):
    return render_template(request, "dashboard.html", page="dashboard")


@router.get("/investigation", include_in_schema=False)
def investigation(request: Request):
    return render_template(request, "investigation.html", page="investigation")


@router.get("/reports", include_in_schema=False)
def reports(request: Request):
    return render_template(request, "reports.html", page="reports")


@router.get("/lab", include_in_schema=False)
def lab(request: Request):
    return render_template(request, "lab.html", page="lab")


@router.get("/data", include_in_schema=False)
def data_page(request: Request):
    return render_template(request, "data.html", page="data")


@router.get("/api/dashboard")
def api_dashboard(
    request: Request,
    dataset: str = "",
    region: str | None = None,
    category: str | None = None,
    product: str | None = None,
    start: str | None = None,
    end: str | None = None,
    user=Depends(require_user),
):
    repo = request.app.state.repo
    try:
        full = repo.load_dataset(dataset, user["id"])
        meta = repo.get_meta(dataset, user["id"])
    except DatasetNotFound:
        return JSONResponse({"error": "Dataset not found. Upload a file first."}, status_code=404)
    df = apply_filters(full, region, category, product, start, end)
    if df.empty:
        return JSONResponse({"error": "No rows match these filters - try widening them."}, status_code=422)
    monthly = kpi.monthly_summary(df)
    return jsonable({
        "meta": meta,
        "options": filter_options(full),
        "filtered_rows": len(df),
        "kpis": kpi.compute_kpis(df),
        "monthly": monthly,
        "products": kpi.group_summary(df, "product"),
        "categories": kpi.group_summary(df, "category"),
        "regions": kpi.group_summary(df, "region"),
        "daily": kpi.daily_series(df),
        "heatmap": extras.heatmap(df),
        "discount_bands": extras.discount_bands(df),
        "forecast": extras.forecast_next_month(monthly),
        "pulse": extras.business_pulse(df, monthly),
        "health": extras.health_score(df, monthly, meta.get("quality", {}).get("quality_score")),
    })
