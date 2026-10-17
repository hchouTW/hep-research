"""physical_data.py (Th9): the CLI over core/constants. Oracles: hbar c and the GeV^-2 -> mb conversion from the
exact constants; a Q value from AME2020 mass excesses; refusal of unknown names and units (exit 2); the pdg backend
without the package (exit 3 with an install hint); --help without NumPy. All inputs are SYNTHETIC requests."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[3]
SCRIPT = PLUGIN / "skills" / "hep-theory" / "scripts" / "physical_data.py"


def run(*args, env=None):
    p = subprocess.run([sys.executable, "-B", str(SCRIPT), *args], capture_output=True, text=True, timeout=600,
                       env=env)
    return p.returncode, (json.loads(p.stdout) if p.stdout.strip().startswith("{") else p.stdout), p.stderr


class PhysicalDataCli(unittest.TestCase):
    def test_get_constant_in_gev(self):
        code, out, _ = run("get", "proton_mass_energy", "--unit", "GeV")
        self.assertEqual(code, 0)
        self.assertEqual(out["status"], "ok")
        self.assertEqual(out["status_label"], "unvalidated")
        q = out["quantity"]
        self.assertEqual((q["value"], q["unit"], q["edition"]), (0.93827208943, "GeV", "CODATA 2022"))
        self.assertIn("NIST", q["source"])
        self.assertIn("status", out["defaults_used"])

    def test_hbar_c_is_exact_and_derived(self):
        code, out, _ = run("get", "hbar_c")
        self.assertEqual(code, 0)
        self.assertTrue(out["quantity"]["exact"])
        self.assertTrue(0 <= out["quantity"]["value"] - 197.3269804 < 1e-7)

    def test_convert_natural_units(self):
        code, out, _ = run("convert", "1", "GeV^-2", "mb")
        self.assertEqual(code, 0)
        self.assertAlmostEqual(out["value"], 0.3893793721, delta=1e-9)

    def test_particle_and_nuclide(self):
        code, out, _ = run("particle", "pi+", "--unit", "GeV")
        self.assertEqual(code, 0)
        self.assertAlmostEqual(out["quantity"]["value"], 0.13957039, delta=1e-12)
        self.assertEqual(out["quantity"]["edition"], "PDG 2026")
        code, out, _ = run("nuclide", "He-4")
        self.assertEqual(code, 0)
        self.assertEqual(out["nuclide"]["atomic_mass_u"], 4.00260325413)
        self.assertEqual(out["nuclear_mass_gev"], 4.00260325413 * 0.93149410372 - 2 * 0.00051099895069)

    def test_qvalue(self):
        code, out, _ = run("qvalue", "14C", "--mode", "beta-")
        self.assertEqual(code, 0)
        self.assertAlmostEqual(out["qvalue"]["value_keV"], 156.476, delta=0.01)
        code, out, _ = run("qvalue", "26Al", "--mode", "beta+")
        self.assertEqual(code, 0)
        self.assertIn("warning", out)

    def test_bad_input_exits_2_with_json(self):
        for args in (("get", "no_such_constant"), ("convert", "1", "GeV", "furlong"), ("particle", "tachyon"),
                     ("nuclide", "4Xx"), ("qvalue", "4He", "--mode", "fission")):
            with self.subTest(args=args):
                code, out, _ = run(*args)
                self.assertEqual(code, 2)
                self.assertEqual(out["status"], "rejected")

    def test_pdg_backend_without_the_package_exits_3(self):
        with tempfile.TemporaryDirectory() as d:
            Path(d, "pdg.py").write_text("raise ImportError('pdg hidden for this test')\n", encoding="utf-8")
            env = dict(os.environ, PYTHONPATH=d, PYTHONDONTWRITEBYTECODE="1")
            code, out, _ = run("particle", "proton", "--backend", "pdg", env=env)
        self.assertEqual(code, 3)
        self.assertEqual(out["status"], "missing-dependency")
        self.assertIn("pip install pdg", out["install"])

    def test_help_without_numpy(self):
        with tempfile.TemporaryDirectory() as d:
            Path(d, "numpy.py").write_text("raise ImportError('numpy hidden for this test')\n", encoding="utf-8")
            env = dict(os.environ, PYTHONPATH=d, PYTHONDONTWRITEBYTECODE="1")
            p = subprocess.run([sys.executable, "-B", str(SCRIPT), "--help"], capture_output=True, text=True,
                               timeout=600, env=env)
        self.assertEqual(p.returncode, 0)
        self.assertIn("qvalue", p.stdout)


if __name__ == "__main__":
    unittest.main()
