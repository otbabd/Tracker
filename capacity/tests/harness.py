"""Small test harness. No framework: one function to assert with, one to report.

Every workbook here is full of formulas, so a test that only reads the file
proves nothing. The rule throughout: recalculate through LibreOffice first, then
read the values back and check them against arithmetic done independently in
Python.
"""
from __future__ import annotations

import glob
import json
import subprocess
import sys
from pathlib import Path

BUILD = Path(__file__).resolve().parents[1] / "build"
sys.path.insert(0, str(BUILD))

ERRORS = ("#REF!", "#VALUE!", "#DIV/0!", "#N/A", "#NAME?", "#NUM!", "#NULL!")


def recalc_script() -> str:
    hits = glob.glob("/root/.claude/skills/**/xlsx/scripts/recalc.py", recursive=True)
    if not hits:
        raise RuntimeError("recalc.py not found")
    return hits[0]


def recalc(path, timeout: int = 900) -> dict:
    out = subprocess.run(
        [sys.executable, recalc_script(), str(path), str(timeout)],
        capture_output=True, text=True)
    try:
        return json.loads(out.stdout)
    except json.JSONDecodeError:
        raise RuntimeError(f"recalc gave no JSON: {out.stdout[-2000:]}{out.stderr[-2000:]}")


class Run:
    def __init__(self, name: str):
        self.name = name
        self.passed = 0
        self.failures: list[str] = []

    def check(self, ok: bool, what: str, detail: str = "") -> bool:
        if ok:
            self.passed += 1
        else:
            self.failures.append(f"{what}{(' — ' + detail) if detail else ''}")
        return ok

    def close(self, tol: float, got, want, what: str) -> bool:
        try:
            ok = abs(float(got or 0) - float(want)) <= tol
        except (TypeError, ValueError):
            ok = False
        return self.check(ok, what, f"got {got!r}, expected {want!r}")

    def equal(self, got, want, what: str) -> bool:
        return self.check(got == want, what, f"got {got!r}, expected {want!r}")

    def report(self) -> int:
        if self.failures:
            print(f"FAIL  {self.name}: {len(self.failures)} of "
                  f"{self.passed + len(self.failures)} checks failed")
            for f in self.failures:
                print(f"        {f}")
            return 1
        print(f"ok    {self.name}: {self.passed} checks")
        return 0


def error_cells(wb, limit: int = 20) -> list[str]:
    """Any cell that recalculated to an Excel error, named."""
    bad = []
    for ws in wb.worksheets:
        for row in ws.iter_rows():
            for c in row:
                if isinstance(c.value, str) and c.value in ERRORS:
                    bad.append(f"{ws.title}!{c.coordinate}={c.value}")
                    if len(bad) >= limit:
                        return bad
    return bad
