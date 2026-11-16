"""Generic-layer sufficiency (Part B section 12, section 17 phase-4 gate): the eight detector-type node-binding examples
of hep-detector `assets/simulation-calibration/` pass the existing contract checker (calib_contract.py check) and the
chain derivation (calib_chain.py p4 and candidates, section 11.4) unchanged. Each example is a contract fragment that
the synthetic fixture of calibration_fixtures completes with what an experiment instance supplies (section 11.2):
observables, event samples, data releases and the five model identity items (synthetic hashes here). Also checks the
shape of the eight specialization pages (section 11.1 items 1-8; A21: item 7 holds only verified citations or "no
literature value"; item 8 only simulation settings with an observable). Each negative test has a positive control."""
from __future__ import annotations

import copy
import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import calibration_fixtures as F  # noqa: E402
from core.calibration import chain  # noqa: E402
from core.calibration import contract as cc  # noqa: E402
from core.calibration import data_release as release  # noqa: E402

DETECTOR = ROOT / "skills" / "hep-detector"
EXAMPLES = DETECTOR / "assets" / "simulation-calibration"
PAGES = DETECTOR / "references" / "simulation-calibration"
SCRIPTS = ROOT / "skills" / "hep-statistics" / "scripts"
TYPES = {"ecal": "ecal.md", "hcal": "hcal.md", "rich": "rich.md", "dirc": "dirc.md", "trd": "trd.md",
         "tracker": "tracker.md", "tof": "tof.md", "muon": "muon-detector.md"}
SHA = "ab" * 32
IDENTITY = {"detector_spec": [SHA, None], "simulation_request": SHA, "run_physics": SHA, "response_pipeline": SHA,
            "build_environment": {"build_hash": SHA, "geant4_version": "11.2.1", "datasets": {"G4EMLOW": "8.5"}}}
RESIM = ["resimulation", "surrogate-model"]
# The candidate methods each page states (section 3.6 step 1, from section 11.4 Table 2).
EXPECTED = {
    "ecal": {"beam_energy": ["analytic-reweighting"], "dead_material_mm": RESIM, "birks": ["rerun"],
             "light_yield": ["rerun"], "wrap_reflectivity": RESIM, "gain": ["rerun"], "noise_sigma": ["rerun"]},
    "hcal": {"beam_energy": ["analytic-reweighting"], "absorber_mm": RESIM, "production_cut": RESIM,
             "birks": ["rerun"], "light_yield": ["rerun"], "gain": ["rerun"]},
    "rich": {"aerogel_rindex": RESIM, "mirror_tilt": RESIM, "sensor_efficiency": RESIM, "gain": ["rerun"]},
    "dirc": {"quartz_rindex": RESIM, "bar_reflectivity": RESIM, "sensor_efficiency": RESIM, "time_offset": ["rerun"]},
    "trd": {"foil_thickness": RESIM, "gas_gain": ["rerun"], "adc_noise": ["rerun"]},
    "tracker": {"sensor_thickness": RESIM, "noise_sigma": ["rerun"], "threshold": ["rerun"],
                "lorentz_shift": ["rerun"], "module_b_offset": ["rerun"]},
    "tof": {"light_yield": ["rerun"], "attenuation_length": RESIM, "t0": ["rerun"], "slewing": ["rerun"]},
    "muon": {"absorber_mm": RESIM, "gas_gain": ["rerun"], "hv_gain_factor": ["rerun"], "threshold": ["rerun"],
             "t0": ["rerun"]},
}
ITEM_HEADINGS = ("## 1. Stage mapping", "## 2. Mechanisms", "## 3. Kernel properties", "## 4. Storage",
                 "## 5. Reference catalog", "## 6. Special functionals", "## 7. V_model correlation kernel (advisory)",
                 "## 8. Alternative hypotheses (advisory)", "## Node-binding example")
CITATION = re.compile(r"arXiv:\d{4}\.\d{4,5}|inspirehep\.net/literature/\d+|doi\.org/10\.\S+|10\.\d{4,9}/\S+")


def example(kind: str) -> dict:
    return json.loads((EXAMPLES / f"{kind}.binding.example.json").read_text(encoding="utf-8"))


def completed(kind: str) -> tuple[dict, dict]:
    """(contract, plan): the example's fragment over the synthetic instance of calibration_fixtures."""
    ex = example(kind)
    fragment = copy.deepcopy(ex["contract_fragment"])
    c = F.contract()
    for key in ("simulator", "source", "stage_graph", "parameters", "references", "models"):
        c[key] = fragment[key]
    c["validation"]["alternatives"] = fragment["validation_alternatives"]
    for model in c["models"]["enumerated"] + c["models"]["absorbed"]:
        model["identity"] = copy.deepcopy(IDENTITY)
    return c, copy.deepcopy(ex["plan"])


def methods(result: dict) -> dict:
    return {name: [e["method"] for e in entries] for name, entries in result["parameters"].items()}


def codes(findings) -> set:
    return {f["code"] for f in findings}


class Engine(unittest.TestCase):
    """The examples through core.calibration as it is (no change of the generic layer)."""

    def test_every_example_is_accepted_and_derives_its_candidates(self):
        self.assertEqual(sorted(p.name.split(".")[0] for p in EXAMPLES.glob("*.binding.example.json")), sorted(TYPES))
        for kind in TYPES:
            with self.subTest(kind):
                c, plan = completed(kind)
                r = cc.check(c, F.releases())
                self.assertEqual((r["status"], r["findings"]), ("accepted", []))
                self.assertIn(cc.IDENTITY_UNVERIFIED, r["deferred"])       # synthetic identities, not recomputed
                self.assertEqual(chain.p4(c)["status"], "passed")
                got = chain.candidate_methods(c, plan)
                self.assertEqual((got["status"], got["findings"], got["without_candidate"]), ("ok", [], []))
                self.assertEqual(methods(got), EXPECTED[kind])

    def test_without_references_p4_fails(self):
        c, _ = completed("ecal")
        self.assertEqual(chain.p4(c)["status"], "passed")                    # control
        c["references"] = []
        r = chain.p4(c)
        self.assertEqual((r["status"], r["remedy_level"]), ("failed", "contract"))

    def test_an_injection_inside_a_node_is_not_split(self):
        c, _ = completed("ecal")
        led = {"id": "led", "type": "mid-chain-injection", "edge": {"from": "collection", "to": "pde"},
               "observation": "cluster_energy", "conversion": {"relation": "S/S0 = (R/R0)^alpha"}}
        c["references"].append(led)
        self.assertEqual(cc.check(c, F.releases())["status"], "accepted")    # control: on an edge
        c["references"][-1] = dict(led, edge={"inside": "collection"})
        self.assertIn("reference.injection_not_split", codes(cc.check(c, F.releases())["findings"]))

    def test_single_photoelectron_split_is_generic_but_refused_by_g4sim(self):
        """The generic layer represents the 4a/4b split; the g4sim binding refuses the reference (no hand-off before
        response stage 3, section 11.4). The example without it is the control."""
        c, plan = completed("ecal")
        self.assertEqual(chain.candidate_methods(c, plan)["status"], "ok")
        c["references"].append({"id": "spe", "type": "mid-chain-injection", "edge": {"from": "pde", "to": "sensor"},
                                "observation": "cluster_energy", "conversion": {"relation": "single photoelectron"}})
        self.assertEqual(cc.check(c, F.releases())["status"], "accepted")
        got = chain.candidate_methods(c, plan)
        self.assertEqual(got["status"], "failed")
        self.assertIn("binding.injection_single_pe", codes(got["findings"]))

    def test_a_parameter_shift_alternative_is_rejected(self):
        c, _ = completed("trd")
        c["validation"]["alternatives"].append({"kind": "parameter-shift", "description": "gas gain +10%"})
        self.assertIn("validation.alternative_shift", codes(cc.check(c, F.releases())["findings"]))

    def test_an_emission_time_theta_has_no_table_2_row(self):
        c, plan = completed("tof")
        c["parameters"].append({"name": "decay", "role": "theta", "nodes": ["quanta"], "mechanism": "time",
                                "physical_bounds": [0.5, 5.0], "sampling_bounds": [1.0, 3.0],
                                "bindings": [{"document": "detector-spec",
                                              "pointer": "/materials/PlasticScint/scintillation/components/0/decay_ns"}]})
        self.assertIn("binding.not_in_table_2", codes(cc.check(c, F.releases())["findings"]))
        self.assertEqual(chain.candidate_methods(c, plan)["status"], "failed")

    def test_two_physics_lists_need_their_confirmation_record(self):
        c, _ = completed("hcal")
        self.assertEqual(cc.check(c, F.releases())["status"], "accepted")    # control: the record is attached
        c["models"].pop("physics_list_confirmations")
        self.assertIn("models.physics_list_unconfirmed", codes(cc.check(c, F.releases())["findings"]))


class Scripts(unittest.TestCase):
    """The same examples through the unchanged CLIs (calib_contract.py check validates the schema first)."""

    def run_script(self, script, *args):
        res = subprocess.run([sys.executable, "-I", str(SCRIPTS / script), *map(str, args)], capture_output=True,
                             text=True, timeout=120)
        return res.returncode, json.loads(res.stdout)

    def test_scripts_accept_every_example(self):
        rels = F.releases()
        with tempfile.TemporaryDirectory() as scratch:
            d = Path(scratch)
            (d / "cal.json").write_text(json.dumps(rels[F.CAL]))
            (d / "val.json").write_text(json.dumps(rels[F.VAL]))
            for kind in TYPES:
                with self.subTest(kind):
                    c, plan = completed(kind)
                    c["data"] = {"calibration_releases": [release.release_hash(rels[F.CAL])],
                                 "validation_releases": [release.release_hash(rels[F.VAL])]}
                    (d / "c.json").write_text(json.dumps(c))
                    (d / "p.json").write_text(json.dumps(plan))
                    rc, out = self.run_script("calib_contract.py", "check", "--contract", d / "c.json",
                                              "--release", d / "cal.json", "--release", d / "val.json")
                    self.assertEqual((rc, out["status"]), (0, "accepted"), out.get("findings"))
                    rc, out = self.run_script("calib_chain.py", "p4", "--contract", d / "c.json")
                    self.assertEqual((rc, out["status"]), (0, "passed"))
                    rc, out = self.run_script("calib_chain.py", "candidates", "--contract", d / "c.json",
                                              "--plan", d / "p.json")
                    self.assertEqual((rc, methods(out)), (0, EXPECTED[kind]))
            c, _ = completed("ecal")
            c["stage_graph"]["edges"].append({"from": "reco", "to": "source"})       # negative: a cycle
            (d / "cyc.json").write_text(json.dumps(c))
            rc, out = self.run_script("calib_chain.py", "check", "--contract", d / "cyc.json")
            self.assertEqual((rc, codes(out["findings"])), (1, {"graph.cycle"}))


class Pages(unittest.TestCase):
    """Section 11.1 items 1-8 on every page; A21 on items 7 and 8."""

    def section(self, text, heading):
        start = text.index(heading)
        end = text.find("\n## ", start + 1)
        return text[start:end if end > 0 else None]

    def test_every_page_carries_the_eight_items_and_its_example(self):
        for kind, page in TYPES.items():
            with self.subTest(kind):
                text = (PAGES / page).read_text(encoding="utf-8")
                positions = [text.find(h) for h in ITEM_HEADINGS]
                self.assertTrue(all(p >= 0 for p in positions), [h for h, p in zip(ITEM_HEADINGS, positions) if p < 0])
                self.assertEqual(positions, sorted(positions))
                self.assertIn(f"assets/simulation-calibration/{kind}.binding.example.json", text)

    def test_item_7_cells_are_a_citation_or_no_literature_value(self):
        for kind, page in TYPES.items():
            text = self.section((PAGES / page).read_text(encoding="utf-8"), ITEM_HEADINGS[6])
            rows = [r for r in text.splitlines() if r.startswith("|") and not r.startswith("|---")][1:]
            self.assertTrue(rows, kind)
            for row in rows:
                for cell in [x.strip() for x in row.strip("|").split("|")][1:]:
                    with self.subTest(kind, cell=cell):
                        self.assertTrue(cell == "no literature value" or CITATION.search(cell), cell)
        self.assertFalse(CITATION.search("f = 0.05"))                         # control: a bare number fails

    def test_item_8_alternatives_are_simulation_settings_with_an_observable(self):
        for kind in TYPES:
            with self.subTest(kind):
                alts = example(kind)["contract_fragment"]["validation_alternatives"]
                self.assertTrue(alts)
                for a in alts:
                    self.assertEqual(a["kind"], "simulation-setting")
                    self.assertTrue(a.get("observable") and a.get("identity_difference"))
                rows = [r for r in self.section((PAGES / TYPES[kind]).read_text(encoding="utf-8"),
                                                ITEM_HEADINGS[7]).splitlines() if r.startswith("| ")][1:]
                self.assertGreaterEqual(len(rows), 2)
                self.assertTrue(all(len([x for x in r.strip("|").split("|") if x.strip()]) == 2 for r in rows))


if __name__ == "__main__":
    unittest.main()
