# Running the 2027 capacity exercise

For whoever owns the exercise centrally. It assumes you have the three things in
`capacity/dist/` and nothing else: twelve group templates, one worked example,
and the consolidator.

## What you are actually running

Two decisions come out of the same submission. The **manpower budget** asks what
2027 costs; the **workforce plan** asks what the bank will be able to do. The
exercise is built so a group answers once and both questions are served, which
is why every ask line carries a driver and a quarter as well as a career level.

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

1. **The bank ceiling** — run-rate cost, net establishment growth, and the
   mandated-seat target.
2. **Each group's share of it.** The shipped split is illustrative (six per cent
   of the pay bill, five per cent of the establishment, two points above today's
   mandated share). Replace it with whatever Finance and the CEO have agreed. The
   sheet tells you underneath whether the twelve allocations still fit inside the
   bank ceiling — if they do not, you are asking the groups to fail.

Then open the hidden **Ref** sheet in each template and replace the **rate card**
with Finance's own rates, and the **career-level ladder** with the bank's own.
This is the single most important edit in the whole exercise: every number a
group sees, and every number you challenge them on, comes off that card. Basic,
housing, transport, target bonus and employer GOSI are separate columns so a rate
can be argued with on its own.

Career level is a property of the job, not of the grade, so the org export cannot
supply it. Either add a `Career Level` column to the export before the templates
are generated, or accept that each group fills it in — but until it is filled,
**every cost on a group's own dashboard reads as a dash**, and its check sheet
says so. Nothing is wrong; nothing can be priced yet.

Send each group **its own file only** — a group cannot see another group's
headcount or cost, and that is deliberate — plus the worked example, which is
the fastest briefing document you have.

## Step 2 — while they are filling it in

The template answers most questions itself. The three that still come:

- *"How do I give up a seat?"* Set its Capacity Direction to **Exit** on
  `2. Current capacity`. That is the only place a seat leaves the establishment,
  and a vacancy you no longer need is exactly what it is for. **Reduce** keeps
  the seat and puts it on the mid-year watch list; it moves no numbers.
- *"Do I type the total or the quarters?"* The quarters. New Asks adds itself up,
  so the two can never disagree.
- *"What is Nationality Mandate?"* A property of the seat, not of the person: does
  this role have to be filled by a Saudi national? It is the floor the bank
  cannot go below.
- *"The cost looks wrong."* It is the loaded cost — basic, housing, transport,
  employer GOSI and target bonus, in SAR thousands — not the salary. It is the
  same rate you will price them at, which is the point.

A group is finished when `5. Check & submit` says **Ready to submit: Yes**. The file will not
let them set the state to Submitted before that.

## Step 3 — receiving and pasting

For each returned file:

1. Open the group's sheet **3. Capacity asks**, select **A6:R205**, copy.
2. In the consolidator, sheet **2. Group asks**, find that group's band — the row
   range is printed on the Envelopes sheet, column **Paste asks into** — and
   **paste values** into column B of the first row of the band.
3. Do the same with the small block at the foot of the group's **4. My position**
   sheet, into **3. Group returns**. That block is where the bridge gets its
   exits and where the mandated-seat share comes from.
4. Read the **Problem** column on the asks sheet. Anything with text in it is a
   line you cannot price, and the reason is written out. Go back to the group
   before you go further.
5. On **1. Envelopes**, set their attrition rate and mark the state Submitted.
   That is the only typing left; everything else arrives in the two pastes.

The band is exactly the size of the template, so a paste cannot spill into the
next group. Everything from the Category column rightwards is recomputed
centrally on the bank's rate card, whatever the group's own file said.

## Step 4 — the challenge meeting

Sheet **4. Challenge**, filtered to the group. Requested is on the left, approved
on the right, and only the approved side rolls forward.

Set a **decision** on every line. Only *Approve fewer* needs a number typed;
*Decline* is zero, *Defer* keeps the position and moves the quarter. Type the
reason as you go — it is the thing you will be asked for three months later, and
nobody reconstructs it afterwards.

Two moves are worth having ready before you walk in:

- **Move the start quarter.** A Q1 start costs four quarters, a Q4 start one. It
  is the cheapest concession a group can make and it usually costs them nothing
  they care about.
- **Change the worker type.** Insourced and outsourced cover come off the same
  rate card; converting a permanent ask for a genuinely temporary peak is often
  the honest answer.
- **Ask what they are giving up.** A group with no seat marked Exit has not done
  the other half of the exercise, and the Exits column on the Envelopes sheet
  says so at a glance.

## Step 5 — the scenario meeting

Sheet **5. Scenarios**. Four cases, six levers each, computed live over the whole
book — you can change a lever in the room and the page is right again.

The ranking rule funds regulatory work first and discretionary work last, so a
tighter envelope shows you exactly which lines fall out and in what order. It is
a starting point, not a decision; the Challenge sheet is where a human overrides
it.

One thing to say out loud before anyone reads the numbers: **the cut is made
against run-rate cost, not cash**. Pushing every start back a quarter therefore
buys cash in 2027 and not one extra position — the run-rate row does not move,
and neither does the headcount. Read the run-rate row and the cash row together;
only one of them is a saving.

## Step 6 — sending the answer back

- **7. Executive summary** — the one page for the committee.
- **9. Group pages** — print the sheet and every group gets its own page: what it
  asked for, what was approved, where it landed against its envelope, and the
  split by priority and quarter.
- **8. Approved establishment** — the flat list for Finance and recruitment. It
  fills itself from the decisions; there is nothing to export.

## Reading the dashboard

| Panel | What it answers | What to look for |
|---|---|---|
| Establishment bridge | Where 2027's headcount came from | A closing number that moves on approved growth alone means nobody marked anything Exit — the giving-up half of the exercise did not happen |
| Groups against envelopes | Who is over, and by how much | A group at 400% of envelope has not had the conversation with its own finance partner |
| Demand by driver | What the bank is buying | Large "not funded" against regulatory drivers is the one thing to escalate |
| Cost phasing | The shape of the year | A Q1-heavy shape is a cash problem; a Q4-heavy one is a delivery problem |

The bridge counts **approved seats, not people**. A seat only leaves the
establishment if a group marked it Exit, which is why the giving-up half of the
exercise matters as much as the asking half.

## Running it again next year

The toolkit is built to be re-run, not rebuilt:

1. In `capacity/build/refdata.py`, change `PLAN_YEAR`. Every year label in all
   three workbooks derives from it.
2. Replace the rate card with next year's rates, and the career-level ladder if it has moved.
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
- **Two pastes per group, and one typed number** — the ask block, the return
  block, and the attrition rate. Everything else comes across in the pastes.
- **Productivity is a bank default with a per-unit override.** A group that types
  nothing gets the default; the scenario multiplier then asks what happens if
  only part of it lands. A multiplier of 1.0 takes the groups at their word.
- **The mandated-seat share is tested on today's seats only.** A new position
  carries no mandate answer, so the share drifts down as the bank grows. That is
  the point of watching it, not a fault in the arithmetic.
- **The scenario cut is made against run-rate cost, not cash.** Pushing starts
  back a quarter buys cash in the plan year and not a single extra position.
