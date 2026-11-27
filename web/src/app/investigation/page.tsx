"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import type { Data, Layout } from "plotly.js";
import { useAuth } from "@/components/AuthProvider";
import { PALETTE, PlotlyChart } from "@/components/PlotlyChart";
import { useToast } from "@/components/ToastProvider";
import { apiFetch, getApiUrl } from "@/lib/api";
import { fmtInr, pctf } from "@/lib/format";
import type { FilterOptions, InvestigationResponse } from "@/types/api";

type ContribTab = "segment" | "product" | "region" | "category";
const TABS: Record<ContribTab, string> = {
  segment: "Product · Region",
  product: "Product",
  region: "Region",
  category: "Category",
};

const PRESETS = [
  "Why did profit decrease this month?",
  "Why did sales change?",
  "Which region caused the change?",
  "Which product is performing poorly?",
];

export default function InvestigationPage() {
  const { loading: authLoading, authenticated, datasetId } = useAuth();
  const { toast } = useToast();

  const [months, setMonths] = useState<string[]>([]);
  const [previous, setPrevious] = useState("");
  const [current, setCurrent] = useState("");
  const [question, setQuestion] = useState("Why did profit decrease this month?");
  const [metric, setMetric] = useState<"auto" | "profit" | "sales">("auto");
  const [tab, setTab] = useState<ContribTab>("segment");

  const [loading, setLoading] = useState(false);
  const [makingReport, setMakingReport] = useState(false);
  const [result, setResult] = useState<InvestigationResponse | null>(null);

  const runInvestigation = useCallback(
    async (opts: { q?: string; prev?: string; curr?: string; m?: "auto" | "profit" | "sales" } = {}) => {
      if (!datasetId) return;
      const qText = (opts.q ?? question).trim();
      if (!qText) {
        toast("Type a question first", true);
        return;
      }
      const prevVal = opts.prev ?? previous;
      const currVal = opts.curr ?? current;
      const metVal = opts.m ?? metric;

      setLoading(true);
      try {
        const res = await apiFetch<InvestigationResponse>("/api/ask", {
          method: "POST",
          body: {
            dataset: datasetId,
            question: qText,
            previous: prevVal || undefined,
            current: currVal || undefined,
            metric: metVal === "auto" ? null : metVal,
          },
        });
        setResult(res);
      } catch (err) {
        setResult(null);
        toast(err instanceof Error ? err.message : "Investigation failed.", true);
      } finally {
        setLoading(false);
      }
    },
    [datasetId, question, previous, current, metric, toast]
  );

  useEffect(() => {
    if (authLoading || !authenticated || !datasetId) return;
    let active = true;
    (async () => {
      try {
        const o = await apiFetch<FilterOptions>(`/api/options?dataset=${encodeURIComponent(datasetId)}`);
        if (!active) return;
        const m = o.months || [];
        const p = m[Math.max(m.length - 2, 0)] || "";
        const c = m[m.length - 1] || "";
        setMonths(m);
        setPrevious(p);
        setCurrent(c);
        if (m.length >= 2) {
          await runInvestigation({ q: "Why did profit decrease this month?", prev: p, curr: c, m: "auto" });
        }
      } catch (err) {
        if (active) toast(err instanceof Error ? err.message : "Could not load months.", true);
      }
    })();
    return () => {
      active = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [authLoading, authenticated, datasetId]);

  const contribChart = useMemo<{ data: Data[]; layout: Partial<Layout> } | null>(() => {
    if (!result) return null;
    const rows = result.investigation.contributors[tab].slice().sort((a, b) => a.delta - b.delta);
    return {
      data: [
        {
          x: rows.map((r) => r.delta),
          y: rows.map((r) => r.name),
          type: "bar",
          orientation: "h",
          marker: { color: rows.map((r) => (r.delta < 0 ? PALETTE.bad : PALETTE.good)) },
          text: rows.map((r) => fmtInr(r.delta)),
          textposition: "outside",
          cliponaxis: false,
          customdata: rows.map((r) => [fmtInr(r.previous), fmtInr(r.current), pctf(r.pct)]),
          hovertemplate: "<b>%{y}</b><br>%{customdata[0]} → %{customdata[1]} (%{customdata[2]})<extra></extra>",
        },
      ],
      layout: { margin: { t: 14, r: 96, b: 34, l: 150 }, height: 330 },
    };
  }, [result, tab]);

  const generateReport = async () => {
    if (!datasetId || !result) return;
    setMakingReport(true);
    try {
      const c = result.investigation.comparison;
      const r = await apiFetch<{ ok: boolean; url: string }>(`/api/report/${datasetId}`, {
        method: "POST",
        body: {
          metric: result.investigation.metric,
          previous: c.previous_period,
          current: c.current_period,
        },
      });
      toast("Report ready ✅");
      window.open(getApiUrl(r.url), "_blank", "noopener,noreferrer");
    } catch (err) {
      toast(err instanceof Error ? err.message : "Report generation failed.", true);
    } finally {
      setMakingReport(false);
    }
  };

  if (authLoading) return <div className="card" style={{ marginTop: 32 }}>Loading…</div>;

  const inv = result?.investigation;
  const comp = inv?.comparison;
  const dr = inv?.drivers;
  const dirCls = comp ? (comp.direction === "decline" ? "down" : comp.direction === "increase" ? "up" : "muted") : "";
  const dirArrow = comp ? (comp.direction === "decline" ? "▼" : comp.direction === "increase" ? "▲" : "■") : "";

  return (
    <>
      <div className="page-head">
        <h2>
          Case <span className="grad">investigation</span>
        </h2>
        <p>Ask a question or pick two months. Code calculates the numbers; the explanation only describes them.</p>
      </div>

      {!datasetId ? (
        <div className="card empty">
          <div className="ico">🕵️</div>
          <h3>No dataset loaded</h3>
          <p className="muted">Load a dataset first.</p>
          <Link className="btn" href="/">
            Go to upload
          </Link>
        </div>
      ) : (
        <div>
          <div className="card glow">
            <div className="ask">
              <input
                value={question}
                maxLength={300}
                aria-label="Your question"
                onChange={(e) => setQuestion(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") void runInvestigation();
                }}
              />
              <button
                type="button"
                className="btn"
                disabled={loading}
                onClick={() => void runInvestigation()}
              >
                {loading ? "Investigating…" : "Investigate"}
              </button>
            </div>
            <div className="row">
              {PRESETS.map((p) => (
                <button
                  type="button"
                  key={p}
                  className="chip"
                  onClick={() => {
                    setQuestion(p);
                    void runInvestigation({ q: p });
                  }}
                >
                  {p}
                </button>
              ))}
            </div>
            <div className="row" style={{ marginTop: 16, paddingTop: 16, borderTop: "1px solid var(--line)" }}>
              <label className="muted" style={{ fontSize: 12, fontWeight: 700 }}>
                COMPARE{" "}
                <select
                  style={{ margin: "0 6px" }}
                  value={previous}
                  onChange={(e) => {
                    setPrevious(e.target.value);
                    void runInvestigation({ prev: e.target.value });
                  }}
                >
                  {months.map((m) => (
                    <option key={m} value={m}>
                      {m}
                    </option>
                  ))}
                </select>{" "}
                →{" "}
                <select
                  style={{ marginLeft: 6 }}
                  value={current}
                  onChange={(e) => {
                    setCurrent(e.target.value);
                    void runInvestigation({ curr: e.target.value });
                  }}
                >
                  {months.map((m) => (
                    <option key={m} value={m}>
                      {m}
                    </option>
                  ))}
                </select>
              </label>
              <div className="seg">
                {(["auto", "profit", "sales"] as const).map((m) => (
                  <button
                    type="button"
                    key={m}
                    className={metric === m ? "on" : undefined}
                    onClick={() => {
                      setMetric(m);
                      void runInvestigation({ m });
                    }}
                  >
                    {m[0].toUpperCase() + m.slice(1)}
                  </button>
                ))}
              </div>
            </div>
          </div>

          <div style={{ marginTop: 18 }}>
            {loading && (
              <div className="card">
                <div className="skel" style={{ width: "70%" }} />
                <br />
                <div className="skel" style={{ width: "92%" }} />
                <br />
                <div className="skel" style={{ width: "55%" }} />
              </div>
            )}

            {!loading && result && inv && comp && (
              <>
                <div className="card glow fade">
                  <div className="verdict">
                    <div>
                      <div className="muted" style={{ fontWeight: 700 }}>
                        {comp.metric.toUpperCase()} · {comp.previous_period} → {comp.current_period}
                      </div>
                      <div className={`pctbig ${dirCls}`}>
                        {dirArrow} {pctf(comp.pct)}
                      </div>
                      <div className="muted">
                        {fmtInr(comp.previous)} → {fmtInr(comp.current)}
                      </div>
                    </div>
                    <div>
                      <div className="between">
                        <b>🕵️ The Detective&apos;s read</b>
                        <span className="src">
                          {result.explanation.source === "llm"
                            ? "🤖 AI-written from evidence"
                            : "📐 rule-based from evidence"}
                        </span>
                      </div>
                      <p className="expl">{result.explanation.text}</p>
                    </div>
                  </div>
                  {comp.partial_warning && <div className="warnbox">⚠ {comp.partial_warning}</div>}
                </div>

                <div className="grid g2" style={{ marginTop: 18 }}>
                  <div className="card fade">
                    <div className="between">
                      <h4 style={{ margin: 0 }}>Who moved the number?</h4>
                      <div className="seg">
                        {(Object.entries(TABS) as [ContribTab, string][]).map(([k, label]) => (
                          <button
                            type="button"
                            key={k}
                            className={tab === k ? "on" : undefined}
                            onClick={() => setTab(k)}
                          >
                            {label}
                          </button>
                        ))}
                      </div>
                    </div>
                    {contribChart && <PlotlyChart data={contribChart.data} layout={contribChart.layout} />}
                  </div>

                  <div className="card fade">
                    <h4 style={{ margin: 0 }}>
                      {dr ? (
                        <>
                          Inside <span className="grad">{dr.segment}</span>
                        </>
                      ) : (
                        "Drivers"
                      )}
                    </h4>
                    <p className="muted" style={{ margin: "4px 0 0", fontSize: 13 }}>
                      What changed within the single biggest contributor
                    </p>
                    <div className="drv">
                      {dr ? (
                        dr.changes.map((x) => {
                          const bad = x.driver === "avg_discount" ? x.change > 0 : x.change < 0;
                          const cls = Math.abs(x.change) < 0.05 ? "muted" : bad ? "down" : "up";
                          return (
                            <div className="d" key={x.driver}>
                              <small>{x.label}</small>
                              <b className={cls}>
                                {x.change >= 0 ? "+" : ""}
                                {x.change.toFixed(1)}
                                {x.unit === "pts" ? " pts" : "%"}
                              </b>
                              <small>
                                {x.previous.toLocaleString("en-IN", { maximumFractionDigits: 1 })} →{" "}
                                {x.current.toLocaleString("en-IN", { maximumFractionDigits: 1 })}
                              </small>
                            </div>
                          );
                        })
                      ) : (
                        <span className="muted">Not enough data.</span>
                      )}
                    </div>
                    <div className="note">
                      Red = moved in the unhelpful direction. These are associations in the data, not proven causes.
                    </div>
                  </div>
                </div>

                <div className="grid g2" style={{ marginTop: 18 }}>
                  <div className="card fade">
                    <h4 style={{ margin: "0 0 6px" }}>🔎 Key findings</h4>
                    {result.findings.map((f, i) => (
                      <div className="find" key={i}>
                        <span className={`tag ${f.severity}`} style={{ height: "fit-content" }}>
                          {f.severity}
                        </span>
                        <div>
                          {f.finding}
                          <small>{f.evidence}</small>
                        </div>
                      </div>
                    ))}
                  </div>

                  <div className="card fade">
                    <h4 style={{ margin: "0 0 6px" }}>🚨 Unusual days</h4>
                    {inv.anomalies.length ? (
                      inv.anomalies.map((a) => (
                        <div className="find" key={a.date}>
                          <span style={{ fontSize: 22 }}>{a.direction === "spike" ? "📈" : "📉"}</span>
                          <div>
                            <b>{a.date}</b> · {fmtInr(a.sales)}
                            <small>
                              typical day {fmtInr(a.typical_daily_sales)} · {a.methods.join(" + ")}
                              <br />
                              {a.note}
                            </small>
                          </div>
                        </div>
                      ))
                    ) : (
                      <p className="muted">No unusual days flagged.</p>
                    )}

                    <h4 style={{ margin: "20px 0 6px" }}>✅ Recommended next checks</h4>
                    <ul className="checks">
                      {result.next_checks.map((x, i) => (
                        <li key={i}>{x}</li>
                      ))}
                    </ul>
                  </div>
                </div>

                <div className="row" style={{ marginTop: 18 }}>
                  <button
                    type="button"
                    className="btn"
                    disabled={makingReport}
                    onClick={() => void generateReport()}
                  >
                    📄 {makingReport ? "Working…" : "Generate report"}
                  </button>
                  <a
                    className="btn ghost"
                    href={getApiUrl(
                      `/api/export/${datasetId}/contributors.csv?metric=${encodeURIComponent(inv.metric)}&previous=${encodeURIComponent(comp.previous_period)}&current=${encodeURIComponent(comp.current_period)}`
                    )}
                  >
                    ⬇ Contributors CSV
                  </a>
                </div>
              </>
            )}
          </div>
        </div>
      )}
    </>
  );
}
