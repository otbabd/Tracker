// ── Headcount: KPIs, breakdowns by every dimension, layer profile ─────────
(() => {
  const { Fmt, state, colorFor, PALETTE } = OrgApp;

  const BREAKDOWNS = [
    ['function', 'Function'], ['department', 'Department'], ['division', 'Division'],
    ['job_level', 'Job Level'], ['job_family', 'Job Family'], ['location', 'Location'],
    ['employment_type', 'Employment Type'], ['cost_center', 'Cost Center'],
  ];

  const charts = [];

  function render(s) {
    const kpi = (label, value, sub) =>
      `<div class="kpi"><div class="kpi-label">${label}</div>
       <div class="kpi-value">${value}</div><div class="kpi-sub">${sub}</div></div>`;

    const present = BREAKDOWNS.filter(([k]) => (s.breakdowns[k] || []).length > 1);

    return `
      <div class="stack">
        <div class="grid grid-kpi">
          ${kpi('Headcount', Fmt.int(s.headcount), `${Fmt.num(s.total_fte, 1)} FTE`)}
          ${kpi('Filled', Fmt.int(s.filled), `${Fmt.pct(100 - s.vacancy_rate)} of positions`)}
          ${kpi('Vacant', `<span class="${s.vacant ? 'text-warn' : ''}">${Fmt.int(s.vacant)}</span>`, `${Fmt.pct(s.vacancy_rate)} vacancy rate`)}
          ${kpi('Managers', Fmt.int(s.managers), `${Fmt.pct(s.manager_ratio)} of headcount`)}
          ${kpi('Avg span', Fmt.num(s.avg_span, 2), `median ${Fmt.int(s.median_span)} · max ${Fmt.int(s.max_span)}`)}
          ${kpi('Layers', Fmt.int(s.layers), `${Fmt.int(s.roots)} top-level node${s.roots === 1 ? '' : 's'}`)}
        </div>

        <div class="grid grid-2">
          <div class="card">
            <h3 class="card-title">Headcount by layer</h3>
            <div class="chart-box"><canvas id="hc-layers"></canvas></div>
          </div>
          <div class="card">
            <h3 class="card-title">Filled vs vacant</h3>
            <div class="chart-box"><canvas id="hc-vacancy"></canvas></div>
          </div>
        </div>

        ${present.map(([key, label]) => section(key, label, s.breakdowns[key])).join('')}
      </div>`;
  }

  function section(key, label, rows) {
    const max = Math.max(1, ...rows.map(r => r.headcount));
    const barHeight = Math.min(420, Math.max(200, Math.min(rows.length, 14) * 28 + 40));
    return `
      <div class="grid grid-2">
        <div class="card">
          <h3 class="card-title">Headcount by ${label.toLowerCase()}</h3>
          <div class="chart-box" style="height:${barHeight}px"><canvas id="hc-${key}"></canvas></div>
        </div>
        <div class="card">
          <h3 class="card-title">${label} detail</h3>
          <div class="table-wrap" style="max-height:${barHeight}px;overflow-y:auto">
            <table>
              <thead><tr><th>${label}</th><th class="num">HC</th><th class="num">FTE</th>
                <th class="num">Vacant</th><th class="num">Share</th></tr></thead>
              <tbody>
                ${rows.map(r => `
                  <tr class="clickable" data-drill="${Fmt.esc(key)}" data-value="${Fmt.esc(r.value)}">
                    <td class="bar-cell">
                      <div class="bar-fill" style="width:${(r.headcount / max * 100).toFixed(1)}%"></div>
                      <span>${Fmt.esc(r.value)}</span>
                    </td>
                    <td class="num">${Fmt.int(r.headcount)}</td>
                    <td class="num">${Fmt.num(r.fte, 1)}</td>
                    <td class="num ${r.vacant ? 'text-warn' : 'text-muted'}">${Fmt.int(r.vacant)}</td>
                    <td class="num text-dim">${Fmt.pct(r.share)}</td>
                  </tr>`).join('')}
              </tbody>
            </table>
          </div>
        </div>
      </div>`;
  }

  function init(s) {
    charts.forEach(c => c.destroy());
    charts.length = 0;
    if (typeof Chart === 'undefined') {
      document.querySelectorAll('.chart-box').forEach(b => b.remove());
    } else {

    charts.push(new Chart(document.getElementById('hc-layers'), {
      type: 'bar',
      data: {
        labels: s.layer_profile.map(l => 'L' + l.level),
        datasets: [
          { label: 'Managers', data: s.layer_profile.map(l => l.managers), backgroundColor: '#6366f1', borderRadius: 3 },
          { label: 'ICs', data: s.layer_profile.map(l => l.ics), backgroundColor: '#22c55e', borderRadius: 3 },
        ],
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        scales: { x: { stacked: true, grid: { display: false } },
                  y: { stacked: true, beginAtZero: true, ticks: { precision: 0 } } },
      },
    }));

    charts.push(new Chart(document.getElementById('hc-vacancy'), {
      type: 'doughnut',
      data: {
        labels: ['Filled', 'Vacant'],
        datasets: [{ data: [s.filled, s.vacant], backgroundColor: ['#22c55e', '#f59e0b'], borderWidth: 0 }],
      },
      options: { responsive: true, maintainAspectRatio: false, cutout: '62%',
                 plugins: { legend: { position: 'bottom' } } },
    }));

    BREAKDOWNS.forEach(([key]) => {
      const canvas = document.getElementById('hc-' + key);
      if (!canvas) return;
      const rows = (s.breakdowns[key] || []).slice(0, 14);
      const values = rows.map(r => r.value);
      charts.push(new Chart(canvas, {
        type: 'bar',
        data: {
          labels: values,
          datasets: [{
            data: rows.map(r => r.headcount),
            backgroundColor: values.map(v => colorFor(v, values)),
            borderRadius: 4,
          }],
        },
        options: {
          indexAxis: 'y',
          responsive: true, maintainAspectRatio: false,
          plugins: { legend: { display: false },
                     tooltip: { callbacks: { label: c => {
                       const r = rows[c.dataIndex];
                       return `${r.headcount} positions · ${r.fte} FTE · ${r.vacant} vacant`;
                     } } } },
          scales: { x: { beginAtZero: true, ticks: { precision: 0 } },
                    y: { grid: { display: false } } },
        },
      }));
    });
    }

    // Clicking a breakdown row filters the whole app to that slice.
    document.getElementById('content').addEventListener('click', e => {
      const row = e.target.closest('[data-drill]');
      if (!row) return;
      OrgApp.setFilter(row.dataset.drill, row.dataset.value);
    });
  }

  OrgApp.registerView('headcount', { render, init });
})();
