"""The consolidator: twelve returned templates in, one decision pack out.

The central team pastes each group's ask block into its own band, prices every
line again on the same rate table the groups were given, ranks the whole book by
the agreed order, challenges it line by line, and reads the result four ways at
once. Formulas only — nothing here needs a macro or a refresh.
"""
from __future__ import annotations

from pathlib import Path

from openpyxl import Workbook
from openpyxl.chart import BarChart, Reference, Series
from openpyxl.formatting.rule import CellIsRule, FormulaRule
from openpyxl.utils import get_column_letter
from openpyxl.workbook.defined_name import DefinedName
from openpyxl.worksheet.datavalidation import DataValidation

import refdata as R
import style as S
import tables as TB

DIST = Path(__file__).resolve().parents[1] / "dist"

INTAKE_ROWS = 300               # matches the template exactly, so a paste cannot overflow
HEAD_ROW = 5
FIRST_ROW = HEAD_ROW + 1
EST_ROWS = 800

SH_READ = "Read me"
SH_ENV = "1. Envelopes"
SH_SUB = "2. Group submissions"
SH_CHAL = "3. Challenge"
SH_SCEN = "4. Scenarios"
SH_DASH = "5. Dashboard"
SH_EXEC = "6. Executive summary"
SH_EST = "7. Approved establishment"
SH_PAGES = "8. Group pages"
SH_ENG = "Engine"
SH_REF = "Ref"

QSET = '{"Q1";"Q2";"Q3";"Q4"}'
DECISIONS = ["Approve as asked", "Approve fewer", "Defer to a later quarter", "Decline"]


def qidx(cell: str) -> str:
    return f"MATCH({cell},{QSET},0)"


def band_first(i: int) -> int:
    return FIRST_ROW + i * INTAKE_ROWS


def last_row(n_groups: int) -> int:
    return FIRST_ROW + n_groups * INTAKE_ROWS - 1


def col_rng(sheet: str, col: str, first: int, last: int) -> str:
    return f"'{sheet}'!${col}${first}:${col}${last}"


# ── Ref ─────────────────────────────────────────────────────────────────────
def build_ref(wb: Workbook, bank: R.Bank) -> None:
    ws = wb.create_sheet(SH_REF)
    ws.sheet_state = "hidden"
    row = S.sheet_title(ws, "Reference data",
                        "The same tables the groups were given. Do not edit mid-exercise.")
    row = TB.write_settings(wb, ws, SH_REF, row)
    row = TB.write_grades(wb, ws, SH_REF, row)
    row = TB.write_drivers(wb, ws, SH_REF, row)
    col = TB.write_lists(wb, ws, SH_REF, row,
                         extra=[("DecisionList", DECISIONS),
                                ("GroupList", bank.groups)])
    return col


# ── Read me ─────────────────────────────────────────────────────────────────
def build_readme(wb: Workbook, bank: R.Bank) -> None:
    ws = wb.create_sheet(SH_READ)
    row = S.sheet_title(ws, f"{R.PLAN_YEAR} Capacity Exercise — consolidator",
                        "For the central team. The order to work in, and what each "
                        "sheet is for.")
    ws.column_dimensions["A"].width = 28
    for c in "BCDEFGH":
        ws.column_dimensions[c].width = 14

    steps = [
        ("1. Envelopes",
         "Set the bank's ceilings and each group's share of them, and type in the four "
         "numbers you read off each returned template: attrition rate, vacancies lapsed, "
         "positions released by closures, and the group's submission state."),
        ("2. Group submissions",
         f"One band of {INTAKE_ROWS} rows per group. Open the group's file, copy A6:N305 "
         "from its Capacity asks sheet, and paste-special values into that group's band "
         "starting at column B. The band is exactly the size of the template, so a paste "
         "cannot spill into the next group. Everything from column P rightwards is "
         "recomputed here on the central rate table."),
        ("3. Challenge",
         "Every line, requested against approved. Set a decision on each line; only "
         "'Approve fewer' needs a number typed. Approved — not requested — is what rolls "
         "forward into every output."),
        ("4. Scenarios",
         "Four cases, six levers each, computed side by side over the whole book. The "
         "ranking rule funds regulatory first and 'other' last, so a tighter envelope "
         "shows you exactly which lines fall out."),
        ("5. Dashboard",
         f"The four analyses: the {R.BASE_YEAR}→{R.PLAN_YEAR} establishment bridge, the "
         "group league table against envelope, demand by driver asked against approved, "
         "and how the cost phases across the year."),
        ("6. Executive summary", "One page for the committee."),
        ("7. Approved establishment",
         "The approved lines as a flat list, ready for Finance and recruitment."),
        ("8. Group pages",
         "One printable page per group, for sending the answer back."),
    ]
    ws.cell(row=row, column=1, value="The order to work in").font = S.H1
    row += 1
    for name, why in steps:
        ws.cell(row=row, column=1, value=name).font = S.H2
        ws.cell(row=row, column=1).alignment = S.TOP
        c = ws.cell(row=row, column=2, value=why)
        c.font = S.BODY_DIM
        c.alignment = S.WRAP
        ws.merge_cells(start_row=row, start_column=2, end_row=row, end_column=8)
        ws.row_dimensions[row].height = 46
        row += 1
    row += 1
    row = S.legend(ws, row)
    ws.cell(row=row, column=1, value="Two things to hold on to").font = S.H1
    row += 1
    for text in [
        "Every line is priced here on the central grade table, not on whatever the group "
        "typed. If a group's number and yours differ, it is the rate table that has moved, "
        "and the grade cost table on the hidden Ref sheet is the only place to change it.",
        "The ranking rule is a starting point, not a decision. It funds regulatory work "
        "first and discretionary work last; the Challenge sheet is where a human overrides "
        "it, and the reason column is what you will be asked for afterwards.",
    ]:
        S.note_line(ws, row, text)
        row += 1
    S.print_setup(ws, landscape=False)


# ── 1. Envelopes ────────────────────────────────────────────────────────────
def build_envelopes(wb: Workbook, bank: R.Bank) -> dict:
    ws = wb.create_sheet(SH_ENV)
    row = S.sheet_title(
        ws, "Envelopes and receipts",
        "What the bank can afford, how it is split, and what has come back so far.")

    tot_cost = sum(bank.group_totals(g)["cost"] for g in bank.groups)
    tot_appr = sum(bank.group_totals(g)["approved"] for g in bank.groups)
    tot_saudi = sum(bank.group_totals(g)["saudi"] for g in bank.groups)
    tot_filled = sum(bank.group_totals(g)["filled"] for g in bank.groups)

    ws.cell(row=row, column=1, value="Bank ceiling").font = S.H1
    row += 1
    bank_rows = {}
    for name, label, value, fmt, why in [
        ("BankCostEnvelope", f"{R.PLAN_YEAR} cost envelope (SAR '000)",
         round(tot_cost * 0.06, 0), S.MONEY,
         "Illustrative: six per cent of the current pay bill."),
        ("BankHeadEnvelope", "Net establishment growth allowed",
         round(tot_appr * 0.05), S.COUNT,
         "Illustrative: five per cent of the current establishment."),
        ("BankSaudiTarget", "Saudization target",
         round(tot_saudi / tot_filled + 0.02, 2), S.PCT,
         "Illustrative: two points above where the bank stands today."),
    ]:
        S.input_cell(S.label_value(ws, row, label, value, fmt, note=why), fmt)
        wb.defined_names.add(DefinedName(name, attr_text=f"'{SH_ENV}'!$B${row}"))
        bank_rows[name] = row
        row += 1
    row += 1

    ws.cell(row=row, column=1, value="By group").font = S.H1
    ws.cell(row=row, column=11,
            value="Blue cells are yours: the allocation, and the four numbers you read "
                  "off each returned template.").font = S.NOTE
    row += 1
    heads = ["Group", f"{R.BASE_YEAR} approved", "Filled", "Vacant", "Saudi",
             f"{R.BASE_YEAR} cost", "Cost envelope", "Headcount envelope",
             "Saudization target", "Attrition rate", "Vacancies lapsed",
             "Released by closures", "State", "Paste into", "Rows received",
             "Rows with a problem", "Requested FTE", "Requested cost",
             "Approved FTE", "Approved cost", "Against envelope"]
    S.header_row(ws, row, heads,
                 [30, 12, 9, 9, 9, 13, 13, 13, 12, 11, 11, 12, 13, 14, 11, 12,
                  12, 13, 12, 13, 14])
    head = row
    first = row + 1
    n = len(bank.groups)
    sub_g = col_rng(SH_SUB, "A", FIRST_ROW, last_row(n))
    sub_t = col_rng(SH_SUB, "D", FIRST_ROW, last_row(n))
    sub_w = col_rng(SH_SUB, "W", FIRST_ROW, last_row(n))
    sub_fte = col_rng(SH_SUB, "I", FIRST_ROW, last_row(n))
    sub_cost = col_rng(SH_SUB, "T", FIRST_ROW, last_row(n))
    ch_g = col_rng(SH_CHAL, "A", FIRST_ROW, last_row(n))
    ch_fte = col_rng(SH_CHAL, "O", FIRST_ROW, last_row(n))
    ch_cost = col_rng(SH_CHAL, "Q", FIRST_ROW, last_row(n))
    for i, g in enumerate(bank.groups):
        r = first + i
        t = bank.group_totals(g)
        q = g.replace('"', '""')
        ws.cell(row=r, column=1, value=g).font = S.H2
        for col, value, fmt in [(2, t["approved"], S.COUNT), (3, t["filled"], S.COUNT),
                                (4, t["vacant"], S.COUNT), (5, t["saudi"], S.COUNT),
                                (6, round(t["cost"], 0), S.MONEY)]:
            ws.cell(row=r, column=col, value=value).number_format = fmt
        base_saudi = t["saudi"] / t["filled"] if t["filled"] else 0
        for col, value, fmt in [
                (7, round(t["cost"] * 0.06, 0), S.MONEY),
                (8, max(5, round(t["approved"] * 0.05)), S.COUNT),
                (9, round(base_saudi + 0.02, 2), S.PCT),
                (10, None, S.PCT), (11, None, S.COUNT), (12, None, S.COUNT),
                (13, "Draft", None)]:
            S.input_cell(ws.cell(row=r, column=col, value=value), fmt)
        bf = band_first(i)
        ws.cell(row=r, column=14,
                value=f"B{bf}:O{bf + INTAKE_ROWS - 1}").font = S.SMALL
        ws.cell(row=r, column=15,
                value=f'=COUNTIFS({sub_g},"{q}",{sub_t},"<>")').number_format = S.COUNT
        ws.cell(row=r, column=16,
                value=f'=COUNTIFS({sub_g},"{q}",{sub_w},"?*")').number_format = S.COUNT
        ws.cell(row=r, column=17,
                value=f'=SUMIFS({sub_fte},{sub_g},"{q}")').number_format = S.FTE
        ws.cell(row=r, column=18,
                value=f'=SUMIFS({sub_cost},{sub_g},"{q}")').number_format = S.MONEY
        ws.cell(row=r, column=19,
                value=f'=SUMIFS({ch_fte},{ch_g},"{q}")').number_format = S.FTE
        ws.cell(row=r, column=20,
                value=f'=SUMIFS({ch_cost},{ch_g},"{q}")').number_format = S.MONEY
        ws.cell(row=r, column=21,
                value=f'=IF($T{r}<=$G{r},"Within","Over by "&TEXT($T{r}-$G{r},"#,##0"))')
        for col in range(1, 22):
            ws.cell(row=r, column=col).border = S.BOX
    last = first + n - 1

    r = last + 1
    ws.cell(row=r, column=1, value="Bank total").font = S.f(10, True, S.NAVY)
    for col in [2, 3, 4, 5, 6, 7, 8, 11, 12, 15, 16, 17, 18, 19, 20]:
        letter = get_column_letter(col)
        ws.cell(row=r, column=col, value=f"=SUM({letter}{first}:{letter}{last})")
        ws.cell(row=r, column=col).number_format = (
            S.MONEY if col in (6, 7, 18, 20) else
            S.FTE if col in (17, 19) else S.COUNT)
        ws.cell(row=r, column=col).font = S.f(10, True)
    ws.cell(row=r, column=21,
            value=f'=IF($T{r}<=BankCostEnvelope,"Within the bank envelope",'
                  f'"Over the bank envelope by "&TEXT($T{r}-BankCostEnvelope,"#,##0"))')
    ws.cell(row=r, column=21).font = S.f(10, True)
    total_row = r
    S.band(ws, r, 21)

    r += 2
    ws.cell(row=r, column=1, value="Allocated against the ceiling").font = S.H2
    ws.cell(row=r, column=2,
            value=f'=IF(SUM($G${first}:$G${last})<=BankCostEnvelope,'
                  f'"Group cost envelopes fit inside the bank envelope",'
                  f'"Group cost envelopes exceed the bank envelope by "'
                  f'&TEXT(SUM($G${first}:$G${last})-BankCostEnvelope,"#,##0"))')
    alloc_row = r

    dv = DataValidation(type="list", formula1='"Draft,Submitted,Challenged,Approved"',
                        allow_blank=True, showErrorMessage=True)
    ws.add_data_validation(dv)
    dv.add(f"M{first}:M{last}")
    ws.conditional_formatting.add(
        f"U{first}:U{last}",
        FormulaRule(formula=[f'LEFT($U{first},4)="Over"'], font=S.f(10, True, S.RED_ALERT)))
    ws.conditional_formatting.add(
        f"P{first}:P{last}",
        CellIsRule(operator="greaterThan", formula=["0"], font=S.f(10, True, S.AMBER)))
    S.print_setup(ws, title_rows=f"{head}:{head}")
    return dict(head=head, first=first, last=last, total_row=total_row,
                alloc_row=alloc_row, bank_rows=bank_rows)


# ── 2. Group submissions ────────────────────────────────────────────────────
def build_submissions(wb: Workbook, bank: R.Bank) -> dict:
    ws = wb.create_sheet(SH_SUB)
    S.sheet_title(
        ws, "Group submissions",
        f"One band of {INTAKE_ROWS} rows per group. Copy A6:N305 from a group's "
        "Capacity asks sheet and paste values into column B of that group's band. "
        "Columns P onwards are recomputed centrally — leave them alone.")
    heads = ["Group", "Ref", "Unit", "Job title", "Grade", "Workforce type",
             "Saudi basis", "Nature", "FTE", "Start quarter", "Driver",
             "Category (as sent)", "Rank (as sent)", "Alternatives considered", "Note",
             "Category", "Rank", "Loaded cost (full year)", "One-off",
             f"{R.PLAN_YEAR} in-year cost", "Run-rate", "Sort key", "Problem"]
    widths = [26, 6, 26, 28, 8, 14, 12, 13, 7, 12, 26, 15, 10, 34, 26,
              14, 7, 15, 9, 15, 13, 12, 34]
    S.header_row(ws, HEAD_ROW, heads, widths)

    n = len(bank.groups)
    for i, g in enumerate(bank.groups):
        bf = band_first(i)
        for j in range(INTAKE_ROWS):
            r = bf + j
            gc = ws.cell(row=r, column=1, value=f'=IF($D{r}="","","{g}")')
            gc.font = S.SMALL
            if j == 0:
                gc.font = S.f(9, True, S.NAVY)
            for col in range(2, 16):        # the paste target
                S.input_cell(ws.cell(row=r, column=col))
            ws.cell(row=r, column=9).number_format = S.FTE

            idx = f"MATCH($E{r},GradeList,0)"
            ws.cell(row=r, column=16, value=(
                f'=IF($K{r}="","",IFERROR(INDEX(DriverCategory,MATCH($K{r},DriverList,0)),'
                f'"Other"))'))
            ws.cell(row=r, column=17, value=(
                f'=IF($K{r}="","",IFERROR(INDEX(DriverRank,MATCH($K{r},DriverList,0)),99))'))
            ws.cell(row=r, column=18, value=(
                f'=IF(ISNA({idx}),"",'
                f'INDEX(GradeBasic,{idx})+INDEX(GradeHousing,{idx})+INDEX(GradeTransport,{idx})'
                f'+INDEX(GradeBasic,{idx})*INDEX(GradeBonus,{idx})'
                f'+(INDEX(GradeBasic,{idx})+INDEX(GradeHousing,{idx}))'
                f'*IF($G{r}="Saudi",GosiSaudi,GosiOther))'))
            ws.cell(row=r, column=19, value=(
                f'=IF(ISNA({idx}),"",IF(INDEX(GradeRank,{idx})>='
                f'INDEX(GradeRank,MATCH("{R.SENIOR_FROM}",GradeList,0)),'
                f'OneOffSenior,OneOffJunior))'))
            ws.cell(row=r, column=20, value=(
                f'=IF(OR($R{r}="",$J{r}="",N($I{r})<=0),"",'
                f'$R{r}*$I{r}*(5-{qidx(f"$J{r}")})/4+$S{r}*$I{r})'))
            ws.cell(row=r, column=21, value=f'=IF($R{r}="","",$R{r}*$I{r})')
            ws.cell(row=r, column=22,
                    value=f'=IF($D{r}="","",$Q{r}*1000000+ROW())')
            problem = "&".join(
                f'IF({test},", {word}","")' for test, word in [
                    (f'$C{r}=""', "no unit"), (f'$E{r}=""', "no grade"),
                    (f'N($I{r})<=0', "no FTE"), (f'$J{r}=""', "no start quarter"),
                    (f'$K{r}=""', "no driver"),
                    (f'AND($E{r}<>"",COUNTIF(GradeList,$E{r})=0)', "grade not on the table"),
                    (f'AND($K{r}<>"",COUNTIF(DriverList,$K{r})=0)', "driver not on the list"),
                    (f'AND($F{r}<>"",COUNTIF(WorkforceTypes,$F{r})=0)',
                     "workforce type not on the list"),
                ])
            ws.cell(row=r, column=23,
                    value=f'=IF($D{r}="","",MID({problem},3,300))').font = S.f(9, color=S.RED_ALERT)
            for col in range(16, 23):
                ws.cell(row=r, column=col).font = (
                    S.f(9, color=S.RED_ALERT) if col == 23 else S.BODY)
            for col in (18, 19, 20, 21):
                ws.cell(row=r, column=col).number_format = S.MONEY
            ws.cell(row=r, column=22).number_format = S.COUNT
        S.band(ws, bf, 23)

    last = last_row(n)
    ws.conditional_formatting.add(
        f"A{FIRST_ROW}:W{last}",
        FormulaRule(formula=[f'$W{FIRST_ROW}<>""'],
                    fill=S.PatternFill("solid", fgColor="FDE7E9")))
    ws.auto_filter.ref = f"A{HEAD_ROW}:W{last}"
    S.print_setup(ws, title_rows=f"{HEAD_ROW}:{HEAD_ROW}")
    return dict(first=FIRST_ROW, last=last)


# ── 3. Challenge ────────────────────────────────────────────────────────────
def build_challenge(wb: Workbook, bank: R.Bank) -> dict:
    ws = wb.create_sheet(SH_CHAL)
    S.sheet_title(
        ws, "Challenge",
        "Requested against approved, line by line. Set a decision on every line; "
        "only 'Approve fewer' needs a number. Approved is what rolls forward.")
    heads = ["Group", "Ref", "Unit", "Job title", "Grade", "Category", "Rank",
             "Requested FTE", "Requested quarter", f"Requested {R.PLAN_YEAR} cost",
             "Decision", "Approved FTE", "Approved quarter", "Reason",
             "Effective FTE", "Effective quarter", f"Approved {R.PLAN_YEAR} cost",
             "Approved run-rate", "Cost variance", "Approved line"]
    widths = [26, 6, 26, 28, 8, 14, 7, 12, 12, 15, 20, 12, 12, 40,
              11, 12, 15, 14, 13, 12]
    S.header_row(ws, HEAD_ROW, heads, widths)

    n = len(bank.groups)
    first, last = FIRST_ROW, last_row(n)
    for r in range(first, last + 1):
        sub = f"'{SH_SUB}'!"
        ws.cell(row=r, column=1, value=f'=IF({sub}$D{r}="","",{sub}$A{r})').font = S.LINK
        for col, src in [(2, "B"), (3, "C"), (4, "D"), (5, "E"), (6, "P"), (7, "Q"),
                         (8, "I"), (9, "J"), (10, "T")]:
            ws.cell(row=r, column=col,
                    value=f'=IF({sub}$D{r}="","",{sub}${src}{r})').font = S.LINK
        ws.cell(row=r, column=8).number_format = S.FTE
        ws.cell(row=r, column=10).number_format = S.MONEY
        for col in range(11, 15):
            S.input_cell(ws.cell(row=r, column=col))
        ws.cell(row=r, column=12).number_format = S.FTE

        # What the decision actually means, in numbers.
        ws.cell(row=r, column=15, value=(
            f'=IF($D{r}="","",'
            f'IF($K{r}="Decline",0,'
            f'IF($K{r}="Approve fewer",IF($L{r}="","",$L{r}),'
            f'IF($K{r}="","",$H{r}))))')).number_format = S.FTE
        ws.cell(row=r, column=16, value=(
            f'=IF($O{r}="","",IF($M{r}<>"",$M{r},$I{r}))'))
        ws.cell(row=r, column=17, value=(
            f'=IF(OR($O{r}="",{sub}$R{r}=""),"",'
            f'{sub}$R{r}*$O{r}*(5-{qidx(f"$P{r}")})/4+{sub}$S{r}*$O{r})'
        )).number_format = S.MONEY
        ws.cell(row=r, column=18, value=(
            f'=IF(OR($O{r}="",{sub}$R{r}=""),"",{sub}$R{r}*$O{r})')).number_format = S.MONEY
        ws.cell(row=r, column=19, value=(
            f'=IF($O{r}="","",$Q{r}-$J{r})')).number_format = S.MONEY
        ws.cell(row=r, column=20, value=(
            f'=IF(N($O{r})<=0,"",COUNTIF($O${first}:$O{r},">0"))')).number_format = S.COUNT
        for col in (15, 16, 17, 18, 19, 20):
            ws.cell(row=r, column=col).font = S.BODY

    dv = DataValidation(type="list", formula1="=DecisionList", allow_blank=True,
                        showErrorMessage=True)
    dv.error = "Pick a decision from the list."
    ws.add_data_validation(dv)
    dv.add(f"K{first}:K{last}")
    dvq = DataValidation(type="list", formula1="=QuarterList", allow_blank=True,
                         showErrorMessage=True)
    ws.add_data_validation(dvq)
    dvq.add(f"M{first}:M{last}")

    ws.conditional_formatting.add(
        f"K{first}:K{last}",
        CellIsRule(operator="equal", formula=['"Decline"'], font=S.f(10, True, S.RED_ALERT)))
    ws.conditional_formatting.add(
        f"S{first}:S{last}",
        CellIsRule(operator="lessThan", formula=["0"], font=S.f(10, color=S.OK_GREEN)))
    ws.auto_filter.ref = f"A{HEAD_ROW}:T{last}"
    S.print_setup(ws, title_rows=f"{HEAD_ROW}:{HEAD_ROW}")
    return dict(first=first, last=last)


# ── 4. Scenarios, and the engine behind them ────────────────────────────────
LEVERS = [
    ("Demand multiplier", "Scales every requested FTE. 1.10 asks what a tenth "
     "more demand would cost.", S.PCT),
    ("Share of envelope released", "How much of the bank envelope this case "
     "funds. The ranked cut falls where this runs out.", S.PCT),
    ("Timing shift (quarters)", "Pushes every start back by this many quarters. "
     "The cheapest concession there is.", None),
    ("Attrition rate", "Used for expected departures, not for the cut.", S.PCT),
    ("Salary inflation", "Applied to the grade table for this case.", S.PCT),
    ("Productivity multiplier", "1.0 takes the groups' own productivity "
     "assumption as given. 1.5 assumes half as much again lands, which shrinks "
     "the ask; 0.5 assumes half of it does not.", None),
]
SCEN_FIRST_COL = 2                      # B..E, one column per scenario
ENG_BLOCK = 6                           # FTE, quarter, cost, run-rate, cumulative, funded


def eng_col(scenario: int, offset: int) -> str:
    return get_column_letter(4 + scenario * ENG_BLOCK + offset)


def build_scenarios(wb: Workbook, bank: R.Bank) -> dict:
    ws = wb.create_sheet(SH_SCEN)
    row = S.sheet_title(
        ws, "Scenarios",
        "Four cases over the same book of asks, computed side by side. Change a "
        "lever and every number below moves with it.")
    ws.column_dimensions["A"].width = 38
    for c in "BCDE":
        ws.column_dimensions[c].width = 16
    ws.column_dimensions["F"].width = 56

    ws.cell(row=row, column=1, value="The levers").font = S.H1
    row += 1
    names = [s[0] for s in R.SCENARIOS]
    S.header_row(ws, row, ["Lever"] + names + ["What it does"],
                 [38, 16, 16, 16, 16, 56])
    ws.freeze_panes = None
    lever_first = row + 1
    for i, (label, why, fmt) in enumerate(LEVERS):
        r = lever_first + i
        ws.cell(row=r, column=1, value=label).font = S.H2
        for k, sc in enumerate(R.SCENARIOS):
            value = [sc[1], sc[2], sc[3], sc[4], sc[5], sc[6]][i]
            S.input_cell(ws.cell(row=r, column=2 + k, value=value), fmt)
        ws.cell(row=r, column=6, value=why).font = S.SMALL
        ws.cell(row=r, column=6).alignment = S.WRAP
        ws.row_dimensions[r].height = 26
    lever_rows = {name: lever_first + i for i, (name, _, _) in enumerate(LEVERS)}
    row = lever_first + len(LEVERS) + 1

    n = len(bank.groups)
    first, last = FIRST_ROW, last_row(n)
    env_filled = f"'{SH_ENV}'!$C$"
    metrics_first = row + 1
    ws.cell(row=row, column=1, value="What each case funds").font = S.H1
    row += 1
    S.header_row(ws, row, ["Measure"] + names + ["Read it this way"],
                 [38, 16, 16, 16, 16, 56])
    ws.freeze_panes = None
    metrics_first = row + 1
    return dict(ws=ws, lever_first=lever_first, lever_rows=lever_rows,
                metrics_first=metrics_first, names=names, first=first, last=last)


def finish_scenarios(wb: Workbook, bank: R.Bank, sc: dict, env: dict) -> dict:
    """Written after the engine exists, because every measure reads from it."""
    ws = sc["ws"]
    first, last = sc["first"], sc["last"]
    names = sc["names"]
    row = sc["metrics_first"]
    eng = f"'{SH_ENG}'!"
    sub = f"'{SH_SUB}'!"
    filled = f"'{SH_ENV}'!$C${env['total_row']}"
    saudi = f"'{SH_ENV}'!$E${env['total_row']}"
    lr = sc["lever_rows"]

    def col(k, off):
        return f"{eng}${eng_col(k, off)}${first}:${eng_col(k, off)}${last}"

    measures = []
    for k in range(len(names)):
        fte, cost, runrate, funded = col(k, 0), col(k, 2), col(k, 3), col(k, 5)
        L = get_column_letter(2 + k)
        measures.append({
            "FTE requested (after the demand lever)": (f"=SUM({fte})", S.FTE),
            "Lines funded": (f'=COUNTIFS({funded},1)', S.COUNT),
            "FTE funded": (f"=SUMIFS({fte},{funded},1)", S.FTE),
            f"{R.PLAN_YEAR} cost funded (SAR '000)": (f"=SUMIFS({cost},{funded},1)", S.MONEY),
            f"Run-rate into {R.PLAN_YEAR + 1} (SAR '000)":
                (f"=SUMIFS({runrate},{funded},1)", S.MONEY),
            "Envelope released (SAR '000)": (f"=BankCostEnvelope*${L}${lr['Share of envelope released']}",
                                             S.MONEY),
            "FTE not funded": (f"=SUM({fte})-SUMIFS({fte},{funded},1)", S.FTE),
            "Regulatory FTE funded":
                (f'=SUMIFS({fte},{funded},1,{eng}$C${first}:$C${last},"Regulatory")', S.FTE),
            "Projected Saudization":
                (f'=({saudi}+SUMIFS({fte},{funded},1,{sub}$G${first}:$G${last},"Saudi"))'
                 f"/({filled}+SUMIFS({fte},{funded},1))", S.PCT),
            "Against the headcount envelope":
                (f'=IF(SUMIFS({fte},{funded},1)<=BankHeadEnvelope,"Within","Over by "'
                 f'&TEXT(SUMIFS({fte},{funded},1)-BankHeadEnvelope,"#,##0.0"))', None),
            "Expected departures at this rate":
                (f"=ROUND({filled}*${L}${lr['Attrition rate']},0)", S.COUNT),
        })
    notes = {
        "FTE requested (after the demand lever)":
            "What the groups asked for, moved by this case's demand assumption.",
        "Lines funded": "How many of the requested positions survive the ranked cut.",
        "FTE funded": "The number that matters: what the bank would actually hire.",
        f"{R.PLAN_YEAR} cost funded (SAR '000)":
            "Part-year cost in the plan year, at this case's start quarters.",
        f"Run-rate into {R.PLAN_YEAR + 1} (SAR '000)":
            "The full-year cost the bank carries out of the plan year.",
        "Envelope released (SAR '000)": "The ceiling this case is cut against.",
        "FTE not funded": "What falls out. Read it with the priority table below.",
        "Regulatory FTE funded":
            "Regulatory work ranks first, so this should hold in every case.",
        "Projected Saudization": "Today's people plus everything this case funds.",
        "Against the headcount envelope": "Tested on funded FTE, not on the ask.",
        "Expected departures at this rate":
            "Not part of the cut — the replacement asks are already lines in the book.",
    }
    for label in measures[0]:
        ws.cell(row=row, column=1, value=label).font = S.H2
        for k in range(len(names)):
            formula, fmt = measures[k][label]
            c = ws.cell(row=row, column=2 + k, value=formula)
            if fmt:
                c.number_format = fmt
            c.font = S.BODY
        ws.cell(row=row, column=6, value=notes[label]).font = S.SMALL
        ws.cell(row=row, column=6).alignment = S.WRAP
        for c in range(1, 7):
            ws.cell(row=row, column=c).border = S.BOX
        row += 1
    metrics_last = row - 1
    cost_row = sc["metrics_first"] + 3
    row += 1

    S.note_line(
        ws, row,
        "The cut is made against in-year cost, so a case that pushes starts back "
        "a quarter can fund more lines than the base case for less money in "
        f"{R.PLAN_YEAR} — while committing almost the same run-rate into "
        f"{R.PLAN_YEAR + 1}. Read the cost row and the run-rate row together; "
        "deferring buys cash this year, not capacity next year.", cols=6)
    row += 2

    ws.cell(row=row, column=1, value="Funded FTE by priority").font = S.H1
    row += 1
    S.header_row(ws, row, ["Priority"] + names + [""], [38, 16, 16, 16, 16, 56])
    ws.freeze_panes = None
    cat_first = row + 1
    for i, (name, rank, why) in enumerate(R.RANK_CATEGORIES):
        r = cat_first + i
        ws.cell(row=r, column=1, value=f"{rank}. {name}").font = S.BODY
        for k in range(len(names)):
            ws.cell(row=r, column=2 + k, value=(
                f'=SUMIFS({col(k, 0)},{col(k, 5)},1,'
                f'{eng}$C${first}:$C${last},"{name}")')).number_format = S.FTE
        ws.cell(row=r, column=6, value=why).font = S.SMALL
        ws.cell(row=r, column=6).alignment = S.WRAP
        for c in range(1, 7):
            ws.cell(row=r, column=c).border = S.BOX
    cat_last = cat_first + len(R.RANK_CATEGORIES) - 1
    row = cat_last + 2

    ws.cell(row=row, column=1, value="Funded cost by group (SAR '000)").font = S.H1
    row += 1
    S.header_row(ws, row, ["Group"] + names + [""], [38, 16, 16, 16, 16, 56])
    ws.freeze_panes = None
    grp_first = row + 1
    for i, g in enumerate(bank.groups):
        r = grp_first + i
        q = g.replace('"', '""')
        ws.cell(row=r, column=1, value=g).font = S.BODY
        for k in range(len(names)):
            ws.cell(row=r, column=2 + k, value=(
                f'=SUMIFS({col(k, 2)},{col(k, 5)},1,'
                f'{eng}$B${first}:$B${last},"{q}")')).number_format = S.MONEY
        for c in range(1, 6):
            ws.cell(row=r, column=c).border = S.BOX
    grp_last = grp_first + len(bank.groups) - 1

    chart = BarChart()
    chart.type = "col"
    chart.title = f"{R.PLAN_YEAR} cost funded by case (SAR '000)"
    chart.legend = None
    chart.height, chart.width = 8, 16
    data = Reference(ws, min_col=2, max_col=5, min_row=cost_row, max_row=cost_row)
    cats = Reference(ws, min_col=2, max_col=5, min_row=sc["metrics_first"] - 1,
                     max_row=sc["metrics_first"] - 1)
    chart.add_data(data, from_rows=True, titles_from_data=False)
    chart.set_categories(cats)
    chart.series[0].graphicalProperties.solidFill = S.NAVY
    ws.add_chart(chart, f"H{sc['lever_first']}")

    stack = BarChart()
    stack.type = "col"
    stack.grouping = "clustered"
    stack.title = "Funded FTE by priority"
    stack.height, stack.width = 8, 16
    data = Reference(ws, min_col=1, max_col=5, min_row=cat_first - 1, max_row=cat_last)
    stack.add_data(data, from_rows=False, titles_from_data=True)
    stack.set_categories(Reference(ws, min_col=1, min_row=cat_first, max_row=cat_last))
    ws.add_chart(stack, f"H{cat_first - 2}")

    S.print_setup(ws)
    return dict(names=names, metrics_first=sc["metrics_first"], metrics_last=metrics_last,
                cost_row=cost_row, fte_row=sc["metrics_first"] + 2,
                cat_first=cat_first, cat_last=cat_last,
                grp_first=grp_first, grp_last=grp_last,
                lever_rows=sc["lever_rows"])


def build_engine(wb: Workbook, bank: R.Bank, sc: dict) -> dict:
    """One row per submitted line, computed under all four cases in parallel.
    Nothing to read here; it is the arithmetic the Scenarios sheet summarises."""
    ws = wb.create_sheet(SH_ENG)
    S.sheet_title(ws, "Engine",
                  "Working sheet. Every submitted line under all four cases. "
                  "Nothing here is typed in, and nothing here needs reading.")
    n = len(bank.groups)
    first, last = FIRST_ROW, last_row(n)
    sub = f"'{SH_SUB}'!"
    scn = f"'{SH_SCEN}'!"
    lr = sc["lever_rows"]

    heads = ["Sort key", "Group", "Priority"]
    for name in sc["names"]:
        heads += [f"{name} FTE", f"{name} quarter", f"{name} cost",
                  f"{name} run-rate", f"{name} cumulative", f"{name} funded"]
    S.header_row(ws, HEAD_ROW, heads, [12, 26, 14] + [12] * (ENG_BLOCK * len(sc["names"])))

    for r in range(first, last + 1):
        ws.cell(row=r, column=1, value=f'=IF({sub}$D{r}="","",{sub}$V{r})')
        ws.cell(row=r, column=2, value=f'=IF({sub}$D{r}="","",{sub}$A{r})')
        ws.cell(row=r, column=3, value=f'=IF({sub}$D{r}="","",{sub}$P{r})')
        for k in range(len(sc["names"])):
            L = get_column_letter(2 + k)
            c = [eng_col(k, i) for i in range(ENG_BLOCK)]
            base = f"{scn}${L}$"
            ws.cell(row=r, column=4 + k * ENG_BLOCK, value=(
                f'=IF(OR({sub}$D{r}="",N({sub}$I{r})<=0),"",'
                f"{sub}$I{r}*{base}{lr['Demand multiplier']}"
                f"/(1+ProductivityDefault*({base}{lr['Productivity multiplier']}-1)))"
            )).number_format = S.FTE
            ws.cell(row=r, column=5 + k * ENG_BLOCK, value=(
                f'=IF(OR(${c[0]}{r}="",{sub}$J{r}=""),"",'
                f"MIN(4,{qidx(f'{sub}$J{r}')}+{base}{lr['Timing shift (quarters)']}))"))
            ws.cell(row=r, column=6 + k * ENG_BLOCK, value=(
                f'=IF(OR(${c[1]}{r}="",{sub}$R{r}=""),"",'
                f"{sub}$R{r}*(1+{base}{lr['Salary inflation']})*${c[0]}{r}"
                f"*(5-${c[1]}{r})/4+{sub}$S{r}*${c[0]}{r})")).number_format = S.MONEY
            ws.cell(row=r, column=7 + k * ENG_BLOCK, value=(
                f'=IF(${c[2]}{r}="","",'
                f"{sub}$R{r}*(1+{base}{lr['Salary inflation']})*${c[0]}{r})"
            )).number_format = S.MONEY
            ws.cell(row=r, column=8 + k * ENG_BLOCK, value=(
                f'=IF(${c[2]}{r}="","",SUMIFS(${c[2]}${first}:${c[2]}${last},'
                f'$A${first}:$A${last},"<="&$A{r}))')).number_format = S.MONEY
            ws.cell(row=r, column=9 + k * ENG_BLOCK, value=(
                f'=IF(${c[2]}{r}="","",IF(${c[4]}{r}<=BankCostEnvelope*'
                f"{base}{lr['Share of envelope released']},1,0))")).number_format = S.COUNT
    ws.sheet_properties.tabColor = S.GREY_BG
    S.print_setup(ws)
    return dict(first=first, last=last)


# ── 5. Dashboard ────────────────────────────────────────────────────────────
def build_dashboard(wb: Workbook, bank: R.Bank, env: dict, scen: dict) -> dict:
    ws = wb.create_sheet(SH_DASH)
    row = S.sheet_title(
        ws, "Dashboard",
        f"The {R.BASE_YEAR} to {R.PLAN_YEAR} bridge, the groups against their "
        "envelopes, demand by driver, and how the cost phases across the year.")
    for col, w in zip("ABCDEFGH", [40, 15, 15, 15, 15, 15, 15, 15]):
        ws.column_dimensions[col].width = w

    charts = {"row": 5}                 # every chart stacks down one clear column

    def place(chart, height_cm: float, width_cm: float = 18) -> None:
        chart.height, chart.width = height_cm, width_cm
        ws.add_chart(chart, f"J{charts['row']}")
        charts["row"] += int(height_cm * 1.9) + 3

    n = len(bank.groups)
    first, last = FIRST_ROW, last_row(n)
    sub = f"'{SH_SUB}'!"
    chal = f"'{SH_CHAL}'!"
    ch_fte = col_rng(SH_CHAL, "O", first, last)
    ch_q = col_rng(SH_CHAL, "P", first, last)
    ch_cost = col_rng(SH_CHAL, "Q", first, last)
    sub_nat = col_rng(SH_SUB, "H", first, last)
    sub_drv = col_rng(SH_SUB, "K", first, last)
    sub_fte = col_rng(SH_SUB, "I", first, last)
    sub_cat = col_rng(SH_SUB, "P", first, last)
    ch_grp = col_rng(SH_CHAL, "A", first, last)
    et = env["total_row"]
    envt = f"'{SH_ENV}'!"

    # ── The bridge ─────────────────────────────────────────────────────────
    ws.cell(row=row, column=1,
            value=f"{R.BASE_YEAR} to {R.PLAN_YEAR} establishment bridge").font = S.H1
    ws.cell(row=row, column=6,
            value="Approved seats, not people. Replacements and conversions keep "
                  "a seat that already exists, so they do not move the bridge.").font = S.NOTE
    row += 1
    S.header_row(ws, row, ["Step", "Change", "Running total", "Base", "Bar"],
                 [40, 15, 15, 15, 15])
    ws.freeze_panes = None
    b_first = row + 1
    steps = [
        (f"Opening {R.BASE_YEAR} approved establishment", f"={envt}$B${et}"),
        (f"less {R.BASE_YEAR} vacancies lapsed", f"=-{envt}$K${et}"),
        ("less positions released by closures and merges", f"=-{envt}$L${et}"),
        ("plus approved growth positions",
         f'=SUMIFS({ch_fte},{sub_nat},"Growth")'),
        (f"Closing {R.PLAN_YEAR} approved establishment", None),
    ]
    for i, (label, formula) in enumerate(steps):
        r = b_first + i
        ws.cell(row=r, column=1, value=label).font = S.H2 if i in (0, 4) else S.BODY
        if formula:
            ws.cell(row=r, column=2, value=formula).number_format = S.FTE
        if i == 0:
            ws.cell(row=r, column=3, value=f"=$B{r}")
            ws.cell(row=r, column=4, value=0)
            ws.cell(row=r, column=5, value=f"=$B{r}")
        elif i < 4:
            ws.cell(row=r, column=3, value=f"=$C{r - 1}+$B{r}")
            ws.cell(row=r, column=4, value=f"=MIN($C{r - 1},$C{r})")
            ws.cell(row=r, column=5, value=f"=ABS($B{r})")
        else:
            ws.cell(row=r, column=2, value=f"=$C{r - 1}")
            ws.cell(row=r, column=3, value=f"=$C{r - 1}")
            ws.cell(row=r, column=4, value=0)
            ws.cell(row=r, column=5, value=f"=$C{r - 1}")
        for col in range(2, 6):
            ws.cell(row=r, column=col).number_format = S.FTE
            ws.cell(row=r, column=col).border = S.BOX
        ws.cell(row=r, column=1).border = S.BOX
    b_last = b_first + len(steps) - 1
    S.band(ws, b_first, 5)
    S.band(ws, b_last, 5)
    row = b_last + 1
    for label, formula in [
        ("of which replacements approved (no net change)",
         f'=SUMIFS({ch_fte},{sub_nat},"Replacement")'),
        ("of which conversions approved (no net change)",
         f'=SUMIFS({ch_fte},{sub_nat},"Conversion")'),
        ("Net establishment change against the bank envelope",
         f'=IF($C${b_last}-$B${b_first}<=BankHeadEnvelope,'
         f'"Within the envelope","Over the envelope by "'
         f'&TEXT($C${b_last}-$B${b_first}-BankHeadEnvelope,"#,##0.0"))'),
    ]:
        ws.cell(row=row, column=1, value=label).font = S.BODY_DIM
        c = ws.cell(row=row, column=2, value=formula)
        c.number_format = S.FTE
        c.font = S.BODY
        row += 1
    row += 1

    wf = BarChart()
    wf.type = "col"
    wf.grouping = "stacked"
    wf.overlap = 100
    wf.title = f"{R.BASE_YEAR} to {R.PLAN_YEAR} establishment"
    wf.legend = None
    base = Reference(ws, min_col=4, min_row=b_first, max_row=b_last)
    bar = Reference(ws, min_col=5, min_row=b_first, max_row=b_last)
    wf.add_data(base, titles_from_data=False)
    wf.add_data(bar, titles_from_data=False)
    wf.set_categories(Reference(ws, min_col=1, min_row=b_first, max_row=b_last))
    wf.series[0].graphicalProperties.noFill = True
    wf.series[1].graphicalProperties.solidFill = S.NAVY
    place(wf, 8)

    # ── League table ───────────────────────────────────────────────────────
    ws.cell(row=row, column=1, value="Groups against their envelopes").font = S.H1
    row += 1
    S.header_row(ws, row, ["Group", "Requested FTE", "Approved FTE",
                           "Approved cost", "Cost envelope", "Share of envelope",
                           "Status"],
                 [40, 15, 15, 15, 15, 15, 22])
    ws.freeze_panes = None
    lg_first = row + 1
    for i, g in enumerate(bank.groups):
        r = lg_first + i
        er = env["first"] + i
        ws.cell(row=r, column=1, value=f"={envt}$A${er}").font = S.BODY
        ws.cell(row=r, column=2, value=f"={envt}$Q${er}").number_format = S.FTE
        ws.cell(row=r, column=3, value=f"={envt}$S${er}").number_format = S.FTE
        ws.cell(row=r, column=4, value=f"={envt}$T${er}").number_format = S.MONEY
        ws.cell(row=r, column=5, value=f"={envt}$G${er}").number_format = S.MONEY
        ws.cell(row=r, column=6, value=f"=IFERROR($D{r}/$E{r},0)").number_format = S.PCT
        ws.cell(row=r, column=7, value=f"={envt}$U${er}")
        for col in range(1, 8):
            ws.cell(row=r, column=col).border = S.BOX
    lg_last = lg_first + len(bank.groups) - 1
    ws.conditional_formatting.add(
        f"F{lg_first}:F{lg_last}",
        CellIsRule(operator="greaterThan", formula=["1"], font=S.f(10, True, S.RED_ALERT)))
    row = lg_last + 2

    league = BarChart()
    league.type = "bar"
    league.title = f"Approved {R.PLAN_YEAR} cost against envelope (SAR '000)"
    data = Reference(ws, min_col=4, max_col=5, min_row=lg_first - 1, max_row=lg_last)
    league.add_data(data, titles_from_data=True)
    league.set_categories(Reference(ws, min_col=1, min_row=lg_first, max_row=lg_last))
    league.series[0].graphicalProperties.solidFill = S.NAVY
    league.series[1].graphicalProperties.solidFill = "C7D3E3"
    league.x_axis.scaling.orientation = "maxMin"
    league.y_axis.crosses = "max"
    place(league, 10)

    # ── Demand by driver ───────────────────────────────────────────────────
    ws.cell(row=row, column=1, value="Demand by driver — asked against approved").font = S.H1
    row += 1
    S.header_row(ws, row, ["Driver", "Priority", "Requested FTE", "Approved FTE",
                           "Not funded"], [40, 15, 15, 15, 15])
    ws.freeze_panes = None
    d_first = row + 1
    for i, (name, cat) in enumerate(R.ASK_DRIVERS):
        r = d_first + i
        q = name.replace('"', '""')
        ws.cell(row=r, column=1, value=name).font = S.BODY
        ws.cell(row=r, column=2, value=cat).font = S.SMALL
        ws.cell(row=r, column=3,
                value=f'=SUMIFS({sub_fte},{sub_drv},"{q}")').number_format = S.FTE
        ws.cell(row=r, column=4,
                value=f'=SUMIFS({ch_fte},{sub_drv},"{q}")').number_format = S.FTE
        ws.cell(row=r, column=5, value=f"=$C{r}-$D{r}").number_format = S.FTE
        for col in range(1, 6):
            ws.cell(row=r, column=col).border = S.BOX
    d_last = d_first + len(R.ASK_DRIVERS) - 1
    row = d_last + 2

    drv = BarChart()
    drv.type = "bar"
    drv.title = "Requested against approved, by driver (FTE)"
    data = Reference(ws, min_col=3, max_col=4, min_row=d_first - 1, max_row=d_last)
    drv.add_data(data, titles_from_data=True)
    drv.set_categories(Reference(ws, min_col=1, min_row=d_first, max_row=d_last))
    drv.series[0].graphicalProperties.solidFill = "C7D3E3"
    drv.series[1].graphicalProperties.solidFill = S.NAVY
    drv.x_axis.scaling.orientation = "maxMin"
    drv.y_axis.crosses = "max"
    place(drv, 14)

    # ── Cost phasing ───────────────────────────────────────────────────────
    ws.cell(row=row, column=1,
            value=f"How the approved {R.PLAN_YEAR} cost phases").font = S.H1
    row += 1
    cats = [c for c, _, _ in R.RANK_CATEGORIES]
    S.header_row(ws, row, ["Start quarter"] + cats + ["Total"],
                 [40] + [13] * len(cats) + [15])
    ws.freeze_panes = None
    p_first = row + 1
    for i, q in enumerate(R.QUARTERS):
        r = p_first + i
        ws.cell(row=r, column=1, value=q).font = S.BODY
        for j, cat in enumerate(cats):
            ws.cell(row=r, column=2 + j, value=(
                f'=SUMIFS({ch_cost},{ch_q},"{q}",{sub_cat},"{cat}")'
            )).number_format = S.MONEY
        letter = get_column_letter(1 + len(cats))
        ws.cell(row=r, column=2 + len(cats),
                value=f"=SUM($B{r}:${letter}{r})").number_format = S.MONEY
        for col in range(1, 3 + len(cats)):
            ws.cell(row=r, column=col).border = S.BOX
    p_last = p_first + len(R.QUARTERS) - 1

    phase = BarChart()
    phase.type = "col"
    phase.grouping = "stacked"
    phase.overlap = 100
    phase.title = f"Approved {R.PLAN_YEAR} cost by start quarter (SAR '000)"
    data = Reference(ws, min_col=2, max_col=1 + len(cats), min_row=p_first - 1,
                     max_row=p_last)
    phase.add_data(data, titles_from_data=True)
    phase.set_categories(Reference(ws, min_col=1, min_row=p_first, max_row=p_last))
    for series, colour in zip(phase.series,
                              ["24466B", "3E7CB1", "6FA8C7", "9BC1D4", "C7D3E3", "E4E9EF"]):
        series.graphicalProperties.solidFill = colour
    place(phase, 9)

    S.print_setup(ws)
    return dict(bridge_first=b_first, bridge_last=b_last, league_first=lg_first,
                league_last=lg_last, driver_first=d_first, driver_last=d_last,
                phase_first=p_first, phase_last=p_last)


# ── 6. Executive summary ────────────────────────────────────────────────────
def build_exec(wb: Workbook, bank: R.Bank, env: dict, scen: dict, dash: dict) -> None:
    ws = wb.create_sheet(SH_EXEC)
    row = S.sheet_title(
        ws, f"{R.PLAN_YEAR} capacity — executive summary",
        "One page. Every number on it comes from the approved column, not the ask.")
    ws.column_dimensions["A"].width = 52
    for c in "BCDE":
        ws.column_dimensions[c].width = 17
    ws.column_dimensions["F"].width = 50

    envt = f"'{SH_ENV}'!"
    et = env["total_row"]
    ws.cell(row=row, column=1, value="The decision in six numbers").font = S.H1
    row += 1
    lines = [
        ("Positions requested by the groups (FTE)", f"={envt}$Q${et}", S.FTE,
         "Twelve submissions, priced centrally on one rate table."),
        ("Positions approved (FTE)", f"={envt}$S${et}", S.FTE,
         "What the challenge process left standing."),
        (f"{R.PLAN_YEAR} cost approved (SAR '000)", f"={envt}$T${et}", S.MONEY,
         "Part-year, at the approved start quarters."),
        ("Against the bank cost envelope", f"=BankCostEnvelope-{envt}$T${et}", S.MONEY,
         "Positive is headroom; negative is the gap to close."),
        (f"Closing {R.PLAN_YEAR} establishment",
         f"='{SH_DASH}'!$C${dash['bridge_last']}", S.FTE,
         "Opening establishment, less lapsed vacancies and closures, plus approved growth."),
        ("Projected Saudization",
         f"=IFERROR(({envt}$E${et}+SUMIFS({col_rng(SH_CHAL, 'O', FIRST_ROW, last_row(len(bank.groups)))},"
         f"{col_rng(SH_SUB, 'G', FIRST_ROW, last_row(len(bank.groups)))},\"Saudi\"))"
         f"/({envt}$C${et}+{envt}$S${et}),0)", S.PCT,
         "Today's people plus everything approved."),
    ]
    for label, formula, fmt, why in lines:
        ws.cell(row=row, column=1, value=label).font = S.H2
        c = ws.cell(row=row, column=2, value=formula)
        c.number_format = fmt
        c.font = S.f(14, True, S.NAVY)
        ws.cell(row=row, column=3, value=why).font = S.SMALL
        ws.cell(row=row, column=3).alignment = S.WRAP
        ws.merge_cells(start_row=row, start_column=3, end_row=row, end_column=6)
        ws.row_dimensions[row].height = 24
        row += 1
    row += 1

    ws.cell(row=row, column=1, value="The four cases").font = S.H1
    row += 1
    S.header_row(ws, row, ["Case"] + scen["names"], [52, 17, 17, 17, 17])
    ws.freeze_panes = None
    r = row + 1
    for label, src in [("FTE funded", scen["fte_row"]),
                       (f"{R.PLAN_YEAR} cost funded (SAR '000)", scen["cost_row"])]:
        ws.cell(row=r, column=1, value=label).font = S.H2
        for k in range(4):
            letter = get_column_letter(2 + k)
            ws.cell(row=r, column=2 + k,
                    value=f"='{SH_SCEN}'!${letter}${src}").number_format = (
                S.FTE if "FTE" in label else S.MONEY)
        for col in range(1, 6):
            ws.cell(row=r, column=col).border = S.BOX
        r += 1
    row = r + 1

    ws.cell(row=row, column=1, value="Where the money goes").font = S.H1
    row += 1
    S.header_row(ws, row, ["Priority", "Requested FTE", "Approved FTE",
                           "Approved cost", "Share of approved cost"],
                 [52, 17, 17, 17, 17])
    ws.freeze_panes = None
    c_first = row + 1
    n = len(bank.groups)
    sub_cat = col_rng(SH_SUB, "P", FIRST_ROW, last_row(n))
    sub_fte = col_rng(SH_SUB, "I", FIRST_ROW, last_row(n))
    ch_fte = col_rng(SH_CHAL, "O", FIRST_ROW, last_row(n))
    ch_cost = col_rng(SH_CHAL, "Q", FIRST_ROW, last_row(n))
    for i, (name, rank, _) in enumerate(R.RANK_CATEGORIES):
        r = c_first + i
        ws.cell(row=r, column=1, value=f"{rank}. {name}").font = S.BODY
        ws.cell(row=r, column=2,
                value=f'=SUMIFS({sub_fte},{sub_cat},"{name}")').number_format = S.FTE
        ws.cell(row=r, column=3,
                value=f'=SUMIFS({ch_fte},{sub_cat},"{name}")').number_format = S.FTE
        ws.cell(row=r, column=4,
                value=f'=SUMIFS({ch_cost},{sub_cat},"{name}")').number_format = S.MONEY
        ws.cell(row=r, column=5,
                value=f"=IFERROR($D{r}/SUM($D${c_first}:$D${c_first + 5}),0)"
                ).number_format = S.PCT
        for col in range(1, 6):
            ws.cell(row=r, column=col).border = S.BOX
    c_last = c_first + len(R.RANK_CATEGORIES) - 1
    row = c_last + 2

    for text in [
        "Every figure on this page recalculates from the Challenge sheet. If a "
        "decision changes in the meeting, this page is right again the moment the "
        "cell is typed — there is nothing to refresh and nothing to rebuild.",
        "The rate table behind the cost is illustrative until Finance replaces it. "
        "It sits on the hidden Ref sheet, one row per grade, with basic, housing, "
        "transport, bonus and employer GOSI shown separately so a rate can be "
        "challenged without rebuilding the model.",
    ]:
        S.note_line(ws, row, text, cols=6)
        row += 1
    S.print_setup(ws, landscape=False)


# ── 7. Approved establishment ───────────────────────────────────────────────
def build_establishment(wb: Workbook, bank: R.Bank) -> None:
    ws = wb.create_sheet(SH_EST)
    S.sheet_title(
        ws, f"Approved {R.PLAN_YEAR} establishment",
        "Every approved line, as a flat list for Finance and recruitment. It fills "
        "itself from the Challenge sheet as decisions are made.")
    heads = ["#", "Row", "Group", "Unit", "Job title", "Grade", "Workforce type",
             "Saudi basis", "Approved FTE", "Start quarter",
             f"{R.PLAN_YEAR} cost", "Run-rate", "Driver"]
    widths = [6, 8, 26, 28, 30, 8, 15, 13, 12, 13, 14, 13, 30]
    S.header_row(ws, HEAD_ROW, heads, widths)
    ws.column_dimensions["B"].hidden = True

    n = len(bank.groups)
    first, last = FIRST_ROW, last_row(n)
    seq_col = col_rng(SH_CHAL, "T", first, last)
    for i in range(EST_ROWS):
        r = FIRST_ROW + i
        ws.cell(row=r, column=1, value=i + 1).font = S.SMALL
        # One MATCH per row, reused by every column beside it.
        ws.cell(row=r, column=2, value=f"=IFERROR(MATCH($A{r},{seq_col},0),\"\")")
        pos = f"$B{r}"
        cols = [(3, SH_CHAL, "A"), (4, SH_CHAL, "C"), (5, SH_CHAL, "D"),
                (6, SH_CHAL, "E"), (7, SH_SUB, "F"), (8, SH_SUB, "G"),
                (9, SH_CHAL, "O"), (10, SH_CHAL, "P"), (11, SH_CHAL, "Q"),
                (12, SH_CHAL, "R"), (13, SH_SUB, "K")]
        for col, sheet, src in cols:
            ws.cell(row=r, column=col, value=(
                f'=IF($B{r}="","",INDEX({col_rng(sheet, src, first, last)},{pos}))'))
        for col, fmt in [(9, S.FTE), (11, S.MONEY), (12, S.MONEY)]:
            ws.cell(row=r, column=col).number_format = fmt
    est_last = FIRST_ROW + EST_ROWS - 1
    r = est_last + 1
    ws.cell(row=r, column=5, value="Total").font = S.f(10, True)
    for col in (9, 11, 12):
        letter = get_column_letter(col)
        ws.cell(row=r, column=col,
                value=f"=SUM({letter}{FIRST_ROW}:{letter}{est_last})").font = S.f(10, True)
        ws.cell(row=r, column=col).number_format = S.FTE if col == 9 else S.MONEY
    ws.auto_filter.ref = f"A{HEAD_ROW}:M{est_last}"
    S.print_setup(ws, title_rows=f"{HEAD_ROW}:{HEAD_ROW}")


# ── 8. Group pages ──────────────────────────────────────────────────────────
def build_group_pages(wb: Workbook, bank: R.Bank, env: dict) -> None:
    from openpyxl.worksheet.pagebreak import Break

    ws = wb.create_sheet(SH_PAGES)
    S.sheet_title(
        ws, "Group pages",
        "One page per group, for sending the answer back. Print the sheet and "
        "every group gets its own sheet of paper.")
    for col, w in zip("ABCDEF", [44, 16, 16, 16, 16, 40]):
        ws.column_dimensions[col].width = w

    n = len(bank.groups)
    first, last = FIRST_ROW, last_row(n)
    envt = f"'{SH_ENV}'!"
    ch_g = col_rng(SH_CHAL, "A", first, last)
    ch_fte = col_rng(SH_CHAL, "O", first, last)
    ch_cost = col_rng(SH_CHAL, "Q", first, last)
    ch_run = col_rng(SH_CHAL, "R", first, last)
    ch_q = col_rng(SH_CHAL, "P", first, last)
    sub_g = col_rng(SH_SUB, "A", first, last)
    sub_cat = col_rng(SH_SUB, "P", first, last)
    sub_fte = col_rng(SH_SUB, "I", first, last)
    sub_t = col_rng(SH_SUB, "D", first, last)

    row = 4
    for i, g in enumerate(bank.groups):
        q = g.replace('"', '""')
        er = env["first"] + i
        if i:
            ws.row_breaks.append(Break(id=row - 1))
        ws.cell(row=row, column=1, value=g).font = S.f(16, True, S.NAVY)
        ws.cell(row=row, column=5,
                value=f"Approved {R.PLAN_YEAR} capacity").font = S.SUBTITLE
        S.band(ws, row, 6)
        row += 2
        pairs = [
            ("Positions requested (FTE)", f"={envt}$Q${er}", S.FTE),
            ("Positions approved (FTE)", f"={envt}$S${er}", S.FTE),
            ("Lines declined",
             f'=COUNTIFS({ch_g},"{q}",{ch_fte},0)', S.COUNT),
            (f"{R.PLAN_YEAR} cost approved (SAR '000)", f"={envt}$T${er}", S.MONEY),
            (f"Run-rate into {R.PLAN_YEAR + 1} (SAR '000)",
             f'=SUMIFS({ch_run},{ch_g},"{q}")', S.MONEY),
            ("Cost envelope (SAR '000)", f"={envt}$G${er}", S.MONEY),
            ("Against the envelope", f"={envt}$U${er}", None),
        ]
        for label, formula, fmt in pairs:
            ws.cell(row=row, column=1, value=label).font = S.H2
            c = ws.cell(row=row, column=2, value=formula)
            if fmt:
                c.number_format = fmt
            c.font = S.BODY
            row += 1
        row += 1

        ws.cell(row=row, column=1, value="Approved by priority").font = S.H2
        ws.cell(row=row, column=4, value="Approved by start quarter").font = S.H2
        row += 1
        head = row
        for label, col in [("Priority", 1), ("FTE", 2), ("Cost", 3)]:
            c = ws.cell(row=head, column=col, value=label)
            c.font = S.TH
            c.fill = S.FILL_HEAD
        for label, col in [("Quarter", 4), ("FTE", 5), ("Cost", 6)]:
            c = ws.cell(row=head, column=col, value=label)
            c.font = S.TH
            c.fill = S.FILL_HEAD
        row += 1
        for j, (name, rank, _) in enumerate(R.RANK_CATEGORIES):
            r = row + j
            ws.cell(row=r, column=1, value=f"{rank}. {name}").font = S.BODY
            ws.cell(row=r, column=2, value=(
                f'=SUMIFS({ch_fte},{ch_g},"{q}",{sub_cat},"{name}")')).number_format = S.FTE
            ws.cell(row=r, column=3, value=(
                f'=SUMIFS({ch_cost},{ch_g},"{q}",{sub_cat},"{name}")')).number_format = S.MONEY
        for j, quarter in enumerate(R.QUARTERS):
            r = row + j
            ws.cell(row=r, column=4, value=quarter).font = S.BODY
            ws.cell(row=r, column=5, value=(
                f'=SUMIFS({ch_fte},{ch_g},"{q}",{ch_q},"{quarter}")')).number_format = S.FTE
            ws.cell(row=r, column=6, value=(
                f'=SUMIFS({ch_cost},{ch_g},"{q}",{ch_q},"{quarter}")')).number_format = S.MONEY
        row += len(R.RANK_CATEGORIES) + 1
        S.note_line(ws, row,
                    f"Approved is what {g} should now plan and recruit against. "
                    "Anything declined can be brought back at the mid-year review "
                    "with the volumes that have actually landed.", cols=6)
        row += 3
    S.print_setup(ws, landscape=False, fit_width=1, fit_height=0)


# ── Assembly ────────────────────────────────────────────────────────────────
TAB_ORDER = [SH_READ, SH_ENV, SH_SUB, SH_CHAL, SH_SCEN, SH_DASH, SH_EXEC,
             SH_EST, SH_PAGES, SH_ENG, SH_REF]


def build_consolidator(path=None, bank: R.Bank | None = None) -> dict:
    bank = bank or R.Bank()
    path = Path(path or DIST / f"{R.PLAN_YEAR}-Capacity-Consolidator.xlsx")
    wb = Workbook()
    wb.remove(wb.active)

    build_readme(wb, bank)
    env = build_envelopes(wb, bank)
    sub = build_submissions(wb, bank)
    chal = build_challenge(wb, bank)
    sc = build_scenarios(wb, bank)
    build_engine(wb, bank, sc)
    scen = finish_scenarios(wb, bank, sc, env)
    dash = build_dashboard(wb, bank, env, scen)
    build_exec(wb, bank, env, scen, dash)
    build_establishment(wb, bank)
    build_group_pages(wb, bank, env)
    build_ref(wb, bank)

    wb._sheets.sort(key=lambda w: TAB_ORDER.index(w.title))
    for ws in wb.worksheets:
        S.protect(ws)
    wb.properties.title = f"{R.PLAN_YEAR} Capacity Exercise - consolidator"
    wb.properties.creator = "Capacity exercise toolkit"
    wb.save(path)
    return dict(path=str(path), env=env, sub=sub, chal=chal, scen=scen, dash=dash,
                first=FIRST_ROW, last=last_row(len(bank.groups)))


if __name__ == "__main__":
    print(build_consolidator()["path"])
