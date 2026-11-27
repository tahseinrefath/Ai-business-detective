"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { useAuth } from "@/components/AuthProvider";
import { useToast } from "@/components/ToastProvider";
import { apiFetch, getApiUrl } from "@/lib/api";
import { fmtInr } from "@/lib/format";
import type { PreviewResponse } from "@/types/api";

const COLS: [keyof PreviewResponse["rows"][number], string, boolean?][] = [
  ["order_date", "Date"],
  ["product", "Product"],
  ["category", "Category"],
  ["region", "Region"],
  ["quantity", "Qty", true],
  ["sales", "Sales", true],
  ["profit", "Profit", true],
  ["discount_pct", "Discount", true],
];

export default function DataExplorerPage() {
  const { loading: authLoading, authenticated, datasetId } = useAuth();
  const { toast } = useToast();

  const [page, setPage] = useState(1);
  const [sort, setSort] = useState("order_date");
  const [dir, setDir] = useState<"asc" | "desc">("desc");
  const [q, setQ] = useState("");
  const [debouncedQ, setDebouncedQ] = useState("");
  const [data, setData] = useState<PreviewResponse | null>(null);

  useEffect(() => {
    const t = setTimeout(() => {
      setDebouncedQ(q);
      setPage(1);
    }, 250);
    return () => clearTimeout(t);
  }, [q]);

  const load = useCallback(async () => {
    if (!datasetId) return;
    try {
      const res = await apiFetch<PreviewResponse>(
        `/api/preview?dataset=${encodeURIComponent(datasetId)}&page=${page}&sort=${encodeURIComponent(sort)}&dir=${dir}&q=${encodeURIComponent(debouncedQ)}&size=15`
      );
      setData(res);
    } catch (err) {
      toast(err instanceof Error ? err.message : "Could not load preview.", true);
    }
  }, [datasetId, page, sort, dir, debouncedQ, toast]);

  useEffect(() => {
    if (authLoading || !authenticated || !datasetId) return;
    void load();
  }, [authLoading, authenticated, datasetId, load]);

  if (authLoading) return <div className="card" style={{ marginTop: 32 }}>Loading…</div>;

  return (
    <>
      <div className="page-head between">
        <div>
          <h2>
            Data <span className="grad">explorer</span>
          </h2>
          <p>Browse the cleaned data the analysis is built on.</p>
        </div>
        <a
          className="btn ghost sm"
          href={datasetId ? getApiUrl(`/api/export/${datasetId}/clean.csv`) : "#"}
        >
          ⬇ Export cleaned CSV
        </a>
      </div>

      {!datasetId ? (
        <div className="card empty">
          <div className="ico">🗂️</div>
          <h3>No dataset loaded</h3>
          <Link className="btn" href="/">
            Go to upload
          </Link>
        </div>
      ) : (
        <div className="card" style={{ marginTop: 16 }}>
          <div className="between" style={{ marginBottom: 14 }}>
            <input
              type="text"
              placeholder="🔎 Search product, category or region…"
              style={{ minWidth: 300 }}
              value={q}
              onChange={(e) => setQ(e.target.value)}
            />
            <span className="muted">{data ? `${data.total.toLocaleString("en-IN")} rows` : ""}</span>
          </div>

          <div className="tablewrap">
            <table className="t">
              <thead>
                <tr>
                  {COLS.map(([colKey, label, isNum]) => (
                    <th
                      key={colKey}
                      className={isNum ? "num" : undefined}
                      onClick={() => {
                        setDir((prev) => (sort === colKey && prev === "desc" ? "asc" : "desc"));
                        setSort(colKey);
                        setPage(1);
                      }}
                    >
                      {label}
                      {sort === colKey ? (dir === "asc" ? " ▲" : " ▼") : ""}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {data && data.rows.length ? (
                  data.rows.map((r, i) => (
                    <tr key={i}>
                      {COLS.map(([colKey, , isNum]) => {
                        const v = r[colKey];
                        if (v == null) {
                          return (
                            <td key={colKey} className={isNum ? "num" : undefined}>
                              <span className="muted">—</span>
                            </td>
                          );
                        }
                        if (colKey === "sales" || colKey === "profit") {
                          const num = Number(v);
                          return (
                            <td key={colKey} className="num">
                              <span className={colKey === "profit" && num < 0 ? "down" : undefined}>
                                {fmtInr(num)}
                              </span>
                            </td>
                          );
                        }
                        if (colKey === "discount_pct") {
                          return (
                            <td key={colKey} className="num">
                              {Number(v).toFixed(1)}%
                            </td>
                          );
                        }
                        return (
                          <td key={colKey} className={isNum ? "num" : undefined}>
                            {String(v)}
                          </td>
                        );
                      })}
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan={8} className="muted">
                      {data ? "No rows match." : "Loading…"}
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>

          <div className="pager">
            <button
              type="button"
              className="btn ghost sm"
              disabled={!data || data.page <= 1}
              onClick={() => setPage((p) => Math.max(1, p - 1))}
            >
              ← Prev
            </button>
            <span>{data ? `Page ${data.page} of ${data.pages}` : ""}</span>
            <button
              type="button"
              className="btn ghost sm"
              disabled={!data || data.page >= data.pages}
              onClick={() => setPage((p) => p + 1)}
            >
              Next →
            </button>
          </div>
        </div>
      )}
    </>
  );
}
