const id = getDataset(), res = document.getElementById('result'), qInput = document.getElementById('q'), go = document.getElementById('go');
const selPrev = document.getElementById('selPrev'), selCurr = document.getElementById('selCurr');
if (!id) document.getElementById('empty').hidden = false; else document.getElementById('content').hidden = false;
let current = null, tab = 'segment', metric = 'auto';
const TABS = { segment: 'Product · Region', product: 'Product', region: 'Region', category: 'Category' };

async function init() {
  const o = await api('/api/options?dataset=' + id), m = o.months, opts = m.map(x => `<option>${esc(x)}</option>`).join('');
  selPrev.innerHTML = selCurr.innerHTML = opts; selPrev.value = m[Math.max(m.length - 2, 0)]; selCurr.value = m[m.length - 1];
  [selPrev, selCurr].forEach(s => s.onchange = run);
}

async function run() {
  const question = qInput.value.trim(); if (!question) return toast('Type a question first', true);
  go.disabled = true; go.textContent = 'Investigating…';
  res.innerHTML = '<div class="card"><div class="skel" style="width:70%"></div><br><div class="skel" style="width:92%"></div><br><div class="skel" style="width:55%"></div></div>';
  try { current = await api('/api/ask', { method: 'POST', body: { dataset: id, question, previous: selPrev.value, current: selCurr.value, metric: metric === 'auto' ? null : metric } }); render(); }
  catch (e) { res.innerHTML = ''; toast(e.message, true); }
  go.disabled = false; go.textContent = 'Investigate';
}

function render() {
  const { investigation: inv, findings, next_checks, explanation } = current, c = inv.comparison, dr = inv.drivers;
  const cls = c.direction === 'decline' ? 'down' : c.direction === 'increase' ? 'up' : 'muted';
  const arrow = c.direction === 'decline' ? '▼' : c.direction === 'increase' ? '▲' : '■';
  res.innerHTML = `
  <div class="card glow fade"><div class="verdict"><div><div class="muted" style="font-weight:700">${esc(c.metric.toUpperCase())} · ${esc(c.previous_period)} → ${esc(c.current_period)}</div>
      <div class="pctbig ${cls}">${arrow} ${pctf(c.pct)}</div><div class="muted">${fmt(c.previous)} → ${fmt(c.current)}</div></div>
    <div><div class="between"><b>🕵️ The Detective's read</b><span class="src">${explanation.source === 'llm' ? '🤖 AI-written from evidence' : '📐 rule-based from evidence'}</span></div>
    <p class="expl">${esc(explanation.text)}</p></div></div>
    ${c.partial_warning ? `<div class="warnbox">⚠ ${esc(c.partial_warning)}</div>` : ''}</div>

  <div class="grid g2" style="margin-top:18px">
    <div class="card fade"><div class="between"><h4 style="margin:0">Who moved the number?</h4>
      <div class="seg" id="tabs">${Object.entries(TABS).map(([k, v]) => `<button data-t="${k}" class="${k === tab ? 'on' : ''}">${v}</button>`).join('')}</div></div>
      <div id="cContrib"></div></div>
    <div class="card fade"><h4 style="margin:0">${dr ? 'Inside <span class="grad">' + esc(dr.segment) + '</span>' : 'Drivers'}</h4>
      <p class="muted" style="margin:4px 0 0;font-size:13px">What changed within the single biggest contributor</p>
      <div class="drv">${dr ? dr.changes.map(x => { const bad = x.driver === 'avg_discount' ? x.change > 0 : x.change < 0;
        return `<div class="d"><small>${esc(x.label)}</small><b class="${Math.abs(x.change) < 0.05 ? 'muted' : bad ? 'down' : 'up'}">${x.change >= 0 ? '+' : ''}${x.change.toFixed(1)}${x.unit === 'pts' ? ' pts' : '%'}</b>
        <small>${x.previous.toLocaleString('en-IN', { maximumFractionDigits: 1 })} → ${x.current.toLocaleString('en-IN', { maximumFractionDigits: 1 })}</small></div>`; }).join('') : '<span class="muted">Not enough data.</span>'}</div>
      <div class="note">Red = moved in the unhelpful direction. These are associations in the data, not proven causes.</div></div>
  </div>

  <div class="grid g2" style="margin-top:18px">
    <div class="card fade"><h4 style="margin:0 0 6px">🔎 Key findings</h4>${findings.map(f => `<div class="find"><span class="tag ${f.severity}" style="height:fit-content">${f.severity}</span>
      <div>${esc(f.finding)}<small>${esc(f.evidence)}</small></div></div>`).join('')}</div>
    <div class="card fade"><h4 style="margin:0 0 6px">🚨 Unusual days</h4>
      ${inv.anomalies.length ? inv.anomalies.map(a => `<div class="find"><span style="font-size:22px">${a.direction === 'spike' ? '📈' : '📉'}</span><div><b>${esc(a.date)}</b> · ${fmt(a.sales)}
        <small>typical day ${fmt(a.typical_daily_sales)} · ${esc(a.methods.join(' + '))}<br>${esc(a.note)}</small></div></div>`).join('') : '<p class="muted">No unusual days flagged.</p>'}
      <h4 style="margin:20px 0 6px">✅ Recommended next checks</h4><ul class="checks">${next_checks.map(x => `<li>${esc(x)}</li>`).join('')}</ul></div>
  </div>
  <div class="row" style="margin-top:18px"><button class="btn" id="mkReport">📄 Generate report</button>
    <a class="btn ghost" href="/api/export/${id}/contributors.csv?metric=${inv.metric}&previous=${c.previous_period}&current=${c.current_period}">⬇ Contributors CSV</a></div>`;

  drawContrib();
  document.getElementById('tabs').onclick = e => { if (!e.target.dataset.t) return; tab = e.target.dataset.t;
    document.querySelectorAll('#tabs button').forEach(b => b.classList.toggle('on', b.dataset.t === tab)); drawContrib(); };
  document.getElementById('mkReport').onclick = async e => { e.target.disabled = true;
    try { const r = await api('/api/report/' + id, { method: 'POST', body: { metric: inv.metric, previous: c.previous_period, current: c.current_period } }); toast('Report ready ✅'); window.open(r.url, '_blank'); }
    catch (err) { toast(err.message, true); } e.target.disabled = false; };
}

function drawContrib() {
  const rows = current.investigation.contributors[tab].slice().sort((a, b) => a.delta - b.delta);
  plot('cContrib', [{ x: rows.map(r => r.delta), y: rows.map(r => r.name), type: 'bar', orientation: 'h',
    marker: { color: rows.map(r => r.delta < 0 ? COLORS.bad : COLORS.good) }, text: rows.map(r => fmt(r.delta)), textposition: 'outside', cliponaxis: false,
    customdata: rows.map(r => [fmt(r.previous), fmt(r.current), pctf(r.pct)]),
    hovertemplate: '<b>%{y}</b><br>%{customdata[0]} → %{customdata[1]} (%{customdata[2]})<extra></extra>' }],
    { margin: { t: 14, r: 96, b: 34, l: 150 }, height: 330 });
}

go.onclick = run; qInput.onkeydown = e => e.key === 'Enter' && run();
document.getElementById('chips').onclick = e => { if (e.target.classList.contains('chip')) { qInput.value = e.target.textContent; run(); } };
document.getElementById('metricSeg').onclick = e => { if (!e.target.dataset.m) return; metric = e.target.dataset.m;
  document.querySelectorAll('#metricSeg button').forEach(b => b.classList.toggle('on', b === e.target)); run(); };
onTheme(() => current && drawContrib());
if (id) init().then(run).catch(e => toast(e.message, true));
