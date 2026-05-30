import streamlit as st
import pandas as pd
from database import get_all_trades, delete_trade, get_setting
from exports import to_csv

sar_rate = float(get_setting("usd_sar_rate") or 3.75)

st.markdown('<div class="page-header">Trade History</div>', unsafe_allow_html=True)

# ── Filters ───────────────────────────────────────────────────────────────────
with st.expander("Filters", expanded=True):
    fc1, fc2, fc3, fc4 = st.columns(4)
    with fc1:
        f_ticker = st.text_input("Ticker")
        f_direction = st.selectbox("Direction", ["All", "Long", "Short"])
    with fc2:
        f_type = st.selectbox("Trade Type", ["All", "Day Trade", "Swing Trade", "Position Trade", "Long Hold"])
        f_outcome = st.selectbox("Outcome", ["All", "Win", "Loss"])
    with fc3:
        f_date_from = st.date_input("From Date", value=None)
    with fc4:
        f_date_to = st.date_input("To Date", value=None)

filters = {}
if f_ticker:
    filters["ticker"] = f_ticker
if f_direction != "All":
    filters["direction"] = f_direction
if f_type != "All":
    filters["trade_type"] = f_type
if f_outcome != "All":
    filters["outcome"] = f_outcome
if f_date_from:
    filters["date_from"] = f_date_from.isoformat()
if f_date_to:
    filters["date_to"] = f_date_to.isoformat()

trades = get_all_trades(filters)

if not trades:
    st.info("No trades found matching the filters.")
    st.stop()

# ── Metrics row ───────────────────────────────────────────────────────────────
from calculations import compute_metrics
m = compute_metrics(trades)
mc1, mc2, mc3, mc4 = st.columns(4)
mc1.metric("Total Trades", m["total_trades"])
pnl_color = "normal" if m["total_pnl"] == 0 else ("normal" if m["total_pnl"] > 0 else "inverse")
mc2.metric("Total P&L (USD)", f"${m['total_pnl']:,.2f}")
mc3.metric("Win Rate", f"{m['win_rate']:.1f}%")
pf = m['profit_factor']
mc4.metric("Profit Factor", "∞" if pf is None else f"{pf:.2f}")

# ── Table ─────────────────────────────────────────────────────────────────────
df = pd.DataFrame(trades)
df["pnl_sar"] = (df["pnl"] * sar_rate).round(2)

# Pagination
page_size = 25
total = len(df)
total_pages = max(1, (total + page_size - 1) // page_size)
page_col, export_col = st.columns([3, 1])
with page_col:
    page = st.number_input("Page", min_value=1, max_value=total_pages, value=1, step=1)
with export_col:
    csv_bytes = to_csv(trades, sar_rate)
    st.download_button("Export CSV", csv_bytes, "trades.csv", "text/csv", use_container_width=True)

start = (page - 1) * page_size
end = start + page_size
page_df = df.iloc[start:end].copy()

display_cols = {
    "exit_date": "Date", "ticker": "Ticker", "direction": "Dir",
    "trade_type": "Type", "entry_price": "Entry", "exit_price": "Exit",
    "shares": "Shares", "holding_period": "Days",
    "return_pct": "Return %", "pnl": "P&L (USD)", "pnl_sar": "P&L (SAR)", "id": "ID",
}
page_df = page_df[list(display_cols.keys())].rename(columns=display_cols)

def style_pnl(val):
    if isinstance(val, (int, float)):
        return "color: #22c55e" if val > 0 else ("color: #ef4444" if val < 0 else "")
    return ""

styled = page_df.style.applymap(style_pnl, subset=["P&L (USD)", "P&L (SAR)", "Return %"]).format({
    "Entry": "{:.2f}", "Exit": "{:.2f}", "Return %": "{:.2f}%",
    "P&L (USD)": "${:,.2f}", "P&L (SAR)": "SAR {:,.2f}",
})
st.dataframe(styled, use_container_width=True, hide_index=True)
st.caption(f"Showing {start+1}–{min(end, total)} of {total} trades")

# ── Trade detail / delete ─────────────────────────────────────────────────────
st.markdown("---")
st.subheader("Trade Actions")
action_col1, action_col2 = st.columns(2)
with action_col1:
    trade_ids = [t["id"] for t in trades]
    selected_id = st.selectbox("Select Trade ID", trade_ids, format_func=lambda x: f"#{x}")
with action_col2:
    view_btn = st.button("View / Edit", use_container_width=True)
    delete_btn = st.button("Delete", use_container_width=True, type="primary")

if view_btn and selected_id:
    st.switch_page("pages/trade_detail.py")

if delete_btn and selected_id:
    if st.session_state.get("confirm_delete") == selected_id:
        delete_trade(selected_id)
        st.success(f"Trade #{selected_id} deleted.")
        st.session_state.pop("confirm_delete", None)
        st.rerun()
    else:
        st.session_state["confirm_delete"] = selected_id
        st.warning(f"Click Delete again to confirm deletion of trade #{selected_id}.")

# Store selected trade id for detail page
if selected_id:
    st.session_state["view_trade_id"] = selected_id
