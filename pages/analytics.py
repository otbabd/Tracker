import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from database import get_all_trades, get_setting
from calculations import compute_metrics, compute_streaks

sar_rate = float(get_setting("usd_sar_rate") or 3.75)

st.markdown('<div class="page-header">Analytics</div>', unsafe_allow_html=True)

# Filters
with st.expander("Filters", expanded=False):
    fc1, fc2, fc3 = st.columns(3)
    with fc1:
        f_ticker = st.text_input("Ticker", key="an_ticker")
        f_direction = st.selectbox("Direction", ["All", "Long", "Short"], key="an_dir")
    with fc2:
        f_type = st.selectbox("Trade Type", ["All", "Day Trade", "Swing Trade", "Position Trade", "Long Hold"], key="an_type")
    with fc3:
        f_date_from = st.date_input("From Date", value=None, key="an_from")
        f_date_to = st.date_input("To Date", value=None, key="an_to")

filters = {}
if f_ticker:
    filters["ticker"] = f_ticker
if f_direction != "All":
    filters["direction"] = f_direction
if f_type != "All":
    filters["trade_type"] = f_type
if f_date_from:
    filters["date_from"] = f_date_from.isoformat()
if f_date_to:
    filters["date_to"] = f_date_to.isoformat()

trades = get_all_trades(filters)

if not trades:
    st.info("No trades found.")
    st.stop()

metrics = compute_metrics(trades)
max_win_streak, max_loss_streak = compute_streaks(trades)

# ── Win/Loss Analysis ─────────────────────────────────────────────────────────
st.subheader("Win / Loss Analysis")
wl1, wl2, wl3, wl4 = st.columns(4)
wl1.metric("Winning Trades", metrics["winning_trades"])
wl2.metric("Losing Trades", metrics["losing_trades"])
wl3.metric("Win Rate", f"{metrics['win_rate']:.1f}%")
pf = metrics["profit_factor"]
wl4.metric("Profit Factor", "∞" if pf is None else f"{pf:.2f}")

wl5, wl6, wl7, wl8 = st.columns(4)
wl5.metric("Avg Winner", f"${metrics['avg_winner']:,.2f}")
wl6.metric("Avg Loser", f"-${metrics['avg_loser']:,.2f}")
wl7.metric("Largest Winner", f"${metrics['largest_winner']:,.2f}")
wl8.metric("Largest Loser", f"${metrics['largest_loser']:,.2f}")

s1, s2 = st.columns(2)
s1.metric("Largest Win Streak", max_win_streak)
s2.metric("Largest Loss Streak", max_loss_streak)

# Win vs Loss donut
fig_donut = go.Figure(go.Pie(
    labels=["Wins", "Losses"],
    values=[metrics["winning_trades"], metrics["losing_trades"]],
    hole=0.6,
    marker_colors=["#22c55e", "#ef4444"],
    textinfo="label+percent",
))
fig_donut.update_layout(
    plot_bgcolor="#0f0f1a", paper_bgcolor="#0f0f1a",
    font_color="#e0e0e0", showlegend=False,
    height=260, margin=dict(l=10, r=10, t=10, b=10),
)
st.plotly_chart(fig_donut, use_container_width=True)

st.markdown("---")

# ── Trade Type Analysis ───────────────────────────────────────────────────────
st.subheader("Performance by Trade Type")
df = pd.DataFrame(trades)

type_grp = df.groupby("trade_type").agg(
    Count=("pnl", "count"),
    Win_Rate=("pnl", lambda x: round((x > 0).sum() / len(x) * 100, 1)),
    PnL_USD=("pnl", "sum"),
).reset_index()
type_grp["PnL_SAR"] = (type_grp["PnL_USD"] * sar_rate).round(2)
type_grp["PnL_USD"] = type_grp["PnL_USD"].round(2)

bar_colors = ["#22c55e" if v >= 0 else "#ef4444" for v in type_grp["PnL_USD"]]
fig_bar = go.Figure(go.Bar(
    x=type_grp["trade_type"],
    y=type_grp["PnL_USD"],
    marker_color=bar_colors,
    text=type_grp["PnL_USD"].apply(lambda v: f"${v:,.0f}"),
    textposition="outside",
))
fig_bar.update_layout(
    plot_bgcolor="#0f0f1a", paper_bgcolor="#0f0f1a",
    font_color="#e0e0e0", height=280,
    xaxis=dict(gridcolor="#1e1e2e"),
    yaxis=dict(gridcolor="#1e1e2e", tickprefix="$", tickformat=",.0f"),
    margin=dict(l=10, r=10, t=10, b=10),
)
st.plotly_chart(fig_bar, use_container_width=True)

type_grp.columns = ["Trade Type", "Count", "Win Rate %", "P&L (USD)", "P&L (SAR)"]
st.dataframe(
    type_grp.style.format({"P&L (USD)": "${:,.2f}", "P&L (SAR)": "SAR {:,.2f}", "Win Rate %": "{:.1f}%"}),
    use_container_width=True, hide_index=True,
)

st.markdown("---")

# ── Performance by Ticker ─────────────────────────────────────────────────────
st.subheader("Performance by Ticker")
ticker_search = st.text_input("Search ticker", key="an_ticker_search")

ticker_grp = df.groupby("ticker").agg(
    Total_Trades=("pnl", "count"),
    Win_Rate=("pnl", lambda x: round((x > 0).sum() / len(x) * 100, 1)),
    Total_Profit=("pnl", "sum"),
    Avg_Return=("return_pct", "mean"),
).reset_index()
ticker_grp["SAR"] = (ticker_grp["Total_Profit"] * sar_rate).round(2)
ticker_grp["Total_Profit"] = ticker_grp["Total_Profit"].round(2)
ticker_grp["Avg_Return"] = ticker_grp["Avg_Return"].round(2)

sort_col = st.selectbox("Sort by", ["Total_Profit", "Win_Rate", "Total_Trades", "Avg_Return"],
                        format_func=lambda x: x.replace("_", " "), key="an_sort")
ticker_grp = ticker_grp.sort_values(sort_col, ascending=False)

if ticker_search:
    ticker_grp = ticker_grp[ticker_grp["ticker"].str.upper().str.contains(ticker_search.upper())]

ticker_grp.columns = ["Ticker", "Total Trades", "Win Rate %", "Total Profit (USD)", "Avg Return %", "Total Profit (SAR)"]
st.dataframe(
    ticker_grp.style.format({
        "Total Profit (USD)": "${:,.2f}",
        "Total Profit (SAR)": "SAR {:,.2f}",
        "Win Rate %": "{:.1f}%",
        "Avg Return %": "{:.2f}%",
    }),
    use_container_width=True, hide_index=True,
)

st.markdown("---")

# ── P&L Distribution ─────────────────────────────────────────────────────────
st.subheader("P&L Distribution")
fig_hist = px.histogram(
    df, x="pnl", nbins=30, color_discrete_sequence=["#5a5aff"],
    labels={"pnl": "P&L (USD)"},
)
fig_hist.add_vline(x=0, line_dash="dash", line_color="#ef4444", annotation_text="Break-even")
fig_hist.update_layout(
    plot_bgcolor="#0f0f1a", paper_bgcolor="#0f0f1a",
    font_color="#e0e0e0", height=280,
    xaxis=dict(gridcolor="#1e1e2e", tickprefix="$"),
    yaxis=dict(gridcolor="#1e1e2e"),
    margin=dict(l=10, r=10, t=10, b=10),
    bargap=0.1,
)
st.plotly_chart(fig_hist, use_container_width=True)
