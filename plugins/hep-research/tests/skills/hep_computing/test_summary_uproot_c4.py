"""C4: summarize_histogram_statistics.py reads with uproot as well as PyROOT, through the reader of
check_histogram_errors.py (C7). Oracles: a TH1 written with known statistics (sum of weights, of weight^2, of w x and of
w x^2) gives its integral, mean, RMS and effective entries; PyROOT and uproot give the same summary of one file; with
neither backend the script exits 3. uproot tests need uproot (E2 venv); the PyROOT comparison needs a Python >= 3.13
with ROOT ($HEP_ROOT_PYTHON). All inputs are SYNTHETIC."""
import json
import math
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[3]
SCRIPT = PLUGIN / "skills" / "hep-computing" / "scripts" / "summarize_histogram_statistics.py"
ROOT_PYTHON = os.environ.get("HEP_ROOT_PYTHON", sys.executable)
try:
    import numpy as np
    import uproot
    from uproot.writing.identify import to_TAxis, to_TH1x
except ImportError:
    uproot = None

# one weighted fill per entry: (x, w)
FILLS = [(0.5, 0.5), (0.5, 1.5), (0.7, 2.0), (1.5, 1.0), (1.2, 0.25), (2.5, 3.0)]
SW = sum(w for _, w in FILLS)
SW2 = sum(w * w for _, w in FILLS)
SWX = sum(w * x for x, w in FILLS)
SWX2 = sum(w * x * x for x, w in FILLS)


def has_pyroot():
    try:
        p = subprocess.run([ROOT_PYTHON, "-c", "import sys, ROOT; assert sys.version_info >= (3, 13)"],
                           capture_output=True, timeout=120)
        return p.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def write_root(path):
    edges = np.array([0.0, 1.0, 2.0, 3.0])
    ax = to_TAxis("xaxis", "", 3, 0.0, 3.0, fXbins=edges)
    vals = np.zeros(5)
    sw2 = np.zeros(5)
    for x, w in FILLS:
        vals[int(x) + 1] += w
        sw2[int(x) + 1] += w * w
    vals[4] += 0.75  # an overflow fill outside the statistics (as ROOT keeps it)
    sw2[4] += 0.75 ** 2
    h = to_TH1x("h", "", vals, float(len(FILLS) + 1), SW, SW2, SWX, SWX2, sw2, ax)
    with uproot.recreate(path) as f:
        f["h"] = h


def run(*args, python=None, env=None):
    p = subprocess.run([python or sys.executable, "-B", str(SCRIPT), *map(str, args)], capture_output=True, text=True,
                       timeout=600, env=env)
    return p.returncode, (json.loads(p.stdout) if p.stdout.strip().startswith("{") else None), p.stderr


@unittest.skipIf(uproot is None, "uproot is not installed (optional extra root-uproot)")
class UprootSummary(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.f = Path(self.tmp.name) / "h.root"
        write_root(self.f)

    def tearDown(self):
        self.tmp.cleanup()

    def test_known_statistics(self):
        code, out, err = run("--input", self.f, "--hist", "h", "--json", "--backend", "uproot")
        self.assertEqual(code, 0, err)
        self.assertEqual(out["backend"], "uproot")
        self.assertAlmostEqual(out["integral"], SW, delta=1e-12)
        mean = SWX / SW
        self.assertAlmostEqual(out["mean"], mean, delta=1e-12)
        self.assertAlmostEqual(out["rms"], math.sqrt(SWX2 / SW - mean * mean), delta=1e-12)
        self.assertAlmostEqual(out["effective_entries"], SW * SW / SW2, delta=1e-12)
        self.assertEqual((out["x_bins"], out["x_min"], out["x_max"]), (3, 0.0, 3.0))
        self.assertEqual(out["entries"], float(len(FILLS) + 1))
        code, out, _ = run("--input", self.f, "--hist", "h", "--json", "--backend", "uproot", "--include-flow")
        self.assertAlmostEqual(out["integral"], SW + 0.75, delta=1e-12)

    def test_missing_histogram_is_bad_input(self):
        code, out, _ = run("--input", self.f, "--hist", "nope", "--json", "--backend", "uproot")
        self.assertEqual(code, 2)
        self.assertEqual(out["status"], "error")

    @unittest.skipUnless(has_pyroot(), "no PyROOT on Python >= 3.13 (set HEP_ROOT_PYTHON)")
    def test_pyroot_and_uproot_agree(self):
        code_u, out_u, err_u = run("--input", self.f, "--hist", "h", "--json", "--backend", "uproot")
        code_p, out_p, err_p = run("--input", self.f, "--hist", "h", "--json", "--backend", "pyroot", python=ROOT_PYTHON)
        self.assertEqual((code_u, code_p), (0, 0), (err_u, err_p))
        for key in ("entries", "integral", "mean", "rms", "effective_entries", "x_bins", "x_min", "x_max",
                    "negative_bins", "empty_bins"):
            with self.subTest(key=key):
                a, b = out_u[key], out_p[key]
                if isinstance(a, float):
                    self.assertAlmostEqual(a, b, delta=1e-9 * max(1.0, abs(b)))
                else:
                    self.assertEqual(a, b)


class Documentation(unittest.TestCase):
    def test_floors_and_backends_documented(self):
        readme = (PLUGIN / "skills" / "hep-computing" / "README.md").read_text(encoding="utf-8")
        self.assertIn("## Python floors", readme)
        self.assertNotIn("the only one of these with an uproot backend", readme)
        self.assertIn("computer algebra system", (PLUGIN / "skills" / "hep-theory" / "README.md").read_text(encoding="utf-8"))


class NoBackend(unittest.TestCase):
    def test_neither_backend_exits_3(self):
        with tempfile.TemporaryDirectory() as d:
            for mod in ("ROOT", "uproot"):
                Path(d, f"{mod}.py").write_text(f"raise ImportError('{mod} hidden for this test')\n", encoding="utf-8")
            f = Path(d) / "x.root"
            f.write_bytes(b"not used")
            env = dict(os.environ, PYTHONPATH=d, PYTHONDONTWRITEBYTECODE="1")
            code, out, _ = run("--input", f, "--hist", "h", "--json", env=env)
        self.assertEqual(code, 3)
        self.assertEqual(out["status"], "missing-dependency")
        self.assertIn("uproot", out["error"])


if __name__ == "__main__":
    unittest.main()
