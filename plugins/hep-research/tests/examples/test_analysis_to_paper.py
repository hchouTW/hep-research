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
        out = SCRIPT.parent / "output"
        for rel in ("results.json", "artifacts/signal_strength.json", "artifacts/selected_mass.json",
                    "artifacts/signal_strength_record.json", "draft/numbers.tex", "draft/main.tex"):
            with self.subTest(file=rel):
                self.assertEqual((Path(self.tmp.name) / rel).read_bytes(), (out / rel).read_bytes())

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
