# Tracker

Two self-contained tools served by one FastAPI app.

| Tool | URL | What it does |
|---|---|---|
| Trading Performance Tracker | `/` | Log trades, track P&L, win rate and streaks, export reports |
| Org Explorer | `/org/` | Drop in a people file and explore the org hierarchy, positions and headcount |

## Running locally

```bash
pip install -r requirements.txt
uvicorn server:app --reload
```

Then open http://127.0.0.1:8000/ (trading) or http://127.0.0.1:8000/org/ (org).

Data lives in SQLite: `trades.db` for the trading tool, `org.db` for the org tool.
Override the locations with `DB_PATH` and `ORG_DB_PATH`.

---

# Org Explorer

Upload an org file — CSV, TSV, Excel (`.xlsx`/`.xls`) or JSON — and get an
interactive view of the hierarchy, the positional structure and headcount.
Try it with the included `sample_org.csv` (813 synthetic positions).

## Importing

Columns are matched automatically against a catalogue of common HRIS header
names, so most exports import untouched. Anything matched incorrectly can be
remapped in the import dialog before committing, and the first rows are shown
alongside so you can see what you are mapping.

Only **Employee ID** is required. Everything else enriches the views when
present:

| Field | Used for |
|---|---|
| Employee ID | Identity — the only required column |
| Name | Node labels; blank means the position is vacant |
| Manager ID | Builds the reporting hierarchy |
| Job Title, Job Code, Job Family, Job Level | Positional hierarchy, layer profile, cross-tab |
| Function, Department, Division | Grouping, colouring and filtering |
| Location, Employment Type, Cost Center | Breakdowns and filters |
| Status | Filled vs vacant (`Vacant`, `Open`, `TBH`, … are recognised) |
| FTE | FTE rollups; accepts `1`, `0.5` or `50` (percent) |
| Email, Hire Date | Shown on the detail card |

Unmapped columns are kept and shown on each person's detail card, so nothing
in the file is lost.

Messy files are handled rather than rejected — a manager ID that isn't in the
file, a reporting cycle, duplicate IDs, rows with no ID and self-reporting
positions are each resolved so the chart can still be drawn, and every fix is
listed under **Data Quality**.

## The views

**Org Chart** — a pan-and-zoom SVG tree. Cards carry name, title,
function · level · location, direct reports, vacancies below, and a badge with
the total headcount of that branch. Colour the chart by any dimension, collapse
and expand branches, drill into a branch and walk back via the breadcrumb, flip
between vertical and horizontal, and export the current chart as SVG. Teams of
individual contributors hang in a compact indented column so wide orgs stay
readable.

**Positional Hierarchy** — the org by management layer rather than by person:
positions, FTE, managers vs ICs, average span and vacancies per layer, with the
common titles and functions that sit there. Below it, span-of-control
distribution, structure signals (delayering candidates, manager ratio) and a
headcount cross-tab of any two dimensions.

**Headcount** — KPI tiles plus breakdowns by function, department, division,
job level, job family, location, employment type and cost center, each with
headcount, FTE, vacancies and share. Clicking a row filters the whole app.

**People** — the full roster with computed columns (layer, direct reports,
branch size, branch FTE), sortable and filterable.

**Data Quality** — everything the importer had to fix, grouped by type.

Filters at the top apply to every view at once. When a filter matches someone
deep in the org, their management chain is kept so the tree stays connected
rather than showing floating fragments. Export the filtered org, with its
computed rollups and reporting lines, as CSV.

Multiple datasets can be held at once, so you can keep snapshots side by side
and switch between them.

## API

All endpoints live under `/api/org` and accept the same filter parameters
(`function`, `department`, `job_level`, `location`, `vacancy`, `search`).

| Endpoint | Purpose |
|---|---|
| `POST /preview` | Parse a file; returns headers, a sample and the guessed mapping |
| `POST /import` | Commit a file with a mapping; returns the import report |
| `GET /datasets`, `PUT /datasets/{id}`, `DELETE /datasets/{id}` | Manage snapshots |
| `GET /tree` | Nested hierarchy with rollups (`root`, `max_depth`) |
| `GET /summary` | KPIs, layer profile, span profile and breakdowns |
| `GET /matrix` | Headcount cross-tab (`rows`, `cols`) |
| `GET /employees`, `GET /employees/{id}` | Flat roster and person detail |
| `GET /issues` | Data quality findings |
| `GET /export/csv` | Flat export with rollups and reporting lines |
| `GET /template.csv` | Blank file in the expected shape |

## Layout

```
org_parser.py     file reading, column detection, row normalisation
org_analytics.py  tree building, rollups, metrics, cross-tabs
org_db.py         SQLite storage for datasets
org_api.py        HTTP API
static/org/       UI (vanilla JS; Chart.js vendored, no CDN)
```
