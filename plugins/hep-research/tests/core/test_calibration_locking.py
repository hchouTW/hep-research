"""The locking report of calib_data and its use by calib_contract check (Part B sections 2.1, 5.2 clause 9, 17)."""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from core.calibration import contract as cc  # noqa: E402
from core.calibration import data_checks as D  # noqa: E402
from core.calibration import toy  # noqa: E402
from core.calibration import toy_problem as TP  # noqa: E402

NAMES = ["beam2_e_mean", "beam2_e_width", "light_e_mean", "spe_e_mean"]


def problem():
    return TP.ToyProblem(lambda n: toy.build_toy(n, "subgraph"), NAMES,
                         {"light_yield": {"bounds": (20, 400), "prior": (95, 105)}}, exposure=2000, mc_events=4000,
                         phi_P={"material_thickness": (1.0, 0.05)})


class Locking(unittest.TestCase):
    def test_double_precision_passes(self):
        r = D.locking_report({}, {"representation_format": "float64"}, problem(), points=[{}, {"light_yield": 105}])
        self.assertEqual(r["status"], "passed")
        self.assertEqual(r["rounding_worst"]["ratio"], 0.0)
        self.assertEqual(set(r["not_applicable"]), {"n_min", "block_conversion", "N_exp"})

    def test_coarse_rounding_rejected(self):
        """Values released with one decimal where sigma^(0) is far smaller: rounding not negligible, the contract is
        rejected (section 15.3.5)."""
        r = D.locking_report({}, {"representation_format": {n: {"kind": "fixed", "decimals": 1} for n in NAMES}},
                             problem(), points=[{}])
        self.assertEqual(r["status"], "failed")
        self.assertEqual(r["findings"][0]["code"], "data.rounding")
        out = cc.check({}, locking=json.loads(json.dumps(r, default=str)))
        self.assertIn("data.rounding", [f["code"] for f in out["findings"]])

    def test_evaluation_points_include_vertices_and_nuisance_axes(self):
        r = D.locking_report({}, {"representation_format": "float64"}, problem(), n_scan=4)
        self.assertEqual(r["points"], (4 + 2) * 3)

    def test_conventions_against_constraints(self):
        """f_A + f_B = 1 declared while the 0-event convention takes f_A = f_B = 0: rejected (section 15.3.7)."""
        c = {"validation": {"N_d": [{"n": {"f_A": 1, "f_B": 1}, "c": 1.0}]},
             "estimators": {"conventions": {"f_A": {"zero_events": 0.0}, "f_B": {"zero_events": 0.0}}}}
        r = D.locking_report(c, {"representation_format": "float64"}, problem(), points=[{}])
        self.assertIn("data.convention_violates_constraint", [f["code"] for f in r["findings"]])
        c["estimators"]["conventions"]["f_B"]["zero_events"] = 1.0
        r = D.locking_report(c, {"representation_format": "float64"}, problem(), points=[{}])
        self.assertEqual(r["status"], "passed")

    def test_decided_rules_leave_deferred(self):
        r = D.locking_report({}, {"representation_format": "float64"}, problem(), points=[{}])
        out = cc.check({}, locking=r)
        self.assertFalse(any(d.startswith("clause 9 item 2") for d in out["deferred"]))
        self.assertTrue(any(d.startswith("clause 9 item 3") for d in out["deferred"]))


if __name__ == "__main__":
    unittest.main()
