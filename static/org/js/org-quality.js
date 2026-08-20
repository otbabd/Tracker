// ── Data quality: what the importer had to fix or could not resolve ────────
(() => {
  const { API, Fmt, query } = OrgApp;

  const LABELS = {
    orphan:         ['Missing manager', 'The named manager is not in the file, so the position was lifted to the top level.'],
    cycle:          ['Reporting cycle', 'A chain of managers loops back on itself; the link was cut so the chart could be drawn.'],
    multiple_roots: ['Multiple top-level nodes', 'More than one position has no manager — the org has several separate trees.'],
    duplicate_id:   ['Duplicate ID', 'The same ID appeared more than once and was suffixed to keep both rows.'],
    missing_id:     ['Missing ID', 'The row had no Employee ID and was skipped.'],
    self_manager:   ['Self-reporting', 'The position lists itself as its own manager.'],
  };

  function render() {
    return '<div id="q-body"><div class="loading">Loading…</div></div>';
  }

  async function init() {
    const wrap = document.getElementById('q-body');
    try {
      const res = await API.get('/api/org/issues' + query());
      wrap.innerHTML = res.count ? groups(res.issues) : `
        <div class="empty">
          <h2>✅ No data issues found</h2>
          <p>Every position resolved to a manager and the hierarchy is a clean tree.</p>
        </div>`;
    } catch (e) {
      wrap.innerHTML = `<div class="alert alert-error">${Fmt.esc(e.message)}</div>`;
    }
  }

  function groups(issues) {
    const byType = {};
    issues.forEach(i => (byType[i.type] = byType[i.type] || []).push(i));

    return `<div class="stack">${Object.entries(byType).map(([type, items]) => {
      const [title, help] = LABELS[type] || [type, ''];
      return `
        <div class="card">
          <h3 class="card-title">${Fmt.esc(title)} <span class="badge badge-vacant">${items.length}</span></h3>
          <p class="text-muted" style="font-size:0.82rem;margin-bottom:10px">${Fmt.esc(help)}</p>
          <div class="table-wrap" style="max-height:280px;overflow-y:auto">
            <table><tbody>
              ${items.map(i => `
                <tr class="${i.employee_id ? 'clickable' : ''}" ${i.employee_id ? `data-employee="${Fmt.esc(i.employee_id)}"` : ''}>
                  <td style="white-space:normal">${Fmt.esc(i.message)}</td>
                </tr>`).join('')}
            </tbody></table>
          </div>
        </div>`;
    }).join('')}</div>`;
  }

  OrgApp.registerView('quality', { render, init });
})();
