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


def _number(x):
    if isinstance(x, bool):
        return None
    if isinstance(x, (int, float)):
        return float(x)
    if isinstance(x, str):
        try:
            return float(x.rstrip(",;.)").lstrip("("))
        except ValueError:
            return None
    return None


def differences(a, b, written: set, path="$", sibling=None) -> list[str]:
    """Where a replayed JSON value a and the committed b differ beyond spec A.4.3 (numbers within relative 1e-9; a
    sha256 may differ when its sibling path or ref names a file the replay writes)."""
    if isinstance(a, dict) and isinstance(b, dict):
        if set(a) != set(b):
            return [f"{path}: keys {sorted(set(a) ^ set(b))}"]
        ref = next((a.get(k) for k in ("path", "ref") if isinstance(a.get(k), str)), None)
        return [d for k in a for d in differences(a[k], b[k], written, f"{path}.{k}", ref if k == "sha256" else None)]
    if isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            return [f"{path}: length {len(a)} != {len(b)}"]
        return [d for i, (x, y) in enumerate(zip(a, b)) for d in differences(x, y, written, f"{path}[{i}]")]
    if a == b:
        return []
    x, y = _number(a), _number(b)
    if x is not None and y is not None and abs(x - y) <= 1e-9 * max(abs(x), abs(y), 1e-300):
        return []
    if isinstance(a, str) and isinstance(b, str) and len(a) == len(b) == 64 and sibling is not None and any(
            sibling.endswith(w) for w in written):
        return []
    return [f"{path}: {a!r} != {b!r}"]


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

    def test_reproduces_the_committed_output(self):
        """Replay reproducibility of the Geant4 program (spec A.4.3): decisions, labels and every string identical,
        numbers within relative 1e-9 (the batch-means statistics go through lgamma and the incomplete beta, whose last
        bits differ between C libraries). A sha256 may differ only where it hashes a file the replay itself writes
        (that file is compared here under the same rule); hashes of inputs must match. Non-JSON files byte for byte."""
        committed = EXAMPLE / "output"
        files = sorted(p.relative_to(committed) for p in committed.rglob("*") if p.is_file())
        self.assertEqual(files, sorted(p.relative_to(self.out) for p in self.out.rglob("*") if p.is_file()))
        written = {str(rel) for rel in files}
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
                    self.assertEqual(differences(a, b, written), [])
                elif rel.suffix != ".md":
                    self.assertEqual(new, old)
                else:  # the report prints rounded numbers: compare it after rounding to 1e-9 relative
                    self.assertEqual(differences(new.decode().split(), old.decode().split(), written), [])

    def test_only_the_reissued_study_records_are_validated_in_scope(self):
        upgraded = set()
        for f in (self.out / "artifacts").rglob("*.json"):
            doc = json.loads(f.read_text(encoding="utf-8"))
            with self.subTest(artifact=f.name):
                if "validated-in-scope" in doc["status"]:
                    upgraded.add(f.name)
                    self.assertEqual(doc["status"], ["validated-in-scope"])
                    self.assertIn("core:evidence-records", doc["required_capabilities"])
                elif doc["artifact_type"] in ("computational-run", "response"):
                    self.assertIn("unvalidated", doc["status"])  # run records, scenarios, response
        self.assertEqual(upgraded, {"mpv.study-validated.computational-run.json",
                                    "sp.study-validated.computational-run.json"})
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
