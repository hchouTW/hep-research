"""Journey J14 (examples/geant4-thin-silicon): Geant4 study of energy loss in 300 um of silicon with independent-
reference benchmarks. The offline replay (no Geant4) must reproduce the committed output/ byte for byte, pass every
pre-declared criterion, keep every artifact unvalidated (phase 1), validate as contract artifacts, and list the gaps of
each negative-control scenario. With HEP_GEANT4_LIVE_TEST=1 and HEP_GEANT4_CONFIG the live run is repeated into a
temporary recorded folder and must give the same verdicts. Standard library only."""
import contextlib
import importlib.util
import io
import json
import os
import tempfile
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[2]
EXAMPLE = PLUGIN / "examples" / "geant4-thin-silicon"


def load():
    spec = importlib.util.spec_from_file_location("geant4_thin_silicon_run", EXAMPLE / "run.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class J14Replay(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = load()
        cls.tmp = tempfile.TemporaryDirectory()
        cls.out = Path(cls.tmp.name) / "output"
        with contextlib.redirect_stdout(io.StringIO()):
            cls.code = cls.mod.main(["--out", str(cls.out)])
        cls.r = json.loads((cls.out / "results.json").read_text(encoding="utf-8"))

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_all_criteria_pass(self):
        self.assertEqual(self.code, 0, self.r["pass"])
        self.assertTrue(all(self.r["pass"].values()), self.r["pass"])

    def test_reproduces_the_committed_output_byte_for_byte(self):
        committed = EXAMPLE / "output"
        files = sorted(p.relative_to(committed) for p in committed.rglob("*") if p.is_file())
        self.assertEqual(files, sorted(p.relative_to(self.out) for p in self.out.rglob("*") if p.is_file()))
        for rel in files:
            with self.subTest(file=str(rel)):
                new, old = (self.out / rel).read_bytes(), (committed / rel).read_bytes()
                if rel.suffix == ".json" and new != old:
                    # versions.plugin_release is the code identity of the checkout (contracts/identity.py): it reads
                    # "unreleased" until a release manifest matches the tree, so it cannot be committed byte for byte
                    a, b = json.loads(new), json.loads(old)
                    for doc in (a, b):
                        if isinstance(doc, dict) and isinstance(doc.get("versions"), dict):
                            doc["versions"].pop("plugin_release", None)
                    self.assertEqual(a, b)
                else:
                    self.assertEqual(new, old)

    def test_every_artifact_is_unvalidated_and_none_upgraded(self):
        for f in (self.out / "artifacts").rglob("*.json"):
            doc = json.loads(f.read_text(encoding="utf-8"))
            with self.subTest(artifact=f.name):
                self.assertNotIn("validated-in-scope", doc["status"])
                if doc["artifact_type"] in ("computational-run", "response"):
                    self.assertIn("unvalidated", doc["status"])
        self.assertIn("ILLUSTRATIVE", self.r["label"])
        self.assertIn("Simulation", (self.out / "report.md").read_text(encoding="utf-8"))

    def test_study_records_embed_benchmarks_convergence_and_scope(self):
        for study in ("mpv", "sp"):
            doc = json.loads((self.out / "artifacts" / f"{study}.study.computational-run.json").read_text("utf-8"))
            st = doc["extension"]["study"]
            self.assertTrue(st["benchmarks"] and st["convergence"]["gate"] == "pass" and st["declared_scope"])
            ref = [b for b in st["benchmarks"] if b["grade"] == "reference"]
            self.assertTrue(all(b["validation_evidence"] and "detection_limit_relative" in b["scope"] for b in ref))

    def test_negative_control_scenarios_list_their_gaps(self):
        sc = self.r["scenarios"]
        self.assertTrue(any("convergence gate not passed" in g for g in sc["coarse-cut"]))
        self.assertTrue(any(g.startswith("stopping-power failed") for g in sc["density-10"]))
        self.assertTrue(any("Geant4 material dump" in g for g in sc["dump-reference"]))

    def test_no_private_paths(self):
        for f in list((EXAMPLE / "recorded").rglob("*.json")) + list(self.out.rglob("*.json")):
            text = f.read_text(encoding="utf-8")
            with self.subTest(file=f.name):
                self.assertNotIn("/" + "Users/", text)  # split: the packaging scan reads this file
                self.assertNotIn("/home/", text)


@unittest.skipUnless(os.environ.get("HEP_GEANT4_LIVE_TEST") == "1" and os.environ.get("HEP_GEANT4_CONFIG"),
                     "set HEP_GEANT4_LIVE_TEST=1 and HEP_GEANT4_CONFIG to rerun J14 with Geant4")
class J14Live(unittest.TestCase):
    def test_live_run_gives_the_recorded_verdicts(self):
        mod = load()
        with tempfile.TemporaryDirectory() as tmp:
            t = Path(tmp)
            with contextlib.redirect_stdout(io.StringIO()):
                code = mod.main(["--live", "--work", str(t / "work"), "--recorded", str(t / "recorded"),
                                 "--out", str(t / "output")])
            live = json.loads((t / "output" / "results.json").read_text(encoding="utf-8"))
        committed = json.loads((EXAMPLE / "output" / "results.json").read_text(encoding="utf-8"))
        self.assertEqual(code, 0)
        self.assertEqual(live["pass"], committed["pass"])
        for s in ("mpv", "sp"):
            self.assertEqual({k: v["verdict"] for k, v in live["studies"][s]["benchmarks"].items()},
                             {k: v["verdict"] for k, v in committed["studies"][s]["benchmarks"].items()})


if __name__ == "__main__":
    unittest.main()
