#!/usr/bin/env python3
"""BIG vs SLIM toy calibration through a Gaussian-process emulator of USINE (cr-propagation C2UF, decision A1.14).

The two-dataset study of usine_two_dataset_family_study.py (SYNTHETIC Asimov B/C and 10Be/9Be from USINE at the BIG
truth, decay on) with the toys run on an emulator instead of a global polynomial: USINE runs on a box that holds both
families' fits and BIG's fits to SLIM's toys are fed to hep-ml's train_emulator.py (a subprocess, R1), the model is
wrapped as an ml-artifact by write_ml_artifact.py and served by the cr-propagation emulator provider with a per-model
declaration (HEP_EMULATOR_ML_ARTIFACT); the emulator is validated against held-out USINE runs at 0.05 of the data
sigma, its largest held-out error per bin is added to each dataset's covariance (P10), and propagation_fit.py fits
BIG and SLIM with the emulator provider and calibrates their delta chi2 with toys on the emulator itself (response
model kind "provider"). Every input is ILLUSTRATIVE.

Steps (each writes into --work; USINE runs go through the provider cache, so a rerun costs no USINE run):
  usine     the training design and the held-out validation runs (--round 0 or 1)
  train     training set from every cached run inside the box, minus the validation points; model and ml-artifact
  validate  the emulator against the held-out runs; the regression_validation block; the emulator error component
  fit       propagation_fit with the emulator provider; the recorded study to --record
Usage:
  python3 usine_emulator_family_study.py STEP --registry REGISTRY.json --cache-dir DIR --work DIR [--round 0]
      [--record FILE] [--family-toys 200]
Exit codes: 0 done (validate: the emulator passed); 1 failed; 2 bad input or USINE not configured.
"""
from __future__ import annotations

import argparse
import copy
import glob
import hashlib
import json
import math
import os
import shutil
import subprocess
import sys
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.dont_write_bytecode = True
for entry in (str(PLUGIN), str(PLUGIN / "skills" / "hep-statistics" / "scripts"), str(HERE)):
    if entry not in sys.path:
        sys.path.insert(0, entry)

import usine_family_study as c2u  # noqa: E402
import usine_two_dataset_family_study as st  # noqa: E402

FIXTURE = PLUGIN / "tests" / "adapters" / "fixtures" / "cr_propagation" / "c2uf"
TWO_DATASET_RECORD = FIXTURE / "usine-two-dataset-family-study.json"
RECORD = FIXTURE / "usine-emulator-family-study.json"
TRAINER = PLUGIN / "skills" / "hep-ml" / "scripts" / "train_emulator.py"
WRITER = PLUGIN / "skills" / "hep-ml" / "scripts" / "write_ml_artifact.py"
PROVIDER_SCRIPT = PLUGIN / "adapters" / "cr-propagation" / "assets" / "emulator_provider.py"
ARTIFACT_ENV = "HEP_EMULATOR_ML_ARTIFACT"
ARTIFACT_ID = "ml-emulator-usine-c2uf"
NAMES = ["D0_cm2_s", "delta", "V_A_kms", "V_c_kms"]
BOX = {"D0_cm2_s": (1.9e28, 4.0e28, "log"), "delta": (0.40, 0.535, "linear"), "V_A_kms": (0.0, 105.0, "linear"),
       "V_c_kms": (0.0, 9.5, "linear")}
TOY_BOX = {"D0_cm2_s": (math.exp(65.191), math.exp(65.772)), "delta": (0.4133, 0.5206), "V_A_kms": (0.0, 94.56),
           "V_c_kms": (0.0, 7.108)}
DESIGN = {0: {"box": 200, "vc0": 40, "va0": 30, "slice": 30}, 1: {"box": 60}}
VALIDATION_SEED = {0: 20261029, 1: 20261030}
SIGMA_REL = {"bc-asimov": math.hypot(0.04, 0.02), "be-asimov": math.hypot(0.06, 0.03)}
TOLERANCE = 0.05
TRAIN_SEED = 20261028


# ---------------------------------------------------------------------------------------------- points
def _from_unit(u, names, box) -> dict:
    out = {}
    for x, n in zip(u, names):
        lo, hi = box[n][0], box[n][1]
        out[n] = math.exp(math.log(lo) + x * (math.log(hi) - math.log(lo))) if n == "D0_cm2_s" else lo + x * (hi - lo)
    return out


def design(rnd: int) -> list[dict]:
    """Training points of a round: scrambled Sobol sets in the box and on its faces (V_c = 0, V_A = 0, both)."""
    import warnings

    from scipy.stats import qmc
    sets = {"box": NAMES, "vc0": NAMES[:3], "va0": ["D0_cm2_s", "delta", "V_c_kms"], "slice": NAMES[:2]}
    pts = []
    for k, (kind, n) in enumerate(DESIGN[rnd].items()):
        names = sets[kind]
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            u = qmc.Sobol(len(names), scramble=True, seed=TRAIN_SEED + 100 * rnd + k).random(n)
        for row in u:
            p = {"V_A_kms": 0.0, "V_c_kms": 0.0}
            p.update(_from_unit(row, names, BOX))
            pts.append({n: float(p[n]) for n in NAMES})
    return pts


def validation_points(rnd: int) -> list[dict]:
    """30 uniform in the toy box and 10 uniform on the SLIM slice (V_A = V_c = 0)."""
    import numpy as np
    rng = np.random.default_rng(VALIDATION_SEED[rnd])
    pts = [{n: float(v) for n, v in _from_unit(rng.uniform(0, 1, 4), NAMES, TOY_BOX).items()} for _ in range(30)]
    for _ in range(10):
        p = _from_unit(rng.uniform(0, 1, 2), NAMES[:2], TOY_BOX)
        pts.append({**{n: float(v) for n, v in p.items()}, "V_A_kms": 0.0, "V_c_kms": 0.0})
    return pts


def _unit(p: dict, n: str) -> float:
    lo, hi = BOX[n][0], BOX[n][1]
    return (math.log(p[n] / lo) / math.log(hi / lo)) if n == "D0_cm2_s" else (p[n] - lo) / (hi - lo)


def _key(p: dict) -> tuple:
    return tuple(round(math.log(p[n]) if n == "D0_cm2_s" else p[n], 12) for n in NAMES)


# ---------------------------------------------------------------------------------------------- USINE
def usine_values(registry: str, cache_dir: str, points: list[dict]) -> tuple[list[list[float]], int]:
    """USINE's 27 values (B/C then 10Be/9Be) per point, one per-point request per chunk; (values, runs sent)."""
    from core.provider.runner import ProviderRunner
    out, sent = [], 0
    with ProviderRunner(registry, cache_dir=cache_dir) as runner:
        for start in range(0, len(points), 20):
            chunk = [dict(p, **c2u.FIXED) for p in points[start:start + 20]]
            req = {"protocol": "cr-provider/1", "provider": c2u.PROVIDER, "provider_version": c2u.VERSION,
                   "transport": st.transport(), "points": chunk, "observables": st.observables(), "want": ["lis"],
                   "seed": None}
            resp = runner.evaluate(req)
            for res in resp["results"]:
                if res.get("status") != "ok":
                    raise SystemExit(f"USINE failed at {res.get('point')}: {res.get('reason')} {res.get('detail')}")
                out.append([v for pred in res["predictions"] for v in pred["values"]["values"]])
        sent = runner.stats["points_sent"]
    return out, sent


def cached_runs(cache_dir: str) -> list[tuple[dict, list[float]]]:
    """Every cached USINE run of the study's request (transport and observables) inside the box."""
    want = {"bc": len(c2u.edges()) - 1, "be": len(st.be_edges()) - 1}
    tsha = None
    from core.provider.hashing import canonical_sha256
    tsha = canonical_sha256(st.transport())
    out = []
    for f in sorted(glob.glob(str(Path(cache_dir) / "*" / "*.json"))):
        res = json.loads(Path(f).read_text(encoding="utf-8"))["result"]
        preds = res.get("predictions") or []
        if len(preds) != 2 or [len(p["values"]["values"]) for p in preds] != [want["bc"], want["be"]]:
            continue
        if any(p["values"]["edges"] != e for p, e in zip(preds, (c2u.edges(), st.be_edges()))):
            continue
        p = res["point"]
        if p.get("L_kpc") != 4.0 or p.get("eta") != 1.0:
            continue
        pp = (preds[0].get("parameter_point") or {})
        if pp.get("transport_sha256") not in (None, tsha):
            continue
        pt = {n: float(p[n]) for n in NAMES}
        if all(BOX[n][0] <= pt[n] <= BOX[n][1] for n in NAMES):
            out.append((pt, [v for pred in preds for v in pred["values"]["values"]]))
    return out


# ---------------------------------------------------------------------------------------------- emulator
def _truth_blocks() -> dict:
    doc = json.loads(TWO_DATASET_RECORD.read_text(encoding="utf-8"))
    return {name: doc["truth_predictions"][name]["observable"] for name in ("bc-asimov", "be-asimov")}


def training_doc(runs) -> dict:
    blocks = _truth_blocks()
    bc, be = c2u.edges(), st.be_edges()
    return {"features": [{"name": n, "min": BOX[n][0], "max": BOX[n][1], "scale": BOX[n][2]} for n in NAMES],
            "outputs": {"name": "B/C and 10Be/9Be", "count": len(bc) + len(be) - 2, "transform": "log", "unit": "1",
                        "observables": [
                            {"id": "B/C", "axis": "ekn", "unit": "GeV/n", "edges": bc, "start": 0,
                             "observable": blocks["bc-asimov"]},
                            {"id": "10Be/9Be", "axis": "ekn", "unit": "GeV/n", "edges": be, "start": len(bc) - 1,
                             "observable": blocks["be-asimov"]}],
                        "labels": [f"B/C bin {i}" for i in range(len(bc) - 1)]
                        + [f"10Be/9Be bin {i}" for i in range(len(be) - 1)]},
            "points": [p for p, _ in runs], "values": [v for _, v in runs], "status": ["synthetic", "unvalidated"],
            "context": {"simulator": "USINE V3.5 through the cr-provider/1 provider usine", "provider": c2u.PROVIDER,
                        "provider_version": c2u.VERSION, "transport": st.transport(),
                        "fixed": dict(c2u.FIXED), "study": "cr-propagation C2UF (A1.14)"}}


def run_json(argv, cwd) -> dict:
    proc = subprocess.run([sys.executable, *map(str, argv)], capture_output=True, text=True, cwd=cwd,
                          env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"), timeout=7200)
    if proc.returncode != 0:
        raise SystemExit(f"{Path(str(argv[0])).name} exit {proc.returncode}: {proc.stdout[-3000:]}{proc.stderr[-2000:]}")
    return json.loads(proc.stdout)


def write_artifact(folder: Path, regression=None) -> dict:
    summary = json.loads((folder / "run_summary.json").read_text(encoding="utf-8"))
    summary.pop("training_set", None)
    summary["checkpoint"] = "emulator-model.json"
    summary["extrapolation_policy"] = {
        "action": "reject",
        "consumer": "adapters/cr-propagation/assets/emulator_provider.py (per-model declaration): a point the stored "
                    "DomainModel calls sparse or outside fails with out-of-domain",
        "method": "DomainModel of skills/hep-ml/scripts/check_surrogate_domain.py on the unit-cube training points"}
    if regression is not None:
        summary["regression_validation"] = regression
    (folder / "run_summary.json").write_text(json.dumps(summary, indent=1) + "\n", encoding="utf-8")
    return run_json([WRITER, "--run-summary", "run_summary.json", "--status", "synthetic", "--status", "unvalidated",
                     "--output-semantics", "regression-value", "--artifact-id", ARTIFACT_ID,
                     "--objective", "Gaussian-process emulator of USINE B/C and 10Be/9Be (ekn, decay on) on the "
                                    "C2UF toy box, served by the cr-propagation emulator provider (per-model "
                                    "declaration)",
                     "--out", "emulator.ml-artifact.json"], cwd=folder)


def emulator_registry(base_registry: str, artifact: Path, out: Path) -> Path:
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", **{ARTIFACT_ENV: str(artifact)})
    proc = subprocess.run([sys.executable, str(PROVIDER_SCRIPT), "--declaration"], capture_output=True, text=True,
                          env=env, timeout=300)
    doc = json.loads(proc.stdout)
    if doc.get("status") != "ok":
        raise SystemExit(f"emulator declaration failed: {doc}")
    reg = json.loads(Path(base_registry).read_text(encoding="utf-8"))
    for item in reg["providers"]:
        if item["declaration"]["id"] == "emulator":
            item["declaration"] = doc["declaration"]
            item["version"] = doc["declaration"]["version"]
    out.write_text(json.dumps(reg, indent=1) + "\n", encoding="utf-8")
    return out


def emulator_values(registry: Path, artifact: Path, points: list[dict]) -> list[dict]:
    from core.provider.registry import load_registry
    from core.provider.runner import ProviderRunner
    os.environ[ARTIFACT_ENV] = str(artifact)
    version = load_registry(str(registry))["emulator"].version
    out = []
    with ProviderRunner(str(registry), session="serve") as runner:
        req = {"protocol": "cr-provider/1", "provider": "emulator", "provider_version": version, "points": points,
               "observables": st.observables(), "want": ["lis"], "seed": None, "transport": st.transport()}
        for res in runner.evaluate(req)["results"]:
            if res.get("status") != "ok":
                out.append({"status": res.get("status"), "reason": res.get("reason"), "detail": res.get("detail")})
            else:
                out.append({"status": "ok", "values": [v for pred in res["predictions"]
                                                      for v in pred["values"]["values"]]})
    return out


# ---------------------------------------------------------------------------------------------- steps
def step_usine(args) -> int:
    pts = design(args.round) + validation_points(args.round)
    _, sent = usine_values(args.registry, args.cache_dir, pts)
    print(json.dumps({"status": "ok", "round": args.round, "points": len(pts), "usine_runs": sent}))
    return 0


def step_train(args) -> int:
    held = {_key(p) for p in validation_points(args.round)}
    runs, seen = [], set()
    for r in cached_runs(args.cache_dir):    # held-out points never; points equal to 1e-9 in the unit cube once
        unit = tuple(round(_unit(r[0], n), 9) for n in NAMES)
        if _key(r[0]) not in held and unit not in seen:
            seen.add(unit)
            runs.append(r)
    folder = args.work / f"model-{args.round}"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "training-set.json").write_text(json.dumps(training_doc(runs)), encoding="utf-8")
    trained = run_json([TRAINER, "train", "--training-set", "training-set.json", "--out-dir", ".", "--seed",
                        str(TRAIN_SEED), "--pca-tolerance", "1e-4", "--restarts", "4", "--status", "synthetic"],
                       cwd=folder)
    art = write_artifact(folder)
    print(json.dumps({"status": "ok", "training_points": len(runs), "trained": {k: trained.get(k) for k in
                      ("components", "n_training", "loo", "domain") if k in trained}, "artifact": art.get("status")}))
    return 0


def step_validate(args) -> int:
    folder = args.work / f"model-{args.round}"
    artifact = folder / "emulator.ml-artifact.json"
    pts = validation_points(args.round)
    usine, _ = usine_values(args.registry, args.cache_dir, pts)   # cached by the usine step
    registry = emulator_registry(args.registry, artifact, folder / "registry.json")
    emu = emulator_values(registry, artifact, pts)
    nbc = len(c2u.edges()) - 1
    rows, worst, err = [], 0.0, [0.0] * len(usine[0])
    for p, u, e in zip(pts, usine, emu):
        if e["status"] != "ok":
            rows.append({"point": p, "status": e["status"], "reason": e["reason"], "detail": e["detail"]})
            worst = math.inf
            continue
        pulls = []
        for i, (a, b) in enumerate(zip(e["values"], u)):
            s = SIGMA_REL["bc-asimov" if i < nbc else "be-asimov"] * b
            pulls.append(abs(a - b) / s)
            err[i] = max(err[i], abs(a - b))
        worst = max(worst, max(pulls))
        rows.append({"point": p, "status": "ok", "max_error_over_sigma": max(pulls),
                     "max_relative_error": max(abs(a / b - 1) for a, b in zip(e["values"], u))})
    passed = worst <= TOLERANCE
    ok_rows = [r for r in rows if r["status"] == "ok"]
    regression = {"holdout": {"points": len(pts), "round": args.round, "seed": VALIDATION_SEED[args.round],
                              "drawn_from": "30 uniform in the toy box, 10 uniform on the SLIM slice V_A = V_c = 0",
                              "max_error_over_data_sigma": worst if math.isfinite(worst) else None,
                              "tolerance_over_data_sigma": TOLERANCE, "passed": passed,
                              "refused_by_domain_model": len(rows) - len(ok_rows)},
                  "max_relative_error": max((r["max_relative_error"] for r in ok_rows), default=None)}
    write_artifact(folder, regression)
    doc = {"round": args.round, "passed": passed, "max_error_over_sigma": worst if math.isfinite(worst) else None,
           "tolerance": TOLERANCE, "rows": rows,
           "error_component": {"bc-asimov": err[:nbc], "be-asimov": err[nbc:]},
           "model_sha256": hashlib.sha256((folder / "emulator-model.json").read_bytes()).hexdigest()}
    (folder / "validation.json").write_text(json.dumps(doc, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({k: doc[k] for k in ("round", "passed", "max_error_over_sigma")}))
    return 0 if passed else 1


def step_fit(args) -> int:
    import propagation_fit as pf
    folder = args.work / f"model-{args.round}"
    val = json.loads((folder / "validation.json").read_text(encoding="utf-8"))
    if not val["passed"]:
        print(json.dumps({"status": "failed", "error": "the emulator did not pass its validation"}))
        return 1
    artifact = folder / "emulator.ml-artifact.json"
    registry = emulator_registry(args.registry, artifact, folder / "registry.json")
    os.environ[ARTIFACT_ENV] = str(artifact)
    from core.provider.registry import load_registry
    version = load_registry(str(registry))["emulator"].version
    two = json.loads(TWO_DATASET_RECORD.read_text(encoding="utf-8"))
    cfg = copy.deepcopy(two["config"])
    for ds in cfg["datasets"]:      # P10: the emulator's largest held-out error per bin, uncorrelated
        ds["measurement"]["extension"]["data"]["uncertainties"].append(
            {"name": "emulator", "kind": "systematic", "correlation": "uncorrelated",
             "values": [float(v) for v in val["error_component"][ds["name"]]]})
    cfg["provider"] = {"id": "emulator", "version": version}
    cfg["fixed"] = {}
    cfg.pop("provider_requests", None)
    cfg["provider_requests"] = "per-point"
    cfg["response_model"] = {"kind": "provider", "layout": "joint", "half_width_sigma": 3.0,
                             "tolerance_sigma": TOLERANCE}
    cfg["family_toys"] = {"n": args.family_toys, "seed": st.SEED, "alpha": 0.05}
    cfg["run_record_keys"] = ["emulator_model", "ml_artifact", "domain_status", "training_provider"]
    cfg.pop("computational_runs", None)
    out = args.work / "fit"
    out.mkdir(parents=True, exist_ok=True)
    (out / "config.json").write_text(json.dumps(cfg, indent=1) + "\n", encoding="utf-8")
    try:
        result = pf.run(cfg, out, str(registry), cache_dir=None, max_evaluations=2_000_000, out_dir=out,
                        cfg_ref="config.json")
    except (pf.FitRefused, pf.FitInputError, pf.FitIncomplete) as exc:
        print(json.dumps({"status": "failed", "error": str(exc), "reason": getattr(exc, "reason", None)}))
        return 1
    res = pf._jsonable(copy.deepcopy(result))
    res["provider_evaluations"].pop("records", None)    # one per emulator evaluation (tens of thousands)
    doc = {"study": "C2UF BIG and SLIM, toys on a Gaussian-process emulator of USINE (B/C and 10Be/9Be, SYNTHETIC "
                    "Asimov, ILLUSTRATIVE inputs; decision A1.14)",
           "truth": two["truth"], "generating_family": "BIG", "config": cfg, "emulator": {
               "ml_artifact": "emulator.ml-artifact.json", "model": "emulator-model.json",
               "model_sha256": val["model_sha256"], "round": args.round,
               "validation": {k: val[k] for k in ("passed", "max_error_over_sigma", "tolerance", "rows",
                                                  "error_component")}},
           "usine_fits": {f["family"]: {"chi2": f["chi2"], "best_fit": {p["name"]: p["best_fit"]
                                                                        for p in f["parameters"]}}
                          for f in two["result"]["fits"]},
           "result": res}
    args.record.parent.mkdir(parents=True, exist_ok=True)
    args.record.write_text(json.dumps(doc, indent=1) + "\n", encoding="utf-8")
    for name in ("emulator-model.json", "emulator.ml-artifact.json"):
        shutil.copy(folder / name, args.record.parent / name)
    print(json.dumps({"status": result["status"], "record": str(args.record),
                      "surviving": result["families"]["surviving"]}))
    return 0 if result["status"] == "ok" else 1


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("step", choices=["usine", "train", "validate", "fit"])
    ap.add_argument("--registry", required=True, help="provider registry (tools/provider_registry.py --write)")
    ap.add_argument("--cache-dir", required=True, help="USINE provider cache (outside the repository)")
    ap.add_argument("--work", required=True, type=Path, help="work folder (outside the repository)")
    ap.add_argument("--round", type=int, default=0, choices=[0, 1], help="design and validation round")
    ap.add_argument("--record", type=Path, default=RECORD, help="recorded study (fit step)")
    ap.add_argument("--family-toys", type=int, default=200, help="toys per family")
    args = ap.parse_args(argv)
    if args.step in ("usine", "validate") and not (os.environ.get("HEP_USINE_BIN") and os.environ.get("HEP_USINE_DATA")
                                                   and os.environ.get("HEP_USINE_RUN_DIR")):
        print(json.dumps({"status": "rejected", "error": "set HEP_USINE_BIN, HEP_USINE_DATA and HEP_USINE_RUN_DIR"}))
        return 2
    args.work = args.work.resolve()
    args.work.mkdir(parents=True, exist_ok=True)
    return {"usine": step_usine, "train": step_train, "validate": step_validate, "fit": step_fit}[args.step](args)


if __name__ == "__main__":
    sys.exit(main())
