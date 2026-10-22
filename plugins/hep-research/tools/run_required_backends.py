#!/usr/bin/env python3
"""Run the statistics test modules with required backends: a missing backend is a failure, never a silent skip.

The fast-tier tests skip a backend-dependent test when the backend is not installed (unverified, not passing). A
gate that promises a backend must not pass through such skips. This tool (1) checks that each required backend
imports at its pinned version, (2) runs the statistics and backend test modules, and (3) fails if any test fails or
errors, or if any skip reason names a required backend. With --no-skips every skip fails, whatever its reason: for
evidence modules that must run in full, such as the slow-tier sci-fix evidence in the release gate.

With --from-ledger the tests are the oracle nodes of the sci-fix ledger (docs/evidence/sci-fixes.json, every
`independence[].test`), each run on its own; their modules are reported, with those missing from MODULES. A node that
does not pass is classified by the `requires` its records state: a missing core dependency is an environment error, a
missing backend leaves the evidence unverified, any other failure or error means the evidence does not hold (a
module missing that no record declares is an environment error too); another skip is a skip. Environment errors and
evidence that does not hold fail the run; with --no-skips so do unverified and skipped nodes, and so does an
unverified node whose backend --require names. --require is optional with --from-ledger.

Usage: python3 tools/run_required_backends.py --require pyhf==0.7.6,arviz==0.23.4 [--modules M1,M2] [--no-skips]
       [--allow-skip-reason TEXT ...] [--out REPORT.json]
       python3 tools/run_required_backends.py --from-ledger [LEDGER] [--require ...] [--no-skips] [--out REPORT.json]
       (--allow-skip-reason: a test meant for the backend's absence, skipped where it is installed, is not a skip for
       the backend; the gates without the backend run it)
       (a requirement exe:NAME is an executable that must be on PATH, for example exe:combine; a name without a
       version only has to import)
Exit codes: 0 every required backend present and no test failed or skipped for it; 1 otherwise; 2 bad usage.
"""
from __future__ import annotations

import argparse
import importlib
import importlib.util
import json
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / "docs" / "evidence" / "sci-fixes.json"
CLASSES = ("pass", "environment-error", "unverified", "does-not-hold", "skipped")
MODULES = [
    "tests.core.test_stats_p0_regressions", "tests.core.test_stats_counting_asymptotic_oracles",
    "tests.core.test_stats_toy_ensemble", "tests.core.test_stats_unfolding_outer", "tests.core.test_stats_weighted_mc",
    "tests.core.test_stats_interpolation", "tests.core.test_stats_linalg", "tests.core.test_properties",
    "tests.contracts.test_statistical_semantics",
    "tests.adapters.test_backend_likelihood_equivalence", "tests.adapters.test_sr_cr_model_card",
    "tests.adapters.test_pyhf_counting", "tests.adapters.test_pyhf_shape", "tests.adapters.test_pyhf_publication",
    "tests.adapters.test_pyhf_published_reproduction", "tests.adapters.test_pyhf_nuisance_diagnostics",
    "tests.adapters.test_pyhf_adapter_statuses",
    "tests.adapters.test_nuisance_interpolation", "tests.skills.hep_statistics.test_bayes_arviz_oracle",
    "tests.skills.hep_statistics.test_result_artifact", "tests.examples.test_stats_benchmarks",
    "tests.skills.hep_ml.test_audit_metric_layer", "tests.skills.hep_ml.test_domain_shift_report",  # pyhf oracles
]


def parse_require(text: str) -> dict[str, str | None]:
    out: dict[str, str | None] = {}
    for item in filter(None, (x.strip() for x in text.split(","))):
        name, _, version = item.partition("==")
        out[name] = version or None
    return out


def version_matches(installed, required: str) -> bool:
    """name==required as PEP 440 reads it for a local label: '2.14.1' matches '2.14.1+cpu' (a requirement without a
    label ignores the installed one's), while '2.14.1+cpu' must match exactly."""
    if not isinstance(installed, str):
        return False
    return installed == required or ("+" not in required and installed.split("+", 1)[0] == required)


def ledger_nodes(path: Path) -> dict[str, dict]:
    """The ledger's oracle nodes ('file.py::Class::method'), each with the entries that cite it and the union of the
    core and backend dependencies their records require, in ledger order."""
    doc = json.loads(Path(path).read_text(encoding="utf-8"))
    nodes: dict[str, dict] = {}
    for fix in doc["fixes"]:
        for rec in fix.get("independence", []):
            node = nodes.setdefault(rec["test"], {"entries": [], "core": [], "backend": []})
            if fix["id"] not in node["entries"]:
                node["entries"].append(fix["id"])
            req = rec.get("requires") or {}
            for part in ("core", "backend"):
                node[part] += [n for n in req.get(part, []) if n not in node[part]]
    return nodes


def node_module(node: str) -> str:
    return ".".join(Path(node.split("::")[0]).with_suffix("").parts)


def _missing(names) -> list[str]:
    out = []
    for name in names:
        try:
            if importlib.util.find_spec(name) is None:
                out.append(name)
        except (ImportError, ValueError):
            out.append(name)
    return out


def classify(outcome: str, text: str, core: list, backend: list) -> tuple[str, str]:
    """(class, reason) of one node's outcome ('pass', 'fail', 'error' or 'skip'; text: the traceback or skip reason)."""
    if outcome == "pass":
        return "pass", ""
    missing_core, missing_backend = _missing(core), _missing(backend)
    if missing_core:
        return "environment-error", "core dependency missing: " + ", ".join(missing_core)
    if missing_backend:
        return "unverified", "backend missing: " + ", ".join(missing_backend)
    absent = re.search(r"ModuleNotFoundError: No module named '([^'.]+)", text)
    if outcome == "error" and absent:
        return "environment-error", f"module {absent.group(1)} missing and not in the records' requires"
    last = text.strip().splitlines()[-1] if text.strip() else ""
    if outcome == "skip":
        return "skipped", text
    return "does-not-hold", f"{outcome}: {last}"


def run_ledger(path: Path, required: dict, no_skips: bool) -> dict:
    nodes = ledger_nodes(path)
    modules = list(dict.fromkeys(node_module(n) for n in nodes))
    results = []
    for node, info in nodes.items():
        file, cls, meth = node.split("::")
        loader = unittest.TestLoader()
        suite = loader.loadTestsFromName(f"{node_module(node)}.{cls}.{meth}")
        res = unittest.TestResult()
        suite.run(res)
        if res.errors or loader.errors:
            outcome, text = "error", res.errors[0][1] if res.errors else loader.errors[0]
        elif res.failures:
            outcome, text = "fail", res.failures[0][1]
        elif res.skipped:
            outcome, text = "skip", res.skipped[0][1]
        elif res.testsRun:
            outcome, text = "pass", ""
        else:
            outcome, text = "error", "no test ran for this node"
        kind, reason = classify(outcome, text, info["core"], info["backend"])
        results.append({"node": node, "entries": info["entries"], "requires": {"core": info["core"],
                        "backend": info["backend"]}, "outcome": outcome, "class": kind, "reason": reason})
    counts = {c: sum(r["class"] == c for r in results) for c in CLASSES}
    failing = {"environment-error", "does-not-hold"} | ({"unverified", "skipped"} if no_skips else set())
    problems = [f"{r['node']}: {r['class']} ({r['reason']})" for r in results if r["class"] in failing]
    names = {n[4:] if n.startswith("exe:") else n for n in required}
    problems += [f"{r['node']}: unverified for a required backend ({r['reason']})" for r in results
                 if r["class"] == "unverified" and r["class"] not in failing
                 and set(_missing(r["requires"]["backend"])) & names]
    return {"ledger": str(path), "nodes": len(results), "modules": modules,
            "modules_not_in_MODULES": [m for m in modules if m not in MODULES], "classes": counts,
            "node_results": results, "ledger_problems": problems}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--require", help="comma-separated name==version (version optional); required without --from-ledger")
    source = ap.add_mutually_exclusive_group()
    source.add_argument("--modules", help="comma-separated test modules (default: the statistics and backend modules)")
    source.add_argument("--from-ledger", nargs="?", const=str(LEDGER), metavar="LEDGER",
                        help="run the sci-fix ledger's oracle nodes (default ledger: docs/evidence/sci-fixes.json)")
    ap.add_argument("--no-skips", action="store_true", help="fail on any skipped test, whatever its reason")
    ap.add_argument("--allow-skip-reason", action="append", default=[], metavar="TEXT",
                    help="a skip whose reason contains TEXT does not count as skipped for a backend (a test meant "
                         "for the backend's absence, run by the gates without it); repeatable")
    ap.add_argument("--out")
    a = ap.parse_args(argv)
    required = parse_require(a.require or "")
    if not required and not a.from_ledger:
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
            if version and not version_matches(got, version):
                report["problems"].append(f"{name} {got} installed, {version} required")
        except ImportError as exc:
            report["backends"][name] = None
            report["problems"].append(f"{name} is required but not importable: {exc}")
    sys.path.insert(0, str(ROOT))
    if a.from_ledger:
        report.update(run_ledger(Path(a.from_ledger), required, a.no_skips))
        report["problems"] += report.pop("ledger_problems")
        report["ok"] = not report["problems"]
        text = json.dumps(report, indent=1)
        if a.out:
            Path(a.out).write_text(text + "\n")
        print(text)
        return 0 if report["ok"] else 1
    modules = [m for m in (a.modules.split(",") if a.modules else MODULES) if m]
    suite = unittest.defaultTestLoader.loadTestsFromNames(modules)
    result = unittest.TextTestRunner(stream=sys.stderr, verbosity=1).run(suite)
    names = [n[4:] if n.startswith("exe:") else n for n in required]
    allowed = [f"{t.id()}: {why}" for t, why in result.skipped if any(s in why for s in a.allow_skip_reason)]
    skipped_for_backend = [f"{t.id()}: {why}" for t, why in result.skipped
                           if any(n.lower() in why.lower() for n in names)
                           and not any(s in why for s in a.allow_skip_reason)]
    report.update({"run": result.testsRun, "failures": len(result.failures), "errors": len(result.errors),
                   "skipped": len(result.skipped), "skipped_for_a_required_backend": skipped_for_backend,
                   "skips_allowed_by_reason": allowed})
    if result.failures or result.errors:
        report["problems"].append(f"{len(result.failures)} failures and {len(result.errors)} errors")
    if skipped_for_backend:
        report["problems"].append("tests skipped for a required backend: " + "; ".join(skipped_for_backend))
    if a.no_skips and result.skipped:
        report["skipped_tests"] = [f"{t.id()}: {why}" for t, why in result.skipped]
        report["problems"].append(f"{len(result.skipped)} tests skipped where --no-skips allows none")
    report["ok"] = not report["problems"]
    text = json.dumps(report, indent=1)
    if a.out:
        Path(a.out).write_text(text + "\n")
    print(text)
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
