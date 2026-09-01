"""Reference data for the 2027 capacity exercise.

Everything the three workbooks share: the bank's structure and 2026 baseline read
from the org tool's own sample export, the grade cost table, the driver
catalogues, and the exercise settings. Read once here so the template, the worked
example and the consolidator cannot drift from each other.
"""
from __future__ import annotations

import csv
import datetime as dt
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
POSITIONS_CSV = REPO / "sample-org.csv"
UNITS_CSV = REPO / "sample-units.csv"

PLAN_YEAR = 2027
BASE_YEAR = PLAN_YEAR - 1
QUARTERS = ["Q1", "Q2", "Q3", "Q4"]
# Part-year weight: a Q1 start is paid for four quarters, a Q4 start for one.
QUARTER_WEIGHT = {"Q1": 1.00, "Q2": 0.75, "Q3": 0.50, "Q4": 0.25}

LADDER = ["Group", "Division", "Department", "Unit", "Sub-unit", "Section"]
WORKFORCE_TYPES = ["Permanent", "Insourced", "Outsourced"]
SAUDI_BASIS = ["Saudi", "Non-Saudi", "Undecided"]
ASK_NATURE = ["Growth", "Replacement", "Conversion"]
SUBMISSION_STATES = ["Draft", "Submitted", "Challenged", "Approved"]

# ── Ranking ────────────────────────────────────────────────────────────────
# What a constrained scenario cuts first, and the order signed off with the
# user: regulatory is untouchable, "other" goes first.
RANK_CATEGORIES = [
    ("Regulatory", 1, "Mandated by SAMA or another regulator; not discretionary."),
    ("Risk", 2, "Risk and control capacity, including audit finding remediation."),
    ("Revenue", 3, "Directly linked to income — volume growth, new product, coverage."),
    ("Replacement", 4, "Backfilling capacity the bank already had and has lost."),
    ("Efficiency", 5, "Pays for itself through automation, centralisation or insourcing."),
    ("Other", 6, "Everything else. First to be cut when the envelope binds."),
]

# ── Why a position is being asked for ──────────────────────────────────────
ASK_DRIVERS = [
    ("SAMA regulatory requirement", "Regulatory"),
    ("New regulation implementation", "Regulatory"),
    ("Regulatory audit finding", "Regulatory"),
    ("Risk framework uplift", "Risk"),
    ("Control gap closure", "Risk"),
    ("Internal audit finding", "Risk"),
    ("Business continuity / resilience", "Risk"),
    ("Volume growth - existing product", "Revenue"),
    ("New product launch", "Revenue"),
    ("Branch or channel expansion", "Revenue"),
    ("Client coverage expansion", "Revenue"),
    ("Backfill - resignation", "Replacement"),
    ("Backfill - retirement", "Replacement"),
    ("Backfill - internal move", "Replacement"),
    ("Automation enablement", "Efficiency"),
    ("Process centralisation", "Efficiency"),
    ("Insourcing from vendor", "Efficiency"),
    ("Service level improvement", "Other"),
    ("Other - see note", "Other"),
]

# ── What drives the workload in a unit ─────────────────────────────────────
# A central catalogue so demand can be compared across groups, plus two slots
# per group for the genuinely unique.
WORKLOAD_DRIVERS = [
    ("Accounts serviced", "accounts"),
    ("Transactions processed", "transactions / yr"),
    ("Applications processed", "applications / yr"),
    ("Payments processed", "payments / yr"),
    ("Cases or tickets handled", "cases / yr"),
    ("Calls handled", "calls / yr"),
    ("Customers covered", "customers"),
    ("Branches supported", "branches"),
    ("Audits or reviews delivered", "reviews / yr"),
    ("Reports or returns produced", "returns / yr"),
    ("Systems or applications supported", "systems"),
    ("Change requests delivered", "changes / yr"),
    ("Headcount supported", "employees"),
    ("Group-specific driver 1", "(state the unit)"),
    ("Group-specific driver 2", "(state the unit)"),
]

STRUCTURE_ACTIONS = [
    "New unit",
    "Move to a new parent",
    "Rename",
    "Merge into another unit",
    "Close",
]

# ── Grade cost table ───────────────────────────────────────────────────────
# SAR '000 per annum. Illustrative and clearly marked as such: the rates are the
# first thing Finance should replace, and every component is separate so a rate
# can be challenged without rebuilding the model.
#   grade: (basic, housing, transport, target bonus %)
GRADE_COST = {
    "G9":  (96,  24,  12, 0.05),
    "G10": (120, 30,  12, 0.06),
    "G11": (150, 38,  14, 0.08),
    "G12": (192, 48,  14, 0.10),
    "G13": (252, 63,  18, 0.12),
    "G14": (336, 84,  18, 0.15),
    "G15": (450, 113, 24, 0.20),
    "G16": (630, 158, 30, 0.25),
    "G17": (900, 225, 36, 0.30),
}
# Employer GOSI on basic + housing. Saudi nationals attract pension and
# unemployment contributions; non-Saudis attract occupational hazard only.
GOSI_SAUDI = 0.1175
GOSI_NON_SAUDI = 0.02
# One-off cost of a hire, by grade band, recognised in the year of joining only.
ONE_OFF_JUNIOR, ONE_OFF_SENIOR = 12, 45
SENIOR_FROM = "G14"

DEFAULT_ATTRITION = 0.09
DEFAULT_PRODUCTIVITY = 0.03
DEFAULT_SALARY_INFLATION = 0.04

# ── Scenarios ──────────────────────────────────────────────────────────────
#   name, demand multiplier, approval rate, timing shift (quarters),
#   attrition, salary inflation, productivity multiplier
SCENARIOS = [
    ("Base", 1.00, 1.00, 0, DEFAULT_ATTRITION, DEFAULT_SALARY_INFLATION, 1.0),
    ("Constrained", 0.90, 0.70, 1, DEFAULT_ATTRITION + 0.02, DEFAULT_SALARY_INFLATION, 1.5),
    ("Growth", 1.15, 1.00, 0, DEFAULT_ATTRITION, DEFAULT_SALARY_INFLATION + 0.01, 0.5),
    ("Custom", 1.00, 0.85, 0, DEFAULT_ATTRITION, DEFAULT_SALARY_INFLATION, 1.0),
]


def _rows(path: Path) -> list[dict]:
    with open(path, encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


class Bank:
    """The 2026 baseline, read from the org tool's own export."""

    def __init__(self, positions_csv: Path = POSITIONS_CSV, units_csv: Path = UNITS_CSV):
        self.positions = _rows(positions_csv)
        self.unit_list = _rows(units_csv)
        self._index()

    def _index(self) -> None:
        self.groups: list[str] = []
        seen = set()
        for p in self.positions:
            g = p["Group"]
            if g and g not in seen:
                seen.add(g)
                self.groups.append(g)
        self.groups.sort()

        # Every distinct point on the ladder, with its parent, in ladder order.
        self.nodes: dict[str, dict] = {}
        self.children: dict[str, list[str]] = defaultdict(list)
        for p in self.positions:
            parent_key = None
            for level, col in enumerate(LADDER):
                name = p.get(col, "").strip()
                if not name:
                    break
                key = f"{level}|{name}"
                if key not in self.nodes:
                    self.nodes[key] = {
                        "name": name, "level": level, "dim": col,
                        "parent": parent_key, "group": p["Group"],
                    }
                    if parent_key is not None:
                        self.children[parent_key].append(key)
                parent_key = key

        # Baseline counts roll up the ladder: a division's establishment is the
        # sum of everything beneath it, which is how the tree has to read.
        self.baseline: dict[str, dict] = {
            k: dict(approved=0, filled=0, vacant=0, saudi=0, cost=0.0)
            for k in self.nodes
        }
        for p in self.positions:
            vacant = (p.get("Position Status") or "").strip().lower() == "vacant"
            saudi = (p.get("Nationality") or "").strip().lower().startswith("saud")
            keys = []
            for level, col in enumerate(LADDER):
                name = p.get(col, "").strip()
                if not name:
                    break
                keys.append(f"{level}|{name}")
            for k in keys:
                b = self.baseline[k]
                b["approved"] += 1
                b["filled"] += 0 if vacant else 1
                b["vacant"] += 1 if vacant else 0
                b["saudi"] += 1 if (saudi and not vacant) else 0
                b["cost"] += loaded_cost(p.get("Grade", "G10"), saudi)

    def group_key(self, group: str) -> str:
        return f"0|{group}"

    def descend(self, key: str, max_level: int = 5):
        """The subtree under a node, in reading order, as (key, node) pairs."""
        out = []

        def walk(k: str) -> None:
            node = self.nodes[k]
            if node["level"] > max_level:
                return
            out.append((k, node))
            for c in sorted(self.children.get(k, []), key=lambda x: self.nodes[x]["name"]):
                walk(c)

        walk(key)
        return out

    def group_totals(self, group: str) -> dict:
        return self.baseline[self.group_key(group)]

    def named_leavers(self, group: str) -> list[dict]:
        """Seats with a departure already booked, from the assignment end date."""
        today = dt.date.today().isoformat()
        out = []
        for p in self.positions:
            if p["Group"] != group:
                continue
            end = (p.get("Assignment End Date") or "").strip()
            if not end or end < today:
                continue
            unit = next((p[c] for c in reversed(LADDER) if p.get(c)), "")
            out.append({
                "unit": unit, "title": p.get("Job Title", ""),
                "grade": p.get("Grade", ""), "date": end,
                "quarter": quarter_of(end),
                "reason": "Resignation / assignment end",
            })
        out.sort(key=lambda r: r["date"])
        return out

    def vacancies(self, group: str) -> list[dict]:
        out = []
        for p in self.positions:
            if p["Group"] != group:
                continue
            if (p.get("Position Status") or "").strip().lower() != "vacant":
                continue
            unit = next((p[c] for c in reversed(LADDER) if p.get(c)), "")
            out.append({
                "unit": unit, "title": p.get("Job Title", ""),
                "grade": p.get("Grade", ""),
                "previous": (p.get("Previous Incumbent") or "").strip(),
            })
        out.sort(key=lambda r: (r["unit"], r["title"]))
        return out


def quarter_of(iso_date: str) -> str:
    try:
        m = int(iso_date[5:7])
    except (ValueError, IndexError):
        return "Q1"
    return QUARTERS[min(3, (m - 1) // 3)]


def gosi_rate(saudi: bool) -> float:
    return GOSI_SAUDI if saudi else GOSI_NON_SAUDI


def loaded_cost(grade: str, saudi: bool = True) -> float:
    """Annual loaded cost in SAR '000, matching the workbook's own formula."""
    basic, housing, transport, bonus = GRADE_COST.get(grade, GRADE_COST["G10"])
    return basic + housing + transport + basic * bonus + (basic + housing) * gosi_rate(saudi)


def one_off(grade: str) -> int:
    return ONE_OFF_SENIOR if grade >= SENIOR_FROM else ONE_OFF_JUNIOR


def rank_of(category: str) -> int:
    for name, rank, _ in RANK_CATEGORIES:
        if name == category:
            return rank
    return len(RANK_CATEGORIES)


def driver_category(driver: str) -> str:
    for name, cat in ASK_DRIVERS:
        if name == driver:
            return cat
    return "Other"


if __name__ == "__main__":
    bank = Bank()
    print(f"{len(bank.groups)} groups, {len(bank.positions)} positions")
    for g in bank.groups:
        t = bank.group_totals(g)
        print(f"  {g:32} approved {t['approved']:5}  filled {t['filled']:5}"
              f"  vacant {t['vacant']:4}  leavers {len(bank.named_leavers(g)):3}"
              f"  cost {t['cost']:9,.0f}")
