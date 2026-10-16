"""F-07: merge semantics. Undeclared numeric keys keep summing (existing callers and committed example outputs do not
change), a key whose name marks a non-additive quantity (seed, median, mean, quantile, min, max, rate, fraction) is
refused unless declared, and a declared rule (sum, min, max, first, concat) is applied. Before the fix the engine
summed the seeds and medians of the chunks."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from core.partition import engine

ROOT = Path(__file__).resolve().parents[2]
CLI = ROOT / "skills" / "hep-computing" / "scripts" / "local_partition.py"


def worker(chunk):
    n = chunk["stop"] - chunk["start"]
    return {"n_events": n, "seed": chunk["seed"], "median_pt": 10.0 + chunk["start"], "hist": [1, n],
            "event_ids": list(range(chunk["start"], chunk["stop"]))}


class MergeRules(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.state = Path(self.tmp.name) / "state"
        self.manifest = engine.make_manifest("f07", 6, 2, 11)
        self.assertTrue(engine.run(self.manifest, self.state, worker)["complete"])

    def test_undeclared_non_additive_keys_are_refused(self):
        res = engine.merge(self.manifest, self.state)
        self.assertEqual(res["status"], "incomplete", res)
        self.assertIsNone(res["merged"])
        refused = [p for p in res["problems"] if p["code"] == "merge.undeclared_non_additive"]
        self.assertEqual(sorted(refused[0]["keys"]), ["median_pt", "seed"])

    def test_declared_rules_are_applied(self):
        rules = {"seed": "first", "median_pt": "max", "event_ids": "concat"}
        res = engine.merge(self.manifest, self.state, rules=rules)
        self.assertEqual(res["status"], "complete", res)
        seeds = [c["seed"] for c in self.manifest["chunks"]]
        self.assertEqual(res["merged"], {"n_events": 6, "seed": seeds[0], "median_pt": 14.0, "hist": [3, 6],
                                         "event_ids": list(range(6))})
        self.assertEqual(res["merge_rules"], rules)
        res = engine.merge(self.manifest, self.state, rules={"seed": "min", "median_pt": "min", "event_ids": "sum"})
        self.assertEqual((res["merged"]["seed"], res["merged"]["median_pt"]), (min(seeds), 10.0))

    def test_undeclared_additive_keys_still_sum(self):
        manifest = engine.make_manifest("f07-additive", 4, 2, 3)
        state = Path(self.tmp.name) / "additive"
        engine.run(manifest, state, lambda c: {"n": c["stop"] - c["start"], "sumw": [0.5, 1.0]})
        res = engine.merge(manifest, state)
        self.assertEqual((res["status"], res["merged"]), ("complete", {"n": 4, "sumw": [1.0, 2.0]}))

    def test_bad_rules_are_refused(self):
        with self.assertRaises(engine.PartitionError):          # an unknown rule is bad input
            engine.merge(self.manifest, self.state, rules={"seed": "average", "median_pt": "max"})
        res = engine.merge(self.manifest, self.state,              # concat of numbers: no merged value
                           rules={"seed": "first", "median_pt": "max", "n_events": "concat"})
        self.assertEqual(res["status"], "incomplete", res)
        self.assertIsNone(res["merged"])

    def test_cli_rule_flag(self):
        mf = Path(self.tmp.name) / "manifest.json"
        mf.write_text(json.dumps(self.manifest))
        base = [sys.executable, "-I", str(CLI), "merge", "--manifest", str(mf), "--state", str(self.state)]
        refused = subprocess.run(base, capture_output=True, text=True, timeout=120)
        self.assertEqual(refused.returncode, 1, refused.stdout)
        ok = subprocess.run(base + ["--rule", "seed=first", "--rule", "median_pt=max", "--rule", "event_ids=concat"],
                            capture_output=True, text=True, timeout=120)
        self.assertEqual(ok.returncode, 0, ok.stdout + ok.stderr)
        self.assertEqual(json.loads(ok.stdout)["merged"]["n_events"], 6)
        bad = subprocess.run(base + ["--rule", "seed"], capture_output=True, text=True, timeout=120)
        self.assertEqual(bad.returncode, 2, bad.stdout)


if __name__ == "__main__":
    unittest.main()
