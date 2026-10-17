"""secondary_gamma.py (Th11): pi0 -> gamma gamma from a pion spectrum, averaged neutrino flavour ratios, and head-on
reaction thresholds on a target photon. Oracles: a mono-energetic pion gives a box between E+- = (E_pi +- p_pi)/2 of
height 2/p_pi; dN/dE_gamma is symmetric under E -> m_pi^2 / (4E) (symmetric in log E about m_pi/2); two photons per
pion; a 1:2:0 source with tribimaximal-like mixing gives 1:1:1; the gamma-gamma threshold E = m_e^2 / eps; the
invariant mass at a threshold equals the sum of the final masses (core/kinematics/fourvector.py). SYNTHETIC inputs."""
import json
import math
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[3]
SCRIPT = PLUGIN / "skills" / "hep-theory" / "scripts" / "secondary_gamma.py"
sys.path.insert(0, str(SCRIPT.parent))
sys.path.insert(0, str(PLUGIN))
from core.kinematics import fourvector as fv  # noqa: E402

M_PI = 0.1349768  # GeV, PDG 2026 (the script reads it from core/constants)


def run(*args):
    p = subprocess.run([sys.executable, "-B", str(SCRIPT), *args], capture_output=True, text=True, timeout=600)
    return p.returncode, (json.loads(p.stdout) if p.stdout.strip().startswith("{") else p.stdout)


class Pi0Photons(unittest.TestCase):
    def setUp(self):
        import secondary_gamma as m
        self.m = m

    def test_monoenergetic_box(self):
        e = 5.0
        p = math.sqrt(e * e - M_PI * M_PI)
        lo, hi = (e - p) / 2, (e + p) / 2
        code, out = run("pi0", "--monoenergetic-gev", str(e), "--e-gamma-gev", str(lo * 1.01), str(hi * 0.99),
                        str(hi * 1.01))
        self.assertEqual(code, 0, out)
        vals = [r["dn_de_gamma"] for r in out["rows"]]
        self.assertAlmostEqual(vals[0], 2 / p, delta=1e-9)
        self.assertAlmostEqual(vals[1], 2 / p, delta=1e-9)
        self.assertEqual(vals[2], 0.0)
        self.assertAlmostEqual(out["box"]["e_minus_gev"], lo, delta=1e-12)

    def test_symmetry_and_photon_count_for_a_power_law(self):
        es = [10 ** (i / 20) for i in range(0, 61)]  # 1 to 1000 GeV
        dn = [x ** -2.7 for x in es]
        spec = {"e_gev": es, "dn_de": dn}
        for e in (0.03, 0.2, 2.0):
            with self.subTest(E=e):
                a = self.m.gamma_spectrum(spec, e, M_PI)
                b = self.m.gamma_spectrum(spec, M_PI ** 2 / (4 * e), M_PI)
                self.assertAlmostEqual(a / b, 1.0, delta=1e-9)
        grid = [10 ** (-6 + i / 200) for i in range(0, 1801)]  # 1e-6 to 1e3 GeV
        g = [self.m.gamma_spectrum(spec, x, M_PI) for x in grid]
        photons = sum(0.5 * (g[i] + g[i + 1]) * (grid[i + 1] - grid[i]) for i in range(len(grid) - 1))
        pions = (1 - 1000 ** -1.7) / 1.7
        self.assertAlmostEqual(photons / (2 * pions), 1.0, delta=2e-3)

    def test_cli_spectrum_file(self):
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "pi.json"
            f.write_text(json.dumps({"e_gev": [1, 10, 100], "dn_de": [1.0, 10 ** -2.7, 10 ** -5.4]}),
                         encoding="utf-8")
            code, out = run("pi0", "--spectrum", str(f), "--e-gamma-gev", "0.5", "5")
        self.assertEqual(code, 0, out)
        self.assertTrue(all(r["dn_de_gamma"] > 0 for r in out["rows"]))
        self.assertEqual(out["pi0_mass"]["edition"], "PDG 2026")


class FlavourAndThresholds(unittest.TestCase):
    def test_tribimaximal_gives_equal_flavours(self):
        code, out = run("flavour", "--theta12", str(math.degrees(math.asin(math.sqrt(1 / 3)))), "--theta13", "0",
                        "--theta23", "45", "--delta-cp", "0", "--source", "1:2:0")
        self.assertEqual(code, 0, out)
        for x in out["earth_fractions"]:
            self.assertAlmostEqual(x, 1 / 3, delta=1e-12)

    def test_flux_is_conserved(self):
        code, out = run("flavour", "--theta12", "33", "--theta13", "8.6", "--theta23", "49", "--delta-cp", "200",
                        "--source", "1:0:0")
        self.assertEqual(code, 0, out)
        self.assertAlmostEqual(sum(out["earth_fractions"]), 1.0, delta=1e-12)

    def test_gamma_gamma_threshold(self):
        eps_ev = 1e-3
        code, out = run("threshold", "--target-photon-ev", str(eps_ev), "--process", "pair")
        self.assertEqual(code, 0, out)
        me = 0.51099895069e-3
        self.assertAlmostEqual(out["threshold_gev"] / (me * me / (eps_ev * 1e-9)), 1.0, delta=1e-12)

    def test_photopion_threshold_invariant_mass(self):
        # a hard target photon (0.1 GeV): the threshold four-vectors are precise in core/kinematics/fourvector.py
        code, out = run("threshold", "--target-photon-ev", "1e8", "--process", "photopion")
        self.assertEqual(code, 0, out)
        e, mp = out["threshold_gev"], out["masses_gev"]["projectile"]
        pp = math.sqrt(e * e - mp * mp)
        m = fv.invariant_mass((e, 0.0, 0.0, pp), (0.1, 0.0, 0.0, -0.1))
        self.assertAlmostEqual(m / out["masses_gev"]["final_sum"], 1.0, delta=1e-12)
        # a CMB-like photon (6.3e-4 eV): the threshold is ~1e20 eV and the stable check holds
        code, out = run("threshold", "--target-photon-ev", "6.3e-4", "--process", "photopion")
        self.assertEqual(code, 0, out)
        self.assertAlmostEqual(out["invariant_mass_check_gev"] / out["masses_gev"]["final_sum"], 1.0, delta=1e-12)
        self.assertTrue(1e10 < out["threshold_gev"] < 1e12)

    def test_bad_input(self):
        for args in (("flavour", "--theta12", "33", "--theta13", "8", "--theta23", "45", "--delta-cp", "0",
                      "--source", "1:2"),
                     ("threshold", "--target-photon-ev", "-1", "--process", "pair"),
                     ("pi0", "--monoenergetic-gev", "0.1", "--e-gamma-gev", "0.05")):
            with self.subTest(args=args):
                code, out = run(*args)
                self.assertEqual(code, 2, out)


if __name__ == "__main__":
    unittest.main()
