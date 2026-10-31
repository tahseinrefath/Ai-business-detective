import re

from flask import Blueprint, current_app, g, jsonify, request

from src import gamify

from src.ai.insight_generator import build_findings, generate_explanation, next_checks
from src.analytics.investigation import investigate
from src.database.repository import DatasetNotFound
from src.utils import jsonable

bp = Blueprint("investigation", __name__)


def _metric_from_question(q: str, default="profit") -> str:
    q = q.lower()
    if re.search(r"\b(sales|revenue|turnover)\b", q) and "profit" not in q:
        return "sales"
    return default


def _run(payload, question):
    ds = payload.get("dataset", "")
    df = current_app.repo.load_dataset(ds, g.user["id"])
    metric = payload.get("metric")
    if metric not in ("sales", "profit"):
        metric = _metric_from_question(question)
    inv = investigate(df, metric, payload.get("previous") or None, payload.get("current") or None)
    gamify.record(g.user["id"], "investigate")
    cfg = current_app.config
    expl = generate_explanation(inv, question, cfg["ANTHROPIC_API_KEY"], cfg["LLM_MODEL"])
    return {"investigation": inv, "findings": build_findings(inv), "next_checks": next_checks(inv),
            "explanation": expl, "question": question}


def _handle(payload, question):
    try:
        return jsonify(jsonable(_run(payload, question)))
    except DatasetNotFound:
        return jsonify(error="Dataset not found. Upload a file first."), 404
    except ValueError as e:
        return jsonify(error=str(e)), 422


@bp.post("/api/investigate")
def api_investigate():
    p = request.get_json(silent=True) or {}
    return _handle(p, f"Why did {p.get('metric', 'profit')} change?")


@bp.post("/api/ask")
def api_ask():
    p = request.get_json(silent=True) or {}
    q = (p.get("question") or "").strip()[:300]
    if not q:
        return jsonify(error="Please type a question."), 400
    return _handle(p, q)
