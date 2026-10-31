const drop = document.getElementById('drop'), fileInput = document.getElementById('file'), msg = document.getElementById('uploadMsg');
const FIELDS = [
  ['order_date', 'Date of sale', true], ['sales', 'Sales amount', true], ['profit', 'Profit', false], ['product', 'Product / item', false],
  ['category', 'Category', false], ['region', 'Region / city / store', false], ['quantity', 'Quantity / units', false], ['discount_pct', 'Discount %', false]];

function success({ dataset, source_note }) {
  setDataset(dataset.id, dataset.filename);
  const q = dataset.quality;
  msg.innerHTML = `<div class="card fade" style="background:rgba(201,205,211,.06)">✅ <b>${esc(dataset.filename)}</b> loaded — ${q.rows_in} rows in, ${q.rows_out} analysed,
    quality score <b>${q.quality_score}/100</b>${q.issues.length ? ` · ${q.issues.length} issue type(s) handled` : ''}.
    ${source_note ? `<div class="muted" style="font-size:13px;margin-top:4px">📎 ${esc(source_note)}</div>` : ''}
    <div class="row" style="margin-top:12px"><a class="btn sm" href="/dashboard">📊 Open dashboard</a><a class="btn sm ghost" href="/investigation">🔍 Investigate</a></div></div>`;
}

async function ingest(promise) {
  msg.innerHTML = '<div class="skel" style="width:60%"></div>';
  try { success(await promise); }
  catch (e) {
    msg.innerHTML = '';
    if (e.data && e.data.needs_mapping) return showMapping(e.data);
    toast(e.message, true);
    msg.innerHTML = `<div class="warnbox">⚠ ${esc(e.message)}</div>`;
  }
}

function showMapping(d) {
  const opts = sel => '<option value="">— none —</option>' + d.columns.map(c => `<option value="${esc(c)}" ${c === sel ? 'selected' : ''}>${esc(c)}</option>`).join('');
  msg.innerHTML = `<div class="card glow fade">
    <h3 style="margin:0 0 4px">🧭 Help me read your columns</h3>
    <p class="muted" style="margin:0 0 14px">I couldn't recognise the column names in <b>${esc(d.filename)}</b>. I've guessed below — please check, then continue. <b>Date</b> and <b>Sales</b> are required.</p>
    <div class="tablewrap" style="margin-bottom:16px"><table class="t"><tr>${d.columns.map(c => `<th>${esc(c)}</th>`).join('')}</tr>
      ${d.preview.map(r => `<tr>${d.columns.map(c => `<td>${esc(r[c])}</td>`).join('')}</tr>`).join('')}</table></div>
    <div class="grid g4" id="mapGrid">${FIELDS.map(([k, label, req]) => `<label class="maplab">${esc(label)} ${req ? '<span class="down">*</span>' : ''}
      <select data-k="${k}">${opts(d.suggestions[k])}</select></label>`).join('')}</div>
    <div class="row" style="margin-top:18px"><button class="btn" id="mapGo">✅ Use these columns</button><button class="btn ghost" id="mapCancel">Cancel</button></div></div>`;
  document.getElementById('mapCancel').onclick = () => msg.innerHTML = '';
  document.getElementById('mapGo').onclick = () => {
    const mapping = {}; document.querySelectorAll('#mapGrid select').forEach(s => { if (s.value) mapping[s.dataset.k] = s.value; });
    if (!mapping.order_date || !mapping.sales) return toast('Please choose the Date and Sales columns.', true);
    ingest(api('/api/upload/map', { method: 'POST', body: { token: d.token, filename: d.filename, mapping } }));
  };
}

const sample = kind => ingest(api('/api/sample', { method: 'POST', body: { kind } }));
const upload = f => { const fd = new FormData(); fd.append('file', f); return ingest(api('/api/upload', { method: 'POST', body: fd })); };

document.getElementById('btnSample').onclick = () => sample('clean');
document.getElementById('btnDirty').onclick = () => sample('dirty');
drop.onclick = () => fileInput.click();
fileInput.onchange = () => { if (fileInput.files[0]) { upload(fileInput.files[0]); fileInput.value = ''; } };
['dragover', 'dragenter'].forEach(e => drop.addEventListener(e, ev => { ev.preventDefault(); drop.classList.add('over'); }));
['dragleave', 'drop'].forEach(e => drop.addEventListener(e, ev => { ev.preventDefault(); drop.classList.remove('over'); }));
drop.addEventListener('drop', e => e.dataTransfer.files[0] && upload(e.dataTransfer.files[0]));
