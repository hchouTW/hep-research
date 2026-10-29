#!/usr/bin/env python3
"""Retired: the cross-artifact analysis check (freeze, check, summary, snapshots gc).

The check was retired (docs/dev/cross-artifact-check/decision-retire.md): its value gate found no error it catches that
the closure tests and contract checks miss. Every command is refused with that reason; read or reproduce an old bundle
or report with the last release that has the check. Review questions that came from its rules are in
skills/hep-measurement/references/review-and-artifacts.md and skills/hep-statistics/references/combinations.md.

Usage: python3 contracts/analysis_check.py ...   (always exit 2)
This pointer is removed in the next minor release.
"""
from __future__ import annotations

import json
import sys

REASON = ("the cross-artifact analysis check was retired (docs/dev/cross-artifact-check/decision-retire.md); "
          "reproduce old bundles and reports with the last release that has the check")


def main(argv=None) -> int:
    print(json.dumps({"status": "retired", "error": REASON}))
    return 2


if __name__ == "__main__":
    sys.exit(main())
