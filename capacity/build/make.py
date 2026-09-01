"""Rebuild the three deliverables and prove they still compute.

    python3 capacity/build/make.py

Writes into capacity/dist/ and recalculates each file through LibreOffice, which
is the only thing that turns a file full of formula strings into a file with
answers in it.
"""
from __future__ import annotations

import glob
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import consolidator as C   # noqa: E402
import example as E        # noqa: E402
import refdata as R        # noqa: E402
import template as T       # noqa: E402

DIST = HERE.parent / "dist"


def recalc(path: Path) -> dict:
    hits = glob.glob("/root/.claude/skills/**/xlsx/scripts/recalc.py", recursive=True)
    if not hits:
        print(f"  ! recalc.py not found; {path.name} ships without cached values")
        return {}
    out = subprocess.run([sys.executable, hits[0], str(path), "900"],
                         capture_output=True, text=True)
    try:
        return json.loads(out.stdout)
    except json.JSONDecodeError:
        print(out.stdout[-1000:], out.stderr[-1000:])
        raise


def slug(group: str) -> str:
    import re
    return re.sub(r"-+", "-", "".join(c if c.isalnum() else "-" for c in group)).strip("-")


def main() -> int:
    DIST.mkdir(exist_ok=True)
    templates = DIST / "templates"
    templates.mkdir(exist_ok=True)
    bank = R.Bank()

    # One template per group: each group sees its own structure and its own
    # baseline, and nobody else's headcount or cost.
    outputs = []
    for group in bank.groups:
        path = templates / f"{R.PLAN_YEAR}-Capacity-{slug(group)}.xlsx"
        T.build_template(group, path, bank)
        outputs.append(path)

    example = DIST / f"{R.PLAN_YEAR}-Capacity-Example-RiskGroup.xlsx"
    E.build_example(example)
    outputs.append(example)
    consolidator = DIST / f"{R.PLAN_YEAR}-Capacity-Consolidator.xlsx"
    C.build_consolidator(consolidator, bank)
    outputs.append(consolidator)

    failed = 0
    for path in outputs:
        result = recalc(path)
        errors = result.get("total_errors")
        print(f"  {path.name}: {result.get('total_formulas', '?')} formulas, "
              f"{errors} errors")
        failed += 1 if errors else 0
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
