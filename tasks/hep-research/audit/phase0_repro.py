#!/usr/bin/env python3
"""Phase 0 minimal counterexamples for the validation-gap audit (T01-T08).

Run from the repository root with the core environment:  python3 tasks/hep-research/audit/phase0_repro.py
Prints one JSON line per check: {"id", "reproduces", "detail"}. "reproduces": true means the audited defect
is present in the code being run. After the fixes every entry should print false.
"""
import copy
import json
import subprocess
import sys
import tempfile
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[3] / "plugins" / "hep-research"
sys.path.insert(0, str(PLUGIN))

from contracts.comparison.gate import gate, side_from_artifact  # noqa: E402
from contracts.validate import validate_artifact  # noqa: E402

PRED = json.loads((PLUGIN / "contracts/fixtures/artifacts/valid/prediction.json").read_text())
out = []


def rec(i, bad, detail):
    out.append({"id": i, "reproduces": bool(bad), "detail": detail})


# T01: measurement identical to the prediction's observable, parameter point cleared
def sides(mutate_meas, mutate_both=None):
    p = side_from_artifact(copy.deepcopy(PRED))
    m = side_from_artifact(copy.deepcopy(PRED))
    p["parameter_point"] = {}
    m["parameter_point"] = {}
    if mutate_both:
        mutate_both(p["observable"]), mutate_both(m["observable"])
    mutate_meas(m["observable"])
    return p, m


base = gate(*sides(lambda o: None))
rec("T01.base", not base["comparable"], "identical sides comparable (sanity)")
variants = {
    "a.process": lambda o: o.update(process="synthetic e+ e- -> tau+ tau-"),
    "b.species": lambda o: o.update(species=[{"name": "tau"}]),
    "c.phase_space": lambda o: o.update(phase_space={"definition": "|cos theta| < 0.5 and pT > 20 GeV", "fiducial": True}),
}
for k, f in variants.items():
    r = gate(*sides(f))
    rec(f"T01.{k}", r["comparable"], r["mismatches"][:1])
two = lambda o: o["variables"].append({"name": "sqrt_s", "unit": "GeV", "edges": [80.0, 90.0, 100.0]})
r = gate(*sides(lambda o: o["variables"].__setitem__(1, {"name": "pT", "unit": "TeV", "edges": [0.0, 1.0, 5.0]}), two))
rec("T01.d.second_axis", r["comparable"], r["mismatches"][:1])

# T02
def val_variant(f):
    d = copy.deepcopy(PRED)
    f(d["extension"])
    rep = validate_artifact(d)
    return rep.ok, [x.code for x in rep.errors]
for k, f in {"a.edges": lambda e: e["values"].__setitem__("edges", [-1.0, -0.4, 0.0, 0.5, 1.0]),
             "b.unit": lambda e: e["values"].__setitem__("unit", "fb"),
             "c.no_values": lambda e: e.pop("values"),
             "d.nan": lambda e: e["values"]["values"].__setitem__(0, float("nan"))}.items():
    ok, codes = val_variant(f)
    rec(f"T02.{k}", ok, codes)

# T03
with tempfile.TemporaryDirectory() as td:
    p = Path(td) / "fit.json"
    p.write_text(json.dumps({"data": [10, 10], "templates": {"sig": [10, 0]}}))
    cp = subprocess.run([sys.executable, str(PLUGIN / "core/stats/template_fit.py"), "bb-fit", "--input", str(p)],
                        capture_output=True, text=True)
    try:
        res = json.loads(cp.stdout)
    except ValueError:
        res = {"raw": cp.stdout[-300:]}
    rec("T03.infeasible", cp.returncode == 0 and res.get("status") == "ok",
        {"exit": cp.returncode, "status": res.get("status"), "bb_yield": (res.get("barlow_beeston") or {}).get("sig")})

# T04
import numpy as np  # noqa: E402
from core.blinding.blinding import scan_paths  # noqa: E402
with tempfile.TemporaryDirectory() as td:
    f = Path(td) / "cache.npy"
    np.save(f, np.array([1.0, 1234.567, 3.0]))
    try:
        r = scan_paths([f], [1234.567])
        rec("T04.A.npy", not r["leaks"], r)
    except Exception as exc:  # noqa: BLE001
        rec("T04.A.npy", True, f"{type(exc).__name__}: {exc}")
    g = Path(td) / "hist.root"
    g.write_bytes(b"root")
    r = scan_paths([g], [1234.567])
    rec("T04.B.unscanned_ok", r.get("ok") is True and not r["scanned"], {k: r.get(k) for k in ("ok", "status", "scanned")})

# T05
d = copy.deepcopy(PRED)
d["inputs"] = [{"ref": "does/not/exist.json", "artifact_type": "theory-spec", "sha256": "not-a-hash", "status": ["synthetic"]}]
rep = validate_artifact(d)
try:
    from contracts import dependencies  # noqa: F401
    have_layer = True
except ImportError:
    have_layer = False
rec("T05.dangling_ref", rep.ok and not have_layer, {"schema_ok": rep.ok, "project_validator": have_layer})

# T06
sys.path.insert(0, str(PLUGIN / "skills/physics-ml/scripts"))
import check_split_integrity as csi  # noqa: E402
a = csi.check({"train": ["a"], "test": ["b"]})
b = csi.check({"train": ["a"], "test": ["b"], "groups": {"a": "run1"}})
rec("T06.no_groups", a["passed"] is True and a.get("status") in (None, "passed"), {"passed": a["passed"], "status": a.get("status")})
rec("T06.partial_groups", b["passed"] is True and b["groups_checked"] is True,
    {"passed": b["passed"], "groups_checked": b["groups_checked"], "status": b.get("status")})

# T08
with tempfile.TemporaryDirectory() as td:
    (Path(td) / "main.tex").write_text("A claim \\cite{Nonexistent}.\n")
    cp = subprocess.run([sys.executable, str(PLUGIN / "skills/research-communication/scripts/check_manuscript.py"), td],
                        capture_output=True, text=True)
    rec("T08.no_bib", cp.returncode == 0, {"exit": cp.returncode, "tail": cp.stdout.strip().splitlines()[-1]})

# T07: label check (no numerical demonstration of undercoverage is attempted here)
from core.stats import likelihood_limits as ll  # noqa: E402
src = (PLUGIN / "core/stats/likelihood_limits.py").read_text()
res = ll.neyman_limit(3, 3.0, 2.0, 0.95, 0.01, 200, 1, 5)
rec("T07.guarantee_label", "guarantee" in res["method"].lower() or "guaranteed coverage" in src,
    {"method": res["method"]})
rec("T07.truncated_aux", "max(b_true + sig * z, 0.0)" in src, "Gaussian aux observation truncated at 0 in the Berger-Boos toys")

for o in out:
    print(json.dumps(o, default=str))
