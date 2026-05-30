registerPage('dashboard', {
  render() {
    return `
<div class="page-header">Dashboard</div>

<div id="kpi-grid" class="kpi-grid mb-6">
  ${[...Array(6)].map(() => '<div class="kpi-card"><div class="kpi-label" style="height:12px;background:var(--surface3);border-radius:4px;width:60%"></div></div>').join('')}
</div>

<div class="section">
  <div class="section-header">
    <span class="section-title">Cumulative P&amp;L</span>
    <div class="flex gap-2 flex-wrap">
      <div class="toggle-group" id="period-toggle">
        <button class="toggle-btn active" data-period="all">All</button>
        <button class="toggle-btn" data-period="yearly">Yearly</button>
        <button class="toggle-btn" data-period="monthly">Monthly</button>
      </div>
      <div class="toggle-group" id="currency-toggle">
        <button class="toggle-btn active" data-cur="usd">USD</button>
        <button class="toggle-btn" data-cur="sar">SAR</button>
      </div>
    </div>
  </div>
  <div class="card"><div class="chart-wrap"><canvas id="chart-cumul"></canvas></div></div>
</div>

<div class="grid-2 mb-6">
  <div class="section">
    <div class="section-header"><span class="section-title">Monthly Performance</span></div>
    <div class="table-wrap"><table>
      <thead><tr><th>Month</th><th>Trades</th><th>P&amp;L (USD)</th><th>P&amp;L (SAR)</th><th>Win Rate</th></tr></thead>
      <tbody id="monthly-body"><tr><td colspan="5" class="text-muted" style="padding:20px;text-align:center">Loading…</td></tr></tbody>
    </table></div>
  </div>
  <div class="section">
    <div class="section-header"><span class="section-title">Recent Trades</span></div>
    <div class="table-wrap"><table>
      <thead><tr><th>Date</th><th>Ticker</th><th>Dir</th><th>Type</th><th>Days</th><th>P&amp;L</th></tr></thead>
      <tbody id="recent-body"><tr><td colspan="6" class="text-muted" style="padding:20px;text-align:center">Loading…</td></tr></tbody>
    </table></div>
  </div>
</div>

<div class="section">
  <div class="section-header">
    <span class="section-title">Performance by Ticker</span>
    <input type="text" id="ticker-search" placeholder="Search ticker…" style="width:180px;font-size:14px;padding:7px 11px">
  </div>
  <div class="table-wrap"><table>
    <thead><tr><th>Ticker</th><th>Trades</th><th>Win Rate</th><th>P&amp;L (USD)</th><th>P&amp;L (SAR)</th></tr></thead>
    <tbody id="ticker-body"><tr><td colspan="5" class="text-muted" style="padding:20px;text-align:center">Loading…</td></tr></tbody>
  </table></div>
</div>`;
  },

  async init() {
    const [metrics, monthly, recent, tickers] = await Promise.all([
      API.get('/api/metrics'),
      API.get('/api/monthly'),
      API.get('/api/trades?limit=10'),
      API.get('/api/ticker-stats'),
    ]);

    renderDashKPIs(metrics);
    renderMonthly(monthly);
    renderRecent(recent);
    renderTickerTable(tickers);

    let period = 'all', cur = 'usd';

    const drawChart = async () => {
      const data = await API.get(`/api/cumulative?period=${period}`);
      renderCumulChart(data, cur);
    };
    await drawChart();

    document.getElementById('period-toggle').addEventListener('click', e => {
      const b = e.target.closest('.toggle-btn');
      if (!b) return;
      period = b.dataset.period;
      document.querySelectorAll('#period-toggle .toggle-btn').forEach(x => x.classList.toggle('active', x === b));
      drawChart();
    });

    document.getElementById('currency-toggle').addEventListener('click', e => {
      const b = e.target.closest('.toggle-btn');
      if (!b) return;
      cur = b.dataset.cur;
      document.querySelectorAll('#currency-toggle .toggle-btn').forEach(x => x.classList.toggle('active', x === b));
      drawChart();
    });

    let allTickers = tickers;
    document.getElementById('ticker-search').addEventListener('input', e => {
      const q = e.target.value.toUpperCase();
      renderTickerTable(q ? allTickers.filter(t => t.ticker.includes(q)) : allTickers);
    });

    document.getElementById('recent-body').addEventListener('click', e => {
      const row = e.target.closest('tr[data-id]');
      if (row) window.location.hash = `trade-${row.dataset.id}`;
    });
  },
});

function renderDashKPIs(m) {
  const pf = Fmt.inf(m.profit_factor);
  const cards = [
    { label: 'Total Realized P&L',  value: Fmt.usd(m.total_pnl, false), cls: Fmt.cls(m.total_pnl), sub: Fmt.sar(m.total_pnl, sarRate) },
    { label: 'Total Trades',        value: m.total_trades,  sub: `${m.winning_trades} W / ${m.losing_trades} L` },
    { label: 'Win Rate',            value: Fmt.pct1(m.win_rate), cls: m.win_rate >= 50 ? 'text-green' : 'text-red', sub: `Profit Factor: ${pf}` },
    { label: 'Expectancy',          value: Fmt.usd(m.expectancy, false), cls: Fmt.cls(m.expectancy), sub: 'Per trade avg' },
    { label: 'Avg Winner',          value: Fmt.usd(m.avg_winner, false), cls: 'text-green', sub: Fmt.sar(m.avg_winner, sarRate) },
    { label: 'Avg Loser',           value: '-' + Fmt.usd(m.avg_loser, false), cls: 'text-red', sub: Fmt.sar(m.avg_loser, sarRate) },
  ];
  document.getElementById('kpi-grid').innerHTML = cards.map(c => `
    <div class="kpi-card">
      <div class="kpi-label">${c.label}</div>
      <div class="kpi-value ${c.cls || ''}">${c.value}</div>
      ${c.sub ? `<div class="kpi-sub">${c.sub}</div>` : ''}
    </div>`).join('');
}

function renderCumulChart(data, cur) {
  const canvas = document.getElementById('chart-cumul');
  if (!canvas) return;
  const ex = Chart.getChart(canvas);
  if (ex) ex.destroy();

  if (!data.length) {
    canvas.parentElement.innerHTML = '<div class="empty-state"><p>No trades yet</p></div>';
    return;
  }

  const labels = data.map(d => d.date);
  const vals   = data.map(d => cur === 'sar' ? +(d.cumulative * sarRate).toFixed(2) : d.cumulative);
  const last   = vals[vals.length - 1];
  const col    = last >= 0 ? '#6366f1' : '#ef4444';
  const prefix = cur === 'sar' ? 'SAR ' : '$';

  new Chart(canvas, {
    type: 'line',
    data: {
      labels,
      datasets: [{
        data: vals,
        borderColor: col,
        backgroundColor: last >= 0 ? 'rgba(99,102,241,0.07)' : 'rgba(239,68,68,0.07)',
        fill: true,
        tension: 0.3,
        pointRadius: data.length > 40 ? 0 : 3,
        pointHoverRadius: 6,
        borderWidth: 2,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: { callbacks: { label: ctx => ` ${prefix}${ctx.raw.toLocaleString('en-US', { minimumFractionDigits: 2 })}` } },
      },
      scales: {
        x: { grid: { color: '#1e1e35' } },
        y: { grid: { color: '#1e1e35' }, ticks: { callback: v => prefix + v.toLocaleString() } },
      },
    },
  });
}

function renderMonthly(rows) {
  const tbody = document.getElementById('monthly-body');
  if (!rows.length) { tbody.innerHTML = '<tr><td colspan="5" style="text-align:center;padding:20px" class="text-muted">No data</td></tr>'; return; }
  tbody.innerHTML = rows.map(r => {
    const cls = Fmt.cls(r.pnl);
    return `<tr>
      <td class="fw-600">${r.month}</td>
      <td>${r.trades}</td>
      <td class="${cls}">${Fmt.usd(r.pnl, false)}</td>
      <td class="${cls}">${Fmt.sar(r.pnl, sarRate)}</td>
      <td class="${r.win_rate >= 50 ? 'text-green' : 'text-red'}">${Fmt.pct1(r.win_rate)}</td>
    </tr>`;
  }).join('');
}

function renderRecent(trades) {
  const tbody = document.getElementById('recent-body');
  if (!trades.length) { tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;padding:20px" class="text-muted">No trades yet. <a href="#add-trade" style="color:var(--primary)">Add your first trade →</a></td></tr>'; return; }
  tbody.innerHTML = trades.map(t => `
    <tr class="clickable" data-id="${t.id}">
      <td>${Fmt.date(t.exit_date)}</td>
      <td class="fw-600">${t.ticker}</td>
      <td>${Fmt.dir(t.direction)}</td>
      <td>${Fmt.type(t.trade_type)}</td>
      <td>${t.holding_period}d</td>
      <td class="${Fmt.cls(t.pnl)}">${Fmt.usd(t.pnl, false)}</td>
    </tr>`).join('');
}

function renderTickerTable(stats) {
  const tbody = document.getElementById('ticker-body');
  if (!stats.length) { tbody.innerHTML = '<tr><td colspan="5" style="text-align:center;padding:20px" class="text-muted">No data</td></tr>'; return; }
  tbody.innerHTML = stats.map(s => `
    <tr>
      <td class="fw-600">${s.ticker}</td>
      <td>${s.trades}</td>
      <td class="${s.win_rate >= 50 ? 'text-green' : 'text-red'}">${Fmt.pct1(s.win_rate)}</td>
      <td class="${Fmt.cls(s.pnl)}">${Fmt.usd(s.pnl, false)}</td>
      <td class="${Fmt.cls(s.pnl)}">${Fmt.sar(s.pnl, sarRate)}</td>
    </tr>`).join('');
}
