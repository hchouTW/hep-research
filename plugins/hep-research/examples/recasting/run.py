#!/usr/bin/env python3
"""Journey J7 (recasting): SYNTHETIC recast of a published-style single-signal-region search with a parametrized
efficiency, giving an upper limit on the coupling of an ILLUSTRATIVE toy model.

SYNTHETIC and ILLUSTRATIVE. The "published" record (observed count, background and its uncertainty, integrated
luminosity, efficiency map) and the toy model are invented in this file and describe no experiment, search or
physical model. No experiment or theory profile is loaded: a recast needs only the record and its efficiency map.

Chain (hep-theory -> detector-response -> hep-statistics):
1. hep-theory: toy prediction sigma(m_X; g) = g^2 sigma_ref (m_ref / m_X)^4 for the fiducial signal region, at
   particle level, as a prediction artifact in the published observable space.
2. detector-response: the record's efficiency map as a response with form "parametrized",
   eps(m_X) = a + b (m_X - m_ref), valid only for m_X in [200, 800] GeV. Points outside are refused, never extrapolated.
3. Comparison gate: the prediction is multiplied by the integrated luminosity and forward-folded with the parametrized
   response, then compared with the record's detector-level count; a variant that applies the efficiency twice is
   rejected.
4. hep-statistics: one CLs upper limit on the signal count from the record (background nuisance profiled, seeded
   toys, core.stats.likelihood_limits). With one signal region the count limit does not depend on m_X; the coupling
   limit is g^2 < s_up / (L sigma_ref (m_ref/m_X)^4 eps(m_X)).
5. Independent check: with the background uncertainty set to zero the toy CLs limit is compared with the closed
   form CLs = P(N <= n | s + b) / P(N <= n | b) solved by bisection.
6. Contract artifacts (record, prediction, parametrized response, statistical result), report.

Usage (from the plugin root): python3 examples/recasting/run.py [--toys 20000] [--seed 20261006] [--out DIR]
Exit 0 when every pre-declared criterion passes, 1 otherwise. Standard library plus numpy (D5 environment).
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import sys
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PLUGIN))
from contracts import CONTRACTS_VERSION  # noqa: E402
from contracts.identity import plugin_release  # noqa: E402
from contracts.comparison.gate import gate, side_from_artifact  # noqa: E402
from contracts.validate import validate_artifact  # noqa: E402
from core.stats.likelihood_limits import profile_cls  # noqa: E402

PLUGIN_VERSION = json.loads((PLUGIN / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))["version"]
LABEL = "SYNTHETIC and ILLUSTRATIVE: invented search record and toy model; no experiment, search or physical model"
RECORD = {"sqrt_s_gev": 500.0, "integrated_luminosity_pb": 20.0, "sr_edges_gev": [150.0, 1000.0],
          "n_obs": 9, "background": 6.2, "background_unc": 1.4,
          "efficiency_map": {"m_ref_gev": 300.0, "a": 0.35, "b_per_gev": 4.0e-4, "validity_gev": [200.0, 800.0]}}
MODEL = {"sigma_ref_pb": 2.0, "m_ref_gev": 300.0, "power": 4}
MASSES = [200.0, 300.0, 400.0, 500.0, 600.0, 700.0, 800.0]
OUTSIDE = 1000.0
CL = 0.95
CRITERIA = {"toy_vs_closed_form_rel": 0.03}


class ValidityError(ValueError):
    pass


def sigma(m, g=1.0):
    return g * g * MODEL["sigma_ref_pb"] * (MODEL["m_ref_gev"] / m) ** MODEL["power"]


def efficiency(m):
    em = RECORD["efficiency_map"]
    lo, hi = em["validity_gev"]
    if not lo <= m <= hi:
        raise ValidityError(f"m_X = {m} GeV is outside the efficiency map's validity range [{lo}, {hi}] GeV; not extrapolated")
    return em["a"] + em["b_per_gev"] * (m - em["m_ref_gev"])


def poisson_cdf(n, mu):
    term = cum = math.exp(-mu)
    for k in range(1, n + 1):
        term *= mu / k
        cum += term
    return cum


def closed_form_cls(n, b, cl):
    f = lambda s: poisson_cdf(n, s + b) / poisson_cdf(n, b) - (1 - cl)
    lo, hi = 0.0, 100.0
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        lo, hi = (mid, hi) if f(mid) > 0 else (lo, mid)
    return 0.5 * (lo + hi)


def base(created, producer):
    return {"contract_version": CONTRACTS_VERSION, "bindings": {"experiments": [], "theory": []},
            "versions": {"plugin": PLUGIN_VERSION, "contracts": CONTRACTS_VERSION, "plugin_release": plugin_release(), "profiles": {}},
            "provenance": {"producer_skill": producer, "created": created, "evidence_ids": []},
            "inputs": [], "outputs": [], "unresolved_inputs": [], "status": ["synthetic"]}


def observable(level, quantity, unit, fiducial):
    return {"quantity": quantity, "process": "illustrative toy signal (synthetic)",
            "variables": [{"name": "m_ll", "unit": "GeV", "edges": RECORD["sr_edges_gev"]}],
            "phase_space": {"definition": "SYNTHETIC signal region 150 < m_ll < 1000 GeV", "fiducial": fiducial},
            "level": level, "frame": "laboratory",
            "normalization": {"kind": "integrated-luminosity", "value": RECORD["integrated_luminosity_pb"], "unit": "pb^-1"},
            "bin_semantics": "bin-integrated", "unit": unit, "conventions": {"energy_variable": "sqrt_s"}}


def record_doc(created):
    return dict(base(created, "hep-statistics"), artifact_id="synthetic-j7-search-record", artifact_type="dataset-record",
                objective="SYNTHETIC published-style search record: one signal region, observed count and background",
                extension={"dataset_id": "synthetic:j7-search-record", "source_evidence_ids": [],
                           "observable": observable("detector", "event-count", "1", False),
                           "data": {"edges": RECORD["sr_edges_gev"], "values": [RECORD["n_obs"]], "unit": "1",
                                    "uncertainties": [{"name": "background", "kind": "systematic", "correlation": "uncorrelated",
                                                       "values": [RECORD["background_unc"]]}]},
                           "covariance": {"status": "present", "ref": "results.json#record",
                                          "note": "one bin: the background uncertainty is the whole covariance"},
                           "conditions": f"sqrt_s = {RECORD['sqrt_s_gev']}", "period": "not-applicable", "status": "synthetic"})


def prediction_doc(m, created):
    return dict(base(created, "hep-theory"), artifact_id=f"synthetic-j7-prediction-m{int(m)}", artifact_type="prediction",
                objective=f"ILLUSTRATIVE toy-model fiducial cross section in the signal region at m_X = {m} GeV, g = 1",
                extension={"observable": observable("particle-fiducial", "cross-section", "pb", True),
                           "theory_spec_ref": "examples/recasting/run.py#MODEL (illustrative toy, not a physical model)",
                           "parameter_point": {"sqrt_s": RECORD["sqrt_s_gev"]}, "model_point": {"m_X_gev": m, "g": 1.0},
                           "representation": "numerical",
                           "values": {"edges": RECORD["sr_edges_gev"], "values": [sigma(m)], "unit": "pb"},
                           "expression": "sigma = g^2 sigma_ref (m_ref / m_X)^4 (illustrative)",
                           "uncertainties": [{"name": "toy model", "kind": "model-alternative", "correlation": "unknown"}],
                           "allowed_transformations": ["multiply-by-normalization", "forward-fold"]})


def response_doc(created):
    em = RECORD["efficiency_map"]
    return dict(base(created, "detector-response"), artifact_id="synthetic-j7-efficiency-map", artifact_type="response",
                objective="SYNTHETIC published efficiency map as a parametrized response (recasting)",
                extension={"truth_axis": "not-applicable", "reco_axis": "not-applicable", "orientation": "rows_reco_cols_truth",
                           "normalization": "conditional_on_generated", "inefficiency": "inside_matrix", "acceptance": "inside_matrix",
                           "includes": ["efficiency", "acceptance"], "applied_separately": ["luminosity"],
                           "conditions": f"sqrt_s = {RECORD['sqrt_s_gev']} GeV (synthetic)", "provenance": "invented in run.py",
                           "form": "parametrized",
                           "parametrization": {"variables": ["m_X"], "function_ref": "run.py#efficiency",
                                               "function": f"eps = {em['a']} + {em['b_per_gev']} (m_X - {em['m_ref_gev']})",
                                               "validity_range": {"m_X": em["validity_gev"]}}})


def transforms(extra=()):
    e = RECORD["sr_edges_gev"]
    return [*extra,
            {"kind": "multiply-by-normalization", "owner": "hep-statistics", "normalization_kind": "integrated-luminosity",
             "unit_in": "pb", "unit_out": "1"},
            {"kind": "forward-fold", "owner": "detector-response", "truth_level": "particle-fiducial", "truth_edges": e, "reco_edges": e,
             "includes": ["efficiency", "acceptance"],
             "justification": "the record's efficiency map gives the probability that a fiducial signal event is selected in the region"}]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--toys", type=int, default=20000)
    ap.add_argument("--seed", type=int, default=20261006)
    ap.add_argument("--created", default="2026-10-02")
    ap.add_argument("--out", type=Path, default=Path(__file__).resolve().parent / "output")
    a = ap.parse_args(argv)
    out = a.out
    (out / "artifacts").mkdir(parents=True, exist_ok=True)

    rec, resp = record_doc(a.created), response_doc(a.created)
    cond = {"sqrt_s": RECORD["sqrt_s_gev"]}
    gates = {}
    for m in MASSES:
        g = gate(side_from_artifact(prediction_doc(m, a.created)), side_from_artifact(rec), transforms(), [], cond)
        gates[str(m)] = {"comparable": g["comparable"], "mismatches": g["mismatches"], "final": g["final_prediction_state"]}
    variant = prediction_doc(300.0, a.created)  # a producer that allows a separate efficiency correction
    variant["extension"]["allowed_transformations"] = ["apply-correction", "multiply-by-normalization", "forward-fold"]
    double = gate(side_from_artifact(variant), side_from_artifact(rec),
                  transforms([{"kind": "apply-correction", "owner": "detector-response", "effect": "efficiency",
                               "justification": "variant: efficiency applied before folding"}]), [], cond)
    try:
        efficiency(OUTSIDE)
        outside = {"refused": False}
    except ValidityError as exc:
        outside = {"refused": True, "reason": str(exc)}

    lim = profile_cls(RECORD["n_obs"], RECORD["background"], RECORD["background_unc"], CL, a.toys, 0, a.seed)
    check_toy = profile_cls(RECORD["n_obs"], RECORD["background"], 0.0, CL, a.toys, 0, a.seed + 1)["observed_upper_limit"]
    check_exact = closed_form_cls(RECORD["n_obs"], RECORD["background"], CL)
    s_up = lim["observed_upper_limit"]
    L = RECORD["integrated_luminosity_pb"]
    table = []
    for m in MASSES:
        per_g2 = L * sigma(m) * efficiency(m)
        table.append({"m_X_gev": m, "sigma_g1_pb": sigma(m), "efficiency": efficiency(m), "expected_signal_g1": per_g2,
                      "g2_upper": s_up / per_g2, "g_upper": math.sqrt(s_up / per_g2)})

    docs = {"search_record": rec, "prediction_m300": prediction_doc(300.0, a.created), "efficiency_map": resp}
    docs["result"] = dict(base(a.created, "hep-statistics"), artifact_id="synthetic-j7-coupling-limit", artifact_type="statistical-result",
                          objective="SYNTHETIC 95% CLs upper limit on the toy-model coupling versus m_X (illustrative recast)",
                          inputs=[{"ref": "artifacts/search_record.json", "artifact_type": "dataset-record", "status": ["synthetic"]},
                                  {"ref": "artifacts/efficiency_map.json", "artifact_type": "response", "status": ["synthetic"]}],
                          extension={"paradigm": "frequentist",
                                     "likelihood": {"form": "Poisson count with a Gaussian-constrained background (one signal region)"},
                                     "parameters_of_interest": ["signal count s", "toy coupling g^2 via s = g^2 L sigma_ref (m_ref/m_X)^4 eps(m_X)"],
                                     "nuisances": ["background"], "test_statistic": "one-sided profile likelihood ratio (q-tilde)",
                                     "construction": "cls", "coverage": {"method": "CLs over-covers by design; not studied further here"},
                                     "fit_status": "converged", "results": {"ref": "results.json#limits"}})
    contract = {k: {"ok": (r := validate_artifact(v)).ok, "errors": [f.message for f in r.errors]} for k, v in docs.items()}
    for k, v in docs.items():
        (out / "artifacts" / f"{k}.json").write_text(json.dumps(v, indent=1) + "\n")

    passes = {"gate_comparable_all_masses": all(g["comparable"] for g in gates.values()),
              "gate_rejects_double_efficiency": not double["comparable"]
                                                and any("already applied before folding" in x["reason"] for x in double["mismatches"]),
              "outside_validity_refused": outside["refused"],
              "toy_vs_closed_form": abs(check_toy / check_exact - 1) < CRITERIA["toy_vs_closed_form_rel"],
              "coupling_limit_weakens_with_mass": all(x["g2_upper"] < y["g2_upper"] for x, y in zip(table, table[1:])),
              "contracts": all(c["ok"] for c in contract.values())}
    results = {"label": LABEL, "profiles_loaded": [], "seed": a.seed, "toys": a.toys, "criteria": CRITERIA, "pass": passes,
               "record": RECORD, "model": MODEL, "cl": CL, "gates": gates,
               "double_efficiency_variant": {"comparable": double["comparable"], "mismatches": double["mismatches"]},
               "outside_validity": {"m_X_gev": OUTSIDE, **outside},
               "signal_count_limit": {k: lim[k] for k in ("method", "observed_upper_limit", "toys", "seed")},
               "closed_form_check": {"sigma_b": 0.0, "toy_limit": check_toy, "closed_form_limit": check_exact,
                                     "rel_diff": check_toy / check_exact - 1},
               "limits": table, "contract_validation": contract}
    (out / "results.json").write_text(json.dumps(results, indent=1) + "\n")
    write_report(out, results)
    print(json.dumps({"pass": passes, "results_sha256": hashlib.sha256((out / "results.json").read_bytes()).hexdigest()}, indent=1))
    return 0 if all(passes.values()) else 1


def write_report(out: Path, r: dict) -> None:
    c = r["closed_form_check"]
    lines = ["# J7 recast (SYNTHETIC, illustrative)", "",
             f"{r['label']}. No profile loaded. Seed {r['seed']}, {r['toys']} toys, CL {r['cl']}.", "",
             f"Signal-count limit (CLs, background profiled): s < {r['signal_count_limit']['observed_upper_limit']:.3f} "
             f"for n = {r['record']['n_obs']}, b = {r['record']['background']} ± {r['record']['background_unc']}.",
             f"Check with sigma_b = 0: toys {c['toy_limit']:.3f}, closed form {c['closed_form_limit']:.3f} (difference {100 * c['rel_diff']:.2f}%).", "",
             "| m_X (GeV) | sigma (g = 1, pb) | efficiency | expected signal (g = 1) | g^2 upper limit |", "|---|---|---|---|---|"]
    lines += [f"| {x['m_X_gev']:.0f} | {x['sigma_g1_pb']:.4f} | {x['efficiency']:.3f} | {x['expected_signal_g1']:.3f} | {x['g2_upper']:.3f} |"
              for x in r["limits"]]
    lines += ["", f"Outside the map's validity (m_X = {r['outside_validity']['m_X_gev']:.0f} GeV): "
                  f"{'refused' if r['outside_validity']['refused'] else 'NOT refused'}.",
              f"Gate: comparable at every mass after multiply-by-normalization and forward-fold; the variant that applies the "
              f"efficiency before folding is {'rejected' if not r['double_efficiency_variant']['comparable'] else 'NOT rejected'}.", "",
              "Criteria: " + ", ".join(f"{k} {'pass' if v else 'FAIL'}" for k, v in r["pass"].items()) + ".", "",
              "Limits: one signal region, so shapes and correlations between regions are not exercised; the efficiency map "
              "has no uncertainty of its own; the toy model is not physics. This shows the J7 chain and its contracts.", "",
              f"Reproduce: `python3 examples/recasting/run.py --toys {r['toys']} --seed {r['seed']}`"]
    (out / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    sys.exit(main())
