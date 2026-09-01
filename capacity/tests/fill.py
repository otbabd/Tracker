"""Push a full exercise through the consolidator.

Twelve groups' worth of asks, the four numbers the centre types per group, and a
spread of challenge decisions. Risk Group's band is filled from the worked
example's own ask sheet, cell for cell, which is the copy-paste path the central
team will actually use; the other eleven are generated so every band and all
3,600 register rows carry load.

Everything written here is returned as plain Python, so the tests can recompute
the workbook's answers without asking the workbook.
"""
from __future__ import annotations

import math
import random
from pathlib import Path

from openpyxl import load_workbook

import harness  # noqa: F401  — puts capacity/build on the path
import consolidator as C
import refdata as R

EXAMPLE_GROUP = "Risk Group"

TITLES = [
    "Analyst", "Senior Analyst", "Officer", "Senior Officer", "Specialist",
    "Senior Specialist", "Manager", "Senior Manager", "Engineer", "Consultant",
]
ALTERNATIVES = [
    "Automation considered; the residual work still needs a person.",
    "Vendor cover priced and rejected on cost.",
    "Reviewed against the existing rota; no slack to absorb it.",
    "Considered deferring to 2028; the regulatory date does not move.",
]


def example_rows(example_path: Path) -> list[list]:
    """Exactly what a group would copy: A6:N305 from its Capacity asks sheet."""
    wb = load_workbook(example_path, data_only=True)
    ws = wb["5. Capacity asks"]
    out = []
    for r in range(6, 306):
        row = [ws.cell(row=r, column=c).value for c in range(1, 15)]
        out.append(row)
    return out


def generated_rows(bank: R.Bank, group: str, seed: int) -> list[list]:
    rng = random.Random(seed)
    units = [n["name"] for _, n in bank.descend(bank.group_key(group))
             if n["level"] >= 2] or [group]
    grades = list(R.GRADE_COST)
    drivers = [d for d, _ in R.ASK_DRIVERS]
    rows = []
    for i in range(rng.randint(14, 30)):
        driver = rng.choice(drivers)
        cat = R.driver_category(driver)
        nature = ("Replacement" if cat == "Replacement"
                  else rng.choice(["Growth", "Growth", "Conversion"]))
        rows.append([
            i + 1,
            rng.choice(units),
            f"{rng.choice(TITLES)} {i + 1}",
            rng.choice(grades[:7]),
            rng.choice(R.WORKFORCE_TYPES[:2]),
            rng.choice(["Saudi", "Saudi", "Saudi", "Non-Saudi"]),
            nature,
            rng.choice([1, 1, 1, 2, 2, 3]),
            rng.choice(R.QUARTERS),
            driver,
            None, None,
            rng.choice(ALTERNATIVES),
            None,
        ])
    return rows


def decide(i: int, category: str, fte) -> tuple[str, object, object]:
    """The decision rule the test recomputes from. Deterministic on purpose."""
    if category in ("Regulatory", "Risk"):
        return "Approve as asked", None, None
    if i % 11 == 0:
        return "Decline", None, None
    if i % 7 == 0:
        return "Approve fewer", max(1, math.floor((fte or 1) / 2)), None
    if i % 13 == 0:
        return "Defer to a later quarter", None, "Q4"
    return "Approve as asked", None, None


def fill(path: Path, example_path: Path, bank: R.Bank | None = None) -> dict:
    bank = bank or R.Bank()
    C.build_consolidator(path, bank)
    wb = load_workbook(path)
    sub = wb[C.SH_SUB]
    chal = wb[C.SH_CHAL]
    env = wb[C.SH_ENV]
    envl = C.build_envelopes.__doc__  # noqa: F841 — keeps the import honest

    # The envelope sheet's group rows are in bank.groups order, first row known
    # from the consolidator's own layout constants.
    env_first = None
    for r in range(1, env.max_row + 1):
        if env.cell(row=r, column=1).value == bank.groups[0]:
            env_first = r
            break
    assert env_first, "could not find the group table on the envelopes sheet"

    lines: dict[int, dict] = {}
    per_group: dict[str, dict] = {}
    for i, group in enumerate(bank.groups):
        rows = (example_rows(example_path) if group == EXAMPLE_GROUP
                else generated_rows(bank, group, seed=4200 + i))
        bf = C.band_first(i)
        used = 0
        for j, row in enumerate(rows):
            if not row[2]:                      # no job title: not a line
                continue
            r = bf + j
            for k, value in enumerate(row):     # A..N lands in B..O
                sub.cell(row=r, column=2 + k, value=value)
            grade, saudi_basis = row[3], row[5]
            fte, quarter, driver = row[7], row[8], row[9]
            category = R.driver_category(driver)
            lines[r] = dict(group=group, ref=row[0], unit=row[1], title=row[2],
                            grade=grade, workforce=row[4], saudi=saudi_basis,
                            nature=row[6], fte=fte, quarter=quarter,
                            driver=driver, category=category,
                            rank=R.rank_of(category))
            decision, approved_fte, approved_q = decide(j, category, fte)
            chal.cell(row=r, column=11, value=decision)
            if approved_fte is not None:
                chal.cell(row=r, column=12, value=approved_fte)
            if approved_q is not None:
                chal.cell(row=r, column=13, value=approved_q)
            chal.cell(row=r, column=14, value="Recorded at the challenge meeting")
            lines[r].update(decision=decision, approved_fte=approved_fte,
                            approved_quarter=approved_q)
            used += 1

        er = env_first + i
        lapsed = 2 + i % 4
        released = 1 + i % 3
        for col, value in [(10, 0.09 + (i % 3) / 100), (11, lapsed),
                           (12, released), (13, "Submitted")]:
            env.cell(row=er, column=col, value=value)
        per_group[group] = dict(row=er, band_first=bf, lines=used,
                                lapsed=lapsed, released=released)

    wb.save(path)
    return dict(path=str(path), lines=lines, groups=per_group,
                env_first=env_first, first=C.FIRST_ROW,
                last=C.last_row(len(bank.groups)))


if __name__ == "__main__":
    import sys

    out = Path(sys.argv[1] if len(sys.argv) > 1 else "/tmp/filled-consolidator.xlsx")
    ex = Path(__file__).resolve().parents[1] / "dist" / "2027-Capacity-Example-RiskGroup.xlsx"
    got = fill(out, ex)
    print(f"{got['path']}: {len(got['lines'])} lines across {len(got['groups'])} groups")
