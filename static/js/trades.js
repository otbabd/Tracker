// ── Add / Edit Trade ──────────────────────────────────────────────────────
registerPage('add-trade', {
  render() {
    const today = new Date().toISOString().split('T')[0];
    return `
<div class="page-header" id="form-title">Add Trade</div>
<div id="form-alert"></div>
<div class="card">
  <form id="trade-form">
    <div class="form-grid">
      <div class="form-group">
        <label>Ticker *</label>
        <input type="text" id="f-ticker" placeholder="AAPL" autocomplete="off" autocapitalize="characters">
      </div>
      <div class="form-group">
        <label>Direction *</label>
        <select id="f-direction">
          <option value="Long">Long</option>
          <option value="Short">Short</option>
        </select>
      </div>
      <div class="form-group">
        <label>Entry Date *</label>
        <input type="date" id="f-entry-date" value="${today}">
      </div>
      <div class="form-group">
        <label>Exit Date *</label>
        <input type="date" id="f-exit-date" value="${today}">
      </div>
      <div class="form-group">
        <label>Entry Price ($) *</label>
        <input type="number" id="f-entry-price" min="0.0001" step="0.01" placeholder="0.00">
      </div>
      <div class="form-group">
        <label>Exit Price ($) *</label>
        <input type="number" id="f-exit-price" min="0.0001" step="0.01" placeholder="0.00">
      </div>
      <div class="form-group">
        <label>Shares *</label>
        <input type="number" id="f-shares" min="0.0001" step="1" placeholder="0">
      </div>
      <div class="form-group">
        <label>Fees ($)</label>
        <input type="number" id="f-fees" min="0" step="0.01" value="0" placeholder="0.00">
      </div>
      <div class="form-group form-full">
        <label>Notes</label>
        <textarea id="f-notes" placeholder="Optional trade notes…"></textarea>
      </div>
    </div>

    <div id="preview-area" class="mt-4" style="display:none">
      <div class="preview-box" id="preview-box">
        <div class="preview-header">Live Preview</div>
        <div class="preview-row">
          <div class="preview-item"><span class="pi-label">P&amp;L (USD)</span><span class="pi-value" id="prev-pnl">—</span></div>
          <div class="preview-item"><span class="pi-label">P&amp;L (SAR)</span><span class="pi-value" id="prev-sar">—</span></div>
          <div class="preview-item"><span class="pi-label">Return %</span><span class="pi-value" id="prev-ret">—</span></div>
          <div class="preview-item"><span class="pi-label">Trade Type</span><span class="pi-value" id="prev-type">—</span></div>
          <div class="preview-item"><span class="pi-label">Days Held</span><span class="pi-value" id="prev-days">—</span></div>
        </div>
      </div>
    </div>

    <div class="flex gap-3 mt-4">
      <button type="submit" class="btn btn-primary" id="submit-btn">Add Trade</button>
      <button type="button" class="btn btn-ghost" onclick="history.back()">Cancel</button>
    </div>
  </form>
</div>`;
  },

  async init() {
    const alertEl = document.getElementById('form-alert');

    // Edit mode?
    if (currentTradeId) {
      const t = await API.get(`/api/trades/${currentTradeId}`);
      document.getElementById('form-title').textContent = `Edit Trade — #${t.id} ${t.ticker}`;
      document.getElementById('submit-btn').textContent = 'Save Changes';
      document.getElementById('f-ticker').value      = t.ticker;
      document.getElementById('f-direction').value   = t.direction;
      document.getElementById('f-entry-date').value  = t.entry_date;
      document.getElementById('f-exit-date').value   = t.exit_date;
      document.getElementById('f-entry-price').value = t.entry_price;
      document.getElementById('f-exit-price').value  = t.exit_price;
      document.getElementById('f-shares').value      = t.shares;
      document.getElementById('f-fees').value        = t.fees;
      document.getElementById('f-notes').value       = t.notes || '';
      updatePreview();
    }

    // Live preview
    const previewInputs = ['f-ticker', 'f-direction', 'f-entry-date', 'f-exit-date',
                           'f-entry-price', 'f-exit-price', 'f-shares', 'f-fees'];
    previewInputs.forEach(id => document.getElementById(id).addEventListener('input', updatePreview));
    previewInputs.forEach(id => document.getElementById(id).addEventListener('change', updatePreview));

    // Submit
    document.getElementById('trade-form').addEventListener('submit', async e => {
      e.preventDefault();
      alertEl.innerHTML = '';

      const body = {
        ticker:      document.getElementById('f-ticker').value,
        direction:   document.getElementById('f-direction').value,
        entry_date:  document.getElementById('f-entry-date').value,
        exit_date:   document.getElementById('f-exit-date').value,
        entry_price: parseFloat(document.getElementById('f-entry-price').value),
        exit_price:  parseFloat(document.getElementById('f-exit-price').value),
        shares:      parseFloat(document.getElementById('f-shares').value),
        fees:        parseFloat(document.getElementById('f-fees').value) || 0,
        notes:       document.getElementById('f-notes').value,
      };

      try {
        if (currentTradeId) {
          await API.put(`/api/trades/${currentTradeId}`, body);
          alertEl.innerHTML = '<div class="alert alert-success">Trade updated successfully.</div>';
        } else {
          await API.post('/api/trades', body);
          alertEl.innerHTML = '<div class="alert alert-success">Trade added successfully.</div>';
          document.getElementById('trade-form').reset();
          document.getElementById('preview-area').style.display = 'none';
          const today = new Date().toISOString().split('T')[0];
          document.getElementById('f-entry-date').value = today;
          document.getElementById('f-exit-date').value  = today;
          document.getElementById('f-fees').value = 0;
        }
        window.scrollTo(0, 0);
      } catch (err) {
        const msgs = Array.isArray(err.detail)
          ? err.detail.map(d => typeof d === 'string' ? d : (d.msg || JSON.stringify(d))).join('<br>')
          : (err.detail || 'Submission failed');
        alertEl.innerHTML = `<div class="alert alert-error">${msgs}</div>`;
        window.scrollTo(0, 0);
      }
    });
  },
});

function updatePreview() {
  const dir   = document.getElementById('f-direction').value;
  const ep    = parseFloat(document.getElementById('f-entry-price').value);
  const xp    = parseFloat(document.getElementById('f-exit-price').value);
  const sh    = parseFloat(document.getElementById('f-shares').value);
  const fees  = parseFloat(document.getElementById('f-fees').value) || 0;
  const ed    = document.getElementById('f-entry-date').value;
  const xd    = document.getElementById('f-exit-date').value;
  const area  = document.getElementById('preview-area');
  const box   = document.getElementById('preview-box');

  if (!ep || !xp || !sh || !ed || !xd) { area.style.display = 'none'; return; }
  area.style.display = 'block';

  const pnl = dir === 'Long'
    ? ((xp - ep) * sh) - fees
    : ((ep - xp) * sh) - fees;
  const ret = dir === 'Long'
    ? ((xp - ep) / ep) * 100
    : ((ep - xp) / ep) * 100;
  const days = Math.max(0, Math.round((new Date(xd) - new Date(ed)) / 86400000));
  const type = days === 0 ? 'Day Trade' : days <= 5 ? 'Swing Trade' : days <= 30 ? 'Position Trade' : 'Long Hold';

  const cls = pnl >= 0 ? 'text-green' : 'text-red';
  box.className = `preview-box ${pnl >= 0 ? 'win' : 'loss'}`;
  document.getElementById('prev-pnl').className  = `pi-value ${cls}`;
  document.getElementById('prev-sar').className  = `pi-value ${cls}`;
  document.getElementById('prev-ret').className  = `pi-value ${cls}`;
  document.getElementById('prev-pnl').textContent  = Fmt.usd(pnl, false);
  document.getElementById('prev-sar').textContent  = Fmt.sar(pnl, sarRate);
  document.getElementById('prev-ret').textContent  = Fmt.pct(ret);
  document.getElementById('prev-type').textContent = type;
  document.getElementById('prev-days').textContent = days + 'd';
}


// ── Trade History ─────────────────────────────────────────────────────────
const PAGE_SIZE = 25;
let histFilters = {}, histPage = 1, histTrades = [], histSort = { col: null, asc: false };

registerPage('history', {
  render() {
    return `
<div class="page-header">Trade History</div>

<div class="filter-bar mb-4">
  <div class="filter-grid">
    <div class="form-group">
      <label>Ticker</label>
      <input type="text" id="hf-ticker" placeholder="AAPL" value="${histFilters.ticker || ''}">
    </div>
    <div class="form-group">
      <label>Direction</label>
      <select id="hf-direction">
        <option value="">All</option>
        <option value="Long" ${histFilters.direction === 'Long' ? 'selected' : ''}>Long</option>
        <option value="Short" ${histFilters.direction === 'Short' ? 'selected' : ''}>Short</option>
      </select>
    </div>
    <div class="form-group">
      <label>Trade Type</label>
      <select id="hf-type">
        <option value="">All</option>
        ${['Day Trade','Swing Trade','Position Trade','Long Hold'].map(t =>
          `<option value="${t}" ${histFilters.trade_type === t ? 'selected' : ''}>${t}</option>`).join('')}
      </select>
    </div>
    <div class="form-group">
      <label>Outcome</label>
      <select id="hf-outcome">
        <option value="">All</option>
        <option value="Win" ${histFilters.outcome === 'Win' ? 'selected' : ''}>Win</option>
        <option value="Loss" ${histFilters.outcome === 'Loss' ? 'selected' : ''}>Loss</option>
      </select>
    </div>
    <div class="form-group">
      <label>From Date</label>
      <input type="date" id="hf-from" value="${histFilters.date_from || ''}">
    </div>
    <div class="form-group">
      <label>To Date</label>
      <input type="date" id="hf-to" value="${histFilters.date_to || ''}">
    </div>
    <div class="form-group" style="align-self:end">
      <button class="btn btn-primary btn-full" id="apply-filters">Apply Filters</button>
    </div>
    <div class="form-group" style="align-self:end">
      <button class="btn btn-ghost btn-full" id="clear-filters">Clear</button>
    </div>
  </div>
</div>

<div class="flex-between mb-4" style="flex-wrap:wrap;gap:10px">
  <div id="hist-summary" class="text-muted" style="font-size:13px"></div>
  <a id="export-csv" class="btn btn-sm" href="#" download="trades.csv">Export CSV</a>
</div>

<div class="table-wrap">
  <table id="hist-table">
    <thead>
      <tr>
        <th data-sort="exit_date">Date ↕</th>
        <th data-sort="ticker">Ticker ↕</th>
        <th>Dir</th>
        <th>Type</th>
        <th data-sort="entry_price">Entry ↕</th>
        <th data-sort="exit_price">Exit ↕</th>
        <th data-sort="shares">Shares ↕</th>
        <th data-sort="holding_period">Days ↕</th>
        <th data-sort="return_pct">Return% ↕</th>
        <th data-sort="pnl">P&amp;L (USD) ↕</th>
        <th>P&amp;L (SAR)</th>
        <th>Actions</th>
      </tr>
    </thead>
    <tbody id="hist-body"><tr><td colspan="12" style="text-align:center;padding:40px" class="text-muted">Loading…</td></tr></tbody>
  </table>
</div>
<div class="pagination" id="pagination"></div>`;
  },

  async init() {
    await loadHistoryData();

    document.getElementById('apply-filters').addEventListener('click', async () => {
      histFilters = {
        ticker:     document.getElementById('hf-ticker').value.trim(),
        direction:  document.getElementById('hf-direction').value,
        trade_type: document.getElementById('hf-type').value,
        outcome:    document.getElementById('hf-outcome').value,
        date_from:  document.getElementById('hf-from').value,
        date_to:    document.getElementById('hf-to').value,
      };
      histPage = 1;
      await loadHistoryData();
    });

    document.getElementById('clear-filters').addEventListener('click', async () => {
      histFilters = {};
      histPage = 1;
      ['hf-ticker','hf-direction','hf-type','hf-outcome','hf-from','hf-to'].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.value = '';
      });
      await loadHistoryData();
    });

    // Column sort
    document.getElementById('hist-table').addEventListener('click', e => {
      const th = e.target.closest('th[data-sort]');
      if (!th) return;
      const col = th.dataset.sort;
      histSort.asc = histSort.col === col ? !histSort.asc : false;
      histSort.col = col;
      renderHistTable();
    });

    // Pagination
    document.getElementById('pagination').addEventListener('click', e => {
      const b = e.target.closest('button[data-p]');
      if (!b) return;
      histPage = parseInt(b.dataset.p);
      renderHistTable();
    });

    // Row actions
    document.getElementById('hist-body').addEventListener('click', e => {
      const row = e.target.closest('tr[data-id]');
      if (!row) return;
      if (e.target.closest('.btn-view'))   { window.location.hash = `trade-${row.dataset.id}`; return; }
      if (e.target.closest('.btn-delete')) { confirmDeleteTrade(parseInt(row.dataset.id)); return; }
      window.location.hash = `trade-${row.dataset.id}`;
    });

    // CSV export
    document.getElementById('export-csv').addEventListener('click', () => {
      window.location.href = '/api/export/csv' + buildQuery(histFilters);
    });
  },
});

async function loadHistoryData() {
  histTrades = await API.get('/api/trades' + buildQuery(histFilters));
  renderHistTable();
}

function renderHistTable() {
  const tbody   = document.getElementById('hist-body');
  const pagDiv  = document.getElementById('pagination');
  const summary = document.getElementById('hist-summary');

  if (!histTrades.length) {
    tbody.innerHTML = '<tr><td colspan="12" style="text-align:center;padding:40px" class="text-muted">No trades found.</td></tr>';
    pagDiv.innerHTML = '';
    if (summary) summary.textContent = '0 trades';
    return;
  }

  // Sort
  let sorted = [...histTrades];
  if (histSort.col) {
    sorted.sort((a, b) => {
      const av = a[histSort.col], bv = b[histSort.col];
      return (av < bv ? -1 : av > bv ? 1 : 0) * (histSort.asc ? 1 : -1);
    });
  }

  const total = sorted.length;
  const pages = Math.max(1, Math.ceil(total / PAGE_SIZE));
  histPage = Math.min(histPage, pages);
  const slice = sorted.slice((histPage - 1) * PAGE_SIZE, histPage * PAGE_SIZE);

  const totalPnl = histTrades.reduce((s, t) => s + t.pnl, 0);
  const wins = histTrades.filter(t => t.pnl > 0).length;
  if (summary) summary.textContent = `${total} trades · P&L: ${Fmt.usd(totalPnl, false)} · Win Rate: ${Fmt.pct1(total ? wins/total*100 : 0)}`;

  tbody.innerHTML = slice.map(t => `
    <tr class="clickable" data-id="${t.id}">
      <td>${Fmt.date(t.exit_date)}</td>
      <td class="fw-600">${t.ticker}</td>
      <td>${Fmt.dir(t.direction)}</td>
      <td>${Fmt.type(t.trade_type)}</td>
      <td>${Fmt.num(t.entry_price, 2)}</td>
      <td>${Fmt.num(t.exit_price, 2)}</td>
      <td>${Fmt.num(t.shares, 0)}</td>
      <td>${t.holding_period}d</td>
      <td class="${Fmt.cls(t.return_pct)}">${Fmt.pct(t.return_pct)}</td>
      <td class="${Fmt.cls(t.pnl)}">${Fmt.usd(t.pnl, false)}</td>
      <td class="${Fmt.cls(t.pnl)}">${Fmt.sar(t.pnl, sarRate)}</td>
      <td>
        <div class="btn-group" style="gap:4px">
          <button class="btn btn-sm btn-ghost btn-view">View</button>
          <button class="btn btn-sm btn-danger btn-delete">Del</button>
        </div>
      </td>
    </tr>`).join('');

  // Pagination
  const pageNums = [];
  for (let i = 1; i <= pages; i++) {
    if (i === 1 || i === pages || Math.abs(i - histPage) <= 2) pageNums.push(i);
    else if (pageNums[pageNums.length - 1] !== '…') pageNums.push('…');
  }

  pagDiv.innerHTML = [
    `<button class="btn btn-sm btn-ghost" data-p="${histPage - 1}" ${histPage === 1 ? 'disabled' : ''}>‹</button>`,
    ...pageNums.map(p => p === '…'
      ? `<span class="page-info">…</span>`
      : `<button class="btn btn-sm ${p === histPage ? 'btn-primary' : 'btn-ghost'}" data-p="${p}">${p}</button>`),
    `<button class="btn btn-sm btn-ghost" data-p="${histPage + 1}" ${histPage === pages ? 'disabled' : ''}>›</button>`,
    `<span class="page-info">${(histPage-1)*PAGE_SIZE+1}–${Math.min(histPage*PAGE_SIZE, total)} of ${total}</span>`,
  ].join('');
}

function confirmDeleteTrade(id) {
  showModal(`Delete trade #${id}? This cannot be undone.`, async () => {
    await API.delete(`/api/trades/${id}`);
    histTrades = histTrades.filter(t => t.id !== id);
    renderHistTable();
  });
}


// ── Trade Detail ──────────────────────────────────────────────────────────
registerPage('trade-detail', {
  render() { return '<div class="loading">Loading…</div>'; },

  async init() {
    const t = await API.get(`/api/trades/${currentTradeId}`);
    const content = document.getElementById('content');
    const sar = t.pnl * sarRate;
    const cls = Fmt.cls(t.pnl);

    content.innerHTML = `
<div class="flex-between mb-6" style="flex-wrap:wrap;gap:12px">
  <div class="page-header" style="margin-bottom:0;border-bottom:none">${t.ticker} — #${t.id}</div>
  <div class="btn-group">
    <button class="btn btn-ghost" onclick="window.location.hash='edit-${t.id}'">Edit Trade</button>
    <button class="btn btn-danger" id="del-btn">Delete Trade</button>
  </div>
</div>

<div class="grid-2 mb-6">
  <div class="kpi-card">
    <div class="kpi-label">P&amp;L</div>
    <div class="kpi-value ${cls}">${Fmt.usd(t.pnl, false)}</div>
    <div class="kpi-sub">${Fmt.sar(t.pnl, sarRate)}</div>
  </div>
  <div class="kpi-card">
    <div class="kpi-label">Return</div>
    <div class="kpi-value ${cls}">${Fmt.pct(t.return_pct)}</div>
    <div class="kpi-sub">${t.trade_type} · ${t.holding_period} day(s)</div>
  </div>
</div>

<div class="grid-2">
  <div class="card">
    <div class="card-title">Trade Details</div>
    ${[
      ['Ticker', `<strong>${t.ticker}</strong>`],
      ['Direction', Fmt.dir(t.direction)],
      ['Trade Type', Fmt.type(t.trade_type)],
      ['Entry Date', t.entry_date],
      ['Exit Date', t.exit_date],
      ['Days Held', t.holding_period],
    ].map(([l,v]) => `<div class="detail-row"><span class="detail-label">${l}</span><span class="detail-value">${v}</span></div>`).join('')}
  </div>
  <div class="card">
    <div class="card-title">Position</div>
    ${[
      ['Entry Price', '$' + Fmt.num(t.entry_price, 4)],
      ['Exit Price', '$' + Fmt.num(t.exit_price, 4)],
      ['Shares', Fmt.num(t.shares, 4)],
      ['Fees', '$' + Fmt.num(t.fees, 2)],
      ['Gross P&L (USD)', Fmt.usd(t.pnl, false)],
      ['Gross P&L (SAR)', Fmt.sar(t.pnl, sarRate)],
    ].map(([l,v]) => `<div class="detail-row"><span class="detail-label">${l}</span><span class="detail-value">${v}</span></div>`).join('')}
  </div>
</div>

${t.notes ? `<div class="card mt-4"><div class="card-title">Notes</div><p style="font-size:14px;line-height:1.7;white-space:pre-wrap">${t.notes}</p></div>` : ''}
`;

    document.getElementById('del-btn').addEventListener('click', () => {
      showModal(`Delete trade #${t.id} (${t.ticker})? This cannot be undone.`, async () => {
        await API.delete(`/api/trades/${t.id}`);
        window.location.hash = 'history';
      });
    });
  },
});
