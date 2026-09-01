"""The arithmetic, done again in Python.

Deliberately written from the exercise's own definitions rather than from the
workbook's formulas, so that a wrong formula and a wrong expectation cannot
agree with each other.
"""
from __future__ import annotations

import refdata as R

QI = {q: i + 1 for i, q in enumerate(R.QUARTERS)}


def loaded(grade: str, saudi_basis: str) -> float:
    b, h, t, bonus = R.GRADE_COST[grade]
    gosi = R.GOSI_SAUDI if saudi_basis == "Saudi" else R.GOSI_NON_SAUDI
    return b + h + t + b * bonus + (b + h) * gosi


def one_off(grade: str) -> int:
    order = list(R.GRADE_COST)
    return (R.ONE_OFF_SENIOR if order.index(grade) >= order.index(R.SENIOR_FROM)
            else R.ONE_OFF_JUNIOR)


def in_year(grade: str, saudi_basis: str, fte: float, quarter: str,
            inflation: float = 0.0) -> float:
    """Part-year cost in the plan year: a Q1 start is paid four quarters."""
    full = loaded(grade, saudi_basis) * (1 + inflation)
    return full * fte * (5 - QI[quarter]) / 4 + one_off(grade) * fte


def run_rate(grade: str, saudi_basis: str, fte: float,
             inflation: float = 0.0) -> float:
    return loaded(grade, saudi_basis) * (1 + inflation) * fte


def effective(line: dict) -> tuple[float | None, str | None]:
    """What a challenge decision means in numbers, per the rule on the sheet."""
    decision = line.get("decision")
    if not decision:
        return None, None
    if decision == "Decline":
        fte = 0.0
    elif decision == "Approve fewer":
        fte = line.get("approved_fte")
        if fte is None:
            return None, None
    else:
        fte = line["fte"]
    quarter = line.get("approved_quarter") or line["quarter"]
    return float(fte), quarter


def scenario_fte(line: dict, demand: float, productivity: float) -> float:
    return line["fte"] * demand / (1 + R.DEFAULT_PRODUCTIVITY * (productivity - 1))


def scenario_quarter(line: dict, shift: int) -> int:
    return min(4, QI[line["quarter"]] + shift)


def scenario_cost(line: dict, fte: float, qi: int, inflation: float) -> float:
    full = loaded(line["grade"], line["saudi"]) * (1 + inflation)
    return full * fte * (5 - qi) / 4 + one_off(line["grade"]) * fte


def funded_set(lines: dict, demand: float, share: float, shift: int,
               inflation: float, productivity: float, envelope: float) -> dict:
    """The ranked cut: lines fund in key order until the envelope runs out."""
    rows = []
    for r, line in lines.items():
        fte = scenario_fte(line, demand, productivity)
        qi = scenario_quarter(line, shift)
        cost = scenario_cost(line, fte, qi, inflation)
        rows.append((line["rank"] * 10**6 + r, r, fte, cost,
                     run_rate(line["grade"], line["saudi"], fte, inflation)))
    rows.sort()
    limit = envelope * share
    cum = 0.0
    out = {}
    for key, r, fte, cost, rr in rows:
        cum += cost
        out[r] = dict(key=key, fte=fte, cost=cost, run_rate=rr, cumulative=cum,
                      funded=1 if cum <= limit else 0)
    return out
