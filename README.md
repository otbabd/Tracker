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
names, the reporting lines and the deliberately broken rows are all generated.

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

**Org units** — the view it opens on. One box per organisational unit, showing
its headcount, FTE and vacancies, the shape of it — layers, average span,
managers against individual contributors — its function type, sub-unit count, the
most senior position inside it and the mix of work it does. The shape of the
organisation rather than the seats in it. It opens as many levels as fit across
the screen legibly — for a twelve-group bank that is the groups themselves — and
the rest is a click away.

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

### Working with units

- **Compare** ranks the units side by side — positions, FTE, vacancies, layers,
  span, managers, ICs, critical roles, SAMA roles, succession gaps, the front /
  middle / back split, incentive-paid positions, talent pool and training —
  sortable on any column, with a level picker so you compare like with like
  rather than a division against a department. The unit name stays put as you
  scroll across. Clicking a row selects that unit in the chart.
- **Units…** controls the structure: nest by up to six columns, order siblings
  by size, name or vacancies, and — when your unit list carries parent
  relationships — build the hierarchy from the list itself rather than from
  column nesting.
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
| **Flag chips** | Highlight critical roles, SAMA roles, succession gaps or vacancies in place. |
| **Colour by** | Recolour the boxes by function, department, grade, location and so on. |
| **Click a box** | Everything held about that position, in two parts: **The job** — code, grade, family, function type, job type, pay basis, talent pool, employment type, FTE, status — and **Where it sits**, the full ladder from group down to section plus branch, function, location and cost centre. Below them the incumbent, succession, mandatory training, direct reports and any column the tool did not recognise. A field your file does not carry is left out rather than shown as a dash. |
| **Presentation** | One switch hides successor names, emails, hire dates and nationality, so the chart is safe to project or screen-share. |
| **PNG** | Saves exactly what is on screen, at slide proportions. |
| **Print** | Lays the current branch out to fit a page, in light theme — use it to save a branch as PDF. |
| **CSV** | Follows the view: positions with computed layer, branch headcount, branch FTE and reporting line — or units with headcount, FTE, vacancies, sub-unit counts, flag totals and the full profile. |

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
renders correctly throughout. Yes/No columns are read generously — `Yes`, `Y`,
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
