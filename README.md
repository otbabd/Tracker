# Org Chart

A single HTML file that turns a position export into an interactive organisation
chart. Open it, drop your file in, and the org is on screen.

```
org-chart.html
```

That is the whole tool. Double-click it, put it on an internal share, or email it
to a colleague — there is no server, no install, no build step and no internet
connection involved. Your file is read inside your own browser and never leaves
your machine.

`sample-org.csv` is synthetic data — 2,567 positions in a bank shaped like a
Saudi one, twelve groups deep to section level — if you want to try it before
pointing it at anything real; `sample-units.csv` is the matching org unit list
and `sample-courses.csv` the mandatory-training list. Nothing in it is real: the
names, the reporting lines, the deliberately broken rows and the deliberate
disagreements between the structure and the reporting line are all generated.

Load the positions, then add the unit list with the **＋ Add unit list** button in
the org-unit view — or put all three on separate tabs of one workbook and they
are picked up together.

The **Try it with sample data** button needs no files at all and carries the
same shape in miniature — the full ladder, branches, job attributes, a unit list
and a course list.

---

## Two views of the same file

A switch in the toolbar changes what a box means. The file is loaded once and
the filters carry across.

**Org units** — the view it opens on. One box per organisational unit: its name,
the most senior position inside it and who holds it, its headcount, vacancies and
FTE, its function type and how many sub-units it holds, with the mix of work it
does as a colour strip along the bottom. Four lines, deliberately — the shape of
it (job layers, average span, managers against individual contributors) is a
click away in the detail panel and a sortable column in **Compare**, rather than
three numbers competing for a row on every box on screen. It opens as many levels
as fit across the screen legibly — for a twelve-group bank that is the groups
themselves — and the rest is a click away.

**Positions** — one box per seat, reached from a unit through *Show these
positions* or the switch. The job title leads, the person in it sits underneath,
and a vacancy is a normal state of a position rather than a gap in the data.
Boxes are joined by reporting lines, taken from Manager ID.

A file with no structural columns has nothing to draw, so it opens on positions
instead.

### The ladder

The org view nests down the levels a bank actually uses, in this order:

```
Group → Division → Department → Unit → Sub-unit → Section
```

A group is the top block under the CEO, named after its discipline and headed by
a C-level officer: **Human Resources Group** under the Chief Human Capital
Officer, holding its divisions, each of those holding its departments.

Whichever of the six your file carries become the nesting, in that order. A
column with the same value on every row is skipped — a single-value level is a
redundant box, which is why a legal entity that never varies belongs outside the
ladder rather than on its top rung.

**Every role sits at its own rung, and the ladder ends there.** The CHCO's row
names the group and stops; a division head names the division and stops. A
position is placed at the last rung it fills rather than pushed into a phantom
unit beneath it — the one exception being a position that fills no rung at all,
which goes to *Unspecified* so the units still add up to the whole.

**Branches run across the ladder, not inside it.** A `Branch` column is a full
dimension — colour, filter, nest — but is never picked as a default level, so
the branch network can be looked at on its own (nest by Branch alone) without
disturbing the head-office hierarchy.

### Which hierarchy is the authority

**Org first.** Supply an org unit list and it becomes the structure: the chart is
built on the units you have approved, parented the way the list says, and each
position is tagged into the deepest declared unit its columns name. Below the
deepest declared unit the ladder columns still nest — the units, sub-units and
sections stay on screen, marked as *not declared* rather than hidden.

That matters because of what it makes visible. A unit that exists only as a tag
— someone typed a department name into an export and nobody ever approved it —
used to become a box indistinguishable from the real ones. Now it is drawn with
a red dashed outline, labelled *not in the approved structure*, and listed in
**Reconcile** with its headcount and the head running it.

With no unit list, the hierarchy comes from the columns as before. The **Units…**
panel lets you switch between the two deliberately.

### Reconcile

Six ways the approved structure and the reporting line can disagree, counted in
the toolbar and listed in a sheet under the chart. Each row clicks through to the
unit or the position it names, and the CSV button exports the list.

| Finding | What it means |
|---|---|
| **Not in the approved structure** | Positions are tagged to a unit the org unit list does not declare |
| **Declared, nobody in it** | A unit in the list with no positions mapped to it |
| **Declared parent disagrees** | The list puts the unit in one place, the position columns in another |
| **Head reports outside the unit** | The most senior position answers to neither its own unit nor its parent |
| **Reporting line skips a level** | The head reports past the parent unit to something above it |
| **Managed from another unit** | Staff whose manager sits neither in their unit nor anywhere above it |

Two things keep the counts meaningful. **A manager in a unit above yours is
normal**, not a finding — in a ladder where every rung has its own head, a team
lead in a sub-unit manages the staff sitting in a section beneath. And **only a
unit somebody actually runs has a head worth checking**: a unit with sub-units,
or whose top position manages people inside it. The most senior of three people
in a section is whoever the sort landed on, not an office.

The first two checks need a unit list; the last four work from the position file
alone. The sheet says which levels the list describes, so the first finding is
never mistaken for a claim about levels the list was never trying to cover.

### Working with units

- **Compare** ranks the units side by side — positions, FTE, vacancies, layers,
  span, managers, ICs, critical roles, SAMA roles, succession gaps, the front /
  middle / back split, incentive-paid positions, talent pool and training —
  sortable on any column, with a level picker so you compare like with like
  rather than a division against a department. The unit name stays put as you
  scroll across. Clicking a row selects that unit in the chart.
- **Units…** controls the structure: where it comes from — the approved unit
  list or the tags on the positions — the nesting columns for the detail below
  the frame, and the sibling order.
- **Function type** is a full lens: colour by it, filter by it, or nest by it, so
  the chart can be arranged by line of defence.

### Job attributes and the unit profile

Three columns describe what kind of work a position is, rather than where it
sits: **job type** (front / middle / back office), **pay basis** (incentive /
bonus / fixed) and **talent pool**. Each is a full dimension — colour, filter,
nest — and each rolls up into a read on the unit:

- a thin stacked strip along the bottom of every unit box, showing the job-type
  mix, or the pay mix where job type is absent — a mostly back-office unit looks
  different from a mostly front-office one at a glance;
- a **Profile** section in the unit detail, with proportion bars and counts for
  each mix the file supports, plus talent-pool coverage and training obligation;
- the matching columns in **Compare**, so the mixes can be ranked across units.

**Mandatory courses** come from a third list — another tab in the workbook, or a
file added by hand. It is matched on position ID first and job code second, since
training is usually attached to a job rather than to a seat. The courses appear
on the position's detail card, and the share of a unit's positions carrying an
obligation appears in its profile.

## What it does

**Built for succession and regulatory work.** Critical roles, SAMA non-objection
roles and successor cover are read straight from your file and shown as badges on
every box — including the one that matters most, a critical role with nobody
lined up behind it. The filter chips above the chart light those up wherever they
are in the hierarchy.

**Sized for a real organisation.** Only the branches you have open are drawn, so a
2,600-position file across seven hundred units opens in about a third of a second
and stays responsive. It opens as many layers as stay readable across the screen
and collapses the rest behind a click.

## Using it

Two rows of chrome and then the chart. The top bar carries identity, the view
switch, search and the presentation toggle, with everything occasional behind
**⋯**. The toolbar under it holds what you are looking at — branch, filters,
highlights, colour — on the left, and what it adds up to on the right. Anything
with more than one setting opens a popover rather than taking a row of its own.

| | |
|---|---|
| **Search** | Name, job title or ID. Matches are highlighted and their branches opened. Press `/` to jump to the box. |
| **Filters** | One narrowing control for each dimension your file actually carries — ladder level, branch, function, job type, pay basis, talent pool, grade, location. Matches keep their reporting line, so the tree never breaks into fragments. |
| **Branch** | Pick one leader — or one unit — to work inside alone. |
| **Units…** | Structure of the org view: nesting columns, sibling order, and whether the hierarchy comes from columns or from the unit list. |
| **Compare** | A sortable table of units under the chart, filtered to one level so the ranking means something. |
| **Reconcile** | Where the approved structure and the reporting line disagree, banded by finding and clickable through to each one. |
| **Flag chips** | Highlight critical roles, SAMA roles, succession gaps or vacancies in place. |
| **Colour by** | Recolour the boxes by function, department, grade, location and so on. |
| **Click a box** | Everything held about that position, in two parts: **The job** — code, grade, family, function type, job type, pay basis, talent pool, employment type, FTE, status — and **Where it sits**, the full ladder from group down to section plus branch, function, location and cost centre. Below them the incumbent, succession, mandatory training, direct reports and any column the tool did not recognise. A field your file does not carry is left out rather than shown as a dash. |
| **Presentation** | One switch hides successor names, emails, hire dates and nationality, so the chart is safe to project or screen-share. |
| **PNG** | Saves exactly what is on screen, at slide proportions. |
| **Print** | A heading naming the scope and the figures for it, and then the chart, which fills the rest of the page in light theme, turned landscape or portrait to suit its shape. Nothing else — the browser already prints the file and the date around the edges. The one exception is a filter, a search or presentation mode, which a reader cannot see and must not miss, so those are named under the heading. With **Compare** or **Reconcile** open, the sheet follows on its own pages — a printed reconciliation to hand to whoever owns the HRIS. Use it to save a PDF. |
| **CSV** | Follows the view — and the open sheet, so with **Reconcile** open it exports the findings. Otherwise positions with computed layer, branch headcount, branch FTE and reporting line — or units with headcount, FTE, vacancies, sub-unit counts, flag totals and the full profile. |

## Units with nobody in them

Three different things get confused under "no people", and they are handled
differently.

**All the positions are vacant.** The unit is drawn as a dashed outline reading
*nobody in post*, and counted in the **Nobody in post** figure.

**Positions exist but their unit column is blank.** They collect in an
*Unspecified* box, flagged in red with an **Unmapped positions** count, so a
blank column shows up as the data problem it is instead of quietly disappearing.

**The unit has no positions at all** — newly approved, dormant, or everyone has
moved out. Nothing in a position export mentions it, so it has to be stated. Two
ways, and you can use both:

1. **A row without a position.** Put the unit's Division / Function / Department
   on a row and leave the ID blank. Instead of being skipped as an ID-less row,
   it becomes an empty unit. Nothing new to produce — just rows in the export you
   already run.

2. **An org unit list** — a second sheet in the same workbook (any tab that names
   units and describes them is picked up automatically), or a second file added
   with the **＋ Add unit list** button in the org-unit view. It is read for unit
   name, parent unit, unit code, function type, unit head and roles &
   responsibilities. Units in the list that have no positions appear as empty
   boxes; units that do have positions are annotated with their type and mandate.

   This is also where **function type** and **roles & responsibilities** come
   from. Without a unit list those two are simply absent — units still show
   headcount, FTE and vacancies, and a function type carried on the position rows
   is inherited, but a mandate has nowhere else to come from.

   A listed unit is matched to a box by name, so it has to be named after a
   column the chart is nesting by. If you list your divisions and then nest by
   Group alone, those divisions have no box to be annotated — the **Units…**
   panel says how many are in that position and names them, so the fix (add the
   column back to the nesting) is obvious rather than a silent gap.

## The file it expects

One row per position. Only an **ID** column is genuinely required — everything
else is used when it is present and ignored when it is not.

To draw a hierarchy you also need a **Manager ID** column pointing at another
row's ID.

Recognised beyond that: job title, incumbent name, grade or band, job code, job
family, **group**, **division**, **department**, **unit**, **sub-unit**,
**section**, **branch**, function, location, employment type, status, FTE, cost
centre, email, hire date, nationality, **function type**, **job type**, **pay
basis**, **talent pool**, **roles & responsibilities**, **critical role**, **SAMA
non-objection role**, **successor identified**, **successor name** and
**successor readiness**.

Function type is whatever classification you use — Business / Support / Control,
or first / second / third line of defence. It appears on unit boxes and in the
unit export. A unit with no type of its own takes the one its positions agree on,
and a genuinely mixed unit is left blank rather than labelled by whichever type
happens to be largest.

Job type and pay basis keep whatever wording your file uses; the strip, the
profile bars and the Front / Middle / Back and Incentive columns recognise the
words *front*, *middle*, *back*, *incentive*, *bonus* and *fixed* inside them, so
`Front office` and `Front-line` both read as front. A value using none of those
words still counts in the mix and gets its own bar — it just is not folded into
those named columns. Talent pool takes a pool name or a plain Yes/No.

Column names are matched loosely, so `Manager ID`, `manager_id` and `Reports To`
all land in the same place. Anything the tool does not recognise is kept and
shown on the position's detail card under *Other columns from your file*, so
nothing is lost — the sample's `Legal Entity` column is there to show it. If
something is matched wrongly, the **Columns** button fixes it, and the correction
is remembered for the next export with the same columns.

Formats: `.xlsx`, `.csv`, `.tsv`. Comma, semicolon, tab and pipe delimiters are
detected automatically, as is a header row sitting below title rows. Arabic text
renders correctly throughout.

**In a workbook, the positions are whichever tab most looks like positions** —
not whichever comes first. A cover sheet, a parameters tab or a pivot summary in
front of the export is skipped: a tab is only a candidate if it has an ID column,
and it is ranked on whether it also carries a manager ID, a job title and an
incumbent name, with the row count breaking ties so a short summary never
outranks the real export. The remaining tabs are read for the unit list and the
course list. When the tab chosen is not the first one, the load message names
it. Yes/No columns are read generously — `Yes`, `Y`,
`TRUE`, `1`, `X`, `✓` and `نعم` all mean yes; `Not required` and `N/A` mean no.

### Messy exports

Real HR extracts break, so the chart is drawn anyway and the repairs are
reported under **Data issues**:

- a manager ID that is not in the file — the position moves to the top level
- a reporting loop — the link is cut
- a duplicate ID — both rows are kept as separate positions
- a row with no ID — skipped
- a position reporting to itself — treated as a root

## Notes on counting

Every row is a position, so somebody holding two roles occupies two boxes and
counts twice. That is what you want for position-based headcount, but it is not
the same as a headcount of people — worth knowing before quoting a number.

The two views count the same population, but they filter differently on purpose.
Filtering to a function in the **org view** is strict, so the unit's headcount is
exactly the positions carrying it. The **position view** keeps each match's
reporting line so the tree stays connected, which pulls in managers above the
filter — the same filter can show one or two more positions there.

A division's headcount in the org-unit view is exactly the number of positions
carrying that division. Note that this
is not the same as the branch size of the person who runs it — a unit is defined
by the column value on each row, not by who reports to whom, so a position sits
in the unit its data says it does even if it reports elsewhere.

A unit's "most senior position" is the one running the largest part of the
organisation, not simply the highest grade.

A unit's average span counts every direct report of every manager in it,
including the occasional report sitting in another unit, so the figure never
disagrees with the one the position view shows for the same person.

Roles & responsibilities are held at unit level, so they come from the org unit
list rather than from the positions. Presentation mode hides a named unit head
along with the other personal fields; the mandate text stays visible.

## Development

`.build/make_sample.py` regenerates `sample-org.csv`, `sample-units.csv` and
`sample-courses.csv`; pass a path to also write a three-sheet `.xlsx`. The
structure it generates lives in one `STRUCTURE` table at the top of that file —
group, then division, then departments. Everything else lives in
`org-chart.html`, whose built-in demo mirrors the same shape in miniature.
