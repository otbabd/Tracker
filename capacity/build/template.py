"""The group capacity template.

One workbook per group, on the simplified collection shape: one row per existing
position, one row per ask, career level and job family rather than grade, and a
quarter split that adds itself up.

Every cross-sheet reference goes through a defined name. Renaming a tab or moving
a column then cannot break another sheet, which is exactly what happened to the
first version of this file.

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
import tables as TB

ASK_ROWS = 200          # generous headroom; no group will reach it
SEAT_PAD = 40           # blank rows under the pre-filled establishment
PIPE_ROWS = 120         # known departures
PROBLEM_ROWS = 20

SH_READ = "How to use"
SH_TREE = "1. My structure"
SH_CAP = "2. Current capacity"
SH_PIPE = "3. Pipeline out"
SH_ASK = "4. Capacity asks"
SH_POS = "5. My position"
SH_CHK = "6. Check & submit"
SH_GLOSS = "Glossary"
SH_REF = "Ref"

HEAD_ROW = 5
FIRST_ROW = HEAD_ROW + 1

# ── The asks sheet, column by column ───────────────────────────────────────
ASK_COLS = [
    ("Ref", 6), ("Division", 24), ("Department", 26), ("Unit", 26),
    ("Sub-Unit", 24), ("Job title", 30), ("Career Level", 18), ("Job Family", 18),
    ("Worker type", 14), ("Current Capacity", 15), ("New Asks", 11),
    ("Q1", 7), ("Q2", 7), ("Q3", 7), ("Q4", 7),
    ("Category", 14), ("Driver", 30), ("Alternatives considered", 44),
    ("What's missing", 38), ("Issue no.", 9),
]
A = {name: get_column_letter(i) for i, (name, _) in enumerate(ASK_COLS, start=1)}

# ── The current-capacity sheet, column by column ───────────────────────────
CAP_COLS = [
    ("Mis Code", 12), ("Division", 24), ("Department", 26), ("Unit", 26),
    ("Sub-Unit", 24), ("Job Title", 30), ("Career Level", 18), ("Job Family", 18),
    ("Nationality Mandate?", 16), ("Approved HC", 12), ("Filled", 9), ("Vacant", 9),
    ("Worker type", 14), ("Capacity Direction", 17), ("HC slated for exit", 15),
    ("Seats released", 13), ("What's missing", 34),
]
C = {name: get_column_letter(i) for i, (name, _) in enumerate(CAP_COLS, start=1)}

# ── The pipeline-out sheet, column by column ───────────────────────────────
PIPE_COLS = [
    ("Ref", 6), ("Division", 22), ("Unit", 26), ("Job title", 28),
    ("Career Level", 17), ("Worker type", 13), ("Name or ID", 20),
    ("Reason", 20), ("Leaving quarter", 13), ("What happens to the seat", 24),
    ("Backfill quarter", 13), ("Paid this year", 13),
    (f"{R.PLAN_YEAR} cash released", 15), ("Run-rate released", 15),
    ("What's missing", 32),
]
P = {name: get_column_letter(i) for i, (name, _) in enumerate(PIPE_COLS, start=1)}

MISSING_COL = "What's missing"


def _name(wb, sheet: str, name: str, ref: str) -> None:
    wb.defined_names.add(DefinedName(name, attr_text=f"'{sheet}'!{ref}"))


def mini_head(ws, row: int, heads, widths=None) -> None:
    """A table header that leaves the freeze pane alone — a dashboard carries
    several tables and only the top of the sheet should freeze."""
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


# ── Reference sheet ─────────────────────────────────────────────────────────
def build_ref(wb: Workbook, bank: R.Bank, group: str) -> None:
    """Lookup tables and the exercise settings. Hidden, and the only place a
    rate is stated — every formula that needs one points here."""
    ws = wb.create_sheet(SH_REF)
    ws.sheet_state = "hidden"
    row = S.sheet_title(ws, "Reference data", "Do not edit. Maintained centrally.")
    row = TB.write_settings(wb, ws, SH_REF, row,
                            extras=[("GroupName", "Group", group, None)])

    # Envelopes — the group's ceilings, set centrally.
    ws.cell(row=row, column=1, value="Envelope for this group").font = S.H1
    row += 1
    tot = bank.group_totals(group)
    base_saudi = tot["saudi"] / tot["filled"] if tot["filled"] else 0
    env = [
        ("CostEnvelope", "Cost envelope (SAR '000, run-rate)",
         round(tot["cost"] * 0.06, 0), S.MONEY,
         "Illustrative: six per cent of the group's current pay bill."),
        ("HeadEnvelope", "Headcount envelope (net adds)",
         max(5, round(tot["approved"] * 0.05)), S.COUNT,
         "Illustrative: five per cent of the group's current establishment."),
        ("SaudiTarget", "Mandated-seat target", round(base_saudi + 0.02, 2), S.PCT,
         "Illustrative: two points above where the group stands today."),
    ]
    for name, label, value, fmt, why in env:
        S.label_value(ws, row, label, value, fmt, note=why).font = S.INPUT
        _name(wb, SH_REF, name, f"$B${row}")
        row += 1
    row += 1

    row = TB.write_rate_card(wb, ws, SH_REF, row)
    row = TB.write_drivers(wb, ws, SH_REF, row)

    levels = R.CAREER_LEVELS
    families = bank.job_families or ["Professional"]
    col = TB.write_lists(wb, ws, SH_REF, row,
                         extra=[("CareerLevels", levels), ("JobFamilies", families)])

    # Every unit in this group, so an ask can only name a real one.
    listed = 0
    for label, want_levels, list_name in [
            ("Divisions", (1,), "DivisionList"),
            ("Units", (2, 3, 4, 5), "UnitList")]:
        names = [n["name"] for _, n in bank.descend(bank.group_key(group))
                 if n["level"] in want_levels] or [group]
        ws.cell(row=row, column=col, value=label).font = S.H2
        for i, u in enumerate(names, start=1):
            ws.cell(row=row + i, column=col, value=u)
        letter = get_column_letter(col)
        _name(wb, SH_REF, list_name,
              f"${letter}${row + 1}:${letter}${row + len(names)}")
        listed = max(listed, len(names))
        col += 2

    # What each capacity direction means, spelled out where it is defined.
    row = row + max(listed, len(levels), len(families)) + 3
    ws.cell(row=row, column=1, value="What each capacity direction means").font = S.H1
    row += 1
    for direction, why in R.CAPACITY_DIRECTIONS:
        ws.cell(row=row, column=1, value=direction).font = S.H2
        ws.cell(row=row, column=2, value=why).font = S.SMALL
        row += 1


# ── How to use ──────────────────────────────────────────────────────────────
def build_readme(wb: Workbook, group: str) -> None:
    ws = wb.create_sheet(SH_READ)
    row = S.sheet_title(
        ws, f"{R.PLAN_YEAR} Capacity Exercise",
        f"{group} — what to do, in the order to do it")
    ws.column_dimensions["A"].width = 26
    for c in "BCDEFGH":
        ws.column_dimensions[c].width = 14

    steps = [
        (SH_TREE,
         "Your group as it stands today. Collapse and expand with the +/- buttons in "
         f"the left margin. Nothing to fill in — the {R.PLAN_YEAR} columns fill "
         "themselves from the three sheets after it."),
        (SH_CAP,
         "One row per job, with the seats you have in it. Fill in the career level, "
         "whether the seat has to be Saudi, and what you intend to do with the job "
         "next year. If you are reducing it, say how many of its seats are going."),
        (SH_PIPE,
         "Everyone you already know is leaving. For each one, say what happens to "
         "the seat: refill it, hold it empty for a while, or give it up to help pay "
         "for what you are asking for."),
        (SH_ASK,
         "One row per position you want. Put the numbers in the quarter you want "
         "them to start — the total adds itself up. Every row needs a driver, "
         "because that is what decides the order things get funded in."),
        (SH_POS,
         "Your headcount and your cost by division, the cash the year actually "
         "costs, and where you land against your envelopes. Read this before you "
         "submit, not after."),
        (SH_CHK,
         "Everything still missing or invalid, listed row by row. When it is clear, "
         "set the state to Submitted and return the file."),
        (SH_GLOSS,
         "Every term this workbook uses, in plain words. Start here if a column "
         "header is not obvious."),
    ]
    ws.cell(row=row, column=1, value="The sheets, in the order to work through them").font = S.H1
    row += 1
    for name, why in steps:
        ws.cell(row=row, column=1, value=name).font = S.H2
        ws.cell(row=row, column=1).alignment = S.TOP
        c = ws.cell(row=row, column=2, value=why)
        c.font = S.BODY_DIM
        c.alignment = S.WRAP
        ws.merge_cells(start_row=row, start_column=2, end_row=row, end_column=8)
        ws.row_dimensions[row].height = 40
        row += 1
    row += 1

    ws.cell(row=row, column=1, value="What each yellow column expects").font = S.H1
    row += 1
    expects = [
        ("Career Level", SH_CAP,
         "The level of the job, not of the person and not the grade. Pick from the "
         "list. Until every row has one, no cost anywhere in this file can be "
         "worked out and it all reads as a dash."),
        ("Nationality Mandate?", SH_CAP,
         "Does this job have to be filled by a Saudi national? A property of the "
         "role, not of whoever is in it today."),
        ("Capacity Direction", SH_CAP,
         "Grow, Hold or Reduce. Grow and Hold change nothing by themselves — "
         "growth arrives as a row on the asks sheet. Reduce is the only way a seat "
         "leaves your establishment."),
        ("HC slated for exit", SH_CAP,
         "How many of the row's seats are going. If the row has four and two are "
         "going, put 2. Only counted when the direction says Reduce."),
        ("What happens to the seat", SH_PIPE,
         "Refill it, hold it empty until a quarter you name, or give it up. Giving "
         "it up is the only one that changes your establishment, and it has to be "
         f"counted in the Reduce column on {SH_CAP} as well."),
        ("Q1 to Q4", SH_ASK,
         "How many people you want starting in each quarter. Leave the rest blank. "
         "The New Asks total adds itself up from these four."),
        ("Driver", SH_ASK,
         "Why you need it. The driver sets the priority, and the priority decides "
         "what survives if the envelope binds."),
        ("Alternatives considered", SH_ASK,
         "What you tried before asking for a person: automation, vendor cover, "
         "reprioritising. The first question you will be asked."),
    ]
    for name, sheet, why in expects:
        ws.cell(row=row, column=1, value=name).font = S.H2
        ws.cell(row=row, column=1).alignment = S.TOP
        c = ws.cell(row=row, column=2, value=f"{sheet} — {why}")
        c.font = S.BODY_DIM
        c.alignment = S.WRAP
        ws.merge_cells(start_row=row, start_column=2, end_row=row, end_column=8)
        ws.row_dimensions[row].height = 40
        row += 1
    row += 1

    row = S.legend(ws, row)

    ws.cell(row=row, column=1, value="The three things people get wrong").font = S.H1
    row += 1
    for text in [
        "The quarters make the total, not the other way round. New Asks is worked "
        "out from what you put in Q1 to Q4, so there is nothing to reconcile and "
        "nothing that can disagree. If the total looks wrong, a quarter is wrong.",
        "Reduce is the only way to give up a seat, and it needs a number. Marking a "
        "job Reduce without saying how many seats are going changes nothing at all. "
        "A vacancy you no longer need is a Reduce; so is a leaver whose seat you are "
        "surrendering on the pipeline sheet.",
        "The cost by division is a full-year run-rate, not what you spend next year. "
        "It sits beside headcount because both are stocks. What the year actually "
        "costs is the separate cash block underneath, and the two answer different "
        "questions — approving both at once counts the same money twice.",
    ]:
        S.note_line(ws, row, text)
        row += 1
    row += 1

    ws.cell(row=row, column=1, value="When the check sheet complains").font = S.H1
    row += 1
    S.note_line(
        ws, row,
        f"{SH_CHK} lists what is still missing and where. Every sheet also has a "
        "last column telling you, row by row, what that row needs — filter on it to "
        "find the rows rather than hunting for them. The file will not let you set "
        "the state to Submitted until every blocking check reads OK, which is the "
        "point: it is quicker to fix here than after the centre has read it.", cols=8)
    S.print_setup(ws, landscape=False)


# ── Glossary ────────────────────────────────────────────────────────────────
def build_glossary(wb: Workbook, group: str) -> None:
    ws = wb.create_sheet(SH_GLOSS)
    row = S.sheet_title(
        ws, "Glossary",
        "Every term this workbook uses. If a column header is not obvious, it is "
        "explained here.")
    S.header_row(ws, row, ["Term", "What it means"], [28, 110])
    first = row + 1
    terms = [
        ("Establishment", "The seats the bank has approved, filled or not. This "
         "exercise plans seats; who sits in them is a separate question."),
        ("Approved HC", "How many seats a job has on the establishment."),
        ("Filled / Vacant", "Of those seats, how many have somebody in them and how "
         "many do not."),
        ("Career level", "The level of the job — the bank's own ladder. A property "
         "of the job, not of the person and not the grade. Everything is priced off "
         "it, so a row without one cannot be costed."),
        ("Job family", "The kind of work, used to group like with like across the "
         "bank."),
        ("Worker type", "Permanent, insourced or outsourced. All three cost money "
         "and all three take a seat; they are simply bought differently."),
        ("Capacity direction", "What you intend to do with a job next year: Grow, "
         "Hold or Reduce."),
        ("Grow", "You need more here. The extra arrives as a row on " + SH_ASK +
         "; the direction on its own changes no numbers."),
        ("Hold", "Stays as it is."),
        ("Reduce", "You are giving up seats on this row. The only direction that "
         "moves the establishment, and it needs a number beside it."),
        ("HC slated for exit", "How many of a row's seats are going. Four seats and "
         "two going means 2, not 4."),
        ("Pipeline out", "People you already know are leaving — resignations, "
         "retirements, contract ends, transfers out."),
        ("Backfill", "Refill the seat. Nothing changes but who is in it."),
        ("Defer backfill", "Keep the seat but hold it empty until a later quarter. "
         "Saves cash this year; the seat is still yours."),
        (R.SURRENDER, "Give the seat up so its cost helps pay for what you have "
         "asked for. Count it in the Reduce column on " + SH_CAP + " as well."),
        ("Run-rate cost", "What a seat costs for a full twelve months, whenever it "
         "starts. What the bank commits to, and what carries into the year after."),
        ("In-year or cash cost", "What is actually paid in the plan year. A "
         "position starting in Q1 is paid four quarters of its cost; one starting "
         "in Q4 is paid one."),
        ("One-off cost", "The cost of bringing somebody in — recruitment, "
         "relocation, setup — paid in the year they join and never again. Kept out "
         "of the run-rate so it does not inflate every year that follows."),
        ("Envelope", "The ceiling set centrally for your group: cost, net "
         "establishment change, and the mandated-seat share."),
        ("Mandated seat", "A seat that has to be filled by a Saudi national. A "
         "property of the role."),
        ("Priority", "Regulatory, Strategic, Control or BAU. Set by the driver you "
         "choose, and it decides the order things are funded in — regulatory first, "
         "BAU first to fall."),
        ("Driver", "The reason a position is needed. Pick the closest; it sets the "
         "priority for you."),
        ("Loaded cost", "Basic pay, housing, transport, target bonus and employer "
         "GOSI together. Not the salary — the whole cost of the seat."),
    ]
    for i, (term, meaning) in enumerate(terms):
        r = first + i
        ws.cell(row=r, column=1, value=term).font = S.H2
        ws.cell(row=r, column=1).alignment = S.TOP
        c = ws.cell(row=r, column=2, value=meaning)
        c.font = S.BODY_DIM
        c.alignment = S.WRAP
        ws.row_dimensions[r].height = 28
        for col in (1, 2):
            ws.cell(row=r, column=col).border = S.BOX
    S.print_setup(ws, landscape=False, title_rows=f"{row}:{row}")


# ── 1. My structure ─────────────────────────────────────────────────────────
def build_tree(wb: Workbook, bank: R.Bank, group: str) -> None:
    ws = wb.create_sheet(SH_TREE)
    row = S.sheet_title(
        ws, "My structure",
        f"{group} as it stands in {R.BASE_YEAR}. Use the +/- buttons on the left "
        f"to collapse and expand. The {R.PLAN_YEAR} columns fill in from sheets 2 and 3.")
    heads = ["Level", "Unit", f"{R.BASE_YEAR} approved", "Filled", "Vacant",
             f"{R.PLAN_YEAR} exits", f"{R.PLAN_YEAR} asked",
             f"{R.PLAN_YEAR} total", "Change", "Name"]
    S.header_row(ws, row, heads, [14, 46, 15, 11, 11, 13, 13, 13, 11, 30])
    ws.column_dimensions["J"].hidden = True
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
        # The name in column B is indented for reading, so it never equals the
        # unit name on the other sheets. Column J carries the raw one and is
        # what every lookup matches on.
        ws.cell(row=r, column=10, value=node["name"]).font = S.SMALL
        ws.cell(row=r, column=3, value=b["approved"]).number_format = S.COUNT
        ws.cell(row=r, column=4, value=b["filled"]).number_format = S.COUNT
        ws.cell(row=r, column=5, value=b["vacant"]).number_format = S.COUNT
        # Defined names, so renaming a sheet or moving a column cannot break
        # this — which is exactly how the first version broke.
        for col, formula in [
            (6, f"=SUMIFS(SeatExits,SeatDivision,$J{r})"
                f"+SUMIFS(SeatExits,SeatDepartment,$J{r})"
                f"+SUMIFS(SeatExits,SeatUnit,$J{r})"
                f"+SUMIFS(SeatExits,SeatSubUnit,$J{r})"),
            (7, f"=SUMIFS(AskTotal,AskDivision,$J{r})"
                f"+SUMIFS(AskTotal,AskDepartment,$J{r})"
                f"+SUMIFS(AskTotal,AskUnit,$J{r})"
                f"+SUMIFS(AskTotal,AskSubUnit,$J{r})"),
            (8, f"=$C{r}-$F{r}+$G{r}"),
            (9, f"=$H{r}-$C{r}"),
        ]:
            ws.cell(row=r, column=col, value=formula).number_format = S.FTE
        for col in range(3, 10):
            ws.cell(row=r, column=col).font = S.BODY if lvl > 1 else S.H2
        if lvl > 0:
            ws.row_dimensions[r].outline_level = min(lvl, 7)
        if lvl <= 1:
            S.band(ws, r, len(heads) - 1)
        r += 1

    last = r - 1
    ws.conditional_formatting.add(
        f"I{first}:I{last}",
        CellIsRule(operator="greaterThan", formula=["0"], font=S.f(10, True, S.OK_GREEN)))
    ws.conditional_formatting.add(
        f"I{first}:I{last}",
        CellIsRule(operator="lessThan", formula=["0"], font=S.f(10, True, S.RED_ALERT)))
    ws.conditional_formatting.add(
        f"E{first}:E{last}",
        CellIsRule(operator="greaterThan", formula=["0"], font=S.f(10, False, S.AMBER)))
    S.note_line(ws, last + 2,
                "Each row counts what names it, and the group and division rows sum "
                f"everything beneath them. Seats released come from the Reduce "
                f"column on {SH_CAP}; asks come from {SH_ASK}.", cols=len(heads) - 1)
    S.print_setup(ws, title_rows=f"{row}:{row}")


# ── 2. Current capacity ─────────────────────────────────────────────────────
def build_capacity(wb: Workbook, bank: R.Bank, group: str) -> dict:
    ws = wb.create_sheet(SH_CAP)
    S.sheet_title(
        ws, "Current capacity",
        "One row per job, with the seats you have in it. The columns that need "
        "you are career level, whether the seat is mandated Saudi, what you "
        f"intend to do with the job in {R.PLAN_YEAR} — and, if you are reducing "
        "it, how many of its seats are going.")
    S.header_row(ws, HEAD_ROW, [h for h, _ in CAP_COLS], [w for _, w in CAP_COLS])

    seats = bank.seats(group)
    first = FIRST_ROW
    last = first + len(seats) + SEAT_PAD - 1
    plain = S.PatternFill(fill_type=None)
    for i in range(len(seats) + SEAT_PAD):
        r = first + i
        seat = seats[i] if i < len(seats) else None
        values = [
            seat["mis"] if seat else None,
            seat["division"] if seat else None,
            seat["department"] if seat else None,
            seat["unit"] if seat else None,
            seat["sub_unit"] if seat else None,
            seat["title"] if seat else None,
            (seat["level"] or None) if seat else None,
            seat["family"] if seat else None,
            None,                                   # nationality mandate: theirs
            seat["approved"] if seat else None,
            seat["filled"] if seat else None,
            seat["vacant"] if seat else None,
            seat["worker_type"] if seat else None,
            None,                                   # capacity direction: theirs
        ]
        for col, value in enumerate(values, start=1):
            # A pre-filled cell is still theirs to correct — the export is not
            # gospel, and a wrong unit here is a wrong unit everywhere.
            cell = S.input_cell(ws.cell(row=r, column=col, value=value))
            if col in (10, 11, 12):
                cell.number_format = S.FTE

        S.input_cell(ws.cell(row=r, column=15), S.FTE)   # HC slated for exit
        # Only a row marked Reduce gives up seats. Reading the typed number
        # straight would let a stale figure, left on a row switched back to
        # Hold, quietly delete seats from the establishment.
        released = ws.cell(row=r, column=16, value=(
            f'=IF(${C["Capacity Direction"]}{r}="{R.REDUCE_DIRECTION}",'
            f'N(${C["HC slated for exit"]}{r}),0)'))
        released.number_format = S.FTE
        released.font = S.BODY
        released.fill = plain

        # Division is deliberately not checked: a group head, and anyone else
        # reporting straight to the group, legitimately sits outside one.
        missing = "&".join(
            f'IF({test},", {word}","")' for test, word in [
                (f'${C["Career Level"]}{r}=""', "career level"),
                (f'${C["Nationality Mandate?"]}{r}=""', "nationality mandate"),
                (f'${C["Capacity Direction"]}{r}=""', "capacity direction"),
                (f'N(${C["Approved HC"]}{r})<=0', "approved HC"),
                (f'AND(${C["Career Level"]}{r}<>"",'
                 f'COUNTIF(CareerLevels,${C["Career Level"]}{r})=0)',
                 "a career level that is not on the ladder"),
                (f'AND(${C["Capacity Direction"]}{r}="{R.REDUCE_DIRECTION}",'
                 f'N(${C["HC slated for exit"]}{r})<=0)',
                 "how many seats Reduce means"),
                (f'AND(N(${C["HC slated for exit"]}{r})>0,'
                 f'${C["Capacity Direction"]}{r}<>"{R.REDUCE_DIRECTION}")',
                 "a number of seats on a row not marked Reduce"),
                (f'N(${C["HC slated for exit"]}{r})>N(${C["Approved HC"]}{r})',
                 "more seats given up than the row has"),
            ])
        flag = ws.cell(row=r, column=17, value=(
            f'=IF(${C["Job Title"]}{r}="","",MID({missing},3,200))'))
        flag.font = S.f(9, color=S.RED_ALERT)
        flag.fill = plain

    for col, list_name in [("Career Level", "CareerLevels"),
                           ("Job Family", "JobFamilies"),
                           ("Nationality Mandate?", "YesNo"),
                           ("Worker type", "WorkerTypes"),
                           ("Capacity Direction", "DirectionList")]:
        dv = DataValidation(type="list", formula1=f"={list_name}", allow_blank=True,
                            showErrorMessage=True)
        dv.error = "Pick a value from the list."
        ws.add_data_validation(dv)
        dv.add(f"{C[col]}{first}:{C[col]}{last}")

    # You cannot give up more seats than the row holds. The cap is the row's
    # own Approved HC, so the rule moves down the column with it.
    dvn = DataValidation(type="decimal", operator="between", formula1="0",
                         formula2=f'${C["Approved HC"]}{first}',
                         allow_blank=True, showErrorMessage=True)
    dvn.errorTitle = "More than the row has"
    dvn.error = ("Give up between none and all of this row's approved "
                 "headcount.")
    ws.add_data_validation(dvn)
    dvn.add(f'{C["HC slated for exit"]}{first}:{C["HC slated for exit"]}{last}')

    miss = C[MISSING_COL]
    released = C["Seats released"]
    approved = C["Approved HC"]
    # Shade a row out only when the whole block goes. A partial reduction is
    # still a live row and should not read as one that has gone.
    ws.conditional_formatting.add(
        f"A{first}:{miss}{last}",
        FormulaRule(formula=[f"AND(N(${approved}{first})>0,"
                             f"${released}{first}=${approved}{first})"],
                    font=S.f(10, color=S.INK_MUTE)))
    ws.conditional_formatting.add(
        f"{released}{first}:{released}{last}",
        CellIsRule(operator="greaterThan", formula=["0"],
                   font=S.f(10, True, S.AMBER)))
    ws.conditional_formatting.add(
        f"{miss}{first}:{miss}{last}",
        FormulaRule(formula=[f'${miss}{first}<>""'],
                    fill=S.PatternFill("solid", fgColor="FDE7E9")))
    ws.auto_filter.ref = f"A{HEAD_ROW}:{miss}{last}"

    for label, col in [("SeatDivision", "Division"), ("SeatDepartment", "Department"),
                       ("SeatUnit", "Unit"), ("SeatSubUnit", "Sub-Unit"),
                       ("SeatTitle", "Job Title"), ("SeatLevel", "Career Level"),
                       ("SeatMandate", "Nationality Mandate?"),
                       ("SeatApproved", "Approved HC"), ("SeatFilled", "Filled"),
                       ("SeatVacant", "Vacant"), ("SeatWorkerType", "Worker type"),
                       ("SeatDirection", "Capacity Direction"),
                       ("SeatSlated", "HC slated for exit"),
                       ("SeatExits", "Seats released"),
                       ("SeatProblem", MISSING_COL)]:
        _name(wb, SH_CAP, label, f"${C[col]}${first}:${C[col]}${last}")

    S.print_setup(ws, title_rows=f"{HEAD_ROW}:{HEAD_ROW}")
    return dict(first=first, last=last, seats=len(seats))


# ── 3. Pipeline out ─────────────────────────────────────────────────────────
def build_pipeline(wb: Workbook, bank: R.Bank, group: str) -> dict:
    """Who is already on the way out, and what happens to the seat.

    The establishment still comes from the Reduce column on the capacity sheet;
    this sheet says which of those seats have a name against them, when the cost
    actually stops, and what the group intends to do about it.
    """
    ws = wb.create_sheet(SH_PIPE)
    S.sheet_title(
        ws, "Pipeline out",
        "Everyone you already know is leaving, and what you intend to do with "
        "each seat. This is where the saving from people going gets counted.")
    S.header_row(ws, HEAD_ROW, [h for h, _ in PIPE_COLS], [w for _, w in PIPE_COLS])

    first, last = FIRST_ROW, FIRST_ROW + PIPE_ROWS - 1
    surrender = R.SURRENDER.replace('"', '""')
    defer = R.DEFER.replace('"', '""')
    for i in range(PIPE_ROWS):
        r = first + i
        ws.cell(row=r, column=1, value=i + 1).font = S.SMALL
        for col in range(2, 12):
            S.input_cell(ws.cell(row=r, column=col))

        leave = f'MATCH(${P["Leaving quarter"]}{r},QuarterList,0)'
        back = f'MATCH(${P["Backfill quarter"]}{r},QuarterList,0)'
        # A seat is paid up to and including the quarter its holder leaves —
        # the mirror of a start being paid from the quarter it begins.
        paid = (
            f'=IF(OR(${P["Job title"]}{r}="",${P["Leaving quarter"]}{r}="",'
            f'${P["What happens to the seat"]}{r}=""),"",'
            f'IF(${P["What happens to the seat"]}{r}="{surrender}",{leave}/4,'
            f'IF(${P["What happens to the seat"]}{r}="{defer}",'
            f'IF(${P["Backfill quarter"]}{r}="",{leave}/4,'
            f"MIN(1,{leave}/4+(5-{back})/4)),1)))")
        ws.cell(row=r, column=12, value=paid).number_format = S.PCT0
        cost = _rate_lookup(f'${P["Career Level"]}{r}')
        ws.cell(row=r, column=13, value=(
            f'=IF(${P["Paid this year"]}{r}="","",'
            f'{cost}*(1-${P["Paid this year"]}{r}))')).number_format = S.MONEY
        ws.cell(row=r, column=14, value=(
            f'=IF(${P["What happens to the seat"]}{r}="{surrender}",{cost},0)')
        ).number_format = S.MONEY

        missing = "&".join(
            f'IF({test},", {word}","")' for test, word in [
                (f'${P["Unit"]}{r}=""', "unit"),
                (f'${P["Career Level"]}{r}=""', "career level"),
                (f'${P["Reason"]}{r}=""', "reason"),
                (f'${P["Leaving quarter"]}{r}=""', "leaving quarter"),
                (f'${P["What happens to the seat"]}{r}=""',
                 "what happens to the seat"),
                (f'AND(${P["What happens to the seat"]}{r}="{defer}",'
                 f'${P["Backfill quarter"]}{r}="")', "the backfill quarter"),
                # AND evaluates every argument, so a blank backfill quarter
                # would push #N/A out of the MATCH before the guard could stop
                # it. IFERROR turns that into "nothing to complain about".
                (f'IFERROR(AND(${P["Backfill quarter"]}{r}<>"",'
                 f'${P["Leaving quarter"]}{r}<>"",{back}<={leave}),FALSE)',
                 "a backfill quarter later than the leaving quarter"),
                (f'AND(${P["Unit"]}{r}<>"",COUNTIF(UnitList,${P["Unit"]}{r})=0)',
                 "a unit that is not in your structure"),
            ])
        ws.cell(row=r, column=15, value=(
            f'=IF(${P["Job title"]}{r}="","",MID({missing},3,300))')
        ).font = S.f(9, color=S.RED_ALERT)
        for col in (12, 13, 14):
            ws.cell(row=r, column=col).font = S.BODY

    for col, list_name in [("Division", "DivisionList"), ("Unit", "UnitList"),
                           ("Career Level", "CareerLevels"),
                           ("Worker type", "WorkerTypes"),
                           ("Reason", "LeavingReasons"),
                           ("Leaving quarter", "QuarterList"),
                           ("What happens to the seat", "DispositionList"),
                           ("Backfill quarter", "QuarterList")]:
        dv = DataValidation(type="list", formula1=f"={list_name}", allow_blank=True,
                            showErrorMessage=True)
        dv.error = "Pick a value from the list."
        ws.add_data_validation(dv)
        dv.add(f"{P[col]}{first}:{P[col]}{last}")

    miss = P[MISSING_COL]
    ws.conditional_formatting.add(
        f'{P["What happens to the seat"]}{first}:'
        f'{P["What happens to the seat"]}{last}',
        CellIsRule(operator="equal", formula=[f'"{R.SURRENDER}"'],
                   font=S.f(10, True, S.OK_GREEN)))
    ws.conditional_formatting.add(
        f"A{first}:{miss}{last}",
        FormulaRule(formula=[f'${miss}{first}<>""'],
                    fill=S.PatternFill("solid", fgColor="FDE7E9")))
    ws.auto_filter.ref = f"A{HEAD_ROW}:{miss}{last}"

    for label, col in [("OutDivision", "Division"), ("OutUnit", "Unit"),
                       ("OutTitle", "Job title"), ("OutLevel", "Career Level"),
                       ("OutQuarter", "Leaving quarter"),
                       ("OutDisposition", "What happens to the seat"),
                       ("OutCash", f"{R.PLAN_YEAR} cash released"),
                       ("OutRunRate", "Run-rate released"),
                       ("OutProblem", MISSING_COL)]:
        _name(wb, SH_PIPE, label, f"${P[col]}${first}:${P[col]}${last}")

    S.note_line(
        ws, last + 2,
        "A seat is paid up to and including the quarter its holder leaves, which "
        "is the mirror of a new position being paid from the quarter it starts. "
        "So a Q1 leaver releases three quarters of cost and a Q4 leaver releases "
        "none. Deferring a backfill releases only the gap between the two "
        "quarters; the seat is still yours and still on the establishment. Only "
        "'" + R.SURRENDER + "' gives the seat up, and it has to be counted in "
        "the Reduce column on " + SH_CAP + " as well — that column, not this "
        "sheet, is what moves the establishment.", cols=len(PIPE_COLS))
    S.print_setup(ws, title_rows=f"{HEAD_ROW}:{HEAD_ROW}")
    return dict(first=first, last=last)


def _rate_lookup(level_cell: str) -> str:
    """Full-year loaded cost of one seat at the level in `level_cell`."""
    m = f"MATCH({level_cell},LevelList,0)"
    return (f"IFERROR(INDEX(LevelBasic,{m})+INDEX(LevelHousing,{m})"
            f"+INDEX(LevelTransport,{m})"
            f"+INDEX(LevelBasic,{m})*INDEX(LevelBonus,{m})"
            f"+(INDEX(LevelBasic,{m})+INDEX(LevelHousing,{m}))*GosiSaudi,0)")


# ── 4. Capacity asks ────────────────────────────────────────────────────────
def build_asks(wb: Workbook, bank: R.Bank, group: str) -> dict:
    ws = wb.create_sheet(SH_ASK)
    S.sheet_title(
        ws, "Capacity asks",
        f"One row per position you want in {R.PLAN_YEAR}. Put each one in the "
        "quarter you want it to start — the total adds itself up.")

    # The quarter columns sit under one banner, as on the collection sheet.
    ws.merge_cells(start_row=HEAD_ROW - 1, start_column=12, end_row=HEAD_ROW - 1,
                   end_column=15)
    banner = ws.cell(row=HEAD_ROW - 1, column=12, value="Start quarter")
    banner.font = S.f(9, True, "FFFFFF")
    banner.fill = S.FILL_HEAD
    banner.alignment = S.CENTRE
    S.header_row(ws, HEAD_ROW, [h for h, _ in ASK_COLS], [w for _, w in ASK_COLS])

    first, last = FIRST_ROW, FIRST_ROW + ASK_ROWS - 1
    for i in range(ASK_ROWS):
        r = first + i
        ws.cell(row=r, column=1, value=i + 1).font = S.SMALL
        for col in [2, 3, 4, 5, 6, 7, 8, 9, 12, 13, 14, 15, 17, 18]:
            cell = S.input_cell(ws.cell(row=r, column=col))
            if col in (12, 13, 14, 15):
                cell.number_format = S.FTE

        # What the unit already has, so the ask is argued against something.
        ws.cell(row=r, column=10, value=(
            f'=IF(${A["Job title"]}{r}="","",'
            f'SUMIFS(SeatApproved,SeatUnit,${A["Unit"]}{r},'
            f'SeatTitle,${A["Job title"]}{r}))')).number_format = S.FTE
        # The total is the split. The two cannot disagree, because there is one.
        ws.cell(row=r, column=11, value=(
            f'=IF(${A["Job title"]}{r}="","",'
            f'SUM(${A["Q1"]}{r}:${A["Q4"]}{r}))')).number_format = S.FTE
        # Category follows the driver, so the ranking rule is visible here
        # rather than hidden in the consolidator.
        ws.cell(row=r, column=16, value=(
            f'=IF(${A["Driver"]}{r}="","",'
            f'IFERROR(INDEX(DriverCategory,MATCH(${A["Driver"]}{r},DriverList,0)),"?"))'))

        missing = "&".join(
            f'IF({test},", {word}","")' for test, word in [
                (f'${A["Division"]}{r}=""', "division"),
                (f'${A["Unit"]}{r}=""', "unit"),
                (f'${A["Job title"]}{r}=""', "job title"),
                (f'${A["Career Level"]}{r}=""', "career level"),
                (f'${A["Job Family"]}{r}=""', "job family"),
                (f'${A["Worker type"]}{r}=""', "worker type"),
                (f'N(${A["New Asks"]}{r})<=0', "the quarter split"),
                (f'${A["Driver"]}{r}=""', "driver"),
                (f'${A["Alternatives considered"]}{r}=""', "alternatives"),
                (f'AND(${A["Unit"]}{r}<>"",COUNTIF(UnitList,${A["Unit"]}{r})=0)',
                 "a unit that is not in your structure"),
            ])
        ws.cell(row=r, column=19, value=(
            f'=IF(COUNTA(${A["Division"]}{r}:${A["Job Family"]}{r})'
            f'+COUNTA(${A["Q1"]}{r}:${A["Q4"]}{r})=0,"",MID({missing},3,300))')
        ).font = S.f(9, color=S.RED_ALERT)
        ws.cell(row=r, column=20, value=(
            f'=IF(${A[MISSING_COL]}{r}="","",'
            f'COUNTIF(${A[MISSING_COL]}${first}:${A[MISSING_COL]}{r},"?*"))')
        ).font = S.SMALL
        for col in (10, 11, 16):
            ws.cell(row=r, column=col).font = S.BODY

    for col, list_name in [("Division", "DivisionList"), ("Unit", "UnitList"),
                           ("Career Level", "CareerLevels"),
                           ("Job Family", "JobFamilies"),
                           ("Worker type", "WorkerTypes"), ("Driver", "DriverList")]:
        dv = DataValidation(type="list", formula1=f"={list_name}", allow_blank=True,
                            showErrorMessage=True)
        dv.error = "Pick a value from the list."
        ws.add_data_validation(dv)
        dv.add(f"{A[col]}{first}:{A[col]}{last}")

    dvq = DataValidation(type="decimal", operator="between", formula1=0, formula2=50,
                         allow_blank=True, showErrorMessage=True)
    dvq.error = "A quarter takes between 0 and 50 positions."
    ws.add_data_validation(dvq)
    dvq.add(f'{A["Q1"]}{first}:{A["Q4"]}{last}')

    ws.conditional_formatting.add(
        f'{A["Category"]}{first}:{A["Category"]}{last}',
        CellIsRule(operator="equal", formula=['"Regulatory"'],
                   font=S.f(10, True, S.RED_ALERT)))
    ws.conditional_formatting.add(
        f'A{first}:{A["Issue no."]}{last}',
        FormulaRule(formula=[f'${A[MISSING_COL]}{first}<>""'],
                    fill=S.PatternFill("solid", fgColor="FDE7E9")))
    ws.auto_filter.ref = f'A{HEAD_ROW}:{A["Issue no."]}{last}'

    for label, col in [("AskRef", "Ref"), ("AskDivision", "Division"),
                       ("AskDepartment", "Department"), ("AskUnit", "Unit"),
                       ("AskSubUnit", "Sub-Unit"), ("AskTitle", "Job title"),
                       ("AskLevel", "Career Level"), ("AskFamily", "Job Family"),
                       ("AskWorkerType", "Worker type"), ("AskTotal", "New Asks"),
                       ("AskQ1", "Q1"), ("AskQ2", "Q2"), ("AskQ3", "Q3"),
                       ("AskQ4", "Q4"), ("AskCategory", "Category"),
                       ("AskDriver", "Driver"), ("AskProblem", MISSING_COL),
                       ("AskIssueNo", "Issue no.")]:
        _name(wb, SH_ASK, label, f"${A[col]}${first}:${A[col]}${last}")

    S.print_setup(ws, title_rows=f"{HEAD_ROW}:{HEAD_ROW}")
    return dict(first=first, last=last)


# ── Pricing ─────────────────────────────────────────────────────────────────
def _rate(idx: int, gosi: str) -> str:
    """The full-year loaded cost of one seat at career level `idx`."""
    return (f"(INDEX(LevelBasic,{idx})+INDEX(LevelHousing,{idx})"
            f"+INDEX(LevelTransport,{idx})"
            f"+INDEX(LevelBasic,{idx})*INDEX(LevelBonus,{idx})"
            f"+(INDEX(LevelBasic,{idx})+INDEX(LevelHousing,{idx}))*{gosi})")


def _cost_sum(qty: str, key_range: str, key: str, level_range: str,
              mandate_range: str | None = None) -> str:
    """Run-rate cost of `qty` where `key_range` matches `key`, by career level.

    One SUMIFS per level rather than a SUMPRODUCT lookup: SUMPRODUCT returns
    #VALUE! the moment a career level is blank, and blank is the normal state of
    that column until the bank fills it in. A term per level simply contributes
    nothing, which is why an unpriced seat reads as a dash rather than an error.
    """
    q = key.replace('"', '""')
    parts = []
    for i in range(len(R.LEVEL_COST)):
        idx = i + 1
        level = f"INDEX(LevelList,{idx})"
        if mandate_range:
            # A mandated seat is costed at the Saudi GOSI rate, the rest at the
            # non-Saudi one.
            for gosi, answer in [("GosiSaudi", "Yes"), ("GosiOther", "No")]:
                parts.append(
                    f'SUMIFS({qty},{key_range},"{q}",{level_range},{level},'
                    f'{mandate_range},"{answer}")*{_rate(idx, gosi)}')
        else:
            parts.append(f'SUMIFS({qty},{key_range},"{q}",{level_range},{level})'
                         f"*{_rate(idx, 'GosiSaudi')}")
    return "=" + "+".join(parts)


def _phased_cost(only: str | None = None) -> str:
    """Part-year cost of the asks: a Q1 start is paid four quarters, a Q4 one."""
    quarters = [only] if only else R.QUARTERS
    parts = []
    for q in quarters:
        weight = (4 - R.QUARTERS.index(q)) / 4
        for i in range(len(R.LEVEL_COST)):
            idx = i + 1
            parts.append(f"SUMIFS(Ask{q},AskLevel,INDEX(LevelList,{idx}))"
                         f"*{_rate(idx, 'GosiSaudi')}*{weight}")
    return "=" + "+".join(parts)


def _one_off_cost() -> str:
    parts = [f"SUMIFS(AskTotal,AskLevel,INDEX(LevelList,{i + 1}))"
             f"*INDEX(LevelOneOff,{i + 1})" for i in range(len(R.LEVEL_COST))]
    return "=" + "+".join(parts)


# ── 4. My position ──────────────────────────────────────────────────────────
def build_position(wb: Workbook, bank: R.Bank, group: str) -> dict:
    """Headcount and cost by division, and the three ceilings."""
    ws = wb.create_sheet(SH_POS)
    row = S.sheet_title(
        ws, "My position",
        "Your headcount and your cost by division, and where they land against "
        "your envelopes. Nothing here is typed in.")
    for col, w in zip("ABCDEFG", [34, 16, 12, 14, 16, 14, 44]):
        ws.column_dimensions[col].width = w

    # A group head, and anyone else reporting straight to the group, carries no
    # division. Without a row for them the division table quietly loses seats
    # and stops reconciling to the structure sheet.
    divisions = [(d, d) for d in bank.divisions(group)]
    if any(not s["division"] for s in bank.seats(group)):
        divisions.append(("Reporting to the group directly", ""))
    if not divisions:
        divisions = [(group, group)]
    heads = ["Division", "Current Capacity", "Exits", "New Asks", "New Capacity",
             "Change", ""]

    # ── Headcount ──────────────────────────────────────────────────────────
    ws.cell(row=row, column=1, value="Headcount").font = S.H1
    row += 1
    mini_head(ws, row, heads)
    hc_first = row + 1
    for i, (label, div) in enumerate(divisions):
        r = hc_first + i
        q = div.replace('"', '""')
        ws.cell(row=r, column=1, value=label).font = S.BODY
        ws.cell(row=r, column=2,
                value=f'=SUMIFS(SeatApproved,SeatDivision,"{q}")').number_format = S.FTE
        ws.cell(row=r, column=3,
                value=f'=SUMIFS(SeatExits,SeatDivision,"{q}")').number_format = S.FTE
        ws.cell(row=r, column=4,
                value=f'=SUMIFS(AskTotal,AskDivision,"{q}")').number_format = S.FTE
        ws.cell(row=r, column=5, value=f"=$B{r}-$C{r}+$D{r}").number_format = S.FTE
        ws.cell(row=r, column=6, value=f"=$E{r}-$B{r}").number_format = S.FTE
        for col in range(1, 7):
            ws.cell(row=r, column=col).border = S.BOX
    hc_last = hc_first + len(divisions) - 1
    hc_total = hc_last + 1
    _total_row(ws, hc_total, hc_first, hc_last, S.FTE)
    ws.conditional_formatting.add(
        f"F{hc_first}:F{hc_last}",
        CellIsRule(operator="lessThan", formula=["0"], font=S.f(10, color=S.OK_GREEN)))
    row = hc_total + 2

    # ── Cost ───────────────────────────────────────────────────────────────
    ws.cell(row=row, column=1, value="Cost (SAR '000, full-year run-rate)").font = S.H1
    ws.cell(row=row, column=7,
            value="Priced off the career-level rate card. A seat with no career "
                  "level cannot be priced and reads as a dash.").font = S.NOTE
    row += 1
    mini_head(ws, row, heads)
    cost_first = row + 1
    for i, (label, div) in enumerate(divisions):
        r = cost_first + i
        ws.cell(row=r, column=1, value=label).font = S.BODY
        ws.cell(row=r, column=2, value=_cost_sum(
            "SeatApproved", "SeatDivision", div, "SeatLevel", "SeatMandate")
        ).number_format = S.MONEY
        ws.cell(row=r, column=3, value=_cost_sum(
            "SeatExits", "SeatDivision", div, "SeatLevel", "SeatMandate")
        ).number_format = S.MONEY
        ws.cell(row=r, column=4, value=_cost_sum(
            "AskTotal", "AskDivision", div, "AskLevel")).number_format = S.MONEY
        ws.cell(row=r, column=5, value=f"=$B{r}-$C{r}+$D{r}").number_format = S.MONEY
        ws.cell(row=r, column=6, value=f"=$E{r}-$B{r}").number_format = S.MONEY
        for col in range(1, 7):
            ws.cell(row=r, column=col).border = S.BOX
    cost_last = cost_first + len(divisions) - 1
    cost_total = cost_last + 1
    _total_row(ws, cost_total, cost_first, cost_last, S.MONEY)
    row = cost_total + 2

    # The cash cost of the plan year, kept apart from the run-rate above.
    ws.cell(row=row, column=1,
            value=f"The {R.PLAN_YEAR} cash cost, separately").font = S.H1
    row += 1
    cash_row = row
    S.label_value(ws, row, "In-year cost of the new asks (SAR '000)",
                  _phased_cost(), S.MONEY, S.BODY,
                  note="Part-year: a Q1 start is paid four quarters, a Q4 start one.")
    row += 1
    one_off_row = row
    S.label_value(ws, row, "One-off cost of those hires (SAR '000)", _one_off_cost(),
                  S.MONEY, S.BODY, note="Recognised in the year of joining only.")
    row += 1
    released_row = row
    S.label_value(ws, row, "less cash released by people leaving (SAR '000)",
                  "=-SUM(OutCash)", S.MONEY, S.BODY,
                  note=f"From {SH_PIPE}. A seat is paid to the end of the "
                       "quarter its holder leaves.")
    row += 1
    net_row = row
    S.label_value(
        ws, row, f"Net {R.PLAN_YEAR} cash (SAR '000)",
        f"=$B${cash_row}+$B${one_off_row}+$B${released_row}", S.MONEY,
        S.f(10, True), note="What the plan year actually costs.")
    ws.cell(row=row, column=1).font = S.f(10, True, S.NAVY)
    S.band(ws, row, 2)
    row += 2

    # ── The three ceilings ─────────────────────────────────────────────────
    ws.cell(row=row, column=1, value="Against your envelopes").font = S.H1
    row += 1
    mini_head(ws, row, ["Test", "Your limit", "Your number", "Headroom", "Status",
                        "", ""])
    env_first = row + 1
    mandated = '=IFERROR(SUMIFS(SeatApproved,SeatMandate,"Yes")/SUM(SeatApproved),0)'
    tests = [
        ("Cost (SAR '000, run-rate)", "=CostEnvelope", f"=$F${cost_total}", S.MONEY,
         "The change in run-rate, not the whole pay bill."),
        ("Net establishment change", "=HeadEnvelope", f"=$F${hc_total}", S.FTE,
         "New asks less the seats you are giving up."),
        ("Mandated-seat share", "=SaudiTarget", mandated, S.PCT,
         "Seats you have marked as having to be Saudi, over the establishment."),
    ]
    r = env_first
    for label, limit, mine, fmt, why in tests:
        ws.cell(row=r, column=1, value=label).font = S.H2
        ws.cell(row=r, column=2, value=limit).font = S.LINK
        ws.cell(row=r, column=3, value=mine).font = S.BODY
        for col in (2, 3, 4):
            ws.cell(row=r, column=col).number_format = fmt
        if label.startswith("Mandated"):
            ws.cell(row=r, column=4, value=f"=$C{r}-$B{r}")
            ws.cell(row=r, column=5,
                    value=f'=IF($C{r}>=$B{r},"At or above target","Below target")')
        else:
            ws.cell(row=r, column=4, value=f"=$B{r}-$C{r}")
            ws.cell(row=r, column=5,
                    value=f'=IF($D{r}>=0,"Within envelope","Over envelope")')
        ws.cell(row=r, column=7, value=why).font = S.SMALL
        ws.cell(row=r, column=7).alignment = S.WRAP
        for col in range(1, 6):
            ws.cell(row=r, column=col).border = S.BOX
        r += 1
    env_last = r - 1
    # Named, so the check sheet can read them without naming this sheet.
    for i, stem in enumerate(["Cost", "Head", "Mandate"]):
        _name(wb, SH_POS, f"{stem}Limit", f"$B${env_first + i}")
        _name(wb, SH_POS, f"{stem}Mine", f"$C${env_first + i}")
    ws.conditional_formatting.add(
        f"E{env_first}:E{env_last}",
        FormulaRule(
            formula=[f'OR($E{env_first}="Over envelope",$E{env_first}="Below target")'],
            font=S.f(10, True, S.RED_ALERT)))
    ws.conditional_formatting.add(
        f"E{env_first}:E{env_last}",
        FormulaRule(
            formula=[f'OR($E{env_first}="Within envelope",$E{env_first}="At or above target")'],
            font=S.f(10, True, S.OK_GREEN)))
    row = env_last + 2

    # ── Where the ask goes ─────────────────────────────────────────────────
    ws.cell(row=row, column=1, value="What the ranking rule funds first").font = S.H1
    ws.cell(row=row, column=7,
            value="Cut order runs bottom-up: BAU goes first, regulatory last.").font = S.NOTE
    row += 1
    mini_head(ws, row, ["Priority", "New Asks", "Run-rate cost", "Cumulative cost",
                        "Inside envelope?", "", ""])
    cat_first = row + 1
    for i, (name, rank, why) in enumerate(R.RANK_CATEGORIES):
        r = cat_first + i
        ws.cell(row=r, column=1, value=f"{rank}. {name}").font = S.BODY
        ws.cell(row=r, column=2,
                value=f'=SUMIFS(AskTotal,AskCategory,"{name}")').number_format = S.FTE
        ws.cell(row=r, column=3, value=_cost_sum(
            "AskTotal", "AskCategory", name, "AskLevel")).number_format = S.MONEY
        ws.cell(row=r, column=4,
                value=f"=SUM($C${cat_first}:$C{r})").number_format = S.MONEY
        ws.cell(row=r, column=5, value=f'=IF($D{r}<=CostEnvelope,"Yes","No")')
        ws.cell(row=r, column=7, value=why).font = S.SMALL
        ws.cell(row=r, column=7).alignment = S.WRAP
        for col in range(1, 6):
            ws.cell(row=r, column=col).border = S.BOX
    cat_last = cat_first + len(R.RANK_CATEGORIES) - 1
    ws.conditional_formatting.add(
        f"E{cat_first}:E{cat_last}",
        CellIsRule(operator="equal", formula=['"No"'], font=S.f(10, True, S.RED_ALERT)))
    row = cat_last + 2

    # ── Phasing ────────────────────────────────────────────────────────────
    ws.cell(row=row, column=1, value="When the new capacity starts").font = S.H1
    row += 1
    mini_head(ws, row, ["Start quarter", "New Asks", "Share of the year paid",
                        f"{R.PLAN_YEAR} cash cost", "", "", ""])
    q_first = row + 1
    for i, q in enumerate(R.QUARTERS):
        r = q_first + i
        ws.cell(row=r, column=1, value=q).font = S.BODY
        ws.cell(row=r, column=2, value=f"=SUM(Ask{q})").number_format = S.FTE
        ws.cell(row=r, column=3, value=(4 - i) / 4).number_format = S.PCT0
        ws.cell(row=r, column=4, value=_phased_cost(only=q)).number_format = S.MONEY
        for col in range(1, 5):
            ws.cell(row=r, column=col).border = S.BOX
    q_last = q_first + len(R.QUARTERS) - 1

    _position_charts(ws, cat_first, cat_last, q_first, q_last, q_last + 3)
    S.print_setup(ws, landscape=False)
    return dict(hc_first=hc_first, hc_last=hc_last, hc_total=hc_total,
                cost_first=cost_first, cost_last=cost_last, cost_total=cost_total,
                cash_row=cash_row, one_off_row=one_off_row,
                released_row=released_row, net_row=net_row,
                cost_test=env_first, head_test=env_first + 1,
                mandate_test=env_first + 2,
                cat_first=cat_first, cat_last=cat_last,
                q_first=q_first, q_last=q_last, divisions=divisions)


def _total_row(ws, row: int, first: int, last: int, fmt: str) -> None:
    ws.cell(row=row, column=1, value="Total").font = S.f(10, True, S.NAVY)
    for col in range(2, 7):
        letter = get_column_letter(col)
        c = ws.cell(row=row, column=col, value=f"=SUM({letter}{first}:{letter}{last})")
        c.number_format = fmt
        c.font = S.f(10, True)
    S.band(ws, row, 6)


def _position_charts(ws, cat_first, cat_last, q_first, q_last, row) -> None:
    """Two native charts, so they move when the numbers do."""
    bar = BarChart()
    bar.type = "bar"
    bar.title = f"{R.PLAN_YEAR} run-rate cost by priority (SAR '000)"
    bar.legend = None
    bar.height, bar.width = 8, 16
    bar.add_data(Reference(ws, min_col=3, min_row=cat_first, max_row=cat_last),
                 titles_from_data=False)
    bar.set_categories(Reference(ws, min_col=1, min_row=cat_first, max_row=cat_last))
    bar.series[0].graphicalProperties.solidFill = S.NAVY
    bar.series[0].graphicalProperties.line.noFill = True
    bar.x_axis.scaling.orientation = "maxMin"
    bar.y_axis.crosses = "max"
    ws.add_chart(bar, f"A{row}")

    col = BarChart()
    col.type = "col"
    col.title = "New capacity by start quarter"
    col.legend = None
    col.height, col.width = 8, 12
    col.add_data(Reference(ws, min_col=2, min_row=q_first, max_row=q_last),
                 titles_from_data=False)
    col.set_categories(Reference(ws, min_col=1, min_row=q_first, max_row=q_last))
    col.series[0].graphicalProperties.solidFill = "3E7CB1"
    col.series[0].graphicalProperties.line.noFill = True
    ws.add_chart(col, f"E{row}")


# ── The return block ────────────────────────────────────────────────────────
def build_return_block(wb: Workbook, group: str, pos: dict) -> dict:
    """A compact table on the position sheet that the centre copies in one go.

    It carries what only this file knows: what the group has today, what it is
    giving up, and how many of its seats have to be Saudi. It replaces the four
    numbers the centre used to read off each return and type by hand.
    """
    ws = wb[SH_POS]
    row = pos["q_last"] + 22          # clear of the charts
    ws.cell(row=row, column=1, value="For the capacity team").font = S.H1
    ws.cell(row=row, column=7,
            value="Copy these rows into the consolidator's return area. Nothing "
                  "to fill in.").font = S.NOTE
    row += 1
    mini_head(ws, row, ["Division", "Current Capacity", "Seats released",
                        "New Asks", "New Capacity", "Mandated seats",
                        "Run-rate cost", f"{R.PLAN_YEAR} cash released"])
    first = row + 1
    for i, (_, div) in enumerate(pos["divisions"]):
        r = first + i
        q = div.replace('"', '""')
        hc = pos["hc_first"] + i
        cost = pos["cost_first"] + i
        ws.cell(row=r, column=1, value=f"=$A{hc}").font = S.LINK
        for col, src in [(2, "B"), (3, "C"), (4, "D"), (5, "E")]:
            ws.cell(row=r, column=col, value=f"=${src}{hc}").number_format = S.FTE
        ws.cell(row=r, column=6, value=(
            f'=SUMIFS(SeatApproved,SeatDivision,"{q}",SeatMandate,"Yes")')
        ).number_format = S.FTE
        ws.cell(row=r, column=7, value=f"=$E{cost}").number_format = S.MONEY
        ws.cell(row=r, column=8, value=(
            f'=SUMIFS(OutCash,OutDivision,"{q}")')).number_format = S.MONEY
        for col in range(1, 9):
            ws.cell(row=r, column=col).border = S.BOX
    last = first + len(pos["divisions"]) - 1
    return dict(first=first, last=last)


# ── 5. Check & submit ───────────────────────────────────────────────────────
def build_check(wb: Workbook, group: str) -> dict:
    """Everything still missing, named by row, and the one switch that says the
    file is ready to go back."""
    ws = wb.create_sheet(SH_CHK)
    row = S.sheet_title(
        ws, "Check & submit",
        "Work down this sheet until every blocking check reads OK, then set the "
        "state at the bottom to Submitted and return the file.")
    for col, w in zip("ABCD", [56, 12, 14, 62]):
        ws.column_dimensions[col].width = w

    ws.cell(row=row, column=1, value="Blocking — these must be clear").font = S.H1
    row += 1
    mini_head(ws, row, ["Check", "Count", "Status", "What to do"])
    first = row + 1
    blocking = [
        ("Positions with something missing", '=COUNTIF(SeatProblem,"?*")',
         f"{SH_CAP} spells out what each row is missing in its last column. "
         "Filter on it to find them."),
        ("Positions with no career level",
         '=SUMPRODUCT((SeatTitle<>"")*(SeatLevel=""))',
         f"{SH_CAP}. Until every seat has a career level, none of the cost on "
         f"{SH_POS} can be worked out and it reads as a dash."),
        ("Jobs with no capacity direction",
         '=SUMPRODUCT((SeatTitle<>"")*(SeatDirection=""))',
         f"{SH_CAP}. Say what you intend to do with each job: Grow, Hold or "
         "Reduce."),
        ("Jobs marked Reduce without saying how many seats go",
         f'=SUMPRODUCT((SeatDirection="{R.REDUCE_DIRECTION}")*(N(SeatSlated)<=0))',
         f"{SH_CAP}. A Reduce with no number changes nothing. If the row has "
         "four seats and two are going, put 2."),
        ("Rows giving up seats but not marked Reduce",
         f'=SUMPRODUCT((N(SeatSlated)>0)*(SeatDirection<>"{R.REDUCE_DIRECTION}"))',
         f"{SH_CAP}. The number is ignored unless the direction says Reduce, so "
         "either set the direction or clear the number."),
        ("Rows giving up more seats than they have",
         "=SUMPRODUCT((N(SeatSlated)>N(SeatApproved))*1)",
         f"{SH_CAP}. You cannot release more than the row's approved headcount."),
        ("Departures with something missing", '=COUNTIF(OutProblem,"?*")',
         f"{SH_PIPE} spells out what each row is missing in its last column."),
        # Counted from the departure side and compared against the total the
        # capacity sheet is reducing for that unit and job. The same job can
        # appear on several rows there — different sub-units, different worker
        # types — so the comparison has to be against their sum, not row by row.
        ("Seats surrendered beyond what the job is reducing",
         f'=SUMPRODUCT((OutDisposition="{R.SURRENDER}")*'
         f'(COUNTIFS(OutUnit,OutUnit,OutTitle,OutTitle,'
         f'OutDisposition,"{R.SURRENDER}")'
         f">SUMIFS(SeatSlated,SeatUnit,OutUnit,SeatTitle,OutTitle)))",
         f"A seat surrendered on {SH_PIPE} has to be counted in the Reduce "
         f"column on {SH_CAP} too. Fewer surrenders than the Reduce count is "
         "fine — the balance is vacancies you are not refilling."),
        ("Ask rows with something missing", '=COUNTIF(AskProblem,"?*")',
         f"{SH_ASK} lists what each row is missing in its last two columns."),
        ("Ask rows with nothing in any quarter",
         '=SUMPRODUCT((AskTitle<>"")*(N(AskTotal)<=0))',
         f"{SH_ASK}. Put the position in the quarter you want it to start."),
        ("Ask rows naming a unit that is not in your structure",
         '=SUMPRODUCT((AskUnit<>"")*(COUNTIF(UnitList,AskUnit)=0))',
         f"{SH_ASK}. Pick the unit from the list — a unit that does not exist "
         "cannot be costed or consolidated."),
    ]
    r = _check_block(ws, first, blocking, "Fix")
    block_last = r - 1

    row = block_last + 2
    ws.cell(row=row, column=1, value="Worth a look — these do not block you").font = S.H1
    row += 1
    mini_head(ws, row, ["Check", "Count", "Status", "What to do"])
    warn_first = row + 1
    warnings = [
        ("Run-rate cost above your envelope",
         "=IF(CostMine>CostLimit,1,0)",
         "Move start quarters later, give up more seats, or say why the "
         "envelope has to move."),
        ("Net establishment change above your envelope",
         "=IF(HeadMine>HeadLimit,1,0)",
         "Convert, insource or reduce somewhere else to pay for it."),
        ("Mandated-seat share below your target",
         "=IF(MandateMine<MandateLimit,1,0)",
         f"Review which seats have to be Saudi on {SH_CAP}, or explain the gap "
         "when you submit."),
    ]
    r = _check_block(ws, warn_first, warnings, "Review")
    warn_last = r - 1

    for ref in (f"C{first}:C{block_last}", f"C{warn_first}:C{warn_last}"):
        for word, colour in [("OK", S.OK_GREEN), ("Fix", S.RED_ALERT),
                             ("Review", S.AMBER)]:
            ws.conditional_formatting.add(
                ref, CellIsRule(operator="equal", formula=[f'"{word}"'],
                                font=S.f(10, True, colour)))

    # The rows themselves, named rather than counted.
    row = warn_last + 2
    ws.cell(row=row, column=1, value="The ask rows that need attention").font = S.H1
    ws.cell(row=row, column=4,
            value=f"The first {PROBLEM_ROWS}. Clear these and the rest "
                  "appear.").font = S.NOTE
    row += 1
    mini_head(ws, row, ["Ask ref", "Unit", "Job title", "What is missing"])
    prob_first = row + 1
    for i in range(PROBLEM_ROWS):
        r = prob_first + i
        match = f"MATCH({i + 1},AskIssueNo,0)"
        for col, src in [(1, "AskRef"), (2, "AskUnit"), (3, "AskTitle"),
                         (4, "AskProblem")]:
            pick = f"INDEX({src},{match})"
            c = ws.cell(row=r, column=col,
                        value=f'=IFERROR(IF({pick}=0,"",{pick}),"")')
            c.font = S.f(9, color=S.RED_ALERT) if col == 4 else S.BODY
            c.border = S.BOX
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
    for label in ("Prepared by", "Contact", "Date"):
        S.input_cell(S.label_value(ws, row, label, None))
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
    for word, colour in [("Yes", S.OK_GREEN), ("No", S.RED_ALERT)]:
        ws.conditional_formatting.add(
            f"B{ready_row}",
            CellIsRule(operator="equal", formula=[f'"{word}"'],
                       font=S.f(12, True, colour)))

    row += 2
    S.note_line(ws, row,
                "Return the file to the capacity team with the state set to "
                "Submitted. The centre prices it again on the same rate card, "
                "challenges it line by line where it has to, and sends back the "
                f"approved {R.PLAN_YEAR} establishment for {group}.", cols=4)
    S.print_setup(ws, landscape=False)
    return dict(ready_row=ready_row, state_row=state_row,
                block_first=first, block_last=block_last,
                warn_first=warn_first, warn_last=warn_last)


def _check_block(ws, first: int, checks, bad_word: str) -> int:
    r = first
    for label, formula, fix in checks:
        ws.cell(row=r, column=1, value=label).font = S.BODY
        ws.cell(row=r, column=2, value=formula).number_format = S.COUNT
        ws.cell(row=r, column=3,
                value=f'=IF($B{r}=0,"OK","{bad_word}")').font = S.f(10, True)
        ws.cell(row=r, column=3).alignment = S.CENTRE
        ws.cell(row=r, column=4, value=fix).font = S.SMALL
        ws.cell(row=r, column=4).alignment = S.WRAP
        ws.row_dimensions[r].height = 26
        for col in range(1, 5):
            ws.cell(row=r, column=col).border = S.BOX
        r += 1
    return r


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
    pipe = build_pipeline(wb, bank, group)
    ask = build_asks(wb, bank, group)
    pos = build_position(wb, bank, group)
    ret = build_return_block(wb, group, pos)
    chk = build_check(wb, group)
    build_glossary(wb, group)
    build_ref(wb, bank, group)

    for ws in wb.worksheets:
        if ws.title not in UNPROTECTED:
            S.protect(ws)
    wb.properties.title = f"{R.PLAN_YEAR} Capacity Exercise - {group}"
    wb.properties.creator = "Capacity exercise toolkit"
    wb.save(path)
    return dict(path=str(path), group=group, cap=cap, pipe=pipe, ask=ask,
                pos=pos, ret=ret, chk=chk,
                cap_cols=C, ask_cols=A, pipe_cols=P)


if __name__ == "__main__":
    import sys

    bank = R.Bank()
    group = sys.argv[1] if len(sys.argv) > 1 else bank.groups[0]
    out = sys.argv[2] if len(sys.argv) > 2 else "capacity/dist/2027-Capacity-Template.xlsx"
    print(build_template(group, out, bank)["path"])
