"""Self-tests of the hep-authoring pilot tools (authoring-items/tools): salted gold commitments and the within-case
permutation test of the frozen pilot protocol. No model calls."""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1] / "authoring-items" / "tools"
sys.path.insert(0, str(TOOLS))
import permutation_test as pt  # noqa: E402


def run(*args) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, *map(str, args)], capture_output=True, text=True, check=False)


class GoldCommitments(unittest.TestCase):
    def test_commit_then_verify_and_detect_tampering(self):
        with tempfile.TemporaryDirectory() as tmp:
            t = Path(tmp)
            (t / "gold" / "c1").mkdir(parents=True)
            (t / "gold" / "c1" / "gold.json").write_text('{"items": []}')
            (t / "gold" / "c2.json").write_text("{}")
            self.assertEqual(run(TOOLS / "commit_gold.py", t / "gold", t / "nonces", t / "c.json").returncode, 0)
            doc = json.loads((t / "c.json").read_text())
            self.assertEqual(sorted(doc["commitments"]), ["c1/gold.json", "c2.json"])
            self.assertNotIn("nonce", (t / "c.json").read_text().lower().replace("sha256(nonce||gold)", ""))
            self.assertEqual(run(TOOLS / "verify_gold.py", t / "gold", t / "nonces", t / "c.json").returncode, 0)
            (t / "gold" / "c2.json").write_text('{"changed": true}')
            res = run(TOOLS / "verify_gold.py", t / "gold", t / "nonces", t / "c.json")
            self.assertEqual(res.returncode, 1)
            self.assertIn("FAIL c2.json", res.stdout)


class PermutationTest(unittest.TestCase):
    def test_full_separation_in_three_cases_is_the_smallest_p(self):
        cases = {c: {"baseline": [1, 2, 3], "candidate": [7, 8, 9]} for c in ("a", "b", "c")}
        r = pt.analyse(cases)
        self.assertEqual(r["n_assignments"], 8000)
        self.assertAlmostEqual(r["p_candidate_better"], 1 / 8000)
        self.assertTrue(r["leave_one_out_up"]["positive"])

    def test_identical_versions_give_no_evidence(self):
        cases = {c: {"baseline": [12, 12, 12], "candidate": [12, 12, 12]} for c in ("a", "b", "c")}
        r = pt.analyse(cases)
        self.assertEqual(r["T"], 0)
        self.assertEqual(r["p_candidate_better"], 1.0)
        self.assertFalse(r["leave_one_out_up"]["positive"])

    def test_p_value_matches_brute_force_for_one_case(self):
        import itertools
        base, cand = [3, 5, 4], [6, 4, 7]
        pool = base + cand
        obs = sum(cand) - sum(base)
        stats = [2 * sum(pool[i] for i in idx) - sum(pool) for idx in itertools.combinations(range(6), 3)]
        expected = sum(s >= obs for s in stats) / len(stats)
        self.assertAlmostEqual(pt.analyse({"x": {"baseline": base, "candidate": cand}})["p_candidate_better"], expected)


if __name__ == "__main__":
    unittest.main()
