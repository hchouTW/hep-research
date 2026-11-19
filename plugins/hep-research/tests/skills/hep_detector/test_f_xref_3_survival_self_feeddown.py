"""F-XREF-3, CHK-AU-02-06 (S2): survival_feeddown.py refuses a fragmentation fraction from a species into itself.

The script's docstring and nuclear-interactions-in-detector-material.md define feed-down as fragmentation into a
lighter species; before the fix compute() accepted {"C": {"C": f}}, exited 0 with status ok, and reported feed-down
events from C into C with a subtract_background recipe step (a wrong verdict). The tool has no charges, so the rule it
can apply is that the two species differ.

Oracle (kind exhaustive, basis exhaustive): every ordered pair (heavy, light) of the stated finite domain
{B, C, N} x {B, C, N} (9 pairs), each in its own run. The expected verdict of every pair is written by hand from that
rule, never taken from the tool's output: refused (exit 2, status rejected, no feeddown and no recipe step) exactly
when heavy == light; computed (exit 0, one feed-down entry heavy -> light, one subtract_background step for
species:light) otherwise. The test does not import the module under test; it runs the script as a subprocess and reads
only keys the parent already writes (status, error, feeddown, recipe_steps).

Tolerances: none. Every comparison is exact (exit codes, status strings, species pairs, step operators and target
scopes); no floating-point value is compared, so no tolerance is needed or may be added later.

Negative control: a real pair (C -> B) of the same table is still computed. All inputs are SYNTHETIC (the example
assets of the skill, plus an invented N row of cross sections for the third species).
"""
import itertools
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[3]
SCRIPT = PLUGIN / "skills" / "hep-detector" / "scripts" / "survival_feeddown.py"
ASSETS = PLUGIN / "skills" / "hep-detector" / "assets"
DOMAIN = ("B", "C", "N")
# SYNTHETIC: invented round-number cross sections (mb) for the third species of the exhaustive domain.
N_INELASTIC_MB = {"C": 300.0, "H": 240.0, "Al": 490.0}


def run(*args):
    p = subprocess.run([sys.executable, "-B", str(SCRIPT), *map(str, args)], capture_output=True, text=True,
                       timeout=600)
    return p.returncode, (json.loads(p.stdout) if p.stdout.strip().startswith("{") else p.stdout)


class SelfFeeddown(unittest.TestCase):
    def setUp(self):
        self.workdir = tempfile.TemporaryDirectory()
        self.d = Path(self.workdir.name)
        self.species = self.d / "s.json"
        self.species.write_text(json.dumps({"species": [{"name": "B"}, {"name": "C", "arriving": 1000}]}),
                                encoding="utf-8")

    def tearDown(self):
        self.workdir.cleanup()

    def xs_with(self, fractions, extra_inelastic=None):
        xs = json.loads((ASSETS / "survival-xs.example.json").read_text(encoding="utf-8"))
        xs["inelastic"].update(extra_inelastic or {})
        xs["fragmentation_fraction"] = fractions
        path = self.d / "x.json"
        path.write_text(json.dumps(xs), encoding="utf-8")
        return path

    def test_a_species_feeding_into_itself_is_refused(self):
        code, out = run("compute", "--layers", ASSETS / "survival-layers.example.json", "--species", self.species,
                        "--xs", self.xs_with({"C": {"C": 0.5}}))
        self.assertEqual(code, 2, out)
        self.assertEqual(out["status"], "rejected")
        self.assertIn("itself", out["error"])
        self.assertNotIn("feeddown", out)

    def test_exhaustive_every_ordered_pair_refused_exactly_when_the_species_are_the_same(self):
        species = self.d / "s3.json"
        species.write_text(json.dumps({"species": [{"name": s, "arriving": 1000} for s in DOMAIN]}),
                           encoding="utf-8")
        for heavy, light in itertools.product(DOMAIN, DOMAIN):
            with self.subTest(heavy=heavy, light=light):
                xs = self.xs_with({heavy: {light: 0.5}}, {"N": N_INELASTIC_MB})
                code, out = run("compute", "--layers", ASSETS / "survival-layers.example.json", "--species", species,
                                "--xs", xs)
                self.assertIsInstance(out, dict, out)
                if heavy == light:
                    self.assertEqual(code, 2, out)
                    self.assertEqual(out["status"], "rejected")
                    self.assertNotIn("feeddown", out)
                    self.assertNotIn("recipe_steps", out)
                else:
                    self.assertEqual(code, 0, out)
                    self.assertEqual(out["status"], "ok")
                    self.assertEqual([(f["from"], f["to"]) for f in out["feeddown"]], [(heavy, light)])
                    subtract = [s for s in out["recipe_steps"] if s["operator"] == "subtract_background"]
                    self.assertEqual(len(subtract), 1, subtract)
                    self.assertEqual(subtract[0]["effect_keys"]["fragmentation_feeddown"]["target_scope"],
                                     f"species:{light}")

    def test_negative_control_a_lighter_species_is_still_computed(self):
        code, out = run("compute", "--layers", ASSETS / "survival-layers.example.json", "--species", self.species,
                        "--xs", self.xs_with({"C": {"B": 0.12}}))
        self.assertEqual(code, 0, out)
        self.assertEqual([(f["from"], f["to"]) for f in out["feeddown"]], [("C", "B")])


if __name__ == "__main__":
    unittest.main()
