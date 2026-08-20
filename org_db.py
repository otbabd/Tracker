"""SQLite storage for imported org datasets."""
import json
import os
import sqlite3
from datetime import datetime
from typing import Optional

from database import DB_PATH as _TRADES_DB

ORG_DB_PATH = os.environ.get("ORG_DB_PATH",
                             os.path.join(os.path.dirname(_TRADES_DB) or ".", "org.db"))

EMP_COLUMNS = [
    "employee_id", "name", "manager_id", "job_title", "job_code", "job_family",
    "job_level", "function", "department", "division", "location",
    "employment_type", "status", "is_vacant", "fte", "cost_center", "email",
    "hire_date", "extra",
]


def get_connection():
    conn = sqlite3.connect(ORG_DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    with get_connection() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS org_datasets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                filename TEXT,
                row_count INTEGER NOT NULL DEFAULT 0,
                mapping TEXT NOT NULL DEFAULT '{}',
                warnings TEXT NOT NULL DEFAULT '[]',
                uploaded_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS org_employees (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                dataset_id INTEGER NOT NULL REFERENCES org_datasets(id) ON DELETE CASCADE,
                employee_id TEXT NOT NULL,
                name TEXT,
                manager_id TEXT,
                job_title TEXT,
                job_code TEXT,
                job_family TEXT,
                job_level TEXT,
                function TEXT,
                department TEXT,
                division TEXT,
                location TEXT,
                employment_type TEXT,
                status TEXT,
                is_vacant INTEGER NOT NULL DEFAULT 0,
                fte REAL NOT NULL DEFAULT 1.0,
                cost_center TEXT,
                email TEXT,
                hire_date TEXT,
                extra TEXT NOT NULL DEFAULT '{}'
            );

            CREATE INDEX IF NOT EXISTS idx_org_emp_dataset ON org_employees(dataset_id);
            CREATE INDEX IF NOT EXISTS idx_org_emp_manager ON org_employees(dataset_id, manager_id);
        """)


def create_dataset(name: str, filename: str, employees: list[dict],
                   mapping: dict, warnings: list[dict]) -> int:
    now = datetime.utcnow().isoformat(timespec="seconds")
    placeholders = ", ".join("?" * len(EMP_COLUMNS))
    with get_connection() as conn:
        cur = conn.execute(
            "INSERT INTO org_datasets (name, filename, row_count, mapping, warnings, uploaded_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (name, filename, len(employees), json.dumps(mapping), json.dumps(warnings), now),
        )
        dataset_id = cur.lastrowid
        conn.executemany(
            f"INSERT INTO org_employees (dataset_id, {', '.join(EMP_COLUMNS)}) "
            f"VALUES (?, {placeholders})",
            [[dataset_id] + [e.get(c) for c in EMP_COLUMNS] for e in employees],
        )
        return dataset_id


def list_datasets() -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT id, name, filename, row_count, uploaded_at FROM org_datasets "
            "ORDER BY id DESC"
        ).fetchall()
        return [dict(r) for r in rows]


def get_dataset(dataset_id: int) -> Optional[dict]:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM org_datasets WHERE id=?", (dataset_id,)).fetchone()
        if not row:
            return None
        d = dict(row)
        d["mapping"] = json.loads(d.get("mapping") or "{}")
        d["warnings"] = json.loads(d.get("warnings") or "[]")
        return d


def latest_dataset_id() -> Optional[int]:
    with get_connection() as conn:
        row = conn.execute("SELECT id FROM org_datasets ORDER BY id DESC LIMIT 1").fetchone()
        return row["id"] if row else None


def rename_dataset(dataset_id: int, name: str):
    with get_connection() as conn:
        conn.execute("UPDATE org_datasets SET name=? WHERE id=?", (name, dataset_id))


def delete_dataset(dataset_id: int):
    with get_connection() as conn:
        conn.execute("DELETE FROM org_employees WHERE dataset_id=?", (dataset_id,))
        conn.execute("DELETE FROM org_datasets WHERE id=?", (dataset_id,))


def get_employees(dataset_id: int) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            f"SELECT {', '.join(EMP_COLUMNS)} FROM org_employees WHERE dataset_id=? ORDER BY id",
            (dataset_id,),
        ).fetchall()
    out = []
    for r in rows:
        e = dict(r)
        try:
            e["extra"] = json.loads(e.get("extra") or "{}")
        except (TypeError, ValueError):
            e["extra"] = {}
        out.append(e)
    return out
