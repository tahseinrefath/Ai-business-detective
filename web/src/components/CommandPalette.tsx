"use client";

import { useRouter } from "next/navigation";
import { useEffect, useMemo, useRef, useState } from "react";
import { useAuth } from "@/components/AuthProvider";
import { useToast } from "@/components/ToastProvider";
import { apiFetch } from "@/lib/api";
import type { UploadSuccessResponse } from "@/types/api";

interface PaletteAction {
  icon: string;
  label: string;
  run: () => void | Promise<void>;
}

export function CommandPalette({ open, onOpenChange }: { open: boolean; onOpenChange: (v: boolean) => void }) {
  const { authenticated, setActiveDataset, signOut } = useAuth();
  const { toast } = useToast();
  const router = useRouter();
  const [query, setQuery] = useState("");
  const [sel, setSel] = useState(0);
  const inputRef = useRef<HTMLInputElement | null>(null);

  const actions: PaletteAction[] = useMemo(() => {
    const go = (url: string) => () => router.push(url);
    if (!authenticated) {
      return [
        { icon: "🔑", label: "Sign in", run: go("/login") },
        { icon: "✨", label: "Create account", run: go("/register") },
      ];
    }
    return [
      { icon: "🏠", label: "Home", run: go("/") },
      { icon: "📊", label: "Dashboard", run: go("/dashboard") },
      { icon: "🔍", label: "Investigate", run: go("/investigation") },
      { icon: "🧪", label: "What-if lab", run: go("/lab") },
      { icon: "🗂️", label: "Data explorer", run: go("/data") },
      { icon: "📄", label: "Reports", run: go("/reports") },
      { icon: "👤", label: "My profile", run: go("/profile") },
      {
        icon: "🔎",
        label: "Load the demo case",
        run: async () => {
          try {
            const r = await apiFetch<UploadSuccessResponse>("/api/sample", {
              method: "POST",
              body: { kind: "clean" },
            });
            setActiveDataset(r.dataset.id, r.dataset.filename);
            router.push("/dashboard");
          } catch (e) {
            toast(e instanceof Error ? e.message : "Could not load sample.", true);
          }
        },
      },
      { icon: "🚪", label: "Sign out", run: signOut },
    ];
  }, [authenticated, router, setActiveDataset, signOut, toast]);

  const shown = useMemo(() => {
    const q = query.toLowerCase().trim();
    return actions.filter((a) => a.label.toLowerCase().includes(q));
  }, [actions, query]);

  useEffect(() => {
    if (open) {
      setQuery("");
      setSel(0);
      setTimeout(() => inputRef.current?.focus(), 30);
    }
  }, [open]);

  useEffect(() => {
    setSel((s) => Math.min(s, Math.max(shown.length - 1, 0)));
  }, [shown.length]);

  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        onOpenChange(!open);
      } else if (open) {
        if (e.key === "Escape") {
          onOpenChange(false);
        } else if (e.key === "ArrowDown") {
          e.preventDefault();
          setSel((s) => Math.min(s + 1, Math.max(shown.length - 1, 0)));
        } else if (e.key === "ArrowUp") {
          e.preventDefault();
          setSel((s) => Math.max(s - 1, 0));
        } else if (e.key === "Enter" && shown[sel]) {
          e.preventDefault();
          const act = shown[sel];
          onOpenChange(false);
          void act.run();
        }
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [open, onOpenChange, shown, sel]);

  return (
    <div
      className={`pal-bg${open ? " open" : ""}`}
      onClick={(e) => {
        if (e.target === e.currentTarget) onOpenChange(false);
      }}
    >
      <div className="pal" role="dialog" aria-label="Quick actions">
        <input
          ref={inputRef}
          value={query}
          onChange={(e) => {
            setQuery(e.target.value);
            setSel(0);
          }}
          placeholder="Type a command… (try: dashboard, lab, profile)"
          aria-label="Search actions"
        />
        <ul>
          {shown.length ? (
            shown.map((a, i) => (
              <li
                key={a.label}
                className={i === sel ? "sel" : undefined}
                onClick={() => {
                  onOpenChange(false);
                  void a.run();
                }}
              >
                <span>{a.icon}</span>
                {a.label}
              </li>
            ))
          ) : (
            <div className="empty-r">No matching action</div>
          )}
        </ul>
      </div>
    </div>
  );
}
