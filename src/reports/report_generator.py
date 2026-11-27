"""Self-contained HTML report (open in a browser, then Print -> Save as PDF if you need a PDF)."""
from datetime import datetime
from html import escape

from src.ai.insight_generator import build_findings, next_checks
from src.utils import inr, pct

CSS = """
:root{--bg:#050507;--card:#101016;--ink:#f2f4f7;--mute:#8a9098;--line:#26262e;--silver:#c9cdd3;--red:#ff1a40}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.6 Inter,system-ui,Segoe UI,sans-serif;padding:40px 20px}
.wrap{max-width:900px;margin:auto}
h1{font-size:32px;margin:0 0 4px;letter-spacing:-1px;background:linear-gradient(135deg,#f7f8fa,#b9bec6 35%,#eef0f3 55%,#7e848d);-webkit-background-clip:text;background-clip:text;color:transparent}
.rule{height:2px;margin:14px 0 6px;background:linear-gradient(90deg,var(--red),transparent);box-shadow:0 0 14px rgba(255,26,64,.6)}
h2{margin:34px 0 12px;font-size:18px;border-left:4px solid var(--red);padding-left:10px}.mute{color:var(--mute)}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:12px}
.card{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:16px}.big{font-size:26px;font-weight:700}
.bad{color:var(--red)}.good{color:var(--silver)}table{width:100%;border-collapse:collapse;background:var(--card);border-radius:12px;overflow:hidden}
th,td{padding:10px 12px;text-align:left;border-bottom:1px solid var(--line)}th{color:var(--mute);font-weight:600;font-size:12px;text-transform:uppercase}
.bar{height:8px;border-radius:99px;background:#1c1c24;overflow:hidden}.bar>i{display:block;height:100%;background:linear-gradient(90deg,var(--silver),var(--red))}
.tag{padding:2px 9px;border-radius:99px;font-size:12px;font-weight:600}.high{background:var(--red);color:#fff}.medium{box-shadow:inset 0 0 0 1px #8a9098;color:var(--silver)}.low{background:#1c1c24;color:var(--mute)}
.note{background:rgba(255,26,64,.08);border:1px solid rgba(255,26,64,.5);border-radius:12px;padding:12px 14px;color:var(--ink)}
@media print{body{background:#fff;color:#111}.card,table{background:#fff;border-color:#ddd}}
"""


def _table(rows, cols):
    head = "".join(f"<th>{c}</th>" for c, _ in cols)
    body = "".join("<tr>" + "".join(f"<td>{fn(r)}</td>" for _, fn in cols) + "</tr>" for r in rows)
    return f"<table><tr>{head}</tr>{body}</table>"


def _contrib_table(rows):
    cols = [("Name", lambda r: escape(r["name"])), ("Previous", lambda r: inr(r["previous"])),
            ("Current", lambda r: inr(r["current"])), ("Change", lambda r: inr(r["delta"])),
            ("Share of net change", lambda r: f"<div class='bar'><i style='width:{min(abs(r['share_of_change']),100):.0f}%'></i></div>"
                                              f"<span class='mute'>{'>100% (offset elsewhere)' if abs(r['share_of_change']) > 100 else format(r['share_of_change'], '.0f') + '%'}</span>")]
    return _table(rows, cols)


def _monthly_svg(monthly):
    """Tiny dependency-free bar chart so the report is a single portable file."""
    if not monthly:
        return ""
    top = max(max(r["sales"], 0) for r in monthly) or 1
    w, h, bw = 120, 150, 34
    bars = ""
    for i, r in enumerate(monthly):
        x = 20 + i * w
        hs, hp = r["sales"] / top * 110, max(r["profit"], 0) / top * 110
        bars += (f"<rect x='{x}' y='{125-hs:.0f}' width='{bw}' height='{hs:.0f}' rx='6' fill='#c9cdd3'/>"
                 f"<rect x='{x+bw+6}' y='{125-hp:.0f}' width='{bw}' height='{hp:.0f}' rx='6' fill='#ff1a40'/>"
                 f"<text x='{x+bw}' y='142' fill='#8a9098' font-size='12' text-anchor='middle'>{escape(r['month'])}</text>")
    return (f"<div class='card'><svg viewBox='0 0 {20+len(monthly)*w} {h}' width='100%'>{bars}</svg>"
            "<div class='mute' style='font-size:12px'><span style='color:#c9cdd3'>■</span> Sales &nbsp; <span style='color:#ff1a40'>■</span> Profit</div></div>")


def generate_html(meta: dict, kpis: dict, inv: dict, explanation: dict, monthly=None) -> str:
    c = inv["comparison"]
    cls = "bad" if c["direction"] == "decline" else "good"
    findings = build_findings(inv)
    f_html = "".join(f"<tr><td><span class='tag {f['severity']}'>{f['severity']}</span></td><td>{escape(f['finding'])}"
                     f"<div class='mute'>{escape(f['evidence'])}</div></td></tr>" for f in findings)
    q = meta.get("quality", {})
    issues = "".join(f"<tr><td>{escape(i['type'].replace('_', ' '))}</td><td>{i['count']}</td><td>{escape(i['detail'])}</td></tr>"
                     for i in q.get("issues", [])) or "<tr><td colspan=3>No data-quality issues detected.</td></tr>"
    checks = "".join(f"<li>{escape(x)}</li>" for x in next_checks(inv))
    warn = f"<div class='note'>⚠ {escape(c['partial_warning'])}</div>" if c.get("partial_warning") else ""
    drivers = ""
    if inv.get("drivers"):
        d = inv["drivers"]
        drivers = f"<h2>What moved inside {escape(d['segment'])}</h2>" + _table(d["changes"], [
            ("Driver", lambda r: r["label"]), ("Previous", lambda r: f"{r['previous']:,.1f}"),
            ("Current", lambda r: f"{r['current']:,.1f}"),
            ("Change", lambda r: f"{r['change']:+.1f} {r['unit']}")])
    anomalies = _table(inv["anomalies"], [("Date", lambda r: r["date"]), ("Type", lambda r: r["direction"]),
                                         ("Sales", lambda r: inr(r["sales"])), ("Typical day", lambda r: inr(r["typical_daily_sales"])),
                                         ("Methods", lambda r: ", ".join(r["methods"]))]) if inv["anomalies"] else "<p class='mute'>No unusual days flagged.</p>"
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><title>AI Business Detective - Report</title>
<style>{CSS}</style></head><body><div class="wrap">
<h1>🕵️ AI Business Detective</h1><div class="rule"></div><div class="mute">Investigation report · {escape(meta['filename'])}{(' · prepared by ' + escape(meta['prepared_by'])) if meta.get('prepared_by') else ''} · generated {datetime.now():%d %b %Y, %H:%M}</div>
<h2>Key metrics</h2><div class="grid">
<div class="card"><div class="mute">Total sales</div><div class="big">{inr(kpis['total_sales'])}</div></div>
<div class="card"><div class="mute">Total profit</div><div class="big">{inr(kpis['total_profit'])}</div></div>
<div class="card"><div class="mute">Profit margin</div><div class="big">{'n/a' if kpis['profit_margin'] is None else format(kpis['profit_margin'], '.1f') + '%'}</div></div>
<div class="card"><div class="mute">Orders</div><div class="big">{kpis['total_orders']:,}</div></div></div>
<h2>Monthly overview</h2>{_monthly_svg(monthly or [])}
<h2>Investigation: {c['metric'].title()} {escape(c['previous_period'])} → {escape(c['current_period'])}</h2>
<div class="card"><span class="big {cls}">{pct(c['pct'])}</span> <span class="mute">&nbsp;{inr(c['previous'])} → {inr(c['current'])}</span>
<p>{escape(explanation['text'])}</p></div>{warn}
<h2>Key findings</h2><table>{f_html}</table>
<h2>Top contributors by product</h2>{_contrib_table(inv['contributors']['product'])}
<h2>Top contributors by region</h2>{_contrib_table(inv['contributors']['region'])}
<h2>Top product × region segments</h2>{_contrib_table(inv['contributors']['segment'])}
{drivers}<h2>Unusual days</h2>{anomalies}
<h2>Recommended next checks</h2><div class="card"><ul>{checks}</ul></div>
<h2>Data quality</h2><p class="mute">{q.get('rows_in', '?')} rows in → {q.get('rows_out', '?')} analysed · quality score {q.get('quality_score', '?')}/100</p>
<table><tr><th>Issue</th><th>Rows</th><th>How it was handled</th></tr>{issues}</table>
<p class="mute" style="margin-top:34px">Contributors show <b>where</b> a change happened, not proof of <b>why</b>. Explanation source: {explanation['source']}.</p>
</div></body></html>"""
