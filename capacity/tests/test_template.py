"""The group template, checked against arithmetic done independently.

Runs against the worked example, because a blank template has nothing to get
wrong. Every figure the workbook computes is recomputed here from the exercise's
definitions and compared.
"""
from __future__ import annotations

import sys
from pathlib import Path

from openpyxl import load_workbook

sys.path.insert(0, str(Path(__file__).resolve().parent))
import harness  # noqa: E402  — imported first; it puts capacity/build on the path
from harness import Run
import example as E
import model as M
import refdata as R
import template as T

SCRATCH = Path("/tmp/claude-0/-home-user-Tracker/"
               "3cac8f7f-9e45-5037-aeaf-db814b62d91c/scratchpad")
TOL = 0.01


def find_row(ws, label: str, col: int = 1) -> int:
    for r in range(1, ws.max_row + 1):
        if ws.cell(row=r, column=col).value == label:
            return r
    raise AssertionError(f"no row labelled {label!r} on {ws.title}")


def prepare(path: Path) -> dict:
    layout = E.build_example(path)
    result = harness.recalc(path, 600)
    if result.get("status") != "success":
        raise AssertionError(f"recalc: {result}")
    layout["recalc"] = result
    return layout


def run(prepared: dict) -> Run:
    t = Run("template — worked example")
    path = prepared["path"]
    A, C = prepared["ask_cols"], prepared["cap_cols"]
    wb = load_workbook(path, data_only=True)
    bad = harness.error_cells(wb)
    t.check(not bad, "no cell holds an Excel error", ", ".join(bad[:5]))
    t.equal(prepared["recalc"]["total_errors"], 0, "recalculates with zero errors")

    # ── What the group typed on the capacity sheet ─────────────────────────
    ws = wb[T.SH_CAP]
    seats = []
    for r in range(prepared["cap"]["first"], prepared["cap"]["last"] + 1):
        title = ws[f"{C['Job Title']}{r}"].value
        if not title:
            continue
        seat = dict(
            row=r, title=title,
            division=ws[f"{C['Division']}{r}"].value or "",
            level=ws[f"{C['Career Level']}{r}"].value,
            mandate=ws[f"{C['Nationality Mandate?']}{r}"].value,
            direction=ws[f"{C['Capacity Direction']}{r}"].value,
            approved=ws[f"{C['Approved HC']}{r}"].value or 0)
        seats.append(seat)
        want_exit = seat["approved"] if seat["direction"] == R.EXIT_DIRECTION else 0
        t.close(TOL, ws[f"{C['Exits']}{r}"].value, want_exit, f"seat {r} exits")
        t.equal(ws[f"{C[T.MISSING_COL]}{r}"].value, None, f"seat {r} is complete")
    t.check(len(seats) > 100, "the example carries a real establishment",
            f"{len(seats)} seats")
    t.check(any(s["direction"] == R.EXIT_DIRECTION for s in seats),
            "the example gives some seats up")

    # ── What it asked for ──────────────────────────────────────────────────
    ws = wb[T.SH_ASK]
    asks = []
    for r in range(prepared["ask"]["first"], prepared["ask"]["last"] + 1):
        title = ws[f"{A['Job title']}{r}"].value
        if not title:
            continue
        ask = dict(row=r, title=title,
                   division=ws[f"{A['Division']}{r}"].value or "",
                   unit=ws[f"{A['Unit']}{r}"].value,
                   level=ws[f"{A['Career Level']}{r}"].value,
                   driver=ws[f"{A['Driver']}{r}"].value,
                   **{q: ws[f"{A[q]}{r}"].value or 0 for q in R.QUARTERS})
        asks.append(ask)
        t.close(TOL, ws[f"{A['New Asks']}{r}"].value, M.ask_total(ask),
                f"ask {r} total is the quarter split")
        t.equal(ws[f"{A['Category']}{r}"].value, R.driver_category(ask["driver"]),
                f"ask {r} category")
        t.equal(ws[f"{A[T.MISSING_COL]}{r}"].value, None, f"ask {r} is complete")
    t.check(len(asks) >= 10, "the example carries a real submission",
            f"{len(asks)} asks")

    # ── Headcount and cost by division ─────────────────────────────────────
    pos = wb[T.SH_POS]
    for i, (label, div) in enumerate(prepared["pos"]["divisions"]):
        hc = prepared["pos"]["hc_first"] + i
        cost = prepared["pos"]["cost_first"] + i
        mine = [s for s in seats if s["division"] == div]
        asked = [a for a in asks if a["division"] == div]
        want_current = sum(s["approved"] for s in mine)
        want_exits = sum(s["approved"] for s in mine
                         if s["direction"] == R.EXIT_DIRECTION)
        want_asks = sum(M.ask_total(a) for a in asked)
        t.close(TOL, pos.cell(row=hc, column=2).value, want_current,
                f"{label}: current headcount")
        t.close(TOL, pos.cell(row=hc, column=3).value, want_exits,
                f"{label}: exits")
        t.close(TOL, pos.cell(row=hc, column=4).value, want_asks,
                f"{label}: new asks")
        t.close(TOL, pos.cell(row=hc, column=5).value,
                want_current - want_exits + want_asks, f"{label}: new capacity")

        t.close(0.05, pos.cell(row=cost, column=2).value,
                sum(M.rate_mandated(s["level"], s["mandate"]) * s["approved"]
                    for s in mine), f"{label}: current run-rate cost")
        t.close(0.05, pos.cell(row=cost, column=3).value,
                sum(M.rate_mandated(s["level"], s["mandate"]) * s["approved"]
                    for s in mine if s["direction"] == R.EXIT_DIRECTION),
                f"{label}: exit run-rate cost")
        t.close(0.05, pos.cell(row=cost, column=4).value,
                sum(M.rate(a["level"]) * M.ask_total(a) for a in asked),
                f"{label}: new-ask run-rate cost")

    # ── The cash cost, kept apart from the run-rate ────────────────────────
    t.close(0.05, pos.cell(row=prepared["pos"]["cash_row"], column=2).value,
            sum(M.rate(a["level"])
                * sum(a[q] * M.weight(q) for q in R.QUARTERS) for a in asks),
            "in-year cash cost of the asks")
    t.close(0.05, pos.cell(row=prepared["pos"]["one_off_row"], column=2).value,
            sum(M.one_off(a["level"]) * M.ask_total(a) for a in asks),
            "one-off cost of the hires")

    # ── The three ceilings ─────────────────────────────────────────────────
    total_asks = sum(M.ask_total(a) for a in asks)
    total_exits = sum(s["approved"] for s in seats
                      if s["direction"] == R.EXIT_DIRECTION)
    r = prepared["pos"]["head_test"]
    t.close(TOL, pos.cell(row=r, column=3).value, total_asks - total_exits,
            "net establishment change")
    t.equal(pos.cell(row=r, column=5).value,
            "Within envelope" if total_asks - total_exits
            <= pos.cell(row=r, column=2).value else "Over envelope",
            "headcount verdict")

    r = prepared["pos"]["mandate_test"]
    want = (sum(s["approved"] for s in seats if s["mandate"] == "Yes")
            / sum(s["approved"] for s in seats))
    t.close(1e-9, pos.cell(row=r, column=3).value, want, "mandated-seat share")
    t.equal(pos.cell(row=r, column=5).value,
            "At or above target" if want >= pos.cell(row=r, column=2).value
            else "Below target", "mandated-seat verdict")

    # ── Priority and phasing ───────────────────────────────────────────────
    cum = 0.0
    for i, (name, rank, _) in enumerate(R.RANK_CATEGORIES):
        r = prepared["pos"]["cat_first"] + i
        mine = [a for a in asks if R.driver_category(a["driver"]) == name]
        want_cost = sum(M.rate(a["level"]) * M.ask_total(a) for a in mine)
        cum += want_cost
        t.close(TOL, pos.cell(row=r, column=2).value,
                sum(M.ask_total(a) for a in mine), f"{name}: positions")
        t.close(0.05, pos.cell(row=r, column=3).value, want_cost,
                f"{name}: run-rate cost")
        t.close(0.05, pos.cell(row=r, column=4).value, cum, f"{name}: cumulative")

    for i, q in enumerate(R.QUARTERS):
        r = prepared["pos"]["q_first"] + i
        t.close(TOL, pos.cell(row=r, column=2).value,
                sum(a[q] for a in asks), f"{q}: positions starting")
        t.close(0.05, pos.cell(row=r, column=4).value,
                sum(M.rate(a["level"]) * a[q] * M.weight(q) for a in asks),
                f"{q}: cash cost")

    # ── The block the centre pastes ────────────────────────────────────────
    for i, (label, _) in enumerate(prepared["pos"]["divisions"]):
        r = prepared["ret"]["first"] + i
        hc = prepared["pos"]["hc_first"] + i
        for col in (2, 3, 4, 5):
            t.close(TOL, pos.cell(row=r, column=col).value,
                    pos.cell(row=hc, column=col).value,
                    f"return block {label}: column {col} matches the headcount table")

    # ── The gate ───────────────────────────────────────────────────────────
    chk = wb[T.SH_CHK]
    for r in range(prepared["chk"]["block_first"], prepared["chk"]["block_last"] + 1):
        t.equal(chk.cell(row=r, column=2).value, 0,
                f"check: {chk.cell(row=r, column=1).value}")
    t.equal(chk.cell(row=prepared["chk"]["ready_row"], column=2).value, "Yes",
            "the example is ready to submit")
    t.equal(chk.cell(row=prepared["chk"]["state_row"], column=2).value, "Submitted",
            "the example is submitted")
    return t


if __name__ == "__main__":
    SCRATCH.mkdir(parents=True, exist_ok=True)
    sys.exit(run(prepare(SCRATCH / "example-check.xlsx")).report())
