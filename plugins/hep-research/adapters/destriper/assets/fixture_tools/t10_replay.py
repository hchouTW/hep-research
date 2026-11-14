#!/usr/bin/env python3
"""Scoring side of T10's destriping replay: helpers the stage 4 job calls (docs/dev/detector-reconstruction/t10-replay-stage-plan.md,
sections 3 and 4). The data side never imports this module.

Operations:
  negatives        apply each negative variant (t10_fixture.NEGATIVE_VARIANTS) to a solver product's embedded scan product, and the
                   disconnected claim, and check that contracts.reconstruction.read_sidecar refuses each with its code
  halved-stopping  print the halving run's stopping value eps_h = eps / 2 from the nominal product (C4, amendment C4-1)
  reference-equals-truth  check that the exact reference of a noiseless fixture equals its truth exactly (the noiseless truth sums to
                   zero, so it is the constrained solution)
  null-mode-drift  the runtime null-mode case (stage plan S13): plain conjugate gradient with no zero-sum projection, started at a = 0 and
                   at a = c 1, leaves the offset where the start put it; the recipe's projected run returns mean 0
  records          write an artifacts_dir: each product's embedded reconstruction-product/1 as <stem>.scan-product.json and one
                   computational-run artifact that refers to them by path, for contracts/validate.py <dir>
  timing           time read_sidecar on each product's embedded scan product

Output: one JSON object per operation with "status"; exit 0 ok, 1 a negative variant was not refused, 2 bad input.
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
PLUGIN = HERE.parents[3]
for folder in (PLUGIN, HERE):
    if str(folder) not in sys.path:
        sys.path.insert(0, str(folder))

import t10_fixture  # noqa: E402
from contracts import CONTRACTS_VERSION  # noqa: E402
from contracts.reconstruction import read_sidecar  # noqa: E402

DISCONNECTED_CODES = ("reconstruction.scan.unidentifiable_unnamed", "reconstruction.scan.unique_claim")


def claimed_disconnected_product(seed: int = 20260) -> dict:
    """The fixture's disconnected scan as a product that claims the zero-sum constraint determines everything: unidentifiable [] and
    a uniqueness claim. The values reported are placeholders (0): the contract refuses the claim before any value matters."""
    timestream, _ = t10_fixture.generate("disconnected", seed)
    pixels, length = timestream["pixels"], timestream["baseline_length"]
    baselines = len(timestream["pixel"]) // length
    width = pixels + baselines
    design = []
    for t, p in enumerate(timestream["pixel"]):
        row = [0] * width
        row[p], row[pixels + t // length] = 1, 1
        design.append(row)
    names = [f"map-{p}" for p in range(pixels)] + [f"baseline-{b}" for b in range(baselines)]
    scan = {"subcase": "global", "source_ref": "t10-destripe/1 disconnected", "coordinates": [{"axis": "sample-index", "kind": "index", "unit": "1"}],
            "conditions_ref": "none", "response_ref": "pointing", "noise_model": {"kind": "white-uniform", "premises": ["stated"]},
            "merging": {"kind": "joint-model"}, "unidentifiable": [],
            "model": {"parameters": names, "design": design, "observation": timestream["value"]},
            "reported": [{"weights": [1] * pixels + [0] * baselines, "value": 0.0}],
            "constraint": {"statement": "zero-sum of the baselines", "weights": [0] * pixels + [1] * baselines, "value": 0},
            "regularization": "none", "uniqueness_claim": True}
    return {"schema": "reconstruction-product/1", "product_id": "product.t10-disconnected-claimed", "revision": 1, "collection": "destriped-map",
            "native": {"type": "destriper::ScanSolution"}, "presence": "present", "role": "reconstruction-input", "conditions_used": [],
            "required_extensions": ["reconstruction:scan-v1"], "scan": scan}


def _load(path: Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def negatives(product_path: Path) -> tuple[bool, list[dict]]:
    embedded = _load(product_path)["reconstruction_product"]
    rows = []
    for name, (_, code) in t10_fixture.NEGATIVE_VARIANTS.items():
        codes = sorted({f.code for f in read_sidecar(t10_fixture.negative_variant(embedded, name)).errors})
        rows.append({"variant": name, "expected": [code], "codes": codes, "refused": code in codes})
    codes = sorted({f.code for f in read_sidecar(claimed_disconnected_product()).errors})
    rows.append({"variant": "disconnected-claimed-determined", "expected": list(DISCONNECTED_CODES), "codes": codes,
                 "refused": set(DISCONNECTED_CODES) <= set(codes)})
    return all(row["refused"] for row in rows), rows


def halved_stopping(product_path: Path) -> float:
    return _load(product_path)["solver"]["stopping"] / 2


def reference_equals_truth(reference: dict, truth: dict) -> bool:
    """Exact equality of the reference's map and baselines (exact "p/q" strings) with the truth's integers."""
    from fractions import Fraction
    found = [Fraction(item["exact"]) for item in reference["map"]], [Fraction(item["exact"]) for item in reference["baselines"]]
    return found == ([Fraction(v) for v in truth["map"]], [Fraction(v) for v in truth["baselines"]])


def _plain_conjugate_gradient(stream, operator, right, start, stopping: float, budget: int):
    """Textbook conjugate gradient on D a = right with no projection (the null mode is left free), from a given start."""
    import numpy
    a = numpy.array(start, dtype=float)
    size = float(numpy.linalg.norm(right))
    residual = right - operator(stream, a)
    direction = residual.copy()
    relative = float(numpy.linalg.norm(residual)) / size
    iterations = 0
    while relative > stopping and iterations < budget:
        image = operator(stream, direction)
        curvature = float(direction @ image)
        if not curvature > 0.0:
            residual = right - operator(stream, a)
            direction = residual.copy()
            iterations += 1
            continue
        step = float(residual @ residual) / curvature
        a = a + step * direction
        updated = residual - step * image
        direction = updated + (float(updated @ updated) / float(residual @ residual)) * direction
        residual = updated
        iterations += 1
        relative = float(numpy.linalg.norm(right - operator(stream, a))) / size
    return a, relative, iterations


def null_mode_drift(document: dict, stopping: float = 1e-10, offset: float = 7.0) -> dict:
    """S13: without the constraint the start, not the data, sets the common offset; with it (the recipe) the mean is 0."""
    import numpy
    sys.path.insert(0, str(HERE.parent))
    from destripe_recipe import solver, timestream
    stream = timestream.read(document)
    hits = numpy.bincount(stream.pixel, minlength=stream.pixels)
    samples = stream.value - (numpy.bincount(stream.pixel, weights=stream.value, minlength=stream.pixels) / hits)[stream.pixel]  # Z y
    right = samples.reshape(stream.baselines, stream.length).sum(axis=1)  # F^T Z y, not projected
    budget = 10 * stream.baselines
    runs = [_plain_conjugate_gradient(stream, solver.reduced_operator, right, numpy.full(stream.baselines, c), stopping, budget) for c in (0.0, offset)]
    (first, r0, _), (second, r1, _) = runs
    demeaned = float(numpy.linalg.norm((second - second.mean()) - (first - first.mean())))
    recipe = solver.solve(stream, stopping=stopping, max_iterations=budget)
    result = {"offset": offset, "means": [float(first.mean()), float(second.mean())], "mean_difference": float(second.mean() - first.mean()),
              "demeaned_difference_relative": demeaned / float(numpy.linalg.norm(first - first.mean())), "relative_residuals": [r0, r1],
              "recipe_mean": float(recipe.baselines.sum()), "recipe_sum_abs": float(numpy.abs(recipe.baselines).sum())}
    result["passed"] = (abs(result["mean_difference"] - offset) <= 1e-9 and result["demeaned_difference_relative"] <= 1e-8
                        and max(r0, r1) <= stopping and abs(result["recipe_mean"]) <= 1e-13 * result["recipe_sum_abs"])
    return result


def _sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _plugin_version() -> str:
    try:
        return json.loads((PLUGIN / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))["version"]
    except (OSError, ValueError, KeyError):
        return "unknown"


def write_records(artifacts: Path, products, inputs, commands, seeds: dict, tolerances: dict, exit_status: int,
                  run_id: str = "t10-destriper-replay") -> Path:
    """The artifacts_dir: every product's embedded scan product as a sidecar, and one computational-run artifact naming them by path
    (relative to the folder, so no host path is written)."""
    artifacts.mkdir(parents=True, exist_ok=False)
    outputs = {}
    for path in map(Path, products):
        sidecar = artifacts / f"{path.stem}.scan-product.json"
        sidecar.write_text(json.dumps(_load(path)["reconstruction_product"], sort_keys=True) + "\n", encoding="utf-8")
        outputs[path.name] = _sha256(path)
        outputs[sidecar.name] = _sha256(sidecar)
    import numpy
    record = {"contract_version": CONTRACTS_VERSION, "artifact_id": run_id, "artifact_type": "computational-run",
              "objective": "T10 destriping reference replay (reco.scan.destriper/1, a development binding, not native) on the synthetic "
                           "fixture t10-destripe/1; the embedded reconstruction:scan-v1 global products are the sidecars below",
              "bindings": {"experiments": [], "theory": []},
              "versions": {"plugin": _plugin_version(), "contracts": CONTRACTS_VERSION, "profiles": {}},
              "provenance": {"producer_skill": "hep-detector", "created": datetime.date.today().isoformat(), "evidence_ids": []},
              "inputs": [], "outputs": [{"ref": name} for name in outputs if name.endswith(".scan-product.json")],
              "unresolved_inputs": [], "status": ["synthetic"] if exit_status == 0 else ["synthetic", "failed"],
              "extension": {"input_manifest": [{"path": Path(p).name, "sha256": _sha256(p)} for p in inputs],
                            "tools": [{"name": "reco.scan.destriper/1 (adapters/destriper)", "version": "0.1.0"},
                                      {"name": "python", "version": "%d.%d.%d" % sys.version_info[:3]},
                                      {"name": "numpy", "version": numpy.__version__}],
                            "commands": list(commands), "environment": {"interpreter": "env/py313"}, "seeds": dict(seeds),
                            "tolerances": dict(tolerances), "exit_status": exit_status, "output_hashes": outputs}}
    path = artifacts / f"{run_id}.computational-run.json"
    path.write_text(json.dumps(record, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    return path


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="operation", required=True)
    neg = sub.add_parser("negatives")
    neg.add_argument("--product", required=True, type=Path)
    half = sub.add_parser("halved-stopping")
    half.add_argument("--product", required=True, type=Path)
    rec = sub.add_parser("records")
    rec.add_argument("--artifacts", required=True, type=Path)
    rec.add_argument("--product", action="append", required=True, type=Path)
    rec.add_argument("--input", action="append", required=True, type=Path)
    rec.add_argument("--command", action="append", default=[])
    rec.add_argument("--seed", type=int, required=True)
    rec.add_argument("--tolerance-record", type=Path, required=True)
    rec.add_argument("--exit-status", type=int, required=True)
    ret = sub.add_parser("reference-equals-truth")
    ret.add_argument("--reference", required=True, type=Path)
    ret.add_argument("--truth", required=True, type=Path)
    drift = sub.add_parser("null-mode-drift")
    drift.add_argument("--timestream", required=True, type=Path)
    tim = sub.add_parser("timing")
    tim.add_argument("--product", action="append", required=True, type=Path)
    args = ap.parse_args(argv)
    try:
        if args.operation == "negatives":
            ok, rows = negatives(args.product)
            for row in rows:
                print(f"{'PASS' if row['refused'] else 'FAIL'} negative {row['variant']}: codes {row['codes']}")
            print(json.dumps({"operation": "negatives", "status": "ok" if ok else "failed", "rows": rows}, sort_keys=True))
            return 0 if ok else 1
        if args.operation == "halved-stopping":
            print(json.dumps({"operation": "halved-stopping", "status": "ok", "stopping": halved_stopping(args.product)}))
            return 0
        if args.operation == "reference-equals-truth":
            same = reference_equals_truth(_load(args.reference), _load(args.truth))
            print(f"{'PASS' if same else 'FAIL'} the noiseless reference equals the truth exactly")
            print(json.dumps({"operation": "reference-equals-truth", "status": "ok" if same else "failed"}))
            return 0 if same else 1
        if args.operation == "null-mode-drift":
            drift = null_mode_drift(_load(args.timestream))
            print(f"{'PASS' if drift['passed'] else 'FAIL'} null-mode drift without the constraint: start offsets 0 and {drift['offset']} give "
                  f"means {drift['means']}; demeaned difference {drift['demeaned_difference_relative']:.3e}; the recipe's mean {drift['recipe_mean']:.3e}")
            print(json.dumps({"operation": "null-mode-drift", "status": "ok" if drift["passed"] else "failed", **drift}, sort_keys=True))
            return 0 if drift["passed"] else 1
        if args.operation == "records":
            tolerance = _load(args.tolerance_record)
            path = write_records(args.artifacts, args.product, args.input, args.command, {"fixture": args.seed},
                                 {"record": args.tolerance_record.name, "sha256": _sha256(args.tolerance_record), "state": tolerance["state"],
                                  "tau_baselines": tolerance["tau_baselines"], "tau_map": tolerance["tau_map"],
                                  "stopping": tolerance["stopping"]}, args.exit_status)
            print(json.dumps({"operation": "records", "status": "written", "record": path.name}))
            return 0
        rows = []
        for path in args.product:
            started = time.perf_counter()
            result = read_sidecar(_load(path)["reconstruction_product"])
            rows.append({"product": path.name, "seconds": round(time.perf_counter() - started, 3), "ok": result.ok})
            print(f"COST read_sidecar {path.name}: {rows[-1]['seconds']} s, ok {result.ok}")
        print(json.dumps({"operation": "timing", "status": "ok", "rows": rows}, sort_keys=True))
        return 0
    except (OSError, ValueError, KeyError) as exc:
        print(json.dumps({"operation": args.operation, "status": "rejected", "reason": str(exc)}))
        return 2


if __name__ == "__main__":
    sys.exit(main())
