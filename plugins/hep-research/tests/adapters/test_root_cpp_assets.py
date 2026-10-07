"""adapters/root-uproot: the C++ assets build against ROOT and run on the SYNTHETIC ROOT fixtures.

- rdf_cutflow_analysis.cpp, fit_histogram.cpp and rdf_histogram_branch.cpp compile with `root-config --cxx --cflags --libs`;
- the C++ RDataFrame cutflow equals the PyROOT asset's cutflow on the same file (two implementations, one selection);
- CMakeLists.txt configures and builds its `analysis` target;
- plot_branch.C runs as a batch macro.

ROOT is found from $HEP_ROOT_CONFIG (a root-config path), else next to $HEP_ROOT_PYTHON, else on PATH. Skipped, and
therefore unverified, without ROOT; the CMake test also needs cmake.
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
ASSETS = ROOT_DIR / "adapters" / "root-uproot" / "assets"
FIXTURES = ROOT_DIR / "tests" / "skills" / "hep_computing" / "make_root_fixtures.py"


def _root_config():
    explicit = os.environ.get("HEP_ROOT_CONFIG")
    if explicit:
        return explicit if Path(explicit).is_file() else None
    py = os.environ.get("HEP_ROOT_PYTHON")
    if py and (Path(py).parent / "root-config").is_file():
        return str(Path(py).parent / "root-config")
    return shutil.which("root-config")


ROOT_CONFIG = _root_config()
BIN = Path(ROOT_CONFIG).parent if ROOT_CONFIG else None


def _pyroot_python():
    """First interpreter that can `import ROOT`: $HEP_ROOT_PYTHON, python next to root-config, the Python ROOT was
    built for (`root-config --python-version`), this interpreter, python3. None if none can (e.g. Homebrew ROOT
    built for 3.14 while python3 is 3.13, where the import fails at dlopen)."""
    cands = [os.environ.get("HEP_ROOT_PYTHON"), str(BIN / "python") if BIN else None]
    if ROOT_CONFIG:
        try:
            ver = subprocess.run([ROOT_CONFIG, "--python-version"], capture_output=True, text=True, timeout=60).stdout.strip()
            cands.append(shutil.which("python" + ".".join(ver.split(".")[:2])) if ver else None)
        except (OSError, subprocess.TimeoutExpired):
            pass
    cands += [sys.executable, shutil.which("python3")]
    for py in dict.fromkeys(c for c in cands if c and Path(c).exists()):
        try:
            if subprocess.run([py, "-c", "import ROOT"], capture_output=True, timeout=120, env=_env()).returncode == 0:
                return py
        except (OSError, subprocess.TimeoutExpired):
            continue
    return None


def _env():
    env = dict(os.environ)
    env["PATH"] = f"{BIN}{os.pathsep}{env.get('PATH', '')}"
    return env


def _rc(*args):
    return subprocess.run([ROOT_CONFIG, *args], capture_output=True, text=True, check=True, env=_env(), timeout=600).stdout.split()


def _cutflow(text):
    return [(m.group(1).strip(), int(m.group(2)), int(m.group(3)))
            for m in re.finditer(r"^(.+?)\s*:\s*pass=(\d+)\s+all=(\d+)", text, re.M)]


@unittest.skipUnless(ROOT_CONFIG, "ROOT not found (set HEP_ROOT_CONFIG or HEP_ROOT_PYTHON)")
class RootCppAssetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        python = _pyroot_python()
        if python is None:
            raise unittest.SkipTest("root-config found but no Python can import ROOT (set HEP_ROOT_PYTHON)")
        cls._tmp = tempfile.TemporaryDirectory()
        cls.dir = Path(cls._tmp.name)
        cls.python = python
        subprocess.run([python, str(FIXTURES), str(cls.dir)], check=True, capture_output=True, env=_env(), timeout=600)
        cls.cxx = _rc("--cxx")[0]
        cls.flags = _rc("--cflags", "--libs")
        libdir = _rc("--libdir")[0]
        cls.binaries = {}
        for name in ("rdf_cutflow_analysis", "fit_histogram", "rdf_histogram_branch"):
            out = cls.dir / name
            proc = subprocess.run([cls.cxx, str(ASSETS / f"{name}.cpp"), "-o", str(out), *cls.flags, f"-Wl,-rpath,{libdir}"],
                                  capture_output=True, text=True, env=_env(), timeout=600)
            cls.binaries[name] = (proc.returncode, proc.stderr[-2000:], out)

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    def run_bin(self, name, *args):
        rc, err, exe = self.binaries[name]
        self.assertEqual(rc, 0, f"build failed: {err}")
        proc = subprocess.run([str(exe), *map(str, args)], capture_output=True, text=True, cwd=self.dir, env=_env(), timeout=600)
        self.assertEqual(proc.returncode, 0, proc.stderr[-2000:])
        return proc.stdout + proc.stderr

    def test_cpp_cutflow_equals_pyroot_cutflow(self):
        cpp = _cutflow(self.run_bin("rdf_cutflow_analysis", "--input", "events.root", "--tree", "Events",
                                    "--output", "cpp_rdf.root"))
        py = subprocess.run([self.python, str(ASSETS / "pyroot_rdf_cutflow_analysis.py"), "--input", "events.root",
                             "--output", "py_rdf.root"], capture_output=True, text=True, cwd=self.dir, env=_env(), timeout=600)
        self.assertEqual(py.returncode, 0, py.stderr[-2000:])
        self.assertEqual(len(cpp), 3)
        self.assertEqual(cpp, _cutflow(py.stdout + py.stderr))
        self.assertEqual(cpp[0][2], 5000)  # every fixture event enters the cutflow
        self.assertTrue((self.dir / "cpp_rdf.root").exists())

    def test_fit_histogram_runs_and_writes_plot(self):
        out = self.run_bin("fit_histogram", "histograms.root", "mass_hist", "fit.pdf")
        self.assertIn("chi2/ndf", out)
        self.assertTrue((self.dir / "fit.pdf").exists())

    def test_rdf_histogram_branch_histograms_a_branch(self):
        out = self.run_bin("rdf_histogram_branch", "events.root", "rdf_out.root", "Events", "Muon_pt")
        self.assertIn("Events: 5000", out)
        self.assertTrue((self.dir / "rdf_out.root").exists())

    def test_plot_branch_macro_runs_in_batch(self):
        root = BIN / "root"
        self.assertTrue(root.exists(), "root executable not next to root-config")
        macro = f'{ASSETS / "plot_branch.C"}("events.root","Events","Muon_pt","macro.root")'
        proc = subprocess.run([str(root), "-b", "-q", "-l", macro], capture_output=True, text=True, cwd=self.dir, env=_env(), timeout=600)
        self.assertEqual(proc.returncode, 0, proc.stderr[-2000:])
        self.assertTrue((self.dir / "macro.root").exists())

    @unittest.skipUnless(shutil.which("cmake"), "cmake not installed")
    def test_cmake_builds_analysis_target(self):
        build = self.dir / "cmake-build"
        prefix = str(BIN.parent)
        cfg = subprocess.run(["cmake", "-S", str(ASSETS), "-B", str(build), f"-DCMAKE_CXX_COMPILER={self.cxx}",
                              f"-DCMAKE_PREFIX_PATH={prefix}"], capture_output=True, text=True, env=_env(), timeout=600)
        self.assertEqual(cfg.returncode, 0, cfg.stderr[-2000:])
        b = subprocess.run(["cmake", "--build", str(build)], capture_output=True, text=True, env=_env(), timeout=600)
        self.assertEqual(b.returncode, 0, (b.stdout + b.stderr)[-2000:])
        self.assertTrue((build / "analysis").exists())


if __name__ == "__main__":
    unittest.main()
