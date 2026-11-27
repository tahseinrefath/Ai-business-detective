(async () => {
  const id = getDataset(); if (!id) { document.getElementById('empty').hidden = false; return; }
  document.getElementById('content').hidden = false; document.getElementById('expCsv').href = `/api/export/${id}/clean.csv`;
  const S = { page: 1, sort: 'order_date', dir: 'desc', q: '' }, tbl = document.getElementById('tbl');
  const COLS = [['order_date', 'Date'], ['product', 'Product'], ['category', 'Category'], ['region', 'Region'], ['quantity', 'Qty', 1], ['sales', 'Sales', 1], ['profit', 'Profit', 1], ['discount_pct', 'Discount', 1]];
  let timer;
  async function load() {
    try {
      const d = await api(`/api/preview?dataset=${id}&page=${S.page}&sort=${S.sort}&dir=${S.dir}&q=${encodeURIComponent(S.q)}&size=15`);
      const cell = (c, r) => { const v = r[c[0]]; if (v == null) return '<span class="muted">—</span>';
        if (c[0] === 'sales' || c[0] === 'profit') return `<span class="${c[0] === 'profit' && v < 0 ? 'down' : ''}">${fmt(v)}</span>`;
        if (c[0] === 'discount_pct') return v.toFixed(1) + '%'; return esc(v); };
      tbl.innerHTML = '<tr>' + COLS.map(c => `<th data-s="${c[0]}" class="${c[2] ? 'num' : ''}">${c[1]}${S.sort === c[0] ? (S.dir === 'asc' ? ' ▲' : ' ▼') : ''}</th>`).join('') + '</tr>' +
        (d.rows.length ? d.rows.map(r => '<tr>' + COLS.map(c => `<td class="${c[2] ? 'num' : ''}">${cell(c, r)}</td>`).join('') + '</tr>').join('') : '<tr><td colspan="8" class="muted">No rows match.</td></tr>');
      document.getElementById('total').textContent = `${d.total.toLocaleString('en-IN')} rows`; document.getElementById('pg').textContent = `Page ${d.page} of ${d.pages}`;
      document.getElementById('prev').disabled = d.page <= 1; document.getElementById('next').disabled = d.page >= d.pages;
    } catch (e) { toast(e.message, true); }
  }
  tbl.onclick = e => { const s = e.target.dataset.s; if (!s) return; S.dir = S.sort === s && S.dir === 'desc' ? 'asc' : 'desc'; S.sort = s; S.page = 1; load(); };
  document.getElementById('prev').onclick = () => { S.page--; load(); }; document.getElementById('next').onclick = () => { S.page++; load(); };
  document.getElementById('search').oninput = e => { clearTimeout(timer); timer = setTimeout(() => { S.q = e.target.value; S.page = 1; load(); }, 250); };
  load();
})();
