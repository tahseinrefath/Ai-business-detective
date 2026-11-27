"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useAuth } from "@/components/AuthProvider";
import { useToast } from "@/components/ToastProvider";
import { apiFetch, getApiUrl } from "@/lib/api";
import type { DatasetMeta } from "@/types/api";

export default function ReportsPage() {
  const { loading: authLoading, authenticated, datasetId, refreshSession } = useAuth();
  const { toast } = useToast();

  const [rows, setRows] = useState<DatasetMeta[] | null>(null);
  const [readyIds, setReadyIds] = useState<Record<string, boolean>>({});
  const [workingIds, setWorkingIds] = useState<Record<string, boolean>>({});

  useEffect(() => {
    if (authLoading || !authenticated) return;
    let active = true;
    (async () => {
      try {
        const list = await apiFetch<DatasetMeta[]>("/api/datasets");
        if (!active) return;
        setRows(list);
        const availability: Record<string, boolean> = {};
        await Promise.all(
          list.map(async (r) => {
            try {
              const res = await fetch(getApiUrl(`/api/report/${r.id}`), { credentials: "include" });
              if (res.ok) availability[r.id] = true;
            } catch {
              // Ignore probe error
            }
          })
        );
        if (active) setReadyIds(availability);
      } catch (err) {
        toast(err instanceof Error ? err.message : "Could not load datasets.", true);
        if (active) setRows([]);
      }
    })();
    return () => {
      active = false;
    };
  }, [authLoading, authenticated, toast]);

  const generateReport = async (id: string) => {
    setWorkingIds((w) => ({ ...w, [id]: true }));
    try {
      await apiFetch(`/api/report/${id}`, { method: "POST", body: { metric: "profit" } });
      setReadyIds((r) => ({ ...r, [id]: true }));
      toast("Report ready ✅");
      void refreshSession();
    } catch (err) {
      toast(err instanceof Error ? err.message : "Failed to generate report.", true);
    } finally {
      setWorkingIds((w) => ({ ...w, [id]: false }));
    }
  };

  if (authLoading) return <div className="card" style={{ marginTop: 32 }}>Loading…</div>;

  return (
    <>
      <div className="page-head">
        <h2>
          Automated <span className="grad">reports</span>
        </h2>
        <p>
          Generate a shareable investigation report. Open it, then use your browser&apos;s Print → Save as PDF if you need
          a PDF.
        </p>
      </div>
      <div className="card" style={{ marginTop: 18 }}>
        <div className="tablewrap">
          <table className="t">
            {rows === null ? (
              <tbody>
                <tr>
                  <td>Loading…</td>
                </tr>
              </tbody>
            ) : !rows.length ? (
              <tbody>
                <tr>
                  <td className="muted">
                    No datasets yet.{" "}
                    <Link href="/" className="grad">
                      <b>Upload one →</b>
                    </Link>
                  </td>
                </tr>
              </tbody>
            ) : (
              <>
                <thead>
                  <tr>
                    <th>Dataset</th>
                    <th>Rows</th>
                    <th>Quality</th>
                    <th>Uploaded</th>
                    <th />
                  </tr>
                </thead>
                <tbody>
                  {rows.map((r) => {
                    const isWorking = Boolean(workingIds[r.id]);
                    const hasReport = Boolean(readyIds[r.id]);
                    return (
                      <tr key={r.id}>
                        <td>
                          <b>{r.filename}</b> {r.id === datasetId && <span className="tag low">active</span>}
                        </td>
                        <td>{r.row_count}</td>
                        <td>{r.quality.quality_score}/100</td>
                        <td className="muted">{r.upload_date.replace("T", " ")}</td>
                        <td className="row">
                          <button
                            type="button"
                            className="btn sm"
                            disabled={isWorking}
                            onClick={() => void generateReport(r.id)}
                          >
                            {isWorking ? "Working…" : hasReport ? "⚡ Regenerate" : "⚡ Generate"}
                          </button>
                          {hasReport && (
                            <>
                              <a
                                className="btn sm ghost"
                                href={getApiUrl(`/api/report/${r.id}`)}
                                target="_blank"
                                rel="noopener noreferrer"
                              >
                                👁 View
                              </a>
                              <a
                                className="btn sm ghost"
                                href={getApiUrl(`/api/report/${r.id}?download=1`)}
                              >
                                ⬇ Download
                              </a>
                            </>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </>
            )}
          </table>
        </div>
      </div>
    </>
  );
}
