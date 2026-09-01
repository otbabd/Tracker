"""The worked example: one group's template, filled in the way it should be.

This is the file that goes in the kickoff pack. It is the same template every
group receives — nothing is added to it — with a plausible set of answers typed
into the yellow cells, so a group head can see what a good submission looks like
before starting their own.
"""
from __future__ import annotations

import random
from pathlib import Path

from openpyxl import load_workbook

import refdata as R
import template as T

GROUP = "Risk Group"
DIST = Path(__file__).resolve().parents[1] / "dist"

# What drives the work in a risk unit. Matched on the unit's own name so the
# example reads like someone who knows the group filled it in.
DRIVER_HINTS = [
    ("audit", "Audits or reviews delivered"),
    ("review", "Audits or reviews delivered"),
    ("report", "Reports or returns produced"),
    ("regulat", "Reports or returns produced"),
    ("model", "Change requests delivered"),
    ("credit", "Applications processed"),
    ("underwrit", "Applications processed"),
    ("fraud", "Cases or tickets handled"),
    ("collect", "Cases or tickets handled"),
    ("recover", "Cases or tickets handled"),
    ("operational", "Cases or tickets handled"),
    ("market", "Transactions processed"),
    ("liquid", "Transactions processed"),
    ("portfolio", "Accounts serviced"),
    ("data", "Systems or applications supported"),
    ("system", "Systems or applications supported"),
    ("policy", "Reports or returns produced"),
    ("govern", "Reports or returns produced"),
]
FALLBACK_DRIVERS = [
    "Cases or tickets handled", "Reports or returns produced",
    "Audits or reviews delivered", "Accounts serviced",
]

COVER_NOTES = [
    "", "", "Two insourced analysts since March",
    "Overtime running at about 6% of hours", "",
    "One vendor resource covering month-end", "",
]


def driver_for(name: str, i: int) -> str:
    low = name.lower()
    for key, driver in DRIVER_HINTS:
        if key in low:
            return driver
    return FALLBACK_DRIVERS[i % len(FALLBACK_DRIVERS)]


# The asks. Written by hand rather than generated: the point of the example is
# that the justifications read like a person wrote them.
ASKS = [
    ("Senior Model Validation Analyst", "G13", "Permanent", "Saudi", "Growth", 1, "Q1",
     "SAMA regulatory requirement",
     "Reviewed with Model Risk; the existing two validators cannot cover the "
     "IFRS 9 revalidation and the new scorecards in the same year.",
     "Two models deferred to 2028 if not filled"),
    ("Model Validation Analyst", "G11", "Permanent", "Saudi", "Growth", 1, "Q2",
     "New regulation implementation",
     "Considered using the vendor panel; rejected on cost and on the "
     "independence requirement.", "Supports the new unit NEW-01"),
    ("Head of Model Validation", "G15", "Permanent", "Saudi", "Growth", 1, "Q1",
     "SAMA regulatory requirement",
     "Cannot be covered by the existing Head of Model Risk without breaching "
     "the separation SAMA asked for in the 2026 review.", "Leads NEW-01"),
    ("Credit Risk Analyst", "G11", "Permanent", "Saudi", "Growth", 2, "Q2",
     "Volume growth - existing product",
     "Automation of the pre-screen took out about 15% of the manual work; the "
     "residual volume still needs two more analysts.",
     "Corporate book growing 18% on plan"),
    ("Senior Credit Risk Analyst", "G13", "Permanent", "Saudi", "Growth", 1, "Q3",
     "Volume growth - existing product",
     "Start held to Q3 so the cost lands half-year.", ""),
    ("Operational Risk Officer", "G12", "Permanent", "Saudi", "Replacement", 1, "Q1",
     "Backfill - resignation",
     "Same role, same grade. The work does not stop when the person leaves.",
     "Leaver confirmed on sheet 3"),
    ("Operational Risk Officer", "G12", "Permanent", "Saudi", "Replacement", 1, "Q2",
     "Backfill - retirement", "Retirement known since 2025; no change to the role.", ""),
    ("Fraud Analyst", "G10", "Permanent", "Saudi", "Growth", 1, "Q2",
     "Control gap closure",
     "The 2026 internal audit finding on out-of-hours cover cannot be closed "
     "with the current five-person rota.", "Audit finding OR-2026-14"),
    ("Senior Fraud Analyst", "G12", "Permanent", "Saudi", "Growth", 1, "Q3",
     "Internal audit finding",
     "Considered extending the outsourced night shift; rejected because the "
     "finding is specifically about decision authority sitting outside the bank.", ""),
    ("Risk Reporting Analyst", "G11", "Permanent", "Saudi", "Conversion", 1, "Q2",
     "Insourcing from vendor",
     "Currently an outsourced seat at a higher day rate. Converting is cheaper "
     "from month nine and keeps the reporting logic in-house.",
     "Replaces an outsourced seat"),
    ("Risk Data Engineer", "G13", "Permanent", "Non-Saudi", "Growth", 1, "Q3",
     "Automation enablement",
     "Pays back inside eighteen months on the manual reconciliation it removes.",
     "Scarce skill; market rate assumed at grade"),
    ("Risk Data Analyst", "G11", "Permanent", "Saudi", "Growth", 1, "Q3",
     "Automation enablement", "Works alongside the engineer above.", ""),
    ("Market Risk Analyst", "G12", "Permanent", "Saudi", "Growth", 1, "Q2",
     "Risk framework uplift",
     "The revised limit framework needs daily monitoring the current team "
     "cannot absorb on top of the FRTB work.", ""),
    ("Liquidity Risk Analyst", "G12", "Permanent", "Saudi", "Growth", 1, "Q4",
     "Regulatory audit finding",
     "Deferred to Q4 deliberately; the framework work has to land first.", ""),
    ("Portfolio Monitoring Officer", "G10", "Permanent", "Saudi", "Growth", 1, "Q3",
     "Volume growth - existing product",
     "Considered raising the review threshold instead; rejected by the Credit "
     "Committee in October.", ""),
    ("Collections Officer", "G9", "Insourced", "Saudi", "Growth", 1, "Q2",
     "Volume growth - existing product",
     "Insourced rather than permanent because the volume peak is expected to "
     "unwind once the 2026 vintage runs off.", "Reviewed again at 2028 planning"),
    ("Risk Governance Officer", "G12", "Permanent", "Saudi", "Replacement", 1, "Q1",
     "Backfill - internal move",
     "Moved to Compliance in November; the committee secretariat still needs "
     "running.", ""),
    ("Risk Policy Specialist", "G13", "Permanent", "Saudi", "Growth", 1, "Q4",
     "New regulation implementation",
     "Considered a fixed-term contract; the policy work is continuing, not a "
     "project.", ""),
]


def fill(layout: dict, bank: R.Bank, path: Path) -> Path:
    rng = random.Random(2027)
    wb = load_workbook(path)

    # ── 2. Current capacity ────────────────────────────────────────────────
    ws = wb[T.SH_CAP]
    first, last = layout["cap"]
    units = [(k, n) for k, n in bank.descend(bank.group_key(GROUP))
             if 2 <= n["level"] <= 3]
    for i, (key, node) in enumerate(units):
        r = first + i
        filled = bank.baseline[key]["filled"] or 1
        driver = driver_for(node["name"], i)
        scale = {"Accounts serviced": 900, "Transactions processed": 14000,
                 "Applications processed": 1100, "Cases or tickets handled": 2400,
                 "Audits or reviews delivered": 9, "Reports or returns produced": 55,
                 "Systems or applications supported": 6,
                 "Change requests delivered": 40}.get(driver, 800)
        base_vol = int(filled * scale * rng.uniform(0.85, 1.2))
        growth = rng.choice([0.05, 0.07, 0.09, 0.12, 0.15, 0.18])
        ws.cell(row=r, column=5, value=driver)
        ws.cell(row=r, column=6, value=base_vol)
        ws.cell(row=r, column=7, value=int(base_vol * (1 + growth)))
        ws.cell(row=r, column=9, value=round(filled * rng.uniform(0.75, 0.95), 1))
        if i % 4 == 0:                      # a few units commit to more than the default
            ws.cell(row=r, column=11, value=rng.choice([0.04, 0.05, 0.06]))
        ws.cell(row=r, column=14, value=COVER_NOTES[i % len(COVER_NOTES)] or None)
        ws.cell(row=r, column=15, value=rng.choice([2, 3, 3, 4, 4, 5]))

    # ── 3. Attrition & pipeline ────────────────────────────────────────────
    ws = wb[T.SH_ATTR]
    attr = layout["attr"]
    ws.cell(row=attr["rate_row"], column=2, value=0.10)
    leavers = bank.named_leavers(GROUP)
    for i in range(len(leavers)):
        r = attr["leaver_first"] + i
        ws.cell(row=r, column=7, value="No" if i % 6 == 5 else "Yes")
    vac = bank.vacancies(GROUP)
    for i in range(len(vac)):
        r = attr["vac_first"] + i
        keep = i % 7 != 6
        ws.cell(row=r, column=5, value="Yes" if keep else "No")
        ws.cell(row=r, column=6,
                value=None if keep else "Work absorbed by the 2026 automation release")

    # ── 4. Structure changes ───────────────────────────────────────────────
    ws = wb[T.SH_CHG]
    cfirst, _ = layout["chg"]
    parents = [n["name"] for _, n in bank.descend(bank.group_key(GROUP))
               if n["level"] == 1]
    parent = parents[0] if parents else GROUP
    changes = [
        ("New unit", "Model Validation", "Unit", parent, "Control",
         "Independent validation, separated from model development at SAMA's "
         "request in the 2026 review.", None, "Q1"),
        ("Merge into another unit", "Operational Risk Reporting", "Sub-unit", parent,
         "Control",
         "Folded into Risk Reporting: one reporting team, one calendar, two "
         "people released.", 2, "Q2"),
        ("Close", "Basel Programme Office", "Unit", parent, "Project",
         "The programme closes in 2026; the residual work moves into policy.",
         1, "Q3"),
    ]
    for i, (action, name, level, par, ftype, why, people, when) in enumerate(changes):
        r = cfirst + i
        for col, value in zip(range(2, 10),
                              [action, name, level, par, ftype, why, people, when]):
            ws.cell(row=r, column=col, value=value)

    # ── 5. Capacity asks ───────────────────────────────────────────────────
    ws = wb[T.SH_ASK]
    unit_names = [n["name"] for _, n in bank.descend(bank.group_key(GROUP))
                  if n["level"] >= 2]
    for i, ask in enumerate(ASKS):
        (title, grade, wtype, basis, nature, fte, quarter, driver,
         alternatives, note) = ask
        r = layout["ask_first"] + i
        unit = ("NEW-01" if "Model Validation" in title
                else unit_names[i % len(unit_names)])
        for col, value in zip(range(2, 15), [
                unit, title, grade, wtype, basis, nature, fte, quarter, driver,
                None, None, alternatives, note or None]):
            if col in (11, 12):             # category and rank are computed
                continue
            ws.cell(row=r, column=col, value=value)

    # ── 7. Check & submit ──────────────────────────────────────────────────
    ws = wb[T.SH_CHK]
    chk = layout["chk"]
    ws.cell(row=chk["ready_row"] + 1, column=2, value="Head of Risk Portfolio & Planning")
    ws.cell(row=chk["ready_row"] + 2, column=2, value="risk.planning@bank.example")
    ws.cell(row=chk["ready_row"] + 3, column=2, value=f"15 October {R.BASE_YEAR}")
    ws.cell(row=chk["state_row"], column=2, value="Submitted")

    wb.save(path)
    return path


def build_example(path=None) -> dict:
    bank = R.Bank()
    path = Path(path or DIST / f"{R.PLAN_YEAR}-Capacity-Example-RiskGroup.xlsx")
    layout = T.build_template(GROUP, path, bank)
    fill(layout, bank, path)
    layout["path"] = str(path)
    return layout


if __name__ == "__main__":
    print(build_example()["path"])
