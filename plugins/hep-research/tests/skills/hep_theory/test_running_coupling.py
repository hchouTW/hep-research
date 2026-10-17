"""running_coupling.py (Th10): alpha_s running at 1-4 loops in MS-bar with flavour-threshold matching (PDG Review 2026,
QCD, Eqs. 9.3-9.4; beta_3 from van Ritbergen, Vermaseren and Larin, Phys. Lett. B 400 (1997) 379, Eq. 11).
Oracles: the beta coefficients equal the PDG closed forms and the paper's numerical form; numerical one-loop running
equals the closed form; running from m_Z down and back up returns the input; the matching at mu = m_h; the stop
where alpha_s > 0.5. Every input value below is SYNTHETIC."""
import json
import math
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[3]
SCRIPT = PLUGIN / "skills" / "hep-theory" / "scripts" / "running_coupling.py"
sys.path.insert(0, str(SCRIPT.parent))
sys.path.insert(0, str(PLUGIN))
import running_coupling as rc  # noqa: E402

THRESHOLDS = {"c": 1.27, "b": 4.18, "t": 162.5}  # SYNTHETIC MS-bar masses, GeV


def run(*args, env=None):
    p = subprocess.run([sys.executable, "-B", str(SCRIPT), *map(str, args)], capture_output=True, text=True,
                       timeout=600, env=env)
    return p.returncode, (json.loads(p.stdout) if p.stdout.strip().startswith("{") else p.stdout)


class Coefficients(unittest.TestCase):
    def test_pdg_closed_forms(self):
        for nf in range(0, 7):
            b = rc.beta_coefficients(nf, 4)
            self.assertAlmostEqual(b[0], (33 - 2 * nf) / (12 * math.pi), delta=1e-15)
            self.assertAlmostEqual(b[1], (153 - 19 * nf) / (24 * math.pi ** 2), delta=1e-15)
            self.assertAlmostEqual(b[2], (2857 - 5033 / 9 * nf + 325 / 27 * nf ** 2) / (128 * math.pi ** 3), delta=1e-14)

    def test_beta3_numerical_form_of_the_paper(self):
        for nf in (3, 4, 5, 6):
            b3 = rc.beta_coefficients(nf, 4)[3] * (4 * math.pi) ** 4
            want = 29243.0 - 6946.30 * nf + 405.089 * nf ** 2 + 1.49931 * nf ** 3  # Eq. (12), rounded
            self.assertAlmostEqual(b3 / want, 1.0, delta=2e-5)

    def test_loops_out_of_range(self):
        with self.assertRaises(rc.CouplingError):
            rc.beta_coefficients(5, 5)


class Running(unittest.TestCase):
    def test_one_loop_numerical_equals_closed_form(self):
        a0, mu0 = 0.118, 91.0
        for mu in (10.0, 50.0, 500.0, 5000.0):
            got = rc.run_fixed_nf(a0, mu0, mu, nf=5, loops=1)
            want = a0 / (1 + rc.beta_coefficients(5, 1)[0] * a0 * math.log(mu ** 2 / mu0 ** 2))
            self.assertAlmostEqual(got, want, delta=1e-12)

    def test_round_trip_through_thresholds(self):
        for loops in (1, 2, 3, 4):
            r = rc.evolve(0.118, 91.0, [1.777], loops=loops, thresholds=THRESHOLDS, scheme="msbar")
            down = r["points"][0]
            self.assertEqual(down["nf"], 4)  # m_tau lies above the charm threshold
            back = rc.evolve(down["alpha_s"], 1.777, [91.0], loops=loops, thresholds=THRESHOLDS, scheme="msbar",
                             nf_start=4)
            self.assertAlmostEqual(back["points"][0]["alpha_s"], 0.118, delta=1e-10)
            self.assertEqual(back["points"][0]["nf"], 5)

    def test_matching_at_the_threshold(self):
        # at mu = m_h with an MS-bar mass, alpha(nf+1) = alpha(nf) (1 + c20 alpha^2), c20 = -11/(72 pi^2)
        a4 = 0.2
        a5 = rc.match(a4, mu=4.18, m_h=4.18, up=True, order=2, scheme="msbar")
        self.assertAlmostEqual(a5, a4 * (1 - 11 / (72 * math.pi ** 2) * a4 ** 2), delta=1e-15)
        self.assertAlmostEqual(rc.match(a5, mu=4.18, m_h=4.18, up=False, order=2, scheme="msbar"), a4, delta=1e-14)
        pole = rc.match(a4, mu=4.18, m_h=4.18, up=True, order=2, scheme="pole")
        self.assertAlmostEqual(pole, a4 * (1 + 7 / (24 * math.pi ** 2) * a4 ** 2), delta=1e-15)

    def test_running_decreases_upward(self):
        r = rc.evolve(0.118, 91.0, [10.0, 91.0, 1000.0], loops=4, thresholds=THRESHOLDS, scheme="msbar")
        a = [p["alpha_s"] for p in r["points"]]
        self.assertGreater(a[0], a[1])
        self.assertGreater(a[1], a[2])
        self.assertAlmostEqual(a[1], 0.118, delta=1e-12)

    def test_stops_above_one_half(self):
        r = rc.evolve(0.118, 91.0, [5.0, 0.6], loops=4, thresholds=THRESHOLDS, scheme="msbar")
        self.assertEqual(r["status"], "incomplete")
        self.assertEqual(len(r["points"]), 1)
        self.assertIn("0.5", r["stopped"])


class Cli(unittest.TestCase):
    BASE = ("--alphas-mz", 0.118, "--alphas-source", "SYNTHETIC test input", "--mz", 91.0, "--loops", 4,
            "--mc", 1.27, "--mb", 4.18, "--mt", 162.5, "--mass-scheme", "msbar")

    def test_run_to_scales(self):
        code, out = run(*self.BASE, "--to", 1.777, 10, 1000)
        self.assertEqual(code, 0, out)
        self.assertEqual(out["status"], "ok")
        self.assertEqual([p["nf"] for p in out["points"]], [4, 5, 6])
        self.assertEqual(out["inputs"]["alphas_source"], "SYNTHETIC test input")
        self.assertIn("matching", out["conventions"])

    def test_default_mz_comes_from_core_constants_with_its_edition(self):
        args = [a for a in self.BASE]
        i = args.index("--mz")
        del args[i:i + 2]
        code, out = run(*args, "--to", 10)
        self.assertEqual(code, 0, out)
        self.assertIn("mz", out["defaults_used"])
        self.assertEqual(out["mz"]["edition"], "PDG 2026")

    def test_stop_exits_3(self):
        code, out = run(*self.BASE, "--to", 0.6)
        self.assertEqual(code, 3, out)
        self.assertEqual(out["status"], "incomplete")
        self.assertTrue(out["warnings"])

    def test_bad_input_exits_2(self):
        for extra in (("--to", -1), ("--to", 10, "--loops", 7)):
            with self.subTest(extra=extra):
                code, out = run(*self.BASE, *extra)
                self.assertEqual(code, 2, out)
        code, out = run("--alphas-mz", 0.118, "--to", 10)  # no source, loops, thresholds
        self.assertEqual(code, 2)

    def test_help_without_numpy(self):
        with tempfile.TemporaryDirectory() as d:
            Path(d, "numpy.py").write_text("raise ImportError('hidden for this test')\n", encoding="utf-8")
            env = dict(os.environ, PYTHONPATH=d, PYTHONDONTWRITEBYTECODE="1")
            code, _ = run("--help", env=env)
            self.assertEqual(code, 0)
            code, out = run(*self.BASE, "--to", 10, env=env)  # standard library only: still runs
            self.assertEqual(code, 0, out)


if __name__ == "__main__":
    unittest.main()
