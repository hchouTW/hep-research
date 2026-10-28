#!/usr/bin/env python3
"""BIG and SLIM fitted with the USINE provider to SYNTHETIC Asimov B/C and 10Be/9Be data (cr-propagation C2UF).

The study behind acceptance entry C2UF-1 (C2U-3 moved by decision A1.12): the C2U study (usine_family_study.py) with
a second dataset. B/C alone constrains thin-disc reacceleration weakly (sigma(V_A) about 28 km/s), so C2U's response
box spanned the whole V_A domain and its polynomial response model was refused. Here a SYNTHETIC Asimov 10Be/9Be set
(down to 0.05 GeV/n, with 10Be beta decay switched on in the shared transport block, r3 P6) is generated from the same
USINE run at the same BIG truth; it fixes D0 for the fixed L, so B/C then constrains V_A. propagation_fit.py fits the
families BIG (D0, delta, V_A, V_c free) and SLIM (D0, delta free, V_A = V_c = 0) with the provider (one request and one
USINE run per point for both datasets, provider_requests "per-point"), and calibrates the delta chi2 of both families
with toys on polynomial response models, one per family's best fit (layout "per-center"), each validated against the
provider, their error added to the toy covariance (P10). Both families share one transport block: the provider's
harmonized-v1 default with decay on and the ILLUSTRATIVE low-rigidity break of C2U, held fixed. Every input is
ILLUSTRATIVE; nothing is fitted to real data.

The live run needs USINE (HEP_USINE_BIN, HEP_USINE_DATA) and keeps every run's computational-run artifact under
HEP_USINE_RUN_DIR; it writes the recorded study (datasets, configuration, fit result with the per-evaluation records,
the USINE predictions at the truth) to --record, from which test_propagation_fit.py checks the criterion offline.

Usage:
  python3 usine_two_dataset_family_study.py --registry REGISTRY.json --cache-dir DIR --out DIR [--record FILE]
      [--max-evaluations 540] [--family-toys 200] [--degree 3] [--design-points 80]
Exit codes: 0 written; 1 the fit failed; 2 bad input or USINE not configured.
"""
from __future__ import annotations

import argparse
import copy
import json
import os
import sys
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.dont_write_bytecode = True
for entry in (str(PLUGIN), str(PLUGIN / "skills" / "hep-statistics" / "scripts"), str(HERE)):
    if entry not in sys.path:
        sys.path.insert(0, entry)

import usine_family_study as c2u  # noqa: E402

RECORD = PLUGIN / "tests" / "adapters" / "fixtures" / "cr_propagation" / "c2uf" / "usine-two-dataset-family-study.json"
DECAY = {"enabled": True, "lorentz_dilation": True, "ec_treatment": "fully-stripped"}
# (dataset name, observable id, edges, uncorrelated fraction, fully correlated fraction)
DATASETS = [("bc-asimov", "B/C", None, 0.04, 0.02),
            ("be-asimov", "10Be/9Be", "be", 0.06, 0.03)]
SEED = 20261028


def be_edges() -> list[float]:
    """12 bins equal in ln(E_k/n) from 0.05 to 10 GeV/n."""
    return [float(f"{0.05 * 200.0 ** (k / 12):.6g}") for k in range(13)]


def edges_of(kind) -> list[float]:
    return be_edges() if kind == "be" else c2u.edges()


def transport() -> dict:
    """C2U's transport (harmonized-v1 default, ILLUSTRATIVE low break, family BIG) with 10Be beta decay on."""
    doc = c2u.transport()
    doc["decay"] = dict(DECAY)
    return doc


def observables() -> list[dict]:
    return [{"id": obs, "axis": "ekn", "unit": "GeV/n",
             "bins": [[a, b] for a, b in zip(edges_of(kind), edges_of(kind)[1:])]} for _, obs, kind, _, _ in DATASETS]


def asimov_record(name, prediction: dict, labels, unc: float, cor: float) -> dict:
    rec = c2u.asimov_record(prediction, labels)
    y = prediction["values"]["values"]
    rec["artifact_id"] = f"c2uf-usine-{name}"
    rec["objective"] = (f"SYNTHETIC Asimov {prediction['observable'].get('process', '').split(' from ')[0]} points "
                        "from the USINE provider at an ILLUSTRATIVE BIG point (C2UF)")
    rec["extension"]["dataset_id"] = f"synthetic:c2uf-usine-{name}"
    rec["extension"]["data"]["uncertainties"][0]["values"] = [unc * v for v in y]
    rec["extension"]["data"]["uncertainties"][1]["values"] = [cor * v for v in y]
    return rec


def config(records: dict, family_toys: int, degree: int, design_points: int, runs_ref=None) -> dict:
    """The fit configuration (C2U's, with the second dataset, per-point requests and per-center response models)."""
    cfg = c2u.config(records["bc-asimov"], family_toys, runs_ref)
    cfg["transport"] = transport()
    cfg["datasets"] = [{"name": name, "measurement": records[name], "observable": obs}
                       for name, obs, _, _, _ in DATASETS]
    cfg["provider_requests"] = "per-point"
    cfg.pop("intervals", None)
    cfg["response_model"] = {"kind": "polynomial", "degree": degree, "design_points": design_points,
                             "validation_points": 20, "tolerance_sigma": 0.05, "half_width_sigma": 5.0,
                             "layout": "per-center"}
    cfg["family_toys"] = {"n": family_toys, "seed": SEED, "alpha": 0.05}
    return cfg


def generate(registry: str, cache_dir: str) -> tuple[dict, dict]:
    """Both datasets' predictions at the truth from one USINE run; (result, {'points_sent'})."""
    from core.provider.runner import ProviderRunner
    req = {"protocol": "cr-provider/1", "provider": c2u.PROVIDER, "provider_version": c2u.VERSION,
           "transport": transport(), "points": [dict(c2u.TRUTH, **c2u.FIXED)], "observables": observables(),
           "want": ["lis"], "seed": None}
    with ProviderRunner(registry, cache_dir=cache_dir) as runner:
        res = runner.evaluate(req)["results"][0]
        sent = runner.stats["points_sent"]
    if res.get("status") != "ok":
        raise SystemExit(f"the truth point failed: {res.get('reason')} {res.get('detail')}")
    return res, {"points_sent": sent}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--registry", required=True, help="provider registry (tools/provider_registry.py --write)")
    ap.add_argument("--cache-dir", required=True, help="provider cache folder (outside the repository)")
    ap.add_argument("--out", required=True, type=Path, help="folder for the fit outputs (outside the repository)")
    ap.add_argument("--record", type=Path, default=RECORD, help="recorded study to write (default: the test fixture)")
    ap.add_argument("--max-evaluations", type=int, default=540, help="cap on USINE evaluations of the fit")
    ap.add_argument("--family-toys", type=int, default=200, help="toys per family for the delta chi2 calibration")
    ap.add_argument("--degree", type=int, default=3, help="total degree of each polynomial response model")
    ap.add_argument("--design-points", type=int, default=80, help="Sobol design points of each response model")
    args = ap.parse_args(argv)
    runs = os.environ.get("HEP_USINE_RUN_DIR")
    if not (os.environ.get("HEP_USINE_BIN") and os.environ.get("HEP_USINE_DATA") and runs):
        print(json.dumps({"status": "rejected", "error": "set HEP_USINE_BIN, HEP_USINE_DATA and HEP_USINE_RUN_DIR"}))
        return 2
    import propagation_fit as pf
    truth_res, gen = generate(args.registry, args.cache_dir)
    labels = truth_res.get("labels") or []
    records = {name: asimov_record(name, pred, labels, unc, cor)
               for (name, _, _, unc, cor), pred in zip(DATASETS, truth_res["predictions"])}
    cfg = config(records, args.family_toys, args.degree, args.design_points, runs)
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "config.json").write_text(json.dumps(cfg, indent=1) + "\n", encoding="utf-8")
    try:
        result = pf.run(cfg, args.out, args.registry, cache_dir=args.cache_dir, max_evaluations=args.max_evaluations,
                        out_dir=args.out, cfg_ref="config.json")
    except (pf.FitRefused, pf.FitInputError, pf.FitIncomplete) as exc:
        print(json.dumps({"status": "failed", "error": str(exc), "reason": getattr(exc, "reason", None)}))
        return 1
    cfg.pop("computational_runs", None)   # a local folder: not recorded
    doc = {"study": "C2UF BIG and SLIM with the USINE provider, B/C and 10Be/9Be (SYNTHETIC Asimov, ILLUSTRATIVE "
                    "inputs)",
           "truth": dict(c2u.TRUTH, **c2u.FIXED), "generating_family": "BIG",
           "truth_evaluation": truth_res["evaluation"],
           "truth_predictions": {name: pred for (name, *_), pred in zip(DATASETS, truth_res["predictions"])},
           "config": cfg,
           "usine_evaluations": {"truth": gen["points_sent"], "fit": result["provider_evaluations"]["points_sent"]},
           "result": pf._jsonable(copy.deepcopy(result))}
    args.record.parent.mkdir(parents=True, exist_ok=True)
    args.record.write_text(json.dumps(doc, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "record": str(args.record),
                      "usine_points_sent": doc["usine_evaluations"]}))
    return 0 if result["status"] == "ok" else 1


if __name__ == "__main__":
    sys.exit(main())
