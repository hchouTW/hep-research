#!/usr/bin/env python3
"""Write the SYNTHETIC dataset record used by the T24 example, shaped like a published (HEPData-style) table.

Values and covariance are copied from the Path B synthetic output (examples/collider-angular/output/results.json):
corrected d sigma / d cos theta in the fiducial region with its full covariance. They are synthetic, not published.
The record stands alone: it names its experiment profile by id but carries no detector information.

Usage (from the plugin root): python3 examples/published-comparison/make_record.py
"""
from __future__ import annotations

import json
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
SRC = PLUGIN / "examples" / "collider-angular" / "output" / "results.json"


def main() -> int:
    r = json.loads(SRC.read_text(encoding="utf-8"))
    lo, hi = r["reported_truth_bins"]
    edges = r["truth_edges"][lo:hi + 1]
    values = r["dsigma"]["values"][lo:hi]
    total = [row[lo:hi] for row in r["dsigma"]["covariance"]["total"][lo:hi]]
    obs = {"quantity": "differential-cross-section", "process": "e+e- -> mu+mu-",
           "variables": [{"name": "cos_theta", "unit": "1", "edges": edges}],
           "phase_space": {"definition": "SYNTHETIC: |cos theta| < 0.9 for the outgoing mu-, sqrt(s) = 10 GeV", "fiducial": True},
           "level": "particle-fiducial", "frame": "center-of-mass",
           "normalization": {"kind": "integrated-luminosity", "value": r["config"]["integrated_luminosity_pb"], "unit": "pb^-1"},
           "bin_semantics": "bin-averaged", "unit": "pb",
           "conventions": {"energy_variable": "sqrt_s", "angle_definition": "theta between the incoming e- beam and the outgoing mu-",
                           "synthcol:fiducial_definition": "|cos theta| < 0.9 at particle level"},
           "external_ids": {"hepdata": "none (synthetic record, not published)"}}
    record = {"contract_version": "1.0.0", "artifact_id": "synthetic-published-dsigma", "artifact_type": "dataset-record",
              "objective": "SYNTHETIC record shaped like a published differential cross-section table (T24)",
              "provenance": {"producer_skill": "hep-analysis", "created": "2026-10-02"}, "status": ["synthetic"],
              "bindings": {"experiments": [], "theory": []},
              "versions": {"plugin": "0.1.0", "contracts": "1.0.0", "profiles": {}},
              "inputs": [], "outputs": [], "unresolved_inputs": [],
              "extension": {"dataset_id": "synthcol:synthetic-published-dsigma", "source_evidence_ids": [], "observable": obs,
                            "data": {"edges": edges, "values": values, "unit": "pb",
                                     "uncertainties": [{"name": "total (statistical + 2% luminosity)", "kind": "statistical",
                                                        "correlation": "covariance", "covariance_ref": "synthetic-published-covariance.json"}]},
                            "covariance": {"status": "present", "ref": "synthetic-published-covariance.json",
                                           "note": "statistical block plus a fully correlated 2% luminosity block"},
                            "period": "not-applicable", "status": "synthetic", "experiment_profile": "experiment:synthetic-collider",
                            "conditions": "sqrt_s_gev = 10.0"}}
    (HERE / "synthetic-published-record.json").write_text(json.dumps(record, indent=1) + "\n", encoding="utf-8")
    (HERE / "synthetic-published-covariance.json").write_text(
        json.dumps({"label": "SYNTHETIC", "unit": "pb^2", "edges": edges, "matrix": total}, indent=1) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
