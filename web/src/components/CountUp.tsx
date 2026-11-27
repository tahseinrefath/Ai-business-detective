"use client";

import { useEffect, useState } from "react";

interface CountUpProps {
  value: number;
  formatter?: (v: number) => string;
  durationMs?: number;
}

export function CountUp({
  value,
  formatter = (v) => String(Math.round(v)),
  durationMs = 900,
}: CountUpProps) {
  const [display, setDisplay] = useState(0);

  useEffect(() => {
    let raf = 0;
    const t0 = performance.now();
    const step = (t: number) => {
      const p = Math.min((t - t0) / durationMs, 1);
      const eased = 1 - Math.pow(1 - p, 3);
      setDisplay(value * eased);
      if (p < 1) raf = requestAnimationFrame(step);
    };
    raf = requestAnimationFrame(step);
    return () => cancelAnimationFrame(raf);
  }, [value, durationMs]);

  return <>{formatter(display)}</>;
}
