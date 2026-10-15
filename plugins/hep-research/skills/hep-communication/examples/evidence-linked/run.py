#!/usr/bin/env python3
"""Worked example of evidence-linked writing (synthetic): run the communication checks over the example project and
write their reports. Usage: python3 run.py [--out-dir DIR] (default: output/ next to this file). Read-only on the
project; every path in the reports is relative, so the output is reproducible on any machine."""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPTS = HERE.parents[1] / "scripts"
STEPS = [
    ("01-check-communication", "check_communication.py", ["artifacts/comm.json", "--project-root", ".", "--checks", "manuscript"]),
    ("02-audit-claims", "audit_claims.py", ["artifacts/comm.json", "--project-root", "."]),
    ("03-revision-impact", "track_revision_impact.py", ["artifacts/comm.json", "artifacts/comm_v2.json", "--project-root", "."]),
    ("04-responses", "check_adaptation.py", ["artifacts/comm_v2.json", "--project-root", ".", "--responses"]),
    ("05-unresolved-source", "check_communication.py", ["artifacts/comm_v3.json", "--project-root", "."]),
]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out-dir", type=Path, default=HERE / "output")
    args = ap.parse_args(argv)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    summary = {"note": "synthetic worked example; statuses are the tools' outcomes on placeholder data", "steps": {}}
    env = dict(os.environ)
    for name, script, cli in STEPS:
        run = subprocess.run([sys.executable, str(SCRIPTS / script), *cli], cwd=str(HERE / "project"), capture_output=True, text=True, env=env, timeout=300)
        try:
            rep = json.loads(run.stdout)
        except ValueError:
            print(f"{name}: no JSON report (exit {run.returncode}): {run.stderr[-500:]}", file=sys.stderr)
            return 1
        (args.out_dir / f"{name}.json").write_text(json.dumps(rep, indent=1, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
        summary["steps"][name] = {"script": script, "args": cli, "status": rep["status"], "exit_code": run.returncode,
                                  "findings": sorted({f["code"] for f in rep["findings"]})}
        print(f"{name}: {rep['status']} (exit {run.returncode})")
    (args.out_dir / "summary.json").write_text(json.dumps(summary, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
