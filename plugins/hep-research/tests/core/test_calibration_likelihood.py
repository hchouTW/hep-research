"""The joint likelihood of Part B section 2.1 and V_model of section 5.4 (phase 2, WP1)."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

import numpy as np
from scipy import special

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from core.calibration import likelihood as L  # noqa: E402


def mixed_problem(seed=1):
    """A layout with every block kind, nu, eta, phi_P, omega, gamma and delta."""
    rng = np.random.default_rng(seed)
    obs = [{"name": "a", "block": "gaussian", "link": "log"},
           {"name": "s", "block": "gaussian", "bins": 3, "shape_link": "alr"},
           {"name": "c", "block": "poisson", "bins": 4, "free_omega": True, "bb": True},
           {"name": "q", "block": "poisson", "bins": 2, "free_omega": False, "bb": True},
           {"name": "e", "block": "binomial"}]
    lay = L.build_layout(obs, ["t1", "t2"], ["ph"], 2, 1)

    def pred(tp):
        t1, t2, ph = tp["t1"], tp["t2"], tp["ph"]
        return {"a": 2.0 * np.exp(0.1 * t1) + 0.05 * ph, "s": np.array([1 + 0.1 * t1, 2 + 0.2 * t2, 3.0]),
                "c": np.array([10, 20 + 5 * t2, 30, 15 + t1]), "q": np.array([50 * np.exp(0.05 * t1), 80.0]),
                "e": special.expit(0.5 + 0.2 * t2 + 0.1 * ph)}

    ng = lay.gaussian_rows().size
    A = rng.normal(size=(ng, ng))
    V = A @ A.T * 0.01 + np.eye(ng) * 0.02
    ref = L.Reference(V_G=V, V_std=V, U=rng.normal(size=(lay.n_link, 2)) * 0.05,
                      S=rng.normal(size=(lay.n_link, 1)) * 0.03,
                      tau={"c": np.array([100, 50, 80, 0.0]), "q": np.array([40., 60.])},
                      n_eff={"e": (500., 300.)}).finalize()
    data = L.Data(y_gauss=rng.normal(size=ng) * 0.1, counts={"c": np.array([9, 25, 33, 14]), "q": np.array([47, 85])},
                  binom={"e": (130, 200)}, phi0=np.array([0.0]), phi_cov=np.array([[1.0]]), aux_k={"e": (290, 505)})
    return L.Likelihood(lay, data, ref), pred, rng


def fd_columns(lk, pred, b, eps=1e-6):
    tp = list(range(lk.sl["theta"].start, lk.sl["phi_P"].stop))
    H = np.zeros((lk.layout.n_link, len(tp)))
    for j, i in enumerate(tp):
        bp, bm = b.copy(), b.copy()
        bp[i] += eps
        bm[i] -= eps
        H[:, j] = (lk.model_link(pred(lk.theta_phi(bp))) - lk.model_link(pred(lk.theta_phi(bm)))) / (2 * eps)
    return H


class Score(unittest.TestCase):
    def test_score_matches_finite_differences(self):
        """The analytic gradient over every block and nuisance equals central differences of -2 ln L."""
        lk, pred, rng = mixed_problem()
        b = lk.initial_beta({"t1": 0.1, "t2": -0.2}) + rng.normal(size=lk.layout.n_beta) * 0.05
        b[lk.sl["omega"]] = 60.0
        h = lk.model_link(pred(lk.theta_phi(b)))
        g, F = lk.score_fisher(b, h, fd_columns(lk, pred, b))

        def D(x):
            return lk.deviance(x, lk.model_link(pred(lk.theta_phi(x))))
        e = 1e-6
        gn = np.array([(D(np.r_[b[:i], b[i] + e, b[i + 1:]]) - D(np.r_[b[:i], b[i] - e, b[i + 1:]])) / (2 * e)
                       for i in range(b.size)])
        self.assertLess(np.abs(g - gn).max() / np.abs(gn).max(), 1e-6)
        self.assertGreater(np.linalg.eigvalsh(F).min(), 0.0)

    def test_aux_terms_depend_on_their_nuisance_only(self):
        """BB-lite and the auxiliary binomial term are functions of gamma and delta only (section 2.1)."""
        lk, pred, rng = mixed_problem()
        b = lk.initial_beta({"t1": 0.0, "t2": 0.0})
        b[lk.sl["gamma"]] = 1.1
        b[lk.sl["delta"]] = 0.2
        aux = []
        for t in (-1.0, 0.0, 1.5):
            x = b.copy()
            x[lk.sl["theta"]] = t
            aux.append(lk.deviance(x, lk.model_link(pred(lk.theta_phi(x))), parts=True)[1]["aux"])
        self.assertTrue(np.allclose(aux, aux[0], rtol=1e-12))


class Links(unittest.TestCase):
    def test_round_trip_and_range(self):
        for kind, x in (("identity", [-3.0, 0.0, 2.5]), ("log", [1e-3, 1.0, 50.0]), ("logit", [1e-6, 0.5, 0.999999]),
                        ("fisher-z", [-0.99, 0.0, 0.7])):
            np.testing.assert_allclose(L.inv_link(L.link(x, kind), kind), x, rtol=1e-10)

    def test_logit_keeps_efficiency_inside_unit_interval(self):
        """Efficiency close to 1 with nu, eta added via logit stays within (0, 1) (section 15.2)."""
        z = L.link(np.array([0.995]), "logit") + np.array([5.0, -5.0, 30.0])[:, None]
        p = L.inv_link(z, "logit")
        self.assertTrue(np.all((p > 0) & (p < 1)))

    def test_simplex_under_alr_shifts(self):
        """p = (0.6, 0.35, 0.05) shifted by +-0.5, +-5 in alr: inside the simplex, summing to 1 (section 15.2); the
        separate-logit construction of section 2.1 gives a negative component (negative control)."""
        p = np.array([0.6, 0.35, 0.05])
        Lm = L.logratio_matrix(3, "alr")
        for s in (0.5, -0.5, 5.0, -5.0):
            for d in (np.array([s, 0.0]), np.array([0.0, s]), np.array([s, s])):
                q = L.logratio_inverse(Lm @ np.log(p) + d, Lm)
                self.assertTrue(np.all(q > 0))
                self.assertAlmostEqual(q.sum(), 1.0, places=12)
        bad = special.expit(special.logit(p[:2]) + 0.5)
        self.assertAlmostEqual(1 - bad.sum(), -0.182, places=3)

    def test_count_likelihood_with_zero_bin(self):
        """Data (60, 40, 0): the count likelihood is defined (section 15.2)."""
        d = L.poisson_deviance([60, 40, 0], [55.0, 40.0, 5.0])
        self.assertTrue(np.isfinite(d) and d > 0)

    def test_half_estimator_defined_for_any_counts(self):
        Lm = L.logratio_matrix(3, "alr")
        for n in ([0, 0, 0], [5, 0, 3], [0, 4, 0]):
            self.assertTrue(np.all(np.isfinite(L.shape_summary(n, Lm))))

    def test_half_estimator_prediction_side(self):
        """E[alr(n + 1/2)] matches alr of the unnormalized expected counts (residual mean 0 within the MC error),
        while normalizing MC to the data size first and then adding 1/2 shifts it (section 2.1, 8.7 note 3)."""
        rng = np.random.default_rng(3)
        lam = np.array([20.0, 60.0, 200.0])
        Lm = L.logratio_matrix(3, "alr")
        n = rng.poisson(lam, size=(400_000, 3))
        mean = (np.log(n + 0.5) @ Lm.T).mean(0)
        se = (np.log(n + 0.5) @ Lm.T).std(0) / np.sqrt(n.shape[0])
        good = Lm @ np.log(lam)
        self.assertTrue(np.all(np.abs(mean - good) < 4 * se + 2e-4))
        bad = Lm @ np.log(lam + 0.5)
        self.assertGreater(np.abs(mean - bad)[0], 10 * se[0])


class Gaussian(unittest.TestCase):
    def test_projection_equals_removal_without_rounding(self):
        """N_d,c t = p1 + p2: the projected likelihood equals the one with t removed (section 2.1, 15.3.4)."""
        rng = np.random.default_rng(5)
        A = rng.normal(size=(2, 2))
        Vp = A @ A.T + np.eye(2)
        T = np.array([[1.0, 0.0], [0.0, 1.0], [1.0, 1.0]])
        V = T @ Vp @ T.T
        V_std = V.copy()
        n = np.array([1.0, 1.0, -1.0])
        W = L.projected_inverse(V, [n], V_std)
        x = rng.normal(size=2)
        r = T @ x
        self.assertAlmostEqual(float(r @ W @ r), float(x @ np.linalg.solve(Vp, x)), places=9)
        with self.assertRaises(np.linalg.LinAlgError):
            np.linalg.cholesky(V)                            # the unprojected V_G is singular (negative control)

    def test_dependent_constraints_rejected(self):
        V = np.eye(3)
        with self.assertRaises(L.LikelihoodError) as c:
            L.projected_inverse(V, [np.array([1., 0, 0]), np.array([0, 1., 0]), np.array([1., 1., 0])])
        self.assertEqual(c.exception.code, "contract.nd_dependent")

    def test_sigma0_zero_rejected(self):
        with self.assertRaises(L.LikelihoodError):
            L.projected_inverse(np.diag([1.0, 0.0]), [])


class WeightedBinomial(unittest.TestCase):
    def test_reduces_when_ratios_equal(self):
        """Equal sum w^2 / sum w for pass and fail: n_eff = W^2 / (S_P + S_F) (section 2.1)."""
        WP, SP, WF, SF = 30.0, 60.0, 70.0, 140.0
        n, k = L.binomial_effective(WP, SP, WF, SF)
        self.assertAlmostEqual(n, 100.0 ** 2 / 200.0)
        self.assertAlmostEqual(k, n * 0.3)

    def test_unequal_ratios_differ(self):
        """Different pass/fail weight moments give different MC uncertainties at the same efficiency centre
        (section 15.3a)."""
        a = L.binomial_effective(30.0, 30.0, 70.0, 280.0)
        b = L.binomial_effective(30.0, 120.0, 70.0, 70.0)
        self.assertNotAlmostEqual(a[0], b[0])
        self.assertAlmostEqual(a[1] / a[0], b[1] / b[0])

    def test_unweighted_is_plain_binomial(self):
        n, k = L.binomial_effective(30.0, 30.0, 70.0, 70.0)
        self.assertAlmostEqual(n, 100.0)
        self.assertAlmostEqual(k, 30.0)

    def test_scope(self):
        s = L.binomial_scope(0.3, 1000.0, 300.0, 700.0, 300.0, 700.0)
        self.assertTrue(s["in_scope"])
        self.assertFalse(L.binomial_scope(0.02, 100.0, 2.0, 98.0, 2.0, 98.0)["in_scope"])


class VModel(unittest.TestCase):
    def test_convolution_cross_kernel_is_psd(self):
        """Two groups with different correlation lengths and C != 0: the D39 (a) cross-kernel stays positive
        semidefinite; plugging the within-group squared exponential across groups with mixed lengths need not."""
        z = np.linspace(0, 10, 25)
        group = np.array(["w"] * 12 + ["m"] * 13)
        C = np.array([[1.0, 0.9], [0.9, 1.0]])
        R = L.kernel_component(np.r_[z[:12], z[:13]], group, {"w": 0.1, "m": 0.05}, {"w": 0.5, "m": 4.0}, C)
        L.check_psd(R)
        R0 = L.kernel_component(np.r_[z[:12], z[:13]], group, {"w": 0.1, "m": 0.05}, {"w": 0.5, "m": 4.0}, C,
                                cross="zero")
        L.check_psd(R0)
        self.assertEqual(np.abs(R0[:12, 12:]).max(), 0.0)

    def test_clr_kernel_invariant_to_reference_category(self):
        """A kernel declared in clr gives the same quadratic forms in alr coordinates for any reference category
        (section 5.4): a^T (H R H^T)^+ a is invariant."""
        rng = np.random.default_rng(2)
        K = 4
        Rc = np.cov(rng.normal(size=(50, K)), rowvar=False)
        P = np.eye(K) - 1.0 / K
        Rc = P @ Rc @ P
        logp = np.log(np.array([0.1, 0.2, 0.3, 0.4]))
        logq = np.log(np.array([0.15, 0.15, 0.35, 0.35]))
        vals = []
        for ref in range(K):
            H = L.logratio_matrix(K, "alr", ref)
            a = H @ (logq - logp)
            vals.append(float(a @ np.linalg.solve(H @ Rc @ H.T, a)))
        self.assertTrue(np.allclose(vals, vals[0], rtol=1e-9))

    def test_truncation_condition_two(self):
        """99% of tr V_model alone discards a part that is large against a precise group; condition 2 keeps more
        components (section 5.4, 19-3)."""
        n = 30
        rng = np.random.default_rng(4)
        E = np.linalg.qr(rng.normal(size=(n, n)))[0]
        lam = np.r_[100.0, 0.5, np.full(n - 2, 1e-3)]
        R = (E * lam) @ E.T
        VG = np.diag(np.r_[np.full(15, 1.0), np.full(15, 1e-4)])
        pc1 = L.principal_components(R, np.arange(n), None, frac=0.99, tr_bound=np.inf)
        pc2 = L.principal_components(R, np.arange(n), np.linalg.inv(VG))
        self.assertLess(pc1["K"], pc2["K"])
        self.assertLessEqual(pc2["tr_VGinv_Vperp"], 0.05)
        self.assertGreaterEqual(pc2["trace_fraction"], 0.99)

    def test_ensemble_second_moment(self):
        d = np.array([1.0, -2.0, 0.5])
        np.testing.assert_allclose(L.ensemble_component([d]), np.outer(d, d))
        R = L.ensemble_component([d, -d])
        np.testing.assert_allclose(R, np.outer(d, d))        # second moment, not the sample covariance (0 mean)

    def test_not_psd_rejected(self):
        with self.assertRaises(L.LikelihoodError):
            L.check_psd(np.array([[1.0, 2.0], [2.0, 1.0]]))


class Bootstrap(unittest.TestCase):
    def test_size_rule_and_factor(self):
        self.assertEqual(L.bootstrap_size(5), 500)
        self.assertEqual(L.bootstrap_size(50), 2500)
        with self.assertRaises(L.LikelihoodError):
            L.bootstrap_covariance(np.zeros((400, 3)))
        self.assertAlmostEqual(L.bootstrap_report_factor(2500, 50), 2448 / 2499)


if __name__ == "__main__":
    unittest.main()
