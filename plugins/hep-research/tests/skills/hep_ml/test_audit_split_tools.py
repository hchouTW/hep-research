"""hep-ml audit (PML-WP0.2, WP0.3): the split tools never pass a chronology or a grouping they did not check.

Each case reproduces a defect of 0.9.0 (source brief Appendix A1-A4): a NaN timestamp, split names in temporal_order
that are not splits, a date that is not ISO-8601 sorted as text, and the group values 1, 1.0 and "1" treated as three
groups. All were "passed" with exit 0 before the fix.
"""
import csv
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SCRIPTS = ROOT / "skills" / "hep-ml" / "scripts"
CHECK = SCRIPTS / "check_split_integrity.py"
MAKE = SCRIPTS / "make_grouped_splits.py"
sys.path.insert(0, str(SCRIPTS))
from check_split_integrity import canonical_key  # noqa: E402


def run(script, *args):
    res = subprocess.run([sys.executable, "-I", str(script), *map(str, args)], capture_output=True, text=True,
                         timeout=600)
    return res.returncode, res.stdout, res.stderr


class TemporalCheckTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def check(self, payload, *flags):
        path = self.dir / "m.json"
        path.write_text(json.dumps(payload))  # json.dumps writes NaN for float('nan'), as the A1 file has it
        return run(CHECK, path, "--json", *flags)

    def test_a1_nan_timestamp_is_invalid_input(self):
        code, out, err = self.check({"train": ["a", "b"], "val": ["c"], "test": ["d"],
                                     "groups": {"a": "R1", "b": "R2", "c": "R3", "d": "R4"},
                                     "timestamps": {"a": float("nan"), "b": 100, "c": 5, "d": 7},
                                     "temporal_order": ["train", "val", "test"]}, "--strict")
        self.assertEqual(code, 2, out + err)
        self.assertIn("'a'", out + err)

    def test_a2_unknown_split_names_in_temporal_order(self):
        code, out, err = self.check({"train": ["a", "b"], "validation": ["c"], "testing": ["d"],
                                     "groups": {"a": "R1", "b": "R2", "c": "R3", "d": "R4"},
                                     "temporal_order": ["train", "val", "test"],
                                     "timestamps": {"a": 1, "b": 200, "c": 3, "d": 4}}, "--strict")
        self.assertEqual(code, 2, out + err)
        self.assertIn("val", out + err)

    def test_a2_single_entry_temporal_order(self):
        code, out, err = self.check({"train": ["a"], "val": ["c"], "test": ["d"],
                                     "groups": {"a": "R1", "c": "R3", "d": "R4"},
                                     "temporal_order": ["train"], "timestamps": {"a": 1, "c": 3, "d": 4}})
        self.assertEqual(code, 2, out + err)

    def test_booleans_and_unpadded_dates_are_invalid(self):
        for bad in (True, "2024-1-10", "yesterday", [1]):
            with self.subTest(bad=bad):
                code, out, err = self.check({"train": ["a"], "test": ["b"], "groups": {"a": "R1", "b": "R2"},
                                             "temporal_order": ["train", "test"],
                                             "timestamps": {"a": bad, "b": "2024-03-01"}})
                self.assertEqual(code, 2, out + err)

    def test_iso_dates_are_compared_as_dates(self):
        code, out, _ = self.check({"train": ["a"], "test": ["b"], "groups": {"a": "R1", "b": "R2"},
                                   "temporal_order": ["train", "test"],
                                   "timestamps": {"a": "2024-03-01", "b": "2024-02-01T10:00:00"}})
        self.assertEqual(code, 1, out)
        rep = json.loads(out)
        self.assertEqual(rep["temporal_violations"]["train|test"]["latest_in_earlier"], "2024-03-01")
        self.assertTrue(rep["timestamps_checked"])

    def test_mixed_numbers_and_dates_are_invalid(self):
        code, out, err = self.check({"train": ["a"], "test": ["b"], "groups": {"a": "R1", "b": "R2"},
                                     "temporal_order": ["train", "test"], "timestamps": {"a": 5, "b": "2024-01-01"}})
        self.assertEqual(code, 2, out + err)

    def test_empty_split_is_incomplete_under_strict(self):
        code, out, _ = self.check({"train": ["a", "b"], "val": [], "test": ["c"],
                                   "groups": {"a": "R1", "b": "R2", "c": "R3"}}, "--strict")
        self.assertEqual(code, 3, out)
        rep = json.loads(out)
        self.assertEqual((rep["status"], rep["empty_splits"]), ("incomplete", ["val"]))
        code, out, _ = self.check({"train": ["a", "b"], "val": [], "test": ["c"],
                                   "groups": {"a": "R1", "b": "R2", "c": "R3"}})
        self.assertEqual(code, 0, out)  # without --strict an empty split is reported, not refused

    def test_misspelled_reserved_key_is_invalid(self):
        for key in ("timestamp", "group", "temporal-order", "Groups"):
            with self.subTest(key=key):
                code, out, err = self.check({"train": ["a"], "test": ["b"], key: {"a": "R1", "b": "R2"}})
                self.assertEqual(code, 2, out + err)
                self.assertIn(key, out + err)

    def test_timestamps_checked_only_when_the_comparison_ran(self):
        code, out, _ = self.check({"train": ["a"], "test": ["b"], "groups": {"a": "R1", "b": "R2"},
                                   "temporal_order": ["train", "test"], "timestamps": {"a": 1}})
        rep = json.loads(out)
        self.assertEqual(code, 3, out)
        self.assertFalse(rep["timestamps_checked"])


class TemporalSplitTests(unittest.TestCase):
    def test_a3_unpadded_date_is_refused(self):
        with tempfile.TemporaryDirectory() as td:
            table = Path(td) / "dates.csv"
            rows = [("a0", "R0", "2024-01-05"), ("a1", "R1", "2024-1-10"), ("a2", "R2", "2024-01-07"),
                    ("a3", "R3", "2024-01-20"), ("a4", "R4", "2024-02-01"), ("a5", "R5", "2024-03-01"),
                    ("a6", "R6", "2024-03-05"), ("a7", "R7", "2024-03-09"), ("a8", "R8", "2024-03-12"),
                    ("a9", "R9", "2024-03-15")]
            with open(table, "w", newline="") as f:
                csv.writer(f).writerows([("id", "run", "t"), *rows])
            code, out, _ = run(MAKE, table, "--id-column", "id", "--group-column", "run", "--time-column", "t",
                               "--mode", "temporal", "--fractions", "0.6", "0.2", "0.2", "--out", Path(td) / "m.json")
            self.assertEqual(code, 2, out)
            self.assertIn("a1", out)
            # With the date written in ISO-8601 the row lands in train and the check passes.
            rows[1] = ("a1", "R1", "2024-01-10")
            with open(table, "w", newline="") as f:
                csv.writer(f).writerows([("id", "run", "t"), *rows])
            code, out, _ = run(MAKE, table, "--id-column", "id", "--group-column", "run", "--time-column", "t",
                               "--mode", "temporal", "--fractions", "0.6", "0.2", "0.2", "--out", Path(td) / "m.json")
            self.assertEqual(code, 0, out)
            manifest = json.loads((Path(td) / "m.json").read_text())
            self.assertIn("a1", manifest["train"])
            code, out, _ = run(CHECK, Path(td) / "m.json", "--strict")
            self.assertEqual(code, 0, out)


class GroupKeyTests(unittest.TestCase):
    def test_canonical_numeric_keys(self):
        self.assertEqual({canonical_key(v) for v in (1, 1.0, "1", " 1 ", "1.0", "1.")}, {"1"})
        self.assertEqual(canonical_key(1.5), "1.5")
        self.assertEqual(canonical_key("007"), "007")  # a string keeps its digits; only a zero fraction is dropped
        self.assertEqual(canonical_key("Run7"), "run7")
        self.assertEqual(canonical_key("Run7", case_sensitive=True), "Run7")
        for bad in (True, False, [1], {"a": 1}):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                canonical_key(bad)

    def test_a4_numeric_group_values_are_one_group(self):
        rows = [{"id": "a", "run": 1}, {"id": "b", "run": 1.0}, {"id": "c", "run": "1"},
                {"id": "d", "run": 2}, {"id": "e", "run": 3}, {"id": "f", "run": 4}]
        with tempfile.TemporaryDirectory() as td:
            table = Path(td) / "groups.json"
            table.write_text(json.dumps(rows))
            built = 0
            for seed in range(8):
                with self.subTest(seed=seed):
                    code, out, _ = run(MAKE, table, "--id-column", "id", "--group-column", "run", "--seed", seed,
                                       "--out", Path(td) / "m.json")
                    if code == 2 and "received no group" in out:
                        continue  # four groups, one of three rows: some shuffles cannot fill three splits
                    self.assertEqual(code, 0, out)
                    built += 1
                    manifest = json.loads((Path(td) / "m.json").read_text())
                    self.assertEqual({manifest["groups"][i] for i in "abc"}, {"1"})
                    home = {name for name in ("train", "val", "test") if set("abc") & set(manifest.get(name, []))}
                    self.assertEqual(len(home), 1, manifest)
            self.assertGreater(built, 0)

    def test_a4_check_reports_leakage_across_numeric_spellings(self):
        with tempfile.TemporaryDirectory() as td:
            f = Path(td) / "m.json"
            f.write_text(json.dumps({"train": ["a", "d"], "val": ["b"], "test": ["c"],
                                     "groups": {"a": 1, "b": 1.0, "c": "1", "d": 2}}))
            code, out, _ = run(CHECK, f, "--json")
        self.assertEqual(code, 1, out)
        self.assertEqual(json.loads(out)["group_leakage"], {"1": ["test", "train", "val"]})

    def test_boolean_list_object_groups_are_invalid(self):
        for bad in (True, [1, 2], {"r": 1}):
            with self.subTest(bad=bad), tempfile.TemporaryDirectory() as td:
                f = Path(td) / "m.json"
                f.write_text(json.dumps({"train": ["a"], "test": ["b"], "groups": {"a": bad, "b": "R2"}}))
                code, out, err = run(CHECK, f)
                self.assertEqual(code, 2, out + err)
                table = Path(td) / "t.json"
                table.write_text(json.dumps([{"id": "a", "run": bad}, {"id": "b", "run": 2}, {"id": "c", "run": 3}]))
                code, out, _ = run(MAKE, table, "--id-column", "id", "--group-column", "run", "--out", Path(td) / "o")
                self.assertEqual(code, 2, out)

    def test_label_column_reports_class_counts_and_refuses_an_empty_class(self):
        rows = [{"id": f"e{i}", "run": f"R{i}", "y": 1 if i == 0 else 0} for i in range(10)]
        with tempfile.TemporaryDirectory() as td:
            table = Path(td) / "t.json"
            table.write_text(json.dumps(rows))
            args = [table, "--id-column", "id", "--group-column", "run", "--label-column", "y", "--seed", "0",
                    "--out", Path(td) / "m.json"]
            code, out, _ = run(MAKE, *args)
            self.assertEqual(code, 2, out)
            self.assertIn("class", out)
            code, out, _ = run(MAKE, *args, "--allow-empty-class")
            self.assertEqual(code, 0, out)
            summary = json.loads(out)
            counts = {name: s["class_counts"] for name, s in summary["splits"].items()}
            self.assertEqual(sum(c.get("1", 0) for c in counts.values()), 1)
            self.assertEqual(sum(sum(c.values()) for c in counts.values()), 10)


if __name__ == "__main__":
    unittest.main()
