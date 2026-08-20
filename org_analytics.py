"""Hierarchy building and headcount analytics for the org tool."""
from collections import Counter, defaultdict
from typing import Optional

# Dimensions available for grouping, colouring and filtering in the UI.
DIMENSIONS = [
    ("function",        "Function"),
    ("department",      "Department"),
    ("division",        "Division"),
    ("job_level",       "Job Level"),
    ("job_family",      "Job Family"),
    ("job_title",       "Job Title"),
    ("location",        "Location"),
    ("employment_type", "Employment Type"),
    ("cost_center",     "Cost Center"),
]

UNSPECIFIED = "Unspecified"


def _val(emp: dict, key: str) -> str:
    return emp.get(key) or UNSPECIFIED


# ── Tree construction ─────────────────────────────────────────────────────────

def build_index(employees: list[dict]) -> dict:
    """Link employees into a parent/child index, breaking cycles and reparenting
    orphans so that every person always ends up reachable from some root."""
    by_id = {e["employee_id"]: dict(e) for e in employees}
    children: dict[Optional[str], list[str]] = defaultdict(list)
    issues: list[dict] = []
    roots: list[str] = []

    for eid, emp in by_id.items():
        mid = emp.get("manager_id")
        if mid and mid not in by_id:
            issues.append({
                "type": "orphan", "employee_id": eid, "name": emp.get("name"),
                "message": f"Manager '{mid}' of {emp.get('name') or eid} is not in the file; "
                           f"treated as a top-level node",
            })
            emp["manager_id"] = None
            emp["orphaned_from"] = mid
            mid = None
        if mid:
            children[mid].append(eid)
        else:
            roots.append(eid)

    # Any node still unreachable sits in a management cycle — cut its link.
    reachable, stack = set(), list(roots)
    while stack:
        nid = stack.pop()
        if nid in reachable:
            continue
        reachable.add(nid)
        stack.extend(children.get(nid, []))

    for eid in by_id:
        if eid in reachable:
            continue
        emp = by_id[eid]
        mid = emp.get("manager_id")
        issues.append({
            "type": "cycle", "employee_id": eid, "name": emp.get("name"),
            "message": f"Reporting cycle detected at {emp.get('name') or eid}; "
                       f"link to manager '{mid}' was cut",
        })
        if mid and eid in children.get(mid, []):
            children[mid].remove(eid)
        emp["manager_id"] = None
        emp["in_cycle"] = True
        roots.append(eid)
        stack = [eid]
        while stack:
            nid = stack.pop()
            if nid in reachable:
                continue
            reachable.add(nid)
            stack.extend(children.get(nid, []))

    for kids in children.values():
        kids.sort(key=lambda i: (by_id[i].get("name") or "").lower())
    roots.sort(key=lambda i: (by_id[i].get("name") or "").lower())

    if len(roots) > 1:
        issues.append({
            "type": "multiple_roots", "employee_id": None, "name": None,
            "message": f"{len(roots)} top-level nodes found — the file has no single CEO/root",
        })

    return {"by_id": by_id, "children": children, "roots": roots, "issues": issues}


def compute_rollups(index: dict) -> dict:
    """Depth-first rollup of headcount, FTE, vacancies and depth onto each node."""
    by_id, children = index["by_id"], index["children"]

    for eid, emp in by_id.items():
        kids = children.get(eid, [])
        emp["direct_reports"] = len(kids)
        emp["is_manager"] = len(kids) > 0

    # Iterative post-order so very deep files can't blow the recursion limit.
    for root in index["roots"]:
        order, stack = [], [root]
        while stack:
            nid = stack.pop()
            order.append(nid)
            stack.extend(children.get(nid, []))
        for nid in reversed(order):
            emp = by_id[nid]
            kids = children.get(nid, [])
            emp["total_reports"] = sum(by_id[k]["total_reports"] + 1 for k in kids)
            emp["total_fte"] = round(emp.get("fte", 1.0) + sum(by_id[k]["total_fte"] for k in kids), 4)
            emp["total_vacant"] = emp.get("is_vacant", 0) + sum(by_id[k]["total_vacant"] for k in kids)
            emp["sub_managers"] = sum(by_id[k]["sub_managers"] + (1 if by_id[k]["is_manager"] else 0)
                                      for k in kids)
            emp["subtree_depth"] = 1 + max((by_id[k]["subtree_depth"] for k in kids), default=0)

    # Depth / chain-of-command, walking down from each root.
    for root in index["roots"]:
        stack = [(root, 0, [])]
        while stack:
            nid, depth, chain = stack.pop()
            emp = by_id[nid]
            emp["depth"] = depth
            emp["level_no"] = depth + 1
            emp["chain"] = chain
            new_chain = chain + [{"employee_id": nid, "name": emp.get("name"),
                                  "job_title": emp.get("job_title")}]
            for k in children.get(nid, []):
                stack.append((k, depth + 1, new_chain))

    index["max_depth"] = max((e.get("depth", 0) for e in by_id.values()), default=0) + 1
    return index


def build(employees: list[dict]) -> dict:
    return compute_rollups(build_index(employees))


# ── Serialisation ─────────────────────────────────────────────────────────────

NODE_FIELDS = [
    "employee_id", "name", "manager_id", "job_title", "job_code", "job_family",
    "job_level", "function", "department", "division", "location",
    "employment_type", "status", "is_vacant", "fte", "cost_center", "email",
    "hire_date", "direct_reports", "total_reports", "total_fte", "total_vacant",
    "sub_managers", "subtree_depth", "depth", "level_no", "is_manager",
]


def to_node(emp: dict) -> dict:
    node = {k: emp.get(k) for k in NODE_FIELDS}
    node["total_headcount"] = (emp.get("total_reports") or 0) + 1
    if emp.get("in_cycle"):
        node["in_cycle"] = True
    if emp.get("orphaned_from"):
        node["orphaned_from"] = emp["orphaned_from"]
    return node


def to_tree(index: dict, root_id: Optional[str] = None, max_depth: Optional[int] = None) -> list[dict]:
    """Serialise the index to nested dicts, optionally rooted at one person."""
    by_id, children = index["by_id"], index["children"]
    roots = [root_id] if root_id and root_id in by_id else index["roots"]

    def pack(nid: str, level: int) -> dict:
        node = to_node(by_id[nid])
        kids = children.get(nid, [])
        if max_depth is not None and level >= max_depth:
            node["children"] = []
            node["truncated"] = len(kids)
        else:
            node["children"] = [pack(k, level + 1) for k in kids]
        return node

    return [pack(r, 0) for r in roots]


# ── Filtering ─────────────────────────────────────────────────────────────────

def filter_employees(employees: list[dict], filters: dict) -> list[dict]:
    """Filter the flat list, then keep every ancestor of a match so the chart
    stays connected rather than showing floating fragments."""
    if not filters:
        return employees

    def matches(e: dict) -> bool:
        for key, want in filters.items():
            if key == "search":
                q = str(want).lower()
                hay = " ".join(str(e.get(f) or "") for f in
                               ("name", "employee_id", "job_title", "department",
                                "function", "email", "location"))
                if q not in hay.lower():
                    return False
            elif key == "vacancy":
                if want == "Vacant" and not e.get("is_vacant"):
                    return False
                if want == "Filled" and e.get("is_vacant"):
                    return False
            elif key == "managers_only":
                continue
            else:
                if (e.get(key) or UNSPECIFIED) != want:
                    return False
        return True

    by_id = {e["employee_id"]: e for e in employees}
    keep: set[str] = set()
    for e in employees:
        if not matches(e):
            continue
        keep.add(e["employee_id"])
        seen, mid = set(), e.get("manager_id")
        while mid and mid in by_id and mid not in seen:
            seen.add(mid)
            keep.add(mid)
            mid = by_id[mid].get("manager_id")

    return [e for e in employees if e["employee_id"] in keep]


# ── Metrics ───────────────────────────────────────────────────────────────────

def _breakdown(employees: list[dict], key: str) -> list[dict]:
    counts, fte, vacant = Counter(), defaultdict(float), Counter()
    for e in employees:
        v = _val(e, key)
        counts[v] += 1
        fte[v] += e.get("fte", 1.0) or 0.0
        vacant[v] += 1 if e.get("is_vacant") else 0
    total = sum(counts.values()) or 1
    return [{
        "value": v,
        "headcount": c,
        "fte": round(fte[v], 2),
        "vacant": vacant[v],
        "filled": c - vacant[v],
        "share": round(c / total * 100, 1),
    } for v, c in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))]


def span_buckets(managers: list[dict]) -> list[dict]:
    buckets = [("1", 1, 1), ("2-3", 2, 3), ("4-6", 4, 6), ("7-9", 7, 9),
               ("10-14", 10, 14), ("15+", 15, 10 ** 9)]
    out = []
    for label, lo, hi in buckets:
        out.append({"value": label,
                    "headcount": sum(1 for m in managers if lo <= m["direct_reports"] <= hi)})
    return out


def summarize(index: dict) -> dict:
    """Org-wide KPIs, layer profile and breakdowns across every dimension."""
    employees = list(index["by_id"].values())
    total = len(employees)
    managers = [e for e in employees if e.get("is_manager")]
    vacant = sum(1 for e in employees if e.get("is_vacant"))
    spans = [e["direct_reports"] for e in managers]

    layers = []
    by_level = defaultdict(list)
    for e in employees:
        by_level[e.get("level_no", 1)].append(e)
    for lvl in sorted(by_level):
        people = by_level[lvl]
        lvl_mgrs = [p for p in people if p.get("is_manager")]
        lvl_spans = [p["direct_reports"] for p in lvl_mgrs]
        layers.append({
            "level": lvl,
            "headcount": len(people),
            "managers": len(lvl_mgrs),
            "ics": len(people) - len(lvl_mgrs),
            "vacant": sum(1 for p in people if p.get("is_vacant")),
            "fte": round(sum(p.get("fte", 1.0) or 0 for p in people), 2),
            "avg_span": round(sum(lvl_spans) / len(lvl_spans), 2) if lvl_spans else 0,
            "titles": [t for t, _ in Counter(
                p.get("job_title") or UNSPECIFIED for p in people).most_common(6)],
            "functions": [f for f, _ in Counter(
                p.get("function") or UNSPECIFIED for p in people).most_common(6)],
        })

    return {
        "headcount":      total,
        "filled":         total - vacant,
        "vacant":         vacant,
        "vacancy_rate":   round(vacant / total * 100, 1) if total else 0,
        "total_fte":      round(sum(e.get("fte", 1.0) or 0 for e in employees), 2),
        "managers":       len(managers),
        "ics":            total - len(managers),
        "manager_ratio":  round(len(managers) / total * 100, 1) if total else 0,
        "avg_span":       round(sum(spans) / len(spans), 2) if spans else 0,
        "median_span":    sorted(spans)[len(spans) // 2] if spans else 0,
        "max_span":       max(spans) if spans else 0,
        "layers":         index.get("max_depth", 0),
        "roots":          len(index["roots"]),
        "single_reports": sum(1 for s in spans if s == 1),
        "layer_profile":  layers,
        "span_profile":   span_buckets(managers),
        "breakdowns":     {key: _breakdown(employees, key) for key, _ in DIMENSIONS},
        "issues":         index.get("issues", []),
    }


def position_matrix(index: dict, row_key: str, col_key: str) -> dict:
    """Headcount cross-tab, e.g. job level (rows) by function (columns)."""
    employees = list(index["by_id"].values())
    grid: dict[str, Counter] = defaultdict(Counter)
    for e in employees:
        grid[_val(e, row_key)][_val(e, col_key)] += 1

    cols = [c["value"] for c in _breakdown(employees, col_key)]
    if row_key == "job_level":
        rows = sorted(grid, key=lambda r: (r == UNSPECIFIED, str(r)))
    else:
        rows = [r["value"] for r in _breakdown(employees, row_key)]

    return {
        "row_key": row_key, "col_key": col_key, "rows": rows, "cols": cols,
        "cells": [{"row": r, "values": [grid[r].get(c, 0) for c in cols],
                   "total": sum(grid[r].values())} for r in rows],
        "col_totals": [sum(grid[r].get(c, 0) for r in rows) for c in cols],
        "total": len(employees),
    }
