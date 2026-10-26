"""skills/hep-computing/scripts/extract_names.py (semantic naming P2): N1, N2, N5 and N16 inventories of a synthetic
project, change marking against a git revision, the working-file rule and the hand-off to contracts/naming_check.py."""
from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "skills/hep-computing/scripts/extract_names.py"
sys.path.insert(0, str(ROOT))

from contracts.schema import validate  # noqa: E402

spec = importlib.util.spec_from_file_location("extract_names", SCRIPT)
X = importlib.util.module_from_spec(spec)
spec.loader.exec_module(X)

ANALYSIS = '''import os

THRESHOLD_GEV = 10.0


def process_data(events, *, pt_min):
    selected = [e for e in events if e > pt_min]
    for i in range(3):
        selected.append(i)
    return selected


class Spectrum:
    def __init__(self, bins):
        self.bins = bins

    def fill(self, value):
        return value


def fit(x):
    return x


def fit(x):
    return 2 * x


LEVEL = os.environ.get("ANALYSIS_LEVEL", "1")
'''
RUN = '''from analysis import process_data

process_data([1, 2], pt_min=1)
'''


def git(root: Path, *args):
    subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True,
                   env={"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.invalid", "GIT_COMMITTER_NAME": "t",
                        "GIT_COMMITTER_EMAIL": "t@example.invalid", "PATH": "/usr/bin:/bin:/usr/local/bin:/opt/homebrew/bin"}, timeout=60)


class ProjectTests(unittest.TestCase):
    def setUp(self):
        self.workdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.workdir.cleanup)
        self.root = Path(self.workdir.name)
        (self.root / "analysis.py").write_text(ANALYSIS)
        (self.root / "run.py").write_text(RUN)

    def by(self, inv, name, **match):
        return [e for e in inv["entities"] if e["name"] == name and all(e.get(k) == v for k, v in match.items())]

    def test_n1_kinds_references_and_duplicates(self):
        inv = X.extract_n1(self.root, ["."])
        self.assertTrue(validate(inv, "naming_inventory.json").ok, validate(inv, "naming_inventory.json").as_dict())
        self.assertEqual(inv["inputs_scanned"], 2)
        pd = self.by(inv, "process_data")[0]
        self.assertEqual(pd["entity_kind"], "module_public")
        froms = {r["from"] for r in pd["references"]}
        self.assertIn("run.py:1", froms)  # the import
        self.assertIn("run.py:3", froms)  # the call
        i = self.by(inv, "i")[0]
        self.assertEqual(i["entity_kind"], "local")
        self.assertTrue(all(r["kind"] == "in-scope" for r in i["references"]))
        pt = self.by(inv, "pt_min")[0]
        self.assertIn("run.py:3", {r["from"] for r in pt["references"]})  # keyword argument at the call site
        self.assertEqual(self.by(inv, "__init__")[0]["source"], "external")
        self.assertEqual(self.by(inv, "bins", entity_kind="module_public")[0]["scope"]["container"], "Spectrum")
        fits = self.by(inv, "fit")
        self.assertEqual(len(fits), 2)
        self.assertNotEqual(fits[0]["entity_id"], fits[1]["entity_id"])

    def test_n1_changes_against_a_revision(self):
        if shutil.which("git") is None:
            self.skipTest("git is not installed")
        git(self.root, "init", "-q")
        git(self.root, "add", ".")
        git(self.root, "commit", "-qm", "base")
        text = ANALYSIS.replace("    return value\n", "    return value * 2\n").replace(
            "def process_data(events, *, pt_min):", "def apply_selection_cuts(events, *, pt_min):")
        (self.root / "analysis.py").write_text(text)
        inv = X.extract_n1(self.root, ["."], "HEAD")
        self.assertEqual(self.by(inv, "fill")[0]["change"], "modified")
        self.assertEqual(self.by(inv, "apply_selection_cuts")[0]["change"], "added")
        gone = self.by(inv, "process_data", change="removed")
        self.assertEqual(len(gone), 1)
        self.assertIn("run.py:3", {r["from"] for r in gone[0]["references"]})
        self.assertEqual(self.by(inv, "THRESHOLD_GEV")[0]["change"], "unchanged")
        # the removed name, still used by the unchanged run.py, is reported by the check
        from contracts.naming_check import registries, run_check
        rules, surfaces = registries()
        rep = run_check([inv], rules=rules, surfaces=surfaces)
        hits = [f for f in rep["findings"] if f["rule_id"] == "naming.common.reference" and f["state"] == "violated"]
        self.assertEqual([f["current"] for f in hits], ["process_data"])
        self.assertEqual(rep["exit_code"], 1)

    def cli(self, *args):
        res = subprocess.run([sys.executable, "-I", str(SCRIPT), "--surface", "N1", *args], capture_output=True, text=True,
                             timeout=120)
        return res.returncode, json.loads(res.stdout)

    def test_changed_alone_uses_the_merge_base_and_a_later_revision_reports_every_name(self):
        if shutil.which("git") is None:
            self.skipTest("git is not installed")
        git(self.root, "init", "-q", "-b", "main")
        git(self.root, "add", ".")
        git(self.root, "commit", "-qm", "base")
        git(self.root, "checkout", "-qb", "work")
        (self.root / "helpers.py").write_text("def do_something():\n    pass\n")
        git(self.root, "add", ".")
        git(self.root, "commit", "-qm", "work")
        out = self.root / "inv.json"
        code, _ = self.cli("--root", str(self.root), "--changed", "--out", str(out))
        inv = json.loads(out.read_text())
        self.assertEqual((code, self.by(inv, "do_something")[0]["change"]), (0, "added"))
        self.assertEqual(inv["change_base"]["hidden_commits"], 0)
        code, _ = self.cli("--root", str(self.root), "--changed", "HEAD", "--out", str(out))
        inv = json.loads(out.read_text())
        self.assertEqual((self.by(inv, "do_something")[0]["change"], inv["change_base"]["hidden_commits"]), ("unchanged", 1))
        from contracts.naming_check import main as check
        import io
        from contextlib import redirect_stdout
        with redirect_stdout(io.StringIO()) as buf:
            code = check(["check", "--inventory", str(out)])
        rep = json.loads(buf.getvalue())
        self.assertNotEqual(code, 0)  # never a pass: the revision hides this branch's work (the fixture's duplicate fit fails)
        self.assertTrue(any("hides work of this branch" in n for n in rep["notes"]))
        self.assertIn("do_something", {f["current"] for f in rep["findings"]})

    def test_a_subfolder_root_is_refused(self):
        if shutil.which("git") is None:
            self.skipTest("git is not installed")
        git(self.root, "init", "-q")
        (self.root / "sub").mkdir()
        (self.root / "sub" / "a.py").write_text("def f():\n    pass\n")
        code, status = self.cli("--root", str(self.root / "sub"), "--out", str(self.root / "inv.json"))
        self.assertEqual((code, status["status"]), (2, "rejected"))
        self.assertIn("--scope", status["error"])

    def test_bad_revision_is_rejected(self):
        res = subprocess.run([sys.executable, "-I", str(SCRIPT), "--surface", "N1", "--root", str(self.root), "--changed",
                              "no-such-rev", "--out", str(self.root / "inv.json")], capture_output=True, text=True, timeout=120)
        self.assertEqual(res.returncode, 2)
        self.assertEqual(json.loads(res.stdout)["status"], "rejected")

    def test_n2_files_versions_and_references(self):
        (self.root / "figures").mkdir()
        (self.root / "figures" / "plot_final2.pdf").write_bytes(b"%PDF")
        (self.root / "paper.tex").write_text("\\includegraphics{figures/plot_final2}\n")
        inv = X.extract_n2(self.root, ["."])
        f = self.by(inv, "plot_final2.pdf")[0]
        self.assertIn("paper.tex:1", {r["from"] for r in f["references"]})
        self.assertIn("N14:**", f["search_coverage"])
        d = self.by(inv, "figures")[0]
        self.assertIn("paper.tex:1", {r["from"] for r in d["references"]})
        from contracts.naming_check import registries, run_check
        rules, surfaces = registries()
        rep = run_check([inv], rules=rules, surfaces=surfaces, report_all=True)
        codes = {f["reason_code"] for f in rep["findings"] if f["current"] == "plot_final2.pdf"}
        self.assertIn("naming.version_in_name", codes)
        self.assertIn("naming.status_label_missing", codes)  # 'final' claims a status nobody declared

    def test_n2_manifest_checksummed(self):
        (self.root / "spectrum.csv").write_text("1,2\n")
        (self.root / "manifest.json").write_text(json.dumps({"outputs": [{"path": "spectrum.csv", "sha256": "0" * 64}]}))
        inv = X.extract_n2(self.root, ["."])
        self.assertEqual(self.by(inv, "spectrum.csv")[0]["entity_kind"], "manifest_checksummed")

    def test_n5_flags_env_and_config(self):
        (self.root / "cli.py").write_text('import argparse\nap = argparse.ArgumentParser()\nap.add_argument("--livetime-s")\n'
                                          'ap.add_argument("--doIt")\n')
        (self.root / "config.json").write_text('{"pt_min": 1, "pt_min": 2, "output": {"dir": "x"}}')
        (self.root / "README.md").write_text("Run with --livetime-s 3.\n")
        inv = X.extract_n5(self.root, ["."])
        kinds = {e["name"]: e["entity_kind"] for e in inv["entities"]}
        self.assertEqual(kinds["--livetime-s"], "project_cli_flag")
        self.assertEqual(kinds["ANALYSIS_LEVEL"], "env_var")
        self.assertEqual(kinds["dir"], "project_config_key")
        self.assertEqual(len(self.by(inv, "pt_min", entity_kind="project_config_key")), 2)
        flag = self.by(inv, "--livetime-s")[0]
        self.assertIn("README.md:1", {r["from"] for r in flag["references"]})

    def test_n5_yaml_without_pyyaml_is_listed(self):
        (self.root / "settings.yaml").write_text("a: 1\n")
        try:
            import yaml  # noqa: F401
            self.skipTest("PyYAML is installed")
        except ImportError:
            pass
        inv = X.extract_n5(self.root, ["."])
        self.assertEqual([s["path"] for s in inv["skipped_inputs"]], ["settings.yaml"])
        self.assertNotIn("N5:**", inv["entities"][0]["search_coverage"])

    def test_n16_outside_the_plugin_scans_nothing(self):
        res = subprocess.run([sys.executable, "-I", str(SCRIPT), "--surface", "N16", "--root", str(self.root),
                              "--out", str(self.root / "inv.json")], capture_output=True, text=True, timeout=120)
        self.assertEqual(res.returncode, 3)
        self.assertEqual(json.loads(res.stdout)["status"], "incomplete")

    def test_out_inside_artifacts_dir_is_refused(self):
        (self.root / "hep-research.project.json").write_text(json.dumps({"schema_version": "1.3.0", "plugin_version": ">=0.1"}))
        art = self.root / "hep-research-artifacts"
        art.mkdir()
        res = subprocess.run([sys.executable, "-I", str(SCRIPT), "--surface", "N1", "--root", str(self.root),
                              "--out", str(art / "inv.json")], capture_output=True, text=True, timeout=120)
        self.assertEqual(res.returncode, 2)
        self.assertFalse((art / "inv.json").exists())

    def test_cli_writes_a_valid_inventory(self):
        (self.root / "naming").mkdir()
        out = self.root / "naming" / "n1.json"
        res = subprocess.run([sys.executable, "-I", str(SCRIPT), "--surface", "N1", "--root", str(self.root),
                              "--out", str(out)], capture_output=True, text=True, timeout=120)
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
        self.assertTrue(validate(json.loads(out.read_text()), "naming_inventory.json").ok)


class PluginTests(unittest.TestCase):
    def test_n16_reads_the_plugin_vocabulary(self):
        inv = X.extract_n16(ROOT, ["."])
        names = {(e["entity_kind"], e["name"]) for e in inv["entities"]}
        self.assertIn(("contract_term", "computational-run"), names)
        self.assertIn(("skill_name", "hep-computing"), names)
        self.assertIn(("script_name", "extract_names.py"), names)
        self.assertIn(("schema_name", "naming_inventory.json"), names)


if __name__ == "__main__":
    unittest.main()
