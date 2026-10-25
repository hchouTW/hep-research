"""J16 (Geant4 program C3): examples/design-search-j16/run.py replays the automated candidate generation on Examples A
and B from the committed design artifacts and the recorded Example A confirmation; every pre-declared criterion holds
and the derived results equal the committed output/results.json (floats within 1e-9 relative, Geant4 program A.4.3).
The search is deterministic (seeded NSGA-II, standard library), so its finalists and their evaluations reproduce."""
import contextlib
import importlib.util
import io
import json
import math
import tempfile
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[2]
HERE = PLUGIN / "examples" / "design-search-j16"


def differences(a, b, path="$"):
    if isinstance(a, dict) and isinstance(b, dict):
        out = [f"{path}: keys {sorted(set(a) ^ set(b))}"] if set(a) != set(b) else []
        return out + [d for k in set(a) & set(b) for d in differences(a[k], b[k], f"{path}.{k}")]
    if isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            return [f"{path}: length {len(a)} != {len(b)}"]
        return [d for i, (x, y) in enumerate(zip(a, b)) for d in differences(x, y, f"{path}[{i}]")]
    if isinstance(a, float) and isinstance(b, (int, float)) and not isinstance(b, bool):
        return [] if math.isclose(a, b, rel_tol=1e-9, abs_tol=1e-12) else [f"{path}: {a!r} != {b!r}"]
    return [] if a == b else [f"{path}: {a!r} != {b!r}"]


class J16Replay(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location("j16_run_test", HERE / "run.py")
        cls.mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.mod)
        cls.tmp = tempfile.TemporaryDirectory()
        with contextlib.redirect_stdout(io.StringIO()):
            cls.code = cls.mod.main(["--out", cls.tmp.name])
        cls.out = Path(cls.tmp.name)
        cls.r = json.loads((cls.out / "results.json").read_text(encoding="utf-8"))

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_criteria(self):
        self.assertEqual(self.code, 0, self.r["pass"])
        self.assertTrue(all(self.r["pass"].values()), self.r["pass"])

    def test_reproduces_the_committed_results(self):
        want = json.loads((HERE / "output" / "results.json").read_text(encoding="utf-8"))
        got = json.loads(json.dumps(self.r))
        for doc in (want, got):
            for ex in ("A", "B"):
                doc[ex].pop("report", None)  # the report's path names the output folder
        self.assertEqual(differences(got, want), [])

    def test_confirmation_runs_on_seeds_the_search_never_used(self):
        art = self.out / "A" / "artifacts"
        summ = json.loads((art / "runs" / "SEARCH-J16A.computational-run.json").read_text())["extension"][
            "search_summary"]
        conf = self.r["A"]["confirmation"]
        study = json.loads((art / "studies" / conf["study"] / "study.computational-run.json").read_text())
        self.assertEqual(summ["seeds"]["geant4_search"], [])
        self.assertEqual(conf["candidate"], f"ams-like-v1:cand-F{summ['finalists'][0]['index']}")
        # recorded as it came out: the reference's -13 % control shifted beyond 1.1 DL, so the upgrade is refused,
        # the study stays unvalidated and its F4 evaluation decides nothing (fidelity.insufficient)
        if conf["upgrade"] == "re-issued as validated-in-scope":
            self.assertEqual(study["status"], ["validated-in-scope"])
        else:
            self.assertIn("unvalidated", study["status"])
            self.assertTrue(conf["gaps"])
            row = self.r["A"]["rows"][f"REQ-TRK-001 {conf['candidate'].split(':')[1]}"]
            self.assertIn("fidelity.insufficient", row["codes"])

    def test_reply_facts(self):
        """C3.4: the reply states the search size and the confirmation status; the report carries screening, the
        comparison basis and the ranking or its refusal."""
        for ex in ("A", "B"):
            s = self.r[ex]["search"]
            self.assertGreater(s["distinct_designs"], 0)
            self.assertGreater(s["topologies"], 1)
            self.assertIn(self.r[ex]["ranking"]["status"], ("refused", "ranked"))
            self.assertIn("holds", self.r[ex]["comparison_basis"])


if __name__ == "__main__":
    unittest.main()
