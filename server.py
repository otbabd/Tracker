from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import pandas as pd

from database import (
    init_db, insert_trade, update_trade, delete_trade,
    get_trade, get_all_trades, get_setting, set_setting,
)
from calculations import build_trade_record, compute_metrics, compute_streaks
from exports import to_csv, to_excel, to_pdf

import org_db
from org_api import router as org_router

app = FastAPI(title="Trading Performance Tracker")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
init_db()
org_db.init_db()
app.include_router(org_router)


class TradeIn(BaseModel):
    ticker: str
    direction: str
    entry_date: str
    exit_date: str
    entry_price: float
    exit_price: float
    shares: float
    fees: float = 0.0
    notes: str = ""


class SettingIn(BaseModel):
    usd_sar_rate: float


def _f(ticker=None, direction=None, trade_type=None, date_from=None, date_to=None, outcome=None):
    f = {}
    if ticker: f["ticker"] = ticker
    if direction and direction != "All": f["direction"] = direction
    if trade_type and trade_type != "All": f["trade_type"] = trade_type
    if date_from: f["date_from"] = date_from
    if date_to: f["date_to"] = date_to
    if outcome and outcome != "All": f["outcome"] = outcome
    return f


def _validate(t: TradeIn):
    errors = []
    if not t.ticker.strip(): errors.append("Ticker cannot be empty")
    if t.direction not in ("Long", "Short"): errors.append("Direction must be Long or Short")
    if t.entry_price <= 0: errors.append("Entry price must be > 0")
    if t.exit_price <= 0: errors.append("Exit price must be > 0")
    if t.shares <= 0: errors.append("Shares must be > 0")
    if t.fees < 0: errors.append("Fees must be >= 0")
    if t.exit_date < t.entry_date: errors.append("Exit date must be on or after entry date")
    if errors: raise HTTPException(422, detail=errors)


# ── Trade CRUD ────────────────────────────────────────────────────────────────

@app.get("/api/trades")
def list_trades(ticker: Optional[str]=None, direction: Optional[str]=None,
                trade_type: Optional[str]=None, date_from: Optional[str]=None,
                date_to: Optional[str]=None, outcome: Optional[str]=None,
                limit: Optional[int]=None):
    trades = get_all_trades(_f(ticker, direction, trade_type, date_from, date_to, outcome))
    return trades[:limit] if limit else trades


@app.post("/api/trades", status_code=201)
def create_trade(t: TradeIn):
    _validate(t)
    record = build_trade_record(t.model_dump())
    trade_id = insert_trade(record)
    return {"id": trade_id, **record}


@app.get("/api/trades/{trade_id}")
def read_trade(trade_id: int):
    t = get_trade(trade_id)
    if not t: raise HTTPException(404, "Not found")
    return t


@app.put("/api/trades/{trade_id}")
def edit_trade(trade_id: int, t: TradeIn):
    if not get_trade(trade_id): raise HTTPException(404, "Not found")
    _validate(t)
    record = build_trade_record(t.model_dump())
    update_trade(trade_id, record)
    return {"id": trade_id, **record}


@app.delete("/api/trades/{trade_id}", status_code=204)
def remove_trade(trade_id: int):
    if not get_trade(trade_id): raise HTTPException(404, "Not found")
    delete_trade(trade_id)


# ── Analytics ─────────────────────────────────────────────────────────────────

@app.get("/api/metrics")
def metrics(ticker: Optional[str]=None, direction: Optional[str]=None,
            trade_type: Optional[str]=None, date_from: Optional[str]=None,
            date_to: Optional[str]=None, outcome: Optional[str]=None):
    trades = get_all_trades(_f(ticker, direction, trade_type, date_from, date_to, outcome))
    m = compute_metrics(trades)
    w, l = compute_streaks(trades)
    m["win_streak"] = w
    m["loss_streak"] = l
    return m


@app.get("/api/cumulative")
def cumulative(period: str="all", ticker: Optional[str]=None,
               direction: Optional[str]=None, trade_type: Optional[str]=None,
               date_from: Optional[str]=None, date_to: Optional[str]=None):
    trades = get_all_trades(_f(ticker, direction, trade_type, date_from, date_to))
    if not trades: return []
    df = pd.DataFrame(trades)
    df["exit_date"] = pd.to_datetime(df["exit_date"])
    df = df.sort_values("exit_date")
    if period == "monthly":
        df["p"] = df["exit_date"].dt.to_period("M").dt.to_timestamp()
    elif period == "yearly":
        df["p"] = df["exit_date"].dt.to_period("Y").dt.to_timestamp()
    else:
        df["p"] = df["exit_date"]
    g = df.groupby("p")["pnl"].sum().reset_index()
    g["cumulative"] = g["pnl"].cumsum().round(2)
    g["date"] = g["p"].dt.strftime("%Y-%m-%d")
    return g[["date", "cumulative"]].to_dict("records")


@app.get("/api/monthly")
def monthly():
    trades = get_all_trades()
    if not trades: return []
    df = pd.DataFrame(trades)
    df["exit_date"] = pd.to_datetime(df["exit_date"])
    df["month"] = df["exit_date"].dt.to_period("M").astype(str)
    g = df.groupby("month").agg(
        trades=("pnl", "count"),
        pnl=("pnl", "sum"),
        win_rate=("pnl", lambda x: round((x > 0).sum() / len(x) * 100, 1))
    ).reset_index().sort_values("month", ascending=False)
    g["pnl"] = g["pnl"].round(2)
    return g.to_dict("records")


@app.get("/api/ticker-stats")
def ticker_stats(ticker: Optional[str]=None, direction: Optional[str]=None,
                 trade_type: Optional[str]=None, date_from: Optional[str]=None,
                 date_to: Optional[str]=None, outcome: Optional[str]=None,
                 sort_by: str="pnl"):
    trades = get_all_trades(_f(ticker, direction, trade_type, date_from, date_to, outcome))
    if not trades: return []
    df = pd.DataFrame(trades)
    g = df.groupby("ticker").agg(
        trades=("pnl", "count"),
        win_rate=("pnl", lambda x: round((x > 0).sum() / len(x) * 100, 1)),
        pnl=("pnl", "sum"),
        avg_return=("return_pct", "mean"),
    ).reset_index()
    g["pnl"] = g["pnl"].round(2)
    g["avg_return"] = g["avg_return"].round(2)
    col = {"win_rate": "win_rate", "trades": "trades"}.get(sort_by, "pnl")
    return g.sort_values(col, ascending=False).to_dict("records")


@app.get("/api/trade-type-stats")
def trade_type_stats(date_from: Optional[str]=None, date_to: Optional[str]=None):
    trades = get_all_trades(_f(date_from=date_from, date_to=date_to))
    if not trades: return []
    df = pd.DataFrame(trades)
    g = df.groupby("trade_type").agg(
        trades=("pnl", "count"),
        win_rate=("pnl", lambda x: round((x > 0).sum() / len(x) * 100, 1)),
        pnl=("pnl", "sum"),
    ).reset_index()
    g["pnl"] = g["pnl"].round(2)
    return g.to_dict("records")


@app.get("/api/pnl-values")
def pnl_values(ticker: Optional[str]=None, direction: Optional[str]=None,
               trade_type: Optional[str]=None, date_from: Optional[str]=None,
               date_to: Optional[str]=None):
    trades = get_all_trades(_f(ticker, direction, trade_type, date_from, date_to))
    return [t["pnl"] for t in trades]


# ── Settings ──────────────────────────────────────────────────────────────────

@app.get("/api/settings")
def get_settings():
    return {"usd_sar_rate": float(get_setting("usd_sar_rate") or 3.75)}


@app.put("/api/settings")
def update_settings(s: SettingIn):
    if s.usd_sar_rate <= 0: raise HTTPException(422, "Rate must be > 0")
    set_setting("usd_sar_rate", str(s.usd_sar_rate))
    return {"usd_sar_rate": s.usd_sar_rate}


# ── Exports ───────────────────────────────────────────────────────────────────

def _export(ticker, direction, trade_type, date_from, date_to, outcome):
    trades = get_all_trades(_f(ticker, direction, trade_type, date_from, date_to, outcome))
    sar = float(get_setting("usd_sar_rate") or 3.75)
    return trades, sar


@app.get("/api/export/csv")
def export_csv(ticker: Optional[str]=None, direction: Optional[str]=None,
               trade_type: Optional[str]=None, date_from: Optional[str]=None,
               date_to: Optional[str]=None, outcome: Optional[str]=None):
    trades, sar = _export(ticker, direction, trade_type, date_from, date_to, outcome)
    return Response(to_csv(trades, sar), media_type="text/csv",
                    headers={"Content-Disposition": 'attachment; filename="trades.csv"'})


@app.get("/api/export/excel")
def export_excel(ticker: Optional[str]=None, direction: Optional[str]=None,
                 trade_type: Optional[str]=None, date_from: Optional[str]=None,
                 date_to: Optional[str]=None, outcome: Optional[str]=None):
    trades, sar = _export(ticker, direction, trade_type, date_from, date_to, outcome)
    content = to_excel(trades, sar, compute_metrics(trades))
    return Response(content,
                    media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    headers={"Content-Disposition": 'attachment; filename="trades.xlsx"'})


@app.get("/api/export/pdf")
def export_pdf(ticker: Optional[str]=None, direction: Optional[str]=None,
               trade_type: Optional[str]=None, date_from: Optional[str]=None,
               date_to: Optional[str]=None, outcome: Optional[str]=None):
    trades, sar = _export(ticker, direction, trade_type, date_from, date_to, outcome)
    return Response(to_pdf(trades, sar, compute_metrics(trades)), media_type="application/pdf",
                    headers={"Content-Disposition": 'attachment; filename="report.pdf"'})


# ── Static ────────────────────────────────────────────────────────────────────
# Mount static last so API routes take priority.
app.mount("/org", StaticFiles(directory="static/org", html=True), name="org")
app.mount("/", StaticFiles(directory="static", html=True), name="static")
