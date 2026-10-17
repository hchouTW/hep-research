"""D4: survival_feeddown.py. Oracles: one layer gives exp(-x/lambda) with lambda = A / (N_A sigma); the synthetic
example of correction-chain.md (x = 10 g/cm2, lambda = 20 g/cm2: P = 0.607; 1000 heavy nuclei with P_heavy = 0.55
and a 10% fragmentation fraction: feed-down 45 events); the mixture rule equals layer by layer; the cross-section
scale derivative equals a finite difference; a table without a source is unvalidated; recipe steps carry correction
keys for the catalog effects survival and fragmentation_feeddown. All inputs are SYNTHETIC."""
import json
import math
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[3]
SCRIPT = PLUGIN / "skills" / "hep-detector" / "scripts" / "survival_feeddown.py"
ASSETS = PLUGIN / "skills" / "hep-detector" / "assets"
sys.path.insert(0, str(PLUGIN))
from core import constants  # noqa: E402

NA = constants.constant("avogadro_constant").value
MB = constants.convert(1.0, "mb", "cm2")


def sigma_mb(A, lam):
    """cross section (mb) that gives interaction length lam (g/cm2) on a target of mass number A"""
    return A / (NA * lam) / MB


def run(*args):
    p = subprocess.run([sys.executable, "-B", str(SCRIPT), *map(str, args)], capture_output=True, text=True,
                       timeout=600)
    return p.returncode, (json.loads(p.stdout) if p.stdout.strip().startswith("{") else p.stdout)


class SurvivalFeeddown(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.d = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, name, obj):
        p = self.d / name
        p.write_text(json.dumps(obj), encoding="utf-8")
        return p

    def example_inputs(self, source="SYNTHETIC: invented"):
        # the correction-chain.md example: one layer, x = 10 g/cm2; lambda_light = 20, P_heavy = 0.55
        lam_heavy = -10.0 / math.log(0.55)
        layers = self.write("l.json", {"layers": [{"name": "top", "grammage_g_cm2": 10.0,
                                                   "composition": [{"target": "C", "A": 12.0, "mass_fraction": 1.0}]}]})
        xs = {"unit": "mb", "inelastic": {"light": {"C": sigma_mb(12.0, 20.0)}, "heavy": {"C": sigma_mb(12.0, lam_heavy)}},
              "fragmentation_fraction": {"heavy": {"light": 0.10}}}
        if source:
            xs["source"] = source
        species = self.write("s.json", {"species": [{"name": "light"}, {"name": "heavy", "arriving": 1000}]})
        return layers, species, self.write("x.json", xs)

    def test_correction_chain_example(self):
        layers, species, xs = self.example_inputs()
        code, out = run("compute", "--layers", layers, "--species", species, "--xs", xs)
        self.assertEqual(code, 0, out)
        sp = {s["species"]: s for s in out["species"]}
        self.assertAlmostEqual(sp["light"]["survival_probability"], math.exp(-0.5), places=12)
        self.assertAlmostEqual(round(sp["light"]["survival_probability"], 3), 0.607)
        self.assertAlmostEqual(sp["light"]["correction_factor"], math.exp(0.5), places=12)
        self.assertAlmostEqual(sp["heavy"]["survival_probability"], 0.55, places=12)
        fd = out["feeddown"][0]
        self.assertEqual((fd["from"], fd["to"]), ("heavy", "light"))
        self.assertAlmostEqual(fd["events"], 45.0, places=9)
        self.assertEqual(out["status"], "ok")
        self.assertEqual(out["status_label"], "unvalidated")

    def test_mixture_rule_equals_layer_by_layer(self):
        xs = self.write("x.json", json.load(open(ASSETS / "survival-xs.example.json")))
        species = self.write("s.json", {"species": [{"name": "B"}, {"name": "C"}]})
        mixed = self.write("m.json", {"layers": [{"name": "mix", "grammage_g_cm2": 5.0, "composition": [
            {"target": "C", "A": 12.011, "mass_fraction": 0.7}, {"target": "Al", "A": 26.98, "mass_fraction": 0.3}]}]})
        split = self.write("p.json", {"layers": [
            {"name": "c", "grammage_g_cm2": 3.5, "composition": [{"target": "C", "A": 12.011, "mass_fraction": 1.0}]},
            {"name": "al", "grammage_g_cm2": 1.5, "composition": [{"target": "Al", "A": 26.98, "mass_fraction": 1.0}]}]})
        _, a = run("compute", "--layers", mixed, "--species", species, "--xs", xs)
        _, b = run("compute", "--layers", split, "--species", species, "--xs", xs)
        for sa, sb in zip(a["species"], b["species"]):
            self.assertAlmostEqual(sa["survival_probability"], sb["survival_probability"], places=13)

    def test_one_layer_closed_form_and_scale_derivative(self):
        layers = ASSETS / "survival-layers.example.json"
        code, out = run("compute", "--layers", layers, "--species", self.write("s.json", {"species": [{"name": "B"}]}),
                        "--xs", ASSETS / "survival-xs.example.json", "--scale-nuisance", "0.05")
        self.assertEqual(code, 0, out)
        b = out["species"][0]
        xs = json.load(open(ASSETS / "survival-xs.example.json"))["inelastic"]["B"]
        inv = 4.0 * (0.9 * NA * xs["C"] * MB / 12.011 + 0.1 * NA * xs["H"] * MB / 1.008) + 2.0 * NA * xs["Al"] * MB / 26.98
        self.assertAlmostEqual(b["survival_probability"], math.exp(-inv), places=12)
        # dP/ds = P ln P for sigma -> (1 + s) sigma
        self.assertAlmostEqual(b["dP_dscale"], b["survival_probability"] * math.log(b["survival_probability"]), places=12)
        lo, hi = b["scale_variation"]["down"], b["scale_variation"]["up"]
        self.assertAlmostEqual(lo, math.exp(-inv * 0.95), places=12)
        self.assertAlmostEqual(hi, math.exp(-inv * 1.05), places=12)

    def test_recipe_steps_and_catalog_effects(self):
        layers, species, xs = self.example_inputs()
        _, out = run("compute", "--layers", layers, "--species", species, "--xs", xs)
        steps = out["recipe_steps"]
        effects = {e for s in steps for e in s["effect_keys"]}
        self.assertEqual(effects, {"survival", "fragmentation_feeddown"})
        for s in steps:
            for key in s["effect_keys"].values():
                self.assertEqual(set(key), {"target_scope", "calibration_digest", "variation_id", "stage"})
                self.assertRegex(key["calibration_digest"], r"^[0-9a-f]{64}$")
        cat = json.loads((PLUGIN / "contracts" / "vocab" / "effects.json").read_text())
        ids = {e["effect_id"] for e in cat["effects"]}
        self.assertLessEqual({"survival", "fragmentation_feeddown"}, ids)

    def test_table_without_source_is_unvalidated(self):
        layers, species, xs = self.example_inputs(source=None)
        code, out = run("compute", "--layers", layers, "--species", species, "--xs", xs, "--status", "synthetic")
        self.assertEqual(code, 0)
        self.assertEqual(out["status_label"], "unvalidated")
        self.assertTrue(any("source" in w for w in out["warnings"]))

    def test_bad_inputs(self):
        layers, species, xs = self.example_inputs()
        missing = self.write("s2.json", {"species": [{"name": "nitrogen"}]})
        bad_frac = self.write("l2.json", {"layers": [{"name": "x", "grammage_g_cm2": 1.0, "composition": [
            {"target": "C", "A": 12.0, "mass_fraction": 0.5}]}]})
        for args in (("--layers", layers, "--species", missing, "--xs", xs),
                     ("--layers", bad_frac, "--species", species, "--xs", xs),
                     ("--layers", self.d / "nope.json", "--species", species, "--xs", xs)):
            with self.subTest(args=args):
                code, out = run("compute", *args)
                self.assertEqual(code, 2)
                self.assertEqual(out["status"], "rejected")


if __name__ == "__main__":
    unittest.main()
