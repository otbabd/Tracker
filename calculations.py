from datetime import date, datetime
from typing import Union


def classify_trade(entry_date: Union[str, date], exit_date: Union[str, date]) -> tuple[str, int]:
    if isinstance(entry_date, str):
        entry_date = datetime.strptime(entry_date[:10], "%Y-%m-%d").date()
    if isinstance(exit_date, str):
        exit_date = datetime.strptime(exit_date[:10], "%Y-%m-%d").date()
    days = (exit_date - entry_date).days
    if days == 0:
        trade_type = "Day Trade"
    elif days <= 5:
        trade_type = "Swing Trade"
    elif days <= 30:
        trade_type = "Position Trade"
    else:
        trade_type = "Long Hold"
    return trade_type, days


def calc_pnl(direction: str, entry_price: float, exit_price: float, shares: float, fees: float) -> float:
    if direction == "Long":
        return ((exit_price - entry_price) * shares) - fees
    else:
        return ((entry_price - exit_price) * shares) - fees


def calc_return_pct(direction: str, entry_price: float, exit_price: float) -> float:
    if direction == "Long":
        return ((exit_price - entry_price) / entry_price) * 100
    else:
        return ((entry_price - exit_price) / entry_price) * 100


def build_trade_record(raw: dict) -> dict:
    trade_type, holding_period = classify_trade(raw["entry_date"], raw["exit_date"])
    pnl = calc_pnl(raw["direction"], raw["entry_price"], raw["exit_price"], raw["shares"], raw["fees"])
    return_pct = calc_return_pct(raw["direction"], raw["entry_price"], raw["exit_price"])
    return {
        "ticker": raw["ticker"].upper().strip(),
        "direction": raw["direction"],
        "entry_date": raw["entry_date"][:10],
        "exit_date": raw["exit_date"][:10],
        "entry_price": raw["entry_price"],
        "exit_price": raw["exit_price"],
        "shares": raw["shares"],
        "fees": raw["fees"],
        "notes": raw.get("notes", ""),
        "trade_type": trade_type,
        "holding_period": holding_period,
        "return_pct": round(return_pct, 4),
        "pnl": round(pnl, 4),
    }


def compute_metrics(trades: list[dict]) -> dict:
    if not trades:
        return {
            "total_trades": 0,
            "total_pnl": 0.0,
            "win_rate": 0.0,
            "profit_factor": 0.0,
            "avg_winner": 0.0,
            "avg_loser": 0.0,
            "expectancy": 0.0,
            "gross_profit": 0.0,
            "gross_loss": 0.0,
            "winning_trades": 0,
            "losing_trades": 0,
            "largest_winner": 0.0,
            "largest_loser": 0.0,
        }

    pnls = [t["pnl"] for t in trades]
    winners = [p for p in pnls if p > 0]
    losers = [p for p in pnls if p < 0]

    total_trades = len(trades)
    total_pnl = sum(pnls)
    gross_profit = sum(winners) if winners else 0.0
    gross_loss = abs(sum(losers)) if losers else 0.0
    win_rate = len(winners) / total_trades if total_trades else 0.0
    loss_rate = 1 - win_rate
    avg_winner = sum(winners) / len(winners) if winners else 0.0
    avg_loser = abs(sum(losers) / len(losers)) if losers else 0.0
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else float("inf")
    expectancy = (win_rate * avg_winner) - (loss_rate * avg_loser)

    return {
        "total_trades": total_trades,
        "total_pnl": round(total_pnl, 2),
        "win_rate": round(win_rate * 100, 2),
        "profit_factor": round(profit_factor, 2) if profit_factor != float("inf") else None,
        "avg_winner": round(avg_winner, 2),
        "avg_loser": round(avg_loser, 2),
        "expectancy": round(expectancy, 2),
        "gross_profit": round(gross_profit, 2),
        "gross_loss": round(gross_loss, 2),
        "winning_trades": len(winners),
        "losing_trades": len(losers),
        "largest_winner": round(max(winners), 2) if winners else 0.0,
        "largest_loser": round(min(losers), 2) if losers else 0.0,
    }


def compute_streaks(trades: list[dict]) -> tuple[int, int]:
    """Return (max_win_streak, max_loss_streak) ordered by exit_date asc."""
    sorted_trades = sorted(trades, key=lambda t: t["exit_date"])
    max_win = max_loss = cur_win = cur_loss = 0
    for t in sorted_trades:
        if t["pnl"] > 0:
            cur_win += 1
            cur_loss = 0
        elif t["pnl"] < 0:
            cur_loss += 1
            cur_win = 0
        else:
            cur_win = cur_loss = 0
        max_win = max(max_win, cur_win)
        max_loss = max(max_loss, cur_loss)
    return max_win, max_loss
