// ── API client ────────────────────────────────────────────────────────────
const API = {
  async req(method, path, body = null) {
    const opts = { method, headers: {} };
    if (body) { opts.headers['Content-Type'] = 'application/json'; opts.body = JSON.stringify(body); }
    const res = await fetch(path, opts);
    if (res.status === 204) return null;
    const data = await res.json();
    if (!res.ok) throw { status: res.status, detail: data.detail || 'Request failed' };
    return data;
  },
  get:    (p)    => API.req('GET', p),
  post:   (p, b) => API.req('POST', p, b),
  put:    (p, b) => API.req('PUT', p, b),
  delete: (p)    => API.req('DELETE', p),
};

// ── Formatters ────────────────────────────────────────────────────────────
const Fmt = {
  usd(v, sign = true) {
    if (v == null) return '—';
    const s = '$' + Math.abs(v).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    if (!sign) return (v < 0 ? '-' : '') + s;
    return (v >= 0 ? '+' : '-') + s;
  },
  sar(v, rate) {
    return 'SAR ' + (Math.abs(v) * rate).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  },
  pct(v)    { return (v >= 0 ? '+' : '') + v.toFixed(2) + '%'; },
  pct1(v)   { return v.toFixed(1) + '%'; },
  num(v, d=2) { return v == null ? '—' : v.toLocaleString('en-US', { minimumFractionDigits: d, maximumFractionDigits: d }); },
  cls(v)    { return v > 0 ? 'text-green' : v < 0 ? 'text-red' : ''; },
  dir(d)    { return `<span class="badge badge-${d.toLowerCase()}">${d}</span>`; },
  type(t)   { return `<span class="badge badge-type">${t}</span>`; },
  date(s)   { return s ? s.substring(0, 10) : '—'; },
  inf(v)    { return v == null ? '∞' : Fmt.num(v); },
};

// ── Global SAR rate ───────────────────────────────────────────────────────
let sarRate = 3.75;
API.get('/api/settings').then(s => { sarRate = s.usd_sar_rate; }).catch(() => {});

// ── Query builder ─────────────────────────────────────────────────────────
function buildQuery(params) {
  const p = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => { if (v) p.append(k, v); });
  const s = p.toString();
  return s ? '?' + s : '';
}

// ── Router ────────────────────────────────────────────────────────────────
const pages = {};
let currentTradeId = null;

function registerPage(id, mod) { pages[id] = mod; }

async function navigate(raw) {
  const hash = raw || 'dashboard';

  // Parameterised routes
  const detailMatch = hash.match(/^trade-(\d+)$/);
  if (detailMatch) {
    currentTradeId = parseInt(detailMatch[1]);
    await loadPage('trade-detail');
    return;
  }
  const editMatch = hash.match(/^edit-(\d+)$/);
  if (editMatch) {
    currentTradeId = parseInt(editMatch[1]);
    await loadPage('add-trade');
    return;
  }

  currentTradeId = null;
  await loadPage(hash);
}

async function loadPage(id) {
  const mod = pages[id];
  if (!mod) return;

  document.querySelectorAll('.nav-item').forEach(a =>
    a.classList.toggle('active', a.dataset.page === id)
  );

  const titles = {
    'dashboard': 'Dashboard', 'add-trade': 'Add Trade', 'history': 'Trade History',
    'analytics': 'Analytics', 'reports': 'Reports', 'settings': 'Settings', 'trade-detail': 'Trade Detail',
  };
  document.getElementById('page-title').textContent = titles[id] || id;

  // Destroy all Chart.js instances before re-rendering
  Object.values(Chart.instances || {}).forEach(c => c.destroy());

  const content = document.getElementById('content');
  content.innerHTML = '<div class="loading">Loading…</div>';

  try {
    content.innerHTML = mod.render ? mod.render() : '';
    if (mod.init) await mod.init();
  } catch (e) {
    const msg = Array.isArray(e.detail)
      ? e.detail.map(d => d.msg || d).join(', ')
      : (e.detail || e.message || String(e));
    content.innerHTML = `<div class="alert alert-error">Failed to load: ${msg}</div>`;
    console.error(e);
  }
  closeSidebar();
}

window.addEventListener('hashchange', () => navigate(window.location.hash.slice(1)));

// ── Sidebar ───────────────────────────────────────────────────────────────
const sidebar = document.getElementById('sidebar');
const overlay = document.getElementById('overlay');
const openSidebar  = () => { sidebar.classList.add('open');    overlay.classList.remove('hidden'); };
const closeSidebar = () => { sidebar.classList.remove('open'); overlay.classList.add('hidden'); };
document.getElementById('menu-btn').addEventListener('click', openSidebar);
document.getElementById('sidebar-close').addEventListener('click', closeSidebar);
overlay.addEventListener('click', closeSidebar);

// ── Confirm modal ─────────────────────────────────────────────────────────
function showModal(msg, onConfirm) {
  const modal = document.getElementById('modal');
  document.getElementById('modal-msg').textContent = msg;
  modal.classList.remove('hidden');

  const ok  = document.getElementById('modal-confirm');
  const no  = document.getElementById('modal-cancel');

  const cleanup = () => {
    modal.classList.add('hidden');
    ok.replaceWith(ok.cloneNode(true));
    no.replaceWith(no.cloneNode(true));
  };
  document.getElementById('modal-confirm').addEventListener('click', () => { cleanup(); onConfirm(); });
  document.getElementById('modal-cancel').addEventListener('click', cleanup);
}

// ── Chart.js defaults ─────────────────────────────────────────────────────
if (typeof Chart !== 'undefined') {
  Chart.defaults.color          = '#55607a';
  Chart.defaults.borderColor    = '#2a2a45';
  Chart.defaults.font.family    = "system-ui,-apple-system,'Segoe UI',Helvetica,Arial,sans-serif";
  Chart.defaults.font.size      = 12;
}

// ── Boot ──────────────────────────────────────────────────────────────────
window.addEventListener('DOMContentLoaded', () => navigate(window.location.hash.slice(1)));
