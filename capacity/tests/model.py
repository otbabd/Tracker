"""The arithmetic, done again in Python.

Deliberately written from the exercise's own definitions rather than from the
workbook's formulas, so that a wrong formula and a wrong expectation cannot
agree with each other.
"""
from __future__ import annotations

import refdata as R

QI = {q: i + 1 for i, q in enumerate(R.QUARTERS)}


def rate(level: str) -> float:
    """Full-year loaded cost of one seat, in SAR '000. An unknown or blank
    career level costs nothing — which is what makes it show as a dash rather
    than as a plausible wrong number."""
    if level not in R.LEVEL_COST:
        return 0.0
    b, h, t, bonus, _ = R.LEVEL_COST[level]
    return b + h + t + b * bonus + (b + h) * R.GOSI_SAUDI


def rate_mandated(level: str, mandated: str) -> float:
    """The seat rate the template uses: a mandated seat carries Saudi GOSI, the
    rest the non-Saudi rate."""
    if level not in R.LEVEL_COST:
        return 0.0
    b, h, t, bonus, _ = R.LEVEL_COST[level]
    gosi = R.GOSI_SAUDI if mandated == "Yes" else R.GOSI_NON_SAUDI
    return b + h + t + b * bonus + (b + h) * gosi


def one_off(level: str) -> float:
    return R.LEVEL_COST[level][4] if level in R.LEVEL_COST else 0.0


def weight(quarter: str, shift: int = 0) -> float:
    """A Q1 start is paid four quarters of the year, a Q4 start one."""
    return (5 - min(4, QI[quarter] + shift)) / 4


def ask_total(ask: dict) -> float:
    return sum(float(ask.get(q) or 0) for q in R.QUARTERS)


def in_year(ask: dict, shift: int = 0, inflation: float = 0.0,
            scale: float = 1.0) -> float:
    """Cash cost of one ask line in the plan year, at its own quarter split."""
    r = rate(ask["level"]) * (1 + inflation)
    phased = sum(float(ask.get(q) or 0) * weight(q, shift) for q in R.QUARTERS)
    return r * phased * scale + one_off(ask["level"]) * ask_total(ask) * scale


def run_rate(ask: dict, inflation: float = 0.0, scale: float = 1.0) -> float:
    return rate(ask["level"]) * (1 + inflation) * ask_total(ask) * scale


def effective(line: dict) -> tuple[float | None, str | None]:
    """What a challenge decision means in numbers, per the rule on the sheet."""
    decision = line.get("decision")
    if not decision:
        return None, None
    if decision == "Decline":
        total = 0.0
    elif decision == "Approve fewer":
        total = line.get("approved")
        if total is None:
            return None, None
    else:
        total = ask_total(line)
    quarter = line.get("approved_quarter") or first_quarter(line)
    return float(total), quarter


def first_quarter(ask: dict) -> str | None:
    """The earliest quarter the group asked for — the start the centre
    challenges against."""
    for q in R.QUARTERS:
        if float(ask.get(q) or 0) > 0:
            return q
    return None


def approved_in_year(line: dict, total: float, quarter: str) -> float:
    return rate(line["level"]) * total * weight(quarter) + one_off(line["level"]) * total


def scenario_scale(demand: float, productivity: float) -> float:
    return demand / (1 + R.DEFAULT_PRODUCTIVITY * (productivity - 1))


def funded_set(lines: dict, demand: float, share: float, shift: int,
               inflation: float, productivity: float, envelope: float) -> dict:
    """The ranked cut: lines fund in key order until the envelope runs out.

    The cut is made against run-rate cost, not against cash, so pushing starts
    back buys cash and not headcount.
    """
    scale = scenario_scale(demand, productivity)
    rows = []
    for r, ask in lines.items():
        total = ask_total(ask) * scale
        rows.append((ask["rank"] * 10**6 + r, r, total,
                     run_rate(ask, inflation, scale),
                     in_year(ask, shift, inflation, scale)))
    rows.sort()
    limit = envelope * share
    cum = 0.0
    out = {}
    for key, r, total, rr, cash in rows:
        cum += rr
        out[r] = dict(key=key, total=total, run_rate=rr, cash=cash,
                      cumulative=cum, funded=1 if cum <= limit else 0)
    return out


# ── Outflow ────────────────────────────────────────────────────────────────
def seats_released(seat: dict) -> float:
    """What a capacity row gives up: the typed number, but only when the row
    actually says Reduce."""
    if seat.get("direction") != R.REDUCE_DIRECTION:
        return 0.0
    return float(seat.get("slated") or 0)


def paid_share(out: dict) -> float | None:
    """The share of the plan year a departing seat is still paid for.

    A seat is paid up to and including the quarter its holder leaves — the
    mirror of a new position being paid from the quarter it starts.
    """
    if not out.get("quarter") or not out.get("disposition"):
        return None
    leave = QI[out["quarter"]] / 4
    if out["disposition"] == R.SURRENDER:
        return leave
    if out["disposition"] == R.DEFER:
        if not out.get("backfill"):
            return leave
        return min(1.0, leave + (5 - QI[out["backfill"]]) / 4)
    return 1.0                      # backfilled at once: paid all year


def cash_released(out: dict) -> float:
    share = paid_share(out)
    if share is None:
        return 0.0
    return rate(out["level"]) * (1 - share)


def run_rate_released(out: dict) -> float:
    return rate(out["level"]) if out.get("disposition") == R.SURRENDER else 0.0
