import streamlit as st
from datetime import date
from database import insert_trade, get_trade, update_trade, get_setting
from calculations import build_trade_record, calc_pnl, calc_return_pct, classify_trade

sar_rate = float(get_setting("usd_sar_rate") or 3.75)

# Support edit mode via query params
edit_id = st.query_params.get("edit_id")
edit_trade = get_trade(int(edit_id)) if edit_id else None

title = "Edit Trade" if edit_trade else "Add Trade"
st.markdown(f'<div class="page-header">{title}</div>', unsafe_allow_html=True)

with st.form("trade_form", clear_on_submit=not edit_trade):
    c1, c2 = st.columns(2)
    with c1:
        ticker = st.text_input("Ticker *", value=edit_trade["ticker"] if edit_trade else "").upper().strip()
        direction = st.selectbox("Direction *", ["Long", "Short"],
                                 index=0 if not edit_trade else ["Long", "Short"].index(edit_trade["direction"]))
        entry_date = st.date_input("Entry Date *",
                                   value=date.fromisoformat(edit_trade["entry_date"]) if edit_trade else date.today())
        exit_date = st.date_input("Exit Date *",
                                  value=date.fromisoformat(edit_trade["exit_date"]) if edit_trade else date.today())
    with c2:
        entry_price = st.number_input("Entry Price * ($)", min_value=0.0001, step=0.01,
                                      value=float(edit_trade["entry_price"]) if edit_trade else 0.01,
                                      format="%.4f")
        exit_price = st.number_input("Exit Price * ($)", min_value=0.0001, step=0.01,
                                     value=float(edit_trade["exit_price"]) if edit_trade else 0.01,
                                     format="%.4f")
        shares = st.number_input("Shares *", min_value=0.0001, step=1.0,
                                 value=float(edit_trade["shares"]) if edit_trade else 1.0, format="%.4f")
        fees = st.number_input("Fees ($)", min_value=0.0, step=0.01,
                               value=float(edit_trade["fees"]) if edit_trade else 0.0, format="%.2f")

    notes = st.text_area("Notes", value=edit_trade["notes"] if edit_trade else "")

    # Live preview
    if entry_price > 0 and exit_price > 0 and shares > 0 and ticker:
        pnl = calc_pnl(direction, entry_price, exit_price, shares, fees)
        ret = calc_return_pct(direction, entry_price, exit_price)
        ttype, days = classify_trade(entry_date, exit_date)
        pnl_sar = pnl * sar_rate
        pnl_color = "#22c55e" if pnl >= 0 else "#ef4444"
        st.markdown(f"""
        <div style="background:#1a1a2e;border:1px solid #2d2d44;border-radius:10px;padding:14px;margin:10px 0">
            <b>Preview</b><br>
            P&L: <span style="color:{pnl_color};font-weight:700">${pnl:,.2f}</span>
            &nbsp;·&nbsp; SAR {pnl_sar:,.2f}
            &nbsp;·&nbsp; Return: <span style="color:{pnl_color}">{ret:.2f}%</span>
            &nbsp;·&nbsp; Type: <b>{ttype}</b> ({days} day{"s" if days != 1 else ""})
        </div>""", unsafe_allow_html=True)

    submitted = st.form_submit_button("Save Trade" if edit_trade else "Add Trade", use_container_width=True)

if submitted:
    errors = []
    if not ticker:
        errors.append("Ticker cannot be empty.")
    if entry_price <= 0:
        errors.append("Entry Price must be > 0.")
    if exit_price <= 0:
        errors.append("Exit Price must be > 0.")
    if shares <= 0:
        errors.append("Shares must be > 0.")
    if fees < 0:
        errors.append("Fees must be ≥ 0.")
    if exit_date < entry_date:
        errors.append("Exit Date must be on or after Entry Date.")

    if errors:
        for e in errors:
            st.error(e)
    else:
        raw = {
            "ticker": ticker,
            "direction": direction,
            "entry_date": entry_date.isoformat(),
            "exit_date": exit_date.isoformat(),
            "entry_price": entry_price,
            "exit_price": exit_price,
            "shares": shares,
            "fees": fees,
            "notes": notes,
        }
        record = build_trade_record(raw)
        if edit_trade:
            update_trade(int(edit_id), record)
            st.success(f"Trade updated. P&L: ${record['pnl']:,.2f}")
        else:
            insert_trade(record)
            st.success(f"Trade added. P&L: ${record['pnl']:,.2f}")
            st.rerun()
