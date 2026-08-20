// ── People: flat, sortable roster with the computed hierarchy columns ──────
(() => {
  const { API, Fmt, query } = OrgApp;

  const COLUMNS = [
    ['name', 'Name', false], ['job_title', 'Job Title', false],
    ['job_level', 'Level', false], ['function', 'Function', false],
    ['department', 'Department', false], ['location', 'Location', false],
    ['level_no', 'Layer', true], ['direct_reports', 'Directs', true],
    ['total_headcount', 'Org size', true], ['total_fte', 'Org FTE', true],
    ['status', 'Status', false],
  ];

  let sortBy = 'total_headcount';
  let managersOnly = false;

  function render() {
    return `
      <div class="card">
        <div style="display:flex;gap:12px;flex-wrap:wrap;align-items:flex-end;margin-bottom:12px">
          <label class="field"><span>Sort by</span>
            <select id="p-sort">
              ${COLUMNS.map(([k, l]) => `<option value="${k}"${k === sortBy ? ' selected' : ''}>${l}</option>`).join('')}
            </select>
          </label>
          <label class="field" style="flex-direction:row;align-items:center;gap:7px;min-width:0">
            <input type="checkbox" id="p-mgr" ${managersOnly ? 'checked' : ''} style="width:auto">
            <span style="text-transform:none;font-size:0.86rem;color:var(--text)">Managers only</span>
          </label>
          <div id="p-count" class="text-muted" style="margin-left:auto;font-size:0.82rem"></div>
        </div>
        <div id="p-table"><div class="loading">Loading…</div></div>
      </div>`;
  }

  async function init() {
    document.getElementById('p-sort').addEventListener('change', e => {
      sortBy = e.target.value; load();
    });
    document.getElementById('p-mgr').addEventListener('change', e => {
      managersOnly = e.target.checked; load();
    });
    await load();
  }

  async function load() {
    const wrap = document.getElementById('p-table');
    wrap.innerHTML = '<div class="loading">Loading…</div>';
    try {
      const res = await API.get('/api/org/employees' +
        query({ sort_by: sortBy, managers_only: managersOnly ? 'true' : '', limit: 2000 }));

      document.getElementById('p-count').textContent =
        `${Fmt.int(res.employees.length)} of ${Fmt.int(res.count)} shown`;

      wrap.innerHTML = `
        <div class="table-wrap" style="max-height:calc(100vh - 320px);overflow-y:auto">
          <table>
            <thead><tr>${COLUMNS.map(([, l, num]) =>
              `<th class="${num ? 'num' : ''}">${l}</th>`).join('')}</tr></thead>
            <tbody>${res.employees.map(rowHtml).join('')}</tbody>
          </table>
        </div>`;
    } catch (e) {
      wrap.innerHTML = `<div class="alert alert-error">${Fmt.esc(e.message)}</div>`;
    }
  }

  function rowHtml(p) {
    const cell = (key, num) => {
      if (key === 'status') {
        return `<td><span class="badge ${p.is_vacant ? 'badge-vacant' : 'badge-filled'}">${p.is_vacant ? 'Vacant' : 'Filled'}</span></td>`;
      }
      if (key === 'total_fte') return `<td class="num">${Fmt.num(p.total_fte, 1)}</td>`;
      if (num) return `<td class="num">${Fmt.int(p[key])}</td>`;
      return `<td>${Fmt.esc(p[key] ?? '—')}</td>`;
    };
    return `<tr class="clickable" data-employee="${Fmt.esc(p.employee_id)}">
      ${COLUMNS.map(([k, , num]) => cell(k, num)).join('')}</tr>`;
  }

  OrgApp.registerView('people', { render, init });
})();
