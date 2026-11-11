"""Propagation by the principal components of the joint posterior and the conflict rules (Part B section 10.4,
15.3.17, 15.3a; phase 2, WP6)."""
from __future__ import annotations

import hashlib
import sys
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from core.calibration import deps  # noqa: E402
from core.calibration import propagate as P  # noqa: E402

V = 0.09


def two_segments(seed=3, phi_sign=1.0):
    """Segment 1: theta1 (2) with eta and a shared phi, their responses partly along theta1's column so the posterior
    correlates theta1, eta and phi; segment 2: theta2 (1), theta1 as a central upstream, eta measured strongly."""
    rng = np.random.default_rng(seed)
    n1, n2 = 15, 10
    J1 = rng.normal(size=(n1, 2))
    s1 = J1[:, 0] + 0.3 * rng.normal(size=n1)
    p1 = phi_sign * 0.8 * J1[:, 0] + 0.3 * rng.normal(size=n1)
    J2 = rng.normal(size=(n2, 1))
    K2 = rng.normal(size=(n2, 2)) * 0.7
    s2 = rng.normal(size=n2) * 2.0
    p2 = rng.normal(size=n2) * 0.3
    th1, th2, eta, phi = np.array([0.4, -0.2]), np.array([0.7]), 0.3, -0.5
    y1 = J1 @ th1 + s1 * eta + p1 * phi + rng.normal(size=n1) * np.sqrt(V)
    y2 = J2 @ th2 + K2 @ th1 + s2 * eta + p2 * phi + rng.normal(size=n2) * np.sqrt(V)
    return dict(J1=J1, s1=s1, p1=p1, J2=J2, K2=K2, s2=s2, p2=p2, y1=y1, y2=y2, n1=n1, n2=n2)


def gls(X, y, prior_prec, prior_mean):
    A = X.T @ X / V + prior_prec
    C = np.linalg.inv(A)
    return C @ (X.T @ y / V + prior_prec @ prior_mean), C


def joint_fit(s):
    n1, n2 = s["n1"], s["n2"]
    X = np.zeros((n1 + n2, 5))
    X[:n1, :2], X[:n1, 3], X[:n1, 4] = s["J1"], s["s1"], s["p1"]
    X[n1:, :2], X[n1:, 2:3], X[n1:, 3], X[n1:, 4] = s["K2"], s["J2"], s["s2"], s["p2"]
    b, C = gls(X, np.r_[s["y1"], s["y2"]], np.diag([0, 0, 0, 1.0, 1.0]), np.zeros(5))
    return b[:3], C[:3, :3]


def segment1(s):
    X1 = np.c_[s["J1"], s["s1"], s["p1"]]
    return gls(X1, s["y1"], np.diag([0, 0, 1.0, 1.0]), np.zeros(4))


def segment2(s, th1hat, Gx, Gz, zmean, Sz):
    n2 = s["n2"]
    Xs = np.zeros((n2, 5))
    Xs[:, 0:1], Xs[:, 1:3] = s["J2"], s["K2"] @ Gx
    Xs[:, 3:5] = s["K2"] @ Gz + np.c_[s["s2"], s["p2"]]
    off = s["K2"] @ (th1hat - Gz @ zmean)
    Pm = np.zeros((5, 5))
    Pm[1:3, 1:3] = np.eye(2)
    Pm[3:5, 3:5] = np.linalg.inv(Sz)
    pm = np.zeros(5)
    pm[3:5] = zmean
    est, C = gls(Xs, s["y2"] - off, Pm, pm)
    th1 = th1hat + Gx @ est[1:3] + Gz @ (est[3:5] - zmean)
    T = np.zeros((3, 5))
    T[:2, 1:3], T[:2, 3:5], T[2, 0] = Gx, Gz, 1.0
    return np.r_[th1, est[0]], T @ C @ T.T


def agree(a, Ca, b, Cb):
    """The gate-2 criteria: |delta theta| <= 0.1 sigma, |sigma ratio - 1| <= 0.1, correlations within 0.1."""
    sa, sb = np.sqrt(np.diag(Ca)), np.sqrt(np.diag(Cb))
    ra, rb = Ca / np.outer(sa, sa), Cb / np.outer(sb, sb)
    return bool(np.all(np.abs(a - b) <= 0.1 * sb) and np.all(np.abs(sa / sb - 1) <= 0.1)
                and np.all(np.abs(ra - rb) <= 0.1))


class Segmented(unittest.TestCase):
    def setUp(self):
        self.s = two_segments()
        self.bj, self.Cj = joint_fit(self.s)
        b1, C1 = segment1(self.s)
        self.b1, self.C1 = b1, C1
        self.pkg = P.export(b1[:2], b1[2:], C1, [0, 1], [2, 3], zeta_keys=["eta:release", "phi:thickness"])

    def test_joint_posterior_export_equals_the_joint_fit(self):
        seg, Cs = segment2(self.s, self.pkg["theta_hat"], self.pkg["G_xi"], self.pkg["G_zeta"],
                           self.pkg["zeta_hat"], self.pkg["Sigma_zeta"])
        np.testing.assert_allclose(seg, self.bj, atol=1e-10)
        np.testing.assert_allclose(Cs, self.Cj, rtol=1e-8, atol=1e-12)
        self.assertTrue(agree(seg, Cs, self.bj, self.Cj))

    def test_variance_identity(self):
        np.testing.assert_allclose(P.variance(self.pkg), self.C1[:2, :2], rtol=1e-10)

    def test_prior_in_place_of_the_posterior_fails(self):
        """The prior N(0, 1) substituted for the exported posterior (counterexample of section 15.3.17)."""
        seg, Cs = segment2(self.s, self.pkg["theta_hat"], self.pkg["G_xi"], self.pkg["G_zeta"], np.zeros(2),
                           np.eye(2))
        self.assertFalse(agree(seg, Cs, self.bj, self.Cj))

    def test_marginal_regressions_fail(self):
        """Two marginal regressions, each component constraining independently, with correlated eta and phi."""
        Gm = P.marginal_regressions(self.C1, [0, 1], [2], [3])
        D = np.diag(np.diag(self.C1)[2:])
        seg, Cs = segment2(self.s, self.b1[:2], self.pkg["G_xi"], Gm, self.b1[2:], D)
        self.assertFalse(agree(seg, Cs, self.bj, self.Cj))
        exported = self.pkg["G_xi"] @ self.pkg["G_xi"].T + Gm @ D @ Gm.T
        self.assertGreater(abs(exported[0, 0] / self.C1[0, 0] - 1), 0.1)

    def test_downstream_constraint_and_version(self):
        dc = P.downstream_constraint(self.pkg)
        np.testing.assert_allclose(dc["zeta"]["cov"], self.pkg["Sigma_zeta"])
        self.assertTrue(dc["no_extra_zeta_prior"])
        payload = {"contract_sha256": "a" * 64, "data_sha256": "b" * 64, "plan_sha256": "c" * 64,
                   "engine_version": "phase-2", "parent_versions": [], "values": {"theta": [0.1]}}
        v1, v2 = P.version(payload), P.version(dict(payload))
        self.assertEqual(v1, v2)
        self.assertNotEqual(v1["version_id"], P.version({**payload, "values": {"theta": [0.2]}})["version_id"])


H = {k: hashlib.sha256(k.encode()).hexdigest() for k in "ABCDEFGH"}


def ups(edges):
    return {r: [{"result_sha256": H[u], "usages": ["xi"]} for u in us] for r, us in edges.items()}


class Conflicts(unittest.TestCase):
    def test_four_shapes_require_a_joint_fit(self):
        """The four shapes of section 10.4 on four distinct dependency graphs (review F11), each a source overlap."""
        A, B, C, D, E = (H[k] for k in "ABCDE")
        u = {H[k]: v for k, v in ups({"B": ["A"], "C": ["A"]}).items()}
        # sibling: two shared-nuisance versions, updated by B and by C, both with xi_A as central input
        sib = deps.check_packages([{"id": "p1", "upstream": D, "zeta_updaters": {"eta1": B}},
                                   {"id": "p2", "upstream": E, "zeta_updaters": {"eta2": C}}], u)
        self.assertEqual([f["code"] for f in sib], ["deps.source_overlap"])
        # triangle: xi_A together with the version updated by B, which has A as central upstream
        tri = deps.check_packages([{"id": "p1", "upstream": A},
                                   {"id": "p2", "upstream": D, "zeta_updaters": {"eta": B}}], u)
        self.assertEqual([f["code"] for f in tri], ["deps.source_overlap"])
        # xi and xi: the xi packages of two results with the same central upstream
        xx = deps.check_packages([{"id": "p1", "upstream": B}, {"id": "p2", "upstream": C}], u)
        self.assertEqual([f["code"] for f in xx], ["deps.source_overlap"])
        # parent-child: xi of R1 = A and of R2 = B with A central
        pc = deps.check_packages([{"id": "p1", "upstream": A}, {"id": "p2", "upstream": B}], u)
        self.assertEqual([f["code"] for f in pc], ["deps.source_overlap"])
        # the same graphs without the shared upstream: no finding
        u0 = {H[k]: v for k, v in ups({"B": ["D"], "C": ["E"]}).items()}
        self.assertEqual(deps.check_packages([{"id": "p1", "upstream": B}, {"id": "p2", "upstream": C}], u0), [])

    def test_parent_child_counterexample_from_exported_packages(self):
        """The parent-child counterexample through the engine's exports: R2 calibrated with R1's theta_1 as a
        central input, joint covariance [[1, -1], [-1, 2]]. Combining the two packages as if independent gives
        Var(theta_1 + theta_2) = 3; the joint treatment (R2's zeta set to R1's theta_1) gives the correct 1."""
        Sigma = np.array([[1.0, -1.0], [-1.0, 2.0]])
        th = np.array([0.3, 0.7])
        p1 = P.export(th[[0]], np.zeros(0), Sigma, [0], [])
        p2 = P.export(th[[1]], th[[0]], Sigma, [1], [0])
        rng = np.random.default_rng(20261111)
        n = 200_000
        x1 = rng.normal(size=(n, p1["G_xi"].shape[1]))
        x2 = rng.normal(size=(n, p2["G_xi"].shape[1]))
        t1 = np.array([P.theta_of(p1, a, [])[0] for a in x1[:20000]])
        joint = np.array([P.theta_of(p2, b, [a])[0] for a, b in zip(t1, x2[:20000])]) + t1
        z_ind = rng.normal(p2["zeta_hat"][0], np.sqrt(p2["Sigma_zeta"][0, 0]), 20000)
        indep = np.array([P.theta_of(p2, b, [z])[0] for z, b in zip(z_ind, x2[:20000])]) + t1
        self.assertAlmostEqual(float(np.var(joint)), 1.0, delta=0.05)
        self.assertAlmostEqual(float(np.var(indep)), 3.0, delta=0.15)
        self.assertAlmostEqual(float(P.variance(p1)[0, 0] + P.variance(p2)[0, 0]), 3.0, places=12)

    def test_disjoint_sources_need_more_than_lineage_of_results(self):
        u = {}
        r = deps.check_packages([{"id": "p1", "upstream": H["D"]}, {"id": "p2", "upstream": H["E"]}], u,
                                common_sources={"p1": {"raw:run-7"}, "p2": {"raw:run-7"}})
        self.assertEqual(r[0]["code"], "deps.common_source")
        self.assertEqual(deps.check_packages([{"id": "p1", "upstream": H["D"]},
                                              {"id": "p2", "upstream": H["E"]}], u), [])

    def test_versions_and_packages(self):
        r = deps.check_packages([{"id": "p1", "upstream": H["D"], "zeta": {"eta": "v1"}},
                                 {"id": "p2", "upstream": H["E"], "zeta": {"eta": "v2"}}], {})
        self.assertEqual(r[0]["code"], "deps.version_conflict")
        same = deps.check_packages([{"id": "p1", "upstream": H["D"], "zeta": {"eta": "v1"}},
                                    {"id": "p2", "upstream": H["E"], "zeta": {"eta": "v1"}}], {})
        self.assertEqual(same, [])
        split = deps.check_packages([{"id": "p1", "upstream": H["D"], "zeta": {"eta": "v2"},
                                      "exported_zeta": {"eta": "v1"}}], {})
        self.assertEqual(split[0]["code"], "deps.package_split")
        tn = deps.check_packages([{"id": "p1", "upstream": H["D"], "exports": ["theta", "nu"]}], {})
        self.assertEqual(tn[0]["code"], "deps.theta_nu_split")

    def test_joint_factor_resolves_overlap(self):
        u = {H["B"]: [{"result_sha256": H["A"], "usages": ["xi"]}]}
        r = deps.check_packages([{"id": "p1", "upstream": H["A"], "joint_factor": ["p1", "p2"]},
                                 {"id": "p2", "upstream": H["B"]}], u)
        self.assertEqual(r, [])

    def test_numbers_instead_of_hashes_rejected(self):
        self.assertFalse(deps.is_hash_reference("0.123"))
        self.assertTrue(deps.is_hash_reference(H["A"]))


if __name__ == "__main__":
    unittest.main()
