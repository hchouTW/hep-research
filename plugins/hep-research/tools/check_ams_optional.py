#!/usr/bin/env python3
"""AMS optionality check (task M3.5, AC09): copy the plugin to a temporary folder without the AMS-02 profile and
without its registry entry, then run Path B, Path C, the registry validator and the generic test suites
(core, contracts, hep-statistics, hep-computing) there. Exit 0 when all pass; prints a JSON summary.

Usage: python3 tools/check_ams_optional.py [--keep]
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AMS = "experiment:ams-02"


def run(name, cmd, cwd):
    p = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True)
    return {"name": name, "exit_code": p.returncode, "status": "pass" if p.returncode == 0 else "fail",
            "tail": (p.stdout + p.stderr)[-1200:] if p.returncode else ""}


def main(argv=None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    tmp = Path(tempfile.mkdtemp(prefix="hep research no ams "))  # a path with spaces on purpose
    dst = tmp / "hep-research"
    ams_dir = None
    reg = json.loads((ROOT / "profiles" / "registry.json").read_text(encoding="utf-8"))
    for p in reg["profiles"]:
        if p["id"] == AMS:
            ams_dir = (ROOT / "profiles" / p["path"]).resolve()
    shutil.copytree(ROOT, dst, ignore=lambda d, names: [n for n in names if n in ("__pycache__", "output")
                                                           or (ams_dir and (Path(d) / n).resolve() == ams_dir)])
    reg["profiles"] = [p for p in reg["profiles"] if p["id"] != AMS]
    (dst / "profiles" / "registry.json").write_text(json.dumps(reg, indent=1) + "\n", encoding="utf-8")
    py = sys.executable
    out = tmp / "outputs"
    checks = [
        {"name": "ams_profile_absent", "status": "pass" if not (dst / "profiles" / "experiments" / "ams-02").exists()
         and AMS not in (dst / "profiles" / "registry.json").read_text() else "fail"},
        run("registry", [py, "contracts/registry.py"], dst),
        run("path_b", [py, "examples/collider-angular/run.py", "--out", str(out / "b")], dst),
        run("path_c", [py, "examples/qed-prediction/run.py", "--out", str(out / "c")], dst),
        run("tests_core", [py, "-m", "unittest", "discover", "-s", "tests/core", "-t", "."], dst),
        run("tests_contracts", [py, "-m", "unittest", "discover", "-s", "tests/contracts", "-t", "."], dst),
        run("tests_hep_statistics", [py, "-m", "unittest", "discover", "-s", "tests/skills/hep_statistics", "-t", "."], dst),
        run("tests_hep_computing", [py, "-m", "unittest", "discover", "-s", "tests/skills/hep_computing", "-t", "."], dst),
        run("tests_paths_b_c", [py, "-m", "unittest", "tests.examples.test_collider_angular", "tests.examples.test_qed_prediction"], dst),
    ]
    for prof in ("experiments/synthetic-collider", "theory/qed-benchmark"):
        checks.append(run(f"profile-tests:{prof}", [py, "-m", "unittest", "discover", "-s", "tests", "-t", "tests"], dst / "profiles" / prof))
    ok = all(c["status"] == "pass" for c in checks)
    print(json.dumps({"ok": ok, "copy": str(dst), "checks": checks}, indent=1))
    if "--keep" not in args:
        shutil.rmtree(tmp, ignore_errors=True)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
