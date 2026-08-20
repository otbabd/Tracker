// ── Import: upload a file, review the detected columns, commit ─────────────
const OrgImport = (() => {
  const { API, Fmt, toast } = OrgApp;

  let fields = [];     // [{key, label, required}]
  let pending = null;  // { file, headers, sample, mapping, row_count }

  const modal = () => document.getElementById('import-modal');
  const body  = () => document.getElementById('import-body');

  async function open() {
    modal().classList.remove('hidden');
    if (!fields.length) {
      try {
        fields = (await API.get('/api/org/fields')).fields;
      } catch (e) {
        body().innerHTML = `<div class="alert alert-error">${Fmt.esc(e.message)}</div>`;
        return;
      }
    }
    renderDrop();
  }

  function close() {
    modal().classList.add('hidden');
    pending = null;
  }

  // ── Step 1: pick a file ──────────────────────────────────────────────────
  function renderDrop() {
    body().innerHTML = `
      <div class="dropzone" id="dropzone">
        <div class="big">📄</div>
        <div><strong>Drop your org file here</strong> or click to browse</div>
        <div class="text-muted" style="font-size:0.8rem;margin-top:6px">
          CSV, TSV, Excel (.xlsx/.xls) or JSON · up to 25 MB
        </div>
      </div>
      <div class="text-muted" style="font-size:0.8rem">
        Needs one row per position with an ID column and a manager-ID column to link the
        hierarchy. Job title, function, level, location, status and FTE are picked up when present.
        <a href="/api/org/template.csv" style="color:#a5b4fc">Download a template</a>.
      </div>
      <input type="file" id="file-input" class="hidden" accept=".csv,.tsv,.tab,.txt,.xlsx,.xlsm,.xls,.json">
      <div id="import-status"></div>`;

    const zone = document.getElementById('dropzone');
    const input = document.getElementById('file-input');

    zone.addEventListener('click', () => input.click());
    input.addEventListener('change', () => input.files[0] && preview(input.files[0]));
    ['dragenter', 'dragover'].forEach(t => zone.addEventListener(t, e => {
      e.preventDefault(); zone.classList.add('over');
    }));
    ['dragleave', 'drop'].forEach(t => zone.addEventListener(t, e => {
      e.preventDefault(); zone.classList.remove('over');
    }));
    zone.addEventListener('drop', e => {
      const file = e.dataTransfer.files[0];
      if (file) preview(file);
    });
  }

  // ── Step 2: confirm the column mapping ───────────────────────────────────
  async function preview(file) {
    const status = document.getElementById('import-status');
    status.innerHTML = '<div class="loading">Reading file…</div>';
    try {
      const fd = new FormData();
      fd.append('file', file);
      const res = await API.post('/api/org/preview', fd);
      pending = { file, ...res };
      renderMapping();
    } catch (e) {
      status.innerHTML = `<div class="alert alert-error">${Fmt.esc(e.message)}</div>`;
    }
  }

  function renderMapping() {
    const { headers, sample, mapping, row_count, file } = pending;
    const defaultName = (file.name || 'Org snapshot').replace(/\.[^.]+$/, '');

    const options = h => headers.map(x =>
      `<option value="${Fmt.esc(x)}"${x === h ? ' selected' : ''}>${Fmt.esc(x)}</option>`).join('');

    const rows = fields.map(f => `
      <div class="map-row">
        <label for="map-${f.key}">${Fmt.esc(f.label)}${f.required ? ' <span class="req">*</span>' : ''}</label>
        <select id="map-${f.key}" data-field="${f.key}" class="${mapping[f.key] ? '' : 'unset'}">
          <option value="">— not in file —</option>
          ${options(mapping[f.key] || null)}
        </select>
      </div>`).join('');

    const previewTable = `
      <div class="preview-wrap">
        <table>
          <thead><tr>${headers.map(h => `<th>${Fmt.esc(h)}</th>`).join('')}</tr></thead>
          <tbody>${sample.map(r =>
            `<tr>${headers.map(h => `<td>${Fmt.esc(r[h] ?? '')}</td>`).join('')}</tr>`).join('')}</tbody>
        </table>
      </div>`;

    const detected = Object.keys(mapping).length;

    body().innerHTML = `
      <div class="alert alert-info">
        Read <strong>${Fmt.int(row_count)}</strong> rows and <strong>${headers.length}</strong> columns
        from <strong>${Fmt.esc(file.name)}</strong>. Auto-matched ${detected} column${detected === 1 ? '' : 's'} —
        adjust anything below before importing.
      </div>

      <div class="field">
        <span>Dataset name</span>
        <input type="text" id="ds-name" value="${Fmt.esc(defaultName)}">
      </div>

      <div>
        <h3 class="card-title">Column mapping</h3>
        <div class="map-grid">${rows}</div>
      </div>

      <div>
        <h3 class="card-title">First ${sample.length} rows</h3>
        ${previewTable}
      </div>

      <div id="import-status"></div>
      <div class="modal-actions">
        <button class="btn btn-ghost" id="map-back">Back</button>
        <button class="btn btn-primary" id="map-import">Import ${Fmt.int(row_count)} rows</button>
      </div>`;

    body().querySelectorAll('select[data-field]').forEach(sel => {
      sel.addEventListener('change', () => sel.classList.toggle('unset', !sel.value));
    });
    document.getElementById('map-back').addEventListener('click', renderDrop);
    document.getElementById('map-import').addEventListener('click', commit);
  }

  // ── Step 3: import ───────────────────────────────────────────────────────
  async function commit() {
    const mapping = {};
    body().querySelectorAll('select[data-field]').forEach(sel => {
      if (sel.value) mapping[sel.dataset.field] = sel.value;
    });

    if (!mapping.employee_id) {
      document.getElementById('import-status').innerHTML =
        '<div class="alert alert-error">Map an <strong>Employee ID</strong> column — it identifies each position.</div>';
      return;
    }

    const btn = document.getElementById('map-import');
    btn.disabled = true;
    btn.textContent = 'Importing…';
    document.getElementById('import-status').innerHTML = '';

    try {
      const fd = new FormData();
      fd.append('file', pending.file);
      fd.append('mapping', JSON.stringify(mapping));
      fd.append('name', document.getElementById('ds-name').value.trim() || pending.file.name);
      const res = await API.post('/api/org/import', fd);

      OrgApp.state.datasetId = res.dataset_id;
      OrgApp.state.rootId = null;
      OrgApp.state.collapsed.clear();
      OrgApp.resetFilters();
      await OrgApp.loadDatasets();
      close();
      await OrgApp.render();

      const warned = (res.warnings || []).length;
      toast(`Imported ${res.imported} positions${warned ? ` · ${warned} issue${warned > 1 ? 's' : ''} flagged` : ''}`,
            warned ? '' : 'ok');
    } catch (e) {
      btn.disabled = false;
      btn.textContent = 'Import';
      document.getElementById('import-status').innerHTML =
        `<div class="alert alert-error">${Fmt.esc(e.message)}</div>`;
    }
  }

  document.addEventListener('DOMContentLoaded', () => {
    document.getElementById('import-close').addEventListener('click', close);
  });

  return { open, close };
})();
