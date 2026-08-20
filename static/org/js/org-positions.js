// ── Positional hierarchy: management layers and a job/function cross-tab ───
(() => {
  const { API, Fmt, state, query } = OrgApp;

  const DIMS = [
    ['job_level', 'Job Level'], ['job_title', 'Job Title'], ['job_family', 'Job Family'],
    ['function', 'Function'], ['department', 'Department'], ['division', 'Division'],
    ['location', 'Location'], ['employment_type', 'Employment Type'], ['cost_center', 'Cost Center'],
  ];

  let matrixRows = 'job_level';
  let matrixCols = 'function';

  function render(s) {
    return `
      <div class="stack">
        <div>
          <h2 class="section-title">Management layers</h2>
          <div class="stack" id="layer-list">${s.layer_profile.map(layerRow).join('')}</div>
        </div>

        <div>
          <h2 class="section-title">Span of control</h2>
          <div class="grid grid-2">
            <div class="card">
              <h3 class="card-title">Managers by number of direct reports</h3>
              <div class="chart-box"><canvas id="span-chart"></canvas></div>
            </div>
            <div class="card">
              <h3 class="card-title">Structure signals</h3>
              <div class="table-wrap"><table>
                <tbody>
                  ${signal('Average span of control', Fmt.num(s.avg_span, 2),
                           s.avg_span < 3 ? 'Narrow — layers may be doing little routing' :
                           s.avg_span > 10 ? 'Wide — managers may be stretched' : 'Healthy range')}
                  ${signal('Median span', Fmt.int(s.median_span), 'Typical manager load')}
                  ${signal('Widest span', Fmt.int(s.max_span), 'Largest single team')}
                  ${signal('Managers with one report', Fmt.int(s.single_reports),
                           s.single_reports ? 'Candidates for delayering' : 'None')}
                  ${signal('Manager ratio', Fmt.pct(s.manager_ratio), `${Fmt.int(s.managers)} managers / ${Fmt.int(s.ics)} ICs`)}
                  ${signal('Layers deep', Fmt.int(s.layers), `${Fmt.int(s.roots)} top-level node${s.roots === 1 ? '' : 's'}`)}
                </tbody>
              </table></div>
            </div>
          </div>
        </div>

        <div>
          <h2 class="section-title">Position cross-tab</h2>
          <div class="card">
            <div style="display:flex;gap:10px;flex-wrap:wrap;margin-bottom:12px">
              <label class="field"><span>Rows</span>
                <select id="m-rows">${DIMS.map(([k, l]) => `<option value="${k}"${k === matrixRows ? ' selected' : ''}>${l}</option>`).join('')}</select>
              </label>
              <label class="field"><span>Columns</span>
                <select id="m-cols">${DIMS.map(([k, l]) => `<option value="${k}"${k === matrixCols ? ' selected' : ''}>${l}</option>`).join('')}</select>
              </label>
            </div>
            <div id="matrix-wrap"><div class="loading">Loading…</div></div>
          </div>
        </div>
      </div>`;
  }

  function signal(label, value, note) {
    return `<tr><td>${label}</td><td class="num"><strong>${value}</strong></td>
            <td class="text-muted" style="white-space:normal">${note}</td></tr>`;
  }

  function layerRow(l) {
    const chips = arr => arr.map(v => `<span class="badge">${Fmt.esc(v)}</span>`).join('');
    return `
      <div class="layer-row">
        <div class="layer-tag">
          <div class="n">L${l.level}</div>
          <div class="l">Layer</div>
        </div>
        <div class="layer-main">
          <div class="layer-stats">
            <div class="layer-stat"><div class="v">${Fmt.int(l.headcount)}</div><div class="k">Positions</div></div>
            <div class="layer-stat"><div class="v">${Fmt.num(l.fte, 1)}</div><div class="k">FTE</div></div>
            <div class="layer-stat"><div class="v">${Fmt.int(l.managers)}</div><div class="k">Managers</div></div>
            <div class="layer-stat"><div class="v">${Fmt.int(l.ics)}</div><div class="k">ICs</div></div>
            <div class="layer-stat"><div class="v">${l.avg_span ? Fmt.num(l.avg_span, 2) : '—'}</div><div class="k">Avg span</div></div>
            <div class="layer-stat"><div class="v ${l.vacant ? 'text-warn' : ''}">${Fmt.int(l.vacant)}</div><div class="k">Vacant</div></div>
          </div>
          <div>
            <div class="k text-muted" style="font-size:0.7rem;text-transform:uppercase;letter-spacing:0.05em;margin-bottom:4px">Common titles</div>
            <div class="chip-row">${chips(l.titles)}</div>
          </div>
          <div>
            <div class="k text-muted" style="font-size:0.7rem;text-transform:uppercase;letter-spacing:0.05em;margin-bottom:4px">Functions</div>
            <div class="chip-row">${chips(l.functions)}</div>
          </div>
        </div>
      </div>`;
  }

  async function init(s) {
    if (typeof Chart !== 'undefined') new Chart(document.getElementById('span-chart'), {
      type: 'bar',
      data: {
        labels: s.span_profile.map(b => b.value),
        datasets: [{ data: s.span_profile.map(b => b.headcount),
                     backgroundColor: '#6366f1', borderRadius: 4 }],
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        plugins: { legend: { display: false },
                   tooltip: { callbacks: { label: c => `${c.parsed.y} managers` } } },
        scales: { x: { grid: { display: false }, title: { display: true, text: 'Direct reports' } },
                  y: { beginAtZero: true, ticks: { precision: 0 } } },
      },
    });
    else spanFallback(s);

    document.getElementById('m-rows').addEventListener('change', e => {
      matrixRows = e.target.value; loadMatrix();
    });
    document.getElementById('m-cols').addEventListener('change', e => {
      matrixCols = e.target.value; loadMatrix();
    });
    await loadMatrix();
  }

  async function loadMatrix() {
    const wrap = document.getElementById('matrix-wrap');
    wrap.innerHTML = '<div class="loading">Loading…</div>';
    try {
      const m = await API.get('/api/org/matrix' + query({ rows: matrixRows, cols: matrixCols }));
      wrap.innerHTML = matrixTable(m);
    } catch (e) {
      wrap.innerHTML = `<div class="alert alert-error">${Fmt.esc(e.message)}</div>`;
    }
  }

  function matrixTable(m) {
    const max = Math.max(1, ...m.cells.flatMap(c => c.values));
    const cols = m.cols.slice(0, 24);
    const truncated = m.cols.length - cols.length;

    const head = `<tr><th class="rot">${labelOf(m.row_key)} \\ ${labelOf(m.col_key)}</th>
      ${cols.map(c => `<th class="num">${Fmt.esc(c)}</th>`).join('')}<th class="num">Total</th></tr>`;

    const rows = m.cells.map(cell => `
      <tr>
        <th>${Fmt.esc(cell.row)}</th>
        ${cols.map((c, i) => {
          const v = cell.values[m.cols.indexOf(c)] ?? 0;
          const a = v ? 0.08 + 0.5 * (v / max) : 0;
          return `<td class="heat" style="background:rgba(99,102,241,${a.toFixed(3)})">${v || ''}</td>`;
        }).join('')}
        <td class="heat"><strong>${Fmt.int(cell.total)}</strong></td>
      </tr>`).join('');

    const totals = `<tr><th>Total</th>
      ${cols.map(c => `<td class="heat"><strong>${Fmt.int(m.col_totals[m.cols.indexOf(c)] ?? 0)}</strong></td>`).join('')}
      <td class="heat"><strong>${Fmt.int(m.total)}</strong></td></tr>`;

    return `<div class="table-wrap"><table class="matrix">
        <thead>${head}</thead><tbody>${rows}${totals}</tbody></table></div>
      ${truncated > 0 ? `<div class="text-muted" style="font-size:0.78rem;margin-top:8px">
        ${truncated} more column${truncated > 1 ? 's' : ''} hidden — filter to narrow the view.</div>` : ''}`;
  }

  // Charts are a nicety — the numbers still have to show if the library is absent.
  function spanFallback(s) {
    const max = Math.max(1, ...s.span_profile.map(b => b.headcount));
    document.getElementById('span-chart').closest('.chart-box').innerHTML =
      `<table>${s.span_profile.map(b => `<tr><td>${b.value} reports</td>
        <td class="bar-cell"><div class="bar-fill" style="width:${b.headcount / max * 100}%"></div>
        <span>${Fmt.int(b.headcount)}</span></td></tr>`).join('')}</table>`;
  }

  const labelOf = key => (DIMS.find(d => d[0] === key) || [, key])[1];

  OrgApp.registerView('positions', { render, init });
})();
