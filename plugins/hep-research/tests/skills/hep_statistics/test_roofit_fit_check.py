"""roofit_fit_check.py (S11, status mapping): a saved RooFitResult maps to the statistical-result status, and weighted
data need a declared error treatment.

Oracles (need PyROOT; skipped unless a Python 3.13 or newer that can `import ROOT` is available: $HEP_ROOT_PYTHON,
e.g. /opt/homebrew/bin/python3.14 for Homebrew ROOT, else the interpreter running the tests; CI's optional ROOT job
runs them): a converged fit (status 0, covQual 3, small EDM) maps to ok with method_kind hesse, and with MINOS to
minos; a fit without HESSE (covQual 1) and a degenerate model (status 1, covQual 2) are failed with the reason, never
ok; an EDM above the declared threshold is failed. Without PyROOT, `result` exits 3 with an install hint. `weighted`
exits 3 when weighted data come without --weighted-errors; sweights points to sweighted_fit.py. --help runs without
NumPy. All data are SYNTHETIC."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tests.skills.hep_computing.pyroot_floor import meets_floor

PLUGIN = Path(__file__).resolve().parents[3]
SCRIPT = PLUGIN / "skills" / "hep-statistics" / "scripts" / "roofit_fit_check.py"
PYTHON = os.environ.get("HEP_ROOT_PYTHON", sys.executable)

FIXTURE = r'''
import sys, ROOT
ROOT.gErrorIgnoreLevel = ROOT.kError
ROOT.RooMsgService.instance().setGlobalKillBelow(ROOT.RooFit.FATAL)
out = sys.argv[1]
x = ROOT.RooRealVar("x", "x", -10, 10)
m = ROOT.RooRealVar("m", "m", 0, -5, 5); s = ROOT.RooRealVar("s", "s", 1, 0.1, 5)
g = ROOT.RooGaussian("g", "g", x, m, s)
ROOT.RooRandom.randomGenerator().SetSeed(1)
d = g.generate(ROOT.RooArgSet(x), 2000)
f = ROOT.TFile(out, "RECREATE")
for name, opts in (("hesse", []), ("minos", [ROOT.RooFit.Minos(True)]),
                   ("nohesse", [ROOT.RooFit.Hesse(False), ROOT.RooFit.Strategy(0)])):
    m.setVal(0.5); s.setVal(1.5)
    r = g.fitTo(d, ROOT.RooFit.Save(True), ROOT.RooFit.PrintLevel(-1), *opts)
    r.SetName(name); r.Write(name)
a = ROOT.RooRealVar("a", "a", 0, -5, 5); b = ROOT.RooRealVar("b", "b", 0, -5, 5)
mu = ROOT.RooFormulaVar("mu", "a+b", ROOT.RooArgList(a, b))
g2 = ROOT.RooGaussian("g2", "g2", x, mu, s)
r = g2.fitTo(d, ROOT.RooFit.Save(True), ROOT.RooFit.PrintLevel(-1))
r.SetName("degenerate"); r.Write("degenerate")
w = ROOT.RooRealVar("w", "w", 0, 10)
xs = ROOT.RooArgSet(x, w)
dw = ROOT.RooDataSet("weighted", "weighted", xs, ROOT.RooFit.WeightVar("w"))
for i in range(50):
    x.setVal(0.1 * i - 2.5); dw.add(xs, 1.5)
dw.Write("weighted")
du = ROOT.RooDataSet("unweighted", "unweighted", ROOT.RooArgSet(x))
for i in range(50):
    x.setVal(0.1 * i - 2.5); du.add(ROOT.RooArgSet(x))
du.Write("unweighted")
f.Close()
'''


def has_pyroot():
    if not meets_floor(PYTHON):
        return False
    try:
        return subprocess.run([PYTHON, "-c", "import ROOT"], capture_output=True, timeout=120).returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def run(*args, python=None, env=None):
    p = subprocess.run([python or sys.executable, "-B", str(SCRIPT), *map(str, args)], capture_output=True, text=True,
                       timeout=600, env=env)
    out = json.loads(p.stdout) if p.stdout.strip().startswith("{") else p.stdout
    return p.returncode, out, p.stderr


class WithoutRoot(unittest.TestCase):
    def test_result_without_pyroot_exits_3(self):
        with tempfile.TemporaryDirectory() as d:
            Path(d, "ROOT.py").write_text("raise ImportError('ROOT hidden for this test')\n", encoding="utf-8")
            env = dict(os.environ, PYTHONPATH=f"{d}{os.pathsep}{PLUGIN}", PYTHONDONTWRITEBYTECODE="1")
            Path(d, "fit.root").write_bytes(b"")  # exists, so the missing PyROOT is what stops the run
            code, out, _ = run("result", "--file", Path(d, "fit.root"), "--name", "r", "--edm-max", "1e-3", env=env)
        self.assertEqual(code, 3)
        self.assertEqual(out["status"], "missing-dependency")
        self.assertIn("ROOT", out["install"])

    def test_weighted_data_need_a_declared_error_treatment(self):
        code, out, _ = run("weighted", "--weighted")
        self.assertEqual(code, 3)
        self.assertEqual(out["status"], "incomplete")
        self.assertIn("--weighted-errors", out["reason"])
        code, out, _ = run("weighted", "--weighted", "--weighted-errors", "asymptotic")
        self.assertEqual(code, 0)
        self.assertEqual(out["roofit_option"], "AsymptoticError(true)")
        code, out, _ = run("weighted", "--weighted", "--weighted-errors", "sweights")
        self.assertEqual(code, 0)
        self.assertIn("sweighted_fit.py", out["next"])
        code, out, _ = run("weighted", "--weighted", "--weighted-errors", "sumw2")
        self.assertEqual(out["roofit_option"], "SumW2Error(true)")
        self.assertIn("known constants", out["caveat"])

    def test_bad_input_exits_2(self):
        code, out, _ = run("weighted", "--weighted-errors", "bootstrap-please")
        self.assertEqual(code, 2)
        self.assertEqual(out["status"], "rejected")
        code, out, _ = run("result", "--file", "x.root", "--name", "r", "--edm-max", "-1")
        self.assertEqual(code, 2)

    def test_help_without_numpy(self):
        with tempfile.TemporaryDirectory() as d:
            Path(d, "numpy.py").write_text("raise ImportError('numpy hidden for this test')\n", encoding="utf-8")
            env = dict(os.environ, PYTHONPATH=d, PYTHONDONTWRITEBYTECODE="1")
            p = subprocess.run([sys.executable, "-B", str(SCRIPT), "--help"], capture_output=True, text=True,
                               timeout=600, env=env)
        self.assertEqual(p.returncode, 0)
        self.assertIn("result", p.stdout)


@unittest.skipUnless(has_pyroot(), "no PyROOT on Python >= 3.13 (set HEP_ROOT_PYTHON)")
class WithRoot(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory()
        cls.file = Path(cls._tmp.name, "fits.root")
        script = Path(cls._tmp.name, "make.py")
        script.write_text(FIXTURE, encoding="utf-8")
        subprocess.run([PYTHON, str(script), str(cls.file)], check=True, capture_output=True, timeout=600)

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    def result(self, name, edm="1e-3"):
        return run("result", "--file", self.file, "--name", name, "--edm-max", edm, python=PYTHON)

    def test_converged_fit_maps_to_ok_with_hesse(self):
        code, out, err = self.result("hesse")
        self.assertEqual(code, 0, (out, err))
        self.assertEqual(out["status"], "ok")
        self.assertEqual(out["method_kind"], "hesse")
        self.assertEqual(out["paradigm"], "frequentist")
        self.assertEqual(out["fit_diagnostics"]["cov_qual"], 3)
        self.assertEqual(out["fit_diagnostics"]["minimizer_status"], 0)
        self.assertIn("m", out["parameters"])
        self.assertEqual(out["status_label"], "unvalidated")

    def test_minos_fit_maps_to_minos(self):
        code, out, _ = self.result("minos")
        self.assertEqual(code, 0)
        self.assertEqual(out["method_kind"], "minos")
        self.assertIn("error_lo", out["parameters"]["m"])

    def test_forced_low_cov_qual_is_failed(self):
        code, out, _ = self.result("nohesse")
        self.assertEqual(code, 1)
        self.assertEqual(out["status"], "failed")
        self.assertTrue(any("covQual" in r for r in out["reasons"]))

    def test_degenerate_model_is_failed(self):
        code, out, _ = self.result("degenerate")
        self.assertEqual(code, 1)
        self.assertEqual(out["status"], "failed")
        self.assertGreaterEqual(len(out["reasons"]), 1)

    def test_edm_above_threshold_is_failed(self):
        code, out, _ = self.result("hesse", edm="1e-12")
        self.assertEqual(code, 1)
        self.assertTrue(any("EDM" in r for r in out["reasons"]))

    def test_weighted_dataset_is_detected(self):
        code, out, _ = run("weighted", "--file", self.file, "--dataset", "weighted", python=PYTHON)
        self.assertEqual(code, 3)
        self.assertTrue(out["weighted"])
        code, out, _ = run("weighted", "--file", self.file, "--dataset", "unweighted", python=PYTHON)
        self.assertEqual(code, 0)
        self.assertFalse(out["weighted"])

    def test_unknown_object_is_bad_input(self):
        code, out, _ = self.result("no-such-result")
        self.assertEqual(code, 2)
        self.assertEqual(out["status"], "rejected")


if __name__ == "__main__":
    unittest.main()
