"use client";

import { useEffect, useRef } from "react";
import type { Config, Data, Layout } from "plotly.js";

export const PALETTE = {
  obsidian: "#050507",
  obsidian2: "#0c0c11",
  silver: "#c9cdd3",
  silverHi: "#f2f4f7",
  silverLo: "#8a9098",
  dim: "#4d525a",
  crimson: "#ff1a40",
  crimsonHi: "#ff4d6d",
  crimsonLo: "#a10020",
  good: "#f2f4f7",
  bad: "#ff1a40",
};

interface PlotlyChartProps {
  data: Data[];
  layout?: Partial<Layout>;
  className?: string;
  style?: React.CSSProperties;
}

export function PlotlyChart({ data, layout = {}, className, style }: PlotlyChartProps) {
  const elRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    let active = true;
    let observer: ResizeObserver | null = null;
    const node = elRef.current;
    if (!node) return;

    (async () => {
      const mod = (await import("plotly.js-dist-min")) as unknown as {
        default?: typeof import("plotly.js");
      } & typeof import("plotly.js");
      if (!active || !elRef.current) return;
      const Plotly = mod.default ?? mod;

      const mergedLayout: Partial<Layout> = {
        autosize: true,
        paper_bgcolor: "rgba(0,0,0,0)",
        plot_bgcolor: "rgba(0,0,0,0)",
        font: { color: PALETTE.silverHi, family: "Inter, system-ui, sans-serif", size: 12 },
        margin: { t: 14, r: 16, b: 40, l: 62 },
        xaxis: { gridcolor: "rgba(201,205,211,.15)", zerolinecolor: "rgba(201,205,211,.15)" },
        yaxis: { gridcolor: "rgba(201,205,211,.15)", zerolinecolor: "rgba(201,205,211,.15)" },
        legend: { orientation: "h", y: 1.16 },
        hoverlabel: { bgcolor: PALETTE.obsidian2, font: { color: PALETTE.silverHi } },
        ...layout,
      };

      const config: Partial<Config> = { displayModeBar: false, responsive: true };
      await Plotly.react(elRef.current, data, mergedLayout, config);

      if (typeof ResizeObserver !== "undefined" && elRef.current) {
        observer = new ResizeObserver(() => {
          if (elRef.current) Plotly.Plots.resize(elRef.current);
        });
        observer.observe(elRef.current);
      }
    })();

    return () => {
      active = false;
      observer?.disconnect();
    };
  }, [data, layout]);

  return <div ref={elRef} className={className} style={{ width: "100%", minHeight: 280, ...style }} />;
}
