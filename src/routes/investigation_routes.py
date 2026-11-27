import re

from fastapi import APIRouter, Body, Depends, Request
from fastapi.responses import JSONResponse

from src import gamify
from src.ai.insight_generator import build_findings, generate_explanation, next_checks
from src.analytics.investigation import investigate
from src.auth.security import require_user
from src.database.repository import DatasetNotFound
from src.schemas import AskRequest, InvestigateRequest
from src.utils import jsonable

router = APIRouter(tags=["investigation"])


def _metric_from_question(q: str, default="profit") -> str:
    q = q.lower()
    if re.search(r"\b(sales|revenue|turnover)\b", q) and "profit" not in q:
        return "sales"
    return default


def _run(request: Request, uid: int, payload: InvestigateRequest, question: str) -> dict:
    df = request.app.state.repo.load_dataset(payload.dataset, uid)
    metric = payload.metric
    if metric not in ("sales", "profit"):
        metric = _metric_from_question(question)
    inv = investigate(df, metric, payload.previous or None, payload.current or None)
    gamify.record(uid, "investigate")
    cfg = request.app.state.config
    expl = generate_explanation(inv, question, cfg.ANTHROPIC_API_KEY, cfg.LLM_MODEL)
    return {
        "investigation": inv,
        "findings": build_findings(inv),
        "next_checks": next_checks(inv),
        "explanation": expl,
        "question": question,
    }


def _handle(request: Request, uid: int, payload: InvestigateRequest, question: str):
    try:
        return jsonable(_run(request, uid, payload, question))
    except DatasetNotFound:
        return JSONResponse({"error": "Dataset not found. Upload a file first."}, status_code=404)
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=422)


@router.post("/api/investigate")
def api_investigate(
    request: Request,
    p: InvestigateRequest = Body(default_factory=InvestigateRequest),
    user=Depends(require_user),
):
    return _handle(request, user["id"], p, f"Why did {p.metric or 'profit'} change?")


@router.post("/api/ask")
def api_ask(
    request: Request,
    p: AskRequest = Body(default_factory=AskRequest),
    user=Depends(require_user),
):
    q = (p.question or "").strip()[:300]
    if not q:
        return JSONResponse({"error": "Please type a question."}, status_code=400)
    return _handle(request, user["id"], p, q)
