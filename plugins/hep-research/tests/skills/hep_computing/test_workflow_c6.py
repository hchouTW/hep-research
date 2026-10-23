"""C6: a workflow as a DAG (assets/workflow/workflow.json), run by scripts/run_workflow.py (standard library) with a
computational-run per step, and mirrored by a Snakefile template. Oracles: a rerun on synthetic data is byte-identical
(every output and every run record); the run records validate as computational-run artifacts; a cycle and a missing
input are refused; the Snakefile has one rule per step with the same outputs; snakemake runs the template when it is
installed (skipped otherwise). All inputs are SYNTHETIC."""
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[3]
RUNNER = PLUGIN / "skills" / "hep-computing" / "scripts" / "run_workflow.py"
WF = PLUGIN / "skills" / "hep-computing" / "assets" / "workflow"
sys.path.insert(0, str(PLUGIN))


def run(*args):
    p = subprocess.run([sys.executable, "-B", str(RUNNER), *map(str, args)], capture_output=True, text=True,
                       timeout=600)
    return p.returncode, (json.loads(p.stdout) if p.stdout.strip().startswith("{") else None), p.stderr


def tree(d: Path) -> dict:
    return {p.relative_to(d).as_posix(): p.read_bytes() for p in sorted(d.rglob("*")) if p.is_file()}


class Runner(unittest.TestCase):
    def test_rerun_is_byte_identical_and_records_validate(self):
        from contracts.validate import validate_artifact
        with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
            for d in (a, b):
                code, out, err = run(WF / "workflow.json", "--work", d, "--created", "2026-10-17", "--status",
                                     "synthetic")
                self.assertEqual(code, 0, (out, err))
                self.assertEqual(out["status"], "ok")
                self.assertEqual([s["id"] for s in out["steps"]], ["generate", "histogram", "report"])
            ta, tb = tree(Path(a)), tree(Path(b))
            self.assertEqual(sorted(ta), sorted(tb))
            for name in ta:
                with self.subTest(file=name):
                    self.assertEqual(ta[name], tb[name])
            records = [n for n in ta if n.startswith("runs/")]
            self.assertEqual(len(records), 3)
            for n in records:
                doc = json.loads(ta[n])
                rep = validate_artifact(doc)
                self.assertTrue(rep.ok, (n, rep.as_dict()))
                self.assertEqual(doc["artifact_type"], "computational-run")
                self.assertEqual(doc["extension"]["exit_status"], 0)
            self.assertNotIn(a.encode(), b"".join(ta.values()))
            report = json.loads(ta["report.json"])
            self.assertEqual(report["n_rows"], 2000)

    def test_dry_run_lists_the_order(self):
        code, out, _ = run(WF / "workflow.json", "--work", "unused", "--dry-run")
        self.assertEqual(code, 0)
        self.assertEqual(out["order"], ["generate", "histogram", "report"])

    def test_cycle_and_missing_input_are_refused(self):
        # {workflow} must keep pointing at the shipped steps when the edited workflow is written elsewhere
        wf = json.loads((WF / "workflow.json").read_text(encoding="utf-8").replace("{workflow}", str(WF)))
        with tempfile.TemporaryDirectory() as d:
            cyc = json.loads(json.dumps(wf))
            cyc["steps"][0]["needs"] = ["report"]
            p = Path(d) / "cyc.json"
            p.write_text(json.dumps(cyc), encoding="utf-8")
            code, out, _ = run(p, "--work", Path(d) / "w1", "--dry-run")
            self.assertEqual(code, 2)
            self.assertIn("cycle", out["error"])
            miss = json.loads(json.dumps(wf))
            miss["steps"][1]["inputs"] = ["nowhere.csv"]
            p = Path(d) / "miss.json"
            p.write_text(json.dumps(miss), encoding="utf-8")
            code, out, _ = run(p, "--work", Path(d) / "w2")
            self.assertEqual(code, 2)
            self.assertIn("nowhere.csv", out["error"])


class Snakefile(unittest.TestCase):
    def test_rules_mirror_the_steps(self):
        wf = json.loads((WF / "workflow.json").read_text(encoding="utf-8"))
        text = (WF / "Snakefile").read_text(encoding="utf-8")
        rules = re.findall(r"^rule (\w+):", text, re.M)
        self.assertEqual(rules, ["all"] + [s["id"] for s in wf["steps"]])
        for s in wf["steps"]:
            for o in s["outputs"]:
                with self.subTest(step=s["id"], output=o):
                    self.assertIn(f'"{o}"', text)

    def test_snakemake_runs_the_template(self):
        if shutil.which("snakemake") is None:
            self.skipTest("snakemake is not installed")
        with tempfile.TemporaryDirectory() as d:
            p = subprocess.run(["snakemake", "-s", str(WF / "Snakefile"), "--cores", "1", "--directory", d,
                                "--config", f"plugin={PLUGIN}", f"python={sys.executable}"],
                               capture_output=True, text=True, timeout=900)
            self.assertEqual(p.returncode, 0, p.stderr[-2000:])
            self.assertTrue((Path(d) / "report.json").is_file())


class Reference(unittest.TestCase):
    def test_reference(self):
        text = (PLUGIN / "skills" / "hep-computing" / "references" / "analysis-workflows.md").read_text(encoding="utf-8")
        for term in ("DAG", "computational-run", "local_partition.py", "Snakefile", "run_workflow.py"):
            with self.subTest(term=term):
                self.assertIn(term, text)


if __name__ == "__main__":
    unittest.main()
