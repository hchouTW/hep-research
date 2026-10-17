"""Tests for ML2: stratified grouped splits and composite group keys in make_grouped_splits.py, and the per-stratum
coverage report of check_split_integrity.py.

Oracles: after stratification no group spans two splits (the checker passes with --strict); every stratum with enough
groups reaches every split; a stratum with fewer groups than splits is listed, not hidden; a composite key
(run, lumi block) keeps each (run, lumi) pair whole while letting one run span splits."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tests.skills.hep_ml.test_make_grouped_splits import CHECKER, mgs, run_cli, split_of


def stratified_rows():
    """Runs of signal or background events: 12 signal runs, 18 background runs, 2 'rare' runs (too few for 3 splits)."""
    rows = []
    for run in range(32):
        label = "sig" if run < 12 else ("bkg" if run < 30 else "rare")
        rows += [{"event": f"r{run}_{i}", "run": run, "label": label} for i in range(5)]
    return rows


def check_manifest(manifest, *extra):
    with tempfile.TemporaryDirectory() as td:
        path = Path(td) / "splits.json"
        path.write_text(json.dumps(manifest), encoding="utf-8")
        res = subprocess.run([sys.executable, "-I", str(CHECKER), "--json", *extra, str(path)],
                             capture_output=True, text=True, timeout=600)
    return res.returncode, json.loads(res.stdout)


class StratifiedSplitTests(unittest.TestCase):
    def test_stratified_split_has_no_leakage_and_every_large_stratum_reaches_every_split(self):
        code, summary, manifest, check = run_cli(stratified_rows(), "--id-column", "event", "--group-column", "run",
                                                 "--stratify-column", "label", "--seed", "3")
        self.assertEqual(code, 0, summary)
        self.assertEqual(check[0], 0, check[1])  # --strict pass: no group leakage after stratification
        self.assertEqual(check[1]["group_leakage"], {})
        where = split_of(manifest, ("train", "val", "test"))
        for label in ("sig", "bkg"):
            reached = {where[r["event"]] for r in stratified_rows() if r["label"] == label}
            self.assertEqual(reached, {"train", "val", "test"}, label)
        self.assertEqual(summary["stratify_column"], "label")
        self.assertEqual(summary["strata"]["sig"]["groups"], 12)
        self.assertEqual(summary["strata_too_few_groups"], ["rare"])
        self.assertEqual(manifest["strata"]["r0_0"], "sig")

    def test_stratified_split_is_deterministic_for_a_seed(self):
        args = ("--id-column", "event", "--group-column", "run", "--stratify-column", "label", "--seed", "11")
        self.assertEqual(run_cli(stratified_rows(), *args)[2], run_cli(stratified_rows(), *args)[2])

    def test_stratified_folds_are_disjoint_and_cover_each_stratum(self):
        code, summary, manifest, check = run_cli(stratified_rows(), "--id-column", "event", "--group-column", "run",
                                                 "--stratify-column", "label", "--folds", "3")
        self.assertEqual(code, 0, summary)
        self.assertEqual(check[0], 0, check[1])
        self.assertEqual(summary["strata"]["bkg"]["splits"], {"fold0": 30, "fold1": 30, "fold2": 30})

    def test_stratify_with_temporal_mode_is_refused(self):
        rows = [dict(r, time=i) for i, r in enumerate(stratified_rows())]
        code, report, _, _ = run_cli(rows, "--id-column", "event", "--group-column", "run", "--stratify-column",
                                     "label", "--mode", "temporal", "--time-column", "time")
        self.assertEqual(code, 2)
        self.assertEqual(report["status"], "rejected")

    def test_missing_stratum_value_is_refused(self):
        rows = stratified_rows()
        rows[0]["label"] = ""
        code, report, _, _ = run_cli(rows, "--id-column", "event", "--group-column", "run",
                                     "--stratify-column", "label")
        self.assertEqual(code, 2)
        self.assertIn("stratum", report["error"])

    def test_group_with_mixed_strata_is_reported(self):
        rows = stratified_rows()
        rows[0]["label"] = "bkg"  # run 0 now holds 4 sig and 1 bkg event: its stratum is the majority, sig
        code, summary, manifest, _ = run_cli(rows, "--id-column", "event", "--group-column", "run",
                                             "--stratify-column", "label")
        self.assertEqual(code, 0, summary)
        self.assertEqual(summary["mixed_stratum_groups"], ["0"])
        self.assertEqual(manifest["strata"]["r0_0"], "bkg")  # per-row stratum is kept as given


class CompositeKeyTests(unittest.TestCase):
    def rows(self):
        return [{"event": f"r{run}_l{lumi}_{i}", "run": run, "lumi": lumi}
                for run in range(3) for lumi in range(6) for i in range(4)]

    def test_composite_key_keeps_each_pair_whole(self):
        code, summary, manifest, check = run_cli(self.rows(), "--id-column", "event", "--group-column", "run",
                                                 "lumi", "--seed", "2")
        self.assertEqual(code, 0, summary)
        self.assertEqual(check[0], 0, check[1])
        self.assertEqual(summary["group_column"], ["run", "lumi"])
        self.assertEqual(summary["groups"], 18)
        where = split_of(manifest, ("train", "val", "test"))
        pairs = {}
        for row in self.rows():
            pairs.setdefault((row["run"], row["lumi"]), set()).add(where[row["event"]])
        self.assertTrue(all(len(s) == 1 for s in pairs.values()))
        runs = {}
        for row in self.rows():
            runs.setdefault(row["run"], set()).add(where[row["event"]])
        self.assertTrue(any(len(s) > 1 for s in runs.values()))  # a coarser key would have kept runs whole

    def test_composite_key_parts_do_not_collide(self):
        rows = [{"event": "a", "x": "1|2", "y": "3"}, {"event": "b", "x": "1", "y": "2|3"},
                {"event": "c", "x": "4", "y": "5"}]
        groups, _, _, _ = mgs.collect_groups(rows, "event", ["x", "y"])
        self.assertEqual(len(groups), 3)

    def test_single_group_column_keeps_its_plain_key(self):
        code, summary, manifest, _ = run_cli(self.rows(), "--id-column", "event", "--group-column", "run",
                                             "--fractions", "0.34", "0.33", "0.33")
        self.assertEqual(code, 0, summary)
        self.assertEqual(summary["group_column"], "run")
        self.assertEqual(manifest["groups"]["r0_l0_0"], "0")


class StratumCoverageReportTests(unittest.TestCase):
    def test_checker_reports_coverage_of_each_stratum(self):
        manifest = {"train": ["a", "b", "c"], "val": ["d"], "test": ["e"],
                    "groups": {"a": 1, "b": 2, "c": 3, "d": 4, "e": 5},
                    "strata": {"a": "sig", "b": "bkg", "c": "bkg", "d": "bkg", "e": "bkg"}}
        code, report = check_manifest(manifest)
        self.assertEqual(code, 0, report)
        cov = report["stratum_coverage"]
        self.assertEqual(cov["strata"]["sig"]["splits"], {"train": 1, "val": 0, "test": 0})
        self.assertEqual(cov["strata"]["sig"]["missing_from"], ["test", "val"])
        self.assertEqual(cov["strata"]["bkg"]["missing_from"], [])
        self.assertEqual(cov["strata_missing_splits"], ["sig"])
        self.assertEqual(cov["ids_with_stratum"], 5)

    def test_strata_must_be_an_object(self):
        code, report = check_manifest({"train": ["a"], "test": ["b"], "strata": ["sig"]})
        self.assertEqual(code, 2)

    def test_no_strata_key_reports_none(self):
        code, report = check_manifest({"train": ["a"], "test": ["b"], "groups": {"a": 1, "b": 2}})
        self.assertEqual(code, 0)
        self.assertIsNone(report["stratum_coverage"])


if __name__ == "__main__":
    unittest.main()
