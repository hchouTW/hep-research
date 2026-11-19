"""CHK-AT-09-02 evidence: the Highland reference of the multiple-scattering sanity benchmark is evaluated at the
benchmark's particle and energy.

geant4_benchmarks.py's multiple-scattering benchmark runs multiple_scattering.py on its highland_stack; before the fix it
passed only the stack path, so Highland was evaluated at that tool's defaults (rigidity 100 GV, beta 1, charge 1)
whatever the benchmark's particle and energy_MeV (for a 1 GeV kinetic-energy proton the reference was 68 times too
small).

Oracle (no expected value comes from the module under test, and none imports it to compute one): RPP eq. (34.16)
(PDG RPP 2024, sec. 34.3, p. 16; the ledger's scifix:S01, claim scifix:C04), transcribed here,
    theta0 = 13.6 MeV / (beta c p) z sqrt(x/X0) [1 + 0.038 ln(x z^2 / (X0 beta^2))],
"p, beta c and z are the momentum, speed and charge number of the incident particle", with x/X0 the stack's summed
material and the particle's p and beta from its kinetic energy T and mass m: E = T + m, p = sqrt(T (T + 2 m)),
beta = p / E. Masses are CODATA 2022 (e, mu, p, d, alpha) and PDG (pi), transcribed. Two records:
- analytic: the issue's case, a proton of T = 1000 MeV;
- exhaustive: every particle name the benchmark accepts (e-, e+, mu-, mu+, pi+, pi-, proton, deuteron, alpha) at
  T = 10, 1000 and 100000 MeV (27 cases).
Negative control: the pre-fix evaluation (100 GV, beta 1, z 1), emulated here with the same formula, misses the
proton case by far more than the tolerance. Invariant: the sign of the charge does not change the reference.

Tolerance, fixed before the first run and never widened: TOL_RELATIVE = 1e-9 on the reference. The code and the oracle
evaluate the same closed form in double precision; they differ only in the order of the operations and in the
decimal round trip of the rigidity and mass through multiple_scattering.py's command line (repr, exact), so their
difference is a few 1e-16; 1e-9 leaves margin and rejects any change in the kinematics (the defect is a factor up to
68, and 1e-3 for a 100 GeV muon, the case that was right by coincidence). All inputs are SYNTHETIC.
"""
import json
import math
import statistics
import sys
import tempfile
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PLUGIN))
sys.path.insert(0, str(PLUGIN / "skills" / "hep-detector" / "scripts"))
import geant4_benchmarks as G  # noqa: E402

TOL_RELATIVE = 1e-9
# (mass in MeV, charge number): CODATA 2022 mass energy equivalents; pi+- from PDG (139.57039 MeV)
PARTICLES = {"e-": (0.51099895069, -1), "e+": (0.51099895069, 1), "mu-": (105.6583755, -1), "mu+": (105.6583755, 1),
             "pi+": (139.57039, 1), "pi-": (139.57039, -1), "proton": (938.27208943, 1),
             "deuteron": (1875.612945, 1), "alpha": (3727.3794118, 2)}
ENERGIES_MEV = (10.0, 1000.0, 100000.0)
LAYERS = [{"name": f"plane{i}", "x_over_x0": 0.0032, "measuring": True} for i in range(3)]
STACK = {"status": "synthetic", "name": "three 0.3 mm silicon planes (SYNTHETIC)", "field_tesla": 1.0,
         "lever_arm_m": 1.0, "point_resolution_um": 10.0, "layers": LAYERS}


def highland(p_mev: float, beta: float, z: int, x_over_x0: float) -> float:
    """RPP eq. (34.16), radians."""
    return 13.6 / (beta * p_mev) * abs(z) * math.sqrt(x_over_x0) * (1 + 0.038 * math.log(x_over_x0 * z * z / beta ** 2))


def expected(particle: str, t_mev: float) -> float:
    m, z = PARTICLES[particle]
    p = math.sqrt(t_mev * (t_mev + 2 * m))
    return highland(p, p / (t_mev + m), z, math.fsum(layer["x_over_x0"] for layer in LAYERS))


def rows(n: int = 400) -> list[dict]:
    nd = statistics.NormalDist(0.0, 1e-3)
    return [{"primary.fate": 1, "primary.end_process": "Transportation", "primary.exit_direction.x": 1.0,
             "primary.exit_direction.y": math.tan(nd.inv_cdf((i + 0.5) / n)),
             "primary.exit_direction.z": math.tan(nd.inv_cdf((n - i - 0.5) / n))} for i in range(n)]


class HighlandAtTheBenchmarkKinematics(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._t = tempfile.TemporaryDirectory()
        cls.d = Path(cls._t.name)
        (cls.d / "stack.json").write_text(json.dumps(STACK), encoding="utf-8")
        cls.rows = rows()

    @classmethod
    def tearDownClass(cls):
        cls._t.cleanup()

    def reference(self, particle: str, t_mev: float) -> float:
        b = {"benchmark": "multiple-scattering", "csv": "unused.csv", "particle": particle, "energy_MeV": t_mev,
             "highland_stack": "stack.json"}
        return G.bench_ms(b, self.rows, {}, self.d)["reference_value"]

    def test_proton_of_1_gev_kinetic_energy(self):
        want = expected("proton", 1000.0)
        self.assertAlmostEqual(want, 7.485e-4, delta=0.001e-4)  # p = 1696 MeV/c, beta = 0.875, x/X0 = 0.0096
        got = self.reference("proton", 1000.0)
        self.assertLess(abs(got / want - 1), TOL_RELATIVE, (got, want))

    def test_every_known_particle_and_energy(self):
        for particle in PARTICLES:
            for t in ENERGIES_MEV:
                with self.subTest(particle=particle, T=t):
                    got, want = self.reference(particle, t), expected(particle, t)
                    self.assertLess(abs(got / want - 1), TOL_RELATIVE, (got, want))

    def test_the_sign_of_the_charge_does_not_change_the_reference(self):
        for a, b in (("mu-", "mu+"), ("pi-", "pi+"), ("e-", "e+")):
            with self.subTest(pair=(a, b)):
                ra, rb = self.reference(a, 1000.0), self.reference(b, 1000.0)
                self.assertLess(abs(ra / rb - 1), 1e-12)

    def test_pre_fix_default_kinematics_miss_the_proton(self):
        """Negative control, emulating the pre-fix evaluation in the test: Highland at 100 GV, beta 1, z 1."""
        x = math.fsum(layer["x_over_x0"] for layer in LAYERS)
        pre_fix = highland(100000.0, 1.0, 1, x)
        self.assertGreater(abs(pre_fix / expected("proton", 1000.0) - 1), 0.9)
        self.assertGreater(abs(pre_fix / expected("mu-", 100000.0) - 1), 100 * TOL_RELATIVE)


if __name__ == "__main__":
    unittest.main()
