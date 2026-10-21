"""anisotropy.py, sci-fix ANISO-WEIGHTED-COV (S1): with an exposure map, the null covariance of the weighted harmonic
components (a, b) is computed from the binned map instead of (2/N_eff) I, the Rayleigh probability is exp(-chi^2 / 2)
with chi^2 = v^T V^-1 v, and the amplitude upper limit holds for any dipole phase under that covariance.

Oracles (docs/maintenance.md, oracle rules; none imports the module to compute an expected value):
- symbolic (third-party): SymPy derives N Cov(a, b) from the definition a = 2 sum(w cos) / sum(w), b likewise, by the
  delta method (moments integrated by SymPy, gradients by sympy.diff) for the exposure 1 + (9/10) cos(alpha);
- independent implementation (third-party): scipy.stats.multivariate_normal integrated over the disk by
  scipy.integrate.dblquad (the CDF of r, the Neyman condition at the reported limit, the null median),
  scipy.stats.chi2.sf (the significance) and scipy.stats.ncx2 (the isotropic Rice case).
Invariants: a uniform map reproduces the unweighted outputs bit for bit; toy skies have the reported covariance; the
new acceptance region and limit cover at four dipole phases (fast: Gaussian toys; slow: event-level toys).
Negative controls emulate the pre-fix 2/N_eff behaviour inside the test and show that it fails the same oracles.

Tolerances, fixed before the first run:
- binning: the map has 3600 bins of the bin-averaged 1 + 0.9 cos(alpha). Replacing 1/rho by 1/<rho> in a bin errs by
  about Var_bin(rho) / rho^2 <= (0.9 dx)^2 / 12 / rho^2 relative; rho' = -0.9 sin(alpha) vanishes where rho is
  smallest, and the bound over the circle is below 2.1e-5. Variances are compared at 1e-4 relative, chi^2 at 1e-4
  relative, the null median at 1e-4 relative, the CDF at the reported limit at 1e-4 absolute;
- quadrature: dblquad at epsabs 1e-12, epsrel 1e-10, and the script's trapezoid converges exponentially, so CDF
  values with the same covariance are compared at 1e-8 absolute;
- the phase grid: a 5 deg step misses a smooth maximum by about (step / 2)^2 x curvature ~ 2e-4; the continuous
  maximum over the phase may exceed the grid maximum by at most 2e-3;
- Monte Carlo: toy variances within 4 standard errors (sqrt(2 / M) relative), coverage at least CL minus 3 binomial
  standard errors, all with fixed seeds.
SYNTHETIC inputs only."""
import json
import math
import os
import random
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "skills" / "hep-measurement" / "scripts" / "anisotropy.py"
sys.path.insert(0, str(SCRIPT.parent))
SLOW = os.environ.get("HEP_SLOW_TESTS") == "1"
E = 0.9  # relative exposure 1 + E cos(alpha - axis)
AXIS = 30.0  # the exposure axis (deg) of the correlated cases
NBINS = 3600
BIN_RTOL = 1e-4
QUAD_ATOL = 1e-8


def import_mod():
    import anisotropy
    return anisotropy


def binned_map(nbins=NBINS, e=E, axis_deg=0.0):
    """Edges in degrees and the bin average of 1 + e cos(alpha - axis), normalised to mean 1."""
    edges = [360.0 * i / nbins for i in range(nbins + 1)]
    rel = []
    for lo, hi in zip(edges, edges[1:]):
        x0, x1 = math.radians(lo - axis_deg), math.radians(hi - axis_deg)
        rel.append(1.0 + e * (math.sin(x1) - math.sin(x0)) / (x1 - x0))
    mean = math.fsum(rel) / nbins
    return edges, [r / mean for r in rel]


_SYMPY_CACHE = {}


def sympy_per_event_covariance(e_num=9, e_den=10, axis_deg=0):
    """N Cov(a, b) for the weighted harmonic under isotropy seen through the exposure 1 + e cos(alpha - axis), from
    the definition by the delta method: per event X = w cos(alpha), S = w sin(alpha), Y = w with w = 1 / exposure and
    alpha distributed as the exposure; a = 2 mean(X) / mean(Y), b = 2 mean(S) / mean(Y). SymPy integrates the moments
    (in beta = alpha - axis, over a full period) and differentiates the ratio estimator."""
    key = (e_num, e_den, axis_deg)
    if key in _SYMPY_CACHE:
        return _SYMPY_CACHE[key]
    import sympy as sp
    beta = sp.symbols("beta", real=True)
    al = sp.symbols("alpha", real=True)
    e = sp.Rational(e_num, e_den)
    rho = 1 + e * sp.cos(beta)
    norm = sp.integrate(rho, (beta, 0, 2 * sp.pi))
    shift = sp.pi * sp.Rational(axis_deg, 180)

    def expect(g, k):
        """E[g(alpha) w^k] = int g rho^(1 - k) / norm."""
        num = sp.expand(sp.expand_trig(g.subs(al, beta + shift)))
        return sp.simplify(sp.integrate(num * rho ** (1 - k), (beta, 0, 2 * sp.pi)) / norm)

    trig = [sp.cos(al), sp.sin(al), sp.Integer(1)]  # X, S, Y = w times these
    mu = [expect(g, 1) for g in trig]
    sigma = sp.Matrix(3, 3, lambda i, j: expect(trig[i] * trig[j], 2) - mu[i] * mu[j])
    xs, ss, ys = sp.symbols("X S Y")
    est = sp.Matrix([2 * xs / ys, 2 * ss / ys])
    jac = est.jacobian([xs, ss, ys]).subs({xs: mu[0], ss: mu[1], ys: mu[2]})
    m = sp.simplify(jac * sigma * jac.T)
    out = [[float(m[0, 0]), float(m[0, 1])], [float(m[1, 0]), float(m[1, 1])]], m
    _SYMPY_CACHE[key] = out
    return out


def scipy_disk_cdf(x, mean, cov):
    """P(|mu + eps| <= x), eps ~ N(0, cov): scipy's bivariate normal density integrated over the disk (polar)."""
    from scipy import integrate, stats
    mvn = stats.multivariate_normal(mean, cov)
    val, _ = integrate.dblquad(lambda r, t: r * mvn.pdf([r * math.cos(t), r * math.sin(t)]), 0.0, 2.0 * math.pi,
                               0.0, x, epsabs=1e-12, epsrel=1e-10)
    return val


def harmonic_from_events(ras, weights):
    """a and b computed here, independently of the module."""
    w_tot = math.fsum(weights)
    a = 2.0 / w_tot * math.fsum(w * math.cos(math.radians(r)) for w, r in zip(weights, ras))
    b = 2.0 / w_tot * math.fsum(w * math.sin(math.radians(r)) for w, r in zip(weights, ras))
    return a, b, w_tot * w_tot / math.fsum(w * w for w in weights)


def sample_sky(rng, edges, rel, n, d=0.0, phase_deg=0.0):
    """Right ascensions seen through the binned exposure from the sky 1 + d cos(alpha - phase), and the weights."""
    width = edges[1] - edges[0]
    top = max(rel) * (1.0 + abs(d))
    ras, weights = [], []
    while len(ras) < n:
        a = 360.0 * rng.random()
        i = min(int(a / width), len(rel) - 1)
        if rng.random() * top <= rel[i] * (1.0 + d * math.cos(math.radians(a - phase_deg))):
            ras.append(a)
            weights.append(1.0 / rel[i])
    return ras, weights


def run(*args):
    p = subprocess.run([sys.executable, "-B", str(SCRIPT), *map(str, args)], capture_output=True, text=True,
                       timeout=600)
    return p.returncode, (json.loads(p.stdout) if p.stdout.strip().startswith("{") else None), p.stderr


def run_harmonic(ras, edges=None, rel=None, cl=0.95):
    with tempfile.TemporaryDirectory() as d:
        ev = Path(d) / "events.csv"
        ev.write_text("ra_deg\n" + "".join(f"{a!r}\n" for a in ras), encoding="utf-8")
        args = ["harmonic", "--events", ev, "--cl", cl]
        if edges is not None:
            emap = Path(d) / "map.json"
            emap.write_text(json.dumps({"ra_edges_deg": edges, "relative_exposure": rel}), encoding="utf-8")
            args += ["--exposure-map", emap]
        code, out, err = run(*args)
    if code != 0:
        raise AssertionError(f"exit {code}: {err}")
    return out


class Covariance(unittest.TestCase):
    def test_covariance_matches_the_sympy_delta_method(self):
        """Symbolic oracle: N Cov(a, b) from the definition (SymPy) against harmonic_covariance on the binned map."""
        an = import_mod()
        expected, exact = sympy_per_event_covariance()
        import sympy as sp
        e = sp.Rational(9, 10)
        # the closed form quoted in the reference, checked symbolically against the SymPy derivation
        self.assertEqual(sp.simplify(exact[0, 0] - 4 / e ** 2 * (1 / sp.sqrt(1 - e ** 2) - 1)), 0)
        self.assertEqual(sp.simplify(exact[1, 1] - 4 / e ** 2 * (1 - sp.sqrt(1 - e ** 2))), 0)
        edges, rel = binned_map()
        n = 20000
        got = an.harmonic_covariance(edges, rel, n)
        cov = got["covariance_ab"]
        self.assertFalse(got["isotropic"])
        self.assertIsNone(got["n_isotropic"])
        for i in range(2):
            self.assertLess(abs(n * cov[i][i] / expected[i][i] - 1.0), BIN_RTOL, (i, n * cov[i][i], expected[i][i]))
        self.assertLess(abs(n * cov[0][1] - expected[0][1]), BIN_RTOL * expected[0][0])
        self.assertEqual(cov[0][1], cov[1][0])
        # the exposure axis at 30 deg: a and b correlate
        expected, _ = sympy_per_event_covariance(axis_deg=int(AXIS))
        self.assertGreater(expected[0][1], 1.0)
        cov = an.harmonic_covariance(*binned_map(axis_deg=AXIS), n)["covariance_ab"]
        for i, j in ((0, 0), (1, 1), (0, 1), (1, 0)):
            self.assertLess(abs(n * cov[i][j] / expected[i][j] - 1.0), BIN_RTOL, (i, j, n * cov[i][j], expected[i][j]))

    def test_toy_skies_have_the_reported_covariance(self):
        """Invariant: the sample covariance of (a, b) over toy skies (isotropic sky through a 24-bin 1 + 0.9 cos map)
        agrees with harmonic_covariance within 4 Monte Carlo standard errors."""
        an = import_mod()
        edges, rel = binned_map(24)
        n, toys = 1000, 2000
        rng = random.Random(20261022)
        pts = []
        for _ in range(toys):
            ras, w = sample_sky(rng, edges, rel, n)
            a, b, _ = harmonic_from_events(ras, w)
            pts.append((a, b))
        ma = math.fsum(p[0] for p in pts) / toys
        mb = math.fsum(p[1] for p in pts) / toys
        vaa = math.fsum((p[0] - ma) ** 2 for p in pts) / (toys - 1)
        vbb = math.fsum((p[1] - mb) ** 2 for p in pts) / (toys - 1)
        vab = math.fsum((p[0] - ma) * (p[1] - mb) for p in pts) / (toys - 1)
        cov = an.harmonic_covariance(edges, rel, n)["covariance_ab"]
        se = math.sqrt(2.0 / toys)
        self.assertLess(abs(vaa / cov[0][0] - 1.0), 4 * se, (vaa, cov[0][0]))
        self.assertLess(abs(vbb / cov[1][1] - 1.0), 4 * se, (vbb, cov[1][1]))
        self.assertLess(abs(vab - cov[0][1]), 4 * math.sqrt(cov[0][0] * cov[1][1] / toys), (vab, cov[0][1]))
        # the pre-fix (2 / N_eff) I is outside the same band for a (the effect is 39 %)
        n_eff = harmonic_from_events(*sample_sky(rng, edges, rel, n))[2]
        self.assertGreater(abs(vaa / (2.0 / n_eff) - 1.0), 4 * se)

    def test_uniform_map_reproduces_the_unweighted_outputs_bit_for_bit(self):
        """Invariant: a uniform exposure map gives exactly (2/N) I and the same numbers as no map (the Rice
        construction is kept unchanged)."""
        rng = random.Random(7)
        ras = [360.0 * rng.random() for _ in range(3000)]
        edges = [15.0 * i for i in range(25)]
        no_map = run_harmonic(ras)
        flat = run_harmonic(ras, edges, [1.0] * 24)
        n = len(ras)
        self.assertEqual(flat["harmonic"]["covariance_ab"], [[2.0 / n, 0.0], [0.0, 2.0 / n]])
        for k in ("a", "b", "amplitude", "phase_deg", "rayleigh_probability", "sigma_per_component", "n_effective"):
            self.assertEqual(flat["harmonic"][k], no_map["harmonic"][k], k)
        self.assertEqual(flat["upper_limit"], no_map["upper_limit"])
        r = no_map["harmonic"]["amplitude"]
        self.assertEqual(no_map["harmonic"]["rayleigh_probability"], math.exp(-n * r * r / 4.0))
        self.assertEqual(no_map["harmonic"]["sigma_per_component"], math.sqrt(2.0 / n))

    def test_a_map_with_an_empty_bin_is_rejected(self):
        an = import_mod()
        edges = [15.0 * i for i in range(25)]
        with self.assertRaises(ValueError):
            an.harmonic_covariance(edges, [0.0] + [1.0] * 23, 100)


class Significance(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # exposure 1 + 0.9 cos(alpha - 30 deg), so a and b correlate; a dipole along the exposure axis
        cls.edges, cls.rel = binned_map(axis_deg=AXIS)
        rng = random.Random(31)
        cls.n = 20000
        cls.ras, cls.w = sample_sky(rng, cls.edges, cls.rel, cls.n, d=0.06, phase_deg=AXIS)
        cls.out = run_harmonic(cls.ras, cls.edges, cls.rel)
        per_event, _ = sympy_per_event_covariance(axis_deg=int(AXIS))
        cls.cov = [[v / cls.n for v in row] for row in per_event]
        cls.a, cls.b, cls.n_eff = harmonic_from_events(cls.ras, cls.w)

    def oracle_chi2(self, cov):
        from scipy.spatial.distance import mahalanobis
        import numpy as np
        return mahalanobis([self.a, self.b], [0.0, 0.0], np.linalg.inv(np.array(cov))) ** 2

    def test_rayleigh_probability_matches_scipy_chi2(self):
        """Independent implementation: P(chi^2_2 >= v^T V^-1 v) from scipy (scipy.spatial mahalanobis,
        scipy.stats.chi2.sf), V from the SymPy oracle, against the CLI's rayleigh_probability."""
        from scipy import stats
        h = self.out["harmonic"]
        self.assertAlmostEqual(h["a"], self.a, delta=1e-12)
        self.assertAlmostEqual(h["b"], self.b, delta=1e-12)
        chi2 = self.oracle_chi2(self.cov)
        p = stats.chi2.sf(chi2, 2)
        self.assertGreater(chi2, 5.0)  # a significance worth testing
        self.assertLess(abs(math.log(h["rayleigh_probability"] / p)), 0.5 * BIN_RTOL * chi2 + 1e-12,
                        (h["rayleigh_probability"], p))
        self.assertLess(abs(h["chi2_ab"] / chi2 - 1.0), BIN_RTOL)

    def test_negative_control_pre_fix_n_eff_fails_the_oracle(self):
        """Negative control: the pre-fix probability exp(-N_eff r^2 / 4) is emulated here and fails the scipy oracle
        (it overstates the significance of a dipole along the less exposed axis); the script no longer reports it."""
        from scipy import stats
        r2 = self.a * self.a + self.b * self.b
        p_pre_fix = math.exp(-self.n_eff * r2 / 4.0)
        p = stats.chi2.sf(self.oracle_chi2(self.cov), 2)
        self.assertLess(p_pre_fix, p / 3.0, (p_pre_fix, p))  # far outside the 1e-4 band
        self.assertGreater(abs(math.log(self.out["harmonic"]["rayleigh_probability"] / p_pre_fix)), 1.0)
        # and the pre-fix (2 / N_eff) I against the SymPy covariance: the variance along the exposure axis is 6.39 / N,
        # 39 % more than 2 / N_eff
        import numpy as np
        self.assertLess(2.0 / self.n_eff / max(np.linalg.eigvalsh(np.array(self.cov))), 0.75)

    def test_limit_meets_the_neyman_condition_by_scipy(self):
        """Independent implementation: at the CLI's Neyman limit s_UL the largest P(r <= r_obs | s_UL, phi) over the
        documented phase grid (72 phases in 5 deg steps from an eigen-axis of V; numpy.linalg.eigh, scipy dblquad, V
        from SymPy) is 1 - CL; the continuous maximum over the phase exceeds it by less than 2e-3; the null median
        matches the scipy root of P(r <= x | 0) = 1/2."""
        import numpy as np
        from scipy import optimize
        ul = self.out["upper_limit"]
        r_obs = self.out["harmonic"]["amplitude"]
        s_ul = ul["neyman_limit"]
        self.assertIsNotNone(s_ul)

        def cdf(s, phi):
            return scipy_disk_cdf(r_obs, [s * math.cos(phi), s * math.sin(phi)], self.cov)

        vecs = np.linalg.eigh(np.array(self.cov))[1]
        axis = math.atan2(vecs[1, 0], vecs[0, 0])
        phases = [axis + math.radians(5.0 * j) for j in range(72)]
        grid = [cdf(s_ul, p) for p in phases]
        self.assertLess(abs(max(grid) - 0.05), 1e-4, grid)
        top = phases[grid.index(max(grid))]
        best = optimize.minimize_scalar(lambda p: -cdf(s_ul, p), bounds=(top - math.radians(5), top + math.radians(5)),
                                        method="bounded", options={"xatol": 1e-6})
        self.assertLess(-best.fun - max(grid), 2e-3)
        median = optimize.brentq(lambda x: scipy_disk_cdf(x, [0.0, 0.0], self.cov) - 0.5, 1e-6, 1.0, xtol=1e-14)
        self.assertLess(abs(ul["median_isotropic_amplitude"] / median - 1.0), BIN_RTOL)

    def test_negative_control_pre_fix_rice_limit_fails_the_neyman_condition(self):
        """Negative control: the pre-fix limit (Rice with sigma^2 = 2/N_eff), emulated here by bisection on
        scipy.stats.ncx2, excludes a true amplitude that the scipy oracle does not exclude along the exposure
        axis."""
        from scipy import optimize, stats
        r_obs = math.hypot(self.a, self.b)
        sig2 = 2.0 / self.n_eff
        s_pre = optimize.brentq(lambda s: stats.ncx2.cdf(r_obs ** 2 / sig2, 2, s * s / sig2) - 0.05, 1e-9, 1.0,
                                xtol=1e-14)
        phi = math.radians(AXIS)
        p0 = scipy_disk_cdf(r_obs, [s_pre * math.cos(phi), s_pre * math.sin(phi)], self.cov)
        self.assertGreater(p0, 0.05 + 0.01, p0)  # s_pre is still allowed there: the pre-fix limit is too tight
        self.assertGreater(self.out["upper_limit"]["neyman_limit"], 1.01 * s_pre)  # the script's limit is not it


class LimitConstruction(unittest.TestCase):
    def test_cdf_matches_scipy(self):
        """Independent implementation: AnisotropicNull.cdf against scipy's bivariate normal over the disk, and the
        isotropic case against scipy.stats.ncx2 (the Rice law)."""
        from scipy import stats
        an = import_mod()
        n = 2000
        per_event, _ = sympy_per_event_covariance()
        cov = [[per_event[0][0] / n, 0.012 / n], [0.012 / n, per_event[1][1] / n]]  # a covariance term as well
        model = an.AnisotropicNull(cov)
        sig = math.sqrt(per_event[0][0] / n)
        for x_sig, s_sig, phase in ((0.5, 0.0, 0.0), (1.5, 0.0, 0.0), (1.0, 1.0, 0.0), (2.0, 3.0, 37.0),
                                    (4.0, 2.0, 90.0), (3.0, 5.0, 200.0), (0.3, 0.8, 300.0)):
            x, s = x_sig * sig, s_sig * sig
            mean = [s * math.cos(math.radians(phase)), s * math.sin(math.radians(phase))]
            with self.subTest(x=x_sig, s=s_sig, phase=phase):
                self.assertAlmostEqual(model.cdf(x, s, phase), scipy_disk_cdf(x, mean, cov), delta=QUAD_ATOL)
        iso = an.AnisotropicNull([[2.0 / n, 0.0], [0.0, 2.0 / n]])
        for x_sig, s_sig in ((0.5, 0.0), (1.0, 2.0), (3.0, 2.5), (6.0, 4.0)):
            x, s = x_sig * math.sqrt(2.0 / n), s_sig * math.sqrt(2.0 / n)
            with self.subTest(isotropic=True, x=x_sig, s=s_sig):
                expected = stats.ncx2.cdf(x * x / (2.0 / n), 2, s * s / (2.0 / n))
                self.assertAlmostEqual(iso.cdf(x, s, 123.0), expected, delta=QUAD_ATOL)

    def test_limit_takes_the_largest_cdf_over_the_phase_grid(self):
        """Independent implementation: with a confidence level below 1/2 (the limit lies below r_obs) the phase that
        decides the limit is not the major eigen-axis; at the reported limit the largest scipy CDF over the 72-point grid
        aligned with V's eigen-axes (numpy.linalg.eigh) is 1 - CL (1e-7: dblquad at 1e-10, the bisection stops at
        1e-13 of s), with V of the exposure 1 + 0.9 cos(alpha - 30 deg)."""
        import numpy as np
        an = import_mod()
        n = 2000
        per_event, _ = sympy_per_event_covariance(axis_deg=int(AXIS))
        cov = (np.array(per_event) / n).tolist()
        vals, vecs = np.linalg.eigh(np.array(cov))
        axis = math.atan2(vecs[1, 1], vecs[0, 1])  # the larger eigenvalue's axis
        sig = math.sqrt(vals[1])
        for cl, r_sig in ((0.3, 2.0), (0.2, 3.0)):
            r_obs = r_sig * sig
            s_ul = an.AnisotropicNull(cov).neyman(r_obs, cl)  # the expected limit is empty below CL 1/2
            grid = [scipy_disk_cdf(r_obs, [s_ul * math.cos(axis + math.radians(5.0 * j)),
                                           s_ul * math.sin(axis + math.radians(5.0 * j))], cov) for j in range(72)]
            with self.subTest(cl=cl, r_sig=r_sig):
                self.assertLess(abs(max(grid) - (1.0 - cl)), 1e-7, max(grid))
                # the decisive phase is not the major axis (off the axes at CL 0.3, the minor axis at CL 0.2)
                self.assertGreater(max(grid) - max(grid[0], grid[36]), 1e-4)

    def test_acceptance_region_covers_at_four_phases(self):
        """Invariant (fast): for Gaussian toys (a, b) ~ N(s (cos phi, sin phi), V) with the covariance of the
        exposure 1 + 0.9 cos(alpha - 30 deg), the true s is not excluded (AnisotropicNull.allowed at CL 0.95) in at
        least CL - 3 SE of the toys at phi = 30, 75, 120, 165 deg; the pre-fix Rice region with sigma^2 = 2/N_eff,
        emulated with scipy.stats.ncx2, under-covers along the exposure axis (phi = 30 deg)."""
        import numpy as np
        from scipy import stats
        an = import_mod()
        n, cl, toys = 2000, 0.95, 1500
        per_event, _ = sympy_per_event_covariance(axis_deg=int(AXIS))
        cov = np.array(per_event) / n
        model = an.AnisotropicNull(cov.tolist())
        s = 5.0 * math.sqrt(max(np.linalg.eigvalsh(cov)))
        floor = cl - 3.0 * math.sqrt(cl * (1.0 - cl) / toys)
        rng = np.random.default_rng(20261022)
        sig2_pre = float(np.trace(cov)) / 2.0  # 2 / N_eff -> 2 E[w^2] / N = (Var a + Var b) / 2 for large N
        for phase in (AXIS + 0.0, AXIS + 45.0, AXIS + 90.0, AXIS + 135.0):
            mu = s * np.array([math.cos(math.radians(phase)), math.sin(math.radians(phase))])
            v = rng.multivariate_normal(mu, cov, size=toys)
            r = np.hypot(v[:, 0], v[:, 1])
            cover = sum(model.allowed(float(x), s, 1.0 - cl) for x in r) / toys
            with self.subTest(phase=phase):
                self.assertGreaterEqual(cover, floor, cover)
            if phase == AXIS:
                pre = float(np.mean(stats.ncx2.cdf(r ** 2 / sig2_pre, 2, s * s / sig2_pre) >= 1.0 - cl))
                self.assertLess(pre, floor, pre)

    @unittest.skipUnless(SLOW, "slow: set HEP_SLOW_TESTS=1")
    def test_upper_limit_covers_with_a_modulated_exposure(self):
        """Invariant (slow tier): event-level toys through the 24-bin 1 + 0.9 cos map, n = 2000, s = 0.15, CL 0.95,
        dipole phases 0, 45, 90, 135 deg: harmonic_covariance, first_harmonic and amplitude_upper_limit as the CLI
        chains them; coverage at least CL - 3 SE at each phase."""
        an = import_mod()
        edges, rel = binned_map(24)
        n, s, cl, toys = 2000, 0.15, 0.95, 400
        null = an.harmonic_covariance(edges, rel, n)
        self.assertFalse(null["isotropic"])
        floor = cl - 3.0 * math.sqrt(cl * (1.0 - cl) / toys)
        rng = random.Random(4)
        for phase in (0.0, 45.0, 90.0, 135.0):
            cover = 0
            for _ in range(toys):
                ras, w = sample_sky(rng, edges, rel, n, d=s, phase_deg=phase)
                h = an.first_harmonic(ras, w, None, null)
                ul = an.amplitude_upper_limit(h["amplitude"], None, cl, covariance=null["covariance_ab"])
                cover += ul["upper_limit"] >= s
            with self.subTest(phase=phase):
                self.assertGreaterEqual(cover / toys, floor, cover / toys)


if __name__ == "__main__":
    unittest.main()
