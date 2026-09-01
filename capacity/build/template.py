"""The group capacity template.

One workbook per group. Carries that group's structure and 2026 baseline, asks
for what it needs in 2027, prices it, tests it against the group's envelopes, and
tells the group head what is still missing before it can be submitted.

Nothing here is macro-driven: every calculation is a native formula, so the file
opens and recalculates anywhere without a security prompt.
"""
from __future__ import annotations

from openpyxl import Workbook
from openpyxl.chart import BarChart, Reference
from openpyxl.formatting.rule import CellIsRule, FormulaRule
from openpyxl.utils import get_column_letter
from openpyxl.workbook.defined_name import DefinedName
from openpyxl.worksheet.datavalidation import DataValidation

import refdata as R
import style as S

ASK_ROWS = 300          # generous headroom; no group will reach it
CHANGE_ROWS = 40
LEAVER_ROWS = 60
DRIVER_ROWS = 80

SH_READ = "Read me"
SH_TREE = "1. My structure"
SH_CAP = "2. Current capacity"
SH_ATTR = "3. Attrition & pipeline"
SH_CHG = "4. Structure changes"
SH_ASK = "5. Capacity asks"
SH_POS = "6. My position"
SH_CHK = "7. Check & submit"
SH_REF = "Ref"


# ── Reference sheet ─────────────────────────────────────────────────────────
def build_ref(wb: Workbook, bank: R.Bank, group: str) -> None:
    """Lookup tables and the exercise settings. Hidden, and the only place a
    rate is stated — every formula that needs one points here."""
    ws = wb.create_sheet(SH_REF)
    ws.sheet_state = "hidden"
    row = S.sheet_title(ws, "Reference data", "Do not edit. Maintained centrally.")

    ws.cell(row=row, column=1, value="Settings").font = S.H1
    row += 1
    settings = [
        ("Plan year", R.PLAN_YEAR, None),
        ("Base year", R.BASE_YEAR, None),
        ("Group", group, None),
        ("Attrition rate (bank default)", R.DEFAULT_ATTRITION, S.PCT),
        ("Productivity uplift (bank default)", R.DEFAULT_PRODUCTIVITY, S.PCT),
        ("Salary inflation", R.DEFAULT_SALARY_INFLATION, S.PCT),
        ("Employer GOSI - Saudi", R.GOSI_SAUDI, S.PCT),
        ("Employer GOSI - non-Saudi", R.GOSI_NON_SAUDI, S.PCT),
        ("One-off cost - grade below " + R.SENIOR_FROM, R.ONE_OFF_JUNIOR, S.MONEY),
        ("One-off cost - grade " + R.SENIOR_FROM + " and above", R.ONE_OFF_SENIOR, S.MONEY),
    ]
    first_setting = row
    for label, value, fmt in settings:
        c = S.label_value(ws, row, label, value, fmt)
        c.font = S.INPUT
        row += 1
    names = {
        "PlanYear": first_setting, "BaseYear": first_setting + 1, "GroupName": first_setting + 2,
        "AttritionDefault": first_setting + 3, "ProductivityDefault": first_setting + 4,
        "SalaryInflation": first_setting + 5, "GosiSaudi": first_setting + 6,
        "GosiOther": first_setting + 7, "OneOffJunior": first_setting + 8,
        "OneOffSenior": first_setting + 9,
    }
    for name, r in names.items():
        wb.defined_names.add(DefinedName(name, attr_text=f"'{SH_REF}'!$B${r}"))

    # Envelopes — the group's ceilings, set centrally.
    row += 1
    ws.cell(row=row, column=1, value="Envelope for this group").font = S.H1
    row += 1
    tot = bank.group_totals(group)
    base_saudi = tot["saudi"] / tot["filled"] if tot["filled"] else 0
    env = [
        ("Cost envelope (SAR '000)", round(tot["cost"] * 0.06, 0), S.MONEY),
        ("Headcount envelope (net adds)", max(5, round(tot["approved"] * 0.05)), S.COUNT),
        ("Saudization target", round(base_saudi + 0.02, 2), S.PCT),
    ]
    first_env = row
    notes = [
        "Illustrative: six per cent of the group's current pay bill.",
        "Illustrative: five per cent of the group's current establishment.",
        "Illustrative: two points above where the group stands today.",
    ]
    for (label, value, fmt), why in zip(env, notes):
        S.label_value(ws, row, label, value, fmt, note=why).font = S.INPUT
        row += 1
    for i, name in enumerate(["CostEnvelope", "HeadEnvelope", "SaudiTarget"]):
        wb.defined_names.add(DefinedName(name, attr_text=f"'{SH_REF}'!$B${first_env + i}"))

    # Grade cost table.
    row += 1
    ws.cell(row=row, column=1, value="Grade cost table (SAR '000 per annum)").font = S.H1
    ws.cell(row=row, column=6,
            value="Illustrative rates — replace with Finance's own before use.").font = S.NOTE
    row += 1
    S.header_row(ws, row, ["Grade", "Basic", "Housing", "Transport", "Bonus %", "Rank"],
                 [12, 12, 12, 12, 12, 8])
    ws.freeze_panes = None
    grade_first = row + 1
    for i, (g, (b, h, t, bo)) in enumerate(R.GRADE_COST.items()):
        r = grade_first + i
        ws.cell(row=r, column=1, value=g)
        ws.cell(row=r, column=2, value=b).number_format = S.MONEY
        ws.cell(row=r, column=3, value=h).number_format = S.MONEY
        ws.cell(row=r, column=4, value=t).number_format = S.MONEY
        ws.cell(row=r, column=5, value=bo).number_format = S.PCT
        ws.cell(row=r, column=6, value=i + 1)
    grade_last = grade_first + len(R.GRADE_COST) - 1
    for name, col in [("GradeList", "A"), ("GradeBasic", "B"), ("GradeHousing", "C"),
                      ("GradeTransport", "D"), ("GradeBonus", "E"), ("GradeRank", "F")]:
        wb.defined_names.add(
            DefinedName(name, attr_text=f"'{SH_REF}'!${col}${grade_first}:${col}${grade_last}"))
    row = grade_last + 2

    # Ask drivers and their ranking category.
    ws.cell(row=row, column=1, value="Ask drivers").font = S.H1
    row += 1
    S.header_row(ws, row, ["Driver", "Category", "Rank"], [40, 18, 8])
    ws.freeze_panes = None
    drv_first = row + 1
    for i, (name, cat) in enumerate(R.ASK_DRIVERS):
        r = drv_first + i
        ws.cell(row=r, column=1, value=name)
        ws.cell(row=r, column=2, value=cat)
        ws.cell(row=r, column=3, value=R.rank_of(cat))
    drv_last = drv_first + len(R.ASK_DRIVERS) - 1
    for name, col in [("DriverList", "A"), ("DriverCategory", "B"), ("DriverRank", "C")]:
        wb.defined_names.add(
            DefinedName(name, attr_text=f"'{SH_REF}'!${col}${drv_first}:${col}${drv_last}"))
    row = drv_last + 2

    # Simple pick lists.
    lists = [
        ("WorkloadDrivers", [d for d, _ in R.WORKLOAD_DRIVERS]),
        ("QuarterList", R.QUARTERS),
        ("WorkforceTypes", R.WORKFORCE_TYPES),
        ("SaudiBasisList", R.SAUDI_BASIS),
        ("AskNatureList", R.ASK_NATURE),
        ("StructureActions", R.STRUCTURE_ACTIONS),
        ("LadderLevels", R.LADDER),
        ("YesNo", ["Yes", "No"]),
    ]
    col = 1
    for name, values in lists:
        ws.cell(row=row, column=col, value=name.replace("List", "")).font = S.H2
        for i, v in enumerate(values, start=1):
            ws.cell(row=row + i, column=col, value=v)
        letter = get_column_letter(col)
        wb.defined_names.add(
            DefinedName(name,
                        attr_text=f"'{SH_REF}'!${letter}${row + 1}:${letter}${row + len(values)}"))
        col += 2

    # Every unit in this group, for the asks dropdown.
    unit_col = col
    ws.cell(row=row, column=unit_col, value="Units").font = S.H2
    units = [n["name"] for _, n in bank.descend(bank.group_key(group))]
    for i, u in enumerate(units, start=1):
        ws.cell(row=row + i, column=unit_col, value=u)
    letter = get_column_letter(unit_col)
    wb.defined_names.add(
        DefinedName("UnitList",
                    attr_text=f"'{SH_REF}'!${letter}${row + 1}:${letter}${row + len(units)}"))
    return


# ── Read me ─────────────────────────────────────────────────────────────────
def build_readme(wb: Workbook, group: str) -> None:
    ws = wb.create_sheet(SH_READ)
    row = S.sheet_title(
        ws, f"{R.PLAN_YEAR} Capacity Exercise",
        f"{group} — what to do, in the order to do it")
    ws.column_dimensions["A"].width = 26
    for c in "BCDEFGH":
        ws.column_dimensions[c].width = 14

    steps = [
        ("1. My structure",
         "Your group as it stands today, down to section level. Collapse and expand with the "
         "+/- buttons in the left margin. Nothing to fill in — read it and check it looks right."),
        ("2. Current capacity",
         "For each unit: what is approved, filled and vacant today, what drives its workload, "
         "and how much of that work one person gets through. This is what your ask will be "
         "argued against, so it is worth getting right."),
        ("3. Attrition & pipeline",
         "Who you already know is leaving, and what is already in recruitment. Confirm each "
         f"{R.BASE_YEAR} vacancy you still need — anything you do not confirm will lapse."),
        ("4. Structure changes",
         "New units, moves, closures, merges and renames. Give a new unit a temporary ID here "
         "and you can then ask for positions into it on the next sheet."),
        ("5. Capacity asks",
         "One row per position you want. The cost is worked out for you as you type. Every row "
         "needs a driver, because that is what decides the order things get funded in."),
        ("6. My position",
         "Where your ask lands against your cost envelope, your headcount envelope and your "
         "Saudization target. Read this before you submit, not after."),
        ("7. Check & submit",
         "Everything still missing or invalid, listed row by row. When it is clear, set the "
         "state to Submitted and return the file."),
    ]
    ws.cell(row=row, column=1, value="What to do").font = S.H1
    row += 1
    for name, why in steps:
        ws.cell(row=row, column=1, value=name).font = S.H2
        ws.cell(row=row, column=1).alignment = S.TOP
        c = ws.cell(row=row, column=2, value=why)
        c.font = S.BODY_DIM
        c.alignment = S.WRAP
        ws.merge_cells(start_row=row, start_column=2, end_row=row, end_column=8)
        ws.row_dimensions[row].height = 34
        row += 1

    row += 1
    row = S.legend(ws, row)

    ws.cell(row=row, column=1, value="Two things worth knowing").font = S.H1
    row += 1
    for text in [
        "The cost shown to you is a loaded cost — basic, housing, transport, employer GOSI and "
        "target bonus — in SAR thousands. It is the same rate table the centre will price your "
        "ask with, so there are no surprises on the way back.",
        "A position asked for in Q1 costs a full year; one asked for in Q4 costs a quarter of a "
        "year. Moving a start date is the cheapest concession you can offer, and it is usually "
        "the first thing you will be asked for.",
    ]:
        S.note_line(ws, row, text)
        row += 1
    S.print_setup(ws, landscape=False)


# ── 1. My structure ─────────────────────────────────────────────────────────
def build_tree(wb: Workbook, bank: R.Bank, group: str) -> None:
    ws = wb.create_sheet(SH_TREE)
    row = S.sheet_title(
        ws, "My structure",
        f"{group} as it stands in {R.BASE_YEAR}. Use the +/- buttons on the left "
        f"to collapse and expand. {R.PLAN_YEAR} fills in from your asks.")
    heads = ["Level", "Unit", f"{R.BASE_YEAR} approved", "Filled", "Vacant",
             f"{R.PLAN_YEAR} asked", f"{R.PLAN_YEAR} total", "Change"]
    S.header_row(ws, row, heads, [14, 46, 15, 11, 11, 14, 14, 11])
    first = row + 1

    ws.sheet_properties.outlinePr.summaryBelow = False
    nodes = bank.descend(bank.group_key(group))
    r = first
    for key, node in nodes:
        b = bank.baseline[key]
        lvl = node["level"]
        ws.cell(row=r, column=1, value=node["dim"]).font = S.SMALL
        name = ws.cell(row=r, column=2, value=("    " * lvl) + node["name"])
        name.font = S.H2 if lvl <= 1 else S.BODY
        ws.cell(row=r, column=3, value=b["approved"]).number_format = S.COUNT
        ws.cell(row=r, column=4, value=b["filled"]).number_format = S.COUNT
        ws.cell(row=r, column=5, value=b["vacant"]).number_format = S.COUNT
        # Asks land against the unit named on the ask sheet.
        ws.cell(row=r, column=6,
                value=f'=SUMIFS(\'{SH_ASK}\'!$H${ASK_FIRST}:$H${ASK_LAST},'
                      f'\'{SH_ASK}\'!$B${ASK_FIRST}:$B${ASK_LAST},$B{r})').number_format = S.FTE
        ws.cell(row=r, column=7, value=f"=$C{r}+$F{r}").number_format = S.FTE
        ws.cell(row=r, column=8, value=f"=$F{r}").number_format = S.FTE
        for col in range(3, 9):
            ws.cell(row=r, column=col).font = S.BODY if lvl > 1 else S.H2
        if lvl > 0:
            ws.row_dimensions[r].outline_level = min(lvl, 7)
        if lvl <= 1:
            S.band(ws, r, len(heads))
        r += 1

    last = r - 1
    ws.conditional_formatting.add(
        f"H{first}:H{last}",
        CellIsRule(operator="greaterThan", formula=["0"], font=S.f(10, True, S.OK_GREEN)))
    ws.conditional_formatting.add(
        f"E{first}:E{last}",
        CellIsRule(operator="greaterThan", formula=["0"], font=S.f(10, False, S.AMBER)))
    S.print_setup(ws, title_rows=f"{row}:{row}")
    return


# ── 2. Current capacity ─────────────────────────────────────────────────────
def build_capacity(wb: Workbook, bank: R.Bank, group: str) -> None:
    ws = wb.create_sheet(SH_CAP)
    row = S.sheet_title(
        ws, "Current capacity",
        "What each unit has today, what drives its work, and how much of that work "
        "one person gets through. The yellow cells are yours.")
    heads = ["Unit", "Approved", "Filled", "Vacant", "Workload driver",
             f"{R.BASE_YEAR} volume", f"{R.PLAN_YEAR} expected volume", "Volume growth",
             "FTE on this work", f"Output per FTE ({R.BASE_YEAR})",
             "Productivity uplift", f"{R.PLAN_YEAR} FTE required", "Gap vs filled",
             "Overtime / insourced cover", "How stretched (1-5)"]
    S.header_row(ws, row, heads,
                 [34, 10, 9, 9, 26, 14, 16, 12, 12, 14, 12, 14, 12, 20, 14])
    first = row + 1

    # One row per unit at department level and below — where work actually sits.
    units = [(k, n) for k, n in bank.descend(bank.group_key(group)) if 2 <= n["level"] <= 3]
    r = first
    for key, node in units:
        b = bank.baseline[key]
        ws.cell(row=r, column=1, value=node["name"]).font = S.BODY
        ws.cell(row=r, column=2, value=b["approved"]).number_format = S.COUNT
        ws.cell(row=r, column=3, value=b["filled"]).number_format = S.COUNT
        ws.cell(row=r, column=4, value=b["vacant"]).number_format = S.COUNT
        for col in (5, 6, 7, 9, 11, 14, 15):
            S.input_cell(ws.cell(row=r, column=col))
        ws.cell(row=r, column=6).number_format = S.MONEY
        ws.cell(row=r, column=7).number_format = S.MONEY
        ws.cell(row=r, column=9).number_format = S.FTE
        ws.cell(row=r, column=11).number_format = S.PCT
        # Growth, implied rate, required FTE and the gap all follow from the inputs.
        ws.cell(row=r, column=8,
                value=f'=IFERROR($G{r}/$F{r}-1,"")').number_format = S.PCT
        ws.cell(row=r, column=10,
                value=f'=IFERROR($F{r}/$I{r},"")').number_format = S.MONEY1
        ws.cell(row=r, column=12,
                value=f'=IFERROR($G{r}/($J{r}*(1+IF($K{r}="",ProductivityDefault,$K{r}))),"")'
                ).number_format = S.FTE
        ws.cell(row=r, column=13,
                value=f'=IFERROR($L{r}-$C{r},"")').number_format = S.FTE
        for col in (8, 10, 12, 13):
            ws.cell(row=r, column=col).font = S.BODY
        r += 1
    last = r - 1

    ws.conditional_formatting.add(
        f"M{first}:M{last}",
        CellIsRule(operator="greaterThan", formula=["0"], font=S.f(10, True, S.AMBER)))

    dv = DataValidation(type="list", formula1="=WorkloadDrivers", allow_blank=True)
    dv.prompt = "Pick the thing that drives this unit's workload."
    dv.promptTitle = "Workload driver"
    ws.add_data_validation(dv)
    dv.add(f"E{first}:E{last}")

    dv5 = DataValidation(type="whole", operator="between", formula1=1, formula2=5,
                         allow_blank=True, showErrorMessage=True)
    dv5.error = "1 = plenty of slack, 5 = at breaking point."
    ws.add_data_validation(dv5)
    dv5.add(f"O{first}:O{last}")

    S.note_line(ws, last + 2,
                "Output per FTE is worked out from what you type: volume divided by the FTE "
                "doing it. Required FTE for " + str(R.PLAN_YEAR) + " is next year's volume "
                "divided by that same rate, improved by the productivity uplift. Leave the "
                "uplift blank to use the bank default.", cols=len(heads))
    S.print_setup(ws, title_rows=f"{row}:{row}")
    return first, last


# ── 3. Attrition & pipeline ─────────────────────────────────────────────────
def build_attrition(wb: Workbook, bank: R.Bank, group: str) -> None:
    ws = wb.create_sheet(SH_ATTR)
    row = S.sheet_title(
        ws, "Attrition & pipeline",
        "Who you already know is going, what rate applies to everyone else, and "
        f"which {R.BASE_YEAR} vacancies you still need.")

    tot = bank.group_totals(group)
    ws.column_dimensions["A"].width = 44
    ws.column_dimensions["B"].width = 16
    ws.cell(row=row, column=1, value="Rate").font = S.H1
    row += 1
    S.label_value(ws, row, "Bank default attrition rate", "=AttritionDefault",
                  S.PCT, S.LINK)
    row += 1
    rate_row = row
    S.input_cell(
        S.label_value(ws, row, "This group's rate (leave blank to use the default)",
                      None, S.PCT, note="Blue cells are yours."), S.PCT)
    row += 1
    filled_row = row
    S.label_value(ws, row, "Filled headcount today", tot["filled"], S.COUNT,
                  note=f"From the {R.BASE_YEAR} establishment.")
    row += 1
    implied_row = row
    S.label_value(
        ws, row, "Leavers implied by the rate",
        f'=ROUND($B${filled_row}*IF($B${rate_row}="",AttritionDefault,$B${rate_row}),0)',
        S.COUNT)
    row += 1
    named_row = row
    S.label_value(ws, row, "Of which already named below", None, S.COUNT)
    row += 1
    further_row = row
    S.label_value(
        ws, row, "Further leavers to assume", f"=MAX(0,$B${implied_row}-$B${named_row})",
        S.COUNT, note="What the rate expects on top of the names you know.")
    row += 2

    ws.cell(row=row, column=1, value="Named leavers and retirements").font = S.H1
    ws.cell(row=row, column=4,
            value="Pre-filled from assignment end dates already in the HR system.").font = S.NOTE
    row += 1
    heads = ["Unit", "Job title", "Grade", "Leaving date", "Quarter", "Reason", "Backfill needed?"]
    S.header_row(ws, row, heads, [34, 34, 10, 14, 10, 26, 16])
    first = row + 1
    leavers = bank.named_leavers(group)
    for i in range(LEAVER_ROWS):
        r = first + i
        src = leavers[i] if i < len(leavers) else None
        ws.cell(row=r, column=1, value=src["unit"] if src else None)
        ws.cell(row=r, column=2, value=src["title"] if src else None)
        ws.cell(row=r, column=3, value=src["grade"] if src else None)
        ws.cell(row=r, column=4, value=src["date"] if src else None)
        ws.cell(row=r, column=5, value=src["quarter"] if src else None)
        ws.cell(row=r, column=6, value=src["reason"] if src else None)
        S.input_cell(ws.cell(row=r, column=7, value="Yes" if src else None))
        if not src:
            for col in range(1, 7):
                S.input_cell(ws.cell(row=r, column=col))
    leaver_last = first + LEAVER_ROWS - 1
    ws.cell(row=named_row, column=2,
            value=f"=COUNTA($B${first}:$B${leaver_last})").number_format = S.COUNT
    dv = DataValidation(type="list", formula1="=YesNo", allow_blank=True)
    ws.add_data_validation(dv)
    dv.add(f"G{first}:G{leaver_last}")
    dvq = DataValidation(type="list", formula1="=QuarterList", allow_blank=True)
    ws.add_data_validation(dvq)
    dvq.add(f"E{first}:E{leaver_last}")

    row = leaver_last + 2
    ws.cell(row=row, column=1,
            value=f"{R.BASE_YEAR} vacancies — confirm each one you still need").font = S.H1
    ws.cell(row=row, column=4,
            value="Anything not confirmed lapses and will not carry into "
                  f"{R.PLAN_YEAR}.").font = S.NOTE
    row += 1
    S.header_row(ws, row, ["Unit", "Job title", "Grade", "Last held by",
                           "Still needed?", "If not, why"], [34, 34, 10, 24, 14, 34])
    vfirst = row + 1
    vac = bank.vacancies(group)
    for i, v in enumerate(vac):
        r = vfirst + i
        ws.cell(row=r, column=1, value=v["unit"])
        ws.cell(row=r, column=2, value=v["title"])
        ws.cell(row=r, column=3, value=v["grade"])
        ws.cell(row=r, column=4, value=v["previous"])
        S.input_cell(ws.cell(row=r, column=5))
        S.input_cell(ws.cell(row=r, column=6))
    vlast = vfirst + max(len(vac), 1) - 1
    dvv = DataValidation(type="list", formula1="=YesNo", allow_blank=True)
    ws.add_data_validation(dvv)
    dvv.add(f"E{vfirst}:E{vlast}")
    ws.conditional_formatting.add(
        f"A{vfirst}:F{vlast}",
        FormulaRule(formula=[f'$E{vfirst}="No"'], font=S.f(10, color=S.INK_MUTE)))

    S.print_setup(ws, title_rows=f"{row}:{row}")
    return dict(rate_row=rate_row, filled_row=filled_row,
                implied_row=implied_row, further_row=further_row,
                leaver_first=first, leaver_last=leaver_last,
                vac_first=vfirst, vac_last=vlast)


# ── 4. Structure changes ────────────────────────────────────────────────────
def build_changes(wb: Workbook, bank: R.Bank, group: str) -> None:
    ws = wb.create_sheet(SH_CHG)
    row = S.sheet_title(
        ws, "Structure changes",
        f"What you want the {R.PLAN_YEAR} structure to look like where it differs "
        "from today. Give a new unit an ID and you can ask for positions into it.")
    heads = ["Change ID", "Action", "Unit name", "Level", "Parent unit",
             "Function type", "Mandate / why", "People affected", "Effective from",
             "Ready to use"]
    S.header_row(ws, row, heads, [12, 22, 34, 14, 32, 22, 46, 14, 14, 12])
    first = row + 1
    for i in range(CHANGE_ROWS):
        r = first + i
        ws.cell(row=r, column=1, value=f"NEW-{i + 1:02d}").font = S.SMALL
        for col in range(2, 10):
            S.input_cell(ws.cell(row=r, column=col))
        ws.cell(row=r, column=8).number_format = S.COUNT
    last = first + CHANGE_ROWS - 1

    for i in range(CHANGE_ROWS):
        r = first + i
        # An ID is only usable on the asks sheet once the row says what the unit
        # is; this is the column the check sheet tests against.
        ws.cell(row=r, column=10,
                value=f'=IF(AND($B{r}<>"",$C{r}<>""),$A{r},"")').font = S.SMALL

    for col, name in [("B", "StructureActions"), ("D", "LadderLevels"), ("I", "QuarterList")]:
        dv = DataValidation(type="list", formula1=f"={name}", allow_blank=True)
        ws.add_data_validation(dv)
        dv.add(f"{col}{first}:{col}{last}")

    S.note_line(ws, last + 2,
                "A new unit needs a name, a level and a parent before a position can be asked "
                "into it. Closures and merges need the people affected, because that is what "
                "funds the growth elsewhere.", cols=len(heads))
    S.print_setup(ws, title_rows=f"{row}:{row}")
    return first, last


# ── 5. Capacity asks ────────────────────────────────────────────────────────
ASK_HEAD_ROW = 5
ASK_FIRST = ASK_HEAD_ROW + 1
ASK_LAST = ASK_HEAD_ROW + ASK_ROWS


def build_asks(wb: Workbook, bank: R.Bank, group: str) -> None:
    ws = wb.create_sheet(SH_ASK)
    S.sheet_title(
        ws, "Capacity asks",
        f"One row per position you want in {R.PLAN_YEAR}. Cost is worked out as you type.")
    heads = [
        "Ref", "Unit (or new unit ID)", "Job title", "Grade", "Workforce type",
        "Saudi basis", "Nature", "FTE", "Start quarter", "Driver", "Category", "Rank",
        "Alternatives considered", "Note",
        "Loaded cost (full year)", "One-off", f"{R.PLAN_YEAR} in-year cost", "Run-rate",
        "What's missing", "Issue no.",
    ]
    widths = [8, 30, 30, 9, 15, 13, 14, 7, 12, 30, 14, 7, 40, 30, 15, 10, 15, 13, 40, 9]
    S.header_row(ws, ASK_HEAD_ROW, heads, widths)

    for i in range(ASK_ROWS):
        r = ASK_FIRST + i
        ws.cell(row=r, column=1, value=i + 1).font = S.SMALL
        for col in range(2, 15):
            S.input_cell(ws.cell(row=r, column=col))
        ws.cell(row=r, column=8).number_format = S.FTE

        # Category and rank follow the driver, so the ranking rule is visible
        # rather than hidden in the consolidator.
        ws.cell(row=r, column=11,
                value=f'=IF($J{r}="","",IFERROR(INDEX(DriverCategory,MATCH($J{r},DriverList,0)),"?"))')
        ws.cell(row=r, column=12,
                value=f'=IF($J{r}="","",IFERROR(INDEX(DriverRank,MATCH($J{r},DriverList,0)),99))')

        # Loaded cost: basic + housing + transport + bonus + employer GOSI.
        idx = f"MATCH($D{r},GradeList,0)"
        ws.cell(row=r, column=15, value=(
            f'=IF($D{r}="","",'
            f'INDEX(GradeBasic,{idx})+INDEX(GradeHousing,{idx})+INDEX(GradeTransport,{idx})'
            f'+INDEX(GradeBasic,{idx})*INDEX(GradeBonus,{idx})'
            f'+(INDEX(GradeBasic,{idx})+INDEX(GradeHousing,{idx}))'
            f'*IF($F{r}="Saudi",GosiSaudi,GosiOther))'))
        ws.cell(row=r, column=16, value=(
            f'=IF($D{r}="","",IF(INDEX(GradeRank,{idx})>='
            f'INDEX(GradeRank,MATCH("{R.SENIOR_FROM}",GradeList,0)),OneOffSenior,OneOffJunior))'))
        # A Q1 start is paid for four quarters, a Q4 start for one.
        ws.cell(row=r, column=17, value=(
            f'=IF(OR($D{r}="",$I{r}="",$H{r}=""),"",'
            f'$O{r}*$H{r}*(5-MATCH($I{r},{{"Q1";"Q2";"Q3";"Q4"}},0))/4+$P{r}*$H{r})'))
        ws.cell(row=r, column=18, value=f'=IF($O{r}="","",$O{r}*$H{r})')

        # Row-level completeness, so the check sheet can name the row and the
        # reason rather than just counting failures. MID(...,3,...) drops the
        # leading separator, and MID of an empty string is itself empty.
        missing = "&".join(
            f'IF({test},", {word}","")' for test, word in [
                (f'$B{r}=""', "unit"), (f'$C{r}=""', "job title"),
                (f'$D{r}=""', "grade"), (f'$E{r}=""', "workforce type"),
                (f'$F{r}=""', "Saudi basis"), (f'$G{r}=""', "nature"),
                (f'N($H{r})<=0', "FTE"), (f'$I{r}=""', "start quarter"),
                (f'$J{r}=""', "driver"), (f'$M{r}=""', "alternatives"),
            ])
        ws.cell(row=r, column=19,
                value=f'=IF(COUNTA($B{r}:$J{r})+COUNTA($M{r}:$N{r})=0,"",'
                      f'MID({missing},3,300))')
        ws.cell(row=r, column=20,
                value=f'=IF($S{r}="","",COUNTIF($S${ASK_FIRST}:$S{r},"?*"))')
        for col in (11, 12, 15, 16, 17, 18, 19, 20):
            ws.cell(row=r, column=col).font = S.BODY
        ws.cell(row=r, column=19).font = S.f(9, color=S.RED_ALERT)
        ws.cell(row=r, column=20).font = S.SMALL
        for col in (15, 16, 17, 18):
            ws.cell(row=r, column=col).number_format = S.MONEY

    validations = [
        ("B", "UnitList"), ("D", "GradeList"), ("E", "WorkforceTypes"),
        ("F", "SaudiBasisList"), ("G", "AskNatureList"), ("I", "QuarterList"),
        ("J", "DriverList"),
    ]
    for col, name in validations:
        dv = DataValidation(type="list", formula1=f"={name}", allow_blank=True,
                            showErrorMessage=True)
        dv.error = "Pick a value from the list."
        ws.add_data_validation(dv)
        dv.add(f"{col}{ASK_FIRST}:{col}{ASK_LAST}")

    dvf = DataValidation(type="decimal", operator="between", formula1=0, formula2=50,
                         allow_blank=True, showErrorMessage=True)
    dvf.error = "FTE must be between 0 and 50."
    ws.add_data_validation(dvf)
    dvf.add(f"H{ASK_FIRST}:H{ASK_LAST}")

    # A regulatory ask reads differently from a nice-to-have.
    ws.conditional_formatting.add(
        f"K{ASK_FIRST}:K{ASK_LAST}",
        FormulaRule(formula=[f'$K{ASK_FIRST}="Regulatory"'], font=S.f(10, True, S.RED_ALERT)))
    ws.conditional_formatting.add(
        f"A{ASK_FIRST}:T{ASK_LAST}",
        FormulaRule(formula=[f'$S{ASK_FIRST}<>""'],
                    fill=S.PatternFill("solid", fgColor="FDE7E9")))
    ws.auto_filter.ref = f"A{ASK_HEAD_ROW}:T{ASK_LAST}"
    S.print_setup(ws, title_rows=f"{ASK_HEAD_ROW}:{ASK_HEAD_ROW}")


# ── Range helpers ───────────────────────────────────────────────────────────
def ask_col(col: str) -> str:
    return f"'{SH_ASK}'!${col}${ASK_FIRST}:${col}${ASK_LAST}"


def rng(sheet: str, col: str, first: int, last: int) -> str:
    return f"'{sheet}'!${col}${first}:${col}${last}"


def mini_head(ws, row: int, heads, widths=None) -> None:
    """A table header that does not touch the freeze pane — dashboards carry
    several tables on one sheet and only the top of the sheet should freeze."""
    for i, text in enumerate(heads, start=1):
        c = ws.cell(row=row, column=i, value=text)
        c.font = S.TH
        c.fill = S.FILL_HEAD
        c.alignment = S.Alignment(vertical="center", wrap_text=True)
        c.border = S.BOX
    ws.row_dimensions[row].height = 28
    if widths:
        for i, w in enumerate(widths, start=1):
            ws.column_dimensions[get_column_letter(i)].width = w


# ── 6. My position ──────────────────────────────────────────────────────────
def build_position(wb: Workbook, bank: R.Bank, group: str,
                   cap: tuple[int, int], chg: tuple[int, int]) -> dict:
    """The group's own dashboard: what it has asked for, and whether that lands
    inside the three ceilings it has been given."""
    ws = wb.create_sheet(SH_POS)
    cap_first, cap_last = cap
    chg_first, chg_last = chg
    row = S.sheet_title(
        ws, "My position",
        "Where your ask lands against your cost envelope, your headcount "
        "envelope and your Saudization target. Nothing here is typed in.")
    for col, w in zip("ABCDEF", [46, 16, 16, 16, 18, 44]):
        ws.column_dimensions[col].width = w

    tot = bank.group_totals(group)
    fte, cost_in, cost_run = ask_col("H"), ask_col("Q"), ask_col("R")

    # Where the group starts from.
    ws.cell(row=row, column=1, value=f"{R.BASE_YEAR} baseline").font = S.H1
    row += 1
    base_filled = row
    S.label_value(ws, row, "Filled headcount today", tot["filled"], S.COUNT)
    row += 1
    base_saudi = row
    S.label_value(ws, row, "Saudi nationals today", tot["saudi"], S.COUNT)
    row += 1
    S.label_value(ws, row, "Saudization today",
                  f"=IFERROR($B${base_saudi}/$B${base_filled},0)", S.PCT)
    row += 2

    # What has been asked for.
    ws.cell(row=row, column=1, value=f"Your {R.PLAN_YEAR} ask").font = S.H1
    row += 1
    ask_fte = row
    S.label_value(ws, row, "Positions asked for (FTE)", f"=SUM({fte})", S.FTE, S.LINK)
    row += 1
    for wt in R.WORKFORCE_TYPES:
        S.label_value(ws, row, f"    of which {wt.lower()}",
                      f'=SUMIFS({fte},{ask_col("E")},"{wt}")', S.FTE)
        row += 1
    ask_cost = row
    S.label_value(ws, row, f"{R.PLAN_YEAR} in-year cost (SAR '000)",
                  f"=SUM({cost_in})", S.MONEY, S.LINK,
                  note="Part-year: a Q1 start costs four quarters, a Q4 start one.")
    row += 1
    S.label_value(ws, row, f"Full-year run-rate from {R.PLAN_YEAR + 1} (SAR '000)",
                  f"=SUM({cost_run})", S.MONEY, S.LINK)
    row += 2

    # The three ceilings.
    ws.cell(row=row, column=1, value="Against your envelopes").font = S.H1
    row += 1
    mini_head(ws, row, ["Test", "Your limit", "Your number", "Headroom", "Status", ""])
    env_first = row + 1
    net_adds = (f"=SUM({fte})"
                f'-SUMIFS({rng(SH_CHG, "H", chg_first, chg_last)},'
                f'{rng(SH_CHG, "B", chg_first, chg_last)},"Close")'
                f'-SUMIFS({rng(SH_CHG, "H", chg_first, chg_last)},'
                f'{rng(SH_CHG, "B", chg_first, chg_last)},"Merge into another unit")')
    saud = (f'=($B${base_saudi}+SUMIFS({fte},{ask_col("F")},"Saudi"))'
            f"/($B${base_filled}+SUM({fte}))")
    tests = [
        (f"{R.PLAN_YEAR} cost (SAR '000)", "=CostEnvelope", f"=$B${ask_cost}", S.MONEY,
         "Positions can start later to bring this down."),
        ("Net establishment change", "=HeadEnvelope", net_adds, S.FTE,
         "Asks less the people released by closures and merges."),
        ("Saudization", "=SaudiTarget", saud, S.PCT,
         "Projected on today's people plus everything you have asked for."),
    ]
    r = env_first
    for label, limit, mine, fmt, why in tests:
        ws.cell(row=r, column=1, value=label).font = S.H2
        ws.cell(row=r, column=2, value=limit).font = S.LINK
        ws.cell(row=r, column=3, value=mine).font = S.BODY
        for col in (2, 3, 4):
            ws.cell(row=r, column=col).number_format = fmt
        if label.startswith("Saudization"):
            ws.cell(row=r, column=4, value=f"=$C{r}-$B{r}")
            ws.cell(row=r, column=5,
                    value=f'=IF($C{r}>=$B{r},"At or above target","Below target")')
        else:
            ws.cell(row=r, column=4, value=f"=$B{r}-$C{r}")
            ws.cell(row=r, column=5,
                    value=f'=IF($D{r}>=0,"Within envelope","Over envelope")')
        ws.cell(row=r, column=6, value=why).font = S.SMALL
        ws.cell(row=r, column=6).alignment = S.WRAP
        for col in range(1, 7):
            ws.cell(row=r, column=col).border = S.BOX
        r += 1
    env_last = r - 1
    cost_test, head_test, saudi_test = env_first, env_first + 1, env_first + 2
    ws.conditional_formatting.add(
        f"E{env_first}:E{env_last}",
        FormulaRule(formula=[f'OR($E{env_first}="Over envelope",$E{env_first}="Below target")'],
                    font=S.f(10, True, S.RED_ALERT)))
    ws.conditional_formatting.add(
        f"E{env_first}:E{env_last}",
        FormulaRule(formula=[f'OR($E{env_first}="Within envelope",$E{env_first}="At or above target")'],
                    font=S.f(10, True, S.OK_GREEN)))
    row = env_last + 2

    # Ranked order, so the group can see for itself what a cut would take.
    ws.cell(row=row, column=1, value="What the ranking rule funds first").font = S.H1
    ws.cell(row=row, column=6,
            value="Cut order runs bottom-up: 'Other' goes first, regulatory last.").font = S.NOTE
    row += 1
    mini_head(ws, row, ["Priority", "FTE asked", f"{R.PLAN_YEAR} cost",
                        "Cumulative cost", "Inside envelope?", ""])
    cat_first = row + 1
    r = cat_first
    for name, rank, why in R.RANK_CATEGORIES:
        ws.cell(row=r, column=1, value=f"{rank}. {name}").font = S.BODY
        ws.cell(row=r, column=2,
                value=f'=SUMIFS({fte},{ask_col("K")},"{name}")').number_format = S.FTE
        ws.cell(row=r, column=3,
                value=f'=SUMIFS({cost_in},{ask_col("K")},"{name}")').number_format = S.MONEY
        ws.cell(row=r, column=4,
                value=f"=SUM($C${cat_first}:$C{r})").number_format = S.MONEY
        ws.cell(row=r, column=5, value=f'=IF($D{r}<=CostEnvelope,"Yes","No")')
        ws.cell(row=r, column=6, value=why).font = S.SMALL
        ws.cell(row=r, column=6).alignment = S.WRAP
        for col in range(1, 7):
            ws.cell(row=r, column=col).border = S.BOX
        r += 1
    cat_last = r - 1
    ws.conditional_formatting.add(
        f"E{cat_first}:E{cat_last}",
        CellIsRule(operator="equal", formula=['"No"'], font=S.f(10, True, S.RED_ALERT)))
    row = cat_last + 2

    # Phasing — the cheapest concession a group can offer is a later start.
    ws.cell(row=row, column=1, value="When the cost lands").font = S.H1
    row += 1
    mini_head(ws, row, ["Start quarter", "FTE starting", f"{R.PLAN_YEAR} cost",
                        "Run-rate added", "", ""])
    q_first = row + 1
    for i, q in enumerate(R.QUARTERS):
        r = q_first + i
        ws.cell(row=r, column=1, value=q).font = S.BODY
        ws.cell(row=r, column=2,
                value=f'=SUMIFS({fte},{ask_col("I")},"{q}")').number_format = S.FTE
        ws.cell(row=r, column=3,
                value=f'=SUMIFS({cost_in},{ask_col("I")},"{q}")').number_format = S.MONEY
        ws.cell(row=r, column=4,
                value=f'=SUMIFS({cost_run},{ask_col("I")},"{q}")').number_format = S.MONEY
        for col in range(1, 5):
            ws.cell(row=r, column=col).border = S.BOX
    q_last = q_first + len(R.QUARTERS) - 1
    row = q_last + 2

    # Demand against capacity, read back from what the group typed on sheet 2.
    ws.cell(row=row, column=1, value="Demand against capacity, by driver").font = S.H1
    row += 1
    mini_head(ws, row, ["Workload driver", "Units", "Filled today",
                        f"{R.PLAN_YEAR} FTE required", "Modelled gap", ""])
    d_first = row + 1
    cap_a, cap_c = rng(SH_CAP, "A", cap_first, cap_last), rng(SH_CAP, "C", cap_first, cap_last)
    cap_e, cap_l = rng(SH_CAP, "E", cap_first, cap_last), rng(SH_CAP, "L", cap_first, cap_last)
    cap_m = rng(SH_CAP, "M", cap_first, cap_last)
    for i, (name, unit) in enumerate(R.WORKLOAD_DRIVERS):
        r = d_first + i
        q = name.replace('"', '""')
        ws.cell(row=r, column=1, value=name).font = S.BODY
        ws.cell(row=r, column=2, value=f'=COUNTIF({cap_e},"{q}")').number_format = S.COUNT
        ws.cell(row=r, column=3,
                value=f'=SUMIFS({cap_c},{cap_e},"{q}")').number_format = S.FTE
        ws.cell(row=r, column=4,
                value=f'=SUMIFS({cap_l},{cap_e},"{q}")').number_format = S.FTE
        ws.cell(row=r, column=5,
                value=f'=SUMIFS({cap_m},{cap_e},"{q}")').number_format = S.FTE
        ws.cell(row=r, column=6, value=unit).font = S.SMALL
        for col in range(1, 6):
            ws.cell(row=r, column=col).border = S.BOX
    d_last = d_first + len(R.WORKLOAD_DRIVERS) - 1
    r = d_last + 1
    ws.cell(row=r, column=1, value="Total modelled gap (FTE)").font = S.H2
    ws.cell(row=r, column=5, value=f"=SUM($E${d_first}:$E${d_last})").number_format = S.FTE
    ws.cell(row=r, column=6,
            value="What the volumes you typed imply.").font = S.SMALL
    r += 1
    ws.cell(row=r, column=1, value="Total you have asked for (FTE)").font = S.H2
    ws.cell(row=r, column=5, value=f"=$B${ask_fte}").number_format = S.FTE
    ws.cell(row=r, column=6,
            value="A wide gap between these two is the first thing the centre "
                  "will ask you about.").font = S.SMALL
    for rr in (r - 1, r):
        ws.cell(row=rr, column=6).alignment = S.WRAP
        ws.cell(row=rr, column=5).font = S.f(10, True)
    ws.conditional_formatting.add(
        f"E{d_first}:E{d_last}",
        CellIsRule(operator="greaterThan", formula=["0"], font=S.f(10, True, S.AMBER)))

    _position_charts(ws, cat_first, cat_last, q_first, q_last, r + 2)
    S.print_setup(ws, landscape=False)
    return dict(ask_fte=ask_fte, ask_cost=ask_cost, cost_test=cost_test,
                head_test=head_test, saudi_test=saudi_test)


def _position_charts(ws, cat_first, cat_last, q_first, q_last, row) -> None:
    """Two native charts, so they move when the numbers do."""
    bar = BarChart()
    bar.type = "bar"
    bar.title = f"{R.PLAN_YEAR} cost by priority (SAR '000)"
    bar.y_axis.title = None
    bar.x_axis.title = None
    bar.legend = None
    bar.height, bar.width = 8, 16
    data = Reference(ws, min_col=3, min_row=cat_first, max_row=cat_last)
    cats = Reference(ws, min_col=1, min_row=cat_first, max_row=cat_last)
    bar.add_data(data, titles_from_data=False)
    bar.set_categories(cats)
    bar.series[0].graphicalProperties.solidFill = S.NAVY
    bar.series[0].graphicalProperties.line.noFill = True
    ws.add_chart(bar, f"A{row}")

    col = BarChart()
    col.type = "col"
    col.title = f"{R.PLAN_YEAR} cost by start quarter (SAR '000)"
    col.legend = None
    col.height, col.width = 8, 12
    data = Reference(ws, min_col=3, min_row=q_first, max_row=q_last)
    cats = Reference(ws, min_col=1, min_row=q_first, max_row=q_last)
    col.add_data(data, titles_from_data=False)
    col.set_categories(cats)
    col.series[0].graphicalProperties.solidFill = "3E7CB1"
    col.series[0].graphicalProperties.line.noFill = True
    ws.add_chart(col, f"E{row}")


# ── 7. Check & submit ───────────────────────────────────────────────────────
PROBLEM_ROWS = 25


def build_check(wb: Workbook, group: str, attr: dict, cap: tuple[int, int],
                chg: tuple[int, int], pos: dict) -> dict:
    """Everything still missing, named by row, and the one switch that says the
    file is ready to go back."""
    ws = wb.create_sheet(SH_CHK)
    cap_first, cap_last = cap
    chg_first, chg_last = chg
    row = S.sheet_title(
        ws, "Check & submit",
        "Work down this sheet until every blocking check reads OK, then set the "
        "state at the bottom to Submitted and return the file.")
    for col, w in zip("ABCD", [56, 12, 14, 62]):
        ws.column_dimensions[col].width = w

    lv_b = rng(SH_ATTR, "B", attr["leaver_first"], attr["leaver_last"])
    lv_g = rng(SH_ATTR, "G", attr["leaver_first"], attr["leaver_last"])
    vac_e = rng(SH_ATTR, "E", attr["vac_first"], attr["vac_last"])
    cp = {c: rng(SH_CAP, c, cap_first, cap_last) for c in "ACEFGI"}
    cg = {c: rng(SH_CHG, c, chg_first, chg_last) for c in "BCDGJ"}

    ws.cell(row=row, column=1, value="Blocking — these must be clear").font = S.H1
    row += 1
    mini_head(ws, row, ["Check", "Count", "Status", "What to do"])
    first = row + 1
    blocking = [
        ("Ask rows with something missing",
         f'=COUNTIF({ask_col("S")},"?*")',
         "Sheet 5 lists what each row is missing in the last two columns. Filter "
         "on 'What's missing' to find them."),
        ("Ask rows naming a unit that does not exist",
         f'=SUMPRODUCT(({ask_col("B")}<>"")*(COUNTIF(UnitList,{ask_col("B")})=0)'
         f'*(COUNTIF({cg["J"]},{ask_col("B")})=0))',
         "Either pick an existing unit, or add the new unit on sheet 4 and use "
         "its change ID."),
        (f"{R.BASE_YEAR} vacancies not yet confirmed",
         f"=COUNTBLANK({vac_e})",
         "Sheet 3. Anything you do not confirm lapses and will not carry into "
         f"{R.PLAN_YEAR}."),
        ("Named leavers with no backfill answer",
         f'=SUMPRODUCT(({lv_b}<>"")*({lv_g}=""))',
         "Sheet 3. Say whether each departure needs replacing."),
        ("Units with no workload driver",
         f'=SUMPRODUCT(({cp["A"]}<>"")*({cp["E"]}=""))',
         "Sheet 2. Every unit needs the one thing that drives its work."),
        ("Units with a driver but missing volumes",
         f'=SUMPRODUCT(({cp["E"]}<>"")*((({cp["F"]}="")+({cp["G"]}="")'
         f'+({cp["I"]}=""))>0))',
         f"Sheet 2 needs the {R.BASE_YEAR} volume, the {R.PLAN_YEAR} expected "
         "volume and the FTE doing that work."),
        ("Structure changes started but incomplete",
         f'=SUMPRODUCT(({cg["B"]}<>"")*((({cg["C"]}="")+({cg["D"]}="")'
         f'+({cg["G"]}=""))>0))',
         "Sheet 4. A change needs a unit name, a level and a reason."),
    ]
    r = first
    for label, formula, fix in blocking:
        ws.cell(row=r, column=1, value=label).font = S.BODY
        ws.cell(row=r, column=2, value=formula).number_format = S.COUNT
        ws.cell(row=r, column=3, value=f'=IF($B{r}=0,"OK","Fix")').font = S.f(10, True)
        ws.cell(row=r, column=3).alignment = S.CENTRE
        ws.cell(row=r, column=4, value=fix).font = S.SMALL
        ws.cell(row=r, column=4).alignment = S.WRAP
        ws.row_dimensions[r].height = 26
        for col in range(1, 5):
            ws.cell(row=r, column=col).border = S.BOX
        r += 1
    block_last = r - 1

    row = block_last + 2
    ws.cell(row=row, column=1, value="Worth a look — these do not block you").font = S.H1
    row += 1
    mini_head(ws, row, ["Check", "Count", "Status", "What to do"])
    warn_first = row + 1
    pos_ref = f"'{SH_POS}'!"
    warnings = [
        ("Cost above your envelope",
         f'=IF({pos_ref}$C${pos["cost_test"]}>{pos_ref}$B${pos["cost_test"]},1,0)',
         "Move start quarters later, or say on sheet 5 why the envelope has to move."),
        ("Net establishment change above your envelope",
         f'=IF({pos_ref}$C${pos["head_test"]}>{pos_ref}$B${pos["head_test"]},1,0)',
         "Convert, insource or close somewhere else to pay for it."),
        ("Saudization below your target",
         f'=IF({pos_ref}$C${pos["saudi_test"]}<{pos_ref}$B${pos["saudi_test"]},1,0)',
         "Change the intended basis on sheet 5, or explain the gap when you submit."),
    ]
    r = warn_first
    for label, formula, fix in warnings:
        ws.cell(row=r, column=1, value=label).font = S.BODY
        ws.cell(row=r, column=2, value=formula).number_format = S.COUNT
        ws.cell(row=r, column=3, value=f'=IF($B{r}=0,"OK","Review")').font = S.f(10, True)
        ws.cell(row=r, column=3).alignment = S.CENTRE
        ws.cell(row=r, column=4, value=fix).font = S.SMALL
        ws.cell(row=r, column=4).alignment = S.WRAP
        ws.row_dimensions[r].height = 26
        for col in range(1, 5):
            ws.cell(row=r, column=col).border = S.BOX
        r += 1
    warn_last = r - 1

    for rng_ref in (f"C{first}:C{block_last}", f"C{warn_first}:C{warn_last}"):
        ws.conditional_formatting.add(
            rng_ref, CellIsRule(operator="equal", formula=['"OK"'],
                                font=S.f(10, True, S.OK_GREEN)))
        ws.conditional_formatting.add(
            rng_ref, CellIsRule(operator="equal", formula=['"Fix"'],
                                font=S.f(10, True, S.RED_ALERT)))
        ws.conditional_formatting.add(
            rng_ref, CellIsRule(operator="equal", formula=['"Review"'],
                                font=S.f(10, True, S.AMBER)))

    # The rows themselves, named rather than counted.
    row = warn_last + 2
    ws.cell(row=row, column=1, value="The rows that need attention").font = S.H1
    ws.cell(row=row, column=4,
            value=f"The first {PROBLEM_ROWS}. Clear these and the rest appear.").font = S.NOTE
    row += 1
    mini_head(ws, row, ["Ask ref", "Unit", "Job title", "What is missing"])
    prob_first = row + 1
    for i in range(PROBLEM_ROWS):
        r = prob_first + i
        match = f'MATCH({i + 1},{ask_col("T")},0)'
        for col, src in [(1, "A"), (2, "B"), (3, "C"), (4, "S")]:
            pick = f"INDEX({ask_col(src)},{match})"
            ws.cell(row=r, column=col,
                    value=f'=IFERROR(IF({pick}=0,"",{pick}),"")').font = (
                S.f(9, color=S.RED_ALERT) if col == 4 else S.BODY)
            ws.cell(row=r, column=col).border = S.BOX
    prob_last = prob_first + PROBLEM_ROWS - 1

    # Submission.
    row = prob_last + 2
    ws.cell(row=row, column=1, value="Submission").font = S.H1
    row += 1
    ready_row = row
    S.label_value(ws, row, "Ready to submit",
                  f'=IF(SUM($B${first}:$B${block_last})=0,"Yes","No")', None,
                  S.f(12, True), note="Every blocking check has to read OK.")
    row += 1
    S.input_cell(S.label_value(ws, row, "Prepared by", None))
    row += 1
    S.input_cell(S.label_value(ws, row, "Contact", None))
    row += 1
    S.input_cell(S.label_value(ws, row, "Date", None))
    row += 1
    state_row = row
    c = S.input_cell(S.label_value(ws, row, "State", "Draft", None, None,
                                   note="Draft or Submitted."))
    ws.cell(row=row, column=1).font = S.f(12, True, S.NAVY)
    c.font = S.f(12, True, S.BLUE_INPUT)
    dv = DataValidation(
        type="custom", showErrorMessage=True,
        formula1=f'AND(OR($B${state_row}="Draft",$B${state_row}="Submitted"),'
                 f'OR($B${state_row}="Draft",$B${ready_row}="Yes"))')
    dv.errorTitle = "Not ready yet"
    dv.error = ("Only 'Draft' or 'Submitted' are accepted, and 'Submitted' only "
                "once every blocking check above reads OK.")
    ws.add_data_validation(dv)
    dv.add(f"B{state_row}")
    ws.conditional_formatting.add(
        f"B{ready_row}",
        CellIsRule(operator="equal", formula=['"Yes"'], font=S.f(12, True, S.OK_GREEN)))
    ws.conditional_formatting.add(
        f"B{ready_row}",
        CellIsRule(operator="equal", formula=['"No"'], font=S.f(12, True, S.RED_ALERT)))

    row += 2
    S.note_line(ws, row,
                f"Return the file to the capacity team with the state set to "
                f"Submitted. The centre will price it again on the same rate table, "
                f"challenge line by line where it has to, and send back the approved "
                f"{R.PLAN_YEAR} establishment for {group}.", cols=4)
    S.print_setup(ws, landscape=False)
    return dict(ready_row=ready_row, state_row=state_row,
                block_first=first, block_last=block_last)


# ── Assembly ────────────────────────────────────────────────────────────────
UNPROTECTED = {SH_TREE}   # outline collapse is blocked on a protected sheet


def build_template(group: str, path, bank: R.Bank | None = None) -> dict:
    """Write one group's template and hand back where everything landed, so the
    worked example and the tests can fill it in without guessing row numbers."""
    bank = bank or R.Bank()
    wb = Workbook()
    wb.remove(wb.active)

    build_readme(wb, group)
    build_tree(wb, bank, group)
    cap = build_capacity(wb, bank, group)
    attr = build_attrition(wb, bank, group)
    chg = build_changes(wb, bank, group)
    build_asks(wb, bank, group)
    pos = build_position(wb, bank, group, cap, chg)
    chk = build_check(wb, group, attr, cap, chg, pos)
    build_ref(wb, bank, group)

    for ws in wb.worksheets:
        if ws.title not in UNPROTECTED:
            S.protect(ws)
    wb.properties.title = f"{R.PLAN_YEAR} Capacity Exercise - {group}"
    wb.properties.creator = "Capacity exercise toolkit"
    wb.save(path)
    return dict(path=str(path), group=group, cap=cap, attr=attr, chg=chg,
                pos=pos, chk=chk,
                ask_first=ASK_FIRST, ask_last=ASK_LAST, ask_head=ASK_HEAD_ROW)


if __name__ == "__main__":
    import sys

    bank = R.Bank()
    group = sys.argv[1] if len(sys.argv) > 1 else bank.groups[0]
    out = sys.argv[2] if len(sys.argv) > 2 else "capacity/dist/2027-Capacity-Template.xlsx"
    print(build_template(group, out, bank)["path"])
