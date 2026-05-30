import io
import pandas as pd
from datetime import datetime


def trades_to_dataframe(trades: list[dict], sar_rate: float) -> pd.DataFrame:
    if not trades:
        return pd.DataFrame()
    df = pd.DataFrame(trades)
    df["pnl_sar"] = (df["pnl"] * sar_rate).round(2)
    df["return_pct"] = df["return_pct"].round(2)
    rename = {
        "id": "ID", "ticker": "Ticker", "direction": "Direction",
        "entry_date": "Entry Date", "exit_date": "Exit Date",
        "entry_price": "Entry Price", "exit_price": "Exit Price",
        "shares": "Shares", "fees": "Fees", "notes": "Notes",
        "trade_type": "Trade Type", "holding_period": "Days Held",
        "return_pct": "Return %", "pnl": "P&L (USD)", "pnl_sar": "P&L (SAR)",
        "created_at": "Created At", "updated_at": "Updated At",
    }
    df = df.rename(columns=rename)
    display_cols = ["ID", "Ticker", "Direction", "Trade Type", "Entry Date", "Exit Date",
                    "Days Held", "Entry Price", "Exit Price", "Shares", "Fees",
                    "Return %", "P&L (USD)", "P&L (SAR)", "Notes"]
    return df[[c for c in display_cols if c in df.columns]]


def to_csv(trades: list[dict], sar_rate: float) -> bytes:
    df = trades_to_dataframe(trades, sar_rate)
    return df.to_csv(index=False).encode("utf-8")


def to_excel(trades: list[dict], sar_rate: float, metrics: dict) -> bytes:
    buf = io.BytesIO()
    df = trades_to_dataframe(trades, sar_rate)

    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        # Summary sheet
        summary_data = {
            "Metric": [
                "Total Trades", "Total P&L (USD)", "Win Rate (%)",
                "Profit Factor", "Avg Winner (USD)", "Avg Loser (USD)",
                "Expectancy (USD)", "Gross Profit (USD)", "Gross Loss (USD)",
                "Report Generated",
            ],
            "Value": [
                metrics.get("total_trades", 0),
                metrics.get("total_pnl", 0),
                metrics.get("win_rate", 0),
                metrics.get("profit_factor", "∞") if metrics.get("profit_factor") is None else metrics.get("profit_factor"),
                metrics.get("avg_winner", 0),
                metrics.get("avg_loser", 0),
                metrics.get("expectancy", 0),
                metrics.get("gross_profit", 0),
                metrics.get("gross_loss", 0),
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            ],
        }
        pd.DataFrame(summary_data).to_excel(writer, sheet_name="Summary", index=False)
        df.to_excel(writer, sheet_name="Trade History", index=False)

        # Monthly performance sheet
        if not df.empty:
            df2 = df.copy()
            df2["Month"] = pd.to_datetime(df2["Exit Date"]).dt.to_period("M").astype(str)
            monthly = df2.groupby("Month").agg(
                Trades=("P&L (USD)", "count"),
                PnL_USD=("P&L (USD)", "sum"),
                PnL_SAR=("P&L (SAR)", "sum"),
                Win_Rate=("P&L (USD)", lambda x: round((x > 0).sum() / len(x) * 100, 2)),
            ).reset_index()
            monthly.columns = ["Month", "Trades", "P&L (USD)", "P&L (SAR)", "Win Rate (%)"]
            monthly.to_excel(writer, sheet_name="Monthly Performance", index=False)

    return buf.getvalue()


def to_pdf(trades: list[dict], sar_rate: float, metrics: dict) -> bytes:
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.units import cm
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=landscape(A4),
                            leftMargin=1.5*cm, rightMargin=1.5*cm,
                            topMargin=1.5*cm, bottomMargin=1.5*cm)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("title", parent=styles["Title"], alignment=TA_CENTER)
    heading_style = ParagraphStyle("h2", parent=styles["Heading2"])

    story = []

    # Title
    story.append(Paragraph("Trading Performance Report", title_style))
    story.append(Paragraph(
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | "
        f"USD/SAR Rate: {sar_rate}",
        styles["Normal"]
    ))
    story.append(Spacer(1, 0.5*cm))

    # Summary metrics table
    story.append(Paragraph("Performance Summary", heading_style))
    pf_val = "∞" if metrics.get("profit_factor") is None else f"{metrics.get('profit_factor', 0):.2f}"
    summary_rows = [
        ["Metric", "Value"],
        ["Total Trades", str(metrics.get("total_trades", 0))],
        ["Total P&L (USD)", f"${metrics.get('total_pnl', 0):,.2f}"],
        ["Total P&L (SAR)", f"SAR {metrics.get('total_pnl', 0) * sar_rate:,.2f}"],
        ["Win Rate", f"{metrics.get('win_rate', 0):.1f}%"],
        ["Profit Factor", pf_val],
        ["Avg Winner (USD)", f"${metrics.get('avg_winner', 0):,.2f}"],
        ["Avg Loser (USD)", f"${metrics.get('avg_loser', 0):,.2f}"],
        ["Expectancy (USD)", f"${metrics.get('expectancy', 0):,.2f}"],
    ]
    t = Table(summary_rows, colWidths=[6*cm, 5*cm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a1a2e")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8f9fa")]),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#dee2e6")),
        ("PADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(t)
    story.append(Spacer(1, 0.5*cm))

    # Trade history table
    if trades:
        story.append(Paragraph("Trade History", heading_style))
        headers = ["Date", "Ticker", "Dir", "Type", "Entry", "Exit", "Shares", "Days", "Return%", "P&L (USD)", "P&L (SAR)"]
        rows = [headers]
        for tr in trades:
            pnl_sar = tr["pnl"] * sar_rate
            rows.append([
                tr["exit_date"],
                tr["ticker"],
                tr["direction"],
                tr["trade_type"],
                f"{tr['entry_price']:.2f}",
                f"{tr['exit_price']:.2f}",
                f"{tr['shares']:.0f}",
                str(tr["holding_period"]),
                f"{tr['return_pct']:.2f}%",
                f"${tr['pnl']:,.2f}",
                f"SAR {pnl_sar:,.2f}",
            ])

        col_widths = [2.2*cm, 1.8*cm, 1.2*cm, 2.5*cm, 1.8*cm, 1.8*cm, 1.8*cm, 1.2*cm, 1.8*cm, 2.5*cm, 2.8*cm]
        trade_table = Table(rows, colWidths=col_widths, repeatRows=1)
        trade_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a1a2e")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 7.5),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8f9fa")]),
            ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#dee2e6")),
            ("PADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(trade_table)

    doc.build(story)
    return buf.getvalue()
