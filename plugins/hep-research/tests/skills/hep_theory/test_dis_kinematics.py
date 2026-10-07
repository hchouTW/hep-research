"""DIS kinematics (hep-theory): the closed forms in references/dis-kinematics.md and scripts/dis_kinematics.py
agree with four-vector arithmetic; unphysical inputs are refused; no experiment is named. All inputs are SYNTHETIC."""
import json
import math
import random
import re
import subprocess
import sys
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[3]
SCRIPT = PLUGIN / "skills" / "hep-theory" / "scripts" / "dis_kinematics.py"
REF = PLUGIN / "skills" / "hep-theory" / "references" / "dis-kinematics.md"
SKILL = PLUGIN / "skills" / "hep-theory" / "SKILL.md"
sys.path.insert(0, str(SCRIPT.parent))
import dis_kinematics as dk  # noqa: E402

M = 0.938          # SYNTHETIC nucleon mass in GeV for the tests; the script takes M as an input
TOL = 1e-9


def run(*args):
    p = subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True)
    return p.returncode, p.stdout, p.stderr


def random_event(rng, E_l, E_h, m_l=0.0, theta_c=0.0):
    """k along the lepton beam, P along the hadron beam, k' scattered with energy fraction f and polar angle th."""
    pl, ph = math.sqrt(E_l**2 - m_l**2), math.sqrt(E_h**2 - M**2)
    k = (E_l, pl * math.sin(theta_c), 0.0, -pl * math.cos(theta_c))
    P = (E_h, 0.0, 0.0, ph)
    Ep = rng.uniform(0.2, 0.9) * E_l
    th, ph_az = rng.uniform(0.3, 2.8), rng.uniform(0, 2 * math.pi)
    pp = math.sqrt(max(Ep**2 - m_l**2, 0.0))
    kp = (Ep, pp * math.sin(th) * math.cos(ph_az), pp * math.sin(th) * math.sin(ph_az), -pp * math.cos(th))
    return k, kp, P


class ClosedFormTests(unittest.TestCase):
    def test_s_matches_four_vector_arithmetic(self):
        for E_l, E_h, theta_c in ((10.0, 275.0, 0.0), (5.0, 41.0, 0.025), (18.0, 100.0, 0.035)):
            k, _, P = random_event(random.Random(1), E_l, E_h, 0.0, theta_c)
            s_vec = (k[0] + P[0])**2 - sum((k[i] + P[i])**2 for i in (1, 2, 3))
            self.assertAlmostEqual(dk.beam_s(E_l, E_h, M, 0.0, theta_c) / s_vec, 1.0, delta=TOL)

    def test_s_closed_form_with_lepton_mass_and_crossing_angle(self):
        E_l, E_h, m_l, th = 10.0, 275.0, 0.10566, 0.025
        closed = m_l**2 + M**2 + 2 * (E_l * E_h + math.sqrt(E_l**2 - m_l**2) * math.sqrt(E_h**2 - M**2) * math.cos(th))
        self.assertAlmostEqual(dk.beam_s(E_l, E_h, M, m_l, th) / closed, 1.0, delta=1e-9)

    def test_round_trip_with_lepton_mass_and_crossing_angle(self):
        rng, E_l, E_h, m_l, th = random.Random(7), 10.0, 275.0, 0.10566, 0.025
        done = 0
        for _ in range(200):
            k, kp, P = random_event(rng, E_l, E_h, m_l, th)
            ref = dk.from_four_vectors(k, kp, P)
            if not (0 < ref["x"] <= 1 and 0 < ref["y"] <= 1 and ref["Q2"] > 0):
                continue
            out = dk.invariants(dk.beam_s(E_l, E_h, M, m_l, th), M, m_l, x=ref["x"], y=ref["y"])
            for key in ("x", "y", "Q2", "nu", "W2", "s"):
                self.assertAlmostEqual(out[key] / ref[key], 1.0, delta=1e-7, msg=key)
            done += 1
            if done == 5:
                break
        self.assertGreater(done, 0)

    def test_crossing_angle_lowers_s(self):
        self.assertLess(dk.beam_s(10.0, 275.0, M, 0.0, 0.025), dk.beam_s(10.0, 275.0, M, 0.0, 0.0))

    def test_invariants_from_two_variables_reproduce_the_four_vector_route(self):
        rng = random.Random(20261004)
        for _ in range(50):
            E_l, E_h = rng.uniform(5, 20), rng.uniform(40, 300)
            k, kp, P = random_event(rng, E_l, E_h)
            ref = dk.from_four_vectors(k, kp, P)
            if not (0 < ref["x"] <= 1 and 0 < ref["y"] <= 1 and ref["Q2"] > 0):
                continue
            s = dk.beam_s(E_l, E_h, M)
            for given in ({"x": ref["x"], "y": ref["y"]}, {"x": ref["x"], "Q2": ref["Q2"]}, {"y": ref["y"], "Q2": ref["Q2"]}):
                out = dk.invariants(s, M, 0.0, **given)
                for key in ("x", "y", "Q2", "nu", "W2", "s"):
                    self.assertAlmostEqual(out[key] / ref[key], 1.0, delta=1e-7, msg=(given, key))

    def test_exact_identity_Q2_equals_xy_times_s_minus_masses(self):
        s = dk.beam_s(10.0, 275.0, M)
        out = dk.invariants(s, M, 0.0, x=0.1, y=0.5)
        self.assertAlmostEqual(out["Q2"], 0.1 * 0.5 * (s - M**2), delta=TOL * s)
        self.assertAlmostEqual(out["W2"], M**2 + out["Q2"] * (1 - 0.1) / 0.1, delta=TOL * s)
        self.assertAlmostEqual(out["nu"], out["Q2"] / (2 * M * 0.1), delta=TOL * s)

    def test_jacobian_of_pdg_eq_18_1(self):
        s, x, y, h = dk.beam_s(10.0, 275.0, M), 0.2, 0.4, 1e-6
        dQ2_dy = (dk.invariants(s, M, 0.0, x=x, y=y + h)["Q2"] - dk.invariants(s, M, 0.0, x=x, y=y - h)["Q2"]) / (2 * h)
        self.assertAlmostEqual(dQ2_dy / (x * (s - M**2)), 1.0, delta=1e-7)


class RefusalTests(unittest.TestCase):
    def test_refuses_unphysical_inputs(self):
        for args in (("--x", "1.2", "--y", "0.5"), ("--x", "0.1", "--y", "0"), ("--x", "0.1", "--Q2", "-3")):
            code, out, _ = run("--E-lepton", "10", "--E-hadron", "275", "--M", str(M), *args)
            self.assertEqual(code, 1, args)
            doc = json.loads(out)
            self.assertEqual(doc["status"], "failed")
            self.assertTrue(doc["reason"])
            self.assertFalse(any(isinstance(v, float) and math.isnan(v) for v in doc.get("outputs", {}).values()))

    def test_bad_arguments_exit_2(self):
        self.assertEqual(run("--E-lepton", "10", "--E-hadron", "275", "--M", str(M), "--x", "0.1")[0], 2)          # one variable only
        self.assertEqual(run("--E-lepton", "10", "--E-hadron", "275", "--M", str(M), "--x", "0.1", "--y", "0.5", "--Q2", "1")[0], 2)
        self.assertEqual(run("--E-lepton", "-10", "--E-hadron", "275", "--M", str(M), "--x", "0.1", "--y", "0.5")[0], 2)

    def test_non_finite_arguments_exit_2_with_empty_stdout(self):
        base = ["--E-lepton", "10", "--E-hadron", "275", "--M", str(M), "--x", "0.1", "--y", "0.5"]
        for flag, val in (("--E-lepton", "nan"), ("--E-lepton", "inf"), ("--E-hadron", "inf"), ("--M", "nan"), ("--M", "inf"),
                          ("--crossing-angle-mrad", "nan"), ("--crossing-angle-mrad", "inf"), ("--m-lepton", "nan"), ("--x", "nan")):
            args = base + [flag, val] if flag in ("--crossing-angle-mrad", "--m-lepton") else \
                [val if (i > 0 and base[i - 1] == flag) else a for i, a in enumerate(base)]
            code, out, _ = run(*args)
            self.assertEqual(code, 2, (flag, val))
            self.assertEqual(out, "", (flag, val))

    def test_invariants_rejects_non_finite(self):
        s = dk.beam_s(10.0, 275.0, M)
        for bad in (float("nan"), float("inf")):
            with self.assertRaises(ValueError):
                dk.invariants(bad, M, 0.0, x=0.1, y=0.5)
            with self.assertRaises(ValueError):
                dk.invariants(s, bad, 0.0, x=0.1, y=0.5)
            with self.assertRaises(ValueError):
                dk.invariants(s, M, bad, x=0.1, y=0.5)
            with self.assertRaises(ValueError):
                dk.invariants(s, M, 0.0, x=bad, y=0.5)

    def test_exit_1_stdout_is_strict_json(self):
        code, out, _ = run("--E-lepton", "10", "--E-hadron", "275", "--M", str(M), "--x", "1.2", "--y", "0.5")
        self.assertEqual(code, 1)
        self.assertNotRegex(out, r"NaN|Infinity")

    def test_cli_success_prints_conventions_and_outputs(self):
        code, out, _ = run("--E-lepton", "10", "--E-hadron", "275", "--M", str(M), "--x", "0.1", "--y", "0.5")
        self.assertEqual(code, 0)
        doc = json.loads(out)
        self.assertEqual(doc["status"], "ok")
        self.assertEqual(doc["conventions"]["lepton_mass_GeV"], 0.0)
        self.assertEqual(doc["conventions"]["hadron_energy"], "per nucleon; M is the mass the user supplied")
        for key in ("x", "y", "Q2", "nu", "W2", "W", "s", "sqrt_s"):
            self.assertIn(key, doc["outputs"])


class ContentTests(unittest.TestCase):
    TEXT = REF.read_text(encoding="utf-8")

    def test_reference_defines_the_pdg_variables_and_cites_the_review(self):
        for needle in ("nu = q.P / M", "Q^2 = -q^2", "x = Q^2 / (2 M nu)", "y = q.P / k.P", "W^2 = (P + q)^2", "s = (k + P)^2",
                       "Q^2 = x y (s - M^2 - m_l^2)", "18.1", "Structure Functions", "revised August 2025"):
            self.assertIn(needle, self.TEXT, needle)

    def test_no_experiment_named(self):
        for path in (REF, SCRIPT):
            self.assertIsNone(re.search(r"\b(EIC|ePIC|HERA|AMS|ATLAS|CMS|LHC)\b", path.read_text(encoding="utf-8")), path.name)

    def test_reference_hands_off_what_it_does_not_own(self):
        for owner in ("detector-response", "hep-analysis", "hep-statistics"):
            self.assertIn(owner, self.TEXT)
        self.assertIn("not derived here", self.TEXT)

    def test_skill_links_the_reference_within_budget(self):
        text = SKILL.read_text(encoding="utf-8")
        self.assertIn("(references/dis-kinematics.md)", text)
        self.assertIn("`dis_kinematics.py`", text)
        self.assertLessEqual(len(text.encode("utf-8")), 8192)


if __name__ == "__main__":
    unittest.main()
