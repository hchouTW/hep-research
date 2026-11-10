"""The calibration schemas of simulator calibration phase 0 (Part B sections 3, 5.1, 9.5, 10.1, 13): the seven abstract
objects, the contract, data release, plan and result, the ledger and the fixture format. Every phase-0 fixture and
written record validates; D11 (approval A6): a result without k, k0 or the unused observables is refused."""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests" / "core"))

import calibration_fixtures as F  # noqa: E402
from contracts.schema import validate  # noqa: E402
from core.calibration import data, deps, use  # noqa: E402

SEVEN = ("calibration_stage_graph", "calibration_mechanism", "calibration_functional", "calibration_control_variable",
         "calibration_reference", "calibration_degeneracy_mode", "calibration_parameter_index")


def errors(value, name):
    return [f.as_dict() for f in validate(value, f"{name}.json").errors]


def result_doc():
    j = use.judge(dict(incomplete=False, mandatory_gate_failed=False, real_data=True, vmode="holdout",
                       design_only=False, p7_failed=False, v_pass=True, power_ok=True, testable_ok=True,
                       validation_data_reuse="none", validation_data_simulated=False, earlier_failure_record="none",
                       own_flags=set()), [])
    r = {"schema": "calibration-result/1", "contract_sha256": F.h("c"), "data_sha256": [F.CAL, F.VAL],
         "plan_sha256": F.h("p"), "contract_versions": [F.h("c")], "engine_version": "0.1.0",
         "grade": {k: j[k] for k in ("own_grade", "effective_grade", "uses", "flags", "variation_flags")},
         "gates": {"P4": "passed"}, "validation": {"V": "passed"}, "k": 3, "k0": 3,
         "unused_observables": [{"observable": "spare", "reason": "rank condition (c)", "clause": "section 9.2"}],
         "upstream": [], "status": ["synthetic"]}
    payload = {"contract_sha256": F.h("c"), "data_sha256": F.CAL, "plan_sha256": F.h("p"), "engine_version": "0.1.0",
               "parent_versions": [], "values": {"beta_hat": {}}}
    return deps.finalize_result(r, payload)


class Schemas(unittest.TestCase):
    def test_seven_abstract_objects_exist(self):
        for name in SEVEN:
            self.assertTrue((ROOT / "contracts" / "schemas" / f"{name}.json").is_file(), name)
        self.assertEqual(errors("yield", "calibration_mechanism"), [])
        self.assertEqual(errors("x-pile-up", "calibration_mechanism"), [])
        self.assertTrue(errors("made-up", "calibration_mechanism"))
        self.assertTrue(errors("skewness", "calibration_functional"))
        self.assertTrue(errors({"name": "E", "level": "true"}, "calibration_control_variable"))
        self.assertEqual(errors({"mechanism": "yield", "channel_set": {"system": 1}, "conditioning": "constant"},
                                "calibration_parameter_index"), [])

    def test_fixtures_validate(self):
        for f in sorted((ROOT / "core" / "calibration" / "data").glob("*.json")):
            with self.subTest(f.name):
                self.assertEqual(errors(json.loads(f.read_text()), "calibration_fixture"), [])

    def test_contract_release_plan(self):
        self.assertEqual(errors(F.contract(), "calibration_contract"), [])
        bad = F.contract()
        bad["validation"]["mode"] = "k-fold"
        self.assertTrue(errors(bad, "calibration_contract"))
        for r in F.releases().values():
            self.assertEqual(errors(r, "calibration_data_release"), [])
        self.assertEqual(errors({"schema": "calibration-plan/1", "kernels": F.toy()["plan"]["kernels"]},
                                "calibration_plan"), [])

    def test_ledger(self):
        led = data.Ledger()
        led.fit_read(F.CAL, ["u1"], led.register_draft("s"))
        k = data.kappa_id(F.h("c"), F.h("p"), "0.1.0")
        led.open_validation(k, F.VAL, ["v1"], ["u1"], {"contract_sha256": F.h("c")})
        led.apply_decision({"kappa": k, "outcome": "fail"})
        self.assertEqual(errors(led.state, "calibration_ledger"), [])

    def test_result_and_d11(self):
        r = result_doc()
        self.assertEqual(errors(r, "calibration_result"), [])
        for key in ("k", "k0", "unused_observables"):
            bad = {x: v for x, v in r.items() if x != key}
            self.assertTrue(errors(bad, "calibration_result"), key)
        bad = json.loads(json.dumps(r))
        bad["unused_observables"][0].pop("reason")
        self.assertTrue(errors(bad, "calibration_result"))
        pend = json.loads(json.dumps(r))
        pend["grade"]["own_grade"] = None                       # a pending input records no own grade (section 10.1)
        self.assertEqual(errors(pend, "calibration_result"), [])


if __name__ == "__main__":
    unittest.main()
