const form = document.getElementById('authForm'), errBox = document.getElementById('formErr'), btn = document.getElementById('submitBtn');
const mode = form.dataset.mode, pw = document.getElementById('password');
const showErr = m => { errBox.textContent = m; errBox.hidden = !m; };

document.getElementById('eye').onclick = e => { const show = pw.type === 'password'; pw.type = show ? 'text' : 'password';
  const p2 = document.getElementById('password2'); if (p2) p2.type = pw.type; e.currentTarget.textContent = show ? '🙈' : '👁'; e.currentTarget.setAttribute('aria-label', show ? 'Hide password' : 'Show password'); };

if (mode === 'register') {
  const bar = document.getElementById('meterBar'), txt = document.getElementById('meterTxt');
  pw.addEventListener('input', () => {
    const v = pw.value; let score = 0;
    if (v.length >= 8) score++; if (v.length >= 12) score++; if (/[A-Za-z]/.test(v) && /\d/.test(v)) score++; if (/[^A-Za-z0-9]/.test(v) || (/[a-z]/.test(v) && /[A-Z]/.test(v))) score++;
    const labels = ['Too weak', 'Weak', 'Okay', 'Good', 'Strong'], colors = ['#ff1a40', '#ff1a40', '#8a9098', '#c9cdd3', '#f2f4f7'];
    bar.style.width = (v ? (score + 1) * 20 : 0) + '%'; bar.style.background = colors[score];
    txt.textContent = v ? labels[score] + (score < 3 ? ' — add length, a number or a symbol' : '') : 'Use 8+ characters with letters and numbers.';
  });
}

form.addEventListener('submit', async e => {
  e.preventDefault(); showErr('');
  const email = form.email.value.trim(), password = pw.value, body = { email, password, next: form.dataset.next };
  if (!email || !password) return showErr('Please fill in your email and password.');
  if (mode === 'register') {
    body.name = form.name.value.trim();
    if (body.name.length < 2) return showErr('Please enter your name (at least 2 characters).');
    if (password !== document.getElementById('password2').value) return showErr('The two passwords do not match.');
  }
  btn.disabled = true; const label = btn.textContent; btn.textContent = mode === 'login' ? 'Signing in…' : 'Creating account…';
  try { const r = await api('/api/auth/' + mode, { method: 'POST', body }); location.href = r.next || '/dashboard'; }
  catch (err) { showErr(err.message); btn.disabled = false; btn.textContent = label; }
});
