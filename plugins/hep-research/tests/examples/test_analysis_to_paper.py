"""Example E-4 (analysis to paper): SYNTHETIC signal plus background through score, cut, template fit, result
artifact, rendered macros, a draft and HEPData. Reproduction against the committed output and every pre-declared
criterion: the AUC within the statistical range of the Bayes limit, mu consistent with the injected value, macros and
table equal to the artifacts, HEPData values equal to the artifacts, the draft's numbers consistent, the RooFit step
either run or exiting 3, synthetic watermarks in the macros. With pdflatex the draft builds and a final build fails;
with PyROOT ($HEP_ROOT_PYTHON) the RooFit and core yields agree; with xgboost the BDT path meets the AUC criterion."""
import contextlib
import importlib.util
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[2]
SCRIPT = PLUGIN / "examples" / "analysis-to-paper" / "run.py"
ROOT_PYTHON = os.environ.get("HEP_ROOT_PYTHON")
HAS_NUMPY = importlib.util.find_spec("numpy") is not None
HAS_XGB = HAS_NUMPY and importlib.util.find_spec("xgboost") is not None


def has_pyroot():
    if not ROOT_PYTHON:
        return False
    try:
        return subprocess.run([ROOT_PYTHON, "-c", "import sys, ROOT; assert sys.version_info >= (3, 13)"],
                              capture_output=True, timeout=120).returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def load():
    spec = importlib.util.spec_from_file_location("analysis_to_paper_run", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["analysis_to_paper_run"] = mod
    spec.loader.exec_module(mod)
    return mod


HEX64 = re.compile(r"^[0-9a-f]{64}$")


def _without_release(doc):
    """The document without versions.plugin_release, with every 64-hex hash replaced by a placeholder."""
    if isinstance(doc, dict):
        return {k: _without_release(v) for k, v in doc.items() if k != "plugin_release"}
    if isinstance(doc, list):
        return [_without_release(v) for v in doc]
    if isinstance(doc, str) and HEX64.match(doc):
        return "<hash>"
    return doc


@unittest.skipUnless(HAS_NUMPY, "numpy is not installed")
class AnalysisToPaper(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = load()
        cls.tmp = tempfile.TemporaryDirectory()
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            cls.code = cls.mod.main(["--out", cls.tmp.name])
        cls.stdout = json.loads(buf.getvalue())
        cls.r = json.loads((Path(cls.tmp.name) / "results.json").read_text(encoding="utf-8"))

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_all_criteria_pass(self):
        self.assertEqual(self.code, 0, self.r["pass"])
        self.assertTrue(all(self.r["pass"].values()), self.r["pass"])

    def test_reproduces_committed_output(self):
        # versions.plugin_release is the release identity: "unreleased" in a working tree, the version and manifest
        # digest in a tree identical to its release manifest (CI after a release). It is not compared, nor are the
        # sha256 hashes of artifacts that carry it (record provenance, numbers.tex); every value is.
        out = SCRIPT.parent / "output"
        for rel in ("results.json", "draft/main.tex"):
            with self.subTest(file=rel):
                self.assertEqual((Path(self.tmp.name) / rel).read_bytes(), (out / rel).read_bytes())
        for rel in ("artifacts/signal_strength.json", "artifacts/selected_mass.json",
                    "artifacts/signal_strength_record.json"):
            with self.subTest(file=rel):
                a, b = (_without_release(json.loads((d / rel).read_text(encoding="utf-8")))
                        for d in (Path(self.tmp.name), out))
                self.assertEqual(a, b)
        sha = re.compile(r"sha256 [0-9a-f]{64}")
        a, b = (sha.sub("sha256 <hash>", (d / "draft/numbers.tex").read_text(encoding="utf-8"))
                for d in (Path(self.tmp.name), out))
        self.assertEqual(a, b)

    def test_synthetic_everywhere(self):
        self.assertIn("SYNTHETIC", self.r["label"])
        for f in (Path(self.tmp.name) / "artifacts").glob("*.json"):
            self.assertIn("synthetic", json.loads(f.read_text(encoding="utf-8"))["status"], f.name)

    def test_roofit_step_without_root_exits_3(self):
        if self.stdout["roofit"].get("ran"):
            self.skipTest("this interpreter has PyROOT")
        self.assertEqual(self.stdout["roofit"]["exit_code"], 3)

    @unittest.skipUnless(shutil.which("pdflatex"), "no pdflatex: the watermark rule is checked at the macro level")
    def test_draft_builds_and_final_fails(self):
        self.assertTrue(self.stdout["latex"]["draft_build_ok"])
        self.assertFalse(self.stdout["latex"]["final_build_ok"])

    @unittest.skipUnless(has_pyroot(), "no PyROOT on Python >= 3.13 (set HEP_ROOT_PYTHON)")
    def test_roofit_and_core_agree(self):
        with tempfile.TemporaryDirectory() as d, contextlib.redirect_stdout(io.StringIO()) as buf:
            code = self.mod.main(["--out", d, "--root-python", ROOT_PYTHON])
        rf = json.loads(buf.getvalue())["roofit"]
        self.assertEqual(code, 0)
        self.assertTrue(rf["ran"] and rf["agree"] and rf["check_status"] == "ok", rf)

    @unittest.skipUnless(HAS_XGB, "xgboost is not installed (optional extra bdt)")
    def test_bdt_path(self):
        with tempfile.TemporaryDirectory() as d, contextlib.redirect_stdout(io.StringIO()):
            code = self.mod.main(["--out", d, "--with-bdt"])
            r = json.loads((Path(d) / "results_bdt.json").read_text(encoding="utf-8"))
        self.assertEqual(code, 0, r["pass"])
        self.assertIn("train_bdt.py", r["score"])


if __name__ == "__main__":
    unittest.main()
