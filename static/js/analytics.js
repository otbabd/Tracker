let anFilters = {};

registerPage('analytics', {
  render() {
    return `
<div class="page-header">Analytics</div>

<div class="filter-bar mb-6">
  <div class="filter-grid">
    <div class="form-group">
      <label>Ticker</label>
      <input type="text" id="an-ticker" placeholder="AAPL" value="${anFilters.ticker || ''}">
    </div>
    <div class="form-group">
      <label>Direction</label>
      <select id="an-direction">
        <option value="">All</option>
        <option value="Long" ${anFilters.direction === 'Long' ? 'selected' : ''}>Long</option>
        <option value="Short" ${anFilters.direction === 'Short' ? 'selected' : ''}>Short</option>
      </select>
    </div>
    <div class="form-group">
      <label>Trade Type</label>
      <select id="an-type">
        <option value="">All</option>
        ${['Day Trade','Swing Trade','Position Trade','Long Hold'].map(t =>
          `<option value="${t}" ${anFilters.trade_type === t ? 'selected' : ''}>${t}</option>`).join('')}
      </select>
    </div>
    <div class="form-group">
      <label>From</label>
      <input type="date" id="an-from" value="${anFilters.date_from || ''}">
    </div>
    <div class="form-group">
      <label>To</label>
      <input type="date" id="an-to" value="${anFilters.date_to || ''}">
    </div>
    <div class="form-group" style="align-self:end">
      <button class="btn btn-primary btn-full" id="an-apply">Apply</button>
    </div>
    <div class="form-group" style="align-self:end">
      <button class="btn btn-ghost btn-full" id="an-clear">Clear</button>
    </div>
  </div>
</div>

<div id="an-content"><div class="loading">Loading…</div></div>`;
  },

  async init() {
    await loadAnalytics();

    document.getElementById('an-apply').addEventListener('click', async () => {
      anFilters = {
        ticker:     document.getElementById('an-ticker').value.trim(),
        direction:  document.getElementById('an-direction').value,
        trade_type: document.getElementById('an-type').value,
        date_from:  document.getElementById('an-from').value,
        date_to:    document.getElementById('an-to').value,
      };
      await loadAnalytics();
    });

    document.getElementById('an-clear').addEventListener('click', async () => {
      anFilters = {};
      ['an-ticker','an-direction','an-type','an-from','an-to'].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.value = '';
      });
      await loadAnalytics();
    });
  },
});

async function loadAnalytics() {
  const q = buildQuery(anFilters);
  const [m, typeStats, tickers, pnlVals] = await Promise.all([
    API.get('/api/metrics' + q),
    API.get('/api/trade-type-stats' + buildQuery({ date_from: anFilters.date_from, date_to: anFilters.date_to })),
    API.get('/api/ticker-stats' + q),
    API.get('/api/pnl-values' + q),
  ]);

  const pf = Fmt.inf(m.profit_factor);
  const div = document.getElementById('an-content');

  if (!m.total_trades) {
    div.innerHTML = '<div class="empty-state"><h3>No trades found</h3><p>Adjust the filters above.</p></div>';
    return;
  }

  div.innerHTML = `
<!-- Win/Loss Stats -->
<div class="stat-grid mb-6">
  ${[
    ['Winning Trades', m.winning_trades,         'text-green'],
    ['Losing Trades',  m.losing_trades,          'text-red'],
    ['Win Rate',       Fmt.pct1(m.win_rate),     m.win_rate >= 50 ? 'text-green' : 'text-red'],
    ['Profit Factor',  pf,                       Fmt.cls(m.total_pnl)],
    ['Avg Winner',     Fmt.usd(m.avg_winner, false), 'text-green'],
    ['Avg Loser',      '-' + Fmt.usd(m.avg_loser, false), 'text-red'],
    ['Largest Winner', Fmt.usd(m.largest_winner, false), 'text-green'],
    ['Largest Loser',  Fmt.usd(m.largest_loser, false),  'text-red'],
    ['Win Streak',     m.win_streak,             'text-green'],
    ['Loss Streak',    m.loss_streak,            'text-red'],
    ['Expectancy',     Fmt.usd(m.expectancy, false), Fmt.cls(m.expectancy)],
    ['Total Trades',   m.total_trades,           ''],
  ].map(([l, v, c]) => `
    <div class="stat-card">
      <div class="stat-label">${l}</div>
      <div class="stat-value ${c}">${v}</div>
    </div>`).join('')}
</div>

<div class="grid-2 mb-6">
  <!-- Donut chart -->
  <div class="card">
    <div class="card-title">Win vs Loss</div>
    <div class="chart-wrap-sm"><canvas id="chart-donut"></canvas></div>
  </div>
  <!-- Trade type bar -->
  <div class="card">
    <div class="card-title">P&amp;L by Trade Type</div>
    <div class="chart-wrap-sm"><canvas id="chart-bar"></canvas></div>
  </div>
</div>

<!-- Trade type table -->
<div class="section">
  <div class="section-header"><span class="section-title">Trade Type Breakdown</span></div>
  <div class="table-wrap"><table>
    <thead><tr><th>Type</th><th>Trades</th><th>Win Rate</th><th>P&amp;L (USD)</th><th>P&amp;L (SAR)</th></tr></thead>
    <tbody>${typeStats.map(r => `
      <tr>
        <td>${Fmt.type(r.trade_type)}</td>
        <td>${r.trades}</td>
        <td class="${r.win_rate >= 50 ? 'text-green' : 'text-red'}">${Fmt.pct1(r.win_rate)}</td>
        <td class="${Fmt.cls(r.pnl)}">${Fmt.usd(r.pnl, false)}</td>
        <td class="${Fmt.cls(r.pnl)}">${Fmt.sar(r.pnl, sarRate)}</td>
      </tr>`).join('')}</tbody>
  </table></div>
</div>

<!-- Ticker table -->
<div class="section">
  <div class="section-header">
    <span class="section-title">Performance by Ticker</span>
    <input type="text" id="an-ticker-search" placeholder="Search…" style="width:170px;font-size:14px;padding:7px 11px">
  </div>
  <div class="table-wrap"><table id="an-ticker-table">
    <thead><tr><th>Ticker</th><th>Trades</th><th>Win Rate</th><th>Total P&amp;L (USD)</th><th>Total P&amp;L (SAR)</th><th>Avg Return</th></tr></thead>
    <tbody id="an-ticker-body"></tbody>
  </table></div>
</div>

<!-- P&L Distribution -->
<div class="section">
  <div class="section-header"><span class="section-title">P&amp;L Distribution</span></div>
  <div class="card"><div class="chart-wrap"><canvas id="chart-hist"></canvas></div></div>
</div>`;

  // Render charts & tables
  renderDonut(m.winning_trades, m.losing_trades);
  renderTypeBar(typeStats);
  renderTickerAnalytics(tickers);
  renderPnlHistogram(pnlVals);

  document.getElementById('an-ticker-search').addEventListener('input', e => {
    const q = e.target.value.toUpperCase();
    renderTickerAnalytics(q ? tickers.filter(t => t.ticker.includes(q)) : tickers);
  });
}

function renderDonut(wins, losses) {
  const canvas = document.getElementById('chart-donut');
  if (!canvas) return;
  new Chart(canvas, {
    type: 'doughnut',
    data: {
      labels: ['Wins', 'Losses'],
      datasets: [{ data: [wins, losses], backgroundColor: ['#22c55e', '#ef4444'], borderWidth: 0 }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      cutout: '65%',
      plugins: {
        legend: { position: 'bottom', labels: { padding: 16 } },
        tooltip: { callbacks: { label: ctx => ` ${ctx.label}: ${ctx.raw} (${Fmt.pct1(ctx.raw / (wins + losses) * 100)})` } },
      },
    },
  });
}

function renderTypeBar(stats) {
  const canvas = document.getElementById('chart-bar');
  if (!canvas || !stats.length) return;
  const order = ['Day Trade', 'Swing Trade', 'Position Trade', 'Long Hold'];
  const sorted = [...stats].sort((a, b) => order.indexOf(a.trade_type) - order.indexOf(b.trade_type));
  new Chart(canvas, {
    type: 'bar',
    data: {
      labels: sorted.map(s => s.trade_type),
      datasets: [{
        data: sorted.map(s => s.pnl),
        backgroundColor: sorted.map(s => s.pnl >= 0 ? 'rgba(99,102,241,0.7)' : 'rgba(239,68,68,0.7)'),
        borderRadius: 4,
        borderSkipped: false,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        x: { grid: { color: '#1e1e35' } },
        y: { grid: { color: '#1e1e35' }, ticks: { callback: v => '$' + v.toLocaleString() } },
      },
    },
  });
}

function renderTickerAnalytics(stats) {
  const tbody = document.getElementById('an-ticker-body');
  if (!tbody) return;
  if (!stats.length) { tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;padding:20px" class="text-muted">No data</td></tr>'; return; }
  tbody.innerHTML = stats.map(s => `
    <tr>
      <td class="fw-600">${s.ticker}</td>
      <td>${s.trades}</td>
      <td class="${s.win_rate >= 50 ? 'text-green' : 'text-red'}">${Fmt.pct1(s.win_rate)}</td>
      <td class="${Fmt.cls(s.pnl)}">${Fmt.usd(s.pnl, false)}</td>
      <td class="${Fmt.cls(s.pnl)}">${Fmt.sar(s.pnl, sarRate)}</td>
      <td class="${Fmt.cls(s.avg_return)}">${Fmt.pct(s.avg_return)}</td>
    </tr>`).join('');
}

function renderPnlHistogram(values) {
  const canvas = document.getElementById('chart-hist');
  if (!canvas || !values.length) return;

  const BINS = Math.min(25, Math.max(5, Math.floor(values.length / 2)));
  const min = Math.min(...values), max = Math.max(...values);
  const width = (max - min) / BINS || 1;
  const counts = Array(BINS).fill(0);
  const labels = [];
  for (let i = 0; i < BINS; i++) labels.push(+(min + (i + 0.5) * width).toFixed(2));
  values.forEach(v => {
    let idx = Math.floor((v - min) / width);
    if (idx >= BINS) idx = BINS - 1;
    counts[idx]++;
  });

  new Chart(canvas, {
    type: 'bar',
    data: {
      labels: labels.map(l => '$' + l.toLocaleString()),
      datasets: [{
        data: counts,
        backgroundColor: labels.map(l => l >= 0 ? 'rgba(99,102,241,0.65)' : 'rgba(239,68,68,0.65)'),
        borderRadius: 3,
        borderSkipped: false,
        barPercentage: 0.95,
        categoryPercentage: 1,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        annotation: {},
      },
      scales: {
        x: { grid: { color: '#1e1e35' }, ticks: { maxRotation: 45, maxTicksLimit: 12 } },
        y: { grid: { color: '#1e1e35' }, title: { display: true, text: 'Count' } },
      },
    },
  });
}
