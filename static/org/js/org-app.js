// ── Org Explorer: shared state, API client and view router ─────────────────
const OrgApp = (() => {

  const API = {
    async req(method, path, body) {
      const opts = { method, headers: {} };
      if (body instanceof FormData) {
        opts.body = body;
      } else if (body) {
        opts.headers['Content-Type'] = 'application/json';
        opts.body = JSON.stringify(body);
      }
      const res = await fetch(path, opts);
      if (res.status === 204) return null;
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(detailText(data.detail) || `Request failed (${res.status})`);
      return data;
    },
    get:    (p)    => API.req('GET', p),
    post:   (p, b) => API.req('POST', p, b),
    put:    (p, b) => API.req('PUT', p, b),
    del:    (p)    => API.req('DELETE', p),
  };

  function detailText(detail) {
    if (!detail) return '';
    if (Array.isArray(detail)) return detail.map(d => d.msg || d.message || d).join(', ');
    return typeof detail === 'string' ? detail : JSON.stringify(detail);
  }

  // ── State ────────────────────────────────────────────────────────────────
  const state = {
    datasetId: null,
    datasets: [],
    view: 'chart',
    filters: { search: '', function: 'All', department: 'All', job_level: 'All',
               location: 'All', vacancy: 'All' },
    summary: null,      // cached summary for the current dataset + filters
    dimensions: [],
    rootId: null,       // chart drill-down root
    colorBy: 'function',
    orientation: 'vertical',
    compact: true,
    collapsed: new Set(),
    selectedId: null,
  };

  const FILTER_KEYS = ['function', 'department', 'job_level', 'location', 'vacancy'];

  // ── Formatting ───────────────────────────────────────────────────────────
  const Fmt = {
    int(v)  { return v == null ? '—' : Number(v).toLocaleString('en-US'); },
    num(v, d = 1) { return v == null ? '—' : Number(v).toLocaleString('en-US', { minimumFractionDigits: d, maximumFractionDigits: d }); },
    pct(v)  { return v == null ? '—' : Number(v).toFixed(1) + '%'; },
    text(v) { return v == null || v === '' ? '—' : String(v); },
    esc(v)  {
      return String(v == null ? '' : v)
        .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
    },
    initials(name) {
      return String(name || '?').trim().split(/\s+/).slice(0, 2)
        .map(w => w[0]).join('').toUpperCase();
    },
  };

  // Categorical palette — stable per value so colours don't shuffle on re-render.
  const PALETTE = ['#6366f1', '#22c55e', '#f59e0b', '#06b6d4', '#ec4899', '#a855f7',
                   '#84cc16', '#f97316', '#14b8a6', '#eab308', '#3b82f6', '#ef4444',
                   '#8b5cf6', '#10b981', '#f472b6', '#0ea5e9'];
  const MUTED = '#55607a';

  function colorFor(value, allValues) {
    if (!value || value === 'Unspecified') return MUTED;
    const i = allValues.indexOf(value);
    return i < 0 ? MUTED : PALETTE[i % PALETTE.length];
  }

  // ── Query string ─────────────────────────────────────────────────────────
  function query(extra = {}) {
    const p = new URLSearchParams();
    if (state.datasetId) p.set('dataset_id', state.datasetId);
    if (state.filters.search) p.set('search', state.filters.search);
    FILTER_KEYS.forEach(k => {
      const v = state.filters[k];
      if (v && v !== 'All') p.set(k, v);
    });
    Object.entries(extra).forEach(([k, v]) => { if (v != null && v !== '') p.set(k, v); });
    const s = p.toString();
    return s ? '?' + s : '';
  }

  function activeFilterCount() {
    let n = state.filters.search ? 1 : 0;
    FILTER_KEYS.forEach(k => { if (state.filters[k] && state.filters[k] !== 'All') n++; });
    return n;
  }

  // ── Toast ────────────────────────────────────────────────────────────────
  let toastTimer = null;
  function toast(msg, kind = '') {
    const el = document.getElementById('toast');
    el.textContent = msg;
    el.className = 'toast ' + kind;
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => el.classList.add('hidden'), 3600);
  }

  // ── Drawer ───────────────────────────────────────────────────────────────
  function openDrawer(title, html) {
    document.getElementById('drawer-title').textContent = title;
    document.getElementById('drawer-body').innerHTML = html;
    document.getElementById('drawer').classList.remove('hidden');
    document.getElementById('drawer-overlay').classList.remove('hidden');
  }

  function closeDrawer() {
    document.getElementById('drawer').classList.add('hidden');
    document.getElementById('drawer-overlay').classList.add('hidden');
  }

  async function showEmployee(employeeId) {
    state.selectedId = employeeId;
    if (state.view === 'chart' && OrgApp.refreshChartSelection) OrgApp.refreshChartSelection();
    openDrawer('Loading…', '<div class="loading">Loading…</div>');
    try {
      const e = await API.get(`/api/org/employees/${encodeURIComponent(employeeId)}${query()}`);
      openDrawer(e.name || e.employee_id, renderEmployee(e));
    } catch (err) {
      openDrawer('Error', `<div class="alert alert-error">${Fmt.esc(err.message)}</div>`);
    }
  }

  function renderEmployee(e) {
    const chain = (e.chain || []).map(c =>
      `<a data-focus="${Fmt.esc(c.employee_id)}">${Fmt.esc(c.name || c.employee_id)}</a>`
    ).join('<span class="sep">›</span>');

    const item = (k, v) => `<div class="detail-item"><div class="k">${k}</div><div class="v">${Fmt.esc(v ?? '—')}</div></div>`;

    const reports = (e.reports || []).map(r => `
      <div class="report-item" data-employee="${Fmt.esc(r.employee_id)}">
        <div>
          <div>${Fmt.esc(r.name)}</div>
          <div class="sub">${Fmt.esc(r.job_title || '—')}</div>
        </div>
        <span class="badge${r.total_headcount > 1 ? ' badge-primary' : ''}">${Fmt.int(r.total_headcount)}</span>
      </div>`).join('');

    const extras = Object.entries(e.extra || {}).map(([k, v]) => item(Fmt.esc(k), v)).join('');

    return `
      <div>
        <div class="chip-row" style="margin-bottom:8px">
          <span class="badge ${e.is_vacant ? 'badge-vacant' : 'badge-filled'}">${e.is_vacant ? 'Vacant' : 'Filled'}</span>
          ${e.job_level ? `<span class="badge badge-primary">${Fmt.esc(e.job_level)}</span>` : ''}
          <span class="badge">Layer ${e.level_no}</span>
          ${e.is_manager ? '<span class="badge">Manager</span>' : '<span class="badge">IC</span>'}
        </div>
        <div style="font-size:0.95rem">${Fmt.esc(e.job_title || '—')}</div>
        ${chain ? `<div class="breadcrumb" style="margin-top:8px">${chain}</div>` : ''}
      </div>

      <div class="grid grid-kpi" style="gap:10px">
        <div class="kpi"><div class="kpi-label">Total headcount</div><div class="kpi-value">${Fmt.int(e.total_headcount)}</div><div class="kpi-sub">incl. this position</div></div>
        <div class="kpi"><div class="kpi-label">Direct reports</div><div class="kpi-value">${Fmt.int(e.direct_reports)}</div><div class="kpi-sub">${Fmt.int(e.sub_managers)} managers below</div></div>
        <div class="kpi"><div class="kpi-label">Org FTE</div><div class="kpi-value">${Fmt.num(e.total_fte, 1)}</div><div class="kpi-sub">${Fmt.int(e.total_vacant)} vacant</div></div>
        <div class="kpi"><div class="kpi-label">Depth below</div><div class="kpi-value">${Fmt.int(e.subtree_depth)}</div><div class="kpi-sub">layers</div></div>
      </div>

      <div class="card">
        <h3 class="card-title">Job &amp; function</h3>
        <div class="detail-grid">
          ${item('Employee ID', e.employee_id)}
          ${item('Job code', e.job_code)}
          ${item('Job family', e.job_family)}
          ${item('Job level', e.job_level)}
          ${item('Function', e.function)}
          ${item('Department', e.department)}
          ${item('Division', e.division)}
          ${item('Location', e.location)}
          ${item('Employment type', e.employment_type)}
          ${item('FTE', e.fte)}
          ${item('Cost center', e.cost_center)}
          ${item('Email', e.email)}
          ${item('Hire date', e.hire_date)}
          ${extras}
        </div>
      </div>

      ${reports ? `<div class="card"><h3 class="card-title">Direct reports (${e.reports.length})</h3><div class="report-list">${reports}</div></div>` : ''}

      <div class="modal-actions">
        <button class="btn btn-primary" data-focus="${Fmt.esc(e.employee_id)}">Focus this branch</button>
      </div>`;
  }

  // ── Filter controls ──────────────────────────────────────────────────────
  function fillFilterOptions(summary) {
    FILTER_KEYS.filter(k => k !== 'vacancy').forEach(key => {
      const sel = document.getElementById('f-' + key);
      if (!sel) return;
      const values = (summary?.breakdowns?.[key] || [])
        .map(b => b.value)
        .sort((a, b) => a.localeCompare(b));
      const current = state.filters[key];
      sel.innerHTML = ['<option value="All">All</option>']
        .concat(values.map(v => `<option value="${Fmt.esc(v)}">${Fmt.esc(v)}</option>`)).join('');
      sel.value = values.includes(current) ? current : 'All';
      state.filters[key] = sel.value;
    });
    document.getElementById('f-vacancy').value = state.filters.vacancy;
    document.getElementById('f-search').value = state.filters.search;
  }

  function updateFilterSummary() {
    const el = document.getElementById('filter-summary');
    const s = state.summary;
    if (!s) { el.textContent = ''; return; }
    const n = activeFilterCount();
    el.textContent = `${Fmt.int(s.headcount)} positions · ${Fmt.num(s.total_fte, 1)} FTE · ${s.layers} layers`
      + (n ? ` · ${n} filter${n > 1 ? 's' : ''} active` : '');
  }

  // ── Data loading ─────────────────────────────────────────────────────────
  async function refreshSummary() {
    state.summary = await API.get('/api/org/summary' + query());
    return state.summary;
  }

  async function loadDatasets() {
    state.datasets = await API.get('/api/org/datasets');
    const sel = document.getElementById('dataset-select');
    if (!state.datasets.length) {
      sel.innerHTML = '<option>No data</option>';
      state.datasetId = null;
      return;
    }
    if (!state.datasets.some(d => d.id === state.datasetId)) {
      state.datasetId = state.datasets[0].id;
    }
    sel.innerHTML = state.datasets.map(d =>
      `<option value="${d.id}">${Fmt.esc(d.name)} · ${Fmt.int(d.row_count)}</option>`).join('');
    sel.value = state.datasetId;
  }

  // ── Views ────────────────────────────────────────────────────────────────
  const views = {};
  function registerView(id, mod) { views[id] = mod; }

  async function render() {
    const content = document.getElementById('content');
    document.querySelectorAll('.tab').forEach(t =>
      t.classList.toggle('active', t.dataset.view === state.view));

    if (!state.datasetId) { renderEmptyState(content); return; }

    content.classList.toggle('flush', state.view === 'chart');
    content.innerHTML = '<div class="loading">Loading…</div>';

    try {
      await refreshSummary();
      fillFilterOptions(state.summary);
      updateFilterSummary();
      updateIssueBadge();

      if (!state.summary.headcount) {
        content.innerHTML = `<div class="empty"><h2>No positions match these filters</h2>
          <p>Loosen the filters to bring people back into view.</p>
          <button class="btn btn-primary" onclick="OrgApp.resetFilters()">Reset filters</button></div>`;
        return;
      }

      const mod = views[state.view];
      content.innerHTML = mod.render ? mod.render(state.summary) : '';
      if (mod.init) await mod.init(state.summary);
    } catch (err) {
      content.innerHTML = `<div class="alert alert-error">${Fmt.esc(err.message)}</div>`;
      console.error(err);
    }
  }

  function renderEmptyState(content) {
    content.classList.remove('flush');
    content.innerHTML = `
      <div class="empty">
        <h2>Drop in an org file to get started</h2>
        <p>Upload a CSV, Excel or JSON export of your people data — the columns are
           detected automatically and you can remap anything that lands in the wrong place.</p>
        <div class="modal-actions" style="justify-content:center">
          <button class="btn btn-primary" onclick="OrgApp.openImport()">⬆ Upload file</button>
          <a class="btn btn-ghost" href="/api/org/template.csv">Download template</a>
        </div>
      </div>`;
    document.getElementById('filter-summary').textContent = '';
  }

  function updateIssueBadge() {
    const badge = document.getElementById('issue-badge');
    const n = (state.summary?.issues || []).length;
    badge.textContent = n;
    badge.classList.toggle('hidden', n === 0);
  }

  function setView(view) {
    state.view = view;
    render();
  }

  function setFilter(key, value) {
    state.filters[key] = value;
    resetTreeView();
    render();
  }

  // Filters change which people are in the tree, so any remembered collapse
  // state belongs to a tree that no longer exists.
  function resetTreeView() {
    state.rootId = null;
    state.collapsed.clear();
  }

  function resetFilters() {
    state.filters = { search: '', function: 'All', department: 'All', job_level: 'All',
                      location: 'All', vacancy: 'All' };
    resetTreeView();
    render();
  }

  function debounce(fn, ms) {
    let t;
    return (...args) => { clearTimeout(t); t = setTimeout(() => fn(...args), ms); };
  }

  // ── Wiring ───────────────────────────────────────────────────────────────
  function wire() {
    document.querySelectorAll('.tab').forEach(tab =>
      tab.addEventListener('click', () => setView(tab.dataset.view)));

    FILTER_KEYS.forEach(key => {
      const el = document.getElementById('f-' + key);
      el.addEventListener('change', () => setFilter(key, el.value));
    });

    document.getElementById('f-search').addEventListener('input',
      debounce(e => setFilter('search', e.target.value.trim()), 320));

    document.getElementById('btn-reset').addEventListener('click', resetFilters);

    document.getElementById('dataset-select').addEventListener('change', e => {
      state.datasetId = parseInt(e.target.value, 10);
      resetTreeView();
      render();
    });

    document.getElementById('btn-upload').addEventListener('click', openImport);
    document.getElementById('btn-export').addEventListener('click', () => {
      if (!state.datasetId) return toast('Upload a file first', 'error');
      window.location.href = '/api/org/export/csv' + query();
    });

    document.getElementById('drawer-close').addEventListener('click', closeDrawer);
    document.getElementById('drawer-overlay').addEventListener('click', closeDrawer);
    document.addEventListener('keydown', e => { if (e.key === 'Escape') closeDrawer(); });

    // Delegated: drill into a branch, or open another person's card.
    document.addEventListener('click', e => {
      const focus = e.target.closest('[data-focus]');
      if (focus) {
        state.collapsed.clear();
        state.rootId = focus.dataset.focus;
        state.view = 'chart';
        closeDrawer();
        render();
        return;
      }
      const person = e.target.closest('[data-employee]');
      if (person) showEmployee(person.dataset.employee);
    });
  }

  function openImport() { OrgImport.open(); }

  async function boot() {
    if (typeof Chart !== 'undefined') {
      Chart.defaults.color = '#55607a';
      Chart.defaults.borderColor = '#2a2a45';
      Chart.defaults.font.family = "system-ui,-apple-system,'Segoe UI',Helvetica,Arial,sans-serif";
      Chart.defaults.font.size = 11;
      Chart.defaults.plugins.legend.labels.boxWidth = 10;
    }
    wire();
    try {
      const meta = await API.get('/api/org/fields');
      state.dimensions = meta.dimensions;
    } catch { /* falls back to hardcoded dimension list in the views */ }
    await loadDatasets();
    await render();
  }

  return { API, Fmt, state, boot, render, setView, setFilter, resetFilters, query, toast,
           loadDatasets, showEmployee, openDrawer, closeDrawer, registerView,
           colorFor, openImport, PALETTE, MUTED, activeFilterCount, debounce };
})();
