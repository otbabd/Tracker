import streamlit as st
from database import get_setting, set_setting

st.markdown('<div class="page-header">Settings</div>', unsafe_allow_html=True)

current_rate = float(get_setting("usd_sar_rate") or 3.75)

st.subheader("Currency Settings")
st.markdown("All trades are recorded in **USD**. SAR is a reference display currency only and does not affect any calculations.")

col1, col2 = st.columns([1, 1])
with col1:
    new_rate = st.number_input(
        "USD / SAR Exchange Rate",
        min_value=0.0001,
        value=current_rate,
        step=0.01,
        format="%.4f",
        help="Default: 3.75. This rate is used only for SAR display conversions.",
    )
    if st.button("Update Rate", use_container_width=True):
        set_setting("usd_sar_rate", str(new_rate))
        st.success(f"Exchange rate updated to {new_rate:.4f}")
        st.rerun()

with col2:
    st.markdown("**Currency Converter**")
    mode = st.radio("Convert", ["USD → SAR", "SAR → USD"], horizontal=True)
    amount = st.number_input("Amount", min_value=0.0, value=1000.0, step=0.01, format="%.2f")
    rate = float(get_setting("usd_sar_rate") or 3.75)
    if mode == "USD → SAR":
        result = amount * rate
        st.markdown(f"**${amount:,.2f} USD = SAR {result:,.2f}**")
    else:
        result = amount / rate
        st.markdown(f"**SAR {amount:,.2f} = ${result:,.2f} USD**")
    st.caption(f"Current rate: 1 USD = {rate:.4f} SAR")

st.markdown("---")
st.subheader("About")
st.markdown("""
**Trading Performance Tracker** — MVP v1.0

- All data stored locally in SQLite (`trades.db`)
- No internet connection required
- No external data transmission
- Primary currency: USD
- Reference currency: SAR (display only)
""")
