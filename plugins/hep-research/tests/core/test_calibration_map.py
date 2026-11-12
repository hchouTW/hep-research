"""The efficiency-map phi of Part B section 6.7 (phase 3, WP-D): native bases and U (calib_propagate), joint-pattern
replicas and the analytic covariance (D28), the map term U(theta) phi_map of the likelihood (calib_likelihood), and the
calib_design items: the theta-noise item of P5, the D84 G6 size check, the seeds of the mapping runs and the rejected
practices, the primaries and job-route checks, and the D83 (1) schema exemption. Sections 15.2, 15.3.1 (P5), 15.3.19,
15.3a. Synthetic fixtures with g4sim's map builder and replica law; Geant4 not run. Each negative test has its positive
control."""
from __future__ import annotations

import copy
import random
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np  # noqa: E402

import calibration_g4sim_fixtures as G  # noqa: E402
import calibration_map_fixtures as MF  # noqa: E402

from contracts.schema import validate  # noqa: E402
from core.calibration import design_g4sim as DG  # noqa: E402
from core.calibration import design_map as DM  # noqa: E402
from core.calibration import emulator as EM  # noqa: E402
from core.calibration import fit as FIT  # noqa: E402
from core.calibration import likelihood as L  # noqa: E402
from core.calibration import map_basis as MB  # noqa: E402
from core.calibration import map_term as MT  # noqa: E402
from core.simulation import digitize, efficiency_map as em, response, rng  # noqa: E402

MAP = G.efficiency_map()
PIPE = G.pipeline()


def deposits(n_events=10, seed=3):
    draw = random.Random(seed)
    return [(e, v, b, draw.uniform(50, 100), draw.uniform(5, 10), 3) for e in range(n_events) for v in range(2)
            for b in range(4)]


def gls(J, C, y):
    Ci = np.linalg.inv(C)
    F = J.T @ Ci @ J
    th = np.linalg.solve(F, J.T @ Ci @ y)
    r = y - J @ th
    return th, float(r @ Ci @ r), np.linalg.inv(F)


# ------------------------------------------------------------------ native basis and U (fixed map)
class TestNativeBasis(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.basis = MB.native_basis({1: MAP}, 100)

    def test_basis_is_the_replica_covariance_and_centre_is_k_over_n(self):
        b = self.basis
        E = np.stack([MB.map_vector({1: MAP}, r) for r in range(1, 101)])
        np.testing.assert_allclose(b["B_map"] @ b["B_map"].T, np.cov(E.T), atol=1e-15)
        np.testing.assert_allclose(b["eps0"], MB.map_vector({1: MAP}, 0))
        self.assertTrue(np.all(MB.dirichlet_mean({1: MAP}) > b["eps0"]))      # Jeffreys mean above k/n (M1)
        self.assertEqual(b["key"]["centre"], "k/n")
        self.assertEqual(b["key"]["maps"]["1"], em.map_sha256(MAP))

    def test_registration_key_follows_R_and_map_bytes(self):
        k1 = self.basis["key"]["id"]
        self.assertNotEqual(k1, MB.native_basis({1: MAP}, 120)["key"]["id"])
        other = copy.deepcopy(MAP)
        other["form"]["uniformity"] = {"status": "passed"}      # any change of bytes changes the hash (D83 (1))
        self.assertNotEqual(k1, MB.registration_key({1: other}, 100, MB.coordinates({1: other}),
                                                    MB.map_vector({1: other}))["id"])
        self.assertEqual(k1, MB.native_basis({1: MAP}, 100)["key"]["id"])        # positive control: reproducible

    def test_fewer_than_100_replicas_refused(self):
        with self.assertRaises(MB.BasisError) as cm:
            MB.native_basis({1: MAP}, 50)
        self.assertEqual(cm.exception.code, "basis.replicas")

    def test_u_digitized_equals_linear_construction_for_linear_observables(self):
        b = self.basis
        J = np.random.default_rng(1).normal(size=(3, 8))
        P = np.stack([J @ MB.map_vector({1: MAP}, r) for r in range(1, 101)])
        np.testing.assert_allclose(MB.u_digitized(P, b), MB.u_linear(J, b), atol=1e-12)
        # a non-linear observable: the secant over the replica spread differs from J B_map
        Pn = np.stack([np.exp(40 * J @ MB.map_vector({1: MAP}, r)) for r in range(1, 101)])
        Jn = 40 * np.exp(40 * J @ b["eps0"])[:, None] * J
        self.assertGreater(np.linalg.norm(MB.u_digitized(Pn, b) - MB.u_linear(Jn, b)), 1e-3 *
                           np.linalg.norm(MB.u_linear(Jn, b)))

    def test_section_15_2_u_from_digi_jobs_agrees_with_linear_construction(self):
        """Section 15.2 (fixed map, U from the digitization job): g4sim-digi-job/1 digitizations at g4sim's replicas
        against J B_map, for photoelectron totals (linear in eps), within the response noise."""
        rows = deposits(10)
        b = self.basis

        def totals(job):
            out = np.zeros(2)
            for _, _, c, pe, _, _ in digitize.digitize({**job, "timing": None}, rows)[0]:
                out[c] += pe
            return out
        P = np.stack([totals(DG.job_from_documents(PIPE, MAP, "ecal", [0, 1, 2, 3], 11, map_replica=r))
                      for r in range(1, 101)])
        key = rng.volume_key(11, "scintillation", 0)
        Nb = np.zeros(4)
        for e, v, bb, large, small, steps in rows:
            Nb[bb] += response.bin_photons(rng.SubStream(key, e, v, bb), 200.0, 0.6, large, small, steps, 1.0)
        J = np.zeros((2, 8))
        for bb in range(4):
            J[0, 2 * bb], J[1, 2 * bb + 1] = Nb[bb], Nb[bb]
        Ud, Ul = MB.u_digitized(P, b), MB.u_linear(J, b)
        self.assertLess(np.linalg.norm(Ud - Ul) / np.linalg.norm(Ul), 0.05)
        np.testing.assert_allclose(np.diag(Ud @ Ud.T) / np.diag(Ul @ Ul.T), 1.0, atol=0.05)


class TestStudies(unittest.TestCase):
    """Section 15.3a: the same map in two studies with opposite observable order."""

    def test_cross_covariance_native_basis_and_pca_by_index_rejected(self):
        b = MB.native_basis({1: MAP}, 100)
        rng_ = np.random.default_rng(4)
        Ja, Jb = rng_.normal(size=(4, 8)), rng_.normal(size=(3, 8))
        Ua, Ub = MB.u_linear(Ja, b), MB.u_linear(Jb[::-1], b)            # study b lists its observables reversed
        sa = MB.study(b["key"]["id"], ["a0", "a1", "a2", "a3"], Ua)
        sb = MB.study(b["key"]["id"], ["b2", "b1", "b0"], Ub)
        cc = MB.cross_covariance(sa, sb)["cov"]
        truth = Ja @ (b["B_map"] @ b["B_map"].T) @ Jb[::-1].T
        np.testing.assert_allclose(cc, truth, atol=1e-14)
        # the rejected construction: per-study PCAs joined by component index give another (wrong) answer
        pa, pb = MB.study_pca(sa["observables"], Ua), MB.study_pca(sb["observables"], Ub)
        k = min(pa["U"].shape[1], pb["U"].shape[1])
        wrong = pa["U"][:, :k] @ pb["U"][:, :k].T
        self.assertGreater(np.linalg.norm(wrong - truth), 0.1 * np.linalg.norm(truth))
        with self.assertRaises(MB.BasisError) as cm:
            MB.cross_covariance(pa, pb)
        self.assertEqual(cm.exception.code, "propagate.pca_by_index")
        other = MB.study("other", ["b2", "b1", "b0"], Ub)
        with self.assertRaises(MB.BasisError):
            MB.cross_covariance(sa, other)

    def test_local_reduction_and_export_map(self):
        b = MB.native_basis({1: MAP}, 100)
        J = np.ones((5, 8)) * np.arange(1, 9)                           # rank one: one direction suffices
        U = MB.u_linear(J, b)
        red = MB.local_reduction(U, np.eye(5) * 1e-6)
        self.assertEqual(red["m"], 1)
        rec = MB.study(b["key"]["id"], list("abcde"), red["U_loc"], local=red)
        np.testing.assert_allclose(MB.native_u(rec) @ MB.native_u(rec).T, U @ U.T, rtol=1e-8, atol=1e-18)
        Ufull = MB.u_linear(np.random.default_rng(2).normal(size=(6, 8)), b)
        self.assertTrue(MB.local_reduction(Ufull, np.eye(6) * 1e-12)["kept_all"])    # control: nothing discardable


# ------------------------------------------------------------------ joint-pattern replicas (D28)
class TestJointPattern(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.maps, cls.bins, cls.dets, cls.chans = MF.scan(photons=20000)
        cls.table = MB.pattern_table(cls.bins, cls.dets, cls.chans)
        cls.key = MB.scan_key([em.map_sha256(m) for m in cls.maps], 11, 0, 20000)
        cls.reps = MB.joint_replicas(cls.table, cls.chans, cls.key, 1, 200)
        cls.Sigma = MB.analytic_covariance(cls.table, cls.chans)

    def test_pattern_table_matches_the_maps(self):
        self.assertEqual(MB.pattern_findings(self.table, self.maps), [])
        bad = copy.deepcopy(self.table)
        bad[0][-1] += 1
        self.assertEqual(MB.pattern_findings(bad, self.maps)[0]["code"], "joint.counts")

    def test_marginal_is_g4sims_dirichlet(self):
        """Section 15.2 (map varies with theta): the marginal of the replicas at each design point agrees with
        g4sim's Dirichlet(k + 1/2): mean and variance within the finite-R tolerance (R = 200)."""
        for j, m in enumerate(self.maps):
            mean, var = MB.dirichlet_mean({1: m}), []
            for row in m["form"]["bins"]:
                a = np.r_[np.asarray(row["detected"]) + 0.5, row["emitted"] - sum(row["detected"]) + 0.5]
                A = a.sum()
                var += list(a[:-1] * (A - a[:-1]) / (A * A * (A + 1)))
            E = self.reps[j]
            se = np.sqrt(np.asarray(var) / 200)
            self.assertLess(np.max(np.abs(E.mean(0) - mean) / se), 4.0)
            np.testing.assert_allclose(E.var(0, ddof=1) / np.asarray(var), 1.0, atol=0.35)

    def test_cross_point_covariance_agrees_with_analytic_and_per_map_replicas_do_not(self):
        E = np.hstack(self.reps)
        n = self.reps[0].shape[1]
        d = np.sqrt(np.diag(self.Sigma))
        ana = self.Sigma[:n, n:2 * n] / np.outer(d[:n], d[n:2 * n])
        rep = np.corrcoef(E.T)[:n, n:2 * n]
        self.assertGreater(float(np.mean(np.diag(ana))), 0.8)                  # strongly coupled scan
        self.assertLess(np.max(np.abs(np.diag(rep) - np.diag(ana))), 0.1)      # finite-R tolerance at R = 200
        g0 = np.stack([MB.map_vector({1: self.maps[0]}, r) for r in range(1, 201)])
        g1 = np.stack([MB.map_vector({1: self.maps[1]}, r) for r in range(1, 201)])
        per_map = np.array([np.corrcoef(g0[:, i], g1[:, i])[0, 1] for i in range(n)])
        self.assertLess(float(np.mean(np.abs(per_map))), 0.2)                 # the D28 failure of per-map replicas

    def test_keys_and_registration(self):
        a = MB.joint_replica(self.table, self.chans, self.key, 1, 3)
        self.assertEqual(a, MB.joint_replica(self.table, self.chans, self.key, 1, 3))
        other = MB.scan_key([em.map_sha256(m) for m in self.maps], 12, 0, 20000)
        self.assertNotEqual(a, MB.joint_replica(self.table, self.chans, other, 1, 3))
        reg = MB.joint_registration_key(self.key, 1, self.table, self.chans, 200)
        self.assertEqual(reg["pattern_table_sha256"], MB.pattern_sha256(self.table))
        with self.assertRaises(MB.BasisError):
            MB.joint_replica(self.table, self.chans, self.key, 1, 0)

    def test_analytic_u_reproduces_the_weighted_covariance(self):
        rng_ = np.random.default_rng(3)
        Js = [rng_.normal(size=(4, r.shape[1])) for r in self.reps]
        U = MB.u_analytic(Js, self.Sigma)
        w = np.array([0.2, 0.5, 0.3])
        Ut = sum(wj * u for wj, u in zip(w, U))
        off = np.cumsum([0] + [J.shape[1] for J in Js])
        want = sum(w[j] * w[k] * Js[j] @ self.Sigma[off[j]:off[j + 1], off[k]:off[k + 1]] @ Js[k].T
                   for j in range(3) for k in range(3))
        np.testing.assert_allclose(Ut @ Ut.T, want, rtol=1e-8, atol=1e-14)


# ------------------------------------------------------------------ the map term of the likelihood
def surrogate(n=6, mode="regression", noise=0.01, seed=1):
    pts = [{"t0": x} for x in np.linspace(0.0, 2.0, n)]
    g = np.random.default_rng(seed)
    vals = np.array([[np.sin(p["t0"]), 0.5 * p["t0"]] for p in pts]) + noise * g.normal(size=(n, 2))
    return EM.Surrogate(["t0"], {"t0": [0.0, 2.0]}, pts, vals, mode=mode)


class MapProblem:
    """A linear Gaussian problem with the map term on its link rows."""

    def __init__(self, J, m0, V, y, term):
        n = len(m0)
        self.layout = L.build_layout([{"name": f"y{i}", "block": "gaussian"} for i in range(n)], ["t0"], [], 0, 0)
        self.layout.n_phi_map = 0 if term is None else term.n_phi
        self.observed = L.Observations(y_gauss=np.asarray(y, float))
        self.J, self.m0, self.V, self.term = np.asarray(J, float), np.asarray(m0, float), np.asarray(V, float), term
        self.edm_tol = 1e-4

    def h(self, tp):
        return self.m0 + self.J @ np.asarray(tp, float)

    def reference(self, tp, beta, frozen=None):
        n = len(self.m0)
        return L.Reference(V_G=self.V, V_std=np.diag(np.diag(self.V)), U=np.zeros((n, 0)), S=np.zeros((n, 0)),
                           map_term=self.term).finalize()

    def bounds(self):
        return [(-10.0, 10.0)]

    def prior_box(self):
        return [(0.0, 2.0)]


class TestMapTerm(unittest.TestCase):
    def test_fixed_map_profile_equals_marginal_gls(self):
        b = MB.native_basis({1: MAP}, 100)
        g = np.random.default_rng(5)
        Jeps = g.normal(size=(6, 8)) * 50
        U = MB.u_linear(Jeps, b)
        J, V = g.normal(size=(6, 1)), np.eye(6) * 0.01
        y = J[:, 0] * 0.7 + U @ g.normal(size=U.shape[1]) + g.normal(size=6) * 0.1
        term = MT.MapTerm([U], np.arange(6), 6, "fixed")
        pr = MapProblem(J, np.zeros(6), V, y, term)
        m = FIT.minimize(pr, pr.reference(None, None), np.zeros(1 + term.n_phi))
        th, chi2, cov = gls(J, V + U @ U.T, y)
        self.assertTrue(m.converged)
        self.assertLess(abs(m.beta[0] - th[0]), 1e-3 * np.sqrt(cov[0, 0]))
        self.assertAlmostEqual(m.D, chi2, places=4)
        pr0 = MapProblem(J, np.zeros(6), V, y, None)                     # control: without the term, plain GLS
        m0 = FIT.minimize(pr0, pr0.reference(None, None), np.zeros(1))
        self.assertGreater(abs(m0.beta[0] - th[0]), 0.01 * np.sqrt(cov[0, 0]))

    def test_shared_mode_is_profiled_with_theta(self):
        """U(theta) is evaluated at the theta of each step and its derivative enters the Jacobian (not held fixed)."""
        s = surrogate()
        g = np.random.default_rng(6)
        Us = [g.normal(size=(2, 5)) * (0.5 + 0.3 * j) for j in range(6)]
        term = MT.MapTerm(Us, [0, 1], 2, "shared", surrogate=s, theta_names=["t0"])
        pr = MapProblem(np.ones((2, 1)), np.zeros(2), np.eye(2), [0.3, -0.2], term)
        lk = L.Likelihood(pr.layout, pr.observed, pr.reference(None, None))
        beta = np.r_[0.8, g.normal(size=5)]
        H = FIT.jacobian(pr, beta[:1], [1e-6])
        grad, _ = lk.score_fisher(beta, pr.h(beta[:1]), H)
        num = []
        for i in range(beta.size):
            a, c = beta.copy(), beta.copy()
            a[i] += 1e-6
            c[i] -= 1e-6
            num.append((lk.deviance(a, pr.h(a[:1])) - lk.deviance(c, pr.h(c[:1]))) / 2e-6)
        np.testing.assert_allclose(grad, num, rtol=1e-5, atol=1e-6)
        # the theta derivative includes (d U / d theta) phi_map: without it the gradient would differ
        z = lk.eta_link(pr.h(beta[:1]), beta)
        np.testing.assert_allclose(z, pr.h(beta[:1]) + term.U({"t0": 0.8}) @ beta[1:])
        self.assertGreater(np.linalg.norm(term.derivatives({"t0": 0.8})[0]), 0.0)

    def test_independent_mode_blocks_and_layout_check(self):
        s = surrogate()
        Us = [np.full((2, 3), j + 1.0) for j in range(6)]
        term = MT.MapTerm(Us, [0, 1], 3, "independent", surrogate=s, theta_names=["t0"])
        self.assertEqual(term.n_phi, 18)
        w = s.weights({"t0": 0.5})
        np.testing.assert_allclose(term.U({"t0": 0.5})[:2, 3:6], w[1] * Us[1])
        self.assertTrue(np.all(term.U({"t0": 0.5})[2] == 0))
        pr = MapProblem(np.ones((3, 1)), np.zeros(3), np.eye(3), [0, 0, 0], term)
        pr.layout.n_phi_map = 5
        with self.assertRaises(L.LikelihoodError):
            L.Likelihood(pr.layout, pr.observed, pr.reference(None, None))
        with self.assertRaises(MT.MapTermError):
            MT.MapTerm(Us[:2], [0, 1], 3, "shared", surrogate=s, theta_names=["t0"])

    def test_fallback_nearest_design_point_held_fixed(self):
        s = surrogate()
        Us = [np.full((2, 3), j + 1.0) for j in range(6)]
        fb = MT.fallback_covariance(Us, s, {"t0": 0.79})
        self.assertEqual(fb["point"], 2)                            # design points at 0, 0.4, 0.8, ...
        np.testing.assert_allclose(fb["V_add"], Us[2] @ Us[2].T)
        self.assertFalse(fb["profiled"] or fb["exported"])


class TestSection152FixedMap(unittest.TestCase):
    """Section 15.2 (efficiency map phi): with the replica basis as phi_map, G7 passes and the 68% coverage holds; with
    the map error put into V_MC instead, G7's T is far below the median of chi2_{r(K-1)} (reported only), and without
    the map term the coverage fails (control)."""

    @classmethod
    def setUpClass(cls):
        cls.b = MB.native_basis({1: MAP}, 100)
        g = np.random.default_rng(8)
        cls.Jeps = np.abs(g.normal(size=(8, 8))) * 30
        cls.U = MB.u_linear(cls.Jeps, cls.b)
        cls.J = np.abs(g.normal(size=(8, 1))) + 0.5
        cls.UU = cls.U @ cls.U.T
        scale = float(np.mean(np.diag(cls.UU)))
        cls.Vd, cls.Vmc = np.eye(8) * scale, np.eye(8) * 0.3 * scale

    def test_g7(self):
        g = np.random.default_rng(9)
        C = self.Vd + self.Vmc + self.UU
        Ci = np.linalg.inv(C)
        A = np.linalg.solve(self.J.T @ Ci @ self.J, self.J.T @ Ci)
        y = g.normal(size=8)
        map_err = self.U @ g.normal(size=self.U.shape[1])           # one map: the same in every refit
        hats = np.array([A @ (y - map_err - g.multivariate_normal(np.zeros(8), self.Vmc)) for _ in range(20)])
        good = FIT.g7(hats, A @ self.Vmc @ A.T)
        bad = FIT.g7(hats, A @ (self.Vmc + self.UU) @ A.T)
        self.assertEqual(good["status"], "passed")
        self.assertLess(bad["T"], 0.5 * bad["df"])                  # far below the median: V_MC overestimated

    def test_coverage(self):
        centre = MB.dirichlet_mean({1: MAP})
        cover = {"with": 0, "without": 0}
        n = 200
        g = np.random.default_rng(10)
        for t in range(n):
            truth = self.Jeps @ (MB.map_vector({1: MAP}, 101 + t) - centre)
            y = 0.5 * self.J[:, 0] + truth + g.multivariate_normal(np.zeros(8), self.Vd)
            for name, C in (("with", self.Vd + self.UU), ("without", self.Vd)):
                th, _, cov = gls(self.J, C, y)
                cover[name] += abs(th[0] - 0.5) <= np.sqrt(cov[0, 0])
        self.assertTrue(0.60 <= cover["with"] / n <= 0.76, cover)
        self.assertLess(cover["without"] / n, 0.55)


# ------------------------------------------------------------------ calib_design items
class TestThetaNoise(unittest.TestCase):
    """Section 15.3.1 (P5): in the mode where the map varies with theta, P5 fails when s_i > 0.25 or kappa_i > 0.05 at
    the worst point, computed with Sigma_jl = 0 for independent seeds and in the fallback."""

    @classmethod
    def setUpClass(cls):
        cls.s = surrogate(noise=0.02)
        g = np.random.default_rng(11)
        base = g.normal(size=(2, 20))
        cls.U = [base + 0.3 * g.normal(size=(2, 20)) for _ in range(6)]
        cls.points = [{"theta": {"t0": x}, "V_G": np.eye(2)} for x in (0.3, 1.0, 1.7)]

    def run_(self, scale, seeding="shared"):
        return DM.theta_noise(self.s, self.points, {"t0": 0.3}, U_list=[scale * u for u in self.U], seeding=seeding)

    def test_negative_and_positive(self):
        ok, bad = self.run_(0.05), self.run_(1.0)
        self.assertTrue(ok["passed"], ok)
        self.assertFalse(bad["passed"])
        self.assertEqual(bad["finding"], "p5.theta_noise")
        self.assertIn("provisional-thresholds", bad["flags"])

    def test_independent_seeds_and_analytic_path(self):
        sh, ind = self.run_(1.0), self.run_(1.0, "independent")
        self.assertGreaterEqual(ind["per_parameter"]["t0"]["s"], sh["per_parameter"]["t0"]["s"])
        Sig = np.array([[u @ v.T for v in self.U] for u in self.U])
        an = DM.theta_noise(self.s, self.points, {"t0": 0.3}, Sigma=Sig, seeding="shared")
        self.assertAlmostEqual(an["per_parameter"]["t0"]["s"], sh["per_parameter"]["t0"]["s"], places=10)
        an0 = DM.theta_noise(self.s, self.points, {"t0": 0.3}, Sigma=Sig, seeding="fallback")
        self.assertAlmostEqual(an0["per_parameter"]["t0"]["kappa"], ind["per_parameter"]["t0"]["kappa"], places=10)


def dirichlet_toys(B, k, n_b, ratio, R, lowrank=False):
    """A fast synthetic replica source with g4sim's replica law Dirichlet(k + 1/2) (one channel per bin)."""
    a = np.c_[np.full(B, k + 0.5), np.full(B, n_b - k + 0.5)]
    Jeps = np.vstack([np.eye(B), np.ones((1, B))])
    if lowrank:
        two = np.vstack([np.ones(B), np.r_[np.ones(B // 2), np.zeros(B - B // 2)]])
        Jeps = np.vstack([two] * 10 + [two[:1]])
    mean = a[:, 0] / a.sum(1)
    msd = np.sqrt(Jeps ** 2 @ (mean * (1 - mean) / (a.sum(1) + 1)))
    V = np.diag((msd / ratio) ** 2)
    J = np.linspace(1, 2, Jeps.shape[0])[:, None] * msd[:, None]

    def draw_set(t):
        g = np.random.default_rng([7, t])
        e, f = g.gamma(a[:, 0], size=(R, B)), g.gamma(a[:, 1], size=(R, B))
        return (e / (e + f)) @ Jeps.T

    def draw_truth(t):
        g = np.random.default_rng([8, t])
        e, f = g.gamma(a[:, 0]), g.gamma(a[:, 1])
        return Jeps @ (e / (e + f) - mean)
    return J, V, draw_set, draw_truth


class TestD84(unittest.TestCase):
    def test_too_few_replicas_with_many_directions_detected(self):
        J, V, ds, dt = dirichlet_toys(20, 30, 1000, 3.0, 100)
        r = DM.g6_size(J, V, ds, dt, 2000)
        self.assertFalse(r["passed"])
        self.assertGreater(r["interval"][0], 1.5 * 0.01)
        self.assertEqual(r["finding"], "design.g6_size_d84")
        self.assertEqual(len(r["remedies"]), 2)

    def test_positive_controls(self):
        for kw in ({"lowrank": True}, {}):
            ratio = 3.0 if kw else 0.3
            J, V, ds, dt = dirichlet_toys(20, 30, 1000, ratio, 100, **kw)
            r = DM.g6_size(J, V, ds, dt, 2000)
            self.assertTrue(r["passed"], (kw, r["size"]))

    def test_g4sim_replicas_beyond_R(self):
        Jeps = np.eye(8) * 100
        ds, dt = DM.g4sim_replica_toys({1: MAP}, Jeps, 100)
        first = ds(0)
        np.testing.assert_allclose(first[0], Jeps @ MB.map_vector({1: MAP}, 101))
        r = DM.g6_size(np.ones((8, 1)), np.eye(8) * 0.1, ds, dt, 3)
        self.assertEqual(r["R"], 100)


def varies_plan(**scan):
    s = {"seeding": "shared", "map_term": "joint-pattern", "N_map": 1000, "R": 200, "pattern_table": True}
    s.update(scan)
    evs = [{"run_id": f"m{j}", "use": "mapping-run", "scan": "s", "point": j, "logical_run_seed": 5,
            "first_event": 0, "events": 1000, "run_seed": 5, "replica": 0} for j in range(3)]
    return {"efficiency_map": {"mode": "varies-with-theta", "linear_in_eps": ["sum"]},
            "design": {"surrogate": {"mode": "regression"}}, "mapping_scans": {"s": s}, "evaluations": evs}


class TestMapPlan(unittest.TestCase):
    """Section 15.3.19: the map-varies-with-theta rejections and the fixed-map linear construction."""

    def codes(self, plan, tn=None):
        return [f["code"] for f in DM.map_plan_findings(plan, tn)]

    def test_positive_control(self):
        self.assertEqual(self.codes(varies_plan()), [])
        self.assertEqual(DM.mapping_seed_findings(varies_plan()), [])
        self.assertEqual(DG.interval_findings(varies_plan())["status"], "passed")   # WP-B's check, reused

    def test_rejected_practices(self):
        cases = {"design.map_per_map_replicas": varies_plan(map_term="g4sim-replicas"),
                 "design.map_comonotone_replicas": varies_plan(map_term="common-uniforms"),
                 "design.map_coupled_independent": varies_plan(seeding="independent", map_term="joint-pattern"),
                 "design.map_no_pattern_table": varies_plan(pattern_table=False),
                 "design.map_analytic_nonlinear": varies_plan(map_term="analytic", observables=["sum", "width"]),
                 "design.map_replicas": varies_plan(R=50)}
        for code, plan in cases.items():
            self.assertIn(code, self.codes(plan), code)
        p = varies_plan()
        p["design"]["surrogate"]["mode"] = "interpolate"
        self.assertIn("design.map_interpolating_surrogate", self.codes(p))
        self.assertIn("design.map_comonotone_replicas", self.codes(varies_plan(map_term="scan-key",
                                                                                seeding="independent")))

    def test_independent_seeds_need_a_passing_theta_noise_item(self):
        p = varies_plan(seeding="independent", map_term="g4sim-replicas")
        self.assertEqual(self.codes(p), ["design.map_independent_theta_noise"])
        self.assertEqual(self.codes(p, {"seeding": "independent", "passed": False}),
                         ["design.map_independent_theta_noise"])
        self.assertEqual(self.codes(p, {"seeding": "shared", "passed": True}), ["design.map_independent_theta_noise"])
        self.assertEqual(self.codes(p, {"seeding": "independent", "passed": True}), [])

    def test_shared_seed_and_interval(self):
        p = varies_plan()
        p["evaluations"][1]["logical_run_seed"] = 6
        p["evaluations"][1]["run_seed"] = 6
        p["evaluations"][2]["first_event"] = 10
        codes = [f["code"] for f in DM.mapping_seed_findings(p)]
        self.assertIn("design.map_shared_seed", codes)
        self.assertIn("design.map_shared_interval", codes)

    def test_nongaussian_block_rule(self):
        """Map varies with theta: a map-affected Poisson or binomial observable must be Gaussian or predicted through the
        surrogate (section 6.7)."""
        contract = {"observables": [{"name": "sum", "block": "gaussian"}, {"name": "hits", "block": "poisson"},
                                    {"name": "eff", "block": "binomial"}]}
        p = varies_plan(observables=["sum"])
        self.assertEqual([f["code"] for f in DM.map_plan_findings(p, None, contract)], [])
        p["efficiency_map"]["affected"] = ["hits", "eff"]
        self.assertEqual([f["code"] for f in DM.map_plan_findings(p, None, contract)],
                         ["design.map_nongaussian_block"] * 2)
        p["efficiency_map"]["through_surrogate"] = ["hits", "eff"]
        self.assertEqual(DM.map_plan_findings(p, None, contract), [])
        p["efficiency_map"]["affected"].append("nope")
        self.assertEqual([f["code"] for f in DM.map_plan_findings(p, None, contract)], ["design.map_observable_unknown"])
        fixed = {"efficiency_map": {"mode": "fixed", "affected": ["hits"]}}
        self.assertEqual(DM.map_plan_findings(fixed, None, contract), [])          # the rule is for the varying map

    def test_fixed_map_linear_construction_only_for_linear_observables(self):
        p = {"efficiency_map": {"mode": "fixed", "R": 100, "linear_in_eps": ["sum"],
                                "u_construction": {"sum": "linear", "width": "digitized"}}}
        self.assertEqual(self.codes(p), [])
        p["efficiency_map"]["u_construction"]["width"] = "linear"
        self.assertEqual(self.codes(p), ["design.map_linear_not_linear"])


class TestScanChecks(unittest.TestCase):
    def test_primaries_agreement(self):
        rows = [[e, 0, 1.0 * e, 2.0, 3.0] for e in range(5)]
        self.assertEqual(DM.primaries_findings({"p0": rows, "p1": copy.deepcopy(rows)}), [])
        other = copy.deepcopy(rows)
        other[3][2] = 9.0
        f = DM.primaries_findings({"p0": rows, "p1": other})
        self.assertEqual((f[0]["code"], f[0]["event"]), ("design.map_primaries", "3"))
        self.assertEqual(DM.primaries_findings({"p0": rows, "p1": rows[:4]})[0]["code"], "design.map_primaries")

    def test_job_route_reproduces_map_replica(self):
        rows = deposits(6)
        self.assertEqual(DM.job_route_findings(PIPE, MAP, "ecal", rows, 5), [])
        job = DG.job_from_documents(PIPE, MAP, "ecal", [0, 1, 2, 3], 11, map_replica=6)    # another replica
        self.assertEqual(DM.job_route_findings(PIPE, MAP, "ecal", rows, 5, job=job)[0]["code"], "design.map_job_route")

    def test_d83_1_exemption(self):
        doc = copy.deepcopy(MAP)
        doc["source_of_facts"] = "mapping run x"
        doc["form"]["uniformity"] = em.transverse_uniformity(doc)
        errs = [{"path": f.path, "code": f.code, "message": f.message} for f in validate(doc, "efficiency_map.json").errors]
        r = DM.map_schema_findings(errs)
        self.assertEqual((r["status"], r["known_defects"]), ("passed", ["D83 (1)"]))
        del doc["source_of_facts"]
        errs = [{"path": f.path, "code": f.code, "message": f.message} for f in validate(doc, "efficiency_map.json").errors]
        self.assertEqual(DM.map_schema_findings(errs)["status"], "failed")


if __name__ == "__main__":
    unittest.main()
