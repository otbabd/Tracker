import streamlit as st
from datetime import datetime
from database import get_all_trades, get_setting
from calculations import compute_metrics
from exports import to_csv, to_excel, to_pdf

sar_rate = float(get_setting("usd_sar_rate") or 3.75)

st.markdown('<div class="page-header">Reports & Export</div>', unsafe_allow_html=True)

# Filters
with st.expander("Filter Dataset", expanded=True):
    fc1, fc2, fc3, fc4 = st.columns(4)
    with fc1:
        f_ticker = st.text_input("Ticker", key="rep_ticker")
        f_direction = st.selectbox("Direction", ["All", "Long", "Short"], key="rep_dir")
    with fc2:
        f_type = st.selectbox("Trade Type", ["All", "Day Trade", "Swing Trade", "Position Trade", "Long Hold"], key="rep_type")
        f_outcome = st.selectbox("Outcome", ["All", "Win", "Loss"], key="rep_outcome")
    with fc3:
        f_date_from = st.date_input("From Date", value=None, key="rep_from")
    with fc4:
        f_date_to = st.date_input("To Date", value=None, key="rep_to")

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
metrics = compute_metrics(trades)
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

st.info(f"Dataset: **{len(trades)} trades** | Total P&L: **${metrics['total_pnl']:,.2f}** | Win Rate: **{metrics['win_rate']:.1f}%**")

if not trades:
    st.warning("No trades in the current filter. Adjust filters to include data.")
    st.stop()

st.markdown("---")
st.subheader("Download Reports")

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("**CSV Export**")
    st.caption("Raw trade data as comma-separated values.")
    csv_bytes = to_csv(trades, sar_rate)
    st.download_button(
        "Download CSV", csv_bytes,
        file_name=f"trades_{timestamp}.csv",
        mime="text/csv",
        use_container_width=True,
    )

with col2:
    st.markdown("**Excel Export**")
    st.caption("Multi-sheet workbook: Summary + Trade History + Monthly.")
    excel_bytes = to_excel(trades, sar_rate, metrics)
    st.download_button(
        "Download Excel", excel_bytes,
        file_name=f"trades_{timestamp}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
    )

with col3:
    st.markdown("**PDF Report**")
    st.caption("Formatted report with summary metrics and trade history.")
    pdf_bytes = to_pdf(trades, sar_rate, metrics)
    st.download_button(
        "Download PDF", pdf_bytes,
        file_name=f"trades_{timestamp}.pdf",
        mime="application/pdf",
        use_container_width=True,
    )

st.markdown("---")

# Summary preview
st.subheader("Report Preview — Performance Summary")
m = metrics
pf = m["profit_factor"]

sc1, sc2 = st.columns(2)
with sc1:
    rows = [
        ("Total Trades", str(m["total_trades"])),
        ("Winning Trades", str(m["winning_trades"])),
        ("Losing Trades", str(m["losing_trades"])),
        ("Win Rate", f"{m['win_rate']:.1f}%"),
        ("Profit Factor", "∞" if pf is None else f"{pf:.2f}"),
    ]
    for label, val in rows:
        c_l, c_v = st.columns([2, 1])
        c_l.markdown(f"**{label}**")
        c_v.markdown(val)

with sc2:
    rows2 = [
        ("Total P&L (USD)", f"${m['total_pnl']:,.2f}"),
        ("Total P&L (SAR)", f"SAR {m['total_pnl'] * sar_rate:,.2f}"),
        ("Avg Winner (USD)", f"${m['avg_winner']:,.2f}"),
        ("Avg Loser (USD)", f"-${m['avg_loser']:,.2f}"),
        ("Expectancy (USD)", f"${m['expectancy']:,.2f}"),
    ]
    for label, val in rows2:
        c_l, c_v = st.columns([2, 1])
        c_l.markdown(f"**{label}**")
        c_v.markdown(val)
