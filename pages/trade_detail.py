import streamlit as st
from database import get_trade, delete_trade, get_setting

sar_rate = float(get_setting("usd_sar_rate") or 3.75)

trade_id = st.session_state.get("view_trade_id")
if not trade_id:
    st.warning("No trade selected. Go to Trade History and select a trade.")
    st.stop()

trade = get_trade(trade_id)
if not trade:
    st.error(f"Trade #{trade_id} not found.")
    st.stop()

st.markdown(f'<div class="page-header">Trade Detail — #{trade["id"]} {trade["ticker"]}</div>', unsafe_allow_html=True)

pnl = trade["pnl"]
pnl_sar = pnl * sar_rate
ret = trade["return_pct"]
pnl_color = "#22c55e" if pnl >= 0 else "#ef4444"

c1, c2 = st.columns(2)
with c1:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">P&L</div>
        <div class="metric-value" style="color:{pnl_color}">${pnl:,.2f}</div>
        <div class="metric-sub">SAR {pnl_sar:,.2f}</div>
    </div>""", unsafe_allow_html=True)
with c2:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">Return</div>
        <div class="metric-value" style="color:{pnl_color}">{ret:+.2f}%</div>
        <div class="metric-sub">{trade['trade_type']} · {trade['holding_period']} day(s)</div>
    </div>""", unsafe_allow_html=True)

st.markdown("")

d1, d2 = st.columns(2)
with d1:
    st.markdown("**Trade Details**")
    details = {
        "Ticker": trade["ticker"],
        "Direction": trade["direction"],
        "Trade Type": trade["trade_type"],
        "Entry Date": trade["entry_date"],
        "Exit Date": trade["exit_date"],
        "Days Held": trade["holding_period"],
    }
    for k, v in details.items():
        st.markdown(f"**{k}:** {v}")

with d2:
    st.markdown("**Price & Position**")
    details2 = {
        "Entry Price": f"${trade['entry_price']:,.4f}",
        "Exit Price": f"${trade['exit_price']:,.4f}",
        "Shares": f"{trade['shares']:,.4f}",
        "Fees": f"${trade['fees']:,.2f}",
    }
    for k, v in details2.items():
        st.markdown(f"**{k}:** {v}")

if trade.get("notes"):
    st.markdown("**Notes**")
    st.info(trade["notes"])

st.markdown("---")
btn1, btn2 = st.columns(2)
with btn1:
    if st.button("Edit Trade", use_container_width=True):
        st.query_params["edit_id"] = str(trade_id)
        st.switch_page("pages/trade_entry.py")

with btn2:
    if st.button("Delete Trade", use_container_width=True, type="primary"):
        if st.session_state.get("confirm_delete_detail") == trade_id:
            delete_trade(trade_id)
            st.session_state.pop("confirm_delete_detail", None)
            st.session_state.pop("view_trade_id", None)
            st.success("Trade deleted.")
            st.switch_page("pages/trade_history.py")
        else:
            st.session_state["confirm_delete_detail"] = trade_id
            st.warning("Click Delete Trade again to confirm.")
