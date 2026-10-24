"""Geant4 program A1.5: adapters/geant4/assets/summary_from_csv.py, the Python producer of simulation-summary/1 from
layered_sim per-event CSVs (SYNTHETIC CSVs; expected values are direct sums over the written events)."""
import gzip
import json
import math
import random
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[2]
SCRIPT = PLUGIN / "adapters" / "geant4" / "assets" / "summary_from_csv.py"
OBS = [{"name": "dep", "source_column": "edep_Si_MeV", "bins": {"lo": 0.0, "hi": 0.5, "width": 0.01},
        "thresholds": [0.25]},
       {"name": "loss", "source_column": "primary_eloss_MeV", "bins": {"lo": 0.0, "hi": 0.5, "width": 0.01},
        "selection": [{"column": "primary_fate", "op": "==", "value": 1},
                      {"column": "primary_end_process", "op": "==", "value": "Transportation"}]}]


class Producer(unittest.TestCase):
    def setUp(self):
        self._t = tempfile.TemporaryDirectory()
        self.d = Path(self._t.name)
        (self.d / "obs.json").write_text(json.dumps(OBS))
        self.record()

    def tearDown(self):
        self._t.cleanup()

    def record(self, ui=()):
        (self.d / "run.json").write_text(json.dumps({"artifact_id": "r", "extension": {
            "simulation": {"spec_sha256": "0" * 64, "ui_commands": list(ui)}}}))

    def csv(self, name, first, n, weight=None, seed=1, gz=False):
        rng = random.Random(seed)
        cols = ["event", "primary_eloss_MeV", "edep_Si_MeV", "primary_fate", "primary_end_process"]
        cols += ["weight"] if weight is not None else []
        rows = []
        for i in range(first, first + n):
            loss = rng.uniform(0.0, 0.6)
            fate = rng.choice([0, 1])
            proc = rng.choice(["Transportation", "muIoni"])
            rows.append([i, loss, 0.9 * loss, fate, proc] + ([weight] if weight is not None else []))
        text = "# SIMULATION\n" + ",".join(cols) + "\n" + "".join(",".join(map(str, r)) + "\n" for r in rows)
        p = self.d / (name + (".csv.gz" if gz else ".csv"))
        p.write_bytes(gzip.compress(text.encode(), mtime=0)) if gz else p.write_text(text)
        return p, rows

    def run_(self, *csvs, B=10, K=8, extra=()):
        args = [a for c in csvs for a in ("--csv", c)]
        p = subprocess.run([sys.executable, "-B", str(SCRIPT), *map(str, args), "--observables", self.d / "obs.json",
                            "--block-size", str(B), "--blocks", str(K), "--run-record", self.d / "run.json",
                            "--out", self.d / "s.json", *extra], capture_output=True, text=True, timeout=120)
        return p.returncode, json.loads(p.stdout)

    def test_blocks_selection_and_overflow(self):
        path, rows = self.csv("a", 0, 85, gz=True)
        code, out = self.run_(path)
        self.assertEqual((code, out["events_in_blocks"], out["events_ignored"]), (0, 80, 5), out)
        s = json.loads((self.d / "s.json").read_text())
        dep, loss = s["observables"]
        for b in range(8):
            mine = [r for r in rows if r[0] // 10 == b]
            kept = [r for r in mine if r[3] == 1 and r[4] == "Transportation"]
            self.assertEqual(loss["blocks"][b]["n"], len(kept))
            self.assertAlmostEqual(loss["blocks"][b]["sum"], math.fsum(r[1] for r in kept), places=12)
            self.assertEqual(dep["blocks"][b]["overflow"], sum(0.9 * r[1] >= 0.5 for r in mine))
            self.assertEqual(dep["blocks"][b]["count_if"], [sum(0.9 * r[1] > 0.25 for r in mine)])
        self.assertEqual(s["run"]["weight_column"], "absent")

    def test_two_jobs_merge_by_block(self):
        a, rows_a = self.csv("a", 0, 37, seed=1)
        b, rows_b = self.csv("b", 37, 43, seed=2)
        code, _ = self.run_(a, b)
        s = json.loads((self.d / "s.json").read_text())
        rows = rows_a + rows_b
        for blk in s["observables"][0]["blocks"]:
            mine = [r for r in rows if r[0] // 10 == blk["block"]]
            self.assertEqual(blk["events"], len(mine))
            self.assertAlmostEqual(blk["sum"], math.fsum(0.9 * r[1] for r in mine), places=12)

    def test_weights_other_than_one_or_biasing_without_weights_are_refused(self):
        path, _ = self.csv("w", 0, 80, weight=0.5)
        self.assertEqual(self.run_(path)[0], 2)
        path, _ = self.csv("w1", 0, 80, weight=1.0)
        code, _ = self.run_(path)
        self.assertEqual(code, 0)
        self.assertEqual(json.loads((self.d / "s.json").read_text())["run"]["weight_column"], "unit")
        self.record(ui=["/process/em/setSecBiasing eBrem SiRegion 10 1 MeV"])
        path, _ = self.csv("nb", 0, 80)
        self.assertEqual(self.run_(path)[0], 2)

    def test_unknown_column_and_bad_declaration(self):
        path, _ = self.csv("a", 0, 80)
        (self.d / "obs.json").write_text(json.dumps([dict(OBS[0], source_column="nope")]))
        self.assertEqual(self.run_(path)[0], 2)
        (self.d / "obs.json").write_text(json.dumps([{"name": "x", "source_column": "edep_Si_MeV"}]))
        self.assertEqual(self.run_(path)[0], 2)


if __name__ == "__main__":
    unittest.main()
