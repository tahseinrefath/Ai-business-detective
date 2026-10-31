const $ = id => document.getElementById(id), DS = getDataset();
if (!DS) $('empty').hidden = false; else { $('content').hidden = false; init(); }
let timer, lastRun = null;

async function init() {
  try {
    const s = await api('/api/whatif/segments?dataset=' + DS);
    $('simMonth').textContent = s.current;
    $('segSel').innerHTML = s.segments.map(x => `<option value="${esc(x.name)}">${esc(x.name)} · ${fmt(x.sales)}</option>`).join('');
    if (!s.segments.length) { toast('No segments found in the latest month.', true); return; }
    runSim(false); loadGoals(); loadNotes();
  } catch (e) { toast(e.message, true); }
}

/* ---------------- what-if ---------------- */
const sliders = [['sOrd', 'oOrd', v => (v > 0 ? '+' : '') + v + '%'], ['sPrice', 'oPrice', v => (v > 0 ? '+' : '') + v + '%'], ['sMar', 'oMar', v => (v > 0 ? '+' : '') + v + ' pts']];
function paintOutputs() { sliders.forEach(([s, o, f]) => $(o).textContent = f(+$(s).value)); }
async function runSim(commit) {
  paintOutputs();
  try {
    const r = await api('/api/whatif', { method: 'POST', body: { dataset: DS, segment: $('segSel').value, commit: !!commit,
      order_change_pct: +$('sOrd').value, price_change_pct: +$('sPrice').value, margin_change_pts: +$('sMar').value } });
    lastRun = r; drawSim(r);
  } catch (e) { toast(e.message, true); }
}
function drawSim(r) {
  const b = r.baseline, s = r.scenario, dp = r.delta_profit, up = dp >= 0;
  $('simOut').innerHTML = `
    <div class="d"><small>Scenario profit</small><b>${fmt(s.profit)}</b></div>
    <div class="d"><small>Change in profit</small><b class="${up ? 'up' : 'down'}">${up ? '▲' : '▼'} ${fmt(Math.abs(dp))}</b></div>
    <div class="d"><small>Scenario sales</small><b>${fmt(s.sales)}</b></div>
    <div class="d"><small>Orders · margin</small><b>${Math.round(s.orders)} · ${s.margin.toFixed(1)}%</b></div>
    <div class="d" style="grid-column:1/-1"><small>Impact on the whole month's profit</small><b class="${up ? 'up' : 'down'}">${r.pct_of_month_profit == null ? 'n/a' : pctf(r.pct_of_month_profit, 2)}</b></div>`;
  plot('cSim', [
    { x: ['Sales', 'Profit'], y: [b.sales, b.profit], type: 'bar', name: 'Now', marker: { color: COLORS.silver } },
    { x: ['Sales', 'Profit'], y: [s.sales, s.profit], type: 'bar', name: 'Scenario', marker: { color: COLORS.crimson } }],
    { barmode: 'group', height: 260, margin: { t: 10, r: 10, b: 30, l: 70 } });
}
sliders.forEach(([s]) => {
  $(s).addEventListener('input', () => { paintOutputs(); clearTimeout(timer); timer = setTimeout(() => runSim(false), 160); });
  $(s).addEventListener('change', () => { clearTimeout(timer); runSim(true); });          // released: counts toward rank XP
});
$('segSel').onchange = () => runSim(true);
$('resetBtn').onclick = () => { ['sOrd', 'sPrice', 'sMar'].forEach(i => $(i).value = 0); runSim(false); };
$('restoreBtn').onclick = () => {
  const v = lastRun && lastRun.restore_order_change_pct;
  if (v == null) return toast('No orders last month to compare with.', true);
  $('sOrd').value = Math.max(-80, Math.min(100, Math.round(v))); runSim(true);
};

/* ---------------- goals ---------------- */
async function loadGoals() {
  try {
    const g = await api('/api/goals?dataset=' + DS);
    $('goalSub').textContent = `Targets for ${g.month} (the latest month in your data).`;
    $('goalList').innerHTML = g.goals.length ? g.goals.map(x => {
      const p = Math.min(x.pct, 100), met = x.pct >= 100;
      return `<div class="goal"><div class="ring" style="--p:${p.toFixed(0)}"><span>${Math.round(x.pct)}%</span></div>
        <div style="flex:1"><b style="text-transform:capitalize">${esc(x.metric)} goal · ${fmt(x.target)}</b>
        <div class="muted" style="font-size:13px">So far ${fmt(x.actual)} ${met ? '· <b class="up">target reached ✔</b>' : `· ${fmt(x.remaining)} to go`}</div>
        <div class="muted" style="font-size:12.5px">${!met && x.needed_per_day != null ? `Needs about ${fmt(x.needed_per_day)} per day for the last ${x.days_left} day(s).` : (met ? 'Nice work.' : 'The month is complete.')}</div></div>
        <button class="x" data-del="${esc(x.metric)}" aria-label="Delete goal">✕</button></div>`; }).join('') : '<p class="muted" style="margin:0">No goals yet.</p>';
  } catch (e) { toast(e.message, true); }
}
$('gSave').onclick = async () => {
  const box = $('goalErr'); box.hidden = true;
  try { await api('/api/goals', { method: 'PUT', body: { dataset: DS, metric: $('gMetric').value, amount: $('gAmount').value } }); $('gAmount').value = ''; toast('Goal saved ✅'); loadGoals(); }
  catch (e) { box.textContent = e.message; box.hidden = false; }
};
$('goalList').onclick = async e => { const m = e.target.dataset.del; if (!m) return;
  try { await api('/api/goals', { method: 'DELETE', body: { dataset: DS, metric: m } }); loadGoals(); } catch (err) { toast(err.message, true); } };

/* ---------------- notes ---------------- */
async function loadNotes() {
  try {
    const r = await api('/api/notes?dataset=' + DS);
    $('noteList').innerHTML = r.notes.length ? r.notes.map(n => `<li><div>${esc(n.text)}<small>${esc(n.created_at)}</small></div><button class="x" data-note="${n.id}" aria-label="Delete note">✕</button></li>`).join('')
      : '<li class="muted">No notes yet.</li>';
  } catch (e) { toast(e.message, true); }
}
$('noteText').oninput = e => $('noteCount').textContent = e.target.value.length + ' / 500';
$('noteAdd').onclick = async () => {
  const t = $('noteText').value.trim(); if (!t) return toast('Write something first.', true);
  try { await api('/api/notes', { method: 'POST', body: { dataset: DS, text: t } }); $('noteText').value = ''; $('noteCount').textContent = '0 / 500'; loadNotes(); }
  catch (e) { toast(e.message, true); }
};
$('noteList').onclick = async e => { const id = e.target.dataset.note; if (!id) return;
  try { await api('/api/notes/' + id, { method: 'DELETE' }); loadNotes(); } catch (err) { toast(err.message, true); } };
