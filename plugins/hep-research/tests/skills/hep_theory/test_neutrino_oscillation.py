"""neutrino_oscillation.py (Th4): three-flavour oscillation probabilities in vacuum and in matter of constant
density, PMNS in the PDG convention (Review of Particle Physics 2026, Eqs. 14.33-14.34, 14.39-14.40, 14.53-14.58).
Oracles: the two-flavour analytic limit; the probabilities of every row and column sum to 1; zero density gives the
vacuum result of Eq. (14.39), computed independently here; the CPT relation P(a->b) = P(bbar->abar) in vacuum; the
two-flavour MSW mixing angle in constant matter; the matter potential sqrt(2) G_F n_e. Every parameter value below
is a SYNTHETIC input (the script has no built-in values)."""
import cmath
import json
import math
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[3]
SCRIPT = PLUGIN / "skills" / "hep-theory" / "scripts" / "neutrino_oscillation.py"
sys.path.insert(0, str(SCRIPT.parent))
sys.path.insert(0, str(PLUGIN))
import neutrino_oscillation as no  # noqa: E402

FLAVOURS = ("e", "mu", "tau")
PARAMS = dict(theta12=33.4, theta13=8.6, theta23=49.0, delta_cp=230.0, dm21=7.4e-5, dm31=2.5e-3)  # SYNTHETIC


def run(*args, env=None):
    p = subprocess.run([sys.executable, "-B", str(SCRIPT), *map(str, args)], capture_output=True, text=True,
                       timeout=600, env=env)
    return p.returncode, (json.loads(p.stdout) if p.stdout.strip().startswith("{") else p.stdout)


def vacuum_reference(theta12, theta13, theta23, delta_cp, dm21, dm31, L_km, E_gev, anti=False):
    """Eq. (14.39) with U of Eq. (14.34), written out independently of the script."""
    t12, t13, t23, d = (math.radians(x) for x in (theta12, theta13, theta23, delta_cp))
    s12, c12, s13, c13, s23, c23 = math.sin(t12), math.cos(t12), math.sin(t13), math.cos(t13), math.sin(t23), math.cos(t23)
    e = cmath.exp(1j * d)
    U = [[c12 * c13, s12 * c13, s13 / e],
         [-s12 * c23 - c12 * s13 * s23 * e, c12 * c23 - s12 * s13 * s23 * e, c13 * s23],
         [s12 * s23 - c12 * s13 * c23 * e, -c12 * s23 - s12 * s13 * c23 * e, c13 * c23]]
    if anti:
        U = [[x.conjugate() for x in row] for row in U]
    m2 = [0.0, dm21, dm31]
    k = no.phase_factor()  # Delta m^2 L / (4 E) per (eV^2 km / GeV), from the exact hbar c
    P = [[0.0] * 3 for _ in range(3)]
    for a in range(3):
        for b in range(3):
            p = 1.0 if a == b else 0.0
            for i in range(3):
                for j in range(i):
                    X = k * (m2[i] - m2[j]) * L_km / E_gev
                    q = U[a][i].conjugate() * U[b][i] * U[a][j] * U[b][j].conjugate()
                    p += -4 * q.real * math.sin(X) ** 2 + 2 * q.imag * math.sin(2 * X)
            P[a][b] = p
    return P


class Oscillations(unittest.TestCase):
    def prob(self, **kw):
        args = dict(PARAMS, L_km=1300.0, E_gev=2.5, density=0.0, ye=0.5, anti=False)
        args.update(kw)
        return no.probabilities(**args)["matrix"]

    def test_phase_factor_matches_the_pdg_number(self):
        self.assertAlmostEqual(no.phase_factor(), 1.267, delta=5e-4)  # Eq. (14.40): 1.267 eV^-2 MeV/m

    def test_two_flavour_limit(self):
        for L, E in ((295.0, 0.6), (1300.0, 2.5), (8000.0, 10.0)):
            P = self.prob(theta12=0.0, theta13=0.0, dm21=0.0, L_km=L, E_gev=E)
            X = no.phase_factor() * PARAMS["dm31"] * L / E
            want = math.sin(2 * math.radians(PARAMS["theta23"])) ** 2 * math.sin(X) ** 2
            self.assertAlmostEqual(P["mu"]["tau"], want, delta=1e-12)
            self.assertAlmostEqual(P["e"]["e"], 1.0, delta=1e-12)

    def test_unitarity(self):
        for dens in (0.0, 2.8, 11.0):
            for anti in (False, True):
                P = self.prob(density=dens, anti=anti)
                for a in FLAVOURS:
                    self.assertAlmostEqual(sum(P[a][b] for b in FLAVOURS), 1.0, delta=1e-12)
                    self.assertAlmostEqual(sum(P[b][a] for b in FLAVOURS), 1.0, delta=1e-12)
                    for b in FLAVOURS:
                        self.assertGreaterEqual(P[a][b], -1e-12)

    def test_zero_density_equals_the_vacuum_formula(self):
        for anti in (False, True):
            for L, E in ((295.0, 0.6), (1300.0, 2.5), (180.0, 0.004)):
                P = self.prob(density=0.0, anti=anti, L_km=L, E_gev=E)
                ref = vacuum_reference(**PARAMS, L_km=L, E_gev=E, anti=anti)
                for i, a in enumerate(FLAVOURS):
                    for j, b in enumerate(FLAVOURS):
                        self.assertAlmostEqual(P[a][b], ref[i][j], delta=1e-10)

    def test_cpt_in_vacuum(self):
        P, Pbar = self.prob(), self.prob(anti=True)
        for a in FLAVOURS:
            for b in FLAVOURS:
                self.assertAlmostEqual(P[a][b], Pbar[b][a], delta=1e-12)
        self.assertGreater(abs(P["mu"]["e"] - Pbar["mu"]["e"]), 1e-3)  # CP violation with delta_cp != 0, 180

    def test_two_flavour_msw_in_constant_matter(self):
        # e-mu two-flavour system (theta13 plays the role of the angle, theta12 = theta23 = 0, dm21 = 0)
        th, dm, E, L, rho, ye = 8.6, 2.5e-3, 5.0, 3000.0, 4.0, 0.5
        V = no.matter_potential_ev(rho, ye)
        A = 2 * E * 1e9 * V  # eV^2
        s2, c2 = math.sin(2 * math.radians(th)), math.cos(2 * math.radians(th))
        dm_m = math.hypot(dm * c2 - A, dm * s2)
        sin2_2thm = (dm * s2 / dm_m) ** 2
        want = sin2_2thm * math.sin(no.phase_factor() * dm_m * L / E) ** 2
        P = self.prob(theta12=0.0, theta23=0.0, theta13=th, dm21=0.0, dm31=dm, delta_cp=0.0, L_km=L, E_gev=E,
                      density=rho, ye=ye)
        self.assertAlmostEqual(P["e"]["tau"], want, delta=1e-9)  # theta23 = 0: the third state is nu_tau

    def test_matter_potential(self):
        # sqrt(2) G_F N_A Y_e rho (hbar c)^3 = 7.63e-14 eV for Y_e rho = 1 g/cm^3
        self.assertAlmostEqual(no.matter_potential_ev(1.0, 1.0) / 7.63e-14, 1.0, delta=2e-3)


class Cli(unittest.TestCase):
    BASE = ("--theta12", 33.4, "--theta13", 8.6, "--theta23", 49.0, "--delta-cp", 230.0, "--dm21", 7.4e-5,
            "--dm31", 2.5e-3, "--baseline-km", 1300, "--energy-gev", 2.5)

    def test_vacuum_and_conventions(self):
        code, out = run(*self.BASE, "--vacuum")
        self.assertEqual(code, 0, out)
        self.assertEqual(out["status"], "ok")
        self.assertEqual(out["status_label"], "unvalidated")
        conv = out["conventions"]
        for key in ("pmns", "units", "L_over_E", "neutrino", "density"):
            self.assertIn(key, conv)
        self.assertIn("14.34", conv["pmns"])
        self.assertEqual(conv["neutrino"], "neutrino")
        self.assertAlmostEqual(sum(out["probabilities"]["mu"].values()), 1.0, delta=1e-12)

    def test_matter_needs_density_and_electron_fraction(self):
        code, out = run(*self.BASE, "--density-g-cm3", 2.8, "--ye", 0.5, "--antineutrino")
        self.assertEqual(code, 0, out)
        self.assertEqual(out["conventions"]["neutrino"], "antineutrino")
        code, out = run(*self.BASE, "--density-g-cm3", 2.8)  # no Y_e: no default
        self.assertEqual(code, 2)
        self.assertEqual(out["status"], "rejected")

    def test_no_built_in_parameters(self):
        code, out = run("--baseline-km", 1300, "--energy-gev", 2.5, "--vacuum")
        self.assertEqual(code, 2)
        self.assertEqual(out["status"], "rejected")

    def test_bad_values(self):
        for extra in (("--vacuum", "--energy-gev", -1), ("--density-g-cm3", -2, "--ye", 0.5)):
            with self.subTest(extra=extra):
                code, out = run(*self.BASE, *extra)
                self.assertEqual(code, 2, out)

    def test_help_without_numpy(self):
        with tempfile.TemporaryDirectory() as d:
            Path(d, "numpy.py").write_text("raise ImportError('hidden for this test')\n", encoding="utf-8")
            env = dict(os.environ, PYTHONPATH=d, PYTHONDONTWRITEBYTECODE="1")
            code, out = run("--help", env=env)
            self.assertEqual(code, 0)
            code, out = run(*self.BASE, "--vacuum", env=env)
            self.assertEqual(code, 3)
            self.assertEqual(out["status"], "missing-dependency")


if __name__ == "__main__":
    unittest.main()
