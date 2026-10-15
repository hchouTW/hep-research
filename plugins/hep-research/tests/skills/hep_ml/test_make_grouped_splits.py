"""Tests for skills/hep-ml/scripts/make_grouped_splits.py: whole groups per split (run, event, period), temporal
ordering, determinism for a seed, grouped k-fold disjointness, null-group refusal and policies, and a manifest that
check_split_integrity.py passes as written."""
import contextlib
import csv
import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SCRIPTS = ROOT / "skills" / "hep-ml" / "scripts"
SCRIPT = SCRIPTS / "make_grouped_splits.py"
CHECKER = SCRIPTS / "check_split_integrity.py"
sys.path.insert(0, str(SCRIPTS))
import make_grouped_splits as mgs  # noqa: E402


def period_rows(n_periods=10, per_period=20):
    """Rows of events in data-taking periods; period p covers times [100p, 100p + per_period)."""
    return [{"event": f"e{p}_{i}", "period": f"P{p:02d}", "time": 100 * p + i}
            for p in range(n_periods) for i in range(per_period)]


def run_cli(rows, *extra, suffix=".csv"):
    with tempfile.TemporaryDirectory() as td:
        table = Path(td) / f"rows{suffix}"
        if suffix == ".csv":
            with open(table, "w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
                writer.writeheader()
                writer.writerows(rows)
        elif suffix == ".jsonl":
            table.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
        else:
            table.write_text(json.dumps(rows), encoding="utf-8")
        out = Path(td) / "splits.json"
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = mgs.main([str(table), "--out", str(out), *extra])
        report = json.loads(buf.getvalue())
        manifest = json.loads(out.read_text(encoding="utf-8")) if out.exists() else None
        check = None
        if manifest is not None:
            res = subprocess.run([sys.executable, "-I", str(CHECKER), "--strict", "--json", str(out)],
                                 capture_output=True, text=True, timeout=600)
            check = (res.returncode, json.loads(res.stdout))
        return code, report, manifest, check


def split_of(manifest, names):
    return {rid: name for name in names for rid in manifest[name]}


class GroupedSplitTests(unittest.TestCase):
    def test_period_grouping_keeps_each_period_in_one_split_and_passes_the_checker(self):
        code, summary, manifest, check = run_cli(period_rows(), "--id-column", "event", "--group-column", "period",
                                                 "--seed", "3")
        self.assertEqual(code, 0)
        where = split_of(manifest, ("train", "val", "test"))
        self.assertEqual(len(where), 200)
        for period in {r["period"] for r in period_rows()}:
            members = {where[r["event"]] for r in period_rows() if r["period"] == period}
            self.assertEqual(len(members), 1, period)
        self.assertEqual({k: v["groups"] for k, v in summary["splits"].items()}, {"train": 6, "val": 2, "test": 2})
        self.assertAlmostEqual(summary["splits"]["train"]["fraction"], 0.6)
        self.assertEqual((summary["mode"], summary["seed"]), ("random-groups", 3))
        self.assertEqual(check[0], 0, check[1])
        self.assertEqual(check[1]["status"], "passed")

    def test_same_seed_same_split_different_seed_differs(self):
        rows = period_rows(n_periods=30, per_period=3)
        args = ("--id-column", "event", "--group-column", "period")
        first = run_cli(rows, *args, "--seed", "7")[2]
        again = run_cli(rows, *args, "--seed", "7", suffix=".json")[2]
        other = run_cli(rows, *args, "--seed", "8")[2]
        self.assertEqual(first, again)
        self.assertNotEqual(first["test"], other["test"])

    def test_temporal_mode_puts_earliest_groups_in_train(self):
        rows = period_rows()
        rows.reverse()  # input order must not matter
        code, summary, manifest, check = run_cli(rows, "--id-column", "event", "--group-column", "period",
                                                 "--time-column", "time", "--mode", "temporal", suffix=".jsonl")
        self.assertEqual(code, 0)
        t = manifest["timestamps"]
        self.assertLess(max(t[i] for i in manifest["train"]), min(t[i] for i in manifest["val"]))
        self.assertLess(max(t[i] for i in manifest["val"]), min(t[i] for i in manifest["test"]))
        self.assertEqual(manifest["temporal_order"], ["train", "val", "test"])
        self.assertEqual({manifest["groups"][i] for i in manifest["test"]}, {"p08", "p09"})
        self.assertEqual(summary["time_ranges_overlap"], [])
        self.assertEqual(check[0], 0, check[1])
        self.assertTrue(check[1]["timestamps_checked"])

    def test_temporal_mode_needs_a_time_column(self):
        code, report, manifest, _ = run_cli(period_rows(), "--id-column", "event", "--group-column", "period",
                                            "--mode", "temporal")
        self.assertEqual((code, manifest), (2, None))
        self.assertIn("time-column", report["error"])

    def test_k_fold_groups_are_disjoint_and_cover_every_row(self):
        rows = [{"id": f"r{i}", "event": f"ev{i // 3}"} for i in range(300)]  # three candidates per event
        code, summary, manifest, check = run_cli(rows, "--id-column", "id", "--group-column", "event", "--folds", "5",
                                                 "--seed", "1")
        self.assertEqual(code, 0)
        folds = [f"fold{i}" for i in range(5)]
        self.assertEqual(sorted(k for k in manifest if k.startswith("fold")), folds)
        seen = [rid for f in folds for rid in manifest[f]]
        self.assertEqual(len(seen), 300)
        self.assertEqual(len(set(seen)), 300)
        event_folds = {}
        for f in folds:
            for rid in manifest[f]:
                event_folds.setdefault(manifest["groups"][rid], set()).add(f)
        self.assertTrue(all(len(v) == 1 for v in event_folds.values()))
        self.assertEqual({v["rows"] for v in summary["splits"].values()}, {60})
        self.assertEqual(check[0], 0, check[1])

    def test_null_groups_refused_without_a_policy(self):
        rows = period_rows(n_periods=5, per_period=4)
        rows[0]["period"] = ""
        rows[5]["period"] = " NaN "
        code, report, manifest, _ = run_cli(rows, "--id-column", "event", "--group-column", "period")
        self.assertEqual((code, manifest), (2, None))
        self.assertIn("2 row(s)", report["error"])

    def test_null_group_policies(self):
        rows = period_rows(n_periods=5, per_period=4)
        rows[0]["period"] = ""
        rows[5]["period"] = "null"
        base = ("--id-column", "event", "--group-column", "period")
        code, summary, manifest, check = run_cli(rows, *base, "--null-group-policy", "drop")
        self.assertEqual(code, 0)
        self.assertEqual(summary["null_groups"], {"null_group_rows": 2, "policy": "drop", "dropped_rows": 2})
        self.assertEqual(summary["rows_assigned"], 18)
        self.assertNotIn("e0_0", manifest["groups"])
        self.assertEqual(check[0], 0, check[1])
        code, summary, manifest, check = run_cli(rows, *base, "--null-group-policy", "own-group")
        self.assertEqual(code, 0)
        self.assertEqual(summary["rows_assigned"], 20)
        self.assertEqual(summary["groups"], 7)
        self.assertNotEqual(manifest["groups"]["e0_0"], manifest["groups"]["e1_1"])
        self.assertEqual(check[0], 0, check[1])

    def test_case_and_whitespace_variants_are_one_group(self):
        rows = [{"id": f"r{i}", "run": ("Run7 " if i % 2 else "run7") if i < 10 else f"run{i}"} for i in range(40)]
        code, summary, manifest, check = run_cli(rows, "--id-column", "id", "--group-column", "run")
        self.assertEqual(code, 0)
        where = split_of(manifest, ("train", "val", "test"))
        self.assertEqual(len({where[f"r{i}"] for i in range(10)}), 1)
        self.assertEqual(check[0], 0, check[1])

    def test_bad_input_is_exit_2(self):
        rows = period_rows(n_periods=3, per_period=2)
        cases = {
            "duplicate": (rows + [dict(rows[0])], ("--id-column", "event", "--group-column", "period")),
            "missing column": (rows, ("--id-column", "event", "--group-column", "run")),
            "fractions": (rows, ("--id-column", "event", "--group-column", "period", "--fractions", "0.5", "0.5",
                                 "0.5")),
            "too few groups": (period_rows(n_periods=2), ("--id-column", "event", "--group-column", "period")),
        }
        for name, (data, args) in cases.items():
            with self.subTest(name):
                code, report, manifest, _ = run_cli(data, *args)
                self.assertEqual((code, manifest), (2, None))
                self.assertIn("error", report)

    def test_command_line_help_and_missing_file(self):
        res = subprocess.run([sys.executable, "-I", str(SCRIPT), "--help"], capture_output=True, text=True,
                             timeout=600)
        self.assertEqual(res.returncode, 0)
        self.assertIn("Exit codes", res.stdout)
        with tempfile.TemporaryDirectory() as td:
            res = subprocess.run([sys.executable, "-I", str(SCRIPT), "/nonexistent/rows.csv", "--id-column", "a",
                                  "--group-column", "b", "--out", str(Path(td) / "o.json")],
                                 capture_output=True, text=True, timeout=600)
        self.assertEqual(res.returncode, 2)
        self.assertIn("error", json.loads(res.stdout))
        self.assertNotIn("Traceback", res.stderr)


if __name__ == "__main__":
    unittest.main()
