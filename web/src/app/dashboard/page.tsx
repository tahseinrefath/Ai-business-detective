"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import type { Data, Layout } from "plotly.js";
import { useAuth } from "@/components/AuthProvider";
import { CountUp } from "@/components/CountUp";
import { PALETTE, PlotlyChart } from "@/components/PlotlyChart";
import { useToast } from "@/components/ToastProvider";
import { apiFetch, getApiUrl } from "@/lib/api";
import { fmtInr, pctf } from "@/lib/format";
import type { DashboardResponse, FilterOptions, GroupRow, MetricKind } from "@/types/api";

interface FiltersState {
  region: string;
  category: string;
  product: string;
  start: string;
  end: string;
}

const DEFAULT_FILTERS: FiltersState = { region: "All", category: "All", product: "All", start: "", end: "" };
const CIRC = 2 * Math.PI * 68;

export default function DashboardPage() {
  const { loading: authLoading, authenticated, datasetId } = useAuth();
  const { toast } = useToast();

  const [filters, setFilters] = useState<FiltersState>(DEFAULT_FILTERS);
  const [options, setOptions] = useState<FilterOptions | null>(null);
  const [data, setData] = useState<DashboardResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [emptyState, setEmptyState] = useState(false);

  const [prodMetric, setProdMetric] = useState<MetricKind>("profit");
  const [regMetric, setRegMetric] = useState<MetricKind>("profit");

  const fetchDashboard = useCallback(
    async (f: FiltersState, isInitial: boolean) => {
      if (!datasetId) return;
      setLoading(true);
      try {
        const params = new URLSearchParams({ dataset: datasetId });
        (Object.entries(f) as [keyof FiltersState, string][]).forEach(([k, v]) => {
          if (v && v !== "All") params.set(k, v);
        });
        const res = await apiFetch<DashboardResponse>(`/api/dashboard?${params.toString()}`);
        setData(res);
        setEmptyState(false);
        if (isInitial) setOptions(res.options);
      } catch (err) {
        if (isInitial) setEmptyState(true);
        toast(err instanceof Error ? err.message : "Failed to load dashboard.", true);
      } finally {
        setLoading(false);
      }
    },
    [datasetId, toast]
  );

  useEffect(() => {
    if (authLoading || !authenticated) return;
    if (!datasetId) {
      setEmptyState(true);
      setData(null);
      return;
    }
    setFilters(DEFAULT_FILTERS);
    void fetchDashboard(DEFAULT_FILTERS, true);
  }, [authLoading, authenticated, datasetId, fetchDashboard]);

  const updateFilter = (key: keyof FiltersState, value: string) => {
    const next = { ...filters, [key]: value };
    setFilters(next);
    void fetchDashboard(next, false);
  };

  const resetFilters = () => {
    setFilters(DEFAULT_FILTERS);
    void fetchDashboard(DEFAULT_FILTERS, false);
  };

  // Memoized Plotly datasets & layouts
  const monthlyChart = useMemo<{ data: Data[]; layout: Partial<Layout> } | null>(() => {
    if (!data) return null;
    const m = data.monthly;
    return {
      data: [
        { x: m.map((r) => r.month), y: m.map((r) => r.sales), type: "bar", name: "Sales", marker: { color: PALETTE.silver } },
        { x: m.map((r) => r.month), y: m.map((r) => r.profit), type: "bar", name: "Profit", marker: { color: PALETTE.crimson } },
        {
          x: m.map((r) => r.month),
          y: m.map((r) => r.margin),
          type: "scatter",
          mode: "lines+markers",
          name: "Margin %",
          yaxis: "y2",
          line: { color: PALETTE.silverHi, width: 3 },
          marker: { size: 8 },
        },
      ],
      layout: { barmode: "group", yaxis2: { overlaying: "y", side: "right", showgrid: false, ticksuffix: "%" } },
    };
  }, [data]);

  const dailyChart = useMemo<{ data: Data[] } | null>(() => {
    if (!data) return null;
    const days = data.daily;
    const roll = days.map((_, i) => {
      const w = days.slice(Math.max(0, i - 6), i + 1);
      return w.reduce((a, b) => a + b.sales, 0) / w.length;
    });
    return {
      data: [
        {
          x: days.map((r) => r.date),
          y: days.map((r) => r.sales),
          type: "scatter",
          mode: "lines",
          name: "Daily",
          line: { color: "rgba(201,205,211,.45)", width: 1.3 },
          fill: "tozeroy",
          fillcolor: "rgba(201,205,211,.08)",
        },
        {
          x: days.map((r) => r.date),
          y: roll,
          type: "scatter",
          mode: "lines",
          name: "7-day average",
          line: { color: PALETTE.crimson, width: 3, shape: "spline" },
        },
      ],
    };
  }, [data]);

  const buildBarData = (rows: GroupRow[], metric: MetricKind): { data: Data[]; layout: Partial<Layout> } => {
    const sorted = rows.slice().sort((a, b) => b[metric] - a[metric]);
    return {
      data: [
        {
          x: sorted.map((r) => r[metric]),
          y: sorted.map((r) => r.name),
          type: "bar",
          orientation: "h",
          marker: { color: sorted.map((r) => (r[metric] >= 0 ? PALETTE.silver : PALETTE.crimson)) },
          text: sorted.map((r) => fmtInr(r[metric])),
          textposition: "outside",
          cliponaxis: false,
        },
      ],
      layout: { yaxis: { autorange: "reversed" }, margin: { t: 10, r: 96, b: 30, l: 96 } },
    };
  };

  const productsChart = useMemo(
    () => (data ? buildBarData(data.products, prodMetric) : null),
    [data, prodMetric]
  );
  const regionsChart = useMemo(
    () => (data ? buildBarData(data.regions, regMetric) : null),
    [data, regMetric]
  );

  const heatChart = useMemo<{ data: Data[]; layout: Partial<Layout> } | null>(() => {
    if (!data) return null;
    return {
      data: [
        {
          z: data.heatmap.z,
          x: data.heatmap.products,
          y: data.heatmap.regions,
          type: "heatmap",
          colorscale: [
            [0, "#15151c"],
            [0.5, "#a10020"],
            [1, "#ff4d6d"],
          ],
          hovertemplate: "%{y} · %{x}<br>Profit ₹%{z:,.0f}<extra></extra>",
          colorbar: { thickness: 10, tickfont: { size: 10 } },
        },
      ],
      layout: { margin: { t: 10, r: 10, b: 44, l: 70 } },
    };
  }, [data]);

  const catChart = useMemo<{ data: Data[]; layout: Partial<Layout> } | null>(() => {
    if (!data) return null;
    return {
      data: [
        {
          labels: data.categories.map((r) => r.name),
          values: data.categories.map((r) => Math.max(r.profit, 0)),
          type: "pie",
          hole: 0.62,
          sort: false,
          marker: {
            colors: [PALETTE.crimson, PALETTE.silver, PALETTE.crimsonLo, PALETTE.silverLo, PALETTE.silverHi],
            line: { color: PALETTE.obsidian, width: 2 },
          },
          textinfo: "label+percent",
          hovertemplate: "%{label}<br>₹%{value:,.0f}<extra></extra>",
        },
      ],
      layout: { margin: { t: 10, r: 10, b: 10, l: 10 }, showlegend: false, height: 340 },
    };
  }, [data]);

  const discChart = useMemo<{ data: Data[]; layout: Partial<Layout> } | null>(() => {
    if (!data?.discount_bands) return null;
    const bands = data.discount_bands;
    const bandColors = [PALETTE.silverHi, PALETTE.silver, PALETTE.silverLo, PALETTE.crimson];
    return {
      data: [
        {
          x: bands.map((b) => b.band),
          y: bands.map((b) => b.margin),
          type: "bar",
          marker: { color: bands.map((_, i) => bandColors[i % 4]) },
          text: bands.map((b) => `${b.margin.toFixed(1)}%`),
          textposition: "outside",
          customdata: bands.map((b) => b.orders),
          hovertemplate: "%{x} discount<br>Margin %{y:.1f}% · %{customdata} orders<extra></extra>",
        },
      ],
      layout: { yaxis: { ticksuffix: "%" }, xaxis: { title: { text: "Discount given" } } },
    };
  }, [data]);

  if (authLoading || (!authenticated && !emptyState)) {
    return <div className="card" style={{ marginTop: 32 }}>Loading…</div>;
  }

  const lastMonth = data?.monthly[data.monthly.length - 1];
  const kpiCards = data
    ? [
        { icon: "💰", label: "Total sales", val: data.kpis.total_sales, fmt: fmtInr, chg: lastMonth?.sales_change ?? null },
        { icon: "📈", label: "Total profit", val: data.kpis.total_profit, fmt: fmtInr, chg: lastMonth?.profit_change ?? null },
        {
          icon: "🎯",
          label: "Profit margin",
          val: data.kpis.profit_margin ?? 0,
          fmt: (v: number) => (data.kpis.profit_margin == null ? "n/a" : `${v.toFixed(1)}%`),
          chg: null,
        },
        {
          icon: "🧾",
          label: "Total orders",
          val: data.kpis.total_orders,
          fmt: (v: number) => Math.round(v).toLocaleString("en-IN"),
          chg: null,
        },
        {
          icon: "📦",
          label: "Units sold",
          val: data.kpis.units_sold,
          fmt: (v: number) => Math.round(v).toLocaleString("en-IN"),
          chg: null,
        },
        {
          icon: "🛒",
          label: "Avg order value",
          val: data.kpis.avg_order_value ?? 0,
          fmt: (v: number) => (data.kpis.avg_order_value == null ? "n/a" : fmtInr(v)),
          chg: null,
        },
      ]
    : [];

  return (
    <>
      <div className="page-head between">
        <div>
          <h2>
            Performance <span className="grad">dashboard</span>
          </h2>
          <p>
            {data
              ? `${data.meta.filename} · ${data.meta.quality.date_range.join(" → ")}`
              : emptyState
                ? "Nothing loaded yet"
                : loading
                  ? "Loading…"
                  : ""}
          </p>
        </div>
        <div className="row">
          <a
            className="btn ghost sm"
            href={datasetId ? getApiUrl(`/api/export/${datasetId}/clean.csv`) : "#"}
          >
            ⬇ Export cleaned CSV
          </a>
          <Link className="btn sm" href="/investigation">
            🔍 Investigate changes
          </Link>
        </div>
      </div>

      {emptyState && !data && (
        <div className="card empty">
          <div className="ico">🕵️</div>
          <h3>No dataset loaded</h3>
          <p className="muted">Upload a file or open the demo case to see your dashboard.</p>
          <Link className="btn" href="/">
            Go to upload
          </Link>
        </div>
      )}

      {data && (
        <div>
          {options && (
            <div className="card filters">
              <label>
                Region
                <select value={filters.region} onChange={(e) => updateFilter("region", e.target.value)}>
                  <option value="All">All</option>
                  {options.regions.map((r) => (
                    <option key={r} value={r}>
                      {r}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Category
                <select value={filters.category} onChange={(e) => updateFilter("category", e.target.value)}>
                  <option value="All">All</option>
                  {options.categories.map((c) => (
                    <option key={c} value={c}>
                      {c}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Product
                <select value={filters.product} onChange={(e) => updateFilter("product", e.target.value)}>
                  <option value="All">All</option>
                  {options.products.map((p) => (
                    <option key={p} value={p}>
                      {p}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                From
                <input
                  type="date"
                  min={options.min_date}
                  max={options.max_date}
                  value={filters.start}
                  onChange={(e) => updateFilter("start", e.target.value)}
                />
              </label>
              <label>
                To
                <input
                  type="date"
                  min={options.min_date}
                  max={options.max_date}
                  value={filters.end}
                  onChange={(e) => updateFilter("end", e.target.value)}
                />
              </label>
              <button type="button" className="btn ghost sm" onClick={resetFilters}>
                ↺ Reset
              </button>
              <span className="muted" style={{ marginLeft: "auto", fontSize: 13 }}>
                {data.filtered_rows.toLocaleString("en-IN")} of {data.meta.row_count.toLocaleString("en-IN")} rows shown
              </span>
            </div>
          )}

          <div className="pulse">
            {data.pulse.map((p, i) => (
              <div className="p fade" key={i}>
                <span>{p.icon}</span>
                <div>
                  <small>{p.label}</small>
                  <b>{p.value}</b> <em>· {p.detail}</em>
                </div>
              </div>
            ))}
          </div>

          <div className="card glow" style={{ marginTop: 18 }}>
            <div className="between">
              <h4 style={{ margin: 0, fontSize: 16, fontFamily: "var(--display)" }}>Business health score</h4>
              <span className="muted" style={{ fontSize: 12.5 }}>
                Transparent formula · not an industry standard
              </span>
            </div>
            <div className="gauge" style={{ marginTop: 14 }}>
              <svg
                viewBox="0 0 170 170"
                role="img"
                aria-label={`Health score ${data.health.score} out of 100, ${data.health.grade}`}
              >
                <circle cx="85" cy="85" r="68" fill="none" stroke="rgba(201,205,211,.12)" strokeWidth="12" />
                <circle
                  cx="85"
                  cy="85"
                  r="68"
                  fill="none"
                  stroke="#ff1a40"
                  strokeWidth="12"
                  strokeLinecap="round"
                  strokeDasharray={`${((data.health.score / 100) * CIRC).toFixed(1)} ${CIRC.toFixed(1)}`}
                  transform="rotate(-90 85 85)"
                />
                <text
                  x="85"
                  y="92"
                  textAnchor="middle"
                  fontSize="46"
                  fontWeight="700"
                  fill="#f2f4f7"
                  fontFamily="Space Grotesk, Inter, sans-serif"
                >
                  {data.health.score}
                </text>
                <text
                  x="85"
                  y="114"
                  textAnchor="middle"
                  fontSize="11"
                  fill="#8a9098"
                  letterSpacing="1.5"
                  fontFamily="Inter, sans-serif"
                >
                  {data.health.grade.toUpperCase()}
                </text>
              </svg>
              <div>
                {data.health.parts.map((part) => (
                  <div className="hbar" key={part.name}>
                    <div className="top">
                      <span>
                        {part.name} — {part.detail}
                      </span>
                      <b>
                        {part.points}/{part.max}
                      </b>
                    </div>
                    <div className="tr">
                      <i style={{ width: `${((part.points / part.max) * 100).toFixed(0)}%` }} />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          <div className="grid g4" style={{ marginTop: 18 }}>
            {kpiCards.map((c, i) => (
              <div className="card kpi hover fade" key={c.label} style={{ animationDelay: `${i * 55}ms` }}>
                <div className="lbl">
                  <span>{c.icon}</span>
                  {c.label}
                </div>
                <div className="val">
                  <CountUp value={c.val} formatter={c.fmt} />
                </div>
                <div className={`sub ${c.chg == null ? "muted" : c.chg >= 0 ? "up" : "down"}`}>
                  {c.chg == null ? "\u00A0" : `${c.chg >= 0 ? "▲ " : "▼ "}${pctf(c.chg)} vs previous month`}
                </div>
              </div>
            ))}
          </div>

          <div className="grid g2" style={{ marginTop: 18 }}>
            <div className="card chart">
              <h4>Monthly sales, profit &amp; margin</h4>
              <div className="hint">Bars: totals · line: profit margin %</div>
              {monthlyChart && <PlotlyChart data={monthlyChart.data} layout={monthlyChart.layout} />}
            </div>

            <div className="card chart">
              <h4>Daily sales trend</h4>
              <div className="hint">Faint area is each day; bright line is the 7-day average.</div>
              {dailyChart && <PlotlyChart data={dailyChart.data} />}
            </div>

            <div className="card chart">
              <div className="between">
                <h4>Product performance</h4>
                <div className="seg">
                  <button
                    type="button"
                    className={prodMetric === "profit" ? "on" : undefined}
                    onClick={() => setProdMetric("profit")}
                  >
                    Profit
                  </button>
                  <button
                    type="button"
                    className={prodMetric === "sales" ? "on" : undefined}
                    onClick={() => setProdMetric("sales")}
                  >
                    Sales
                  </button>
                </div>
              </div>
              {productsChart && <PlotlyChart data={productsChart.data} layout={productsChart.layout} />}
            </div>

            <div className="card chart">
              <div className="between">
                <h4>Regional performance</h4>
                <div className="seg">
                  <button
                    type="button"
                    className={regMetric === "profit" ? "on" : undefined}
                    onClick={() => setRegMetric("profit")}
                  >
                    Profit
                  </button>
                  <button
                    type="button"
                    className={regMetric === "sales" ? "on" : undefined}
                    onClick={() => setRegMetric("sales")}
                  >
                    Sales
                  </button>
                </div>
              </div>
              {regionsChart && <PlotlyChart data={regionsChart.data} layout={regionsChart.layout} />}
            </div>

            <div className="card chart">
              <h4>Profit by region × product</h4>
              <div className="hint">Darker cells earn more profit. Spot weak combinations fast.</div>
              {heatChart && <PlotlyChart data={heatChart.data} layout={heatChart.layout} />}
            </div>

            <div className="card chart">
              <h4>Category share of profit</h4>
              <div className="hint">Hover a slice for exact figures.</div>
              {catChart && <PlotlyChart data={catChart.data} layout={catChart.layout} />}
            </div>

            {discChart && (
              <div className="card chart">
                <h4>Margin by discount level</h4>
                <div className="hint">Do bigger discounts leave less profit per rupee sold?</div>
                <PlotlyChart data={discChart.data} layout={discChart.layout} />
              </div>
            )}

            <div className="card chart">
              <h4>Next-month trend projection</h4>
              <div className="hint">A straight-line extension of past months.</div>
              {data.forecast ? (
                <>
                  <div className="fc">
                    <div className="d">
                      <small>{data.forecast.next_month} sales (projected)</small>
                      <b>{fmtInr(data.forecast.sales.projected)}</b>
                      <small className={data.forecast.sales.trend_per_month >= 0 ? "up" : "down"}>
                        {data.forecast.sales.trend_per_month >= 0 ? "▲" : "▼"}{" "}
                        {fmtInr(Math.abs(data.forecast.sales.trend_per_month))} / month trend
                      </small>
                    </div>
                    <div className="d">
                      <small>{data.forecast.next_month} profit (projected)</small>
                      <b>{fmtInr(data.forecast.profit.projected)}</b>
                      <small className={data.forecast.profit.trend_per_month >= 0 ? "up" : "down"}>
                        {data.forecast.profit.trend_per_month >= 0 ? "▲" : "▼"}{" "}
                        {fmtInr(Math.abs(data.forecast.profit.trend_per_month))} / month trend
                      </small>
                    </div>
                  </div>
                  <div className="note">
                    Based on only {data.forecast.history_months} months of history and a straight line — treat it as a
                    rough direction, not a prediction.
                  </div>
                </>
              ) : (
                <p className="muted">Needs at least 3 months of data (after filters) to project a trend.</p>
              )}
            </div>
          </div>

          <div className="card" style={{ marginTop: 18 }}>
            <div className="between" style={{ alignItems: "flex-start", gap: 24 }}>
              <div style={{ flex: 1, minWidth: 260 }}>
                <h4 style={{ margin: "0 0 4px", fontSize: 17 }}>🧹 Data quality report</h4>
                <div className="muted">
                  {data.meta.quality.rows_in} rows in → {data.meta.quality.rows_out} analysed (
                  {data.meta.quality.rows_removed} removed)
                </div>
                {data.meta.quality.issues.length ? (
                  data.meta.quality.issues.map((issue, i) => (
                    <div className="issue" key={i}>
                      <div className="n">{issue.count}</div>
                      <div>
                        <span className={`tag ${issue.severity}`}>{issue.severity}</span>{" "}
                        <b>{issue.type.replace(/_/g, " ")}</b>
                        <div className="muted" style={{ fontSize: 13 }}>
                          {issue.detail}
                        </div>
                      </div>
                    </div>
                  ))
                ) : (
                  <p className="up">✅ No issues detected.</p>
                )}
              </div>
              <div className="score" style={{ ["--p" as string]: data.meta.quality.quality_score }}>
                <span>{data.meta.quality.quality_score}</span>
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
