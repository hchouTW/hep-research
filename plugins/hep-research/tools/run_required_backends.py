#!/usr/bin/env python3
"""Run the statistics test modules with required backends: a missing backend is a failure, never a silent skip.

The fast-tier tests skip a backend-dependent test when the backend is not installed (unverified, not passing). A
gate that promises a backend must not pass through such skips. This tool (1) checks that each required backend
imports at its pinned version, (2) runs the statistics and backend test modules, and (3) fails if any test fails or
errors, or if any skip reason names a required backend.

Usage: python3 tools/run_required_backends.py --require pyhf==0.7.6,arviz==0.23.4 [--modules M1,M2] [--out REPORT.json]
       (a requirement exe:NAME is an executable that must be on PATH, for example exe:combine)
Exit codes: 0 every required backend present and no test failed or skipped for it; 1 otherwise; 2 bad usage.
"""
from __future__ import annotations

import argparse
import importlib
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULES = [
    "tests.core.test_stats_p0_regressions", "tests.core.test_stats_counting_asymptotic_oracles",
    "tests.core.test_stats_toy_ensemble", "tests.core.test_stats_unfolding_outer", "tests.core.test_stats_weighted_mc",
    "tests.core.test_stats_interpolation", "tests.contracts.test_statistical_semantics",
    "tests.adapters.test_backend_likelihood_equivalence", "tests.adapters.test_sr_cr_model_card",
    "tests.adapters.test_pyhf_counting", "tests.adapters.test_pyhf_shape", "tests.adapters.test_pyhf_publication",
    "tests.adapters.test_pyhf_published_reproduction", "tests.adapters.test_pyhf_nuisance_diagnostics",
    "tests.adapters.test_nuisance_interpolation", "tests.skills.hep_statistics.test_bayes_arviz_oracle",
    "tests.skills.hep_statistics.test_result_artifact", "tests.examples.test_stats_benchmarks",
]


def parse_require(text: str) -> dict[str, str | None]:
    out: dict[str, str | None] = {}
    for item in filter(None, (x.strip() for x in text.split(","))):
        name, _, version = item.partition("==")
        out[name] = version or None
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--require", required=True, help="comma-separated name==version (version optional)")
    ap.add_argument("--modules", help="comma-separated test modules (default: the statistics and backend modules)")
    ap.add_argument("--out")
    a = ap.parse_args(argv)
    required = parse_require(a.require)
    if not required:
        print(json.dumps({"ok": False, "error": "--require names no backend"}))
        return 2
    report: dict = {"required": required, "backends": {}, "problems": []}
    import shutil
    for name, version in required.items():
        if name.startswith("exe:"):
            path = shutil.which(name[4:])
            report["backends"][name] = path
            if not path:
                report["problems"].append(f"executable {name[4:]} is required but not on PATH")
            continue
        try:
            mod = importlib.import_module(name)
            got = getattr(mod, "__version__", None)
            report["backends"][name] = got
            if version and got != version:
                report["problems"].append(f"{name} {got} installed, {version} required")
        except ImportError as exc:
            report["backends"][name] = None
            report["problems"].append(f"{name} is required but not importable: {exc}")
    sys.path.insert(0, str(ROOT))
    modules = [m for m in (a.modules.split(",") if a.modules else MODULES) if m]
    suite = unittest.defaultTestLoader.loadTestsFromNames(modules)
    result = unittest.TextTestRunner(stream=sys.stderr, verbosity=1).run(suite)
    names = [n[4:] if n.startswith("exe:") else n for n in required]
    skipped_for_backend = [f"{t.id()}: {why}" for t, why in result.skipped if any(n.lower() in why.lower() for n in names)]
    report.update({"run": result.testsRun, "failures": len(result.failures), "errors": len(result.errors),
                   "skipped": len(result.skipped), "skipped_for_a_required_backend": skipped_for_backend})
    if result.failures or result.errors:
        report["problems"].append(f"{len(result.failures)} failures and {len(result.errors)} errors")
    if skipped_for_backend:
        report["problems"].append("tests skipped for a required backend: " + "; ".join(skipped_for_backend))
    report["ok"] = not report["problems"]
    text = json.dumps(report, indent=1)
    if a.out:
        Path(a.out).write_text(text + "\n")
    print(text)
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
