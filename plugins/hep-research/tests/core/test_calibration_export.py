"""Feeding a calibration result back to g4sim (Part B section 10.4 "Feeding back to g4sim", 15.3.19, A21 19-g6; phase 4,
WP-N): propagate.export_g4sim writes theta-hat into a condition-snapshot/1 or alignment-overlay/1 with the result's
hash, effective grade, uses and flags in source_of_facts; use.check_export rejects an exported record without the
result's hash and checks the use matrix of section 10.2. Every negative case has a positive control that passes."""
from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import calibration_fixtures as F  # noqa: E402
import calibration_g4sim_fixtures as G4  # noqa: E402
from contracts.schema import validate  # noqa: E402
from core.calibration import deps, model_identity, use  # noqa: E402
from core.calibration import propagate as P  # noqa: E402
from core.geometry import alignment  # noqa: E402
from core.simulation import conditions  # noqa: E402

SCHEMA_FILE = {"condition-snapshot/1": "condition_snapshot.json", "alignment-overlay/1": "alignment_overlay.json"}


def inputs(**kw):
    c = dict(incomplete=False, mandatory_gate_failed=False, real_data=True, vmode="holdout", design_only=False,
             p7_failed=False, v_pass=True, power_ok=True, testable_ok=True, validation_data_reuse="none",
             validation_data_simulated=False, earlier_failure_record="none", own_flags=set())
    c.update(kw)
    return c


def result(beta=None, **kw):
    """A finalized calibration-result/1 (result_sha256 after version_id) graded by use.judge."""
    j = use.judge(inputs(**kw), [])
    r = {"schema": "calibration-result/1", "contract_sha256": F.h("c"), "data_sha256": [F.CAL, F.VAL],
         "plan_sha256": F.h("p"), "contract_versions": [F.h("c")], "engine_version": "0.1.0",
         "beta_hat": beta or {"threshold_0": 2.25, "shift_x": 0.0375},
         "grade": {k: j[k] for k in ("own_grade", "effective_grade", "uses", "flags", "variation_flags")},
         "gates": {"P4": "passed"}, "validation": {"V": "passed"}, "k": 3, "k0": 3, "unused_observables": [],
         "upstream": [], "status": ["synthetic"]}
    payload = {"contract_sha256": F.h("c"), "data_sha256": F.CAL, "plan_sha256": F.h("p"), "engine_version": "0.1.0",
               "parent_versions": [], "values": {"beta_hat": r["beta_hat"]}}
    return deps.finalize_result(r, payload)


def contract():
    c = G4.contract()
    c["parameters"].append(G4.parameter("shift_x", "theta", "reco", "alignment-overlay", "/shifts/0/delta_mm/0"))
    return c


def schema_errors(record):
    return [f.as_dict() for f in validate(record, SCHEMA_FILE[record["schema"]]).errors]


class Export(unittest.TestCase):
    def setUp(self):
        self.r = result()
        self.c = contract()

    def test_snapshot_export(self):
        rec = P.export_g4sim(G4.snapshot(), self.r, self.c, "production")
        self.assertEqual(schema_errors(rec), [])
        conditions.check_snapshot(rec, ("volume", "channel"))
        self.assertEqual(rec["iovs"][0]["rows"][0]["threshold"], 2.25)
        self.assertEqual(rec["iovs"][0]["rows"][0]["gain_factor"], 1.02)          # not bound: unchanged
        sof = rec["source_of_facts"]
        self.assertEqual(sof["/iovs/0/rows/0/threshold"], "calibration-result:" + self.r["result_sha256"])
        self.assertEqual(sof["/iovs"], "synthetic")                                # the template's entry stays
        self.assertEqual(sof["calibration_result"]["result_sha256"], self.r["result_sha256"])
        self.assertEqual(sof["calibration_result"]["effective_grade"], "validated-in-scope")
        self.assertEqual(sof["calibration_result"]["use"], "production")
        self.assertEqual(use.check_export(rec, self.r), [])
        # the model identity masks source_of_facts and the theta values (D86): the export changes no identity
        tb = G4.tables()["condition-snapshot"]
        rule = dict(G4.EVENT_TIME)
        self.assertEqual(model_identity.snapshot_hash(rec, tb, ["/iovs/0/rows/0/threshold"], rule),
                         model_identity.snapshot_hash(G4.snapshot(), tb, ["/iovs/0/rows/0/threshold"], rule))

    def test_overlay_export(self):
        rec = P.export_g4sim(G4.overlay(), self.r, self.c, "production")
        self.assertEqual(schema_errors(rec), [])
        alignment.check_overlay(rec)
        self.assertEqual(rec["shifts"][0]["delta_mm"], ["0.0375", "0", "0"])
        self.assertEqual(rec["source_of_facts"]["calibration_result"]["parameters"],
                         {"/shifts/0/delta_mm/0": "shift_x"})
        self.assertEqual(use.check_export(rec, self.r), [])
        small = P.export_g4sim(G4.overlay(), self.r, self.c, "production", {"shift_x": 1e-7, "threshold_0": 1.0})
        self.assertEqual(small["shifts"][0]["delta_mm"][0], "0.0000001")           # decimal, no exponent

    def test_export_refusals(self):
        """Negatives of the export, each next to its control above (test_snapshot_export)."""
        cases = {
            "export.no_hash": (G4.snapshot(), {k: v for k, v in self.r.items() if k != "result_sha256"}, self.c),
            "export.no_grade": (G4.snapshot(), dict(self.r, grade={"effective_grade": "incomplete", "uses": [],
                                                                   "flags": []}), self.c),
            "export.schema": ({"schema": "response-pipeline/1"}, self.r, self.c),
            "export.values": (G4.snapshot(), dict(self.r, beta_hat={"shift_x": 0.1}), self.c),
        }
        nothing = contract()
        nothing["parameters"] = [p for p in nothing["parameters"] if p["name"] != "threshold_0"]
        cases["export.nothing"] = (G4.snapshot(), self.r, nothing)
        dead = contract()
        dead["parameters"].append(G4.parameter("dead", "theta", "electronics", "condition-snapshot",
                                               "/iovs/0/rows/0/dead"))
        cases["export.binding"] = (G4.snapshot(), dict(self.r, beta_hat={**self.r["beta_hat"], "dead": 1}), dead)
        missing = contract()
        missing["parameters"][5]["bindings"] = [{"document": "condition-snapshot", "pointer": "/iovs/3/rows/0/threshold"}]
        cases["export.pointer"] = (G4.snapshot(), self.r, missing)
        for code, (tpl, res, con) in cases.items():
            with self.subTest(code):
                with self.assertRaises(P.PropagationError) as cm:
                    P.export_g4sim(tpl, res, con, "production")
                self.assertEqual(cm.exception.code, code)


class CheckExport(unittest.TestCase):
    """Section 15.3.19: an exported condition-snapshot/1 or alignment-overlay/1 without the calibration result's hash in
    source_of_facts is rejected by calib_use.py (section 10.4); A21 19-g6: the use matrix on the exported record."""

    def setUp(self):
        self.r = result()
        self.snap = P.export_g4sim(G4.snapshot(), self.r, contract(), "production")
        self.over = P.export_g4sim(G4.overlay(), self.r, contract(), "production")

    def codes(self, record, res=None):
        return [f["code"] for f in use.check_export(record, self.r if res is None else res)]

    def test_controls_accepted(self):
        for rec in (self.snap, self.over):
            self.assertEqual(self.codes(rec), [])
            self.assertEqual(schema_errors(rec), [])

    def test_without_source_of_facts_rejected(self):
        for rec in (self.snap, self.over):
            with self.subTest(rec["schema"]):
                bare = {k: v for k, v in rec.items() if k != "source_of_facts"}
                self.assertEqual(schema_errors(bare), [])          # g4sim's schema accepts it: optional in S9
                self.assertEqual(self.codes(bare), ["export.source_of_facts"])
                # g4sim's own source label (the template's), no calibration result: rejected
                self.assertEqual(self.codes(dict(rec, source_of_facts={"/shifts": "survey"})),
                                 ["export.source_of_facts"])
                # a number instead of the hash: rejected
                sof = copy.deepcopy(rec["source_of_facts"])
                sof["calibration_result"]["result_sha256"] = "2.25"
                self.assertEqual(self.codes(dict(rec, source_of_facts=sof)), ["export.source_of_facts"])

    def test_another_results_hash_rejected(self):
        other = result(beta={"threshold_0": 2.5, "shift_x": 0.0375})
        self.assertIn("export.hash_mismatch", self.codes(self.snap, other))
        self.assertEqual(self.codes(P.export_g4sim(G4.snapshot(), other, contract(), "production"), other), [])

    def test_result_hash_must_recompute(self):
        forged = dict(self.r, beta_hat={"threshold_0": 9.0, "shift_x": 0.0375})
        self.assertIn("export.result_hash", self.codes(self.snap, forged))

    def test_stated_grade_must_be_the_results(self):
        prov = result(own_flags={"closure-not-tested"})
        rec = P.export_g4sim(G4.snapshot(), prov, contract(), "systematic-variation")
        self.assertEqual(self.codes(rec, prov), [])
        sof = copy.deepcopy(rec["source_of_facts"])
        sof["calibration_result"]["flags"] = []
        sof["calibration_result"]["effective_grade"] = "validated-in-scope"
        self.assertIn("export.grade_mismatch", self.codes(dict(rec, source_of_facts=sof), prov))

    def test_use_matrix(self):
        """Section 15.3.17 "projection used for a production correction is rejected": the export refuses a use the
        result does not allow (review F8), and calib_use rejects a record whose stated use was edited to one; production
        simulation accepts only validated-in-scope (section 10.4); calibrated-unvalidated is accepted for systematic
        variations; a use-blocking flag removes publication. Controls: the allowed uses are exported and accepted."""
        def refused(tpl, res, use):
            with self.assertRaises(P.PropagationError) as cm:
                P.export_g4sim(tpl, res, contract(), use)
            self.assertEqual(cm.exception.code, "export.use")

        def edited(tpl, res, allowed, use):
            rec = P.export_g4sim(tpl, res, contract(), allowed)
            rec["source_of_facts"][P.SOURCE_KEY]["use"] = use
            return self.codes(rec, res)

        proj = result(real_data=False)
        self.assertEqual(proj["grade"]["effective_grade"], "projection")
        refused(G4.snapshot(), proj, "production")
        self.assertEqual(edited(G4.snapshot(), proj, "design-study", "production"), ["export.use"])
        self.assertEqual(self.codes(P.export_g4sim(G4.snapshot(), proj, contract(), "design-study"), proj), [])
        cu = result(v_pass=False)
        refused(G4.overlay(), cu, "production")
        self.assertEqual(edited(G4.overlay(), cu, "systematic-variation", "production"), ["export.use"])
        self.assertEqual(self.codes(P.export_g4sim(G4.overlay(), cu, contract(), "systematic-variation"), cu), [])
        failed = result(mandatory_gate_failed=True, own_flags={"outside-validated-range"})
        refused(G4.snapshot(), failed, "systematic-variation")
        self.assertEqual(self.codes(P.export_g4sim(G4.snapshot(), failed, contract(), "diagnostics"), failed), [])
        prov = result(own_flags={"preliminary"})
        refused(G4.snapshot(), prov, "publication")
        self.assertEqual(self.codes(P.export_g4sim(G4.snapshot(), prov, contract(), "production"), prov), [])
        refused(G4.snapshot(), self.r, "make-believe")

    def test_values_must_be_the_results(self):
        rec = copy.deepcopy(self.snap)
        rec["iovs"][0]["rows"][0]["threshold"] = 3.0
        self.assertEqual(self.codes(rec), ["export.value_mismatch"])
        sof = copy.deepcopy(self.over["source_of_facts"])
        sof["/shifts/0/delta_mm/0"] = "survey"
        self.assertEqual(self.codes(dict(self.over, source_of_facts=sof)), ["export.hash_mismatch"])

    def test_written_values_must_be_declared(self):
        """Review F3: a tampered value cannot hide by emptying or misnaming the entry's parameter map, nor by being
        labelled with the result's hash without being declared. Control: the untampered record is accepted."""
        self.assertEqual(self.codes(self.snap), [])
        key = P.SOURCE_KEY
        for params in ({}, {"/iovs/0/rows/0/threshold": "not_a_parameter"}):
            rec = copy.deepcopy(self.snap)
            rec["iovs"][0]["rows"][0]["threshold"] = 3.0
            rec["source_of_facts"][key]["parameters"] = params
            with self.subTest(params=params):
                self.assertIn("export.parameters", self.codes(rec))

    def test_not_an_exported_record(self):
        self.assertEqual(self.codes({"schema": "detector-spec/1"}), ["export.schema"])


if __name__ == "__main__":
    unittest.main()
