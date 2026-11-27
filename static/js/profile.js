const $ = id => document.getElementById(id);
const show = (box, msg) => { box.textContent = msg || ''; box.hidden = !msg; };
let ME = null;

function avatarHTML(u) { return u.has_avatar ? `<img src="/avatar/me?v=${u.avatar_v}" alt="Your profile picture">` : esc(initials(u.name)); }
const initials = n => (n.split(/\s+/).filter(Boolean).slice(0, 2).map(p => p[0]).join('') || '?').toUpperCase();

function paint(u, stats) {
  ME = u;
  $('bigAvatar').innerHTML = avatarHTML(u); $('rmBtn').hidden = !u.has_avatar;
  const nav = document.querySelector('.usermenu .avatar'); if (nav) nav.innerHTML = avatarHTML(u);        // keep the nav avatar in sync
  $('pName').textContent = u.name; $('pRole').textContent = [u.job_title, u.company].filter(Boolean).join(' · ') || 'Add your job title';
  $('pMeta').textContent = [u.location, 'Member since ' + (u.created_at || '').slice(0, 10)].filter(Boolean).join(' · ');
  $('f_name').value = u.name; $('f_email').value = u.email; $('f_job').value = u.job_title; $('f_company').value = u.company; $('f_loc').value = u.location; $('f_bio').value = u.bio;
  $('bioCount').textContent = u.bio.length + ' / 300';
  if (stats) {
    $('rankTitle').textContent = '🕵️ ' + stats.title; $('rankLvl').textContent = 'Lv ' + stats.level;
    $('xpFill').style.width = (stats.xp_into_level / stats.xp_per_level * 100) + '%'; $('xpTxt').textContent = `${stats.xp} XP · ${stats.xp_per_level - stats.xp_into_level} XP to level ${stats.level + 1}`;
    $('badges').innerHTML = stats.badges.map(b => `<div class="badge ${b.earned ? 'on' : ''}" title="${esc(b.how)}"><span>${b.icon}</span>${esc(b.name)}</div>`).join('');
  }
}
async function load() { const r = await api('/api/profile'); paint(r.user, r.stats); }

/* ---- avatar ---- */
async function sendAvatar(file) {
  if (!file) return;
  if (!/^image\/(png|jpeg|webp|gif)$/.test(file.type)) return toast('Please choose a PNG, JPG, WEBP or GIF image.', true);
  if (file.size > 3 * 1024 * 1024) return toast('That image is over 3 MB.', true);
  const url = URL.createObjectURL(file); $('bigAvatar').innerHTML = `<img src="${url}" alt="">`;   // instant preview
  const fd = new FormData(); fd.append('avatar', file);
  try { const r = await api('/api/profile/avatar', { method: 'POST', body: fd }); await load(); toast('Profile picture updated ✅'); }
  catch (e) { await load(); toast(e.message, true); }
  URL.revokeObjectURL(url);
}
$('pickBtn').onclick = () => $('avatarFile').click();
$('avatarFile').onchange = e => { sendAvatar(e.target.files[0]); e.target.value = ''; };
const drop = $('drop');
['dragenter', 'dragover'].forEach(ev => drop.addEventListener(ev, e => { e.preventDefault(); drop.classList.add('over'); }));
['dragleave', 'drop'].forEach(ev => drop.addEventListener(ev, e => { e.preventDefault(); drop.classList.remove('over'); }));
drop.addEventListener('drop', e => sendAvatar(e.dataTransfer.files[0]));
$('rmBtn').onclick = async () => { try { await api('/api/profile/avatar', { method: 'DELETE' }); await load(); toast('Picture removed'); } catch (e) { toast(e.message, true); } };

/* ---- details ---- */
$('f_bio').oninput = e => $('bioCount').textContent = e.target.value.length + ' / 300';
$('profForm').onsubmit = async e => {
  e.preventDefault(); show($('profErr'), '');
  try { const r = await api('/api/profile', { method: 'PUT', body: { name: $('f_name').value, job_title: $('f_job').value, company: $('f_company').value, location: $('f_loc').value, bio: $('f_bio').value } });
    paint(r.user); document.querySelector('.menu .who b').textContent = r.user.name; toast('Profile saved ✅'); }
  catch (err) { show($('profErr'), err.message); }
};

/* ---- password ---- */
$('pwForm').onsubmit = async e => {
  e.preventDefault(); show($('pwErr'), '');
  if ($('pw_new').value !== $('pw_new2').value) return show($('pwErr'), 'The new passwords do not match.');
  try { await api('/api/profile/password', { method: 'POST', body: { current: $('pw_cur').value, new: $('pw_new').value } });
    e.target.reset(); toast('Password updated ✅'); }
  catch (err) { show($('pwErr'), err.message); }
};

/* ---- delete account ---- */
const modal = $('delModal'); const closeModal = () => { modal.classList.remove('open'); $('del_pw').value = ''; show($('delErr'), ''); };
$('delBtn').onclick = () => { modal.classList.add('open'); setTimeout(() => $('del_pw').focus(), 40); };
$('delCancel').onclick = closeModal; modal.onclick = e => { if (e.target === modal) closeModal(); };
addEventListener('keydown', e => { if (e.key === 'Escape') closeModal(); });
$('delGo').onclick = async () => {
  try { await api('/api/profile/delete', { method: 'POST', body: { password: $('del_pw').value } });
    Object.keys(localStorage).filter(k => k.startsWith('abd_dataset')).forEach(k => localStorage.removeItem(k)); location.href = '/'; }
  catch (err) { show($('delErr'), err.message); }
};
load().catch(e => toast(e.message, true));
