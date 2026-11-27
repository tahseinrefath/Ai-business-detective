"use client";

import { FormEvent, useCallback, useEffect, useRef, useState } from "react";
import { useAuth } from "@/components/AuthProvider";
import { useToast } from "@/components/ToastProvider";
import { apiFetch, getApiUrl } from "@/lib/api";
import { initialsOf } from "@/lib/format";
import type { GamifyStats, UserProfile } from "@/types/api";

export default function ProfilePage() {
  const { loading: authLoading, authenticated, refreshSession } = useAuth();
  const { toast } = useToast();
  const fileRef = useRef<HTMLInputElement | null>(null);

  const [me, setMe] = useState<UserProfile | null>(null);
  const [stats, setStats] = useState<GamifyStats | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [avatarDrag, setAvatarDrag] = useState(false);

  const [name, setName] = useState("");
  const [jobTitle, setJobTitle] = useState("");
  const [company, setCompany] = useState("");
  const [locationStr, setLocationStr] = useState("");
  const [bio, setBio] = useState("");
  const [profErr, setProfErr] = useState("");

  const [pwCur, setPwCur] = useState("");
  const [pwNew, setPwNew] = useState("");
  const [pwNew2, setPwNew2] = useState("");
  const [pwErr, setPwErr] = useState("");

  const [delOpen, setDelOpen] = useState(false);
  const [delPw, setDelPw] = useState("");
  const [delErr, setDelErr] = useState("");

  const load = useCallback(async () => {
    try {
      const r = await apiFetch<{ user: UserProfile; stats: GamifyStats }>("/api/profile");
      setMe(r.user);
      setStats(r.stats);
      setName(r.user.name);
      setJobTitle(r.user.job_title);
      setCompany(r.user.company);
      setLocationStr(r.user.location);
      setBio(r.user.bio);
    } catch (err) {
      toast(err instanceof Error ? err.message : "Could not load profile.", true);
    }
  }, [toast]);

  useEffect(() => {
    if (authLoading || !authenticated) return;
    void load();
  }, [authLoading, authenticated, load]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setDelOpen(false);
        setDelPw("");
        setDelErr("");
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  const sendAvatar = async (file: File | undefined) => {
    if (!file) return;
    if (!/^image\/(png|jpeg|webp|gif)$/.test(file.type)) {
      toast("Please choose a PNG, JPG, WEBP or GIF image.", true);
      return;
    }
    if (file.size > 3 * 1024 * 1024) {
      toast("That image is over 3 MB.", true);
      return;
    }
    const localUrl = URL.createObjectURL(file);
    setPreviewUrl(localUrl);
    const fd = new FormData();
    fd.append("avatar", file);
    try {
      await apiFetch("/api/profile/avatar", { method: "POST", body: fd });
      await Promise.all([load(), refreshSession()]);
      toast("Profile picture updated ✅");
    } catch (err) {
      await load();
      toast(err instanceof Error ? err.message : "Could not update photo.", true);
    } finally {
      setPreviewUrl(null);
      URL.revokeObjectURL(localUrl);
    }
  };

  const removeAvatar = async () => {
    try {
      await apiFetch("/api/profile/avatar", { method: "DELETE" });
      await Promise.all([load(), refreshSession()]);
      toast("Picture removed");
    } catch (err) {
      toast(err instanceof Error ? err.message : "Failed to remove picture.", true);
    }
  };

  const saveProfile = async (e: FormEvent) => {
    e.preventDefault();
    setProfErr("");
    try {
      const r = await apiFetch<{ ok: boolean; user: UserProfile }>("/api/profile", {
        method: "PUT",
        body: { name, job_title: jobTitle, company, location: locationStr, bio },
      });
      setMe(r.user);
      await refreshSession();
      toast("Profile saved ✅");
    } catch (err) {
      setProfErr(err instanceof Error ? err.message : "Failed to save profile.");
    }
  };

  const updatePassword = async (e: FormEvent) => {
    e.preventDefault();
    setPwErr("");
    if (pwNew !== pwNew2) {
      setPwErr("The new passwords do not match.");
      return;
    }
    try {
      await apiFetch("/api/profile/password", {
        method: "POST",
        body: { current: pwCur, new: pwNew },
      });
      setPwCur("");
      setPwNew("");
      setPwNew2("");
      toast("Password updated ✅");
    } catch (err) {
      setPwErr(err instanceof Error ? err.message : "Failed to update password.");
    }
  };

  const deleteAccount = async () => {
    setDelErr("");
    try {
      await apiFetch("/api/profile/delete", { method: "POST", body: { password: delPw } });
      Object.keys(localStorage)
        .filter((k) => k.startsWith("abd_dataset"))
        .forEach((k) => localStorage.removeItem(k));
      window.location.href = "/";
    } catch (err) {
      setDelErr(err instanceof Error ? err.message : "Failed to delete account.");
    }
  };

  if (authLoading || !me) return <div className="card" style={{ marginTop: 32 }}>Loading…</div>;

  return (
    <>
      <div className="page-head">
        <h2>
          My <span className="grad">profile</span>
        </h2>
        <p>Manage your details, picture and appearance.</p>
      </div>

      <div className="prof">
        <div>
          <div className="card prof-card fade">
            <label
              className={`avatar-drop${avatarDrag ? " over" : ""}`}
              title="Click or drop an image"
              onDragEnter={(e) => {
                e.preventDefault();
                setAvatarDrag(true);
              }}
              onDragOver={(e) => {
                e.preventDefault();
                setAvatarDrag(true);
              }}
              onDragLeave={(e) => {
                e.preventDefault();
                setAvatarDrag(false);
              }}
              onDrop={(e) => {
                e.preventDefault();
                setAvatarDrag(false);
                void sendAvatar(e.dataTransfer.files?.[0]);
              }}
            >
              <span className="avatar xl">
                {previewUrl ? (
                  <img src={previewUrl} alt="" />
                ) : me.has_avatar ? (
                  <img src={getApiUrl(`/avatar/me?v=${me.avatar_v}`)} alt="Your profile picture" />
                ) : (
                  initialsOf(me.name)
                )}
              </span>
              <span className="cam">📷</span>
              <input
                ref={fileRef}
                type="file"
                accept="image/png,image/jpeg,image/webp,image/gif"
                hidden
                onChange={(e) => {
                  void sendAvatar(e.target.files?.[0]);
                  e.target.value = "";
                }}
              />
            </label>

            <h3 style={{ margin: 0, fontSize: 22 }}>{me.name}</h3>
            <div className="muted" style={{ marginTop: 2 }}>
              {[me.job_title, me.company].filter(Boolean).join(" · ") || "Add your job title"}
            </div>
            <div className="muted" style={{ fontSize: 13, marginTop: 4 }}>
              {[me.location, `Member since ${(me.created_at || "").slice(0, 10)}`].filter(Boolean).join(" · ")}
            </div>
            <div className="row" style={{ justifyContent: "center", marginTop: 16 }}>
              <button type="button" className="btn sm" onClick={() => fileRef.current?.click()}>
                ⬆ Upload photo
              </button>
              {me.has_avatar && (
                <button type="button" className="btn ghost sm" onClick={() => void removeAvatar()}>
                  Remove
                </button>
              )}
            </div>
            <div className="hint2" style={{ marginTop: 10 }}>
              PNG, JPG, WEBP or GIF · up to 3 MB · cropped to a square
            </div>
          </div>

          {stats && (
            <div className="card fade" style={{ marginTop: 18 }}>
              <div className="between">
                <b>🕵️ {stats.title}</b>
                <span className="tag low">Lv {stats.level}</span>
              </div>
              <div className="xpbar">
                <i style={{ width: `${(stats.xp_into_level / stats.xp_per_level) * 100}%` }} />
              </div>
              <div className="muted" style={{ fontSize: 12.5 }}>
                {stats.xp} XP · {stats.xp_per_level - stats.xp_into_level} XP to level {stats.level + 1}
              </div>
              <div className="badges">
                {stats.badges.map((b) => (
                  <div className={`badge${b.earned ? " on" : ""}`} key={b.id} title={b.how}>
                    <span>{b.icon}</span>
                    {b.name}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        <div style={{ display: "grid", gap: 18 }}>
          <div className="card fade">
            <h3 style={{ margin: "0 0 4px" }}>Personal details</h3>
            <p className="muted" style={{ margin: "0 0 18px", fontSize: 14 }}>
              Shown only to you inside this app.
            </p>
            {profErr && (
              <div className="err" role="alert">
                {profErr}
              </div>
            )}
            <form className="form2" onSubmit={(e) => void saveProfile(e)} noValidate>
              <div className="field">
                <label htmlFor="f_name">Full name</label>
                <input id="f_name" maxLength={60} value={name} onChange={(e) => setName(e.target.value)} required />
              </div>
              <div className="field">
                <label htmlFor="f_email">Email</label>
                <input id="f_email" value={me.email} disabled title="Email can't be changed" />
              </div>
              <div className="field">
                <label htmlFor="f_job">Job title</label>
                <input
                  id="f_job"
                  maxLength={80}
                  placeholder="e.g. Data Analyst"
                  value={jobTitle}
                  onChange={(e) => setJobTitle(e.target.value)}
                />
              </div>
              <div className="field">
                <label htmlFor="f_company">Company / college</label>
                <input
                  id="f_company"
                  maxLength={80}
                  placeholder="e.g. NPRO Technologies"
                  value={company}
                  onChange={(e) => setCompany(e.target.value)}
                />
              </div>
              <div className="field full">
                <label htmlFor="f_loc">Location</label>
                <input
                  id="f_loc"
                  maxLength={80}
                  placeholder="e.g. Bengaluru, India"
                  value={locationStr}
                  onChange={(e) => setLocationStr(e.target.value)}
                />
              </div>
              <div className="field full">
                <label htmlFor="f_bio">About me</label>
                <textarea
                  id="f_bio"
                  maxLength={300}
                  placeholder="A line or two about you…"
                  value={bio}
                  onChange={(e) => setBio(e.target.value)}
                />
                <div className="hint2">{bio.length} / 300</div>
              </div>
              <div className="full row">
                <button className="btn" type="submit">
                  💾 Save changes
                </button>
              </div>
            </form>
          </div>

          <div className="card fade">
            <h3 style={{ margin: "0 0 14px" }}>Change password</h3>
            {pwErr && (
              <div className="err" role="alert">
                {pwErr}
              </div>
            )}
            <form className="form2" onSubmit={(e) => void updatePassword(e)} noValidate>
              <div className="field full">
                <label htmlFor="pw_cur">Current password</label>
                <input
                  id="pw_cur"
                  type="password"
                  autoComplete="current-password"
                  value={pwCur}
                  onChange={(e) => setPwCur(e.target.value)}
                />
              </div>
              <div className="field">
                <label htmlFor="pw_new">New password</label>
                <input
                  id="pw_new"
                  type="password"
                  autoComplete="new-password"
                  maxLength={128}
                  value={pwNew}
                  onChange={(e) => setPwNew(e.target.value)}
                />
              </div>
              <div className="field">
                <label htmlFor="pw_new2">Confirm new password</label>
                <input
                  id="pw_new2"
                  type="password"
                  autoComplete="new-password"
                  maxLength={128}
                  value={pwNew2}
                  onChange={(e) => setPwNew2(e.target.value)}
                />
              </div>
              <div className="full">
                <button className="btn ghost" type="submit">
                  🔑 Update password
                </button>
              </div>
            </form>
          </div>

          <div className="card danger-zone fade">
            <h3 style={{ margin: "0 0 4px", color: "var(--bad)" }}>Danger zone</h3>
            <p className="muted" style={{ margin: "0 0 14px", fontSize: 14 }}>
              Deleting your account permanently removes your profile, picture, datasets, reports, goals and notes. This
              cannot be undone.
            </p>
            <button type="button" className="btn ghost danger" onClick={() => setDelOpen(true)}>
              🗑 Delete my account
            </button>
          </div>
        </div>
      </div>

      <div
        className={`modal-bg${delOpen ? " open" : ""}`}
        onClick={(e) => {
          if (e.target === e.currentTarget) {
            setDelOpen(false);
            setDelPw("");
            setDelErr("");
          }
        }}
      >
        <div className="modal" role="dialog" aria-modal="true" aria-labelledby="dmTitle">
          <h3 id="dmTitle" style={{ margin: "0 0 8px" }}>
            Delete your account?
          </h3>
          <p className="muted" style={{ margin: "0 0 16px" }}>
            Type your password to confirm. Everything will be erased.
          </p>
          {delErr && <div className="err">{delErr}</div>}
          <div className="field">
            <label htmlFor="del_pw">Password</label>
            <input
              id="del_pw"
              type="password"
              autoComplete="current-password"
              value={delPw}
              onChange={(e) => setDelPw(e.target.value)}
            />
          </div>
          <div className="row" style={{ justifyContent: "flex-end" }}>
            <button
              type="button"
              className="btn ghost"
              onClick={() => {
                setDelOpen(false);
                setDelPw("");
                setDelErr("");
              }}
            >
              Cancel
            </button>
            <button type="button" className="btn danger" onClick={() => void deleteAccount()}>
              Delete forever
            </button>
          </div>
        </div>
      </div>
    </>
  );
}
