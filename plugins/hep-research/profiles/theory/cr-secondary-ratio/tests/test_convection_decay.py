"""theory:cr-secondary-ratio, work package B2: closed forms with constant convection and radioactive decay.

B2-1: for V_c -> 0 and tau -> infinity the solutions reduce to pure diffusion (symbolically in SymPy and numerically
against predict.thin_disc_ratio). B2-2: the dimension checks of the derivation pass and are recorded. Also: the closed
forms agree with an independent solve_bvp solution, decay conserves number, the stored derivation record is current,
and the checks are discriminating (a wrong disc term or a missing stable assumption is caught)."""
import json
import math
import sys
import unittest
from importlib.util import find_spec
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

HAVE_SCIPY = find_spec("scipy") is not None and find_spec("numpy") is not None
HAVE_SYMPY = find_spec("sympy") is not None
if HAVE_SCIPY:
    import convection_decay as cd
    import predict
if HAVE_SYMPY:
    import derive_convection_decay as dcd
    import sympy as sp

CONFIG = ROOT / "benchmarks" / "convection-decay-benchmark.json"


@unittest.skipUnless(HAVE_SYMPY, "sympy is required (requirements-core.txt)")
class SymbolicTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out = dcd.derive()

    def test_all_checks_pass(self):
        self.assertEqual(self.out["status"], "analytic-derivation")
        self.assertTrue(all(self.out["checks"].values()), [k for k, v in self.out["checks"].items() if not v])

    def test_pure_diffusion_limits_recorded(self):  # B2-1, symbolic
        for key in ("limit_V_c_then_Gamma_gives_2D_over_L", "limit_Gamma_then_V_c_gives_2D_over_L",
                    "limit_ratio_equals_pure_diffusion_ratio", "series_in_V_c_constant_term_is_2D_over_L",
                    "series_in_Gamma_constant_term_is_2D_over_L", "daughter_gain_vanishes_without_decay"):
            self.assertTrue(self.out["checks"][key], key)

    def test_dimension_checks_recorded(self):  # B2-2
        dims = {k: v for k, v in self.out["checks"].items() if k.startswith("dim_")}
        self.assertGreaterEqual(len(dims), 10)
        self.assertTrue(all(dims.values()), dims)
        stored = json.loads((ROOT / "derivations" / "convection-decay-derivation.json").read_text(encoding="utf-8"))
        self.assertEqual({k: v for k, v in stored["checks"].items() if k.startswith("dim_")}, dims)

    def test_stored_record_is_current(self):
        stored = json.loads((ROOT / "derivations" / "convection-decay-derivation.json").read_text(encoding="utf-8"))
        self.assertEqual(stored["checks"], self.out["checks"])
        self.assertEqual(stored["results"], self.out["results"])
        self.assertEqual(stored["status"], "analytic-derivation")

    def test_zero_test_is_discriminating(self):
        # the advective form (no 2 V_c N(0) sweeping term at the disc) does not give the closed form
        prof = dcd.N0 * (sp.exp(dcd.V * dcd.L / dcd.D) - sp.exp(dcd.V * dcd.z / dcd.D)) / (
            sp.exp(dcd.V * dcd.L / dcd.D) - 1)
        lhs = -2 * dcd.D * sp.diff(prof, dcd.z).subs(dcd.z, 0) + 2 * dcd.h * dcd.n * dcd.v * dcd.sigma * dcd.N0
        n0 = sp.solve(sp.Eq(lhs, 2 * dcd.h * dcd.q), dcd.N0)[0]
        closed = dcd.stable_species()["mid_plane"]
        self.assertFalse(dcd.is_zero(n0 - closed))

    def test_dimension_check_is_discriminating(self):
        self.assertNotEqual(dcd.dimension(dcd.D / dcd.L ** 2), dcd.LEN / dcd.TIME)
        with self.assertRaises(ValueError):
            dcd.dimension(dcd.V + dcd.D)


@unittest.skipUnless(HAVE_SCIPY, "numpy and scipy are required (requirements-core.txt)")
class NumericalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg = predict.load_json(CONFIG)
        cls.bench = cd.benchmark(cls.cfg)

    def test_benchmark_checks_pass(self):
        self.assertTrue(all(self.bench["checks"].values()), self.bench["checks"])

    def test_pure_diffusion_reduction(self):  # B2-1, numerical
        self.assertLess(self.bench["max_rel_dev"]["pure_diffusion_reference"], 1e-12)
        devs = [a["max_rel_dev"] for a in self.bench["approach"]]
        self.assertTrue(all(b < a for a, b in zip(devs, devs[1:])), devs)
        self.assertLess(devs[-1], 1e-4)

    def test_escape_speed_limits(self):
        diff, big_l = 3e28, 4.0 * predict.KPC_CM
        self.assertEqual(cd.escape_speed(diff, 0.0, big_l, 0.0), 2 * diff / big_l)
        self.assertAlmostEqual(cd.escape_speed(diff, 1e-3, big_l, 0.0) / (2 * diff / big_l), 1.0, places=9)
        # pure convection: K = V_c (1 + coth(V_c L / 2D))
        v_c = 1e6
        self.assertAlmostEqual(cd.escape_speed(diff, v_c, big_l, 0.0) / (v_c * (1 + 1 / math.tanh(
            v_c * big_l / (2 * diff)))), 1.0, places=12)

    def test_closed_forms_match_boundary_value_solution(self):
        self.assertLess(self.bench["max_rel_dev"]["closed_vs_bvp"], 1e-6)

    def test_boundary_value_comparison_is_discriminating(self):
        # dropping the V_c sweeping term from the disc condition changes N(0) far beyond the 1e-6 tolerance
        params = cd.model_parameters(self.cfg)
        xs = predict.load_cross_sections(self.cfg)
        e_n = self.cfg["energies_gev_per_n"][2]
        inp = cd._species_inputs(params, e_n, self.cfg, xs)
        s = inp["species"]["11B"]
        good = cd.mid_plane_density(s["q"], s["D"], inp["V_c"], inp["L"], 0.0, inp["h"], s["loss"])
        wrong = 2 * inp["h"] * s["q"] / (cd.escape_speed(s["D"], inp["V_c"], inp["L"], 0.0) - inp["V_c"]
                                         + 2 * inp["h"] * s["loss"])
        numeric = cd.boundary_value_mid_plane(params, e_n, self.cfg, xs)["density"]["11B"]
        self.assertLess(abs(good / numeric - 1), 1e-6)
        self.assertGreater(abs(wrong / numeric - 1), 1e-3)

    def test_decay_conserves_number(self):
        totals = self.bench["conservation_totals"]
        self.assertLess(max(abs(t / totals[0] - 1) for t in totals), 1e-10)

    def test_decay_gain_and_lorentz_dilation(self):
        out = cd.evaluate(self.cfg)
        gain = out["decay_gain_fraction"]["10B"]
        self.assertTrue(all(g > 0 for g in gain))
        self.assertTrue(all(b < a for a, b in zip(gain, gain[1:])), gain)  # time dilation: less decay at high E
        be = next(s for s in self.cfg["secondaries"] if s["name"] == "10Be")
        rates = [cd.decay_rate(e, be) for e in (0.1, 1.0, 10.0)]
        for e, r in zip((0.1, 1.0, 10.0), rates):
            self.assertAlmostEqual(r * cd.lorentz_gamma(e, be) * cd.rest_lifetime_s(be), 1.0, places=12)
        ratio = out["observables"]["10Be/9Be"]
        no_decay = cd.evaluate(dict(self.cfg, secondaries=[
            dict(s, decay=None, stable_assumption="test only") if s["name"] == "10Be" else s
            for s in self.cfg["secondaries"]]))["observables"]["10Be/9Be"]
        self.assertTrue(all(a < b for a, b in zip(ratio, no_decay)))

    def test_half_life_from_core_constants(self):
        from core.constants.physical import half_life
        be = next(s for s in self.cfg["secondaries"] if s["name"] == "10Be")
        q = half_life("10Be")
        self.assertEqual(q.unit, "My")
        self.assertAlmostEqual(cd.rest_lifetime_s(be) * math.log(2.0)
                               / cd.half_life_seconds("10Be")["value"], 1.0, places=12)

    def test_stable_assumption_required_for_unstable_species(self):
        secs = [{k: v for k, v in s.items() if k != "stable_assumption"} for s in self.cfg["secondaries"]]
        with self.assertRaises(predict.InputError):
            cd.evaluate(dict(self.cfg, secondaries=secs))

    def test_bad_inputs_refused(self):
        with self.assertRaises(predict.InputError):
            cd.model_parameters(self.cfg, {"V_c_kms": -1.0})
        with self.assertRaises(predict.InputError):
            cd.model_parameters(self.cfg, {"Vc": 1.0})
        secs = [dict(s, decay={"mode": "beta-", "daughter": "9Be"}) if s["name"] == "10Be" else s
                for s in self.cfg["secondaries"]]
        self.assertIsInstance(cd.evaluate(dict(self.cfg, secondaries=secs)), dict)  # any stable daughter works
        secs = [dict(s, decay={"mode": "beta-", "daughter": "6Li"}) if s["name"] == "10Be" else s
                for s in self.cfg["secondaries"]]
        with self.assertRaises(predict.InputError):
            cd.evaluate(dict(self.cfg, secondaries=secs))

    def test_cli(self):
        import subprocess
        script = ROOT / "scripts" / "convection_decay.py"
        proc = subprocess.run([sys.executable, str(script), "--set", "V_c_kms=20"], capture_output=True, text=True,
                              timeout=300)
        self.assertEqual(proc.returncode, 0, proc.stdout[-500:])
        self.assertEqual(json.loads(proc.stdout)["parameter_point"]["V_c_kms"], 20.0)
        proc = subprocess.run([sys.executable, str(script), "--set", "nope=1"], capture_output=True, text=True,
                              timeout=300)
        self.assertEqual(proc.returncode, 2)
        self.assertEqual(json.loads(proc.stdout)["status"], "failed")


if __name__ == "__main__":
    unittest.main()
