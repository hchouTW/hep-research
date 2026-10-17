"""Tests for core/kinematics/fourvector.py (Th7): two-body decays (Kallen function), Lorentz boosts, invariant
masses, Mandelstam variables, reaction thresholds, Dalitz boundaries, rapidity and pseudorapidity, and width,
lifetime and c tau. Oracles: energy and momentum conservation; the invariant mass is unchanged by a boost;
s + t + u equals the sum of the squared masses; Dalitz points from sequential decays lie inside the boundary.
Masses are SYNTHETIC inputs in GeV. Standard library only."""
import math
import random
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from core.kinematics import fourvector as fv  # noqa: E402
from core.kinematics.relativistic import KinematicsError  # noqa: E402

TOL = 1e-9


def random_direction(rng):
    cos_t, phi = rng.uniform(-1, 1), rng.uniform(0, 2 * math.pi)
    sin_t = math.sqrt(1 - cos_t * cos_t)
    return (sin_t * math.cos(phi), sin_t * math.sin(phi), cos_t)


def random_beta(rng, max_beta=0.95):
    b = rng.uniform(0, max_beta)
    return tuple(b * c for c in random_direction(rng))


class KallenAndTwoBody(unittest.TestCase):
    def test_kallen_symmetric_and_zero_at_threshold(self):
        self.assertEqual(fv.kallen(1.0, 2.0, 3.0), fv.kallen(3.0, 1.0, 2.0))
        self.assertAlmostEqual(fv.kallen(9.0, 4.0, 1.0), 81 + 16 + 1 - 72 - 18 - 8)
        self.assertAlmostEqual(fv.kallen((1.0 + 2.0) ** 2, 1.0, 4.0), 0.0, delta=1e-12)

    def test_two_body_momentum_against_closed_forms(self):
        # massless daughters: p* = M/2; one massless: p* = (M^2 - m^2) / 2M
        self.assertAlmostEqual(fv.two_body_momentum(3.0, 0.0, 0.0), 1.5, delta=1e-15)
        self.assertAlmostEqual(fv.two_body_momentum(3.0, 1.0, 0.0), (9.0 - 1.0) / 6.0, delta=1e-15)
        d = fv.two_body_decay(0.497611, 0.13957039, 0.13957039)  # SYNTHETIC K0 -> pi pi masses
        self.assertAlmostEqual(d["E1"] + d["E2"], 0.497611, delta=1e-12)
        self.assertAlmostEqual(d["p"], math.sqrt(0.497611 ** 2 / 4 - 0.13957039 ** 2), delta=1e-12)

    def test_closed_channel_is_refused(self):
        with self.assertRaises(KinematicsError):
            fv.two_body_momentum(0.2, 0.13957039, 0.13957039)
        with self.assertRaises(KinematicsError):
            fv.two_body_momentum(-1.0, 0.0, 0.0)

    def test_conservation_after_decay_and_boost(self):
        rng = random.Random(7)
        for _ in range(200):
            M = rng.uniform(1.0, 10.0)
            m1, m2 = rng.uniform(0, M / 2.2), rng.uniform(0, M / 2.2)
            p = fv.two_body_momentum(M, m1, m2)
            n = random_direction(rng)
            d1 = (math.hypot(p, m1), p * n[0], p * n[1], p * n[2])
            d2 = (math.hypot(p, m2), -p * n[0], -p * n[1], -p * n[2])
            parent = (M, 0.0, 0.0, 0.0)
            beta = random_beta(rng)
            b1, b2, bp = (fv.boost(v, beta) for v in (d1, d2, parent))
            for i in range(4):
                self.assertAlmostEqual(b1[i] + b2[i], bp[i], delta=TOL * max(1.0, abs(bp[i])))
            self.assertAlmostEqual(fv.invariant_mass(b1, b2), M, delta=TOL * M)
            self.assertAlmostEqual(fv.invariant_mass(b1), m1, delta=1e-7 * max(M, 1))


class Boosts(unittest.TestCase):
    def test_boost_preserves_invariant_mass_and_inverts(self):
        rng = random.Random(11)
        for _ in range(200):
            m = rng.uniform(0, 5)
            p = [rng.uniform(-20, 20) for _ in range(3)]
            v = (math.sqrt(m * m + sum(x * x for x in p)), *p)
            beta = random_beta(rng, 0.99)
            w = fv.boost(v, beta)
            self.assertAlmostEqual(fv.mass_squared(w), fv.mass_squared(v), delta=1e-8 * v[0] ** 2)
            back = fv.boost(w, tuple(-b for b in beta))
            for a, b in zip(back, v):
                self.assertAlmostEqual(a, b, delta=1e-9 * max(1.0, v[0]))

    def test_rest_frame(self):
        v = (5.0, 1.0, 2.0, 3.0)
        r = fv.boost(v, fv.beta_of(v))
        self.assertAlmostEqual(r[0], math.sqrt(fv.mass_squared(v)), delta=1e-12)
        for x in r[1:]:
            self.assertAlmostEqual(x, 0.0, delta=1e-12)

    def test_superluminal_boost_is_refused(self):
        with self.assertRaises(KinematicsError):
            fv.boost((1.0, 0, 0, 0), (0.6, 0.8, 0.1))


class Mandelstam(unittest.TestCase):
    def test_s_plus_t_plus_u_equals_sum_of_masses_squared(self):
        rng = random.Random(3)
        for _ in range(200):
            m1, m2, m3, m4 = (rng.uniform(0, 2) for _ in range(4))
            sqrt_s = m1 + m2 + m3 + m4 + rng.uniform(0.1, 10)
            pi = fv.two_body_momentum(sqrt_s, m1, m2)
            pf = fv.two_body_momentum(sqrt_s, m3, m4)
            n = random_direction(rng)
            p1 = (math.hypot(pi, m1), 0.0, 0.0, pi)
            p2 = (math.hypot(pi, m2), 0.0, 0.0, -pi)
            p3 = (math.hypot(pf, m3), pf * n[0], pf * n[1], pf * n[2])
            p4 = (math.hypot(pf, m4), -pf * n[0], -pf * n[1], -pf * n[2])
            beta = random_beta(rng)
            p1, p2, p3, p4 = (fv.boost(v, beta) for v in (p1, p2, p3, p4))
            s, t, u = fv.mandelstam(p1, p2, p3, p4)
            self.assertAlmostEqual(s, sqrt_s ** 2, delta=1e-8 * s)
            self.assertAlmostEqual(s + t + u, m1 ** 2 + m2 ** 2 + m3 ** 2 + m4 ** 2, delta=1e-7 * s)


class Thresholds(unittest.TestCase):
    def test_antiproton_production_threshold(self):
        # p p -> p p p pbar on a proton at rest: E_beam = 7 m_p, kinetic 6 m_p (textbook result)
        mp = 0.938
        th = fv.fixed_target_threshold(mp, mp, [mp, mp, mp, mp])
        self.assertAlmostEqual(th["beam_energy"], 7 * mp, delta=1e-12)
        self.assertAlmostEqual(th["beam_kinetic_energy"], 6 * mp, delta=1e-12)
        self.assertAlmostEqual(th["sqrt_s"], 4 * mp, delta=1e-12)

    def test_below_beam_mass_is_open(self):
        th = fv.fixed_target_threshold(1.0, 1.0, [0.5, 0.5])
        self.assertEqual(th["beam_kinetic_energy"], 0.0)
        self.assertTrue(th["open_at_rest"])


class Dalitz(unittest.TestCase):
    def test_sequential_decays_lie_inside_the_boundary(self):
        rng = random.Random(5)
        M, m1, m2, m3 = 1.86484, 0.493677, 0.13957039, 0.1349768  # SYNTHETIC D0 -> K pi pi0 masses
        lo, hi = fv.dalitz_m12_range(M, m1, m2, m3)
        self.assertAlmostEqual(lo, (m1 + m2) ** 2)
        self.assertAlmostEqual(hi, (M - m3) ** 2)
        for _ in range(500):
            m12sq = rng.uniform(lo, hi)
            m23_lo, m23_hi = fv.dalitz_m23_range(M, m1, m2, m3, m12sq)
            # build the point: (12) system and particle 3 back to back, then 12 -> 1 2 in its rest frame
            m12 = math.sqrt(m12sq)
            p3 = fv.two_body_momentum(M, m12, m3)
            q = fv.two_body_momentum(m12, m1, m2)
            n = random_direction(rng)
            p1r = (math.hypot(q, m1), q * n[0], q * n[1], q * n[2])
            p2r = (math.hypot(q, m2), -q * n[0], -q * n[1], -q * n[2])
            beta12 = (0.0, 0.0, p3 / math.hypot(p3, m12))
            p2 = fv.boost(p2r, tuple(-b for b in beta12))
            p3v = (math.hypot(p3, m3), 0.0, 0.0, -p3)
            m23sq = fv.mass_squared(tuple(a + b for a, b in zip(p2, p3v)))
            self.assertGreaterEqual(m23sq, m23_lo - 1e-9)
            self.assertLessEqual(m23sq, m23_hi + 1e-9)

    def test_outside_the_m12_range_is_refused(self):
        with self.assertRaises(KinematicsError):
            fv.dalitz_m23_range(1.0, 0.3, 0.3, 0.3, 0.1)


class RapidityAndLifetime(unittest.TestCase):
    def test_rapidity_equals_pseudorapidity_for_massless_and_shifts_under_z_boost(self):
        v = (10.0, 3.0, 0.0, 9.539392014169456)
        self.assertAlmostEqual(fv.rapidity(v), fv.pseudorapidity(v), delta=1e-12)
        m = (5.0, 1.0, 2.0, 3.0)
        b = 0.4
        w = fv.boost(m, (0.0, 0.0, b))
        self.assertAlmostEqual(fv.rapidity(w), fv.rapidity(m) - math.atanh(b), delta=1e-12)
        self.assertAlmostEqual(fv.pseudorapidity((1.0, 1.0, 0.0, 0.0)), 0.0, delta=1e-15)
        with self.assertRaises(KinematicsError):
            fv.pseudorapidity((1.0, 0.0, 0.0, 1.0))  # along the axis: infinite

    def test_width_lifetime_ctau_round_trip(self):
        tau = 2.6033e-8  # s, SYNTHETIC charged-pion-like mean life
        out = fv.lifetime_relations(lifetime_s=tau)
        self.assertAlmostEqual(out["ctau_m"], tau * 299792458.0, delta=1e-12)
        back = fv.lifetime_relations(width_gev=out["width_gev"])
        self.assertAlmostEqual(back["lifetime_s"] / tau, 1.0, delta=1e-14)
        self.assertAlmostEqual(out["width_gev"] * tau, 6.582119569e-25, delta=1e-33)  # hbar in GeV s
        with self.assertRaises(KinematicsError):
            fv.lifetime_relations(lifetime_s=tau, width_gev=1.0)
        with self.assertRaises(KinematicsError):
            fv.lifetime_relations(ctau_m=-1.0)


if __name__ == "__main__":
    unittest.main()
