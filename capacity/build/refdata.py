"""Reference data for the 2027 capacity exercise.

Everything the three workbooks share: the bank's structure and 2026 baseline read
from the org tool's own sample export, the career-level rate card, the driver
catalogue, and the exercise settings. Read once here so the template, the worked
example and the consolidator cannot drift from each other.
"""
from __future__ import annotations

import csv
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
SUBMISSION_STATES = ["Draft", "Submitted", "Challenged", "Approved"]

# ── Career level ───────────────────────────────────────────────────────────
# A property of the job, not of the grade, so it cannot be derived from the org
# export. These are placeholders: replace them with the bank's own ladder on the
# Ref sheet, or supply the level per position in the export and it flows through.
CAREER_LEVELS = [
    "Executive",
    "Senior Management",
    "Management",
    "Professional",
    "Officer",
    "Support",
]

# ── What each existing seat is meant to do in the plan year ────────────────
# Only Exit moves the establishment. The others are intent, and Reduce is a
# watch list rather than a number — see the note written onto the sheet.
CAPACITY_DIRECTIONS = [
    ("Grow", "More capacity needed here. The growth arrives as a row on the asks sheet."),
    ("Hold", "Stays as it is."),
    ("Reduce", "Under review. The seat stays for now and is revisited mid-year."),
    ("Exit", "The seat lapses and comes out of the plan-year establishment."),
]
EXIT_DIRECTION = "Exit"

# ── Ranking ────────────────────────────────────────────────────────────────
# What a constrained scenario cuts first. The order is the user's: the growth
# agenda sits above control capacity, and business as usual absorbs the cut.
RANK_CATEGORIES = [
    ("Regulatory", 1, "Mandated by SAMA or another regulator; not discretionary."),
    ("Strategic", 2, "The growth agenda — volume, new products, coverage, automation."),
    ("Control", 3, "Risk and control capacity, including audit finding remediation."),
    ("BAU", 4, "Running the bank. First to be cut when the envelope binds."),
]

# ── Why a position is being asked for ──────────────────────────────────────
ASK_DRIVERS = [
    ("SAMA regulatory requirement", "Regulatory"),
    ("New regulation implementation", "Regulatory"),
    ("Regulatory audit finding", "Regulatory"),
    ("Risk framework uplift", "Regulatory"),
    ("Volume growth - existing product", "Strategic"),
    ("New product launch", "Strategic"),
    ("Branch or channel expansion", "Strategic"),
    ("Client coverage expansion", "Strategic"),
    ("Automation enablement", "Strategic"),
    ("Control gap closure", "Control"),
    ("Internal audit finding", "Control"),
    ("Business continuity / resilience", "Control"),
    ("Backfill - resignation", "BAU"),
    ("Backfill - retirement", "BAU"),
    ("Backfill - internal move", "BAU"),
    ("Process centralisation", "BAU"),
    ("Insourcing from vendor", "BAU"),
    ("Service level improvement", "BAU"),
    ("Other - see note", "BAU"),
]

# ── The rate card ──────────────────────────────────────────────────────────
# SAR '000 per annum, by career level. Illustrative and clearly marked as such:
# these rates are the first thing Finance should replace, and every component is
# separate so a rate can be challenged without rebuilding the model.
#   career level: (basic, housing, transport, target bonus %, one-off of a hire)
LEVEL_COST = {
    "Executive":        (900, 225, 36, 0.30, 45),
    "Senior Management": (540, 135, 30, 0.22, 45),
    "Management":       (336, 84,  18, 0.15, 30),
    "Professional":     (216, 54,  14, 0.10, 18),
    "Officer":          (138, 35,  12, 0.07, 12),
    "Support":          (96,  24,  12, 0.05, 12),
}
# Employer GOSI on basic + housing. Saudi nationals attract pension and
# unemployment contributions; non-Saudis attract occupational hazard only. A
# seat the bank has mandated as Saudi is costed at the Saudi rate.
GOSI_SAUDI = 0.1175
GOSI_NON_SAUDI = 0.02

# Grades are still in the org export and are the only cost signal the sample
# data carries, so they set the illustrative envelope — and nothing else. No
# formula in any workbook reads them.
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
                b["cost"] += envelope_cost(p.get("Grade", "G10"), saudi)

        families = {(p.get("Job Family") or "").strip() for p in self.positions}
        self.job_families = sorted(f for f in families if f)

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

    def divisions(self, group: str) -> list[str]:
        return [n["name"] for _, n in self.descend(self.group_key(group))
                if n["level"] == 1]

    def seats(self, group: str) -> list[dict]:
        """One row per existing position, shaped for the Current capacity sheet.

        Career level is absent on purpose: it is a property of the job rather
        than of the grade, so it cannot be derived here. Add a "Career Level"
        column to the export and it flows straight through.
        """
        out = []
        for p in self.positions:
            if p.get("Group") != group:
                continue
            vacant = (p.get("Position Status") or "").strip().lower() == "vacant"
            # A seat counts as one seat. The export carries a fractional FTE for
            # part-timers, but the structure sheet counts positions, and two
            # sheets in one file disagreeing about the establishment is worse
            # than losing the half.
            seat = 1.0
            out.append({
                "mis": (p.get("Cost Center") or "").strip(),
                "division": (p.get("Division") or "").strip(),
                "department": (p.get("Department") or "").strip(),
                "unit": (p.get("Unit") or "").strip(),
                "sub_unit": (p.get("Sub-unit") or "").strip(),
                "title": (p.get("Job Title") or "").strip(),
                "level": (p.get("Career Level") or "").strip(),
                "family": (p.get("Job Family") or "").strip(),
                "worker_type": worker_type_of(p.get("Employment Type", "")),
                "approved": seat,
                "filled": 0.0 if vacant else seat,
                "vacant": seat if vacant else 0.0,
            })
        out.sort(key=lambda r: (r["division"], r["department"], r["unit"],
                                r["sub_unit"], r["title"]))
        return out


def worker_type_of(employment_type: str) -> str:
    """The export's employment types, mapped onto the three the exercise uses."""
    text = (employment_type or "").strip().lower()
    if "outsourc" in text or "vendor" in text:
        return "Outsourced"
    if "insourc" in text or "contract" in text or "agency" in text:
        return "Insourced"
    return "Permanent"


def gosi_rate(saudi: bool) -> float:
    return GOSI_SAUDI if saudi else GOSI_NON_SAUDI


def level_cost(level: str, mandated_saudi: bool = True) -> float:
    """Full-year loaded cost in SAR '000, matching the workbook's own formula."""
    if level not in LEVEL_COST:
        return 0.0
    basic, housing, transport, bonus, _ = LEVEL_COST[level]
    return (basic + housing + transport + basic * bonus
            + (basic + housing) * gosi_rate(mandated_saudi))


def one_off(level: str) -> int:
    """One-off cost of a hire, recognised in the year of joining only."""
    return LEVEL_COST[level][4] if level in LEVEL_COST else 0


def envelope_cost(grade: str, saudi: bool = True) -> float:
    """Grade-based cost, used only to set the illustrative envelope from the
    2026 population. No workbook formula reads it."""
    basic, housing, transport, bonus = GRADE_COST.get(grade, GRADE_COST["G10"])
    return basic + housing + transport + basic * bonus + (basic + housing) * gosi_rate(saudi)


def rank_of(category: str) -> int:
    for name, rank, _ in RANK_CATEGORIES:
        if name == category:
            return rank
    return len(RANK_CATEGORIES)


def driver_category(driver: str) -> str:
    for name, cat in ASK_DRIVERS:
        if name == driver:
            return cat
    return RANK_CATEGORIES[-1][0]


if __name__ == "__main__":
    bank = Bank()
    print(f"{len(bank.groups)} groups, {len(bank.positions)} positions, "
          f"{len(bank.job_families)} job families")
    for g in bank.groups:
        t = bank.group_totals(g)
        seats = bank.seats(g)
        levelled = sum(1 for s in seats if s["level"])
        print(f"  {g:32} approved {t['approved']:5}  filled {t['filled']:5}"
              f"  vacant {t['vacant']:4}  seats {len(seats):4}"
              f"  with a career level {levelled:4}"
              f"  divisions {len(bank.divisions(g)):2}")
