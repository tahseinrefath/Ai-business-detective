from fastapi import APIRouter, Body, Depends, Request
from fastapi.responses import JSONResponse, Response

from src import gamify
from src.ai.insight_generator import generate_explanation
from src.analytics import kpi
from src.analytics.investigation import investigate
from src.auth.security import require_user
from src.database.repository import DatasetNotFound
from src.reports.report_generator import generate_html
from src.schemas import ReportCreateRequest

router = APIRouter(tags=["reports"])


@router.post("/api/report/{ds_id}")
def create_report(
    request: Request,
    ds_id: str,
    body: ReportCreateRequest = Body(default_factory=ReportCreateRequest),
    user=Depends(require_user),
):
    repo = request.app.state.repo
    uid = user["id"]
    try:
        df = repo.load_dataset(ds_id, uid)
        meta = dict(repo.get_meta(ds_id, uid), prepared_by=user["name"])
        metric = body.metric if body.metric in ("sales", "profit") else "profit"
        inv = investigate(df, metric, body.previous or None, body.current or None)
    except DatasetNotFound:
        return JSONResponse({"error": "Dataset not found."}, status_code=404)
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=422)
    cfg = request.app.state.config
    expl = generate_explanation(inv, f"Why did {metric} change?", cfg.ANTHROPIC_API_KEY, cfg.LLM_MODEL)
    gamify.record(uid, "report")
    repo.save_report(ds_id, uid, generate_html(meta, kpi.compute_kpis(df), inv, expl, kpi.monthly_summary(df)))
    return {"ok": True, "url": f"/api/report/{ds_id}"}


@router.get("/api/report/{ds_id}", responses={200: {"content": {"text/html": {}}}})
def get_report(request: Request, ds_id: str, download: str | None = None, user=Depends(require_user)):
    try:
        path = request.app.state.repo.report_path(ds_id, user["id"]) if ds_id.isalnum() else None
    except DatasetNotFound:
        path = None
    if not path:
        return JSONResponse({"error": "Report not generated yet."}, status_code=404)
    headers = {"Content-Disposition": f"attachment; filename=detective_report_{ds_id}.html"} if download else {}
    return Response(content=path.read_text(encoding="utf-8"), media_type="text/html", headers=headers)
