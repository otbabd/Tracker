"""Every check, in one command."""
from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_build
import test_consolidator
import test_template


def main() -> int:
    started = time.time()
    failures = 0
    failures += test_build.run().report()

    test_template.SCRATCH.mkdir(parents=True, exist_ok=True)
    example = test_template.prepare(test_template.SCRATCH / "example-check.xlsx")
    failures += test_template.run(example).report()
    failures += test_template.run_gate(
        example, test_template.SCRATCH / "example-broken.xlsx").report()

    filled = test_consolidator.prepare(test_consolidator.SCRATCH / "filled.xlsx")
    failures += test_consolidator.run(filled).report()

    print(f"\n{'FAILED' if failures else 'All good'} in {time.time() - started:.0f}s")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
