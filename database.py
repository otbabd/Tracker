import sqlite3
import os
from datetime import datetime
from typing import Optional

DB_PATH = os.path.join(os.path.dirname(__file__), "trades.db")


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    with get_connection() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker TEXT NOT NULL,
                direction TEXT NOT NULL CHECK(direction IN ('Long', 'Short')),
                entry_date TEXT NOT NULL,
                exit_date TEXT NOT NULL,
                entry_price REAL NOT NULL,
                exit_price REAL NOT NULL,
                shares REAL NOT NULL,
                fees REAL NOT NULL DEFAULT 0,
                notes TEXT,
                trade_type TEXT NOT NULL,
                holding_period INTEGER NOT NULL,
                return_pct REAL NOT NULL,
                pnl REAL NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            INSERT OR IGNORE INTO settings (key, value, updated_at) VALUES
                ('usd_sar_rate', '3.75', datetime('now'));
            INSERT OR IGNORE INTO settings (key, value, updated_at) VALUES
                ('base_currency', 'USD', datetime('now'));
            INSERT OR IGNORE INTO settings (key, value, updated_at) VALUES
                ('ref_currency', 'SAR', datetime('now'));
        """)


def get_setting(key: str) -> Optional[str]:
    with get_connection() as conn:
        row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
        return row["value"] if row else None


def set_setting(key: str, value: str):
    now = datetime.utcnow().isoformat()
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO settings (key, value, updated_at) VALUES (?, ?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at",
            (key, value, now),
        )


def insert_trade(trade: dict) -> int:
    now = datetime.utcnow().isoformat()
    trade = {**trade, "created_at": now, "updated_at": now}
    cols = ", ".join(trade.keys())
    placeholders = ", ".join("?" * len(trade))
    with get_connection() as conn:
        cur = conn.execute(
            f"INSERT INTO trades ({cols}) VALUES ({placeholders})",
            list(trade.values()),
        )
        return cur.lastrowid


def update_trade(trade_id: int, trade: dict):
    now = datetime.utcnow().isoformat()
    trade["updated_at"] = now
    set_clause = ", ".join(f"{k}=?" for k in trade)
    with get_connection() as conn:
        conn.execute(
            f"UPDATE trades SET {set_clause} WHERE id=?",
            list(trade.values()) + [trade_id],
        )


def delete_trade(trade_id: int):
    with get_connection() as conn:
        conn.execute("DELETE FROM trades WHERE id=?", (trade_id,))


def get_trade(trade_id: int) -> Optional[dict]:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM trades WHERE id=?", (trade_id,)).fetchone()
        return dict(row) if row else None


def get_all_trades(filters: dict = None) -> list[dict]:
    query = "SELECT * FROM trades WHERE 1=1"
    params = []

    if filters:
        if filters.get("ticker"):
            query += " AND UPPER(ticker) LIKE ?"
            params.append(f"%{filters['ticker'].upper()}%")
        if filters.get("direction"):
            query += " AND direction = ?"
            params.append(filters["direction"])
        if filters.get("trade_type"):
            query += " AND trade_type = ?"
            params.append(filters["trade_type"])
        if filters.get("date_from"):
            query += " AND exit_date >= ?"
            params.append(filters["date_from"])
        if filters.get("date_to"):
            query += " AND exit_date <= ?"
            params.append(filters["date_to"])
        if filters.get("outcome") == "Win":
            query += " AND pnl > 0"
        elif filters.get("outcome") == "Loss":
            query += " AND pnl < 0"

    query += " ORDER BY exit_date DESC, id DESC"

    with get_connection() as conn:
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]
