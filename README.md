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

`sample-org.csv` is synthetic data (2,600 positions) if you want to try it before
pointing it at anything real. The **Try it with sample data** button generates a
smaller example without any file at all.

---

## Two views of the same file

A switch in the toolbar changes what a box means. The file is loaded once and
the filters carry across.

**Positions** — one box per seat. The job title leads, the person in it sits
underneath, and a vacancy is a normal state of a position rather than a gap in
the data. Boxes are joined by reporting lines, taken from Manager ID.

**Org units** — one box per organisational unit, nested by Division → Function →
Department (you can change the nesting to any columns your file has, up to three
levels deep). Each unit shows its headcount, FTE, vacancies, how many sub-units
it contains and the most senior position inside it. Roughly fifty boxes instead
of a few thousand: the shape of the organisation rather than the seats in it.
"Show these positions" on any unit drops you back into the position view,
filtered to it.

## What it does

**Built for succession and regulatory work.** Critical roles, SAMA non-objection
roles and successor cover are read straight from your file and shown as badges on
every box — including the one that matters most, a critical role with nobody
lined up behind it. The filter chips above the chart light those up wherever they
are in the hierarchy.

**Sized for a real organisation.** Only the branches you have open are drawn, so a
2,600-position file opens in about a quarter of a second and stays responsive. It
starts at the top three layers with everything below collapsed behind a click.

## Using it

| | |
|---|---|
| **Search** | Name, job title or ID. Matches are highlighted and their branches opened. Press `/` to jump to the box. |
| **Filters** | Narrow by function, department or grade. Matches keep their reporting line, so the tree never breaks into fragments. |
| **Branch** | Pick one leader — or one unit — to work inside alone. |
| **Nest by** | In the org-unit view, choose which columns build the hierarchy. |
| **Flag chips** | Highlight critical roles, SAMA roles, succession gaps or vacancies in place. |
| **Colour by** | Recolour the boxes by function, department, grade, location and so on. |
| **Click a box** | Everything held about that position, its reporting line, its direct reports, and its successor with readiness. |
| **Presentation** | One switch hides successor names, emails, hire dates and nationality, so the chart is safe to project or screen-share. |
| **PNG** | Saves exactly what is on screen, at slide proportions. |
| **Print** | Lays the current branch out to fit a page, in light theme — use it to save a branch as PDF. |
| **CSV** | Follows the view: positions with computed layer, branch headcount, branch FTE and reporting line — or units with headcount, FTE, vacancies, sub-unit counts and flag totals. |

## The file it expects

One row per position. Only an **ID** column is genuinely required — everything
else is used when it is present and ignored when it is not.

To draw a hierarchy you also need a **Manager ID** column pointing at another
row's ID.

Recognised beyond that: job title, incumbent name, grade or band, job code, job
family, function, department, division, location, employment type, status, FTE,
cost centre, email, hire date, nationality, **critical role**, **SAMA
non-objection role**, **successor identified**, **successor name** and
**successor readiness**.

Column names are matched loosely, so `Manager ID`, `manager_id` and `Reports To`
all land in the same place. Anything the tool does not recognise is kept and
shown on the position's detail card, so nothing in your file is lost. If
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

The two views count the same population: a division's headcount in the org-unit
view is exactly the number of positions carrying that division. Note that this
is not the same as the branch size of the person who runs it — a unit is defined
by the column value on each row, not by who reports to whom, so a position sits
in the unit its data says it does even if it reports elsewhere.

A unit's "most senior position" is the one running the largest part of the
organisation, not simply the highest grade.

## Development

`.build/make_sample.py` regenerates `sample-org.csv`. Everything else lives in
`org-chart.html`.
