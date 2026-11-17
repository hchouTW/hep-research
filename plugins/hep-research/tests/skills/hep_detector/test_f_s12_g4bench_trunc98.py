"""CHK-AT-09-01 evidence: the Gaussian truncation factor of the multiple-scattering sanity benchmark.

geant4_benchmarks.py's multiple-scattering benchmark estimates the core width of the projected exit angle as the RMS of
the central 98 % of the angles divided by TRUNC_98, the RMS of a unit Gaussian truncated to its central 98 %. For a
Gaussian of width sigma that RMS is sigma * sqrt(1 - 2 z phi(z) / (2 Phi(z) - 1)) with z = Phi^-1(0.99), 0.93459
sigma; 0.8673 (the factor before the fix) is close to the truncated variance 0.87346, not to its square root, and
makes the estimate 7.8 % high for exactly Gaussian angles.

Oracles (no expected value comes from the module under test, and none imports it to compute one):
- symbolic (SymPy): the second moment of N(0, 1) over [-z, z] divided by its probability content, integrated by SymPy
  from the definition, with z = sqrt(2) erfinv(0.98) (the 1 % and 99 % quantiles), evaluated to 30 digits.
- independent implementation (Python's statistics.NormalDist): angles placed at the exact normal quantiles
  sigma * Phi^-1((i + 1/2) / N), so the central 98 % of the sample is the central 98 % of the distribution by
  construction; a correct core-width estimator returns sigma.
Negative control: the pre-fix estimator, RMS(central 98 %) / 0.8673, emulated here on the same angles, misses sigma by
more than the oracle tolerance. Invariant: the estimate scales with the angles.

Tolerances, fixed before the first run and never widened:
- TOL_SYMBOLIC = 1e-9 absolute on the factor: SymPy evaluates to 30 digits and a double carries about 16; the factor
  in the code may be written to more digits than 9 or computed, so 1e-9 accepts any double-precision evaluation and
  rejects every value that differs in the 9th digit (the defect is 0.067).
- TOL_QUANTILE = 1e-4 relative on the core width: the quantile sample is a midpoint rule in probability over
  [0.01, 0.99] with N = 20000 points (step 5e-5, cut exactly at 200 points per side); its error is O(step^2) times the
  second derivative of Phi^-1(p)^2 on the window, below 1e-6 relative; tan and atan2 round trips add about 1e-16. The
  defect is 7.8 %.
All inputs are SYNTHETIC.
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

TOL_SYMBOLIC = 1e-9
TOL_QUANTILE = 1e-4
PRE_FIX_FACTOR = 0.8673  # the factor before the fix, for the negative control only
N_EVENTS = 20000
STACK = {"status": "synthetic", "name": "three 0.3 mm silicon planes (SYNTHETIC)", "field_tesla": 1.0,
         "lever_arm_m": 1.0, "point_resolution_um": 10.0,
         "layers": [{"name": f"plane{i}", "x_over_x0": 0.0032, "measuring": True} for i in range(3)]}


def symbolic_truncated_rms() -> float:
    """sqrt(E[x^2 | |x| <= z]) for x ~ N(0, 1), z the 99 % quantile, by SymPy from the definition."""
    import sympy as sp
    x = sp.symbols("x", real=True)
    z = sp.sqrt(2) * sp.erfinv(sp.Rational(49, 50))
    density = sp.exp(-x ** 2 / 2)
    second = sp.integrate(x ** 2 * density, (x, -z, z))
    mass = sp.integrate(density, (x, -z, z))
    return float(sp.sqrt(second / mass).evalf(30))


def quantile_angles(sigma: float, n: int = N_EVENTS) -> list[float]:
    nd = statistics.NormalDist(0.0, sigma)
    return [nd.inv_cdf((i + 0.5) / n) for i in range(n)]


def rows_for(angles_y: list[float], angles_z: list[float]) -> list[dict]:
    """Per-event rows in the benchmark's semantic columns: transmitted primaries with the given projected angles."""
    return [{"primary.fate": 1, "primary.end_process": "Transportation", "primary.exit_direction.x": 1.0,
             "primary.exit_direction.y": math.tan(ay), "primary.exit_direction.z": math.tan(az)}
            for ay, az in zip(angles_y, angles_z)]


class _Bench(unittest.TestCase):
    def setUp(self):
        self._t = tempfile.TemporaryDirectory()
        self.d = Path(self._t.name)
        (self.d / "stack.json").write_text(json.dumps(STACK), encoding="utf-8")

    def tearDown(self):
        self._t.cleanup()

    def core_width(self, sigma: float) -> float:
        a = quantile_angles(sigma)
        b = {"benchmark": "multiple-scattering", "csv": "unused.csv", "particle": "mu-", "energy_MeV": 100000.0,
             "highland_stack": "stack.json"}
        return G.bench_ms(b, rows_for(a, list(reversed(a))), {}, self.d)["geant4"]


class TruncationFactor(unittest.TestCase):
    def test_factor_is_the_rms_of_the_central_98_percent_of_a_unit_gaussian(self):
        expected = symbolic_truncated_rms()
        self.assertAlmostEqual(expected, 0.93459, delta=1e-5)  # the value the issue quotes, to its 5 digits
        self.assertLess(abs(G.TRUNC_98 - expected), TOL_SYMBOLIC, (G.TRUNC_98, expected))


class GaussianCoreWidth(_Bench):
    SIGMA = 1.0e-3

    def test_bench_ms_recovers_the_width_of_gaussian_quantile_angles(self):
        got = self.core_width(self.SIGMA)
        self.assertLess(abs(got / self.SIGMA - 1), TOL_QUANTILE, got)

    def test_core_width_scales_with_the_angles(self):
        """Invariant: doubling every angle doubles the estimate (both projections, same events)."""
        one, two = self.core_width(self.SIGMA), self.core_width(2 * self.SIGMA)
        self.assertLess(abs(two / one - 2), 1e-12 * 2)

    def test_pre_fix_factor_misses_the_width(self):
        """Negative control, emulating the pre-fix estimator in the test: RMS(central 98 %) / 0.8673 on the same
        quantile angles is about 7.8 % high, far outside TOL_QUANTILE; the oracle discriminates the defect."""
        a = sorted(quantile_angles(self.SIGMA) * 2)
        cut = int(0.01 * len(a))
        core = a[cut:len(a) - cut]
        rms = math.sqrt(math.fsum(x * x for x in core) / len(core))
        pre_fix = rms / PRE_FIX_FACTOR
        self.assertGreater(abs(pre_fix / self.SIGMA - 1), 100 * TOL_QUANTILE)
        self.assertAlmostEqual(pre_fix / self.SIGMA - 1, 0.0776, delta=0.002)  # 0.93459 / 0.8673 - 1


if __name__ == "__main__":
    unittest.main()
