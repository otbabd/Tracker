import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from database import get_all_trades, get_setting
from calculations import compute_metrics

sar_rate = float(get_setting("usd_sar_rate") or 3.75)
trades = get_all_trades()

st.markdown('<div class="page-header">Dashboard</div>', unsafe_allow_html=True)

if not trades:
    st.info("No trades recorded yet. Add your first trade to see the dashboard.")
    st.stop()

metrics = compute_metrics(trades)

# ── KPI Cards ────────────────────────────────────────────────────────────────
def color_val(val, prefix="$"):
    cls = "positive" if val > 0 else ("negative" if val < 0 else "")
    return f'<span class="{cls}">{prefix}{val:,.2f}</span>'

c1, c2, c3, c4 = st.columns(4)
total_pnl = metrics["total_pnl"]
with c1:
    sar_equiv = total_pnl * sar_rate
    color = "positive" if total_pnl >= 0 else "negative"
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">Total Realized P&L</div>
        <div class="metric-value {color}">${total_pnl:,.2f}</div>
        <div class="metric-sub">SAR {sar_equiv:,.2f}</div>
    </div>""", unsafe_allow_html=True)
with c2:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">Total Trades</div>
        <div class="metric-value">{metrics['total_trades']}</div>
        <div class="metric-sub">{metrics['winning_trades']} W / {metrics['losing_trades']} L</div>
    </div>""", unsafe_allow_html=True)
with c3:
    wr = metrics["win_rate"]
    wr_color = "positive" if wr >= 50 else "negative"
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">Win Rate</div>
        <div class="metric-value {wr_color}">{wr:.1f}%</div>
        <div class="metric-sub">Profit Factor: {"∞" if metrics["profit_factor"] is None else f"{metrics['profit_factor']:.2f}"}</div>
    </div>""", unsafe_allow_html=True)
with c4:
    exp = metrics["expectancy"]
    exp_color = "positive" if exp >= 0 else "negative"
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">Expectancy</div>
        <div class="metric-value {exp_color}">${exp:,.2f}</div>
        <div class="metric-sub">Per trade average</div>
    </div>""", unsafe_allow_html=True)

st.markdown("")
c5, c6 = st.columns(2)
with c5:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">Avg Winning Trade</div>
        <div class="metric-value positive">${metrics['avg_winner']:,.2f}</div>
        <div class="metric-sub">SAR {metrics['avg_winner'] * sar_rate:,.2f}</div>
    </div>""", unsafe_allow_html=True)
with c6:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">Avg Losing Trade</div>
        <div class="metric-value negative">-${metrics['avg_loser']:,.2f}</div>
        <div class="metric-sub">SAR -{metrics['avg_loser'] * sar_rate:,.2f}</div>
    </div>""", unsafe_allow_html=True)

st.markdown("---")

# ── Cumulative P&L Chart ─────────────────────────────────────────────────────
st.subheader("Cumulative P&L")

df = pd.DataFrame(trades)
df["exit_date"] = pd.to_datetime(df["exit_date"])
df = df.sort_values("exit_date")

view_col, currency_col = st.columns([3, 1])
with view_col:
    view = st.radio("View", ["All", "Yearly", "Monthly", "Daily"], horizontal=True, key="chart_view")
with currency_col:
    chart_currency = st.radio("Currency", ["USD", "SAR"], horizontal=True, key="chart_currency")

if view == "Daily":
    grouped = df.groupby("exit_date")["pnl"].sum().reset_index()
elif view == "Monthly":
    df["period"] = df["exit_date"].dt.to_period("M").dt.to_timestamp()
    grouped = df.groupby("period")["pnl"].sum().reset_index().rename(columns={"period": "exit_date"})
elif view == "Yearly":
    df["period"] = df["exit_date"].dt.to_period("Y").dt.to_timestamp()
    grouped = df.groupby("period")["pnl"].sum().reset_index().rename(columns={"period": "exit_date"})
else:
    grouped = df.groupby("exit_date")["pnl"].sum().reset_index()

grouped = grouped.sort_values("exit_date")
grouped["cumulative"] = grouped["pnl"].cumsum()
y_col = "cumulative"
multiplier = sar_rate if chart_currency == "SAR" else 1.0
grouped["display"] = grouped[y_col] * multiplier
currency_prefix = "SAR " if chart_currency == "SAR" else "$"

fig = go.Figure()
fig.add_trace(go.Scatter(
    x=grouped["exit_date"],
    y=grouped["display"],
    mode="lines+markers",
    line=dict(color="#5a5aff", width=2),
    marker=dict(size=5),
    fill="tozeroy",
    fillcolor="rgba(90,90,255,0.1)",
    hovertemplate=f"%{{x|%Y-%m-%d}}<br>Cumulative P&L: {currency_prefix}%{{y:,.2f}}<extra></extra>",
))
fig.update_layout(
    plot_bgcolor="#0f0f1a",
    paper_bgcolor="#0f0f1a",
    font_color="#e0e0e0",
    xaxis=dict(gridcolor="#1e1e2e", showgrid=True),
    yaxis=dict(gridcolor="#1e1e2e", showgrid=True,
               tickprefix=currency_prefix, tickformat=",.0f"),
    margin=dict(l=10, r=10, t=10, b=10),
    height=320,
    hovermode="x unified",
)
st.plotly_chart(fig, use_container_width=True)

# ── Monthly Performance + Recent Trades ──────────────────────────────────────
left, right = st.columns([1, 1])

with left:
    st.subheader("Monthly Performance")
    df2 = pd.DataFrame(trades)
    df2["exit_date"] = pd.to_datetime(df2["exit_date"])
    df2["Month"] = df2["exit_date"].dt.to_period("M").astype(str)
    monthly = df2.groupby("Month").agg(
        Trades=("pnl", "count"),
        PnL_USD=("pnl", "sum"),
        Win_Rate=("pnl", lambda x: round((x > 0).sum() / len(x) * 100, 1)),
    ).reset_index().sort_values("Month", ascending=False)
    monthly["PnL_SAR"] = (monthly["PnL_USD"] * sar_rate).round(2)
    monthly["PnL_USD"] = monthly["PnL_USD"].round(2)

    def highlight_month(row):
        color = "#0d2b1a" if row["PnL_USD"] > 0 else "#2b0d0d"
        return [f"background-color: {color}"] * len(row)

    styled = monthly[["Month", "Trades", "PnL_USD", "PnL_SAR", "Win_Rate"]].rename(columns={
        "PnL_USD": "P&L (USD)", "PnL_SAR": "P&L (SAR)", "Win_Rate": "Win Rate %"
    }).style.apply(highlight_month, axis=1).format({
        "P&L (USD)": "${:,.2f}", "P&L (SAR)": "SAR {:,.2f}", "Win Rate %": "{:.1f}%"
    })
    st.dataframe(styled, use_container_width=True, hide_index=True)

with right:
    st.subheader("Recent Trades")
    recent = pd.DataFrame(trades[:10])
    if not recent.empty:
        recent["pnl_display"] = recent["pnl"].apply(lambda x: f"+${x:,.2f}" if x > 0 else f"-${abs(x):,.2f}")
        display_cols = {
            "exit_date": "Date", "ticker": "Ticker", "direction": "Dir",
            "trade_type": "Type", "entry_price": "Entry",
            "exit_price": "Exit", "holding_period": "Days", "pnl_display": "P&L"
        }
        recent_display = recent[list(display_cols.keys())].rename(columns=display_cols)

        def color_pnl(val):
            if val.startswith("+"):
                return "color: #22c55e"
            elif val.startswith("-"):
                return "color: #ef4444"
            return ""

        styled_recent = recent_display.style.applymap(color_pnl, subset=["P&L"])
        st.dataframe(styled_recent, use_container_width=True, hide_index=True)

# ── Performance by Ticker ─────────────────────────────────────────────────────
st.subheader("Performance by Ticker")
df3 = pd.DataFrame(trades)
sort_by = st.selectbox("Sort by", ["Total P&L", "Win Rate", "Trades"], key="ticker_sort")

ticker_grp = df3.groupby("ticker").agg(
    Trades=("pnl", "count"),
    Win_Rate=("pnl", lambda x: round((x > 0).sum() / len(x) * 100, 1)),
    Total_PnL=("pnl", "sum"),
).reset_index()
ticker_grp["Total_SAR"] = (ticker_grp["Total_PnL"] * sar_rate).round(2)
ticker_grp["Total_PnL"] = ticker_grp["Total_PnL"].round(2)

sort_map = {"Total P&L": "Total_PnL", "Win Rate": "Win_Rate", "Trades": "Trades"}
ticker_grp = ticker_grp.sort_values(sort_map[sort_by], ascending=False)

ticker_search = st.text_input("Search ticker", key="ticker_search_dash")
if ticker_search:
    ticker_grp = ticker_grp[ticker_grp["ticker"].str.upper().str.contains(ticker_search.upper())]

ticker_grp.columns = ["Ticker", "Trades", "Win Rate %", "P&L (USD)", "P&L (SAR)"]
st.dataframe(
    ticker_grp.style.format({"P&L (USD)": "${:,.2f}", "P&L (SAR)": "SAR {:,.2f}", "Win Rate %": "{:.1f}%"}),
    use_container_width=True, hide_index=True,
)
