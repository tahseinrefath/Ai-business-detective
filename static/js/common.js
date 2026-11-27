/* Shared helpers: secure API wrapper, formatting, toast, theme/accent, command palette, background, Plotly theme. */
const UID = document.body.dataset.uid || '0', AUTHED = document.body.dataset.authed === '1';
const KEY = 'abd_dataset_' + UID;                       // per-user, so accounts never share a "current dataset"
const getDataset = () => localStorage.getItem(KEY);
const setDataset = (id, name) => { localStorage.setItem(KEY, id); localStorage.setItem(KEY + '_name', name || ''); paintBadge(); };
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const fmt = n => n == null ? 'n/a' : (n < 0 ? '-' : '') + '₹' + Math.abs(Math.round(n)).toLocaleString('en-IN');
const pctf = (n, d = 1) => n == null ? 'n/a' : (n > 0 ? '+' : '') + n.toFixed(d) + '%';
const csrf = () => document.querySelector('meta[name="csrf-token"]')?.content || '';

async function api(url, opts = {}) {
  const init = { method: opts.method || 'GET', headers: { 'X-CSRF-Token': csrf() }, credentials: 'same-origin' };
  if (opts.body) { init.body = opts.body instanceof FormData ? opts.body : JSON.stringify(opts.body);
    if (!(opts.body instanceof FormData)) init.headers['Content-Type'] = 'application/json'; }
  const res = await fetch(url, init);
  const data = await res.json().catch(() => ({}));
  if (res.status === 401 && data.login_required) { location.href = '/login?next=' + encodeURIComponent(location.pathname); throw new Error('Please sign in.'); }
  if (!res.ok) { const err = new Error(data.error || 'Something went wrong'); err.data = data; err.status = res.status; throw err; }
  return data;
}

let toastTimer;
function toast(msg, isErr = false) {
  const t = document.getElementById('toast'); t.textContent = msg; t.className = 'toast show' + (isErr ? ' err' : '');
  clearTimeout(toastTimer); toastTimer = setTimeout(() => t.className = 'toast', 3800);
}
function paintBadge() {
  const b = document.getElementById('dsBadge'), id = AUTHED ? getDataset() : null;
  b.hidden = !AUTHED; b.innerHTML = id ? `Dataset: <b>${esc(localStorage.getItem(KEY + '_name') || id)}</b>` : 'No dataset';
}
paintBadge();

/* ---- one fixed palette (obsidian / chrome / laser crimson): no theme switching. onTheme kept as a no-op for older callers ---- */
const onTheme = () => {};

/* ---- user menu / logout ---- */
const userBtn = document.getElementById('userBtn'), userMenu = document.getElementById('userMenu');
if (userBtn) {
  userBtn.onclick = e => { e.stopPropagation(); userMenu.classList.toggle('open'); };
  document.addEventListener('click', e => { if (!userMenu.contains(e.target)) userMenu.classList.remove('open'); });
  document.getElementById('logoutBtn').onclick = signOut;
}
async function signOut() { try { await api('/api/auth/logout', { method: 'POST' }); } catch (e) {} location.href = '/login'; }

/* ---- reveal, count-up ---- */
function countUp(el, to, formatter = v => Math.round(v), ms = 900) {
  const t0 = performance.now();
  (function step(t) { const p = Math.min((t - t0) / ms, 1), e = 1 - Math.pow(1 - p, 3);
    el.textContent = formatter(to * e); if (p < 1) requestAnimationFrame(step); })(t0);
}
const io = new IntersectionObserver(es => es.forEach(e => { if (e.isIntersecting) { e.target.classList.add('in'); io.unobserve(e.target); } }), { threshold: .12 });
document.querySelectorAll('.reveal').forEach(el => io.observe(el));
document.querySelectorAll('[data-count]').forEach(el => countUp(el, +el.dataset.count, v => Math.round(v), 1200));

/* ---- card spotlight that follows the pointer ---- */
document.addEventListener('pointermove', e => { const c = e.target.closest && e.target.closest('.card'); if (!c) return;
  const r = c.getBoundingClientRect(); c.style.setProperty('--mx', (e.clientX - r.left) + 'px'); c.style.setProperty('--my', (e.clientY - r.top) + 'px'); });

/* ---- animated network background ---- */
(function () {
  const cv = document.getElementById('bgnet'); if (!cv || matchMedia('(prefers-reduced-motion: reduce)').matches) return;
  const ctx = cv.getContext('2d'); let W, H, dots = [], raf;
  const resize = () => { const r = Math.min(devicePixelRatio || 1, 1.5); W = cv.width = innerWidth * r; H = cv.height = innerHeight * r; ctx.setTransform(r, 0, 0, r, 0, 0);
    dots = Array.from({ length: Math.round(Math.min(70, innerWidth / 22)) }, () => ({ x: Math.random() * innerWidth, y: Math.random() * innerHeight, vx: (Math.random() - .5) * .25, vy: (Math.random() - .5) * .25 })); };
  function frame() {
    ctx.clearRect(0, 0, innerWidth, innerHeight); const c1 = getComputedStyle(document.documentElement).getPropertyValue('--a1').trim() || '#c9cdd3';
    ctx.fillStyle = c1; ctx.strokeStyle = c1;
    for (const d of dots) { d.x += d.vx; d.y += d.vy; if (d.x < 0 || d.x > innerWidth) d.vx *= -1; if (d.y < 0 || d.y > innerHeight) d.vy *= -1;
      ctx.globalAlpha = .55; ctx.beginPath(); ctx.arc(d.x, d.y, 1.4, 0, 6.3); ctx.fill(); }
    for (let i = 0; i < dots.length; i++) for (let j = i + 1; j < dots.length; j++) { const dx = dots[i].x - dots[j].x, dy = dots[i].y - dots[j].y, dist = dx * dx + dy * dy;
      if (dist < 14000) { ctx.globalAlpha = (1 - dist / 14000) * .22; ctx.beginPath(); ctx.moveTo(dots[i].x, dots[i].y); ctx.lineTo(dots[j].x, dots[j].y); ctx.stroke(); } }
    raf = requestAnimationFrame(frame);
  }
  resize(); frame(); addEventListener('resize', resize);
  document.addEventListener('visibilitychange', () => document.hidden ? cancelAnimationFrame(raf) : frame());
})();

/* ---- command palette (Ctrl/Cmd + K) ---- */
(function () {
  const go = u => () => location.href = u;
  const actions = AUTHED ? [
    ['🏠', 'Home', go('/')], ['📊', 'Dashboard', go('/dashboard')], ['🔍', 'Investigate', go('/investigation')], ['🧪', 'What-if lab', go('/lab')],
    ['🗂️', 'Data explorer', go('/data')], ['📄', 'Reports', go('/reports')], ['👤', 'My profile', go('/profile')],
    ['🔎', 'Load the demo case', async () => { try { const r = await api('/api/sample', { method: 'POST', body: { kind: 'clean' } }); setDataset(r.dataset.id, r.dataset.filename); location.href = '/dashboard'; } catch (e) { toast(e.message, true); } }],
    ['🚪', 'Sign out', signOut]]
    : [['🔑', 'Sign in', go('/login')], ['✨', 'Create account', go('/register')]];
  const bg = document.createElement('div'); bg.className = 'pal-bg';
  bg.innerHTML = '<div class="pal" role="dialog" aria-label="Quick actions"><input placeholder="Type a command… (try: dashboard, theme, profile)" aria-label="Search actions"><ul></ul></div>';
  document.body.appendChild(bg);
  const input = bg.querySelector('input'), ul = bg.querySelector('ul'); let shown = [], sel = 0;
  function draw() { const q = input.value.toLowerCase().trim(); shown = actions.filter(a => a[1].toLowerCase().includes(q)); sel = Math.min(sel, Math.max(shown.length - 1, 0));
    ul.innerHTML = shown.length ? shown.map((a, i) => `<li class="${i === sel ? 'sel' : ''}" data-i="${i}"><span>${a[0]}</span>${esc(a[1])}</li>`).join('') : '<div class="empty-r">No matching action</div>'; }
  const open = () => { bg.classList.add('open'); input.value = ''; sel = 0; draw(); setTimeout(() => input.focus(), 30); }, close = () => bg.classList.remove('open');
  const run = i => { const a = shown[i]; if (a) { close(); a[2](); } };
  document.getElementById('palBtn').onclick = open;
  addEventListener('keydown', e => { if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') { e.preventDefault(); bg.classList.contains('open') ? close() : open(); }
    else if (bg.classList.contains('open')) { if (e.key === 'Escape') close(); else if (e.key === 'ArrowDown') { sel = Math.min(sel + 1, shown.length - 1); draw(); e.preventDefault(); }
      else if (e.key === 'ArrowUp') { sel = Math.max(sel - 1, 0); draw(); e.preventDefault(); } else if (e.key === 'Enter') run(sel); } });
  input.oninput = () => { sel = 0; draw(); }; bg.onclick = e => { if (e.target === bg) close(); }; ul.onclick = e => { const li = e.target.closest('li'); if (li) run(+li.dataset.i); };
})();

/* ---- Plotly theme (reads the CSS palette variables) ---- */
const css = v => getComputedStyle(document.documentElement).getPropertyValue(v).trim();
const COLORS = { silver: '#c9cdd3', silverHi: '#f2f4f7', silverLo: '#8a9098', dim: '#4d525a', crimson: '#ff1a40', crimsonHi: '#ff4d6d', crimsonLo: '#a10020',
  /* legacy names used by older chart code, mapped onto the palette */
  cyan: '#c9cdd3', violet: '#ff1a40', pink: '#ff4d6d', good: '#f2f4f7', bad: '#ff1a40', amber: '#8a9098' };
function plotLayout(extra = {}) {
  const grid = css('--line'), ink = css('--ink');
  return Object.assign({ paper_bgcolor: 'rgba(0,0,0,0)', plot_bgcolor: 'rgba(0,0,0,0)', font: { color: ink, family: 'Inter, system-ui, sans-serif', size: 12 },
    margin: { t: 14, r: 16, b: 40, l: 62 }, xaxis: { gridcolor: grid, zerolinecolor: grid }, yaxis: { gridcolor: grid, zerolinecolor: grid },
    legend: { orientation: 'h', y: 1.16 }, hoverlabel: { bgcolor: css('--bg2'), font: { color: ink } } }, extra);
}
const plot = (id, data, layout) => Plotly.react(id, data, plotLayout(layout), { displayModeBar: false, responsive: true });


/* ---- keep emoji monochrome (U+FE0E asks for the flat text glyph) - the CSS font-variant-emoji rule covers modern browsers, this covers the rest ---- */
(function () {
  const HAS = /\p{Extended_Pictographic}/u, FIX = /(\p{Extended_Pictographic})(?:\uFE0F|(?!\uFE0E))/gu, skip = new Set(['SCRIPT', 'STYLE', 'TEXTAREA', 'INPUT']);
  function mono(root) {
    const w = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
    for (let n = w.nextNode(); n; n = w.nextNode()) {
      if (skip.has(n.parentNode.nodeName) || !HAS.test(n.nodeValue)) continue;
      const v = n.nodeValue.replace(FIX, '$1\uFE0E'); if (v !== n.nodeValue) n.nodeValue = v;
    }
  }
  let pending = false;
  new MutationObserver(() => { if (pending) return; pending = true; requestAnimationFrame(() => { pending = false; mono(document.body); }); })
    .observe(document.body, { childList: true, subtree: true });
  mono(document.body);
})();
