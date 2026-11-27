"use client";

import Link from "next/link";
import { useRef, useState } from "react";
import { useAuth } from "@/components/AuthProvider";
import { CountUp } from "@/components/CountUp";
import { useToast } from "@/components/ToastProvider";
import { ApiError, apiFetch } from "@/lib/api";
import type { TargetField, UploadNeedsMappingError, UploadSuccessResponse } from "@/types/api";

const MAPPING_FIELDS: [TargetField, string, boolean][] = [
  ["order_date", "Date of sale", true],
  ["sales", "Sales amount", true],
  ["profit", "Profit", false],
  ["product", "Product / item", false],
  ["category", "Category", false],
  ["region", "Region / city / store", false],
  ["quantity", "Quantity / units", false],
  ["discount_pct", "Discount %", false],
];

export default function HomePage() {
  const { authenticated, setActiveDataset } = useAuth();
  const { toast } = useToast();
  const fileRef = useRef<HTMLInputElement | null>(null);

  const [dragOver, setDragOver] = useState(false);
  const [busy, setBusy] = useState(false);
  const [errorMsg, setErrorMsg] = useState("");
  const [success, setSuccess] = useState<UploadSuccessResponse | null>(null);
  const [mappingData, setMappingData] = useState<UploadNeedsMappingError | null>(null);
  const [mapping, setMapping] = useState<Record<string, string>>({});

  const runIngest = async (fn: () => Promise<UploadSuccessResponse>) => {
    setBusy(true);
    setErrorMsg("");
    setSuccess(null);
    setMappingData(null);
    try {
      const r = await fn();
      setActiveDataset(r.dataset.id, r.dataset.filename);
      setSuccess(r);
    } catch (err) {
      if (err instanceof ApiError && err.data?.needs_mapping) {
        const md = err.data as unknown as UploadNeedsMappingError;
        const initial: Record<string, string> = {};
        for (const [k] of MAPPING_FIELDS) {
          const val = md.suggestions?.[k];
          if (val) initial[k] = val;
        }
        setMapping(initial);
        setMappingData(md);
      } else {
        const msg = err instanceof Error ? err.message : "Upload failed.";
        toast(msg, true);
        setErrorMsg(msg);
      }
    } finally {
      setBusy(false);
    }
  };

  const loadSample = (kind: "clean" | "dirty") =>
    void runIngest(() => apiFetch<UploadSuccessResponse>("/api/sample", { method: "POST", body: { kind } }));

  const uploadFile = (file: File) => {
    const fd = new FormData();
    fd.append("file", file);
    void runIngest(() => apiFetch<UploadSuccessResponse>("/api/upload", { method: "POST", body: fd }));
  };

  const submitMapping = () => {
    if (!mappingData) return;
    if (!mapping.order_date || !mapping.sales) {
      toast("Please choose the Date and Sales columns.", true);
      return;
    }
    const chosen = Object.values(mapping).filter(Boolean);
    if (new Set(chosen).size !== chosen.length) {
      toast("Each column can only be used once.", true);
      return;
    }
    void runIngest(() =>
      apiFetch<UploadSuccessResponse>("/api/upload/map", {
        method: "POST",
        body: { token: mappingData.token, filename: mappingData.filename, mapping },
      })
    );
  };

  return (
    <>
      <section className="hero">
        <div className="laser-beam" aria-hidden="true" />
        <div className="fade">
          <span className="eyebrow">
            <i /> Evidence first · no guessed causes
          </span>
          <h1>
            Your sales dipped.
            <br />
            <span className="grad">Now find out</span> <span className="hot">why.</span>
          </h1>
          <p className="lead">
            AI Business Detective cleans your sales file, spots unusual changes, and shows exactly which products and
            regions moved the numbers — then explains it in plain English, using only what the data supports.
          </p>
          <div className="row" style={{ marginTop: 26 }}>
            {authenticated ? (
              <>
                <button type="button" className="btn" id="btnSample" onClick={() => loadSample("clean")}>
                  🔎 Open the demo case
                </button>
                <button type="button" className="btn ghost" id="btnDirty" onClick={() => loadSample("dirty")}>
                  🧹 See it fix messy data
                </button>
              </>
            ) : (
              <>
                <Link className="btn" href="/register">
                  🔴 Create your free account
                </Link>
                <Link className="btn ghost" href="/login">
                  Sign in
                </Link>
              </>
            )}
          </div>
          <div className="stats">
            <div className="card">
              <b>
                <CountUp value={10} durationMs={1200} />
              </b>
              <span>analysis tools</span>
            </div>
            <div className="card">
              <b>
                <CountUp value={50} durationMs={1200} />
              </b>
              <span>automated tests</span>
            </div>
            <div className="card">
              <b>0 ₹</b>
              <span>to run locally</span>
            </div>
          </div>
        </div>

        <div className="fade" style={{ animationDelay: ".15s" }}>
          <div className="card glow hero-card">
            <div className="between">
              <b>Profit · Sep → Oct</b>
              <span className="tag high">−22.7%</span>
            </div>
            <div className="mini-kpis" style={{ marginTop: 12 }}>
              <div className="mini">
                <small>Biggest contributor</small>
                <b>Laptop · South</b>
              </div>
              <div className="mini">
                <small>Orders in segment</small>
                <b className="down">−72%</b>
              </div>
              <div className="mini">
                <small>Avg discount</small>
                <b className="down">+11.7 pts</b>
              </div>
              <div className="mini">
                <small>Unusual days</small>
                <b>3 flagged</b>
              </div>
            </div>
            <svg className="spark" viewBox="0 0 400 90" preserveAspectRatio="none">
              <defs>
                <linearGradient id="sg" x1="0" x2="1">
                  <stop offset="0" stopColor="#c9cdd3" />
                  <stop offset="1" stopColor="#ff1a40" />
                </linearGradient>
              </defs>
              <path
                d="M0 60 C40 55 60 30 100 38 S160 62 200 42 S270 14 310 52 S370 70 400 78"
                fill="none"
                stroke="url(#sg)"
                strokeWidth="4"
                strokeLinecap="round"
              />
            </svg>
            <span className="float-chip c1">🚨 Spike on 21 Sep</span>
            <span className="float-chip c2">✅ Evidence-based</span>
          </div>
        </div>
      </section>

      {authenticated ? (
        <section className="card" style={{ marginTop: 34 }} id="upload">
          <div className="between">
            <div>
              <h3 style={{ margin: 0, fontSize: 20 }}>Start with your own data</h3>
              <span className="muted">Up to 50 MB · private to your account</span>
            </div>
          </div>
          <div className="row" style={{ marginTop: 12 }} id="fmtChips">
            <span className="chip">📗 Excel .xlsx .xlsm .xls</span>
            <span className="chip">📄 CSV / TSV / TXT</span>
            <span className="chip">📕 PDF tables</span>
            <span className="chip">📊 Power BI .pbix</span>
            <span className="chip">🧾 JSON</span>
            <span className="chip">📘 OpenDocument .ods</span>
          </div>
          <div
            className={`drop${dragOver ? " over" : ""}`}
            style={{ marginTop: 16 }}
            onClick={() => fileRef.current?.click()}
            onDragEnter={(e) => {
              e.preventDefault();
              setDragOver(true);
            }}
            onDragOver={(e) => {
              e.preventDefault();
              setDragOver(true);
            }}
            onDragLeave={(e) => {
              e.preventDefault();
              setDragOver(false);
            }}
            onDrop={(e) => {
              e.preventDefault();
              setDragOver(false);
              const f = e.dataTransfer.files?.[0];
              if (f) uploadFile(f);
            }}
          >
            <div className="ico">📂</div>
            <b>Drop a file here, or click to browse</b>
            <div className="muted" style={{ fontSize: 13, marginTop: 2 }}>
              Excel · CSV · PDF · Power BI · JSON · ODS
            </div>
            <p className="muted" style={{ margin: "8px 0 0" }}>
              Columns: <code>order_date</code> <code>product</code> <code>category</code> <code>region</code>{" "}
              <code>quantity</code> <code>sales</code> <code>profit</code>{" "}
              <span className="muted">
                (optional <code>discount_pct</code>)
              </span>
            </p>
            <input
              ref={fileRef}
              type="file"
              accept=".csv,.tsv,.txt,.xlsx,.xlsm,.xls,.ods,.json,.pdf,.pbix"
              hidden
              onChange={(e) => {
                const f = e.target.files?.[0];
                if (f) uploadFile(f);
                e.target.value = "";
              }}
            />
          </div>

          <div style={{ marginTop: 16 }}>
            {busy && <div className="skel" style={{ width: "60%" }} />}
            {errorMsg && <div className="warnbox">⚠ {errorMsg}</div>}

            {success && (
              <div className="card fade" style={{ background: "rgba(201,205,211,.06)" }}>
                ✅ <b>{success.dataset.filename}</b> loaded — {success.dataset.quality.rows_in} rows in,{" "}
                {success.dataset.quality.rows_out} analysed, quality score{" "}
                <b>{success.dataset.quality.quality_score}/100</b>
                {success.dataset.quality.issues.length
                  ? ` · ${success.dataset.quality.issues.length} issue type(s) handled`
                  : ""}
                .
                {success.source_note && (
                  <div className="muted" style={{ fontSize: 13, marginTop: 4 }}>
                    📎 {success.source_note}
                  </div>
                )}
                <div className="row" style={{ marginTop: 12 }}>
                  <Link className="btn sm" href="/dashboard">
                    📊 Open dashboard
                  </Link>
                  <Link className="btn sm ghost" href="/investigation">
                    🔍 Investigate
                  </Link>
                </div>
              </div>
            )}

            {mappingData && (
              <div className="card glow fade">
                <h3 style={{ margin: "0 0 4px" }}>🧭 Help me read your columns</h3>
                <p className="muted" style={{ margin: "0 0 14px" }}>
                  I couldn&apos;t recognise the column names in <b>{mappingData.filename}</b>. I&apos;ve guessed below —
                  please check, then continue. <b>Date</b> and <b>Sales</b> are required.
                </p>
                <div className="tablewrap" style={{ marginBottom: 16 }}>
                  <table className="t">
                    <thead>
                      <tr>
                        {mappingData.columns.map((c) => (
                          <th key={c}>{c}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {mappingData.preview.map((row, i) => (
                        <tr key={i}>
                          {mappingData.columns.map((c) => (
                            <td key={c}>{row[c]}</td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>

                <div className="grid g4">
                  {MAPPING_FIELDS.map(([key, label, req]) => (
                    <label key={key} className="maplab">
                      <span>
                        {label} {req && <span className="down">*</span>}
                      </span>
                      <select
                        value={mapping[key] || ""}
                        onChange={(e) => setMapping((m) => ({ ...m, [key]: e.target.value }))}
                      >
                        <option value="">— none —</option>
                        {mappingData.columns.map((c) => (
                          <option key={c} value={c}>
                            {c}
                          </option>
                        ))}
                      </select>
                    </label>
                  ))}
                </div>

                <div className="row" style={{ marginTop: 18 }}>
                  <button type="button" className="btn" onClick={submitMapping}>
                    ✅ Use these columns
                  </button>
                  <button type="button" className="btn ghost" onClick={() => setMappingData(null)}>
                    Cancel
                  </button>
                </div>
              </div>
            )}
          </div>
        </section>
      ) : (
        <section className="card glow" style={{ marginTop: 34, textAlign: "center", padding: "38px 24px" }}>
          <h3 style={{ margin: "0 0 6px", fontSize: 22 }}>Sign in to start investigating</h3>
          <p className="muted" style={{ margin: "0 0 18px" }}>
            Your datasets, reports, notes and goals are private to your account.
          </p>
          <div className="row" style={{ justifyContent: "center" }}>
            <Link className="btn" href="/register">
              Create account
            </Link>
            <Link className="btn ghost" href="/login">
              Sign in
            </Link>
          </div>
        </section>
      )}

      <h2 className="sec reveal">
        Everything an analyst does by hand — <span className="grad">automated</span>
      </h2>
      <p className="sec-sub reveal">From a raw spreadsheet to a defensible explanation in a few clicks.</p>
      <div className="bento">
        <div className="card feat hover reveal b2">
          <div className="ico">🧹</div>
          <h3>Reads almost any file</h3>
          <p>
            Excel (even with title rows and many sheets), CSV, PDF tables, Power BI and JSON. Then cleans it without
            guessing — every fix is listed.
          </p>
        </div>
        <div className="card feat hover reveal b4">
          <div className="ico">🔍</div>
          <h3>Finds who moved the number</h3>
          <p>
            Ranks contributors by product, region, category and product × region, then looks inside the biggest one: did
            orders fall, did prices drop, did discounts or margins change?
          </p>
        </div>
        <div className="card feat hover reveal b3">
          <div className="ico">🎛️</div>
          <h3>Interactive dashboard</h3>
          <p>
            Filter by region, category, product and dates. Heatmaps, trends, margin-by-discount and a simple next-month
            projection.
          </p>
        </div>
        <div className="card feat hover reveal b3">
          <div className="ico">🚨</div>
          <h3>Unusual-day detection</h3>
          <p>
            Robust statistics plus Isolation Forest flag spikes and dips — described as &quot;unusual&quot;, never as
            &quot;wrong&quot;.
          </p>
        </div>
        <div className="card feat hover reveal b2">
          <div className="ico">💬</div>
          <h3>Ask in plain English</h3>
          <p>&quot;Why did profit drop?&quot; gets an answer built only from calculated figures.</p>
        </div>
        <div className="card feat hover reveal b2">
          <div className="ico">🗂️</div>
          <h3>Data explorer</h3>
          <p>Search, sort and page through your cleaned data. Export it as CSV.</p>
        </div>
        <div className="card feat hover reveal b2">
          <div className="ico">📄</div>
          <h3>Shareable reports</h3>
          <p>One-click HTML report you can print to PDF, plus contributor tables as CSV.</p>
        </div>
        <div className="card feat hover reveal b3">
          <div className="ico">🧪</div>
          <h3>What-if lab</h3>
          <p>
            Nudge orders, price or margin for one product-region segment and see the profit impact instantly — an
            illustration, never a forecast.
          </p>
        </div>
        <div className="card feat hover reveal b3">
          <div className="ico">❤</div>
          <h3>Business health score</h3>
          <p>A 0–100 score from growth, profitability, stability and data quality. The formula is shown.</p>
        </div>
        <div className="card feat hover reveal b2">
          <div className="ico">🎯</div>
          <h3>Goals &amp; case notes</h3>
          <p>Set a monthly target, see the daily pace you need, and keep notes against each dataset.</p>
        </div>
        <div className="card feat hover reveal b2">
          <div className="ico">🔐</div>
          <h3>Private accounts</h3>
          <p>Sign-in, profile photo and your own space. Datasets are tied to you — nobody else can open them.</p>
        </div>
        <div className="card feat hover reveal b2">
          <div className="ico">🏅</div>
          <h3>Detective ranks</h3>
          <p>
            Earn XP and badges as you upload, investigate and report. Press <span className="kbd">Ctrl K</span> for
            quick actions.
          </p>
        </div>
      </div>

      <h2 className="sec reveal">How it works</h2>
      <div className="grid g4 steps" style={{ marginTop: 26 }}>
        <div className="card reveal">
          <b>Upload</b>
          <p className="muted" style={{ margin: "6px 0 0" }}>
            Excel, CSV, PDF, Power BI or JSON.
          </p>
        </div>
        <div className="card reveal">
          <b>Clean</b>
          <p className="muted" style={{ margin: "6px 0 0" }}>
            Every fix is documented and counted.
          </p>
        </div>
        <div className="card reveal">
          <b>Investigate</b>
          <p className="muted" style={{ margin: "6px 0 0" }}>
            Pandas calculates contributors and drivers.
          </p>
        </div>
        <div className="card reveal">
          <b>Explain</b>
          <p className="muted" style={{ margin: "6px 0 0" }}>
            Plain-English findings, charts and a report.
          </p>
        </div>
      </div>

      <h2 className="sec reveal">Good questions</h2>
      <div style={{ marginTop: 20, maxWidth: 820 }} className="reveal">
        <details className="faq">
          <summary>Does the AI make up causes?</summary>
          <p>
            No. Python and pandas do every calculation. The explanation only describes those numbers, and it states that
            a contributor shows <i>where</i> a change happened, not proof of <i>why</i>.
          </p>
        </details>
        <details className="faq">
          <summary>Which file types work, and what are the limits?</summary>
          <p>
            Excel, CSV/TSV, JSON and OpenDocument work best. PDFs must contain real text tables — scanned images cannot
            be read. Power BI .pbix files work when the data is imported into the file; live-connection or DirectQuery
            reports hold no data, so export a table to CSV/Excel instead.
          </p>
        </details>
        <details className="faq">
          <summary>Is my data uploaded anywhere?</summary>
          <p>
            Data is processed by your connected FastAPI service and saved in your private account workspace. An optional
            LLM key sends only calculated summary figures — never raw rows.
          </p>
        </details>
        <details className="faq">
          <summary>What if my latest month is incomplete?</summary>
          <p>
            The app detects partial months and warns you, so a half-finished month isn&apos;t mistaken for a real
            decline.
          </p>
        </details>
        <details className="faq">
          <summary>What does the forecast mean?</summary>
          <p>It extends the monthly trend in a straight line. It is a rough guide, not a prediction.</p>
        </details>
      </div>

      <section className="card glow cta reveal">
        <h2>
          Ready to <span className="grad">crack the case</span>?
        </h2>
        <p className="muted">Open the demo and watch it find a planted decline.</p>
        {authenticated ? (
          <button type="button" className="btn" onClick={() => loadSample("clean")}>
            🔎 Open the demo case
          </button>
        ) : (
          <Link className="btn" href="/register">
            Create your free account
          </Link>
        )}
      </section>
    </>
  );
}
