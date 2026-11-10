"""The toy detector of Part B section 15.1 and the evaluator interface of section 7.1 (phase 1): the stage graph of the
phase-0 fixture is simulated node by node, reproducibly, with its variants; resample + evaluate_from is the rerun;
a deterministic rerun equals a full re-evaluation with the same random numbers (gate 2 item 3)."""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests" / "core"))

import calibration_phase1 as H  # noqa: E402
from core.calibration import evaluator as E  # noqa: E402
from core.calibration import toy  # noqa: E402

N = 4000


def small(plan=None, **spec):
    plan = dict(plan or {"seeds": {"nominal": 5}})
    plan["evaluator"] = {"kind": "toy-detector", "events": N, **spec}
    return E.make(plan)


class ToyDetector(unittest.TestCase):
    def test_graph_matches_the_phase0_fixture(self):
        fx = json.loads((ROOT / "core" / "calibration" / "data" / "toy_detector.json").read_text())
        nodes = {n["id"] for n in fx["contract"]["stage_graph"]["nodes"]}
        model = toy.build_toy(100)
        simulated = {n for r in model.runs.values() for n in r.kernels}
        self.assertEqual(simulated, nodes)
        for p in fx["contract"]["parameters"]:
            self.assertEqual(toy.TOY_PARAM_NODES[p["name"]], p["nodes"], p["name"])
        edges = {(e["from"], e["to"]) for e in fx["contract"]["stage_graph"]["edges"]}
        self.assertEqual({(p, c) for c, ps in toy.TOY_PARENTS.items() for p in ps}, edges)
        self.assertEqual(model.status, ["synthetic"])

    def test_references_and_branches(self):
        model = toy.build_toy(100)
        self.assertIsInstance(model.runs["light"].kernels["photon_generation"], toy.Fixed)   # light source
        self.assertIsInstance(model.runs["spe"].kernels["pde"], toy.Fixed)                   # single photoelectron
        self.assertNotIn("input", model.runs["track5"].kernels)                              # track branch alone
        self.assertIn("e_over_p", model.runs["eop"].kernels)                                 # merge node
        sub = toy.build_toy(100, "subgraph")
        self.assertFalse(any("track" in r or r == "eop" for r in sub.runs))

    def test_reproducible_and_seeded(self):
        a, b, c = small(), small(), small({"seeds": {"nominal": 6}})
        np.testing.assert_array_equal(a.evaluate({})["pred"], b.evaluate({})["pred"])
        self.assertFalse(np.allclose(a.evaluate({})["pred"], c.evaluate({})["pred"]))

    def test_nominal_scale_and_interface(self):
        r = small().evaluate({})
        for k in ("pred", "V_MC", "n_eff", "node_diag", "V_emu", "V_learn"):
            self.assertIn(k, r)
        pred = dict(zip(r["names"], r["pred"]))
        sd = dict(zip(r["names"], np.sqrt(np.diag(r["V_MC"]))))
        for e in toy.BEAM_ENERGIES:                     # the reconstruction constant makes E_a an energy
            self.assertLess(abs(pred[f"beam{int(e)}_e_mean"] - e * 0.995), 6 * sd[f"beam{int(e)}_e_mean"] + 0.01 * e)
        self.assertAlmostEqual(pred["light_e_mean"], 0.25 * 400 * 10 / toy.C_CAL, delta=5 * sd["light_e_mean"])
        self.assertTrue(0.5 < pred["spe_efficiency"] < 1.0)                     # zero suppression in the spe run

    def test_resample_and_evaluate_from_is_the_rerun(self):
        ev = small()
        th = {"pde": 0.252}
        s = {"resample": 17}
        a = ev.evaluate_from("pde", ev.resample("pde", th, None, None, "nominal", None, s), th, None, None,
                             "nominal", s)
        b = ev.rerun("pde", th, 17)
        np.testing.assert_array_equal(a["pred"], b["pred"])

    def test_deterministic_rerun_equals_full_reevaluation(self):
        """Gate 2 item 3 (unit form): a rerun of module b and layer b from stored inputs equals the events generated at
        the new values with the same random numbers, to a relative 1e-12."""
        ev = small()
        for th in ({"relative_gain_b": 1.02}, {"layer_b_offset": 0.1, "sum_term_b": 0.55}):
            rerun = ev.evaluate(th)
            fresh = ev.generate(ev.seeds["nominal"], th)
            full = toy.observe(ev.model, {r: fresh["runs"][r]["events"] for r in fresh["runs"]},
                               {r: np.ones(ev.model.runs[r].n) for r in ev.model.runs})
            np.testing.assert_allclose(rerun["pred"], full["pred"], rtol=1e-12, atol=1e-15)
            self.assertEqual(rerun["methods"], {k: "rerun" for k in th})

    def test_parameter_acts_only_downstream_of_its_nodes(self):
        ev = small()
        base = ev.evaluate({})
        moved = ev.evaluate({"relative_gain_b": 1.02})
        changed = {n for n, a, b in zip(base["names"], base["pred"], moved["pred"]) if a != b}
        self.assertEqual(changed, {f"beam{int(e)}_ratio_mean" for e in toy.BEAM_ENERGIES})

    def test_bimodal_variant_is_mirror_symmetric(self):
        ev = E.make({"evaluator": {"kind": "toy-detector-bimodal", "events": 20_000, "alpha": 2.0, "beta": 2.0},
                     "seeds": {"nominal": 3}})
        a = ev.evaluate({"a": 1.0, "b": 0.6})
        b = ev.evaluate({"a": 0.6, "b": 1.0})
        sd = np.sqrt(np.diag(a["V_MC"]) + np.diag(b["V_MC"]))
        self.assertTrue(np.all(np.abs(a["pred"][:2] - b["pred"][:2]) < 5 * sd[:2]))

    def test_unknown_evaluator_is_incomplete(self):
        with self.assertRaises(E.EvaluatorUnavailable):
            E.make({"evaluator": {"kind": "g4sim"}})


class DesignFixture(unittest.TestCase):
    def test_design_fixture_is_consistent(self):
        fx = H.toy_design()
        model = toy.build_toy(10)
        self.assertEqual([o["name"] for o in fx["contract"]["observables"]], [o.name for o in model.observables])
        self.assertEqual(set(fx["plan"]["methods"]), set(toy.TOY_PARAM_NODES))
        self.assertEqual(fx["status"], "synthetic")


if __name__ == "__main__":
    unittest.main()
