"""The consolidator, with a full exercise pushed through it.

Twelve groups' asks — Risk Group's pasted from the worked example exactly as the
central team would paste it — challenged, scored and read back. Every number the
workbook produces is recomputed in Python from the same inputs.
"""
from __future__ import annotations

import sys
from pathlib import Path

from openpyxl import load_workbook

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fill as F
import harness
from harness import Run
import model as M
import refdata as R
import consolidator as C

SCRATCH = Path("/tmp/claude-0/-home-user-Tracker/"
               "3cac8f7f-9e45-5037-aeaf-db814b62d91c/scratchpad")
DIST = Path(__file__).resolve().parents[1] / "dist"
TOL = 0.01


def find_row(ws, label: str, col: int = 1) -> int:
    for r in range(1, ws.max_row + 1):
        if ws.cell(row=r, column=col).value == label:
            return r
    raise AssertionError(f"no row labelled {label!r} on {ws.title}")


def prepare(path: Path) -> dict:
    got = F.fill(path, DIST / "2027-Capacity-Example-RiskGroup.xlsx")
    result = harness.recalc(path, 900)
    if result.get("status") != "success":
        raise AssertionError(f"recalc: {result}")
    got["recalc"] = result
    return got


def run(prepared: dict) -> Run:
    t = Run("consolidator — full exercise")
    lines = prepared["lines"]
    wb = load_workbook(prepared["path"], data_only=True)
    bad = harness.error_cells(wb)
    t.check(not bad, "no cell holds an Excel error", ", ".join(bad[:5]))
    t.equal(prepared["recalc"]["total_errors"], 0, "recalculates with zero errors")

    # ── Central pricing, line by line ──────────────────────────────────────
    sub = wb[C.SH_SUB]
    keys = {}
    for r, line in lines.items():
        want_cat = R.driver_category(line["driver"])
        t.equal(sub.cell(row=r, column=16).value, want_cat, f"sub {r} category")
        t.equal(sub.cell(row=r, column=17).value, R.rank_of(want_cat), f"sub {r} rank")
        t.close(TOL, sub.cell(row=r, column=18).value,
                M.loaded(line["grade"], line["saudi"]), f"sub {r} loaded cost")
        t.close(TOL, sub.cell(row=r, column=19).value,
                M.one_off(line["grade"]), f"sub {r} one-off")
        t.close(TOL, sub.cell(row=r, column=20).value,
                M.in_year(line["grade"], line["saudi"], line["fte"], line["quarter"]),
                f"sub {r} in-year cost")
        t.close(TOL, sub.cell(row=r, column=21).value,
                M.run_rate(line["grade"], line["saudi"], line["fte"]),
                f"sub {r} run-rate")
        t.equal(sub.cell(row=r, column=23).value, None, f"sub {r} has no problem")
        keys[r] = sub.cell(row=r, column=22).value
    t.equal(len(set(keys.values())), len(keys), "every sort key is unique")
    t.check(all(k == lines[r]["rank"] * 10**6 + r for r, k in keys.items()),
            "sort keys follow rank then row")

    # ── The challenge rule ─────────────────────────────────────────────────
    chal = wb[C.SH_CHAL]
    approved = {}
    for r, line in lines.items():
        want_fte, want_q = M.effective(line)
        got_fte = chal.cell(row=r, column=15).value
        t.close(TOL, got_fte, want_fte, f"challenge {r} effective FTE")
        t.equal(chal.cell(row=r, column=16).value, want_q, f"challenge {r} quarter")
        t.close(TOL, chal.cell(row=r, column=17).value,
                M.in_year(line["grade"], line["saudi"], want_fte, want_q),
                f"challenge {r} approved cost")
        t.close(TOL, chal.cell(row=r, column=18).value,
                M.run_rate(line["grade"], line["saudi"], want_fte),
                f"challenge {r} approved run-rate")
        approved[r] = (want_fte, want_q)

    # ── Receipts and totals by group ───────────────────────────────────────
    env = wb[C.SH_ENV]
    for group, info in prepared["groups"].items():
        er = info["row"]
        mine = {r: l for r, l in lines.items() if l["group"] == group}
        t.equal(env.cell(row=er, column=15).value, len(mine), f"{group}: rows received")
        t.equal(env.cell(row=er, column=16).value, 0, f"{group}: rows with a problem")
        t.close(TOL, env.cell(row=er, column=17).value,
                sum(l["fte"] for l in mine.values()), f"{group}: requested FTE")
        t.close(TOL, env.cell(row=er, column=18).value,
                sum(M.in_year(l["grade"], l["saudi"], l["fte"], l["quarter"])
                    for l in mine.values()), f"{group}: requested cost")
        t.close(TOL, env.cell(row=er, column=19).value,
                sum(approved[r][0] for r in mine), f"{group}: approved FTE")
        t.close(TOL, env.cell(row=er, column=20).value,
                sum(M.in_year(l["grade"], l["saudi"], approved[r][0], approved[r][1])
                    for r, l in mine.items()), f"{group}: approved cost")

    # ── The bridge balances ────────────────────────────────────────────────
    dash = wb[C.SH_DASH]
    opening = dash.cell(row=find_row(dash,
                                     f"Opening {R.BASE_YEAR} approved establishment"),
                        column=2).value
    lapsed = -dash.cell(row=find_row(dash, f"less {R.BASE_YEAR} vacancies lapsed"),
                        column=2).value
    released = -dash.cell(row=find_row(
        dash, "less positions released by closures and merges"), column=2).value
    growth = dash.cell(row=find_row(dash, "plus approved growth positions"),
                       column=2).value
    closing = dash.cell(row=find_row(
        dash, f"Closing {R.PLAN_YEAR} approved establishment"), column=2).value
    t.equal(lapsed, sum(i["lapsed"] for i in prepared["groups"].values()),
            "vacancies lapsed roll up")
    t.equal(released, sum(i["released"] for i in prepared["groups"].values()),
            "closures roll up")
    t.close(TOL, growth,
            sum(approved[r][0] for r, l in lines.items() if l["nature"] == "Growth"),
            "approved growth positions")
    t.close(TOL, closing, opening - lapsed - released + growth, "the bridge balances")
    for nature, label in [("Replacement", "of which replacements approved (no net change)"),
                          ("Conversion", "of which conversions approved (no net change)")]:
        t.close(TOL, dash.cell(row=find_row(dash, label), column=2).value,
                sum(approved[r][0] for r, l in lines.items() if l["nature"] == nature),
                f"{nature.lower()}s approved")

    # ── Four scenarios, recomputed from the levers on the sheet ────────────
    scen = wb[C.SH_SCEN]
    envelope = env.cell(row=find_row(
        env, f"{R.PLAN_YEAR} cost envelope (SAR '000)"), column=2).value
    lever = {name: find_row(scen, name) for name, _, _ in C.LEVERS}
    for k, name in enumerate([s[0] for s in R.SCENARIOS]):
        col = 2 + k
        demand = scen.cell(row=lever["Demand multiplier"], column=col).value
        share = scen.cell(row=lever["Share of envelope released"], column=col).value
        shift = scen.cell(row=lever["Timing shift (quarters)"], column=col).value
        infl = scen.cell(row=lever["Salary inflation"], column=col).value
        prod = scen.cell(row=lever["Productivity multiplier"], column=col).value
        want = M.funded_set(lines, demand, share, shift, infl, prod, envelope)

        eng = wb[C.SH_ENG]
        mismatch = [r for r, w in want.items()
                    if eng.cell(row=r, column=9 + k * C.ENG_BLOCK).value != w["funded"]]
        t.check(not mismatch, f"{name}: every line's funding decision matches",
                f"{len(mismatch)} lines differ, first at row {mismatch[0] if mismatch else ''}")

        funded = [w for w in want.values() if w["funded"]]
        t.equal(scen.cell(row=find_row(scen, "Lines funded"), column=col).value,
                len(funded), f"{name}: lines funded")
        t.close(TOL, scen.cell(row=find_row(scen, "FTE funded"), column=col).value,
                sum(w["fte"] for w in funded), f"{name}: FTE funded")
        t.close(0.05, scen.cell(row=find_row(
            scen, f"{R.PLAN_YEAR} cost funded (SAR '000)"), column=col).value,
            sum(w["cost"] for w in funded), f"{name}: cost funded")
        t.close(0.05, scen.cell(row=find_row(
            scen, f"Run-rate into {R.PLAN_YEAR + 1} (SAR '000)"), column=col).value,
            sum(w["run_rate"] for w in funded), f"{name}: run-rate funded")
        t.close(TOL, scen.cell(row=find_row(scen, "Regulatory FTE funded"),
                               column=col).value,
                sum(w["fte"] for r, w in want.items()
                    if w["funded"] and lines[r]["category"] == "Regulatory"),
                f"{name}: regulatory FTE funded")

        # The cut has to fall in ranking order: nothing discretionary survives
        # while something regulatory is dropped.
        worst_funded = max((lines[r]["rank"] for r, w in want.items() if w["funded"]),
                           default=0)
        best_dropped = min((lines[r]["rank"] for r, w in want.items() if not w["funded"]),
                           default=99)
        t.check(worst_funded <= best_dropped,
                f"{name}: the cut respects the ranking order",
                f"funded down to rank {worst_funded}, dropped from rank {best_dropped}")

    # ── The approved establishment list ────────────────────────────────────
    est = wb[C.SH_EST]
    listed = [r for r in range(C.FIRST_ROW, C.FIRST_ROW + C.EST_ROWS)
              if est.cell(row=r, column=5).value]
    want_lines = [r for r in lines if approved[r][0] and approved[r][0] > 0]
    t.equal(len(listed), len(want_lines), "every approved line is listed")
    t.close(0.05, sum(est.cell(row=r, column=9).value or 0 for r in listed),
            sum(approved[r][0] for r in want_lines), "listed FTE matches approved FTE")
    t.close(0.5, sum(est.cell(row=r, column=11).value or 0 for r in listed),
            sum(M.in_year(lines[r]["grade"], lines[r]["saudi"], approved[r][0],
                          approved[r][1]) for r in want_lines),
            "listed cost matches approved cost")
    return t


if __name__ == "__main__":
    SCRATCH.mkdir(parents=True, exist_ok=True)
    sys.exit(run(prepare(SCRATCH / "filled.xlsx")).report())
