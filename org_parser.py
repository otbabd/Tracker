"""File ingestion for the org tool: read a dumped file, guess its columns,
and normalise rows into employee records."""
import io
import json
import math
import re
from typing import Optional

import pandas as pd

# ── Field catalogue ───────────────────────────────────────────────────────────
# (key, label, aliases) — aliases are matched against normalised header names.
FIELDS = [
    ("employee_id",  "Employee ID",   ["employeeid", "empid", "id", "personid", "personnelnumber",
                                       "staffid", "staffno", "staffnumber", "workerid", "workerno",
                                       "badge", "employeenumber", "employeeno", "empno", "empcode",
                                       "employeecode", "personno", "personnelno", "personnelid",
                                       "positionid", "positionno", "positionnumber", "uid",
                                       "recordid", "idno", "hrid", "sapid", "userid"]),
    ("name",         "Name",          ["name", "fullname", "employeename", "displayname", "employee",
                                       "worker", "preferredname", "incumbent"]),
    ("manager_id",   "Manager ID",    ["managerid", "managerempid", "supervisorid", "reportsto",
                                       "reportstoid", "parentid", "managerof", "linemanagerid",
                                       "supervisor", "manager", "linemanager", "reportsto2"]),
    ("job_title",    "Job Title",     ["jobtitle", "title", "position", "positiontitle", "role",
                                       "jobname", "designation"]),
    ("job_code",     "Job Code",      ["jobcode", "positioncode", "jobid", "roleid", "jobreqcode"]),
    ("job_family",   "Job Family",    ["jobfamily", "family", "jobgroup", "career", "careertrack",
                                       "jobcategory", "subfunction"]),
    ("job_level",    "Job Level",     ["joblevel", "level", "grade", "band", "paygrade", "payband",
                                       "seniority", "rank", "gradelevel", "jobgrade"]),
    ("function",     "Function",      ["function", "businessfunction", "orgfunction", "area",
                                       "discipline", "practice"]),
    ("department",   "Department",    ["department", "dept", "team", "orgunit", "unit", "section",
                                       "costcentername", "subdivision"]),
    ("division",     "Division",      ["division", "businessunit", "bu", "sector", "group",
                                       "company", "entity", "segment"]),
    ("location",     "Location",      ["location", "office", "site", "city", "country", "region",
                                       "worklocation", "basedin"]),
    ("employment_type", "Employment Type", ["employmenttype", "workertype", "contracttype",
                                            "emptype", "employeetype", "type", "category"]),
    ("status",       "Status",        ["status", "positionstatus", "employeestatus", "vacancy",
                                       "vacant", "filled", "occupancy", "state"]),
    ("fte",          "FTE",           ["fte", "headcount", "hc", "fteequivalent",
                                       "fulltimeequivalent", "capacity"]),
    ("cost_center",  "Cost Center",   ["costcenter", "costcentre", "cc", "costcentercode",
                                       "glcode", "budgetcode"]),
    ("email",        "Email",         ["email", "emailaddress", "workemail", "mail", "upn"]),
    ("hire_date",    "Hire Date",     ["hiredate", "startdate", "joindate", "dateofjoining",
                                       "dateofhire", "effectivedate", "seniority date"]),
]

FIELD_KEYS = [f[0] for f in FIELDS]
REQUIRED_FIELDS = ["employee_id", "name"]

VACANT_TOKENS = {"vacant", "open", "tbh", "tobehired", "unfilled", "notfilled", "new",
                 "openrole", "openposition", "vacancy", "hiring", "backfill", "torecruit"}
BLANK_NAME_TOKENS = {"", "-", "--", "n/a", "na", "none", "null", "tbd", "tbh", "vacant",
                     "open", "unknown", "?"}


def _norm(s: str) -> str:
    """Normalise a header for alias matching: lowercase, alphanumerics only."""
    return re.sub(r"[^a-z0-9]", "", str(s).strip().lower())


def _clean(v) -> Optional[str]:
    """Coerce a raw cell to a trimmed string, or None when empty."""
    if v is None:
        return None
    if isinstance(v, float) and math.isnan(v):
        return None
    if isinstance(v, float) and v.is_integer():
        v = int(v)
    s = str(v).strip()
    if s == "" or s.lower() in ("nan", "nat", "none", "null"):
        return None
    return s


# ── Reading ───────────────────────────────────────────────────────────────────

def read_table(filename: str, content: bytes) -> tuple[list[str], list[dict]]:
    """Read a dumped file into (headers, rows). Supports csv/tsv/xlsx/xls/json."""
    name = (filename or "").lower()
    try:
        if name.endswith((".xlsx", ".xlsm", ".xls")):
            df = pd.read_excel(io.BytesIO(content), dtype=object)
        elif name.endswith(".json"):
            payload = json.loads(content.decode("utf-8-sig"))
            if isinstance(payload, dict):
                for key in ("employees", "data", "rows", "records", "items"):
                    if isinstance(payload.get(key), list):
                        payload = payload[key]
                        break
            if not isinstance(payload, list):
                raise ValueError("JSON must be an array of objects, or an object wrapping one")
            df = pd.DataFrame(payload, dtype=object)
        else:
            text = content.decode("utf-8-sig", errors="replace")
            sep = "\t" if name.endswith((".tsv", ".tab")) else None
            df = pd.read_csv(io.StringIO(text), dtype=object, sep=sep,
                             engine="python", skip_blank_lines=True)
    except Exception as e:
        raise ValueError(f"Could not read {filename or 'file'}: {e}")

    df = df.dropna(axis=1, how="all").dropna(axis=0, how="all")
    df.columns = [str(c).strip() for c in df.columns]
    # De-duplicate blank/repeated headers so mapping stays unambiguous.
    seen, headers = {}, []
    for i, c in enumerate(df.columns):
        c = c if c and not c.lower().startswith("unnamed:") else f"Column {i + 1}"
        if c in seen:
            seen[c] += 1
            c = f"{c} ({seen[c]})"
        else:
            seen[c] = 1
        headers.append(c)
    df.columns = headers

    rows = [{h: _clean(r.get(h)) for h in headers} for r in df.to_dict("records")]
    rows = [r for r in rows if any(v is not None for v in r.values())]
    if not rows:
        raise ValueError("File contains no data rows")
    return headers, rows


# ── Column mapping ────────────────────────────────────────────────────────────

def suggest_mapping(headers: list[str], rows: Optional[list[dict]] = None) -> dict:
    """Best-effort guess of field -> header, so most files import untouched."""
    normalised = {h: _norm(h) for h in headers}
    mapping, taken = {}, set()

    def claim(field, header):
        if header and header not in taken:
            mapping[field] = header
            taken.add(header)

    # Pass 1: exact alias hits, in alias-priority order.
    for field, _label, aliases in FIELDS:
        if field in mapping:
            continue
        for alias in aliases:
            match = next((h for h, n in normalised.items() if n == alias and h not in taken), None)
            if match:
                claim(field, match)
                break

    # Pass 2: substring hits for anything still unmapped.
    for field, _label, aliases in FIELDS:
        if field in mapping:
            continue
        for alias in aliases:
            if len(alias) < 4:
                continue
            match = next((h for h, n in normalised.items() if alias in n and h not in taken), None)
            if match:
                claim(field, match)
                break

    # Last resort for the one field we cannot do without: the left-most column
    # that is fully populated and unique looks like an identifier.
    if "employee_id" not in mapping and rows:
        for h in headers:
            if h in taken:
                continue
            values = [r.get(h) for r in rows]
            filled = [v for v in values if v is not None]
            if len(filled) == len(values) and len(set(filled)) == len(filled):
                claim("employee_id", h)
                break

    return mapping


def unmapped_headers(headers: list[str], mapping: dict) -> list[str]:
    used = set(mapping.values())
    return [h for h in headers if h not in used]


# ── Normalisation ─────────────────────────────────────────────────────────────

def _parse_fte(raw: Optional[str]) -> float:
    if raw is None:
        return 1.0
    s = str(raw).strip().replace("%", "")
    try:
        v = float(s)
    except ValueError:
        return 1.0
    if v > 1.5:            # 100 / 50 style percentages
        v = v / 100.0
    return round(max(v, 0.0), 4)


def _is_vacant(name: Optional[str], status: Optional[str], title: Optional[str]) -> bool:
    if status and _norm(status) in VACANT_TOKENS:
        return True
    if status and any(t in _norm(status) for t in ("vacant", "tobehired", "unfilled", "openposition")):
        return True
    if name is None or str(name).strip().lower() in BLANK_NAME_TOKENS:
        return True
    if name and _norm(name) in VACANT_TOKENS:
        return True
    if title and _norm(title).startswith("vacant"):
        return True
    return False


def normalize_rows(rows: list[dict], mapping: dict, headers: list[str]) -> tuple[list[dict], list[dict]]:
    """Apply the column mapping and return (employees, warnings).

    Rows without a usable ID are dropped and reported; duplicate IDs are
    suffixed so the tree stays well-formed rather than silently losing people.
    """
    warnings: list[dict] = []
    missing = [f for f in REQUIRED_FIELDS if f == "employee_id" and not mapping.get(f)]
    if missing:
        raise ValueError("An 'Employee ID' column must be mapped before importing")

    extras = unmapped_headers(headers, mapping)
    employees, seen_ids = [], {}

    for i, row in enumerate(rows):
        get = lambda f: row.get(mapping[f]) if mapping.get(f) else None  # noqa: E731

        emp_id = _clean(get("employee_id"))
        if not emp_id:
            warnings.append({"type": "missing_id", "row": i + 2,
                             "message": f"Row {i + 2} has no Employee ID and was skipped"})
            continue
        if emp_id in seen_ids:
            seen_ids[emp_id] += 1
            dup = f"{emp_id}#{seen_ids[emp_id]}"
            warnings.append({"type": "duplicate_id", "row": i + 2,
                             "message": f"Row {i + 2}: duplicate ID '{emp_id}' imported as '{dup}'"})
            emp_id = dup
        else:
            seen_ids[emp_id] = 1

        name = _clean(get("name"))
        status = _clean(get("status"))
        title = _clean(get("job_title"))
        manager_id = _clean(get("manager_id"))
        if manager_id == emp_id:
            warnings.append({"type": "self_manager", "row": i + 2,
                             "message": f"'{name or emp_id}' reports to themselves; treated as a root"})
            manager_id = None

        vacant = _is_vacant(name, status, title)
        employees.append({
            "employee_id":     emp_id,
            "name":            name or ("Vacant" if vacant else emp_id),
            "manager_id":      manager_id,
            "job_title":       title,
            "job_code":        _clean(get("job_code")),
            "job_family":      _clean(get("job_family")),
            "job_level":       _clean(get("job_level")),
            "function":        _clean(get("function")),
            "department":      _clean(get("department")),
            "division":        _clean(get("division")),
            "location":        _clean(get("location")),
            "employment_type": _clean(get("employment_type")),
            "status":          status or ("Vacant" if vacant else "Filled"),
            "is_vacant":       1 if vacant else 0,
            "fte":             _parse_fte(_clean(get("fte"))),
            "cost_center":     _clean(get("cost_center")),
            "email":           _clean(get("email")),
            "hire_date":       _clean(get("hire_date")),
            "extra":           json.dumps({h: row[h] for h in extras if row.get(h) is not None}),
        })

    if not employees:
        raise ValueError("No rows had a usable Employee ID")
    return employees, warnings
