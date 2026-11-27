#!/usr/bin/env python3
"""Build and package the static frontend for Netlify deployment."""
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend"


def setup_directories():
    for sub in ("css", "fonts", "js", "vendor", "images"):
        (FRONTEND / sub).mkdir(parents=True, exist_ok=True)


def copy_static_assets():
    # Copy fonts
    for f in (ROOT / "static" / "fonts").glob("*"):
        if f.is_file():
            shutil.copy2(f, FRONTEND / "fonts" / f.name)

    # Copy vendor
    for f in (ROOT / "static" / "vendor").glob("*"):
        if f.is_file():
            shutil.copy2(f, FRONTEND / "vendor" / f.name)

    # Copy css
    shutil.copy2(ROOT / "static" / "css" / "style.css", FRONTEND / "css" / "style.css")


def write_config_js():
    content = '''/**
 * Netlify Frontend Configuration
 *
 * When using Netlify proxy rewrites (configured in netlify.toml and _redirects),
 * API_BASE_URL should remain an empty string ("") so all /api/* calls are
 * proxied seamlessly to your backend without CORS or third-party cookie restrictions.
 *
 * If you are hosting the backend independently and calling it directly without
 * proxying, set window.API_BASE_URL to your backend URL (e.g. "https://api.example.com").
 */
window.API_BASE_URL = window.API_BASE_URL || "";
'''
    (FRONTEND / "js" / "config.js").write_text(content, encoding="utf-8")


def write_common_js():
    content = '''/* Shared helpers: secure API wrapper, formatting, toast, command palette, background, Plotly theme, and dynamic session hydration for Netlify static hosting. */
const API_BASE = (typeof window !== 'undefined' && window.API_BASE_URL) || '';
let UID = document.body.dataset.uid || '0';
let AUTHED = document.body.dataset.authed === '1';
let KEY = 'abd_dataset_' + UID;

const getDataset = () => localStorage.getItem(KEY);
const setDataset = (id, name) => { localStorage.setItem(KEY, id); localStorage.setItem(KEY + '_name', name || ''); paintBadge(); };
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const fmt = n => n == null ? 'n/a' : (n < 0 ? '-' : '') + '₹' + Math.abs(Math.round(n)).toLocaleString('en-IN');
const pctf = (n, d = 1) => n == null ? 'n/a' : (n > 0 ? '+' : '') + n.toFixed(d) + '%';
let CSRF_TOKEN = document.querySelector('meta[name="csrf-token"]')?.content || '';
const csrf = () => CSRF_TOKEN || document.querySelector('meta[name="csrf-token"]')?.content || '';

async function api(url, opts = {}) {
  const fullUrl = url.startsWith('http') ? url : (API_BASE + url);
  const init = {
    method: opts.method || 'GET',
    headers: { 'X-CSRF-Token': csrf(), ...(opts.headers || {}) },
    credentials: 'include'
  };
  if (opts.body) {
    init.body = opts.body instanceof FormData ? opts.body : JSON.stringify(opts.body);
    if (!(opts.body instanceof FormData)) init.headers['Content-Type'] = 'application/json';
  }
  const res = await fetch(fullUrl, init);
  const data = await res.json().catch(() => ({}));
  if (data && data.csrf_token) {
    CSRF_TOKEN = data.csrf_token;
    const meta = document.querySelector('meta[name="csrf-token"]');
    if (meta) meta.content = data.csrf_token;
  }
  if (res.status === 401 && data.login_required) {
    location.href = '/login?next=' + encodeURIComponent(location.pathname + location.search);
    throw new Error('Please sign in.');
  }
  if (!res.ok) {
    const err = new Error(data.error || 'Something went wrong');
    err.data = data;
    err.status = res.status;
    throw err;
  }
  return data;
}

let toastTimer;
function toast(msg, isErr = false) {
  const t = document.getElementById('toast');
  if (!t) return;
  t.textContent = msg;
  t.className = 'toast show' + (isErr ? ' err' : '');
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => t.className = 'toast', 3800);
}

function paintBadge() {
  const b = document.getElementById('dsBadge');
  if (!b) return;
  const id = AUTHED ? getDataset() : null;
  b.hidden = !AUTHED;
  b.innerHTML = id ? `Dataset: <b>${esc(localStorage.getItem(KEY + '_name') || id)}</b>` : 'No dataset';
}

const onTheme = () => {};

/* ---- user menu / logout ---- */
function setupUserMenu() {
  const userBtn = document.getElementById('userBtn'), userMenu = document.getElementById('userMenu');
  if (userBtn && userMenu) {
    userBtn.onclick = e => { e.stopPropagation(); userMenu.classList.toggle('open'); };
    document.addEventListener('click', e => { if (!userMenu.contains(e.target)) userMenu.classList.remove('open'); });
  }
  const logoutBtn = document.getElementById('logoutBtn');
  if (logoutBtn) logoutBtn.onclick = signOut;
}

async function signOut() {
  try { await api('/api/auth/logout', { method: 'POST' }); } catch (e) {}
  localStorage.removeItem(KEY);
  location.href = '/login';
}

/* ---- Session Hydration & UI Synchronization ---- */
const PROTECTED_PAGES = ['/dashboard', '/investigation', '/lab', '/data', '/reports', '/profile'];

function updateNav(user, stats) {
  const navLinks = document.getElementById('navLinks');
  const navAuthed = document.getElementById('navAuthed');
  const navAnon = document.getElementById('navAnon');
  const navRight = document.getElementById('navRight');

  const curPath = location.pathname.replace(/\\.html$/, '').replace(/\\/$/, '') || '/';

  if (user) {
    if (navLinks) {
      navLinks.style.display = 'flex';
      navLinks.querySelectorAll('a').forEach(a => {
        const targetPath = a.getAttribute('href').replace(/\\.html$/, '').replace(/\\/$/, '') || '/';
        if (targetPath === curPath || (targetPath !== '/' && curPath.startsWith(targetPath))) {
          a.classList.add('on');
        } else {
          a.classList.remove('on');
        }
      });
    }
    if (navAuthed) navAuthed.style.display = 'flex';
    if (navAnon) navAnon.style.display = 'none';
    if (navRight) navRight.style.marginLeft = '';

    const lvlNum = document.getElementById('navLvlNum');
    if (lvlNum && stats) lvlNum.textContent = stats.level;
    const lvlTitle = document.getElementById('navLvlTitle');
    if (lvlTitle && stats) lvlTitle.textContent = stats.title;

    const whoName = document.getElementById('navWhoName');
    if (whoName) whoName.textContent = user.name;
    const whoEmail = document.getElementById('navWhoEmail');
    if (whoEmail) whoEmail.textContent = user.email;

    const avatarWrap = document.getElementById('navAvatarWrap');
    if (avatarWrap) {
      if (user.has_avatar) {
        avatarWrap.innerHTML = `<img id="navAvatar" src="${API_BASE}/avatar/me?v=${user.avatar_v || Date.now()}" alt="">`;
      } else {
        const parts = (user.name || '').trim().split(/\\s+/);
        const inits = (parts.slice(0, 2).map(p => p[0]).join('') || '?').toUpperCase();
        avatarWrap.innerHTML = `<span id="navInitials">${esc(inits)}</span>`;
      }
    }
  } else {
    if (navLinks) navLinks.style.display = 'none';
    if (navAuthed) navAuthed.style.display = 'none';
    if (navAnon) navAnon.style.display = 'flex';
    if (navRight) navRight.style.marginLeft = 'auto';
  }
}

function updatePageForAuth(isAuthed) {
  const heroAuthed = document.getElementById('heroAuthed');
  const heroAnon = document.getElementById('heroAnon');
  if (heroAuthed) heroAuthed.style.display = isAuthed ? 'flex' : 'none';
  if (heroAnon) heroAnon.style.display = isAuthed ? 'none' : 'flex';

  const uploadSec = document.getElementById('upload');
  const authPrompt = document.getElementById('authPrompt');
  if (uploadSec) uploadSec.style.display = isAuthed ? 'block' : 'none';
  if (authPrompt) authPrompt.style.display = isAuthed ? 'none' : 'block';

  const ctaAuthed = document.getElementById('ctaAuthed');
  const ctaAnon = document.getElementById('ctaAnon');
  if (ctaAuthed) ctaAuthed.style.display = isAuthed ? 'block' : 'none';
  if (ctaAnon) ctaAnon.style.display = isAuthed ? 'none' : 'block';
}

async function initSession() {
  try {
    const res = await fetch((API_BASE || '') + '/api/auth/session', {
      method: 'GET',
      credentials: 'include',
      headers: { 'Accept': 'application/json' }
    });
    if (res.ok) {
      const data = await res.json();
      if (data.csrf_token) {
        CSRF_TOKEN = data.csrf_token;
        const meta = document.querySelector('meta[name="csrf-token"]');
        if (meta) meta.content = data.csrf_token;
      }
      if (data.authenticated && data.user) {
        UID = String(data.user.id);
        AUTHED = true;
        KEY = 'abd_dataset_' + UID;
        document.body.dataset.uid = UID;
        document.body.dataset.authed = '1';
        updateNav(data.user, data.stats);
        updatePageForAuth(true);
        paintBadge();

        const p = location.pathname.toLowerCase();
        if (p === '/login' || p === '/login.html' || p === '/register' || p === '/register.html') {
          const params = new URLSearchParams(location.search);
          location.href = params.get('next') || '/dashboard';
        }
        return data;
      }
    }
  } catch (err) {
    console.warn('Session check could not reach backend API:', err);
  }

  UID = '0';
  AUTHED = false;
  KEY = 'abd_dataset_0';
  document.body.dataset.uid = '0';
  document.body.dataset.authed = '0';
  updateNav(null);
  updatePageForAuth(false);
  paintBadge();

  const curPath = location.pathname.replace(/\\.html$/, '').replace(/\\/$/, '') || '/';
  if (PROTECTED_PAGES.includes(curPath)) {
    location.href = '/login?next=' + encodeURIComponent(location.pathname + location.search);
  }
  return null;
}

/* ---- reveal, count-up ---- */
function countUp(el, to, formatter = v => Math.round(v), ms = 900) {
  const t0 = performance.now();
  (function step(t) {
    const p = Math.min((t - t0) / ms, 1), e = 1 - Math.pow(1 - p, 3);
    el.textContent = formatter(to * e);
    if (p < 1) requestAnimationFrame(step);
  })(t0);
}
const io = new IntersectionObserver(es => es.forEach(e => {
  if (e.isIntersecting) { e.target.classList.add('in'); io.unobserve(e.target); }
}), { threshold: .12 });
document.querySelectorAll('.reveal').forEach(el => io.observe(el));
document.querySelectorAll('[data-count]').forEach(el => countUp(el, +el.dataset.count, v => Math.round(v), 1200));

/* ---- card spotlight that follows the pointer ---- */
document.addEventListener('pointermove', e => {
  const c = e.target.closest && e.target.closest('.card');
  if (!c) return;
  const r = c.getBoundingClientRect();
  c.style.setProperty('--mx', (e.clientX - r.left) + 'px');
  c.style.setProperty('--my', (e.clientY - r.top) + 'px');
});

/* ---- animated network background ---- */
(function () {
  const cv = document.getElementById('bgnet');
  if (!cv || matchMedia('(prefers-reduced-motion: reduce)').matches) return;
  const ctx = cv.getContext('2d');
  let W, H, dots = [], raf;
  const resize = () => {
    const r = Math.min(devicePixelRatio || 1, 1.5);
    W = cv.width = innerWidth * r;
    H = cv.height = innerHeight * r;
    ctx.setTransform(r, 0, 0, r, 0, 0);
    dots = Array.from({ length: Math.round(Math.min(70, innerWidth / 22)) }, () => ({
      x: Math.random() * innerWidth, y: Math.random() * innerHeight,
      vx: (Math.random() - .5) * .25, vy: (Math.random() - .5) * .25
    }));
  };
  function frame() {
    ctx.clearRect(0, 0, innerWidth, innerHeight);
    const c1 = getComputedStyle(document.documentElement).getPropertyValue('--a1').trim() || '#c9cdd3';
    ctx.fillStyle = c1;
    ctx.strokeStyle = c1;
    for (const d of dots) {
      d.x += d.vx; d.y += d.vy;
      if (d.x < 0 || d.x > innerWidth) d.vx *= -1;
      if (d.y < 0 || d.y > innerHeight) d.vy *= -1;
      ctx.globalAlpha = .55;
      ctx.beginPath();
      ctx.arc(d.x, d.y, 1.4, 0, 6.3);
      ctx.fill();
    }
    for (let i = 0; i < dots.length; i++) {
      for (let j = i + 1; j < dots.length; j++) {
        const dx = dots[i].x - dots[j].x, dy = dots[i].y - dots[j].y, dist = dx * dx + dy * dy;
        if (dist < 14000) {
          ctx.globalAlpha = (1 - dist / 14000) * .22;
          ctx.beginPath();
          ctx.moveTo(dots[i].x, dots[i].y);
          ctx.lineTo(dots[j].x, dots[j].y);
          ctx.stroke();
        }
      }
    }
    raf = requestAnimationFrame(frame);
  }
  resize();
  frame();
  addEventListener('resize', resize);
  document.addEventListener('visibilitychange', () => document.hidden ? cancelAnimationFrame(raf) : frame());
})();

/* ---- command palette (Ctrl/Cmd + K) ---- */
function setupCommandPalette() {
  const go = u => () => location.href = u;
  const getActions = () => AUTHED ? [
    ['🏠', 'Home', go('/')],
    ['📊', 'Dashboard', go('/dashboard')],
    ['🔍', 'Investigate', go('/investigation')],
    ['🧪', 'What-if lab', go('/lab')],
    ['🗂️', 'Data explorer', go('/data')],
    ['📄', 'Reports', go('/reports')],
    ['👤', 'My profile', go('/profile')],
    ['🔎', 'Load the demo case', async () => {
      try {
        const r = await api('/api/sample', { method: 'POST', body: { kind: 'clean' } });
        setDataset(r.dataset.id, r.dataset.filename);
        location.href = '/dashboard';
      } catch (e) {
        toast(e.message, true);
      }
    }],
    ['🚪', 'Sign out', signOut]
  ] : [
    ['🔑', 'Sign in', go('/login')],
    ['✨', 'Create account', go('/register')]
  ];

  const bg = document.createElement('div');
  bg.className = 'pal-bg';
  bg.innerHTML = '<div class="pal" role="dialog" aria-label="Quick actions"><input placeholder="Type a command… (try: dashboard, lab, profile)" aria-label="Search actions"><ul></ul></div>';
  document.body.appendChild(bg);
  const input = bg.querySelector('input'), ul = bg.querySelector('ul');
  let shown = [], sel = 0;

  function draw() {
    const q = input.value.toLowerCase().trim();
    const actions = getActions();
    shown = actions.filter(a => a[1].toLowerCase().includes(q));
    sel = Math.min(sel, Math.max(shown.length - 1, 0));
    ul.innerHTML = shown.length
      ? shown.map((a, i) => `<li class="${i === sel ? 'sel' : ''}" data-i="${i}"><span>${a[0]}</span>${esc(a[1])}</li>`).join('')
      : '<div class="empty-r">No matching action</div>';
  }

  const open = () => { bg.classList.add('open'); input.value = ''; sel = 0; draw(); setTimeout(() => input.focus(), 30); };
  const close = () => bg.classList.remove('open');
  const run = i => { const a = shown[i]; if (a) { close(); a[2](); } };

  const palBtn = document.getElementById('palBtn');
  if (palBtn) palBtn.onclick = open;

  addEventListener('keydown', e => {
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
      e.preventDefault();
      bg.classList.contains('open') ? close() : open();
    } else if (bg.classList.contains('open')) {
      if (e.key === 'Escape') close();
      else if (e.key === 'ArrowDown') { sel = Math.min(sel + 1, shown.length - 1); draw(); e.preventDefault(); }
      else if (e.key === 'ArrowUp') { sel = Math.max(sel - 1, 0); draw(); e.preventDefault(); }
      else if (e.key === 'Enter') run(sel);
    }
  });

  input.oninput = () => { sel = 0; draw(); };
  bg.onclick = e => { if (e.target === bg) close(); };
  ul.onclick = e => { const li = e.target.closest('li'); if (li) run(+li.dataset.i); };
}

/* ---- Plotly palette theme helper ---- */
const css = v => getComputedStyle(document.documentElement).getPropertyValue(v).trim();
const COLORS = {
  obsidian: '#050507', obsidian2: '#0c0c11',
  silver: '#c9cdd3', silverHi: '#f2f4f7', silverLo: '#8a9098', dim: '#4d525a',
  crimson: '#ff1a40', crimsonHi: '#ff4d6d', crimsonLo: '#a10020',
  cyan: '#c9cdd3', violet: '#ff1a40', pink: '#ff4d6d', good: '#f2f4f7', bad: '#ff1a40', amber: '#8a9098'
};
function plotLayout(extra = {}) {
  const grid = css('--line'), ink = css('--ink');
  return Object.assign({
    paper_bgcolor: 'rgba(0,0,0,0)',
    plot_bgcolor: 'rgba(0,0,0,0)',
    font: { color: ink, family: 'Inter, system-ui, sans-serif', size: 12 },
    margin: { t: 14, r: 16, b: 40, l: 62 },
    xaxis: { gridcolor: grid, zerolinecolor: grid },
    yaxis: { gridcolor: grid, zerolinecolor: grid },
    legend: { orientation: 'h', y: 1.16 },
    hoverlabel: { bgcolor: css('--bg2'), font: { color: ink } }
  }, extra);
}
const plot = (id, data, layout = {}) => {
  const el = document.getElementById(id);
  if (!el || typeof Plotly === 'undefined') return;
  return Plotly.react(el, data, plotLayout(layout), { displayModeBar: false, responsive: true });
};

/* ---- keep emoji monochrome (U+FE0E asks for the flat text glyph) ---- */
(function () {
  const HAS = /\\p{Extended_Pictographic}/u, FIX = /(\\p{Extended_Pictographic})(?:\\uFE0F|(?!\\uFE0E))/gu, skip = new Set(['SCRIPT', 'STYLE', 'TEXTAREA', 'INPUT']);
  function mono(root) {
    const w = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
    for (let n = w.nextNode(); n; n = w.nextNode()) {
      if (skip.has(n.parentNode.nodeName) || !HAS.test(n.nodeValue)) continue;
      const v = n.nodeValue.replace(FIX, '$1\\uFE0E');
      if (v !== n.nodeValue) n.nodeValue = v;
    }
  }
  let pending = false;
  new MutationObserver(() => {
    if (pending) return;
    pending = true;
    requestAnimationFrame(() => { pending = false; mono(document.body); });
  }).observe(document.body, { childList: true, subtree: true });
  mono(document.body);
})();

// Initial hydration on page load; page scripts await window.sessionReady before reading per-user state
setupUserMenu();
setupCommandPalette();
window.sessionReady = initSession();
'''
    (FRONTEND / "js" / "common.js").write_text(content, encoding="utf-8")


def copy_and_adapt_scripts():
    # 1. auth.js
    auth_src = (ROOT / "static" / "js" / "auth.js").read_text(encoding="utf-8")
    auth_adapted = auth_src.replace(
        "const mode = form.dataset.mode, pw = document.getElementById('password');",
        "const mode = form.dataset.mode || (location.pathname.includes('register') ? 'register' : 'login'), pw = document.getElementById('password');"
    )
    auth_adapted = "const nextParam = new URLSearchParams(location.search).get('next');\nif (document.getElementById('authForm') && nextParam) document.getElementById('authForm').dataset.next = nextParam;\n" + auth_adapted
    (FRONTEND / "js" / "auth.js").write_text(auth_adapted, encoding="utf-8")

    # 2. upload.js
    up_src = (ROOT / "static" / "js" / "upload.js").read_text(encoding="utf-8")
    up_adapted = up_src.replace(
        "document.getElementById('btnSample').onclick = () => sample('clean');",
        "const btnSample = document.getElementById('btnSample'); if (btnSample) btnSample.onclick = () => sample('clean');"
    ).replace(
        "document.getElementById('btnDirty').onclick = () => sample('dirty');",
        "const btnDirty = document.getElementById('btnDirty'); if (btnDirty) btnDirty.onclick = () => sample('dirty');"
    ).replace(
        "drop.onclick = () => fileInput.click();",
        "if (drop && fileInput) { drop.onclick = () => fileInput.click();"
    ).replace(
        "drop.addEventListener('drop', e => e.dataTransfer.files[0] && upload(e.dataTransfer.files[0]));",
        "drop.addEventListener('drop', e => e.dataTransfer.files[0] && upload(e.dataTransfer.files[0])); }"
    )
    (FRONTEND / "js" / "upload.js").write_text(up_adapted, encoding="utf-8")

    # 3. profile.js
    prof_src = (ROOT / "static" / "js" / "profile.js").read_text(encoding="utf-8")
    prof_adapted = prof_src.replace(
        'src="/avatar/me?v=${u.avatar_v}"',
        'src="${(window.API_BASE_URL || \'\')}/avatar/me?v=${u.avatar_v}"'
    ).replace(
        "load().catch(e => toast(e.message, true));",
        "(window.sessionReady || Promise.resolve()).then(s => s && load()).catch(e => toast(e.message, true));"
    )
    (FRONTEND / "js" / "profile.js").write_text(prof_adapted, encoding="utf-8")

    # 4. dashboard.js
    dash_src = (ROOT / "static" / "js" / "dashboard.js").read_text(encoding="utf-8")
    dash_adapted = dash_src.replace(
        "(async () => {\n  const id = getDataset();",
        "(async () => {\n  const sess = await (window.sessionReady || Promise.resolve());\n  if (!sess) return;\n  const id = getDataset();"
    ).replace(
        "document.getElementById('expCsv').href = `/api/export/${id}/clean.csv`;",
        "document.getElementById('expCsv').href = (window.API_BASE_URL || '') + `/api/export/${id}/clean.csv`;"
    )
    (FRONTEND / "js" / "dashboard.js").write_text(dash_adapted, encoding="utf-8")

    # 5. data.js
    data_src = (ROOT / "static" / "js" / "data.js").read_text(encoding="utf-8")
    data_adapted = data_src.replace(
        "(async () => {\n  const id = getDataset();",
        "(async () => {\n  const sess = await (window.sessionReady || Promise.resolve());\n  if (!sess) return;\n  const id = getDataset();"
    ).replace(
        "document.getElementById('expCsv').href = `/api/export/${id}/clean.csv`;",
        "document.getElementById('expCsv').href = (window.API_BASE_URL || '') + `/api/export/${id}/clean.csv`;"
    )
    (FRONTEND / "js" / "data.js").write_text(data_adapted, encoding="utf-8")

    # 6. investigation.js
    inv_src = (ROOT / "static" / "js" / "investigation.js").read_text(encoding="utf-8")
    inv_adapted = inv_src.replace(
        "const id = getDataset(), res = document.getElementById('result'), qInput = document.getElementById('q'), go = document.getElementById('go');\nconst selPrev = document.getElementById('selPrev'), selCurr = document.getElementById('selCurr');\nif (!id) document.getElementById('empty').hidden = false; else document.getElementById('content').hidden = false;",
        "let id = null;\nconst res = document.getElementById('result'), qInput = document.getElementById('q'), go = document.getElementById('go');\nconst selPrev = document.getElementById('selPrev'), selCurr = document.getElementById('selCurr');"
    ).replace(
        'href="/api/export/${id}/contributors.csv',
        'href="${(window.API_BASE_URL || \'\')}/api/export/${id}/contributors.csv'
    ).replace(
        "window.open(r.url, '_blank');",
        "window.open((window.API_BASE_URL || '') + r.url, '_blank');"
    ).replace(
        "if (id) init().then(run).catch(e => toast(e.message, true));",
        "(window.sessionReady || Promise.resolve()).then(s => {\n  if (!s) return;\n  id = getDataset();\n  if (!id) { document.getElementById('empty').hidden = false; return; }\n  document.getElementById('content').hidden = false;\n  return init().then(run);\n}).catch(e => toast(e.message, true));"
    )
    (FRONTEND / "js" / "investigation.js").write_text(inv_adapted, encoding="utf-8")

    # 7. lab.js
    lab_src = (ROOT / "static" / "js" / "lab.js").read_text(encoding="utf-8")
    lab_adapted = lab_src.replace(
        "const $ = id => document.getElementById(id), DS = getDataset();\nif (!DS) $('empty').hidden = false; else { $('content').hidden = false; init(); }",
        "const $ = id => document.getElementById(id);\nlet DS = null;\n(window.sessionReady || Promise.resolve()).then(s => {\n  if (!s) return;\n  DS = getDataset();\n  if (!DS) $('empty').hidden = false; else { $('content').hidden = false; init(); }\n});"
    )
    (FRONTEND / "js" / "lab.js").write_text(lab_adapted, encoding="utf-8")


def generate_html_files():
    def make_shell(title, content, head_extra="", body_extra="", page=""):
        return f'''<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
  <title>{title}</title>
  <meta name="description" content="Upload sales data and find out which products and regions drove a change, with evidence-based explanations.">
  <meta name="csrf-token" content="">
  <meta name="theme-color" content="#050507">
  <link rel="icon" href="data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 64 64%22><rect width=%2264%22 height=%2264%22 rx=%2214%22 fill=%22%23050507%22/><circle cx=%2227%22 cy=%2727%22 r=%2216%22 fill=%22none%22 stroke=%22%23c9cdd3%22 stroke-width=%226%22/><path d=%22M40 40l16 16%22 stroke=%22%23ff1a40%22 stroke-width=%227%22 stroke-linecap=%22round%22/></svg>">
  <link rel="preload" href="/fonts/inter-latin-wght-normal.woff2" as="font" type="font/woff2" crossorigin>
  <link rel="preload" href="/fonts/space-grotesk-latin-wght-normal.woff2" as="font" type="font/woff2" crossorigin>
  <link rel="stylesheet" href="/css/style.css">
  {head_extra}
</head>
<body data-uid="0" data-authed="0" data-page="{page}">
  <canvas id="bgnet" aria-hidden="true"></canvas>
  <nav class="nav"><div class="wrap">
    <a class="brand" href="/" aria-label="AI Business Detective home">
      <svg viewBox="0 0 64 64" width="32" height="32"><defs><linearGradient id="lg" x1="0" x2="1"><stop offset="0" stop-color="var(--a1)"/><stop offset=".6" stop-color="var(--a2)"/><stop offset="1" stop-color="var(--a3)"/></linearGradient></defs>
        <circle cx="27" cy="27" r="17" fill="none" stroke="url(#lg)" stroke-width="6"/><path d="M40 40l16 16" stroke="url(#lg)" stroke-width="7" stroke-linecap="round"/>
        <path d="M18 31l6-6 5 4 7-8" fill="none" stroke="currentColor" stroke-width="3.2" stroke-linecap="round" stroke-linejoin="round"/></svg>
      <span>AI Business <b class="grad">Detective</b></span></a>
    
    <div class="links" id="navLinks" style="display:none">
      <a href="/" class="nav-home">Home</a>
      <a href="/dashboard" class="nav-dashboard">Dashboard</a>
      <a href="/investigation" class="nav-investigation">Investigate</a>
      <a href="/lab" class="nav-lab">Lab</a>
      <a href="/data" class="nav-data">Data</a>
      <a href="/reports" class="nav-reports">Reports</a>
    </div>

    <div class="badge-ds" id="dsBadge" hidden>No dataset</div>

    <div class="nav-right" id="navRight">
      <button class="nav-search" id="palBtn" aria-label="Open command menu">⌘ <span>Quick actions</span> <span class="kbd">Ctrl K</span></button>

      <div id="navAuthed" style="display:none;align-items:center;gap:12px">
        <a class="lvl" id="navLvl" href="/profile" title="Your detective rank">Lv <b id="navLvlNum">1</b> · <span id="navLvlTitle">Rookie</span></a>
        <div class="usermenu">
          <button id="userBtn" aria-label="Account menu" aria-haspopup="true">
            <span class="avatar" id="navAvatarWrap"><span id="navInitials">?</span></span></button>
          <div class="menu" id="userMenu" role="menu">
            <div class="who"><b id="navWhoName">User</b><span id="navWhoEmail">user@example.com</span></div>
            <a href="/profile">👤 My profile</a><a href="/lab">🧪 What-if lab</a><a href="/reports">📄 My reports</a>
            <button id="logoutBtn">🚪 Sign out</button>
          </div>
        </div>
      </div>

      <div id="navAnon" style="display:flex;align-items:center;gap:8px">
        <a class="btn ghost sm" href="/login">Sign in</a><a class="btn sm" href="/register">Get started</a>
      </div>
    </div>
  </div></nav>
  <main class="wrap">{content}</main>
  <footer class="wrap">Turning business data into actionable insights.<br>Contributors show <b>where</b> a change happened — not proof of <b>why</b>. Sample data is illustrative only.</footer>
  <div class="toast" id="toast" role="status"></div>
  <script src="/js/config.js"></script>
  <script src="/js/common.js"></script>
  {body_extra}
</body>
</html>'''

    # 1. index.html
    index_content = '''<section class="hero"><div class="laser-beam" aria-hidden="true"></div>
  <div class="fade">
    <span class="eyebrow"><i></i> Evidence first · no guessed causes</span>
    <h1>Your sales dipped.<br><span class="grad">Now find out</span> <span class="hot">why.</span></h1>
    <p class="lead">AI Business Detective cleans your sales file, spots unusual changes, and shows exactly which products and regions moved the numbers — then explains it in plain English, using only what the data supports.</p>
    <div class="row" style="margin-top:26px" id="heroActions">
      <div id="heroAuthed" style="display:none;gap:10px" class="row">
        <button class="btn" id="btnSample">🔎 Open the demo case</button>
        <button class="btn ghost" id="btnDirty">🧹 See it fix messy data</button>
      </div>
      <div id="heroAnon" style="display:flex;gap:10px" class="row">
        <a class="btn" href="/register">🔴 Create your free account</a>
        <a class="btn ghost" href="/login">Sign in</a>
      </div>
    </div>
    <div class="stats">
      <div class="card"><b data-count="10">0</b><span>analysis tools</span></div>
      <div class="card"><b data-count="48">0</b><span>automated tests</span></div>
      <div class="card"><b>0 ₹</b><span>to run locally</span></div>
    </div>
  </div>
  <div class="fade" style="animation-delay:.15s">
    <div class="card glow hero-card">
      <div class="between"><b>Profit · Sep → Oct</b><span class="tag high">−22.7%</span></div>
      <div class="mini-kpis" style="margin-top:12px">
        <div class="mini"><small>Biggest contributor</small><b>Laptop · South</b></div><div class="mini"><small>Orders in segment</small><b class="down">−72%</b></div>
        <div class="mini"><small>Avg discount</small><b class="down">+11.7 pts</b></div><div class="mini"><small>Unusual days</small><b>3 flagged</b></div>
      </div>
      <svg class="spark" viewBox="0 0 400 90" preserveAspectRatio="none"><defs><linearGradient id="sg" x1="0" x2="1"><stop offset="0" stop-color="#c9cdd3"/><stop offset="1" stop-color="#ff1a40"/></linearGradient></defs>
        <path d="M0 60 C40 55 60 30 100 38 S160 62 200 42 S270 14 310 52 S370 70 400 78" fill="none" stroke="url(#sg)" stroke-width="4" stroke-linecap="round"/></svg>
      <span class="float-chip c1">🚨 Spike on 21 Sep</span><span class="float-chip c2">✅ Evidence-based</span>
    </div>
  </div>
</section>

<section class="card" style="margin-top:34px;display:none" id="upload">
  <div class="between"><div><h3 style="margin:0;font-size:20px">Start with your own data</h3><span class="muted">Up to 50 MB · everything stays secure</span></div></div>
  <div class="row" style="margin-top:12px" id="fmtChips"><span class="chip">📗 Excel .xlsx .xlsm .xls</span><span class="chip">📄 CSV / TSV / TXT</span><span class="chip">📕 PDF tables</span><span class="chip">📊 Power BI .pbix</span><span class="chip">🧾 JSON</span><span class="chip">📘 OpenDocument .ods</span></div>
  <div class="drop" id="drop" style="margin-top:16px">
    <div class="ico">📂</div><b>Drop a file here, or click to browse</b><div class="muted" style="font-size:13px;margin-top:2px">Excel · CSV · PDF · Power BI · JSON · ODS</div>
    <p class="muted" style="margin:8px 0 0">Columns: <code>order_date</code> <code>product</code> <code>category</code> <code>region</code> <code>quantity</code> <code>sales</code> <code>profit</code> <span class="muted">(optional <code>discount_pct</code>)</span></p>
    <input type="file" id="file" accept=".csv,.tsv,.txt,.xlsx,.xlsm,.xls,.ods,.json,.pdf,.pbix" hidden>
  </div>
  <div id="uploadMsg" style="margin-top:16px"></div>
</section>

<section class="card glow" style="margin-top:34px;text-align:center;padding:38px 24px" id="authPrompt">
  <h3 style="margin:0 0 6px;font-size:22px">Sign in to start investigating</h3>
  <p class="muted" style="margin:0 0 18px">Your datasets, reports, notes and goals are private to your account.</p>
  <div class="row" style="justify-content:center"><a class="btn" href="/register">Create account</a><a class="btn ghost" href="/login">Sign in</a></div>
</section>

<h2 class="sec reveal">Everything an analyst does by hand — <span class="grad">automated</span></h2>
<p class="sec-sub reveal">From a raw spreadsheet to a defensible explanation in a few clicks.</p>
<div class="bento">
  <div class="card feat hover reveal b2"><div class="ico">🧹</div><h3>Reads almost any file</h3><p>Excel (even with title rows and many sheets), CSV, PDF tables, Power BI and JSON. Then cleans it without guessing — every fix is listed.</p></div>
  <div class="card feat hover reveal b4"><div class="ico">🔍</div><h3>Finds who moved the number</h3><p>Ranks contributors by product, region, category and product × region, then looks inside the biggest one: did orders fall, did prices drop, did discounts or margins change?</p></div>
  <div class="card feat hover reveal b3"><div class="ico">🎛️</div><h3>Interactive dashboard</h3><p>Filter by region, category, product and dates. Heatmaps, trends, margin-by-discount and a simple next-month projection.</p></div>
  <div class="card feat hover reveal b3"><div class="ico">🚨</div><h3>Unusual-day detection</h3><p>Robust statistics plus Isolation Forest flag spikes and dips — described as "unusual", never as "wrong".</p></div>
  <div class="card feat hover reveal b2"><div class="ico">💬</div><h3>Ask in plain English</h3><p>"Why did profit drop?" gets an answer built only from calculated figures.</p></div>
  <div class="card feat hover reveal b2"><div class="ico">🗂️</div><h3>Data explorer</h3><p>Search, sort and page through your cleaned data. Export it as CSV.</p></div>
  <div class="card feat hover reveal b2"><div class="ico">📄</div><h3>Shareable reports</h3><p>One-click HTML report you can print to PDF, plus contributor tables as CSV.</p></div>

  <div class="card feat hover reveal b3"><div class="ico">🧪</div><h3>What-if lab</h3><p>Nudge orders, price or margin for one product-region segment and see the profit impact instantly — an illustration, never a forecast.</p></div>
  <div class="card feat hover reveal b3"><div class="ico">❤</div><h3>Business health score</h3><p>A 0–100 score from growth, profitability, stability and data quality. The formula is shown, so you can argue with it.</p></div>
  <div class="card feat hover reveal b2"><div class="ico">🎯</div><h3>Goals &amp; case notes</h3><p>Set a monthly target, see the daily pace you need, and keep notes against each dataset.</p></div>
  <div class="card feat hover reveal b2"><div class="ico">🔐</div><h3>Private accounts</h3><p>Sign-in, profile photo and your own space. Datasets are tied to you — nobody else can open them.</p></div>
  <div class="card feat hover reveal b2"><div class="ico">🏅</div><h3>Detective ranks</h3><p>Earn XP and badges as you upload, investigate and report. Press <span class="kbd">Ctrl K</span> for quick actions.</p></div>
</div>

<h2 class="sec reveal">How it works</h2>
<div class="grid g4 steps" style="margin-top:26px">
  <div class="card reveal"><b>Upload</b><p class="muted" style="margin:6px 0 0">Excel, CSV, PDF, Power BI or JSON.</p></div>
  <div class="card reveal"><b>Clean</b><p class="muted" style="margin:6px 0 0">Every fix is documented and counted.</p></div>
  <div class="card reveal"><b>Investigate</b><p class="muted" style="margin:6px 0 0">Pandas calculates contributors and drivers.</p></div>
  <div class="card reveal"><b>Explain</b><p class="muted" style="margin:6px 0 0">Plain-English findings, charts and a report.</p></div>
</div>

<h2 class="sec reveal">Good questions</h2>
<div style="margin-top:20px;max-width:820px" class="reveal">
  <details class="faq"><summary>Does the AI make up causes?</summary><p>No. Python and pandas do every calculation. The explanation only describes those numbers, and it states that a contributor shows <i>where</i> a change happened, not proof of <i>why</i>.</p></details>
  <details class="faq"><summary>Which file types work, and what are the limits?</summary><p>Excel, CSV/TSV, JSON and OpenDocument work best. PDFs must contain real text tables — scanned images cannot be read. Power BI .pbix files work when the data is imported into the file; live-connection or DirectQuery reports hold no data, so export a table to CSV/Excel instead.</p></details>
  <details class="faq"><summary>Is my data uploaded anywhere?</summary><p>Data is processed through your connected API service and saved in your private account workspace. An optional LLM key sends only calculated summary figures — never raw rows.</p></details>
  <details class="faq"><summary>What if my latest month is incomplete?</summary><p>The app detects partial months and warns you, so a half-finished month isn't mistaken for a real decline.</p></details>
  <details class="faq"><summary>What does the forecast mean?</summary><p>It extends the monthly trend in a straight line. It is a rough guide, not a prediction, and is labelled that way.</p></details>
</div>

<section class="card glow cta reveal"><h2>Ready to <span class="grad">crack the case</span>?</h2><p class="muted">Open the demo and watch it find a planted decline.</p>
  <div id="ctaAuthed" style="display:none"><button class="btn" onclick="document.getElementById('btnSample').click()">🔎 Open the demo case</button></div>
  <div id="ctaAnon"><a class="btn" href="/register">Create your free account</a></div>
</section>'''
    (FRONTEND / "index.html").write_text(
        make_shell("AI Business Detective — find what moved your numbers", index_content, body_extra='<script src="/js/upload.js"></script>', page="home"),
        encoding="utf-8"
    )

    # 2. dashboard.html
    dash_content = '''<div class="page-head between"><div><h2>Performance <span class="grad">dashboard</span></h2><p id="sub">Loading…</p></div>
  <div class="row"><a class="btn ghost sm" id="expCsv" href="#">⬇ Export cleaned CSV</a><a class="btn sm" href="/investigation">🔍 Investigate changes</a></div></div>
<div id="empty" class="card empty" hidden><div class="ico">🕵️</div><h3>No dataset loaded</h3><p class="muted">Upload a file or open the demo case to see your dashboard.</p><a class="btn" href="/">Go to upload</a></div>
<div id="content" hidden>
  <div class="card filters" id="filters">
    <label>Region<select id="fRegion"><option>All</option></select></label>
    <label>Category<select id="fCategory"><option>All</option></select></label>
    <label>Product<select id="fProduct"><option>All</option></select></label>
    <label>From<input type="date" id="fStart"></label><label>To<input type="date" id="fEnd"></label>
    <button class="btn ghost sm" id="fReset">↺ Reset</button><span class="muted" id="fCount" style="margin-left:auto;font-size:13px"></span>
  </div>
  <div class="pulse" id="pulse"></div>
  <div class="card glow" id="healthCard" style="margin-top:18px"><div class="between"><h4 style="margin:0;font-size:16px;font-family:var(--display)">Business health score</h4><span class="muted" style="font-size:12.5px">Transparent formula · not an industry standard</span></div>
    <div class="gauge" id="healthBody" style="margin-top:14px"></div></div>
  <div class="grid g4" id="kpis" style="margin-top:18px"></div>
  <div class="grid g2" style="margin-top:18px">
    <div class="card chart"><h4>Monthly sales, profit & margin</h4><div class="hint">Bars: totals · line: profit margin %</div><div id="cMonthly"></div></div>
    <div class="card chart"><h4>Daily sales trend</h4><div class="hint">Faint area is each day; bright line is the 7-day average.</div><div id="cDaily"></div></div>
    <div class="card chart"><div class="between"><h4>Product performance</h4><div class="seg" data-target="products"><button data-m="profit" class="on">Profit</button><button data-m="sales">Sales</button></div></div><div id="cProducts"></div></div>
    <div class="card chart"><div class="between"><h4>Regional performance</h4><div class="seg" data-target="regions"><button data-m="profit" class="on">Profit</button><button data-m="sales">Sales</button></div></div><div id="cRegions"></div></div>
    <div class="card chart"><h4>Profit by region × product</h4><div class="hint">Darker cells earn more profit. Spot weak combinations fast.</div><div id="cHeat"></div></div>
    <div class="card chart"><h4>Category share of profit</h4><div class="hint">Hover a slice for exact figures.</div><div id="cCat"></div></div>
    <div class="card chart" id="discCard"><h4>Margin by discount level</h4><div class="hint">Do bigger discounts leave less profit per rupee sold?</div><div id="cDisc"></div></div>
    <div class="card chart" id="fcCard"><h4>Next-month trend projection</h4><div class="hint">A straight-line extension of past months.</div><div id="fcBody"></div></div>
  </div>
  <div class="card" style="margin-top:18px" id="quality"></div>
</div>'''
    (FRONTEND / "dashboard.html").write_text(
        make_shell(
            "Dashboard · AI Business Detective",
            dash_content,
            head_extra='<script src="/vendor/plotly.min.js" charset="utf-8"></script>',
            body_extra='<script src="/js/dashboard.js"></script>',
            page="dashboard"
        ),
        encoding="utf-8"
    )

    # 3. investigation.html
    inv_content = '''<div class="page-head"><h2>Case <span class="grad">investigation</span></h2><p>Ask a question or pick two months. Code calculates the numbers; the explanation only describes them.</p></div>
<div id="empty" class="card empty" hidden><div class="ico">🕵️</div><h3>No dataset loaded</h3><p class="muted">Load a dataset first.</p><a class="btn" href="/">Go to upload</a></div>
<div id="content" hidden>
  <div class="card glow">
    <div class="ask"><input id="q" value="Why did profit decrease this month?" maxlength="300" aria-label="Your question"><button class="btn" id="go">Investigate</button></div>
    <div class="row" id="chips">
      <button class="chip">Why did profit decrease this month?</button><button class="chip">Why did sales change?</button>
      <button class="chip">Which region caused the change?</button><button class="chip">Which product is performing poorly?</button>
    </div>
    <div class="row" style="margin-top:16px;padding-top:16px;border-top:1px solid var(--line)">
      <label class="muted" style="font-size:12px;font-weight:700">COMPARE <select id="selPrev" style="margin:0 6px"></select> → <select id="selCurr" style="margin-left:6px"></select></label>
      <div class="seg" id="metricSeg"><button data-m="auto" class="on">Auto</button><button data-m="profit">Profit</button><button data-m="sales">Sales</button></div>
    </div>
  </div>
  <div id="result" style="margin-top:18px"></div>
</div>'''
    (FRONTEND / "investigation.html").write_text(
        make_shell(
            "Investigation · AI Business Detective",
            inv_content,
            head_extra='<script src="/vendor/plotly.min.js" charset="utf-8"></script>',
            body_extra='<script src="/js/investigation.js"></script>',
            page="investigation"
        ),
        encoding="utf-8"
    )

    # 4. lab.html
    lab_content = '''<div class="page-head"><h2>The <span class="grad">Lab</span></h2><p>Test "what if?" scenarios, track monthly goals and keep case notes — all private to you.</p></div>
<div id="empty" class="card empty" hidden><div class="ico">🧪</div><h3>No dataset loaded</h3><p class="muted">Load a dataset first, then come back to experiment.</p><a class="btn" href="/">Go to upload</a></div>
<div class="lab" id="content" hidden>
  <div class="card glow fade">
    <div class="between"><h3 style="margin:0">What-if simulator</h3><span class="tag medium" id="simMonth"></span></div>
    <p class="muted" style="margin:6px 0 0;font-size:14px">Pick one product-region segment and nudge orders, price or margin to see the profit impact.</p>
    <div class="field" style="margin-top:16px"><label for="segSel">Segment</label><select id="segSel"></select></div>
    <div class="slider-row"><div class="top"><span>Orders</span><output id="oOrd">0%</output></div><input type="range" id="sOrd" min="-80" max="100" step="1" value="0" aria-label="Change in orders, percent"></div>
    <div class="slider-row"><div class="top"><span>Average price per order</span><output id="oPrice">0%</output></div><input type="range" id="sPrice" min="-30" max="30" step="1" value="0" aria-label="Change in price, percent"></div>
    <div class="slider-row"><div class="top"><span>Profit margin</span><output id="oMar">0 pts</output></div><input type="range" id="sMar" min="-15" max="15" step="0.5" value="0" aria-label="Change in margin, percentage points"></div>
    <div class="row" style="margin-bottom:6px"><button class="btn ghost sm" id="restoreBtn">↺ Match last month's orders</button><button class="btn ghost sm" id="resetBtn">Reset sliders</button></div>
    <div class="result" id="simOut"></div>
    <div id="cSim" style="margin-top:8px"></div>
    <div class="note">Illustration, not a forecast: it assumes the segment's average order value and margin stay the same unless you change them, and that nothing else moves.</div>
  </div>

  <div style="display:grid;gap:18px">
    <div class="card fade"><h3 style="margin:0 0 4px">Monthly goals</h3><p class="muted" style="margin:0 0 14px;font-size:14px" id="goalSub">Set a target for the latest month.</p>
      <div id="goalList"></div>
      <div class="row" style="margin-top:14px;align-items:flex-end">
        <div class="field" style="margin:0;flex:0 0 120px"><label for="gMetric">Metric</label><select id="gMetric"><option value="profit">Profit</option><option value="sales">Sales</option></select></div>
        <div class="field" style="margin:0;flex:1;min-width:120px"><label for="gAmount">Target (₹)</label><input id="gAmount" type="number" min="1" step="1000" placeholder="e.g. 500000"></div>
        <button class="btn sm" id="gSave">Set goal</button></div>
      <div id="goalErr" class="err" hidden style="margin-top:12px"></div>
    </div>
    <div class="card fade"><h3 style="margin:0 0 4px">Case notes</h3><p class="muted" style="margin:0 0 12px;font-size:14px">Jot down hunches and follow-ups for this dataset.</p>
      <div class="field" style="margin:0"><textarea id="noteText" maxlength="500" placeholder="e.g. Ask the South team about the laptop discount campaign…" style="min-height:76px"></textarea><div class="hint2" id="noteCount">0 / 500</div></div>
      <div class="row" style="margin-top:8px"><button class="btn sm" id="noteAdd">＋ Add note</button></div>
      <ul class="notes" id="noteList"></ul></div>
  </div>
</div>'''
    (FRONTEND / "lab.html").write_text(
        make_shell(
            "Lab · AI Business Detective",
            lab_content,
            head_extra='<script src="/vendor/plotly.min.js" charset="utf-8"></script>',
            body_extra='<script src="/js/lab.js"></script>',
            page="lab"
        ),
        encoding="utf-8"
    )

    # 5. data.html
    data_content = '''<div class="page-head between"><div><h2>Data <span class="grad">explorer</span></h2><p id="sub">Browse the cleaned data the analysis is built on.</p></div>
  <a class="btn ghost sm" id="expCsv" href="#">⬇ Export cleaned CSV</a></div>
<div id="empty" class="card empty" hidden><div class="ico">🗂️</div><h3>No dataset loaded</h3><a class="btn" href="/">Go to upload</a></div>
<div id="content" hidden>
  <div class="card" style="margin-top:16px">
    <div class="between" style="margin-bottom:14px"><input type="text" id="search" placeholder="🔎 Search product, category or region…" style="min-width:300px"><span class="muted" id="total"></span></div>
    <div class="tablewrap"><table class="t" id="tbl"></table></div>
    <div class="pager"><button class="btn ghost sm" id="prev">← Prev</button><span id="pg"></span><button class="btn ghost sm" id="next">Next →</button></div>
  </div>
</div>'''
    (FRONTEND / "data.html").write_text(
        make_shell("Data explorer · AI Business Detective", data_content, body_extra='<script src="/js/data.js"></script>', page="data"),
        encoding="utf-8"
    )

    # 6. reports.html
    rep_content = '''<div class="page-head"><h2>Automated <span class="grad">reports</span></h2><p>Generate a shareable investigation report. Open it, then use your browser's Print → Save as PDF if you need a PDF.</p></div>
<div class="card" style="margin-top:18px"><table class="t" id="tbl"><tr><td>Loading…</td></tr></table></div>'''
    rep_script = '''<script>
(async () => {
  const sess = await (window.sessionReady || Promise.resolve());
  if (!sess) return;
  const t = document.getElementById('tbl');
  let rows;
  try {
    rows = await api('/api/datasets');
  } catch (err) {
    t.innerHTML = `<tr><td class="muted">Could not load datasets. ${esc(err.message)}</td></tr>`;
    return;
  }
  const cur = getDataset();
  if (!rows || !rows.length) {
    t.innerHTML = '<tr><td class="muted">No datasets yet. <a href="/" class="grad"><b>Upload one →</b></a></td></tr>';
    return;
  }
  t.innerHTML = '<tr><th>Dataset</th><th>Rows</th><th>Quality</th><th>Uploaded</th><th></th></tr>' + rows.map(r => `
    <tr><td><b>${esc(r.filename)}</b> ${r.id===cur?'<span class="tag low">active</span>':''}</td><td>${r.row_count}</td>
    <td>${r.quality.quality_score}/100</td><td class="muted">${esc(r.upload_date.replace('T',' '))}</td>
    <td class="row"><button class="btn sm" data-gen="${r.id}">⚡ Generate</button>
    <a class="btn sm ghost" data-view="${r.id}" href="${(window.API_BASE_URL || '')}/api/report/${r.id}" target="_blank" hidden>👁 View</a>
    <a class="btn sm ghost" data-dl="${r.id}" href="${(window.API_BASE_URL || '')}/api/report/${r.id}?download=1" hidden>⬇ Download</a></td></tr>`).join('');
  
  for (const r of rows) {
    const ok = (await fetch((window.API_BASE_URL || '') + '/api/report/' + r.id, { credentials: 'include' })).ok;
    if (ok) showLinks(r.id);
  }
  t.addEventListener('click', async e => {
    const id = e.target.dataset.gen;
    if (!id) return;
    e.target.disabled = true;
    e.target.textContent = 'Working…';
    try {
      await api('/api/report/' + id, { method: 'POST', body: { metric: 'profit' } });
      showLinks(id);
      toast('Report ready ✅');
    } catch(err) {
      toast(err.message, true);
    }
    e.target.disabled = false;
    e.target.textContent = '⚡ Regenerate';
  });
  function showLinks(id) {
    t.querySelectorAll(`[data-view="${id}"],[data-dl="${id}"]`).forEach(a => a.hidden = false);
  }
})();
</script>'''
    (FRONTEND / "reports.html").write_text(
        make_shell("Reports · AI Business Detective", rep_content, body_extra=rep_script, page="reports"),
        encoding="utf-8"
    )

    # 7. login.html
    login_content = '''<section class="auth">
  <aside class="auth-art">
    <span class="eyebrow"><i></i> Your private case room</span>
    <h2>Solve the case<br>behind your <span class="grad">numbers</span>.</h2>
    <ul>
      <li><i>🔐</i><div><b>Your data stays yours</b>Every dataset is tied to your account. Nobody else can open it.</div></li>
      <li><i>🧪</i><div><b>Test ideas before you try them</b>What-if lab, monthly goals and case notes — all saved to your profile.</div></li>
      <li><i>🏅</i><div><b>Earn your detective rank</b>Collect badges as you upload, investigate and report.</div></li>
    </ul>
    <svg class="float" viewBox="0 0 300 220" fill="none" aria-hidden="true"><defs><linearGradient id="ag" x1="0" x2="1"><stop offset="0" stop-color="var(--a1)"/><stop offset="1" stop-color="var(--a3)"/></linearGradient></defs>
      <rect x="20" y="130" width="34" height="70" rx="8" fill="var(--a1)" opacity=".7"/><rect x="70" y="95" width="34" height="105" rx="8" fill="var(--a2)" opacity=".8"/>
      <rect x="120" y="60" width="34" height="140" rx="8" fill="var(--a3)" opacity=".85"/><path d="M10 120 C70 90 110 60 170 70 S250 30 290 20" stroke="url(#ag)" stroke-width="5" stroke-linecap="round"/></svg>
  </aside>

  <div class="auth-form">
    <div class="auth-box fade">
      <h1>Welcome back</h1><p class="sub">Sign in to continue your investigation.</p>
      <div id="formErr" class="err" hidden role="alert"></div>
      <form id="authForm" novalidate autocomplete="on" data-mode="login" data-next="/dashboard">
        <div class="field"><label for="email">Email</label><input id="email" name="email" type="email" autocomplete="email" maxlength="120" placeholder="you@example.com" required></div>
        <div class="field"><label for="password">Password</label>
          <input id="password" name="password" type="password" autocomplete="current-password" maxlength="128" placeholder="Your password" required>
          <button type="button" class="eye" id="eye" aria-label="Show password">👁</button>
        </div>
        <button class="btn" id="submitBtn" style="width:100%;justify-content:center;padding:15px" type="submit">Sign in</button>
      </form>
      <p class="swap">
        New here? <a href="/register">Create an account</a>
      </p>
    </div>
  </div>
</section>'''
    (FRONTEND / "login.html").write_text(
        make_shell("Sign in · AI Business Detective", login_content, body_extra='<script src="/js/auth.js"></script>', page="auth"),
        encoding="utf-8"
    )

    # 8. register.html
    reg_content = '''<section class="auth">
  <aside class="auth-art">
    <span class="eyebrow"><i></i> Your private case room</span>
    <h2>Solve the case<br>behind your <span class="grad">numbers</span>.</h2>
    <ul>
      <li><i>🔐</i><div><b>Your data stays yours</b>Every dataset is tied to your account. Nobody else can open it.</div></li>
      <li><i>🧪</i><div><b>Test ideas before you try them</b>What-if lab, monthly goals and case notes — all saved to your profile.</div></li>
      <li><i>🏅</i><div><b>Earn your detective rank</b>Collect badges as you upload, investigate and report.</div></li>
    </ul>
    <svg class="float" viewBox="0 0 300 220" fill="none" aria-hidden="true"><defs><linearGradient id="ag" x1="0" x2="1"><stop offset="0" stop-color="var(--a1)"/><stop offset="1" stop-color="var(--a3)"/></linearGradient></defs>
      <rect x="20" y="130" width="34" height="70" rx="8" fill="var(--a1)" opacity=".7"/><rect x="70" y="95" width="34" height="105" rx="8" fill="var(--a2)" opacity=".8"/>
      <rect x="120" y="60" width="34" height="140" rx="8" fill="var(--a3)" opacity=".85"/><path d="M10 120 C70 90 110 60 170 70 S250 30 290 20" stroke="url(#ag)" stroke-width="5" stroke-linecap="round"/></svg>
  </aside>

  <div class="auth-form">
    <div class="auth-box fade">
      <h1>Create your account</h1><p class="sub">Free, secure and takes under a minute.</p>
      <div id="formErr" class="err" hidden role="alert"></div>
      <form id="authForm" novalidate autocomplete="on" data-mode="register" data-next="/dashboard">
        <div class="field"><label for="name">Full name</label><input id="name" name="name" autocomplete="name" maxlength="60" placeholder="e.g. Asha Kumar" required></div>
        <div class="field"><label for="email">Email</label><input id="email" name="email" type="email" autocomplete="email" maxlength="120" placeholder="you@example.com" required></div>
        <div class="field"><label for="password">Password</label>
          <input id="password" name="password" type="password" autocomplete="new-password" maxlength="128" placeholder="At least 8 characters, with a letter and a number" required>
          <button type="button" class="eye" id="eye" aria-label="Show password">👁</button>
          <div class="meter"><i id="meterBar"></i></div><div class="hint2" id="meterTxt">Use 8+ characters with letters and numbers.</div>
        </div>
        <div class="field"><label for="password2">Confirm password</label><input id="password2" type="password" autocomplete="new-password" maxlength="128" placeholder="Repeat your password" required></div>
        <button class="btn" id="submitBtn" style="width:100%;justify-content:center;padding:15px" type="submit">Create account</button>
      </form>
      <p class="swap">
        Already have an account? <a href="/login">Sign in</a>
      </p>
    </div>
  </div>
</section>'''
    (FRONTEND / "register.html").write_text(
        make_shell("Create your account · AI Business Detective", reg_content, body_extra='<script src="/js/auth.js"></script>', page="auth"),
        encoding="utf-8"
    )

    # 9. profile.html
    prof_content = '''<div class="page-head"><h2>My <span class="grad">profile</span></h2><p>Manage your details, picture and appearance.</p></div>
<div class="prof">
  <div>
    <div class="card prof-card fade">
      <label class="avatar-drop" id="drop" title="Click or drop an image">
        <span class="avatar xl" id="bigAvatar"></span><span class="cam">📷</span>
        <input type="file" id="avatarFile" accept="image/png,image/jpeg,image/webp,image/gif" hidden>
      </label>
      <h3 id="pName" style="margin:0;font-size:22px"></h3>
      <div class="muted" id="pRole" style="margin-top:2px"></div>
      <div class="muted" id="pMeta" style="font-size:13px;margin-top:4px"></div>
      <div class="row" style="justify-content:center;margin-top:16px"><button class="btn sm" id="pickBtn">⬆ Upload photo</button><button class="btn ghost sm" id="rmBtn" hidden>Remove</button></div>
      <div class="hint2" style="margin-top:10px">PNG, JPG, WEBP or GIF · up to 3 MB · cropped to a square</div>
    </div>
    <div class="card fade" style="margin-top:18px">
      <div class="between"><b id="rankTitle">Rookie</b><span class="tag low" id="rankLvl">Lv 1</span></div>
      <div class="xpbar"><i id="xpFill" style="width:0"></i></div><div class="muted" style="font-size:12.5px" id="xpTxt"></div>
      <div class="badges" id="badges"></div>
    </div>
  </div>

  <div style="display:grid;gap:18px">
    <div class="card fade"><h3 style="margin:0 0 4px">Personal details</h3><p class="muted" style="margin:0 0 18px;font-size:14px">Shown only to you inside this app.</p>
      <div id="profErr" class="err" hidden role="alert"></div>
      <form id="profForm" class="form2" novalidate>
        <div class="field"><label for="f_name">Full name</label><input id="f_name" maxlength="60" required></div>
        <div class="field"><label for="f_email">Email</label><input id="f_email" disabled title="Email can't be changed"></div>
        <div class="field"><label for="f_job">Job title</label><input id="f_job" maxlength="80" placeholder="e.g. Data Analyst"></div>
        <div class="field"><label for="f_company">Company / college</label><input id="f_company" maxlength="80" placeholder="e.g. NPRO Technologies"></div>
        <div class="field full"><label for="f_loc">Location</label><input id="f_loc" maxlength="80" placeholder="e.g. Bengaluru, India"></div>
        <div class="field full"><label for="f_bio">About me</label><textarea id="f_bio" maxlength="300" placeholder="A line or two about you…"></textarea><div class="hint2" id="bioCount">0 / 300</div></div>
        <div class="full row"><button class="btn" id="saveBtn" type="submit">💾 Save changes</button></div>
      </form>
    </div>

    <div class="card fade"><h3 style="margin:0 0 14px">Change password</h3>
      <div id="pwErr" class="err" hidden role="alert"></div>
      <form id="pwForm" class="form2" novalidate>
        <div class="field full"><label for="pw_cur">Current password</label><input id="pw_cur" type="password" autocomplete="current-password"></div>
        <div class="field"><label for="pw_new">New password</label><input id="pw_new" type="password" autocomplete="new-password" maxlength="128"></div>
        <div class="field"><label for="pw_new2">Confirm new password</label><input id="pw_new2" type="password" autocomplete="new-password" maxlength="128"></div>
        <div class="full"><button class="btn ghost" type="submit">🔑 Update password</button></div>
      </form>
    </div>

    <div class="card danger-zone fade"><h3 style="margin:0 0 4px;color:var(--bad)">Danger zone</h3>
      <p class="muted" style="margin:0 0 14px;font-size:14px">Deleting your account permanently removes your profile, picture, datasets, reports, goals and notes. This cannot be undone.</p>
      <button class="btn ghost danger" id="delBtn">🗑 Delete my account</button></div>
  </div>
</div>

<div class="modal-bg" id="delModal"><div class="modal" role="dialog" aria-modal="true" aria-labelledby="dmTitle">
  <h3 id="dmTitle" style="margin:0 0 8px">Delete your account?</h3><p class="muted" style="margin:0 0 16px">Type your password to confirm. Everything will be erased.</p>
  <div id="delErr" class="err" hidden></div>
  <div class="field"><label for="del_pw">Password</label><input id="del_pw" type="password" autocomplete="current-password"></div>
  <div class="row" style="justify-content:flex-end"><button class="btn ghost" id="delCancel">Cancel</button><button class="btn danger" id="delGo">Delete forever</button></div>
</div></div>'''
    (FRONTEND / "profile.html").write_text(
        make_shell("My profile · AI Business Detective", prof_content, body_extra='<script src="/js/profile.js"></script>', page="profile"),
        encoding="utf-8"
    )

    # 10. 404.html
    not_found_content = '''<div class="card glow" style="text-align:center;padding:60px 24px;margin-top:40px">
  <div style="font-size:56px">🕵️</div>
  <h1 style="font-size:32px;margin:12px 0 6px">Case not found <span class="hot">(404)</span></h1>
  <p class="muted" style="font-size:16px;max-width:500px;margin:0 auto 24px">
    The clue or page you are looking for does not exist, was moved, or has expired.
  </p>
  <div class="row" style="justify-content:center;gap:12px">
    <a class="btn" href="/">Return to Home</a>
    <a class="btn ghost" href="/dashboard">Go to Dashboard</a>
  </div>
</div>'''
    (FRONTEND / "404.html").write_text(
        make_shell("Page Not Found · AI Business Detective", not_found_content, page="404"),
        encoding="utf-8"
    )


def write_netlify_configs():
    # Netlify TOML in root
    netlify_toml = '''[build]
  publish = "frontend"
  # If you want Netlify to re-run the build script on git push, uncomment below:
  # command = "python scripts/build_frontend.py"

# Proxy API and avatar requests to your hosted FastAPI backend
# Replace https://your-fastapi-backend.onrender.com with your actual backend URL:
[[redirects]]
  from = "/api/*"
  to = "https://your-fastapi-backend.onrender.com/api/:splat"
  status = 200
  force = true

[[redirects]]
  from = "/avatar/*"
  to = "https://your-fastapi-backend.onrender.com/avatar/:splat"
  status = 200
  force = true

# Pretty URLs for clean routing
[[redirects]]
  from = "/login"
  to = "/login.html"
  status = 200

[[redirects]]
  from = "/register"
  to = "/register.html"
  status = 200

[[redirects]]
  from = "/dashboard"
  to = "/dashboard.html"
  status = 200

[[redirects]]
  from = "/investigation"
  to = "/investigation.html"
  status = 200

[[redirects]]
  from = "/lab"
  to = "/lab.html"
  status = 200

[[redirects]]
  from = "/data"
  to = "/data.html"
  status = 200

[[redirects]]
  from = "/reports"
  to = "/reports.html"
  status = 200

[[redirects]]
  from = "/profile"
  to = "/profile.html"
  status = 200

# Fallback 404
[[redirects]]
  from = "/*"
  to = "/404.html"
  status = 404

# Security and cache headers
[[headers]]
  for = "/*"
  [headers.values]
    X-Frame-Options = "DENY"
    X-Content-Type-Options = "nosniff"
    Referrer-Policy = "strict-origin-when-cross-origin"

[[headers]]
  for = "/fonts/*"
  [headers.values]
    Cache-Control = "public, max-age=31536000, immutable"

[[headers]]
  for = "/vendor/*"
  [headers.values]
    Cache-Control = "public, max-age=2592000"
'''
    (ROOT / "netlify.toml").write_text(netlify_toml, encoding="utf-8")

    # frontend/_redirects
    redirects_content = '''# Netlify Proxy redirects for FastAPI backend API
/api/*     https://your-fastapi-backend.onrender.com/api/:splat  200!
/avatar/*  https://your-fastapi-backend.onrender.com/avatar/:splat  200!

# Clean URLs
/login          /login.html          200
/register       /register.html       200
/dashboard      /dashboard.html      200
/investigation  /investigation.html  200
/lab            /lab.html            200
/data           /data.html           200
/reports        /reports.html        200
/profile        /profile.html        200

# Custom 404
/*              /404.html            404
'''
    (FRONTEND / "_redirects").write_text(redirects_content, encoding="utf-8")

    # frontend/_headers
    headers_content = '''/*
  X-Frame-Options: DENY
  X-Content-Type-Options: nosniff
  Referrer-Policy: strict-origin-when-cross-origin

/fonts/*
  Cache-Control: public, max-age=31536000, immutable

/vendor/*
  Cache-Control: public, max-age=2592000
'''
    (FRONTEND / "_headers").write_text(headers_content, encoding="utf-8")


def main():
    print("Building Netlify frontend package...")
    setup_directories()
    copy_static_assets()
    write_config_js()
    write_common_js()
    copy_and_adapt_scripts()
    generate_html_files()
    write_netlify_configs()
    print("Frontend built successfully in 'frontend/' ready for Netlify deployment!")


if __name__ == "__main__":
    main()
