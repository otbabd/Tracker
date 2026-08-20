"""HTTP API for the org hierarchy tool."""
import csv
import io
import json
from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel

import org_analytics as OA
import org_db as ODB
import org_parser as OP

router = APIRouter(prefix="/api/org", tags=["org"])

MAX_UPLOAD_BYTES = 25 * 1024 * 1024
PREVIEW_ROWS = 12


class RenameIn(BaseModel):
    name: str


# ── Helpers ───────────────────────────────────────────────────────────────────

def _read_upload(file: UploadFile) -> tuple[list[str], list[dict]]:
    content = file.file.read()
    if not content:
        raise HTTPException(422, "The uploaded file is empty")
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, f"File is larger than {MAX_UPLOAD_BYTES // (1024 * 1024)} MB")
    try:
        return OP.read_table(file.filename or "", content)
    except ValueError as e:
        raise HTTPException(422, str(e))


def _resolve_dataset(dataset_id: Optional[int]) -> int:
    did = dataset_id or ODB.latest_dataset_id()
    if not did or not ODB.get_dataset(did):
        raise HTTPException(404, "No org dataset found — upload a file first")
    return did


def _filters(function=None, department=None, division=None, job_level=None,
             job_family=None, location=None, employment_type=None,
             vacancy=None, search=None) -> dict:
    raw = {"function": function, "department": department, "division": division,
           "job_level": job_level, "job_family": job_family, "location": location,
           "employment_type": employment_type, "vacancy": vacancy, "search": search}
    return {k: v for k, v in raw.items() if v and v != "All"}


def _load(dataset_id: Optional[int], filters: dict) -> tuple[int, dict]:
    did = _resolve_dataset(dataset_id)
    employees = ODB.get_employees(did)
    if filters:
        employees = OA.filter_employees(employees, filters)
    if not employees:
        return did, OA.build([])
    return did, OA.build(employees)


# ── Import ────────────────────────────────────────────────────────────────────

@router.get("/fields")
def fields():
    """Field catalogue + dimensions, so the UI never hardcodes the schema."""
    return {
        "fields": [{"key": k, "label": lbl, "required": k in OP.REQUIRED_FIELDS}
                   for k, lbl, _ in OP.FIELDS],
        "dimensions": [{"key": k, "label": lbl} for k, lbl in OA.DIMENSIONS],
    }


@router.post("/preview")
def preview(file: UploadFile = File(...)):
    """Parse a dumped file and return headers, a sample and a guessed mapping."""
    headers, rows = _read_upload(file)
    mapping = OP.suggest_mapping(headers, rows)
    return {
        "filename": file.filename,
        "headers": headers,
        "row_count": len(rows),
        "sample": rows[:PREVIEW_ROWS],
        "mapping": mapping,
        "unmapped": OP.unmapped_headers(headers, mapping),
    }


@router.post("/import", status_code=201)
def import_file(file: UploadFile = File(...),
                mapping: Optional[str] = Form(None),
                name: Optional[str] = Form(None)):
    headers, rows = _read_upload(file)
    try:
        user_mapping = json.loads(mapping) if mapping else None
    except ValueError:
        raise HTTPException(422, "Mapping must be valid JSON")

    final_mapping = {k: v for k, v in (user_mapping or OP.suggest_mapping(headers, rows)).items()
                     if v and v in headers}
    try:
        employees, warnings = OP.normalize_rows(rows, final_mapping, headers)
    except ValueError as e:
        raise HTTPException(422, str(e))

    index = OA.build(employees)
    warnings = warnings + index["issues"]
    dataset_id = ODB.create_dataset(
        name or (file.filename or "Org snapshot"), file.filename,
        employees, final_mapping, warnings,
    )
    return {
        "dataset_id": dataset_id,
        "imported": len(employees),
        "skipped": len(rows) - len(employees),
        "mapping": final_mapping,
        "warnings": warnings,
        "summary": OA.summarize(index),
    }


# ── Datasets ──────────────────────────────────────────────────────────────────

@router.get("/datasets")
def datasets():
    return ODB.list_datasets()


@router.get("/datasets/{dataset_id}")
def dataset_detail(dataset_id: int):
    d = ODB.get_dataset(dataset_id)
    if not d:
        raise HTTPException(404, "Dataset not found")
    return d


@router.put("/datasets/{dataset_id}")
def rename(dataset_id: int, body: RenameIn):
    if not ODB.get_dataset(dataset_id):
        raise HTTPException(404, "Dataset not found")
    if not body.name.strip():
        raise HTTPException(422, "Name cannot be empty")
    ODB.rename_dataset(dataset_id, body.name.strip())
    return {"id": dataset_id, "name": body.name.strip()}


@router.delete("/datasets/{dataset_id}", status_code=204)
def remove(dataset_id: int):
    if not ODB.get_dataset(dataset_id):
        raise HTTPException(404, "Dataset not found")
    ODB.delete_dataset(dataset_id)


# ── Views ─────────────────────────────────────────────────────────────────────

@router.get("/tree")
def tree(dataset_id: Optional[int] = None, root: Optional[str] = None,
         max_depth: Optional[int] = None, function: Optional[str] = None,
         department: Optional[str] = None, division: Optional[str] = None,
         job_level: Optional[str] = None, job_family: Optional[str] = None,
         location: Optional[str] = None, employment_type: Optional[str] = None,
         vacancy: Optional[str] = None, search: Optional[str] = None):
    f = _filters(function, department, division, job_level, job_family,
                 location, employment_type, vacancy, search)
    did, index = _load(dataset_id, f)
    if root and root not in index["by_id"]:
        raise HTTPException(404, "Root employee not found in this view")
    return {
        "dataset_id": did,
        "roots": OA.to_tree(index, root, max_depth),
        "count": len(index["by_id"]),
        "max_depth": index.get("max_depth", 0),
        "breadcrumb": index["by_id"][root].get("chain", []) if root else [],
    }


@router.get("/summary")
def summary(dataset_id: Optional[int] = None, function: Optional[str] = None,
            department: Optional[str] = None, division: Optional[str] = None,
            job_level: Optional[str] = None, job_family: Optional[str] = None,
            location: Optional[str] = None, employment_type: Optional[str] = None,
            vacancy: Optional[str] = None, search: Optional[str] = None):
    f = _filters(function, department, division, job_level, job_family,
                 location, employment_type, vacancy, search)
    did, index = _load(dataset_id, f)
    out = OA.summarize(index)
    out["dataset_id"] = did
    return out


@router.get("/matrix")
def matrix(dataset_id: Optional[int] = None, rows: str = "job_level",
           cols: str = "function", function: Optional[str] = None,
           department: Optional[str] = None, division: Optional[str] = None,
           job_level: Optional[str] = None, job_family: Optional[str] = None,
           location: Optional[str] = None, employment_type: Optional[str] = None,
           vacancy: Optional[str] = None, search: Optional[str] = None):
    valid = {k for k, _ in OA.DIMENSIONS}
    if rows not in valid or cols not in valid:
        raise HTTPException(422, f"rows/cols must be one of: {', '.join(sorted(valid))}")
    f = _filters(function, department, division, job_level, job_family,
                 location, employment_type, vacancy, search)
    _did, index = _load(dataset_id, f)
    return OA.position_matrix(index, rows, cols)


@router.get("/employees")
def employees(dataset_id: Optional[int] = None, function: Optional[str] = None,
              department: Optional[str] = None, division: Optional[str] = None,
              job_level: Optional[str] = None, job_family: Optional[str] = None,
              location: Optional[str] = None, employment_type: Optional[str] = None,
              vacancy: Optional[str] = None, search: Optional[str] = None,
              managers_only: bool = False, sort_by: str = "name",
              limit: int = Query(500, ge=1, le=20000)):
    f = _filters(function, department, division, job_level, job_family,
                 location, employment_type, vacancy, search)
    _did, index = _load(dataset_id, f)
    people = [OA.to_node(e) for e in index["by_id"].values()]
    if managers_only:
        people = [p for p in people if p["is_manager"]]
    reverse = sort_by in ("total_headcount", "direct_reports", "total_fte", "level_no")
    people.sort(key=lambda p: (p.get(sort_by) is None,
                               p.get(sort_by) if not isinstance(p.get(sort_by), str)
                               else p[sort_by].lower()),
                reverse=reverse)
    return {"count": len(people), "employees": people[:limit]}


@router.get("/employees/{employee_id}")
def employee_detail(employee_id: str, dataset_id: Optional[int] = None):
    did = _resolve_dataset(dataset_id)
    raw = ODB.get_employees(did)
    index = OA.build(raw)
    emp = index["by_id"].get(employee_id)
    if not emp:
        raise HTTPException(404, "Employee not found")
    extra = next((e.get("extra") for e in raw if e["employee_id"] == employee_id), {})
    node = OA.to_node(emp)
    node["chain"] = emp.get("chain", [])
    node["extra"] = extra if isinstance(extra, dict) else {}
    node["reports"] = [OA.to_node(index["by_id"][k])
                       for k in index["children"].get(employee_id, [])]
    return node


@router.get("/issues")
def issues(dataset_id: Optional[int] = None):
    did = _resolve_dataset(dataset_id)
    index = OA.build(ODB.get_employees(did))
    stored = ODB.get_dataset(did).get("warnings", [])
    seen, merged = set(), []
    for item in stored + index["issues"]:
        key = (item.get("type"), item.get("message"))
        if key not in seen:
            seen.add(key)
            merged.append(item)
    return {"dataset_id": did, "count": len(merged), "issues": merged}


# ── Exports ───────────────────────────────────────────────────────────────────

EXPORT_COLUMNS = [
    "employee_id", "name", "job_title", "job_level", "job_family", "function",
    "department", "division", "location", "employment_type", "status", "fte",
    "cost_center", "manager_id", "manager_name", "level_no", "direct_reports",
    "total_headcount", "total_fte", "total_vacant", "is_manager", "reporting_line",
]


@router.get("/export/csv")
def export_csv(dataset_id: Optional[int] = None, function: Optional[str] = None,
               department: Optional[str] = None, division: Optional[str] = None,
               job_level: Optional[str] = None, job_family: Optional[str] = None,
               location: Optional[str] = None, employment_type: Optional[str] = None,
               vacancy: Optional[str] = None, search: Optional[str] = None):
    f = _filters(function, department, division, job_level, job_family,
                 location, employment_type, vacancy, search)
    _did, index = _load(dataset_id, f)

    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=EXPORT_COLUMNS, extrasaction="ignore")
    writer.writeheader()
    for emp in sorted(index["by_id"].values(),
                      key=lambda e: (e.get("level_no", 0), (e.get("name") or "").lower())):
        row = OA.to_node(emp)
        mgr = index["by_id"].get(emp.get("manager_id") or "")
        row["manager_name"] = mgr.get("name") if mgr else ""
        row["is_manager"] = "Yes" if emp.get("is_manager") else "No"
        row["reporting_line"] = " > ".join(c["name"] or c["employee_id"]
                                           for c in emp.get("chain", []))
        writer.writerow(row)

    return Response(buf.getvalue(), media_type="text/csv",
                    headers={"Content-Disposition": 'attachment; filename="org_hierarchy.csv"'})


@router.get("/template.csv")
def template():
    """A blank file in the shape the importer expects."""
    headers = [lbl for _k, lbl, _a in OP.FIELDS]
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(headers)
    w.writerow(["E001", "Amina Yusuf", "", "Chief Executive Officer", "JC-100", "Executive",
                "L1", "Executive", "Executive Office", "Corporate", "Riyadh", "Full-time",
                "Filled", "1", "CC-100", "amina@example.com", "2018-01-15"])
    w.writerow(["E002", "Vacant", "E001", "Chief Financial Officer", "JC-101", "Executive",
                "L2", "Finance", "Finance", "Corporate", "Riyadh", "Full-time",
                "Vacant", "1", "CC-200", "", ""])
    return Response(buf.getvalue(), media_type="text/csv",
                    headers={"Content-Disposition": 'attachment; filename="org_template.csv"'})
