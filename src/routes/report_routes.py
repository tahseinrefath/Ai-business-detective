from flask import Blueprint, Response, current_app, g, jsonify, request

from src import gamify

from src.ai.insight_generator import generate_explanation
from src.analytics import kpi
from src.analytics.investigation import investigate
from src.database.repository import DatasetNotFound
from src.reports.report_generator import generate_html

bp = Blueprint("reports_api", __name__)


@bp.post("/api/report/<ds_id>")
def create_report(ds_id):
    repo = current_app.repo
    try:
        uid = g.user["id"]
        df, meta = repo.load_dataset(ds_id, uid), dict(repo.get_meta(ds_id, uid), prepared_by=g.user["name"])
        body = request.get_json(silent=True) or {}
        metric = body.get("metric") if body.get("metric") in ("sales", "profit") else "profit"
        inv = investigate(df, metric, body.get("previous") or None, body.get("current") or None)
    except DatasetNotFound:
        return jsonify(error="Dataset not found."), 404
    except ValueError as e:
        return jsonify(error=str(e)), 422
    cfg = current_app.config
    expl = generate_explanation(inv, f"Why did {metric} change?", cfg["ANTHROPIC_API_KEY"], cfg["LLM_MODEL"])
    gamify.record(g.user["id"], "report")
    repo.save_report(ds_id, uid, generate_html(meta, kpi.compute_kpis(df), inv, expl, kpi.monthly_summary(df)))
    return jsonify(ok=True, url=f"/api/report/{ds_id}")


@bp.get("/api/report/<ds_id>")
def get_report(ds_id):
    try:
        path = current_app.repo.report_path(ds_id, g.user["id"]) if ds_id.isalnum() else None
    except DatasetNotFound:
        path = None
    if not path:
        return jsonify(error="Report not generated yet."), 404
    download = request.args.get("download")
    headers = {"Content-Disposition": f"attachment; filename=detective_report_{ds_id}.html"} if download else {}
    return Response(path.read_text(encoding="utf-8"), mimetype="text/html", headers=headers)
