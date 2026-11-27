"use client";

import React, { createContext, useCallback, useContext, useEffect, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import { apiFetch, setCsrfToken } from "@/lib/api";
import type { GamifyStats, SessionResponse, UserProfile } from "@/types/api";

interface AuthContextValue {
  loading: boolean;
  sessionError: string | null;
  authenticated: boolean;
  user: UserProfile | null;
  stats: GamifyStats | null;
  datasetId: string | null;
  datasetName: string | null;
  setActiveDataset: (id: string, filename: string) => void;
  refreshSession: () => Promise<void>;
  signOut: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);
const PROTECTED = ["/dashboard", "/investigation", "/lab", "/data", "/reports", "/profile"];

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [loading, setLoading] = useState(true);
  const [sessionError, setSessionError] = useState<string | null>(null);
  const [user, setUser] = useState<UserProfile | null>(null);
  const [stats, setStats] = useState<GamifyStats | null>(null);
  const [datasetId, setDatasetId] = useState<string | null>(null);
  const [datasetName, setDatasetName] = useState<string | null>(null);

  const router = useRouter();
  const pathname = usePathname() || "/";

  const readStoredDataset = useCallback((uid: number) => {
    const key = `abd_dataset_${uid}`;
    setDatasetId(localStorage.getItem(key));
    setDatasetName(localStorage.getItem(`${key}_name`));
  }, []);

  const refreshSession = useCallback(async () => {
    setSessionError(null);
    try {
      const sess = await apiFetch<SessionResponse>("/api/auth/session");
      setCsrfToken(sess.csrf_token);
      if (sess.authenticated && sess.user) {
        setUser(sess.user);
        setStats(sess.stats);
        readStoredDataset(sess.user.id);
      } else {
        setUser(null);
        setStats(null);
        setDatasetId(null);
        setDatasetName(null);
      }
    } catch (err) {
      setSessionError(err instanceof Error ? err.message : "Could not reach backend API.");
    } finally {
      setLoading(false);
    }
  }, [readStoredDataset]);

  useEffect(() => {
    void refreshSession();
  }, [refreshSession]);

  useEffect(() => {
    if (loading || sessionError) return;
    const norm = pathname.replace(/\/$/, "") || "/";
    const isProtected = PROTECTED.some((p) => norm === p || norm.startsWith(`${p}/`));
    if (!user && isProtected) {
      const search = typeof window !== "undefined" ? window.location.search : "";
      router.replace(`/login?next=${encodeURIComponent(norm + search)}`);
    } else if (user && (norm === "/login" || norm === "/register")) {
      router.replace("/dashboard");
    }
  }, [loading, sessionError, user, pathname, router]);

  const setActiveDataset = useCallback(
    (id: string, filename: string) => {
      if (!user) return;
      const key = `abd_dataset_${user.id}`;
      localStorage.setItem(key, id);
      localStorage.setItem(`${key}_name`, filename);
      setDatasetId(id);
      setDatasetName(filename);
    },
    [user]
  );

  const signOut = useCallback(async () => {
    try {
      await apiFetch("/api/auth/logout", { method: "POST" });
    } catch {
      // Ignore error if session already expired
    }
    if (user) {
      localStorage.removeItem(`abd_dataset_${user.id}`);
      localStorage.removeItem(`abd_dataset_${user.id}_name`);
    }
    setUser(null);
    setStats(null);
    setDatasetId(null);
    setDatasetName(null);
    router.replace("/login");
  }, [user, router]);

  return (
    <AuthContext.Provider
      value={{
        loading,
        sessionError,
        authenticated: Boolean(user),
        user,
        stats,
        datasetId,
        datasetName,
        setActiveDataset,
        refreshSession,
        signOut,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside <AuthProvider>");
  return ctx;
}
