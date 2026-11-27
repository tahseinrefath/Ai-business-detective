"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { Data, Layout } from "plotly.js";
import { useAuth } from "@/components/AuthProvider";
import { PALETTE, PlotlyChart } from "@/components/PlotlyChart";
import { useToast } from "@/components/ToastProvider";
import { apiFetch } from "@/lib/api";
import { fmtInr, pctf } from "@/lib/format";
import type { GoalItem, MetricKind, NoteItem, WhatIfResponse, WhatIfSegment } from "@/types/api";

export default function LabPage() {
  const { loading: authLoading, authenticated, datasetId, refreshSession } = useAuth();
  const { toast } = useToast();

  const [segments, setSegments] = useState<WhatIfSegment[]>([]);
  const [simMonth, setSimMonth] = useState("");
  const [segment, setSegment] = useState("");
  const [ordersPct, setOrdersPct] = useState(0);
  const [pricePct, setPricePct] = useState(0);
  const [marginPts, setMarginPts] = useState(0);
  const [simOut, setSimOut] = useState<WhatIfResponse | null>(null);

  const [goalMonth, setGoalMonth] = useState("");
  const [goals, setGoals] = useState<GoalItem[]>([]);
  const [goalMetric, setGoalMetric] = useState<MetricKind>("profit");
  const [goalAmount, setGoalAmount] = useState("");
  const [goalErr, setGoalErr] = useState("");

  const [notes, setNotes] = useState<NoteItem[]>([]);
  const [noteText, setNoteText] = useState("");

  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const runSim = useCallback(
    async (
      segName: string,
      ord: number,
      prc: number,
      mar: number,
      commit: boolean
    ) => {
      if (!datasetId || !segName) return;
      try {
        const r = await apiFetch<WhatIfResponse>("/api/whatif", {
          method: "POST",
          body: {
            dataset: datasetId,
            segment: segName,
            commit,
            order_change_pct: ord,
            price_change_pct: prc,
            margin_change_pts: mar,
          },
        });
        setSimOut(r);
        if (commit) void refreshSession();
      } catch (err) {
        toast(err instanceof Error ? err.message : "Could not run scenario.", true);
      }
    },
    [datasetId, refreshSession, toast]
  );

  const loadGoals = useCallback(async () => {
    if (!datasetId) return;
    try {
      const g = await apiFetch<{ month: string; goals: GoalItem[] }>(`/api/goals?dataset=${encodeURIComponent(datasetId)}`);
      setGoalMonth(g.month);
      setGoals(g.goals);
    } catch (err) {
      toast(err instanceof Error ? err.message : "Could not load goals.", true);
    }
  }, [datasetId, toast]);

  const loadNotes = useCallback(async () => {
    if (!datasetId) return;
    try {
      const r = await apiFetch<{ notes: NoteItem[] }>(`/api/notes?dataset=${encodeURIComponent(datasetId)}`);
      setNotes(r.notes);
    } catch (err) {
      toast(err instanceof Error ? err.message : "Could not load notes.", true);
    }
  }, [datasetId, toast]);

  useEffect(() => {
    if (authLoading || !authenticated || !datasetId) return;
    let active = true;
    (async () => {
      try {
        const s = await apiFetch<{ current: string; previous: string; segments: WhatIfSegment[] }>(
          `/api/whatif/segments?dataset=${encodeURIComponent(datasetId)}`
        );
        if (!active) return;
        setSimMonth(s.current);
        setSegments(s.segments);
        if (!s.segments.length) {
          toast("No segments found in the latest month.", true);
          return;
        }
        const firstSeg = s.segments[0].name;
        setSegment(firstSeg);
        setOrdersPct(0);
        setPricePct(0);
        setMarginPts(0);
        await Promise.all([
          runSim(firstSeg, 0, 0, 0, false),
          loadGoals(),
          loadNotes(),
        ]);
      } catch (err) {
        if (active) toast(err instanceof Error ? err.message : "Failed to initialize lab.", true);
      }
    })();
    return () => {
      active = false;
    };
  }, [authLoading, authenticated, datasetId, runSim, loadGoals, loadNotes, toast]);

  const schedulePreview = (ord: number, prc: number, mar: number) => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      void runSim(segment, ord, prc, mar, false);
    }, 160);
  };

  const commitRelease = (ord: number, prc: number, mar: number) => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    void runSim(segment, ord, prc, mar, true);
  };

  const simChart = useMemo<{ data: Data[]; layout: Partial<Layout> } | null>(() => {
    if (!simOut) return null;
    const b = simOut.baseline;
    const s = simOut.scenario;
    return {
      data: [
        { x: ["Sales", "Profit"], y: [b.sales, b.profit], type: "bar", name: "Now", marker: { color: PALETTE.silver } },
        { x: ["Sales", "Profit"], y: [s.sales, s.profit], type: "bar", name: "Scenario", marker: { color: PALETTE.crimson } },
      ],
      layout: { barmode: "group", height: 260, margin: { t: 10, r: 10, b: 30, l: 70 } },
    };
  }, [simOut]);

  const saveGoal = async () => {
    if (!datasetId) return;
    setGoalErr("");
    try {
      await apiFetch("/api/goals", {
        method: "PUT",
        body: { dataset: datasetId, metric: goalMetric, amount: goalAmount },
      });
      setGoalAmount("");
      toast("Goal saved ✅");
      await loadGoals();
      void refreshSession();
    } catch (err) {
      setGoalErr(err instanceof Error ? err.message : "Could not save goal.");
    }
  };

  const deleteGoal = async (metric: MetricKind) => {
    if (!datasetId) return;
    try {
      await apiFetch("/api/goals", { method: "DELETE", body: { dataset: datasetId, metric } });
      await loadGoals();
    } catch (err) {
      toast(err instanceof Error ? err.message : "Could not delete goal.", true);
    }
  };

  const addNote = async () => {
    if (!datasetId) return;
    const text = noteText.trim();
    if (!text) {
      toast("Write something first.", true);
      return;
    }
    try {
      await apiFetch("/api/notes", { method: "POST", body: { dataset: datasetId, text } });
      setNoteText("");
      await loadNotes();
      void refreshSession();
    } catch (err) {
      toast(err instanceof Error ? err.message : "Could not add note.", true);
    }
  };

  const deleteNote = async (id: number) => {
    try {
      await apiFetch(`/api/notes/${id}`, { method: "DELETE" });
      await loadNotes();
    } catch (err) {
      toast(err instanceof Error ? err.message : "Could not delete note.", true);
    }
  };

  if (authLoading) return <div className="card" style={{ marginTop: 32 }}>Loading…</div>;

  const dp = simOut?.delta_profit ?? 0;
  const up = dp >= 0;

  return (
    <>
      <div className="page-head">
        <h2>
          The <span className="grad">Lab</span>
        </h2>
        <p>Test &quot;what if?&quot; scenarios, track monthly goals and keep case notes — all private to you.</p>
      </div>

      {!datasetId ? (
        <div className="card empty">
          <div className="ico">🧪</div>
          <h3>No dataset loaded</h3>
          <p className="muted">Load a dataset first, then come back to experiment.</p>
          <Link className="btn" href="/">
            Go to upload
          </Link>
        </div>
      ) : (
        <div className="lab">
          <div className="card glow fade">
            <div className="between">
              <h3 style={{ margin: 0 }}>What-if simulator</h3>
              <span className="tag medium">{simMonth}</span>
            </div>
            <p className="muted" style={{ margin: "6px 0 0", fontSize: 14 }}>
              Pick one product-region segment and nudge orders, price or margin to see the profit impact.
            </p>
            <div className="field" style={{ marginTop: 16 }}>
              <label htmlFor="segSel">Segment</label>
              <select
                id="segSel"
                value={segment}
                onChange={(e) => {
                  const seg = e.target.value;
                  setSegment(seg);
                  void runSim(seg, ordersPct, pricePct, marginPts, true);
                }}
              >
                {segments.map((x) => (
                  <option key={x.name} value={x.name}>
                    {x.name} · {fmtInr(x.sales)}
                  </option>
                ))}
              </select>
            </div>

            <div className="slider-row">
              <div className="top">
                <span>Orders</span>
                <output>{`${ordersPct > 0 ? "+" : ""}${ordersPct}%`}</output>
              </div>
              <input
                type="range"
                min={-80}
                max={100}
                step={1}
                value={ordersPct}
                aria-label="Change in orders, percent"
                onChange={(e) => {
                  const v = Number(e.target.value);
                  setOrdersPct(v);
                  schedulePreview(v, pricePct, marginPts);
                }}
                onPointerUp={() => commitRelease(ordersPct, pricePct, marginPts)}
                onKeyUp={() => commitRelease(ordersPct, pricePct, marginPts)}
              />
            </div>

            <div className="slider-row">
              <div className="top">
                <span>Average price per order</span>
                <output>{`${pricePct > 0 ? "+" : ""}${pricePct}%`}</output>
              </div>
              <input
                type="range"
                min={-30}
                max={30}
                step={1}
                value={pricePct}
                aria-label="Change in price, percent"
                onChange={(e) => {
                  const v = Number(e.target.value);
                  setPricePct(v);
                  schedulePreview(ordersPct, v, marginPts);
                }}
                onPointerUp={() => commitRelease(ordersPct, pricePct, marginPts)}
                onKeyUp={() => commitRelease(ordersPct, pricePct, marginPts)}
              />
            </div>

            <div className="slider-row">
              <div className="top">
                <span>Profit margin</span>
                <output>{`${marginPts > 0 ? "+" : ""}${marginPts} pts`}</output>
              </div>
              <input
                type="range"
                min={-15}
                max={15}
                step={0.5}
                value={marginPts}
                aria-label="Change in margin, percentage points"
                onChange={(e) => {
                  const v = Number(e.target.value);
                  setMarginPts(v);
                  schedulePreview(ordersPct, pricePct, v);
                }}
                onPointerUp={() => commitRelease(ordersPct, pricePct, marginPts)}
                onKeyUp={() => commitRelease(ordersPct, pricePct, marginPts)}
              />
            </div>

            <div className="row" style={{ marginBottom: 6 }}>
              <button
                type="button"
                className="btn ghost sm"
                onClick={() => {
                  const v = simOut?.restore_order_change_pct;
                  if (v == null) {
                    toast("No orders last month to compare with.", true);
                    return;
                  }
                  const clamped = Math.max(-80, Math.min(100, Math.round(v)));
                  setOrdersPct(clamped);
                  void runSim(segment, clamped, pricePct, marginPts, true);
                }}
              >
                ↺ Match last month&apos;s orders
              </button>
              <button
                type="button"
                className="btn ghost sm"
                onClick={() => {
                  setOrdersPct(0);
                  setPricePct(0);
                  setMarginPts(0);
                  void runSim(segment, 0, 0, 0, false);
                }}
              >
                Reset sliders
              </button>
            </div>

            {simOut && (
              <>
                <div className="result">
                  <div className="d">
                    <small>Scenario profit</small>
                    <b>{fmtInr(simOut.scenario.profit)}</b>
                  </div>
                  <div className="d">
                    <small>Change in profit</small>
                    <b className={up ? "up" : "down"}>
                      {up ? "▲" : "▼"} {fmtInr(Math.abs(dp))}
                    </b>
                  </div>
                  <div className="d">
                    <small>Scenario sales</small>
                    <b>{fmtInr(simOut.scenario.sales)}</b>
                  </div>
                  <div className="d">
                    <small>Orders · margin</small>
                    <b>
                      {Math.round(simOut.scenario.orders)} · {simOut.scenario.margin.toFixed(1)}%
                    </b>
                  </div>
                  <div className="d" style={{ gridColumn: "1/-1" }}>
                    <small>Impact on the whole month&apos;s profit</small>
                    <b className={up ? "up" : "down"}>
                      {simOut.pct_of_month_profit == null ? "n/a" : pctf(simOut.pct_of_month_profit, 2)}
                    </b>
                  </div>
                </div>
                {simChart && (
                  <div style={{ marginTop: 8 }}>
                    <PlotlyChart data={simChart.data} layout={simChart.layout} />
                  </div>
                )}
              </>
            )}

            <div className="note">
              Illustration, not a forecast: it assumes the segment&apos;s average order value and margin stay the same
              unless you change them, and that nothing else moves.
            </div>
          </div>

          <div style={{ display: "grid", gap: 18 }}>
            <div className="card fade">
              <h3 style={{ margin: "0 0 4px" }}>Monthly goals</h3>
              <p className="muted" style={{ margin: "0 0 14px", fontSize: 14 }}>
                {goalMonth ? `Targets for ${goalMonth} (the latest month in your data).` : "Set a target for the latest month."}
              </p>

              <div>
                {goals.length ? (
                  goals.map((x) => {
                    const p = Math.min(x.pct, 100);
                    const met = x.pct >= 100;
                    return (
                      <div className="goal" key={x.metric}>
                        <div className="ring" style={{ ["--p" as string]: p.toFixed(0) }}>
                          <span>{Math.round(x.pct)}%</span>
                        </div>
                        <div style={{ flex: 1 }}>
                          <b style={{ textTransform: "capitalize" }}>
                            {x.metric} goal · {fmtInr(x.target)}
                          </b>
                          <div className="muted" style={{ fontSize: 13 }}>
                            So far {fmtInr(x.actual)}{" "}
                            {met ? (
                              <>
                                · <b className="up">target reached ✔</b>
                              </>
                            ) : (
                              `· ${fmtInr(x.remaining)} to go`
                            )}
                          </div>
                          <div className="muted" style={{ fontSize: 12.5 }}>
                            {!met && x.needed_per_day != null
                              ? `Needs about ${fmtInr(x.needed_per_day)} per day for the last ${x.days_left} day(s).`
                              : met
                                ? "Nice work."
                                : "The month is complete."}
                          </div>
                        </div>
                        <button
                          type="button"
                          className="x"
                          aria-label="Delete goal"
                          onClick={() => void deleteGoal(x.metric)}
                        >
                          ✕
                        </button>
                      </div>
                    );
                  })
                ) : (
                  <p className="muted" style={{ margin: 0 }}>
                    No goals yet.
                  </p>
                )}
              </div>

              <div className="row" style={{ marginTop: 14, alignItems: "flex-end" }}>
                <div className="field" style={{ margin: 0, flex: "0 0 120px" }}>
                  <label htmlFor="gMetric">Metric</label>
                  <select
                    id="gMetric"
                    value={goalMetric}
                    onChange={(e) => setGoalMetric(e.target.value as MetricKind)}
                  >
                    <option value="profit">Profit</option>
                    <option value="sales">Sales</option>
                  </select>
                </div>
                <div className="field" style={{ margin: 0, flex: 1, minWidth: 120 }}>
                  <label htmlFor="gAmount">Target (₹)</label>
                  <input
                    id="gAmount"
                    type="number"
                    min={1}
                    step={1000}
                    placeholder="e.g. 500000"
                    value={goalAmount}
                    onChange={(e) => setGoalAmount(e.target.value)}
                  />
                </div>
                <button type="button" className="btn sm" onClick={() => void saveGoal()}>
                  Set goal
                </button>
              </div>
              {goalErr && (
                <div className="err" style={{ marginTop: 12 }}>
                  {goalErr}
                </div>
              )}
            </div>

            <div className="card fade">
              <h3 style={{ margin: "0 0 4px" }}>Case notes</h3>
              <p className="muted" style={{ margin: "0 0 12px", fontSize: 14 }}>
                Jot down hunches and follow-ups for this dataset.
              </p>
              <div className="field" style={{ margin: 0 }}>
                <textarea
                  maxLength={500}
                  placeholder="e.g. Ask the South team about the laptop discount campaign…"
                  style={{ minHeight: 76 }}
                  value={noteText}
                  onChange={(e) => setNoteText(e.target.value)}
                />
                <div className="hint2">{noteText.length} / 500</div>
              </div>
              <div className="row" style={{ marginTop: 8 }}>
                <button type="button" className="btn sm" onClick={() => void addNote()}>
                  ＋ Add note
                </button>
              </div>
              <ul className="notes">
                {notes.length ? (
                  notes.map((n) => (
                    <li key={n.id}>
                      <div>
                        {n.text}
                        <small>{n.created_at}</small>
                      </div>
                      <button
                        type="button"
                        className="x"
                        aria-label="Delete note"
                        onClick={() => void deleteNote(n.id)}
                      >
                        ✕
                      </button>
                    </li>
                  ))
                ) : (
                  <li className="muted">No notes yet.</li>
                )}
              </ul>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
