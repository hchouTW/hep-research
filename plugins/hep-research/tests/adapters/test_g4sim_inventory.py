"""The inventory table (g4sim S1, Section 7.4): the four classes, and the Section 15.1 negative tests: a run left unclassified, a
summary-only run marked as covering the column file, a reproduction check using a different seed."""
from __future__ import annotations

import hashlib
import importlib.util
import tempfile
import unittest
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("g4sim_inventory", ROOT / "adapters/geant4/assets/g4sim_inventory.py")
inventory = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(inventory)

COLUMNS = {"run/events.csv": "match", "run/log.txt": "missing"}
SUMMARY = {"run/events.csv": "missing", "run/summary.json": "match"}
NOTHING = {"run/events.csv": "different"}
GOOD = {"built": True, "reproduced": True, "probe_agrees": None, "field_visible": True, "seed_as_recorded": True}


class Classes(unittest.TestCase):
    def test_a_reproduced_run_with_its_output_is_t1_recorded(self):
        self.assertEqual(inventory.classify(COLUMNS, GOOD), {"class": "T1-recorded", "reason": "existing output reproduced",
                                                             "scope": ["columns"]})

    def test_a_summary_only_run_covers_the_summary_only(self):
        self.assertEqual(inventory.classify(SUMMARY, GOOD)["scope"], ["summary"])

    def test_a_regenerated_baseline_is_t1_regenerated(self):
        self.assertEqual(inventory.classify(NOTHING, {**GOOD, "regenerated": True})["class"], "T1-regenerated")

    def test_each_failure_makes_the_run_t2_with_its_reason(self):
        for change, words in (({"built": False}, "cannot be built"), ({"reproduced": False}, "reproduction check failed"),
                              ({"probe_agrees": False}, "disagrees"), ({"field_visible": False}, "GB22")):
            with self.subTest(change=change):
                result = inventory.classify(COLUMNS, {**GOOD, **change})
                self.assertEqual(result["class"], "T2")
                self.assertIn(words, result["reason"])

    def test_no_reference_and_no_baseline_is_not_regressable(self):
        self.assertEqual(inventory.classify(NOTHING, GOOD)["class"], "not-regressable")

    def test_a_different_seed_gives_no_class(self):
        self.assertIsNone(inventory.classify(COLUMNS, {**GOOD, "seed_as_recorded": False})["class"])

    def test_no_result_yet_is_never_t1(self):
        self.assertEqual(inventory.classify(COLUMNS, None)["class"], "T2")


class Table(unittest.TestCase):
    facts = [{"run": "a"}, {"run": "b"}]

    def row(self, run, cls="T1-recorded", scope=("columns",), states=None):
        return {"run": run, "class": cls, "scope": list(scope), "states": COLUMNS if states is None else states}

    def test_a_complete_table_has_no_problems(self):
        self.assertEqual(inventory.table_problems([self.row("a"), self.row("b")], self.facts), [])

    def test_a_run_left_out_is_found(self):
        self.assertTrue(inventory.table_problems([self.row("a")], self.facts))

    def test_a_run_left_unclassified_is_found(self):
        self.assertTrue(inventory.table_problems([self.row("a"), self.row("b", cls=None)], self.facts))

    def test_a_run_listed_twice_is_found(self):
        self.assertTrue(inventory.table_problems([self.row("a"), self.row("a"), self.row("b")], self.facts))

    def test_a_summary_only_run_marked_as_covering_the_column_file_is_found(self):
        self.assertTrue(inventory.table_problems([self.row("a", states=SUMMARY), self.row("b")], self.facts))


class Collect(unittest.TestCase):
    def test_every_recorded_geant4_run_is_found(self):
        rows = inventory.collect(ROOT)
        self.assertEqual(Counter(row["journey"] for row in rows), {"J14": 26, "J15": 74, "J16": 10})
        self.assertEqual(len({row["run"] for row in rows}), 110)

    def test_every_run_has_a_source_commit_and_a_spec_file_with_its_hash(self):
        for row in inventory.collect(ROOT):
            with self.subTest(run=row["run"]):
                self.assertIsNotNone(row["source_commit"])
                found = list((ROOT / inventory.EXAMPLES[row["journey"]] / "recorded").rglob(row["spec_name"]))
                self.assertIn(row["spec_file_sha256"], {hashlib.sha256(path.read_bytes()).hexdigest() for path in found})

    def test_each_row_says_how_to_rerun_it(self):
        for row in inventory.collect(ROOT):
            self.assertTrue(row["seeds"] and row["events"] and row["spec_sha256"] and row["outputs"], row["run"])


class CheckWork(unittest.TestCase):
    def test_a_file_is_matched_by_its_hash(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "j" / "run").mkdir(parents=True)
            (root / "j" / "run" / "events.csv").write_text("1\n", encoding="utf-8")
            (root / "j" / "run" / "log.txt").write_text("changed\n", encoding="utf-8")
            digest = hashlib.sha256(b"1\n").hexdigest()
            row = {"run": "r", "work": "~/Workspace/geant4-work/j", "outputs": {
                "run/events.csv": digest, "run/log.txt": digest, "run/gone.json": digest}}
            self.assertEqual(inventory.check_work([row], root)["r"],
                             {"run/events.csv": "match", "run/log.txt": "different", "run/gone.json": "missing"})


if __name__ == "__main__":
    unittest.main()
