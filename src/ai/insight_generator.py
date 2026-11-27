"""Turn calculated evidence into plain-English findings.

Default: deterministic, rule-based explainer (no API key, fully reproducible, never hallucinates).
Optional: if ANTHROPIC_API_KEY is set, an LLM rewrites the SAME evidence as a smoother narrative.
If the LLM call fails for any reason we fall back to the rule-based text.
"""
from src.utils import inr, pct

from .prompts import SYSTEM_PROMPT, build_user_prompt


def share_text(r: dict) -> str:
    """Share of the net change; >100% means other segments offset it, which we say plainly."""
    share = abs(r["share_of_change"])
    if share > 100:
        return "a bigger move than the net change itself (other segments offset it)"
    return f"{share:.0f}% of the net change"


def _fmt_driver(d):
    if d["driver"] in ("margin", "avg_discount"):
        return f"{d['label'].lower()} {d['change']:+.1f} pts ({d['previous']:.1f}% → {d['current']:.1f}%)"
    return f"{d['label'].lower()} {pct(d['change'])} ({d['previous']:,.0f} → {d['current']:,.0f})"


def build_findings(inv: dict) -> list[dict]:
    """Structured findings: {finding, evidence, severity}. Used by the UI, the report and the database."""
    c, metric = inv["comparison"], inv["metric"]
    findings = []
    if c["direction"] == "flat":
        findings.append({"finding": f"{metric.title()} was broadly flat.", "severity": "low",
                         "evidence": f"{inr(c['previous'])} → {inr(c['current'])} ({pct(c['pct'])})."})
    else:
        verb = "fell" if c["direction"] == "decline" else "rose"
        findings.append({
            "finding": f"{metric.title()} {verb} {abs(c['pct']):.1f}% between {c['previous_period']} and {c['current_period']}.",
            "evidence": f"{inr(c['previous'])} → {inr(c['current'])} (change {inr(c['delta'])}).",
            "severity": inv["severity"]})
    for dim in ("category", "region", "segment"):
        rows = inv["contributors"].get(dim) or []
        if rows and abs(rows[0]["share_of_change"]) >= 25:
            r = rows[0]
            findings.append({
                "finding": f"{r['name']} ({dim}) contributed most to the change.",
                "evidence": f"{inr(r['delta'])} change - {share_text(r)}.",
                "severity": "high" if abs(r["share_of_change"]) >= 40 else "medium"})
    for a in inv["anomalies"][:3]:
        findings.append({"finding": f"Unusual {a['direction']} on {a['date']}.",
                         "evidence": f"Sales {inr(a['sales'])} vs typical day {inr(a['typical_daily_sales'])} ({', '.join(a['methods'])}).",
                         "severity": "medium"})
    if c.get("partial_warning"):
        findings.append({"finding": "Partial-period warning.", "evidence": c["partial_warning"], "severity": "medium"})
    return findings


def next_checks(inv: dict) -> list[str]:
    checks = []
    dr = inv.get("drivers")
    if dr:
        by = {d["driver"]: d for d in dr["changes"]}
        seg = dr["segment"]
        if by.get("orders") and (by["orders"]["change"] or 0) <= -10:
            checks.append(f"Check why {seg} orders fell: stock availability, campaigns, competitor pricing, sales-team changes.")
        if by.get("avg_discount") and by["avg_discount"]["change"] >= 2:
            checks.append(f"Review discount policy for {seg}: average discount rose {by['avg_discount']['change']:.1f} pts.")
        if by.get("margin") and by["margin"]["change"] <= -1:
            checks.append(f"Compare cost / supplier price for {seg}: margin fell {abs(by['margin']['change']):.1f} pts.")
        if by.get("avg_selling_price") and abs(by["avg_selling_price"]["change"] or 0) >= 5:
            checks.append(f"Look at product mix inside {seg}: average selling price moved {pct(by['avg_selling_price']['change'])}.")
    if inv["anomalies"]:
        checks.append("Confirm the flagged unusual days are genuine (bulk orders, outages) and not data-entry errors.")
    checks.append("Re-run this analysis with cost data and customer segments if available - contributors show WHERE, not WHY.")
    return checks[:4]


def rule_based_explanation(inv: dict) -> str:
    c, metric = inv["comparison"], inv["metric"]
    if c["direction"] == "flat":
        head = f"{metric.title()} was broadly flat ({inr(c['previous'])} → {inr(c['current'])}, {pct(c['pct'])})."
    else:
        verb = "decreased" if c["direction"] == "decline" else "increased"
        head = (f"{metric.title()} {verb} by {abs(c['pct']):.1f}%, from {inr(c['previous'])} in {c['previous_period']} "
                f"to {inr(c['current'])} in {c['current_period']}.")
    parts = [head]
    seg = (inv["contributors"].get("segment") or [None])[0]
    reg = (inv["contributors"].get("region") or [None])[0]
    prod = (inv["contributors"].get("product") or [None])[0]
    if prod:
        parts.append(f"By product, {prod['name']} moved most ({inr(prod['delta'])}; {share_text(prod)}).")
    if reg:
        parts.append(f"By region, {reg['name']} moved most ({inr(reg['delta'])}; {share_text(reg)}).")
    if seg:
        parts.append(f"The single biggest product-region combination was {seg['name']} ({inr(seg['delta'])}; {share_text(seg)}).")
    dr = inv.get("drivers")
    if dr:
        parts.append(f"Inside {dr['segment']}: " + "; ".join(_fmt_driver(d) for d in dr["changes"]) + ".")
    parts.append("These figures show where the change happened and what moved alongside it; they do not on their own prove why it happened.")
    if c.get("partial_warning"):
        parts.append("Note: " + c["partial_warning"])
    return " ".join(parts)


def generate_explanation(inv: dict, question: str, api_key: str = "", model: str = "claude-sonnet-4-6") -> dict:
    baseline = rule_based_explanation(inv)
    if api_key:
        try:
            import anthropic
            evidence = {"comparison": inv["comparison"], "contributors": inv["contributors"], "drivers": inv["drivers"],
                        "anomalies": inv["anomalies"][:3], "baseline_summary": baseline}
            msg = anthropic.Anthropic(api_key=api_key).messages.create(
                model=model, max_tokens=600, system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": build_user_prompt(question, evidence)}])
            return {"text": msg.content[0].text.strip(), "source": "llm"}
        except Exception as exc:  # fall back, never fail the request
            return {"text": baseline, "source": "rules", "llm_error": type(exc).__name__}
    return {"text": baseline, "source": "rules"}
