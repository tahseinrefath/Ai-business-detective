(async () => {
  const id = getDataset(); const empty = document.getElementById('empty'), content = document.getElementById('content');
  if (!id) { empty.hidden = false; document.getElementById('sub').textContent = 'Nothing loaded yet'; return; }
  document.getElementById('expCsv').href = `/api/export/${id}/clean.csv`;
  const F = { region: 'All', category: 'All', product: 'All', start: '', end: '' };
  const sels = { region: 'fRegion', category: 'fCategory', product: 'fProduct' };
  const state = { products: 'profit', regions: 'profit' }; let D = null, firstLoad = true;

  const qs = () => new URLSearchParams({ dataset: id, ...Object.fromEntries(Object.entries(F).filter(([, v]) => v && v !== 'All')) });

  async function load() {
    try { D = await api('/api/dashboard?' + qs()); } catch (e) { if (firstLoad) { empty.hidden = false; } toast(e.message, true); return; }
    content.hidden = false; empty.hidden = true;
    if (firstLoad) { fillFilters(D.options); firstLoad = false; }
    render();
  }

  function fillFilters(o) {
    const opt = (el, arr) => document.getElementById(el).innerHTML = '<option>All</option>' + arr.map(v => `<option>${esc(v)}</option>`).join('');
    opt('fRegion', o.regions); opt('fCategory', o.categories); opt('fProduct', o.products);
    const s = document.getElementById('fStart'), e = document.getElementById('fEnd'); s.min = e.min = o.min_date; s.max = e.max = o.max_date;
    Object.entries(sels).forEach(([k, el]) => document.getElementById(el).onchange = ev => { F[k] = ev.target.value; load(); });
    s.onchange = ev => { F.start = ev.target.value; load(); }; e.onchange = ev => { F.end = ev.target.value; load(); };
    document.getElementById('fReset').onclick = () => { Object.assign(F, { region: 'All', category: 'All', product: 'All', start: '', end: '' });
      Object.values(sels).forEach(el => document.getElementById(el).value = 'All'); s.value = e.value = ''; load(); };
  }

  function render() {
    const d = D, k = d.kpis, m = d.monthly, last = m[m.length - 1];
    document.getElementById('sub').textContent = `${d.meta.filename} · ${d.meta.quality.date_range.join(' → ')}`;
    document.getElementById('fCount').textContent = `${d.filtered_rows.toLocaleString('en-IN')} of ${d.meta.row_count.toLocaleString('en-IN')} rows shown`;

    document.getElementById('pulse').innerHTML = d.pulse.map(p => `<div class="p fade"><span>${p.icon}</span><div><small>${esc(p.label)}</small><b>${esc(p.value)}</b> <em>· ${esc(p.detail)}</em></div></div>`).join('');

    const h = d.health, CIRC = 2 * Math.PI * 68;
    document.getElementById('healthBody').innerHTML = `<svg viewBox="0 0 170 170" role="img" aria-label="Health score ${h.score} out of 100, ${esc(h.grade)}">
      <circle cx="85" cy="85" r="68" fill="none" stroke="rgba(201,205,211,.12)" stroke-width="12"/>
      <circle cx="85" cy="85" r="68" fill="none" stroke="#ff1a40" stroke-width="12" stroke-linecap="round" stroke-dasharray="${(h.score / 100 * CIRC).toFixed(1)} ${CIRC.toFixed(1)}" transform="rotate(-90 85 85)"/>
      <text x="85" y="92" text-anchor="middle" font-size="46" font-weight="700" fill="#f2f4f7" font-family="Space Grotesk, Inter, sans-serif">${h.score}</text>
      <text x="85" y="114" text-anchor="middle" font-size="11" fill="#8a9098" letter-spacing="1.5" font-family="Inter, sans-serif">${esc(h.grade).toUpperCase()}</text></svg>
      <div>${h.parts.map(p => `<div class="hbar"><div class="top"><span>${esc(p.name)} — ${esc(p.detail)}</span><b>${p.points}/${p.max}</b></div><div class="tr"><i style="width:${(p.points / p.max * 100).toFixed(0)}%"></i></div></div>`).join('')}</div>`;

    const cards = [['💰', 'Total sales', k.total_sales, fmt, last.sales_change], ['📈', 'Total profit', k.total_profit, fmt, last.profit_change],
      ['🎯', 'Profit margin', k.profit_margin, v => v.toFixed(1) + '%', null], ['🧾', 'Total orders', k.total_orders, v => Math.round(v).toLocaleString('en-IN'), null],
      ['📦', 'Units sold', k.units_sold, v => Math.round(v).toLocaleString('en-IN'), null], ['🛒', 'Avg order value', k.avg_order_value, fmt, null]];
    document.getElementById('kpis').innerHTML = cards.map((c, i) => `<div class="card kpi hover fade" style="animation-delay:${i * 55}ms">
      <div class="lbl"><span>${c[0]}</span>${c[1]}</div><div class="val" id="kv${i}">0</div>
      <div class="sub ${c[4] == null ? 'muted' : c[4] >= 0 ? 'up' : 'down'}">${c[4] == null ? '&nbsp;' : (c[4] >= 0 ? '▲ ' : '▼ ') + pctf(c[4]) + ' vs previous month'}</div></div>`).join('');
    cards.forEach((c, i) => countUp(document.getElementById('kv' + i), c[2], c[3]));

    plot('cMonthly', [
      { x: m.map(r => r.month), y: m.map(r => r.sales), type: 'bar', name: 'Sales', marker: { color: COLORS.silver } },
      { x: m.map(r => r.month), y: m.map(r => r.profit), type: 'bar', name: 'Profit', marker: { color: COLORS.crimson } },
      { x: m.map(r => r.month), y: m.map(r => r.margin), type: 'scatter', mode: 'lines+markers', name: 'Margin %', yaxis: 'y2', line: { color: COLORS.silverHi, width: 3 }, marker: { size: 8 } }],
      { barmode: 'group', yaxis2: { overlaying: 'y', side: 'right', showgrid: false, ticksuffix: '%' } });

    const days = d.daily, roll = days.map((_, i) => { const w = days.slice(Math.max(0, i - 6), i + 1); return w.reduce((a, b) => a + b.sales, 0) / w.length; });
    plot('cDaily', [
      { x: days.map(r => r.date), y: days.map(r => r.sales), type: 'scatter', mode: 'lines', name: 'Daily', line: { color: 'rgba(201,205,211,.45)', width: 1.3 }, fill: 'tozeroy', fillcolor: 'rgba(201,205,211,.08)' },
      { x: days.map(r => r.date), y: roll, type: 'scatter', mode: 'lines', name: '7-day average', line: { color: COLORS.crimson, width: 3, shape: 'spline' } }]);

    drawBars();
    plot('cHeat', [{ z: d.heatmap.z, x: d.heatmap.products, y: d.heatmap.regions, type: 'heatmap', colorscale: [[0, '#15151c'], [.5, '#a10020'], [1, '#ff4d6d']],
      hovertemplate: '%{y} · %{x}<br>Profit ₹%{z:,.0f}<extra></extra>', colorbar: { thickness: 10, tickfont: { size: 10 } } }], { margin: { t: 10, r: 10, b: 44, l: 70 } });
    plot('cCat', [{ labels: d.categories.map(r => r.name), values: d.categories.map(r => Math.max(r.profit, 0)), type: 'pie', hole: .62, sort: false,
      marker: { colors: [COLORS.crimson, COLORS.silver, COLORS.crimsonLo, COLORS.silverLo, COLORS.silverHi], line: { color: '#050507', width: 2 } }, textinfo: 'label+percent', hovertemplate: '%{label}<br>₹%{value:,.0f}<extra></extra>' }],
      { margin: { t: 10, r: 10, b: 10, l: 10 }, showlegend: false, height: 340 });

    const dc = document.getElementById('discCard');
    if (d.discount_bands) { dc.hidden = false; plot('cDisc', [{ x: d.discount_bands.map(b => b.band), y: d.discount_bands.map(b => b.margin), type: 'bar',
      marker: { color: d.discount_bands.map((_, i) => ['#f2f4f7', '#c9cdd3', '#8a9098', '#ff1a40'][i % 4]) }, text: d.discount_bands.map(b => b.margin.toFixed(1) + '%'), textposition: 'outside',
      customdata: d.discount_bands.map(b => b.orders), hovertemplate: '%{x} discount<br>Margin %{y:.1f}% · %{customdata} orders<extra></extra>' }],
      { yaxis: { ticksuffix: '%', gridcolor: css('--line') }, xaxis: { title: 'Discount given' } }); } else dc.hidden = true;

    const fb = document.getElementById('fcBody'), f = d.forecast;
    fb.innerHTML = f ? `<div class="fc"><div class="d"><small>${esc(f.next_month)} sales (projected)</small><b>${fmt(f.sales.projected)}</b><small class="${f.sales.trend_per_month >= 0 ? 'up' : 'down'}">${f.sales.trend_per_month >= 0 ? '▲' : '▼'} ${fmt(Math.abs(f.sales.trend_per_month))} / month trend</small></div>
      <div class="d"><small>${esc(f.next_month)} profit (projected)</small><b>${fmt(f.profit.projected)}</b><small class="${f.profit.trend_per_month >= 0 ? 'up' : 'down'}">${f.profit.trend_per_month >= 0 ? '▲' : '▼'} ${fmt(Math.abs(f.profit.trend_per_month))} / month trend</small></div></div>
      <div class="note">Based on only ${f.history_months} months of history and a straight line — treat it as a rough direction, not a prediction.</div>`
      : '<p class="muted">Needs at least 3 months of data (after filters) to project a trend.</p>';

    const q = d.meta.quality;
    document.getElementById('quality').innerHTML = `<div class="between" style="align-items:flex-start;gap:24px"><div style="flex:1;min-width:260px">
      <h4 style="margin:0 0 4px;font-size:17px">🧹 Data quality report</h4><div class="muted">${q.rows_in} rows in → ${q.rows_out} analysed (${q.rows_removed} removed)</div>
      ${q.issues.length ? q.issues.map(i => `<div class="issue"><div class="n">${i.count}</div><div><span class="tag ${i.severity}">${i.severity}</span> <b>${esc(i.type.replace(/_/g, ' '))}</b>
        <div class="muted" style="font-size:13px">${esc(i.detail)}</div></div></div>`).join('') : '<p class="up">✅ No issues detected.</p>'}</div>
      <div class="score" style="--p:${q.quality_score}"><span>${q.quality_score}</span></div></div>`;
  }

  function drawBars() {
    const bars = (el, rows, metric) => plot(el, [{ x: rows.map(r => r[metric]), y: rows.map(r => r.name), type: 'bar', orientation: 'h',
      marker: { color: rows.map(r => r[metric] >= 0 ? COLORS.silver : COLORS.crimson) }, text: rows.map(r => fmt(r[metric])), textposition: 'outside', cliponaxis: false }],
      { yaxis: { autorange: 'reversed' }, margin: { t: 10, r: 96, b: 30, l: 96 } });
    const sorted = (rows, m) => rows.slice().sort((a, b) => b[m] - a[m]);
    bars('cProducts', sorted(D.products, state.products), state.products); bars('cRegions', sorted(D.regions, state.regions), state.regions);
  }
  document.querySelectorAll('.seg').forEach(s => s.addEventListener('click', e => { if (!e.target.dataset.m) return;
    s.querySelectorAll('button').forEach(b => b.classList.remove('on')); e.target.classList.add('on'); state[s.dataset.target] = e.target.dataset.m; drawBars(); }));
  onTheme(() => D && render());
  load();
})();
