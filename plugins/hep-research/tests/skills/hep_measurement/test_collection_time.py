"""collection_time.py (M1): collection time per era, time bin and variable bin from declared periods. Oracles: a
hand-computed synthetic answer; T does not grow with the safety factor; a period split across files is counted once;
partial accumulation followed by merge equals a single run; overlaps, missing keys, periods crossing an era or
time-bin boundary, conflicting duplicates and a configuration without a required key are refused. All periods are
SYNTHETIC."""
import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[3]
SCRIPT = PLUGIN / "skills" / "hep-measurement" / "scripts" / "collection_time.py"

CONFIG = {
    "key": "period",
    "start_column": "start_s",
    "duration_column": "duration_s",
    "live_fraction_column": "live_fraction",
    "quality_cuts": [{"name": "in_saa", "column": "saa", "op": "==", "value": 0},
                     {"name": "bad_run", "column": "good", "op": "==", "value": 1}],
    "transmission": {"cutoff_column": "cutoff_gv", "safety_factors": [1.0, 1.2]},
    "x": {"variable": "rigidity", "unit": "GV", "edges": [1, 2, 4, 8, 16]},
    "time_edges": [0, 1000, 2000],
    "eras": [{"id": "e1", "start": 0, "end": 1000}, {"id": "e2", "start": 1000, "end": 2000}],
}
HEADER = "period,start_s,duration_s,live_fraction,cutoff_gv,saa,good\n"
ROWS = {
    "p1": "p1,0,100,0.9,1.5,0,1\n",
    "p2": "p2,100,200,0.5,3.5,0,1\n",
    "p3": "p3,300,50,1.0,1.0,1,1\n",     # in the SAA: removed
    "p4": "p4,400,100,0.8,1.0,0,0\n",    # bad run: removed
    "p5": "p5,1000,100,1.0,0.5,0,1\n",
}


def run(*args):
    p = subprocess.run([sys.executable, "-B", str(SCRIPT), *map(str, args)], capture_output=True, text=True,
                       timeout=600)
    out = json.loads(p.stdout) if p.stdout.strip().startswith("{") else p.stdout
    return p.returncode, out, p.stderr


class CollectionTime(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.d = Path(self.tmp.name)
        self.config = self.write_config(CONFIG)
        self.all = self.write("all.csv", "p1 p2 p3 p4 p5")

    def write_config(self, cfg, name="config.json"):
        p = self.d / name
        p.write_text(json.dumps(cfg), encoding="utf-8")
        return p

    def write(self, name, keys, extra=""):
        p = self.d / name
        p.write_text(HEADER + "".join(ROWS[k] for k in keys.split()) + extra, encoding="utf-8")
        return p

    def test_known_synthetic_answer(self):
        code, out, err = run("accumulate", "--config", self.config, self.all)
        self.assertEqual(code, 0, err)
        self.assertEqual(out["status"], "ok")
        self.assertEqual(out["status_label"], "unvalidated")
        ct = out["collection_time_s"]
        # p1: 100 s x 0.9 above 1.5 GV (sf 1.0) or 1.8 GV (sf 1.2): bins with low edge >= threshold: 2, 4, 8
        # p2: 200 s x 0.5 above 3.5 GV or 4.2 GV; p5: 100 s above 0.5 or 0.6 GV (every bin), era e2
        self.assertEqual(ct["e1"]["1.0"], [[0.0, 90.0, 190.0, 190.0], [0.0, 0.0, 0.0, 0.0]])
        self.assertEqual(ct["e1"]["1.2"], [[0.0, 90.0, 90.0, 190.0], [0.0, 0.0, 0.0, 0.0]])
        self.assertEqual(ct["e2"]["1.0"], [[0.0, 0.0, 0.0, 0.0], [100.0, 100.0, 100.0, 100.0]])
        self.assertEqual(out["livetime_s"], {"e1": [190.0, 0.0], "e2": [0.0, 100.0]})
        diag = out["diagnostics"]
        self.assertEqual((diag["periods_read"], diag["periods_unique"], diag["duplicates_removed"], diag["periods_kept"]),
                         (5, 5, 0, 3))
        self.assertEqual(diag["removed"], {"in_saa": 1, "bad_run": 1})
        norm = out["normalization"]
        self.assertEqual(norm["composition"], "exposure_acceptance_livetime_transmission")
        self.assertEqual(sorted(norm["effects_applied"]), ["cutoff_transmission", "livetime"])
        self.assertIn("collection time", out["naming"])

    def test_safety_factor_never_increases_t(self):
        cfg = copy.deepcopy(CONFIG)
        cfg["transmission"]["safety_factors"] = [1.0, 1.1, 1.3, 2.0, 4.0]
        code, out, err = run("accumulate", "--config", self.write_config(cfg, "c2.json"), self.all)
        self.assertEqual(code, 0, err)
        for era, by_sf in out["collection_time_s"].items():
            flat = [sum(sum(row) for row in by_sf[k]) for k in ("1.0", "1.1", "1.3", "2.0", "4.0")]
            self.assertEqual(flat, sorted(flat, reverse=True), era)
        e1 = out["collection_time_s"]["e1"]
        self.assertLess(sum(map(sum, e1["4.0"])), sum(map(sum, e1["1.0"])))

    def test_period_split_across_files_is_counted_once(self):
        a = self.write("a.csv", "p1 p2 p3")
        b = self.write("b.csv", "p3 p4 p5")  # p3 repeated identically
        code, single, _ = run("accumulate", "--config", self.config, self.all)
        code, split, err = run("accumulate", "--config", self.config, a, b)
        self.assertEqual(code, 0, err)
        self.assertEqual(split["collection_time_s"], single["collection_time_s"])
        self.assertEqual(split["diagnostics"]["duplicates_removed"], 1)

    def test_partial_then_merge_equals_a_single_run(self):
        a = self.write("a.csv", "p1 p2 p3")
        b = self.write("b.csv", "p3 p4 p5")
        code, single, _ = run("accumulate", "--config", self.config, a, b)
        pa, pb = self.d / "pa.json", self.d / "pb.json"
        for f, p in ((a, pa), (b, pb)):
            code, out, err = run("accumulate", "--config", self.config, f, "--emit-partial", p)
            self.assertEqual(code, 0, err)
            self.assertEqual(out["status"], "ok")
        code, merged, err = run("merge", "--config", self.config, pa, pb)
        self.assertEqual(code, 0, err)
        for key in ("collection_time_s", "livetime_s", "diagnostics"):
            self.assertEqual(json.dumps(merged[key], sort_keys=True), json.dumps(single[key], sort_keys=True), key)

    def test_partial_from_another_configuration_is_refused(self):
        cfg = copy.deepcopy(CONFIG)
        cfg["transmission"]["safety_factors"] = [1.5]
        pa, pb = self.d / "pa.json", self.d / "pb.json"
        run("accumulate", "--config", self.config, self.all, "--emit-partial", pa)
        run("accumulate", "--config", self.write_config(cfg, "other.json"), self.all, "--emit-partial", pb)
        code, out, _ = run("merge", "--config", self.config, pa, pb)
        self.assertEqual((code, out["status"]), (2, "rejected"))

    def test_refusals(self):
        cases = {
            "overlap": self.write("ov.csv", "p1 p2", "p6,50,10,1.0,1.0,0,1\n"),
            "conflict": self.write("cf.csv", "p1 p2", "p1,0,100,0.8,1.5,0,1\n"),
            "era crossing": self.write("era.csv", "p1", "p7,950,100,1.0,1.0,0,1\n"),
            "missing key": self.write("mk.csv", "p1", ",600,10,1.0,1.0,0,1\n"),
        }
        for what, path in cases.items():
            with self.subTest(what):
                code, out, _ = run("accumulate", "--config", self.config, path)
                self.assertEqual((code, out["status"]), (2, "rejected"), out)
        missing_col = self.d / "nocol.csv"
        missing_col.write_text("period,start_s,duration_s,live_fraction,saa,good\np1,0,100,0.9,0,1\n", encoding="utf-8")
        code, out, _ = run("accumulate", "--config", self.config, missing_col)
        self.assertEqual((code, out["status"]), (2, "rejected"))

    def test_time_bin_crossing_is_refused(self):
        cfg = copy.deepcopy(CONFIG)
        cfg["time_edges"] = [0, 150, 1000, 2000]
        code, out, _ = run("accumulate", "--config", self.write_config(cfg, "tb.json"), self.all)
        self.assertEqual((code, out["status"]), (2, "rejected"))
        self.assertIn("p2", json.dumps(out))

    def test_configuration_has_no_defaults_and_no_eval(self):
        for drop in ("transmission", "eras", "quality_cuts", "live_fraction_column"):
            cfg = {k: v for k, v in CONFIG.items() if k != drop}
            with self.subTest(drop=drop):
                code, out, _ = run("accumulate", "--config", self.write_config(cfg, f"no-{drop}.json"), self.all)
                self.assertEqual((code, out["status"]), (2, "rejected"))
        cfg = copy.deepcopy(CONFIG)
        cfg["quality_cuts"][0]["op"] = "__import__('os')"
        code, out, _ = run("accumulate", "--config", self.write_config(cfg, "evil.json"), self.all)
        self.assertEqual((code, out["status"]), (2, "rejected"))

    def test_missing_input_and_status_label(self):
        code, out, _ = run("accumulate", "--config", self.config, self.d / "nope.csv")
        self.assertEqual((code, out["status"]), (2, "rejected"))
        code, out, _ = run("accumulate", "--config", self.config, self.all, "--status", "synthetic")
        self.assertEqual((code, out["status_label"]), (0, "synthetic"))


if __name__ == "__main__":
    unittest.main()
