registerPage('settings', {
  render() {
    return `
<div class="page-header">Settings</div>

<div class="grid-2">
  <div class="card">
    <div class="card-title">USD / SAR Exchange Rate</div>
    <p style="font-size:13.5px;color:var(--text-dim);margin-bottom:16px;line-height:1.6">
      All trades are stored and calculated in <strong>USD</strong>.
      SAR values are for display reference only and do not affect any calculations.
    </p>
    <div id="rate-alert"></div>
    <div class="form-group mb-4">
      <label>Exchange Rate (1 USD = ? SAR)</label>
      <input type="number" id="sar-rate-input" min="0.0001" step="0.0001" placeholder="3.75">
    </div>
    <button class="btn btn-primary" id="save-rate">Update Rate</button>
  </div>

  <div class="card">
    <div class="card-title">Currency Converter</div>
    <p style="font-size:13px;color:var(--text-muted);margin-bottom:16px">Reference only — does not affect trade records.</p>
    <div class="form-group mb-4">
      <label>Convert</label>
      <select id="conv-mode">
        <option value="usd-sar">USD → SAR</option>
        <option value="sar-usd">SAR → USD</option>
      </select>
    </div>
    <div class="form-group mb-4">
      <label>Amount</label>
      <input type="number" id="conv-amount" min="0" step="0.01" value="1000">
    </div>
    <div class="card" style="background:var(--surface3);border-color:var(--border)">
      <div id="conv-result" style="font-size:18px;font-weight:700;text-align:center;padding:8px">—</div>
      <div id="conv-rate-label" style="font-size:12px;color:var(--text-muted);text-align:center;margin-top:4px"></div>
    </div>
  </div>
</div>

<div class="card mt-4">
  <div class="card-title">About</div>
  <div style="font-size:13.5px;color:var(--text-dim);line-height:1.8">
    <p><strong>Trading Performance Tracker</strong> — MVP v1.0</p>
    <p>• All data stored locally in SQLite</p>
    <p>• No external data transmission</p>
    <p>• Primary currency: USD &nbsp;·&nbsp; Reference currency: SAR (display only)</p>
    <p>• Supports Long and Short trades with automatic classification</p>
  </div>
</div>`;
  },

  async init() {
    const s = await API.get('/api/settings');
    sarRate = s.usd_sar_rate;
    document.getElementById('sar-rate-input').value = sarRate;

    const updateConverter = () => {
      const mode   = document.getElementById('conv-mode').value;
      const amount = parseFloat(document.getElementById('conv-amount').value) || 0;
      const rate   = parseFloat(document.getElementById('sar-rate-input').value) || sarRate;
      const result = mode === 'usd-sar' ? amount * rate : amount / rate;
      const from   = mode === 'usd-sar' ? `$${amount.toLocaleString('en-US', {minimumFractionDigits:2})} USD` : `SAR ${amount.toLocaleString('en-US', {minimumFractionDigits:2})}`;
      const to     = mode === 'usd-sar' ? `SAR ${result.toLocaleString('en-US', {minimumFractionDigits:2})}` : `$${result.toLocaleString('en-US', {minimumFractionDigits:2})} USD`;
      document.getElementById('conv-result').textContent = `${from} = ${to}`;
      document.getElementById('conv-rate-label').textContent = `Rate: 1 USD = ${rate.toFixed(4)} SAR`;
    };

    updateConverter();
    document.getElementById('conv-mode').addEventListener('change', updateConverter);
    document.getElementById('conv-amount').addEventListener('input', updateConverter);
    document.getElementById('sar-rate-input').addEventListener('input', updateConverter);

    document.getElementById('save-rate').addEventListener('click', async () => {
      const alertEl = document.getElementById('rate-alert');
      const rate = parseFloat(document.getElementById('sar-rate-input').value);
      if (!rate || rate <= 0) {
        alertEl.innerHTML = '<div class="alert alert-error">Rate must be greater than 0.</div>';
        return;
      }
      try {
        await API.put('/api/settings', { usd_sar_rate: rate });
        sarRate = rate;
        alertEl.innerHTML = `<div class="alert alert-success">Rate updated to ${rate.toFixed(4)}.</div>`;
        setTimeout(() => { alertEl.innerHTML = ''; }, 3000);
      } catch (e) {
        alertEl.innerHTML = `<div class="alert alert-error">${e.detail || 'Failed to update.'}</div>`;
      }
    });
  },
});
