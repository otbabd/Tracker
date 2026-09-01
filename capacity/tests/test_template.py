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
import harness
from harness import Run
import model as M
import refdata as R

DIST = Path(__file__).resolve().parents[1] / "dist"
EXAMPLE = DIST / "2027-Capacity-Example-RiskGroup.xlsx"
ASK_FIRST, ASK_LAST = 6, 305
TOL = 0.01


def find_row(ws, label: str, col: int = 1) -> int:
    for r in range(1, ws.max_row + 1):
        if ws.cell(row=r, column=col).value == label:
            return r
    raise AssertionError(f"no row labelled {label!r} on {ws.title}")


def run(path: Path = EXAMPLE) -> Run:
    t = Run("template — worked example")
    wb = load_workbook(path, data_only=True)
    t.check(not harness.error_cells(wb), "no cell holds an Excel error",
            ", ".join(harness.error_cells(wb)[:5]))

    ws = wb["5. Capacity asks"]
    lines = []
    for r in range(ASK_FIRST, ASK_LAST + 1):
        title = ws.cell(row=r, column=3).value
        if not title:
            continue
        line = dict(row=r, unit=ws.cell(row=r, column=2).value, title=title,
                    grade=ws.cell(row=r, column=4).value,
                    workforce=ws.cell(row=r, column=5).value,
                    saudi=ws.cell(row=r, column=6).value,
                    nature=ws.cell(row=r, column=7).value,
                    fte=ws.cell(row=r, column=8).value,
                    quarter=ws.cell(row=r, column=9).value,
                    driver=ws.cell(row=r, column=10).value)
        lines.append(line)
    t.check(len(lines) >= 15, "the example carries a real submission",
            f"{len(lines)} lines")

    # Per line: category, rank and all four cost columns.
    for line in lines:
        r = line["row"]
        want_cat = R.driver_category(line["driver"])
        t.equal(ws.cell(row=r, column=11).value, want_cat, f"row {r} category")
        t.equal(ws.cell(row=r, column=12).value, R.rank_of(want_cat), f"row {r} rank")
        t.close(TOL, ws.cell(row=r, column=15).value,
                M.loaded(line["grade"], line["saudi"]), f"row {r} loaded cost")
        t.close(TOL, ws.cell(row=r, column=16).value,
                M.one_off(line["grade"]), f"row {r} one-off")
        t.close(TOL, ws.cell(row=r, column=17).value,
                M.in_year(line["grade"], line["saudi"], line["fte"], line["quarter"]),
                f"row {r} in-year cost")
        t.close(TOL, ws.cell(row=r, column=18).value,
                M.run_rate(line["grade"], line["saudi"], line["fte"]),
                f"row {r} run-rate")
        t.equal(ws.cell(row=r, column=19).value, None, f"row {r} is complete")

    total_fte = sum(l["fte"] for l in lines)
    total_in = sum(M.in_year(l["grade"], l["saudi"], l["fte"], l["quarter"])
                   for l in lines)
    total_run = sum(M.run_rate(l["grade"], l["saudi"], l["fte"]) for l in lines)

    # Positions released by closures and merges, read off the group's own sheet.
    chg = wb["4. Structure changes"]
    released = 0
    for r in range(1, chg.max_row + 1):
        if chg.cell(row=r, column=2).value in ("Close", "Merge into another unit"):
            released += chg.cell(row=r, column=8).value or 0

    pos = wb["6. My position"]
    t.close(TOL, pos.cell(row=find_row(pos, "Positions asked for (FTE)"), column=2).value,
            total_fte, "total FTE asked")
    t.close(TOL, pos.cell(row=find_row(pos, f"{R.PLAN_YEAR} in-year cost (SAR '000)"),
                          column=2).value, total_in, "total in-year cost")
    t.close(TOL, pos.cell(row=find_row(pos,
                                       f"Full-year run-rate from {R.PLAN_YEAR + 1} (SAR '000)"),
                          column=2).value, total_run, "total run-rate")
    for wt in R.WORKFORCE_TYPES:
        want = sum(l["fte"] for l in lines if l["workforce"] == wt)
        t.close(TOL, pos.cell(row=find_row(pos, f"    of which {wt.lower()}"),
                              column=2).value, want, f"FTE {wt.lower()}")

    # The three envelope tests.
    r = find_row(pos, f"{R.PLAN_YEAR} cost (SAR '000)")
    limit = pos.cell(row=r, column=2).value
    t.close(TOL, pos.cell(row=r, column=3).value, total_in, "envelope test reads the cost")
    t.close(TOL, pos.cell(row=r, column=4).value, limit - total_in, "cost headroom")
    t.equal(pos.cell(row=r, column=5).value,
            "Within envelope" if total_in <= limit else "Over envelope", "cost verdict")

    r = find_row(pos, "Net establishment change")
    t.close(TOL, pos.cell(row=r, column=3).value, total_fte - released,
            "net establishment change")

    r = find_row(pos, "Saudization")
    base_filled = pos.cell(row=find_row(pos, "Filled headcount today"), column=2).value
    base_saudi = pos.cell(row=find_row(pos, "Saudi nationals today"), column=2).value
    saudi_fte = sum(l["fte"] for l in lines if l["saudi"] == "Saudi")
    want = (base_saudi + saudi_fte) / (base_filled + total_fte)
    t.close(1e-9, pos.cell(row=r, column=3).value, want, "projected Saudization")
    t.equal(pos.cell(row=r, column=5).value,
            "At or above target" if want >= pos.cell(row=r, column=2).value
            else "Below target", "Saudization verdict")

    # Priority table, cumulative in ranking order.
    cum = 0.0
    for name, rank, _ in R.RANK_CATEGORIES:
        r = find_row(pos, f"{rank}. {name}")
        want_fte = sum(l["fte"] for l in lines
                       if R.driver_category(l["driver"]) == name)
        want_cost = sum(M.in_year(l["grade"], l["saudi"], l["fte"], l["quarter"])
                        for l in lines if R.driver_category(l["driver"]) == name)
        cum += want_cost
        t.close(TOL, pos.cell(row=r, column=2).value, want_fte, f"{name} FTE")
        t.close(TOL, pos.cell(row=r, column=3).value, want_cost, f"{name} cost")
        t.close(TOL, pos.cell(row=r, column=4).value, cum, f"{name} cumulative cost")

    # Phasing.
    for q in R.QUARTERS:
        r = find_row(pos, q)
        t.close(TOL, pos.cell(row=r, column=2).value,
                sum(l["fte"] for l in lines if l["quarter"] == q), f"{q} FTE")
        t.close(TOL, pos.cell(row=r, column=3).value,
                sum(M.in_year(l["grade"], l["saudi"], l["fte"], l["quarter"])
                    for l in lines if l["quarter"] == q), f"{q} cost")

    # The check sheet has to agree that this is submittable.
    chk = wb["7. Check & submit"]
    for label in ["Ask rows with something missing",
                  "Ask rows naming a unit that does not exist",
                  f"{R.BASE_YEAR} vacancies not yet confirmed",
                  "Named leavers with no backfill answer",
                  "Units with no workload driver",
                  "Units with a driver but missing volumes",
                  "Structure changes started but incomplete"]:
        t.equal(chk.cell(row=find_row(chk, label), column=2).value, 0, f"check: {label}")
    t.equal(chk.cell(row=find_row(chk, "Ready to submit"), column=2).value, "Yes",
            "the example is ready to submit")
    t.equal(chk.cell(row=find_row(chk, "State"), column=2).value, "Submitted",
            "the example is submitted")
    return t


if __name__ == "__main__":
    sys.exit(run().report())
