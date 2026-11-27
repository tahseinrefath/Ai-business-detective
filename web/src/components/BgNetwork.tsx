"use client";

import { useEffect, useRef } from "react";

export function BgNetwork() {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    // Card pointer spotlight
    const onPointerMove = (e: PointerEvent) => {
      const target = e.target as HTMLElement | null;
      const card = target?.closest?.(".card") as HTMLElement | null;
      if (!card) return;
      const r = card.getBoundingClientRect();
      card.style.setProperty("--mx", `${e.clientX - r.left}px`);
      card.style.setProperty("--my", `${e.clientY - r.top}px`);
    };
    document.addEventListener("pointermove", onPointerMove);

    // IntersectionObserver for .reveal elements
    const io = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add("in");
            io.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.12 }
    );
    const observeReveals = () => {
      document.querySelectorAll(".reveal:not(.in)").forEach((el) => io.observe(el));
    };
    observeReveals();

    // Monochrome emoji selector (\uFE0E)
    const HAS = /\p{Extended_Pictographic}/u;
    const FIX = /(\p{Extended_Pictographic})(?:\uFE0F|(?!\uFE0E))/gu;
    const skip = new Set(["SCRIPT", "STYLE", "TEXTAREA", "INPUT"]);
    const mono = (root: Node) => {
      const w = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
      for (let n = w.nextNode(); n; n = w.nextNode()) {
        if (!n.parentNode || skip.has(n.parentNode.nodeName) || !n.nodeValue || !HAS.test(n.nodeValue)) continue;
        const v = n.nodeValue.replace(FIX, "$1\uFE0E");
        if (v !== n.nodeValue) n.nodeValue = v;
      }
    };
    let pending = false;
    const mo = new MutationObserver(() => {
      if (pending) return;
      pending = true;
      requestAnimationFrame(() => {
        pending = false;
        mono(document.body);
        observeReveals();
      });
    });
    mo.observe(document.body, { childList: true, subtree: true });
    mono(document.body);

    // Animated particle canvas
    const cv = canvasRef.current;
    let raf = 0;
    let cleanupCanvas: (() => void) | null = null;
    if (cv && !window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      const ctx = cv.getContext("2d");
      if (ctx) {
        let dots: { x: number; y: number; vx: number; vy: number }[] = [];
        const resize = () => {
          const r = Math.min(window.devicePixelRatio || 1, 1.5);
          cv.width = window.innerWidth * r;
          cv.height = window.innerHeight * r;
          ctx.setTransform(r, 0, 0, r, 0, 0);
          dots = Array.from({ length: Math.round(Math.min(70, window.innerWidth / 22)) }, () => ({
            x: Math.random() * window.innerWidth,
            y: Math.random() * window.innerHeight,
            vx: (Math.random() - 0.5) * 0.25,
            vy: (Math.random() - 0.5) * 0.25,
          }));
        };
        const frame = () => {
          ctx.clearRect(0, 0, window.innerWidth, window.innerHeight);
          const c1 = getComputedStyle(document.documentElement).getPropertyValue("--a1").trim() || "#c9cdd3";
          ctx.fillStyle = c1;
          ctx.strokeStyle = c1;
          for (const d of dots) {
            d.x += d.vx;
            d.y += d.vy;
            if (d.x < 0 || d.x > window.innerWidth) d.vx *= -1;
            if (d.y < 0 || d.y > window.innerHeight) d.vy *= -1;
            ctx.globalAlpha = 0.55;
            ctx.beginPath();
            ctx.arc(d.x, d.y, 1.4, 0, Math.PI * 2);
            ctx.fill();
          }
          for (let i = 0; i < dots.length; i++) {
            for (let j = i + 1; j < dots.length; j++) {
              const dx = dots[i].x - dots[j].x;
              const dy = dots[i].y - dots[j].y;
              const dist = dx * dx + dy * dy;
              if (dist < 14000) {
                ctx.globalAlpha = (1 - dist / 14000) * 0.22;
                ctx.beginPath();
                ctx.moveTo(dots[i].x, dots[i].y);
                ctx.lineTo(dots[j].x, dots[j].y);
                ctx.stroke();
              }
            }
          }
          raf = requestAnimationFrame(frame);
        };
        const onVis = () => {
          if (document.hidden) cancelAnimationFrame(raf);
          else raf = requestAnimationFrame(frame);
        };
        resize();
        raf = requestAnimationFrame(frame);
        window.addEventListener("resize", resize);
        document.addEventListener("visibilitychange", onVis);
        cleanupCanvas = () => {
          cancelAnimationFrame(raf);
          window.removeEventListener("resize", resize);
          document.removeEventListener("visibilitychange", onVis);
        };
      }
    }

    return () => {
      document.removeEventListener("pointermove", onPointerMove);
      io.disconnect();
      mo.disconnect();
      cleanupCanvas?.();
    };
  }, []);

  return <canvas ref={canvasRef} id="bgnet" aria-hidden="true" />;
}
