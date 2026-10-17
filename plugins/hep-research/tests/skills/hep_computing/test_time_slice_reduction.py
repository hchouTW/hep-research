"""time_slice_reduction.py (C1): deduplicate time-sliced records by a stable key, then sum, alone or through
core/partition. Oracles: a period split across two files is counted once; partial sums merged by local_partition.py
equal a single run byte for byte; a key whose duplicates disagree is refused; the merge inputs are recorded.
All records are SYNTHETIC."""
import json
import shlex
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[3]
ASSET = PLUGIN / "skills" / "hep-computing" / "assets" / "time_slice_reduction.py"
PARTITION = PLUGIN / "skills" / "hep-computing" / "scripts" / "local_partition.py"

HEADER = "period,era,livetime_s,n_events\n"
FILE_A = HEADER + "p1,e1,10.5,3\np2,e1,20.25,5\np3,e2,7.0,1\n"
FILE_B = HEADER + "p3,e2,7.0,1\np4,e2,12.0,4\n"          # p3 split across the file boundary: identical copy
FILE_C = HEADER + "p5,e1,1.125,0\np6,e2,2.5,2\n"


def run(*args, cwd=None):
    p = subprocess.run([sys.executable, "-B", str(ASSET), *map(str, args)], capture_output=True, text=True,
                       timeout=600, cwd=cwd)
    out = json.loads(p.stdout) if p.stdout.strip().startswith("{") else p.stdout
    return p.returncode, out, p.stderr


class TimeSliceReduction(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.d = Path(self.tmp.name)
        self.files = []
        for name, text in (("a.csv", FILE_A), ("b.csv", FILE_B), ("c.csv", FILE_C)):
            (self.d / name).write_text(text, encoding="utf-8")
            self.files.append(self.d / name)
        self.common = ["--key", "period", "--sum", "livetime_s,n_events", "--group-by", "era"]

    def test_split_period_is_counted_once(self):
        code, out, err = run("reduce", *self.files, *self.common)
        self.assertEqual(code, 0, err)
        self.assertEqual(out["status"], "ok")
        self.assertEqual(out["status_label"], "unvalidated")
        self.assertEqual(out["n_records_unique"], 6)
        self.assertEqual(out["duplicates_removed"], 1)
        self.assertEqual(out["groups"]["e1"], {"livetime_s": 10.5 + 20.25 + 1.125, "n_events": 8})
        self.assertEqual(out["groups"]["e2"], {"livetime_s": 7.0 + 12.0 + 2.5, "n_events": 7})
        self.assertEqual(out["totals"]["n_events"], 15)
        self.assertEqual(len(out["sources"]), 3)
        self.assertTrue(all(len(s["sha256"]) == 64 for s in out["sources"]))

    def test_partials_merged_by_local_partition_equal_a_single_run(self):
        code, single, err = run("reduce", *self.files, *self.common)
        self.assertEqual(code, 0, err)
        flist = self.d / "files.txt"
        flist.write_text("\n".join(str(f) for f in self.files) + "\n", encoding="utf-8")
        manifest, state = self.d / "manifest.json", self.d / "state"
        p = subprocess.run([sys.executable, "-B", str(PARTITION), "plan", "--job", "slices", "--items", "3",
                            "--chunk-size", "1", "--seed", "1", "--out", str(manifest)],
                           capture_output=True, text=True, timeout=600)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        q = shlex.quote  # the plugin may sit in a folder whose path has spaces (check_relocation, check_ams_optional)
        cmd = (f"{q(sys.executable)} -B {q(str(ASSET))} partial --file-list {q(str(flist))} --start {{start}} --stop {{stop}} "
               f"--key period --sum livetime_s,n_events --group-by era --out {{out}}")
        p = subprocess.run([sys.executable, "-B", str(PARTITION), "run", "--manifest", str(manifest), "--state",
                            str(state), "--cmd", cmd], capture_output=True, text=True, timeout=600)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        merged = self.d / "merged.json"
        p = subprocess.run([sys.executable, "-B", str(PARTITION), "merge", "--manifest", str(manifest), "--state",
                            str(state), "--rule", "records=concat", "--rule", "sources=concat"],
                           capture_output=True, text=True, timeout=600)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        merged.write_text(p.stdout, encoding="utf-8")
        code, final, err = run("finalize", merged, *self.common)
        self.assertEqual(code, 0, err)
        for key in ("groups", "totals", "n_records_unique", "duplicates_removed", "sources"):
            self.assertEqual(final[key], single[key], key)
        self.assertEqual(json.dumps(final["groups"], sort_keys=True), json.dumps(single["groups"], sort_keys=True))
        mi = final["merge_inputs"]
        self.assertEqual((mi["kind"], mi["complete"], mi["chunks_merged"], mi["chunks_expected"]),
                         ("core-partition-merge", True, 3, 3))
        self.assertEqual(mi["sources_digest"], single["merge_inputs"]["sources_digest"])

    def test_partials_given_directly(self):
        code, single, _ = run("reduce", *self.files, *self.common)
        parts = []
        for i, f in enumerate(self.files):
            out = self.d / f"part{i}.json"
            code, _, err = run("partial", f, *self.common, "--out", out)
            self.assertEqual(code, 0, err)
            parts.append(out)
        code, final, err = run("finalize", *parts, *self.common)
        self.assertEqual(code, 0, err)
        self.assertEqual(final["groups"], single["groups"])
        self.assertEqual(final["merge_inputs"]["partials"], 3)

    def test_conflicting_duplicate_is_refused(self):
        bad = self.d / "bad.csv"
        bad.write_text(HEADER + "p3,e2,7.5,1\n", encoding="utf-8")
        code, out, _ = run("reduce", self.files[0], bad, *self.common)
        self.assertEqual(code, 2)
        self.assertEqual(out["status"], "rejected")
        self.assertIn("p3", json.dumps(out["conflicts"]))

    def test_missing_key_or_column_is_refused(self):
        bad = self.d / "nokey.csv"
        bad.write_text("era,livetime_s,n_events\ne1,1,1\n", encoding="utf-8")
        code, out, _ = run("reduce", bad, *self.common)
        self.assertEqual((code, out["status"]), (2, "rejected"))
        blank = self.d / "blank.csv"
        blank.write_text(HEADER + ",e1,1,1\n", encoding="utf-8")
        code, out, _ = run("reduce", blank, *self.common)
        self.assertEqual((code, out["status"]), (2, "rejected"))
        nonnum = self.d / "nonnum.csv"
        nonnum.write_text(HEADER + "p1,e1,abc,1\n", encoding="utf-8")
        code, out, _ = run("reduce", nonnum, *self.common)
        self.assertEqual((code, out["status"]), (2, "rejected"))

    def test_json_lines_and_composite_key(self):
        jl = self.d / "x.jsonl"
        jl.write_text('{"run": 1, "slice": 1, "t": 2.0}\n{"run": 1, "slice": 2, "t": 3.0}\n'
                      '{"run": 2, "slice": 1, "t": 4.0}\n{"run": 1, "slice": 2, "t": 3.0}\n', encoding="utf-8")
        code, out, err = run("reduce", jl, "--key", "run,slice", "--sum", "t", "--status", "synthetic")
        self.assertEqual(code, 0, err)
        self.assertEqual(out["totals"], {"t": 9.0})
        self.assertEqual(out["duplicates_removed"], 1)
        self.assertEqual(out["status_label"], "synthetic")

    def test_missing_input_and_incomplete_merge(self):
        code, out, _ = run("reduce", self.d / "nope.csv", *self.common)
        self.assertEqual((code, out["status"]), (2, "rejected"))
        inc = self.d / "incomplete.json"
        inc.write_text(json.dumps({"status": "incomplete", "merged": None, "problems": [{"code": "merge.missing_chunks"}]}),
                       encoding="utf-8")
        code, out, _ = run("finalize", inc, *self.common)
        self.assertEqual((code, out["status"]), (3, "incomplete"))


if __name__ == "__main__":
    unittest.main()
