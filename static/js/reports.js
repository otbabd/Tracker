let repFilters = {};

registerPage('reports', {
  render() {
    return `
<div class="page-header">Reports &amp; Export</div>

<div class="filter-bar mb-6">
  <div class="filter-grid">
    <div class="form-group">
      <label>Ticker</label>
      <input type="text" id="rep-ticker" placeholder="AAPL" value="${repFilters.ticker || ''}">
    </div>
    <div class="form-group">
      <label>Direction</label>
      <select id="rep-direction">
        <option value="">All</option>
        <option value="Long" ${repFilters.direction === 'Long' ? 'selected' : ''}>Long</option>
        <option value="Short" ${repFilters.direction === 'Short' ? 'selected' : ''}>Short</option>
      </select>
    </div>
    <div class="form-group">
      <label>Trade Type</label>
      <select id="rep-type">
        <option value="">All</option>
        ${['Day Trade','Swing Trade','Position Trade','Long Hold'].map(t =>
          `<option value="${t}" ${repFilters.trade_type === t ? 'selected' : ''}>${t}</option>`).join('')}
      </select>
    </div>
    <div class="form-group">
      <label>Outcome</label>
      <select id="rep-outcome">
        <option value="">All</option>
        <option value="Win" ${repFilters.outcome === 'Win' ? 'selected' : ''}>Win</option>
        <option value="Loss" ${repFilters.outcome === 'Loss' ? 'selected' : ''}>Loss</option>
      </select>
    </div>
    <div class="form-group">
      <label>From</label>
      <input type="date" id="rep-from" value="${repFilters.date_from || ''}">
    </div>
    <div class="form-group">
      <label>To</label>
      <input type="date" id="rep-to" value="${repFilters.date_to || ''}">
    </div>
    <div class="form-group" style="align-self:end">
      <button class="btn btn-primary btn-full" id="rep-apply">Apply Filters</button>
    </div>
  </div>
</div>

<div id="rep-content"><div class="loading">Loading…</div></div>`;
  },

  async init() {
    await loadReports();

    document.getElementById('rep-apply').addEventListener('click', async () => {
      repFilters = {
        ticker:     document.getElementById('rep-ticker').value.trim(),
        direction:  document.getElementById('rep-direction').value,
        trade_type: document.getElementById('rep-type').value,
        outcome:    document.getElementById('rep-outcome').value,
        date_from:  document.getElementById('rep-from').value,
        date_to:    document.getElementById('rep-to').value,
      };
      await loadReports();
    });
  },
});

async function loadReports() {
  const q = buildQuery(repFilters);
  const [trades, m] = await Promise.all([
    API.get('/api/trades' + q),
    API.get('/api/metrics' + q),
  ]);

  const div = document.getElementById('rep-content');
  const pf = Fmt.inf(m.profit_factor);
  const cnt = trades.length;

  div.innerHTML = `
<div class="alert" style="background:var(--surface2);border:1px solid var(--border);color:var(--text-dim);margin-bottom:20px">
  Dataset: <strong>${cnt} trade${cnt !== 1 ? 's' : ''}</strong> ·
  Total P&amp;L: <strong class="${Fmt.cls(m.total_pnl)}">${Fmt.usd(m.total_pnl, false)}</strong> ·
  Win Rate: <strong>${Fmt.pct1(m.win_rate)}</strong>
  ${!cnt ? ' — <span class="text-red">No trades match current filters.</span>' : ''}
</div>

<div class="grid-3 mb-6">
  <div class="card" style="text-align:center">
    <div class="card-title">CSV Export</div>
    <p style="font-size:13px;color:var(--text-dim);margin-bottom:16px">Raw trade data as comma-separated values. Open in Excel, Google Sheets, or any spreadsheet app.</p>
    <button class="btn btn-primary btn-full" id="dl-csv" ${!cnt ? 'disabled' : ''}>Download CSV</button>
  </div>
  <div class="card" style="text-align:center">
    <div class="card-title">Excel Export</div>
    <p style="font-size:13px;color:var(--text-dim);margin-bottom:16px">Multi-sheet workbook with Summary, Trade History, and Monthly Performance sheets.</p>
    <button class="btn btn-primary btn-full" id="dl-excel" ${!cnt ? 'disabled' : ''}>Download Excel</button>
  </div>
  <div class="card" style="text-align:center">
    <div class="card-title">PDF Report</div>
    <p style="font-size:13px;color:var(--text-dim);margin-bottom:16px">Formatted report with performance summary and full trade history table.</p>
    <button class="btn btn-primary btn-full" id="dl-pdf" ${!cnt ? 'disabled' : ''}>Download PDF</button>
  </div>
</div>

<div class="card">
  <div class="card-title">Performance Summary Preview</div>
  <div class="grid-2">
    <div>
      ${[
        ['Total Trades',     cnt],
        ['Winning Trades',   m.winning_trades],
        ['Losing Trades',    m.losing_trades],
        ['Win Rate',         Fmt.pct1(m.win_rate)],
        ['Profit Factor',    pf],
        ['Largest Winner',   Fmt.usd(m.largest_winner, false)],
        ['Largest Loser',    Fmt.usd(m.largest_loser, false)],
      ].map(([l,v]) => `<div class="detail-row"><span class="detail-label">${l}</span><span class="detail-value">${v}</span></div>`).join('')}
    </div>
    <div>
      ${[
        ['Total P&L (USD)',   Fmt.usd(m.total_pnl, false)],
        ['Total P&L (SAR)',   Fmt.sar(m.total_pnl, sarRate)],
        ['Avg Winner (USD)',  Fmt.usd(m.avg_winner, false)],
        ['Avg Loser (USD)',   '-' + Fmt.usd(m.avg_loser, false)],
        ['Expectancy (USD)',  Fmt.usd(m.expectancy, false)],
        ['Gross Profit',      Fmt.usd(m.gross_profit, false)],
        ['Gross Loss',        Fmt.usd(m.gross_loss, false)],
      ].map(([l,v]) => `<div class="detail-row"><span class="detail-label">${l}</span><span class="detail-value">${v}</span></div>`).join('')}
    </div>
  </div>
</div>`;

  if (cnt) {
    document.getElementById('dl-csv').addEventListener('click',   () => { window.location.href = '/api/export/csv'   + q; });
    document.getElementById('dl-excel').addEventListener('click', () => { window.location.href = '/api/export/excel' + q; });
    document.getElementById('dl-pdf').addEventListener('click',   () => { window.location.href = '/api/export/pdf'   + q; });
  }
}
