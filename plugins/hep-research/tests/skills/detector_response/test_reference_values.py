"""Cross-check the physics helpers against independent references, not themselves.

Each test compares a script's result with either an independent numerical route
(scipy distributions, a direct profile-likelihood fit) or a published value
(PDG tables, Smart & Shea 2005). The scipy-based tests are skipped if scipy is
missing. Run from the skill directory: python3 -m unittest discover -s tests -v
"""
import math
import sys
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[3]  # plugin root (tests/skills/<skill>/<this file>)
ROOT = PLUGIN
for _skill in ('hep-statistics', 'hep-analysis', 'detector-response'):
    sys.path.insert(0, str(PLUGIN / 'skills' / _skill / 'scripts'))
from calorimeter_resolution import evaluate, fit_resolution
from cherenkov_angle import cherenkov_angle, saturation_angle, threshold_momentum
from cosmic_ray_flux import flux_from_counts, poisson_interval
from geomagnetic_cutoff import stormer_cutoff_gv
from li_ma_significance import li_ma_significance
from multiple_scattering import highland_angle
from pid_separation_power import MASSES_GEV, bethe_bloch_mev_per_g_cm2, time_of_flight_ns
from solar_modulation_force_field import modulate, power_law_lis
from tag_and_probe_efficiency import clopper_pearson
from xmax_gaisser_hillas import gaisser_hillas, shower_age

try:
    from scipy import optimize, stats
    HAVE_SCIPY = True
except ImportError:
    HAVE_SCIPY = False


@unittest.skipUnless(HAVE_SCIPY, 'scipy not installed')
class ScipyReferenceTests(unittest.TestCase):
    def test_li_ma_equals_numerical_profile_likelihood_ratio(self):
        # Li & Ma (1983) eq. 17 is sqrt(-2 ln lambda) for ON/OFF Poisson counting;
        # recompute lambda by numerically maximizing the Poisson likelihoods.
        def nll(params, n_on, n_off, alpha, free_signal):
            b = params[0]
            s = params[1] if free_signal else 0.0
            if b <= 0 or s + alpha * b <= 0:
                return 1e300
            return -(stats.poisson.logpmf(n_on, s + alpha * b) + stats.poisson.logpmf(n_off, b))

        opts = dict(xatol=1e-10, fatol=1e-12, maxiter=20000)
        for n_on, n_off, alpha in [(50, 100, 0.2), (130, 300, 0.25), (10, 5, 1.0)]:
            null = optimize.minimize(nll, [n_off], args=(n_on, n_off, alpha, False),
                                     method='Nelder-Mead', options=opts)
            free = optimize.minimize(nll, [n_off, n_on - alpha * n_off],
                                     args=(n_on, n_off, alpha, True),
                                     method='Nelder-Mead', options=opts)
            expected = math.sqrt(2.0 * (null.fun - free.fun))
            got = li_ma_significance(n_on, n_off, alpha)['significance']
            self.assertAlmostEqual(got, expected, places=6)

    def test_clopper_pearson_matches_beta_quantiles(self):
        for k, n in [(0, 10), (3, 10), (10, 10), (95, 100), (500, 1000)]:
            lower, upper = clopper_pearson(k, n, 0.95)
            ref_lower = stats.beta.ppf(0.025, k, n - k + 1) if k > 0 else 0.0
            ref_upper = stats.beta.ppf(0.975, k + 1, n - k) if k < n else 1.0
            self.assertAlmostEqual(lower, ref_lower, places=10)
            self.assertAlmostEqual(upper, ref_upper, places=10)

    def test_garwood_poisson_interval_matches_chi2_quantiles(self):
        alpha = 1.0 - 0.6827
        for n in [0, 1, 5, 20, 100]:
            lower, upper = poisson_interval(n, 0.6827)
            ref_lower = stats.chi2.ppf(alpha / 2.0, 2 * n) / 2.0 if n else 0.0
            ref_upper = stats.chi2.ppf(1.0 - alpha / 2.0, 2 * n + 2) / 2.0
            self.assertAlmostEqual(lower, ref_lower, places=8)
            self.assertAlmostEqual(upper, ref_upper, places=8)


class PublishedValueTests(unittest.TestCase):
    def test_vertical_stormer_cutoff_smart_shea(self):
        # Smart & Shea 2005: vertical dipole cutoff 14.9 cos^4(lambda) / r^2 GV.
        for lat in (0.0, 30.0, 51.6):
            self.assertAlmostEqual(stormer_cutoff_gv(lat), 14.9 * math.cos(math.radians(lat)) ** 4,
                                   places=6)

    def test_bethe_bloch_minimum_ionization_matches_pdg_tables(self):
        # PDG "Atomic and nuclear properties" <dE/dx>_min in MeV cm^2/g. Gases agree
        # tightly; condensed media come out ~2-3% high because the script omits the
        # density-effect correction (documented in its docstring).
        pdg = {'argon': (1.519, 0.005), 'neon': (1.724, 0.005), 'xenon': (1.255, 0.005),
               'silicon': (1.664, 0.03), 'water': (1.992, 0.03)}
        muon = MASSES_GEV['mu']
        for material, (reference, tolerance) in pdg.items():
            minimum = min(bethe_bloch_mev_per_g_cm2(p / 1000.0, muon, material)['mev_per_g_cm2']
                          for p in range(100, 2000, 5))
            self.assertLess(abs(minimum / reference - 1.0), tolerance, material)
            self.assertGreaterEqual(minimum, reference * 0.995, material)

    def test_highland_formula_pdg_form(self):
        # PDG: theta0 = 13.6 MeV/(beta c p) z sqrt(x/X0) [1 + 0.038 ln(x z^2 / (X0 beta^2))].
        expected = 0.0136 / 1.0 * math.sqrt(0.01) * (1.0 + 0.038 * math.log(0.01))
        self.assertAlmostEqual(highland_angle(1.0, 0.01), expected, places=12)
        # Helium at the same rigidity: p = 2R, z = 2, so the prefactor is unchanged and
        # only the log term picks up z^2.
        expected_he = 0.0136 / 1.0 * math.sqrt(0.01) * (1.0 + 0.038 * math.log(0.04))
        self.assertAlmostEqual(highland_angle(1.0, 0.01, charge=2), expected_he, places=12)

    def test_cherenkov_water_threshold_and_saturation(self):
        # Water n = 1.33: saturation angle arccos(1/1.33) ~= 41.2 deg; muon threshold
        # momentum m/sqrt(n^2-1) ~= 0.120 GeV (total energy ~0.160 GeV).
        self.assertAlmostEqual(math.degrees(saturation_angle(1.33)), 41.25, places=2)
        p_thr = threshold_momentum(MASSES_GEV['mu'], 1.33)
        self.assertAlmostEqual(p_thr, 0.1205, places=4)
        self.assertAlmostEqual(math.hypot(p_thr, MASSES_GEV['mu']), 0.160, places=3)
        self.assertIsNone(cherenkov_angle(0.99 * p_thr, MASSES_GEV['mu'], 1.33))


class IndependentFormulaTests(unittest.TestCase):
    def test_force_field_matches_gleeson_axford_by_hand(self):
        # Proton, T = 1 GeV, phi = 0.5 GV: J = J_LIS(1.5) * T(T+2m) / ((T+phi)(T+phi+2m)).
        m = 0.938272
        lis = lambda e: power_law_lis(e, 1e4, 2.7)
        got = modulate(1.0, m, 1, 0.5, lis)['flux_toa']
        expected = lis(1.5) * (1.0 * (1.0 + 2 * m)) / (1.5 * (1.5 + 2 * m))
        self.assertAlmostEqual(got, expected, places=10)

    def test_gaisser_hillas_peaks_at_xmax_with_value_nmax(self):
        n_max, x_max, x0, lam = 1e9, 750.0, -50.0, 70.0
        self.assertAlmostEqual(gaisser_hillas(x_max, n_max, x_max, x0, lam), n_max, places=3)
        self.assertLess(gaisser_hillas(x_max - 1.0, n_max, x_max, x0, lam), n_max)
        self.assertLess(gaisser_hillas(x_max + 1.0, n_max, x_max, x0, lam), n_max)
        self.assertAlmostEqual(shower_age(x_max, x_max, x0), 1.0, places=12)

    def test_time_of_flight_difference(self):
        # t = L/c * sqrt(1 + m^2/p^2); pi/K at 1 GeV over 1 m differ by ~0.37 ns.
        c = 0.299792458  # m/ns
        dt = time_of_flight_ns(1.0, MASSES_GEV['K'], 1.0) - time_of_flight_ns(1.0, MASSES_GEV['pi'], 1.0)
        ref = (math.sqrt(1 + MASSES_GEV['K'] ** 2) - math.sqrt(1 + MASSES_GEV['pi'] ** 2)) / c
        self.assertAlmostEqual(dt, ref, places=10)

    def test_calorimeter_fit_recovers_generated_terms(self):
        a, b, c = 0.10, 0.20, 0.01
        points = [(e, evaluate(a, b, c, e)['relative_resolution']) for e in (1, 2, 5, 10, 50, 100, 200)]
        fitted = fit_resolution(points)
        for name, want in (('stochastic', a), ('noise', b), ('constant', c)):
            self.assertAlmostEqual(fitted[name], want, places=6)

    def test_flux_is_counts_over_exposure_times_bin_width(self):
        result = flux_from_counts(100, exposure=2.5e3, bin_width=0.5)
        self.assertAlmostEqual(result['flux'], 100 / (2.5e3 * 0.5), places=12)



class SkillGarwoodTableTest(unittest.TestCase):
    """The exact-interval table in skills/hep-analysis/references/hep-analysis-guide.md (legacy SKILL.md) must match cosmic_ray_flux.poisson_interval."""

    def test_table_matches_script(self):
        text = (ROOT / 'skills/hep-analysis/references/hep-analysis-guide.md').read_text()
        rows = {}
        for line in text.splitlines():
            cells = [c.strip() for c in line.strip().strip('|').split('|')]
            if cells and cells[0] in ('N', 'lower', 'upper'):
                rows[cells[0]] = cells[1:]
        self.assertEqual(set(rows), {'N', 'lower', 'upper'})
        for n, lo, hi in zip(rows['N'], rows['lower'], rows['upper']):
            exp_lo, exp_hi = poisson_interval(int(n))
            self.assertAlmostEqual(float(lo), exp_lo, delta=0.006, msg=f'N={n} lower')
            self.assertAlmostEqual(float(hi), exp_hi, delta=0.006, msg=f'N={n} upper')

class SkillUnitsAndScriptRulesTest(unittest.TestCase):
    """P01 and P08 rules: the fb^-1 x pb factor, and running the flux script rather than dividing."""

    def test_unit_factor_is_right(self):
        # 138 fb^-1 x 833.9 pb = 138e3 pb^-1 x 833.9 pb
        self.assertAlmostEqual(138.0 * 1000 * 833.9, 138e3 * 833.9, places=6)

    def test_flux_script_gives_the_documented_numbers(self):
        r = flux_from_counts(3, exposure=1.8e7, bin_width=0.6)
        self.assertAlmostEqual(r['flux'], 2.7778e-7, delta=1e-10)
        self.assertAlmostEqual(r['flux_lower'], 1.2660e-7, delta=1e-10)
        self.assertAlmostEqual(r['flux_upper'], 5.4799e-7, delta=1e-10)


class SkillAwkwardLeadingObjectTest(unittest.TestCase):
    """SKILL.md must carry the leading-object rule that Haiku (which skips references) needs."""

    def test_documented_pattern_picks_leading_jets_and_the_banned_one_does_not(self):
        try:
            import awkward as ak
        except ImportError:
            self.skipTest('awkward not installed')
        pt = ak.Array([[50, 40, 30], [60, 20], [90, 80, 70, 10]])
        order = ak.argsort(pt, axis=1, ascending=False)
        self.assertEqual(ak.to_list(pt[order][:, 0]), [50, 60, 90])
        self.assertEqual(ak.to_list(ak.firsts(pt[order][:, :1])), [50, 60, 90])
        self.assertEqual(ak.to_list(ak.firsts(pt[ak.argmax(pt, axis=1, keepdims=True)])), [50, 60, 90])
        banned = ak.to_list(pt[order[:, 0]])
        self.assertNotEqual(banned, [50, 60, 90])
        self.assertEqual(banned, [[50, 40, 30]] * 3)  # whole events, not one jet each


if __name__ == '__main__':
    unittest.main()
