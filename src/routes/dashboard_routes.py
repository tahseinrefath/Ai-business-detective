from flask import Blueprint, current_app, g, jsonify, render_template, request

from src.analytics import extras, kpi
from src.analytics.filters import apply_filters, filter_options
from src.database.repository import DatasetNotFound
from src.utils import jsonable

bp = Blueprint("dashboard", __name__)


@bp.get("/")
def index():
    return render_template("index.html", page="home")


@bp.get("/dashboard")
def dashboard():
    return render_template("dashboard.html", page="dashboard")


@bp.get("/investigation")
def investigation():
    return render_template("investigation.html", page="investigation")


@bp.get("/reports")
def reports():
    return render_template("reports.html", page="reports")


@bp.get("/lab")
def lab():
    return render_template("lab.html", page="lab")


@bp.get("/data")
def data_page():
    return render_template("data.html", page="data")


@bp.get("/api/dashboard")
def api_dashboard():
    a = request.args
    try:
        ds = a.get("dataset", "")
        full = current_app.repo.load_dataset(ds, g.user["id"])
        meta = current_app.repo.get_meta(ds, g.user["id"])
    except DatasetNotFound:
        return jsonify(error="Dataset not found. Upload a file first."), 404
    df = apply_filters(full, a.get("region"), a.get("category"), a.get("product"), a.get("start"), a.get("end"))
    if df.empty:
        return jsonify(error="No rows match these filters - try widening them."), 422
    monthly = kpi.monthly_summary(df)
    return jsonify(jsonable({
        "meta": meta, "options": filter_options(full), "filtered_rows": len(df), "kpis": kpi.compute_kpis(df),
        "monthly": monthly, "products": kpi.group_summary(df, "product"), "categories": kpi.group_summary(df, "category"),
        "regions": kpi.group_summary(df, "region"), "daily": kpi.daily_series(df),
        "heatmap": extras.heatmap(df), "discount_bands": extras.discount_bands(df),
        "forecast": extras.forecast_next_month(monthly), "pulse": extras.business_pulse(df, monthly),
        "health": extras.health_score(df, monthly, meta.get("quality", {}).get("quality_score"))}))
