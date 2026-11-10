"""core/calibration/chain (simulator calibration phase 0): the stage graph, candidate methods and P4.

Gate (section 17, phase 0): the three fixtures (ECAL, RICH, tracker; ECAL and tracker each with a pair of overlapping
modules) can derive candidate methods and reachability; the negative test of P4 (section 15.3.1) passes. Also the
toy-detector graph structure and its subgraph and bimodal variants (section 15.1), and the section 3.4 examples."""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from core.calibration import chain  # noqa: E402

DATA = ROOT / "core" / "calibration" / "data"


def load(name):
    return json.loads((DATA / f"{name}.json").read_text())


def only(c, *ids):
    c = json.loads(json.dumps(c))
    c["references"] = [dict(r, enabled=r["id"] in ids) for r in c["references"]]
    return c


class Fixtures(unittest.TestCase):
    def test_every_fixture_is_a_valid_graph_and_derives(self):
        for name in ("ecal", "rich", "tracker", "toy_detector", "toy_detector_subgraph", "toy_detector_bimodal"):
            with self.subTest(name):
                d = load(name)
                self.assertEqual(d["status"], "synthetic")
                c = d["contract"]
                self.assertEqual(chain.check_graph(c["stage_graph"]), [])
                self.assertEqual(chain.check_references(c["stage_graph"], c["references"]), [])
                m = chain.candidate_methods(c, d["plan"])
                self.assertEqual(m["status"], "ok", m["without_candidate"])
                self.assertEqual(set(m["parameters"]), {p["name"] for p in c["parameters"]})
                p4 = chain.p4(c)
                self.assertEqual(p4["status"], "passed", p4["unconstrainable"])

    def test_ecal_and_tracker_have_overlapping_modules(self):
        for name, comp in (("ecal", "crystal_ratio"), ("tracker", "hit_residual"), ("toy_detector", "energy_ratio"),
                           ("toy_detector", "position_difference")):
            g = load(name)["contract"]["stage_graph"]
            self.assertEqual(chain.node_index(g)[comp]["kind"], "comparison")
            self.assertEqual(len(chain.parents_of(g)[comp]), 2)

    def test_candidate_methods_follow_node_properties(self):
        d = load("ecal")
        m = chain.candidate_methods(d["contract"], d["plan"])["parameters"]
        self.assertEqual([x["method"] for x in m["pde"]], ["analytic-reweighting"])
        self.assertEqual([x["method"] for x in m["dead_material"]], ["resimulation", "surrogate-model"])
        self.assertEqual([x["method"] for x in m["relative_gain_b"]], ["rerun"])
        plan = json.loads(json.dumps(d["plan"]))
        plan["kernels"]["pde"]["support_declared"] = False
        self.assertEqual(chain.candidate_methods(d["contract"], plan)["parameters"]["pde"], [])
        plan["kernels"]["shower_deposition"]["stored"]["steps"] = True
        got = [x["method"] for x in chain.candidate_methods(d["contract"], plan)["parameters"]["dead_material"]]
        self.assertEqual(got, ["step-level-reweighting", "resimulation", "surrogate-model"])
        self.assertEqual(chain.candidate_methods(d["contract"], dict(plan, node_binding={"x": 1}))["status"],
                         "incomplete")                                      # g4sim Table 2: phase 3


class ReferenceCoverage(unittest.TestCase):
    def test_15_3_1_p4_subgraph(self):
        """Subgraph variant, known input switched off, only single-photoelectron injection left: yield and PDE are
        decided as not constrainable; the gain can be."""
        c = only(load("toy_detector_subgraph")["contract"], "single_photoelectron")
        r = chain.p4(c)
        self.assertEqual(r["status"], "failed")
        self.assertIn("light_yield", r["unconstrainable"])
        self.assertIn("pde", r["unconstrainable"])
        self.assertEqual(r["parameters"]["gain"], ["single_photoelectron"])
        self.assertEqual(r["remedy_level"], "contract")

    def test_section_3_4_examples(self):
        toy = load("toy_detector")["contract"]
        g = toy["stage_graph"]
        refs = {r["id"]: r for r in toy["references"]}
        # straight chain: only parameters downstream of the injection edge
        self.assertFalse(chain.can_constrain(g, refs["light_source"], "photon_generation"))
        self.assertTrue(chain.can_constrain(g, refs["light_source"], "pde"))
        # merging branches: the momentum reference of the track branch reaches the calorimeter scale through E/p
        self.assertTrue(chain.can_constrain(g, refs["momentum_reference"], "gain"))
        # a known input constrains all ancestors of its observation node
        self.assertTrue(chain.can_constrain(g, refs["known_input"], "photon_generation"))
        # a reference on the output edge of a comparison node: every ancestor of that node
        self.assertTrue(chain.can_constrain(g, refs["module_overlap"], "module_b"))
        self.assertFalse(chain.can_constrain(g, refs["module_overlap"], "momentum_measurement"))
        # the known input switched off and only the light source left: the yield is not constrainable
        r = chain.p4(only(toy, "light_source"))
        self.assertIn("light_yield", r["unconstrainable"])
        self.assertNotIn("pde", r["unconstrainable"])


class GraphRejections(unittest.TestCase):
    def test_rejections(self):
        g = load("toy_detector_subgraph")["contract"]["stage_graph"]
        bad = json.loads(json.dumps(g))
        bad["nodes"][2]["kernel"] = "unknown"
        self.assertEqual({f["code"] for f in chain.check_graph(bad)}, {"graph.kernel_nature"})
        bad = json.loads(json.dumps(g))
        bad["edges"].append({"from": "pde", "to": "nowhere"})
        self.assertIn("graph.edge_endpoint", {f["code"] for f in chain.check_graph(bad)})
        bad = json.loads(json.dumps(g))
        bad["nodes"].append(dict(bad["nodes"][0]))
        self.assertIn("graph.duplicate_node", {f["code"] for f in chain.check_graph(bad)})
        self.assertEqual(chain.check_graph({"nodes": "x"})[0]["code"], "graph.shape")
        refs = [{"id": "k", "type": "known-input", "edge": {"into": "pde"}, "observation": "module_a"},
                {"id": "x", "type": "made-up", "edge": {"into": "input"}, "observation": "module_a"},
                {"id": "o", "type": "population-feature", "edge": {"out_of": "module_a"}, "observation": "gain"}]
        self.assertEqual({f["code"] for f in chain.check_references(g, refs)},
                         {"reference.known_input_edge", "reference.type", "reference.observation"})


if __name__ == "__main__":
    unittest.main()
