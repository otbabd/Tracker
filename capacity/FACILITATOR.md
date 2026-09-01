# Running the 2027 capacity exercise

For whoever owns the exercise centrally. It assumes you have the three things in
`capacity/dist/` and nothing else: twelve group templates, one worked example,
and the consolidator.

## What you are actually running

Two decisions come out of the same submission. The **manpower budget** asks what
2027 costs; the **workforce plan** asks what the bank will be able to do. The
exercise is built so a group answers once and both questions are served, which
is why every ask line carries a driver and a quarter as well as a grade.

Nothing runs on macros. Every file opens, recalculates and prints anywhere,
including on a locked-down laptop with a security prompt disabled.

## The calendar

| When | What | Who |
|---|---|---|
| Week 1 | Set the envelopes, issue the templates and the worked example | You |
| Weeks 2–4 | Groups fill in and return their template | Group heads |
| Week 5 | Paste, check, price centrally, prepare the challenge pack | You |
| Week 6 | Challenge meetings, one per group | You and each group |
| Week 7 | Scenario meeting; the case that gets approved | ExCom |
| Week 8 | Approved establishment out to Finance, recruitment and the groups | You |

Three weeks with the file is the shortest that works. Groups need one week to
argue internally before they will type anything.

## Step 1 — before you send anything

Open the consolidator, sheet **1. Envelopes**, and set:

1. **The bank ceiling** — cost, net establishment growth, Saudization target.
2. **Each group's share of it.** The shipped split is illustrative (six per cent
   of the pay bill, five per cent of the establishment, two points above today's
   Saudization). Replace it with whatever Finance and the CEO have agreed. The
   sheet tells you underneath whether the twelve allocations still fit inside the
   bank ceiling — if they do not, you are asking the groups to fail.

Then open the hidden **Ref** sheet in each template and replace the **grade cost
table** with Finance's own rates. This is the single most important edit in the
whole exercise: every number a group sees, and every number you challenge them
on, comes off that table. Basic, housing, transport, target bonus and employer
GOSI are separate columns so a rate can be argued with on its own.

Send each group **its own file only** — a group cannot see another group's
headcount or cost, and that is deliberate — plus the worked example, which is
the fastest briefing document you have.

## Step 2 — while they are filling it in

The template answers most questions itself. The three that still come:

- *"Can I ask for a position in a unit that does not exist yet?"* Yes. Add the
  unit on sheet 4, and use its `NEW-nn` ID as the unit on sheet 5.
- *"Do I have to re-confirm vacancies I already have?"* Yes. Anything not
  confirmed on sheet 3 lapses and will not carry into 2027. This is where most
  of the quiet establishment creep gets cleaned up.
- *"The cost looks wrong."* It is the loaded cost — basic, housing, transport,
  employer GOSI and target bonus, in SAR thousands — not the salary. It is the
  same rate you will price them at, which is the point.

A group is finished when sheet 7 says **Ready to submit: Yes**. The file will not
let them set the state to Submitted before that.

## Step 3 — receiving and pasting

For each returned file:

1. Open the group's sheet **5. Capacity asks**, select **A6:N305**, copy.
2. In the consolidator, sheet **2. Group submissions**, find that group's band —
   the row range is printed on the Envelopes sheet, column **Paste into** — and
   **paste values** into column B of the first row of the band.
3. Read across to column **W**. Anything with text in it is a line you cannot
   price, and the reason is written out. Go back to the group before you go
   further.
4. On sheet 1, type the four numbers you read off their file: their attrition
   rate (sheet 3), vacancies lapsed (sheet 3, the ones answered "No"), positions
   released by closures and merges (sheet 4), and set the state to Submitted.

The band is exactly the size of the template, so a paste cannot spill into the
next group. Everything from column P rightwards is recomputed centrally: the
group's own cost column is not carried over, on purpose.

## Step 4 — the challenge meeting

Sheet **3. Challenge**, filtered to the group. Requested is on the left, approved
on the right, and only the approved side rolls forward.

Set a **decision** on every line. Only *Approve fewer* needs a number typed;
*Decline* is zero, *Defer* keeps the position and moves the quarter. Type the
reason as you go — it is the thing you will be asked for three months later, and
nobody reconstructs it afterwards.

Two moves are worth having ready before you walk in:

- **Move the start quarter.** A Q1 start costs four quarters, a Q4 start one. It
  is the cheapest concession a group can make and it usually costs them nothing
  they care about.
- **Change the workforce type.** Insourced and outsourced cover come off the same
  rate table; converting a permanent ask for a genuinely temporary peak is often
  the honest answer.

## Step 5 — the scenario meeting

Sheet **4. Scenarios**. Four cases, six levers each, computed live over the whole
book — you can change a lever in the room and the page is right again.

The ranking rule funds regulatory work first and discretionary work last, so a
tighter envelope shows you exactly which lines fall out and in what order. It is
a starting point, not a decision; the Challenge sheet is where a human overrides
it.

One thing to say out loud before anyone reads the numbers: **the cut is made
against in-year cost**. A case that pushes every start back a quarter funds more
positions for less money in 2027 while committing almost the same run-rate into
2028. Read the cost row and the run-rate row together, or the meeting will
approve a cash saving and a permanent cost at the same time.

## Step 6 — sending the answer back

- **6. Executive summary** — the one page for the committee.
- **8. Group pages** — print the sheet and every group gets its own page: what it
  asked for, what was approved, where it landed against its envelope, and the
  split by priority and quarter.
- **7. Approved establishment** — the flat list for Finance and recruitment. It
  fills itself from the decisions; there is nothing to export.

## Reading the dashboard

| Panel | What it answers | What to look for |
|---|---|---|
| Establishment bridge | Where 2027's headcount came from | A closing number that moves a long way on approved growth alone means the lapsed vacancies and closures were not real |
| Groups against envelopes | Who is over, and by how much | A group at 400% of envelope has not had the conversation with its own finance partner |
| Demand by driver | What the bank is buying | Large "not funded" against regulatory drivers is the one thing to escalate |
| Cost phasing | The shape of the year | A Q1-heavy shape is a cash problem; a Q4-heavy one is a delivery problem |

The bridge counts **approved seats, not people**. Replacements and conversions
keep a seat that already exists, so they do not move it — they are listed
underneath so nobody thinks they were lost.

## Running it again next year

The toolkit is built to be re-run, not rebuilt:

1. In `capacity/build/refdata.py`, change `PLAN_YEAR`. Every year label in all
   three workbooks derives from it.
2. Replace the grade cost table with next year's rates.
3. Point `POSITIONS_CSV` and `UNITS_CSV` at a fresh export from the org tool, so
   the baseline is this year's approved establishment rather than last year's.
4. `python3 capacity/build/make.py` rebuilds all fourteen files and
   recalculates each one.
5. `python3 capacity/tests/run_all.py` proves the arithmetic still holds.

## Known limits — say these out loud rather than discovering them

- **The rates are illustrative until Finance replaces them.** Every cost in every
  file is wrong until step 1 is done.
- **The baseline is the org tool's sample export.** Swap in the real HRIS extract
  before the exercise runs for real.
- **300 ask rows per group, 800 approved lines.** Generous, but finite; the
  consolidator's bands are sized to the template exactly.
- **Four numbers per group are typed, not pasted** — attrition, vacancies lapsed,
  positions released, state. Everything else comes across in the paste.
- **Productivity is a bank default with a per-unit override.** A group that types
  nothing gets the default; the scenario multiplier then asks what happens if
  only part of it lands. A multiplier of 1.0 takes the groups at their word.
- **Saudization is tested on intended basis, not on offers made.** It is a
  planning number, and it will move when recruitment meets the market.
