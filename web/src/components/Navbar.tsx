"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { useAuth } from "@/components/AuthProvider";
import { getApiUrl } from "@/lib/api";
import { initialsOf } from "@/lib/format";

const NAV_ITEMS = [
  { href: "/", label: "Home", match: "/" },
  { href: "/dashboard", label: "Dashboard", match: "/dashboard" },
  { href: "/investigation", label: "Investigate", match: "/investigation" },
  { href: "/lab", label: "Lab", match: "/lab" },
  { href: "/data", label: "Data", match: "/data" },
  { href: "/reports", label: "Reports", match: "/reports" },
];

export function Navbar({ onOpenPalette }: { onOpenPalette: () => void }) {
  const { authenticated, user, stats, datasetId, datasetName, signOut } = useAuth();
  const pathname = (usePathname() || "/").replace(/\/$/, "") || "/";
  const [menuOpen, setMenuOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const onDocClick = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setMenuOpen(false);
      }
    };
    document.addEventListener("click", onDocClick);
    return () => document.removeEventListener("click", onDocClick);
  }, []);

  useEffect(() => {
    setMenuOpen(false);
  }, [pathname]);

  return (
    <nav className="nav">
      <div className="wrap">
        <Link className="brand" href="/" aria-label="AI Business Detective home">
          <svg viewBox="0 0 64 64" width="32" height="32">
            <defs>
              <linearGradient id="lg" x1="0" y1="0" x2="1" y2="1">
                <stop offset="0" stopColor="var(--a1)" />
                <stop offset=".6" stopColor="var(--a2)" />
                <stop offset="1" stopColor="var(--a3)" />
              </linearGradient>
            </defs>
            <circle cx="27" cy="27" r="17" fill="none" stroke="url(#lg)" strokeWidth="6" />
            <path d="M40 40l16 16" stroke="url(#lg)" strokeWidth="7" strokeLinecap="round" />
            <path
              d="M18 31l6-6 5 4 7-8"
              fill="none"
              stroke="currentColor"
              strokeWidth="3.2"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
          <span>
            AI Business <b className="grad">Detective</b>
          </span>
        </Link>

        {authenticated && (
          <div className="links">
            {NAV_ITEMS.map((item) => {
              const active =
                item.match === "/"
                  ? pathname === "/"
                  : pathname === item.match || pathname.startsWith(`${item.match}/`);
              return (
                <Link key={item.href} href={item.href} className={active ? "on" : undefined}>
                  {item.label}
                </Link>
              );
            })}
          </div>
        )}

        {authenticated && (
          <div className="badge-ds" id="dsBadge">
            {datasetId ? (
              <>
                Dataset: <b>{datasetName || datasetId}</b>
              </>
            ) : (
              "No dataset"
            )}
          </div>
        )}

        <div className="nav-right" style={!authenticated ? { marginLeft: "auto" } : undefined}>
          <button
            type="button"
            className="nav-search"
            id="palBtn"
            aria-label="Open command menu"
            onClick={onOpenPalette}
          >
            ⌘ <span>Quick actions</span> <span className="kbd">Ctrl K</span>
          </button>

          {authenticated && user ? (
            <>
              <Link className="lvl" href="/profile" title="Your detective rank">
                Lv <b>{stats?.level ?? 1}</b> · {stats?.title ?? "Rookie"}
              </Link>
              <div className="usermenu" ref={menuRef}>
                <button
                  type="button"
                  id="userBtn"
                  aria-label="Account menu"
                  aria-haspopup="true"
                  aria-expanded={menuOpen}
                  onClick={(e) => {
                    e.stopPropagation();
                    setMenuOpen((o) => !o);
                  }}
                >
                  <span className="avatar">
                    {user.has_avatar ? (
                      <img id="navAvatar" src={getApiUrl(`/avatar/me?v=${user.avatar_v || 0}`)} alt="" />
                    ) : (
                      <span id="navInitials">{initialsOf(user.name)}</span>
                    )}
                  </span>
                </button>
                <div className={`menu${menuOpen ? " open" : ""}`} id="userMenu" role="menu">
                  <div className="who">
                    <b>{user.name}</b>
                    <span>{user.email}</span>
                  </div>
                  <Link href="/profile">👤 My profile</Link>
                  <Link href="/lab">🧪 What-if lab</Link>
                  <Link href="/reports">📄 My reports</Link>
                  <button type="button" id="logoutBtn" onClick={() => void signOut()}>
                    🚪 Sign out
                  </button>
                </div>
              </div>
            </>
          ) : (
            <>
              <Link className="btn ghost sm" href="/login">
                Sign in
              </Link>
              <Link className="btn sm" href="/register">
                Get started
              </Link>
            </>
          )}
        </div>
      </div>
    </nav>
  );
}
