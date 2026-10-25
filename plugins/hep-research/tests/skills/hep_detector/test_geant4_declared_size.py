"""R5, control rule declared-size/1 of multiple-scattering-reference (maintainer decision 2026-10-25, for new
studies): a control's expected shift follows from its injection through Lynch and Dahl's formula; it counts when
caught and its expected shift is at most 1.5 x the planned detection limit; the benchmark claims the largest detection
limit a caught control demonstrated; plan-controls sizes the controls before they run. The default rule
(shift-window/1) is unchanged. All inputs are SYNTHETIC; the J15 100 GV numbers are the recorded ones."""
import json
import math
import random
import sys
import tempfile
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PLUGIN))
sys.path.insert(0, str(PLUGIN / "skills" / "hep-detector" / "scripts"))
import geant4_benchmarks as G  # noqa: E402

STUDY = {"materials": [{"name": "G4_Si", "z": 14, "a_g_mole": 28.0855, "density_g_cm3": 2.329,
                        "radiation_length_mm": 93.7, "reference_source": "PDG 2024 (test)",
                        "reference_origin": "independent"}]}
B = {"benchmark": "multiple-scattering-reference", "element_spec": "spec.json", "crossings": "nominal.csv",
     "measuring_plane": "Plane", "material": "G4_Si", "particle": "proton", "momentum_MeV": 1000.0,
     "thickness_mm": 0.3, "tolerance": {"reference_accuracy_relative": 0.02, "k_sigma": 3.0}}


def control(caught, shift, dl, expected):
    return {"status": "caught" if caught else "not-caught", "shift": shift, "detection_limit_relative": dl,
            "expected_shift_relative": expected}


class ExpectedShift(unittest.TestCase):
    def test_the_lynch_dahl_response(self):
        """An areal-density change d moves theta0 by about d/2 plus Lynch and Dahl's log term, the same sign as d."""
        up, down = G.ms_expected_shift(B, STUDY, 0.13), G.ms_expected_shift(B, STUDY, -0.13)
        self.assertGreater(up, 0)
        self.assertLess(down, 0)
        self.assertGreater(abs(down), abs(up))  # theta0 ~ sqrt(x): the minus side moves more
        self.assertTrue(0.055 < up < 0.075 and 0.060 < -down < 0.085, (up, down))
        self.assertEqual(G.ms_expected_shift(B, STUDY, 0.0), 0.0)
        with self.assertRaises(G.BenchmarkError):
            G.ms_expected_shift(B, STUDY, -1.0)


class DeclaredSize(unittest.TestCase):
    def test_j15_100_gv_numbers_under_both_rules(self):
        """J15's recorded 100 GV controls (+-13 % density; shifts +6.31 %, -8.14 %; DL 6.28 %, 6.30 %): the window rule
        refuses the minus control (|shift| > 1.1 DL); under declared-size/1 both are sized (expected shifts about
        6.5-7 % <= 1.5 x the planned DL) and caught, and the benchmark claims the 8.14 % a control demonstrated. This
        shows the rule; the recorded J15 study keeps the rule it ran with."""
        planned = 0.0630
        ctl = [control(True, 0.06314, 0.06285, G.ms_expected_shift(B, STUDY, 0.13)),
               control(True, -0.08143, 0.06300, G.ms_expected_shift(B, STUDY, -0.13))]
        self.assertFalse(abs(ctl[1]["shift"]) <= 1.1 * ctl[1]["detection_limit_relative"])  # shift-window/1 refuses
        out = G.declared_size(ctl, planned)
        self.assertTrue(all(c["sized"] and c["at_claimed_detection_limit"] for c in ctl), ctl)
        self.assertAlmostEqual(out["detection_limit_relative"], 0.08143)
        self.assertEqual((out["control_rule"], out["target_factor"], out["ceiling_factor"]),
                         ("declared-size/1", 1.25, 1.5))

    def test_oversized_and_uncaught_controls(self):
        planned = 0.05
        ctl = [control(True, 0.20, 0.06, 0.18),     # gross: declared 3.6 x the planned DL, not counted
               control(False, -0.03, 0.06, -0.06),  # sized but not caught: no demonstrated limit
               control(True, 0.04, 0.06, 0.07)]     # sized and caught below its DL: demonstrates DL
        out = G.declared_size(ctl, planned)
        self.assertEqual([c["at_claimed_detection_limit"] for c in ctl], [False, False, True])
        self.assertEqual([c["sized"] for c in ctl], [False, True, True])
        self.assertIsNone(ctl[1]["demonstrated_detection_limit_relative"])
        self.assertEqual(ctl[2]["demonstrated_detection_limit_relative"], 0.06)
        self.assertAlmostEqual(out["detection_limit_relative"], 0.20)  # never less than a control showed
        ctl = [control(True, 0.05, 0.06, None)]  # no injected_relative: undeclared, never sized
        G.declared_size(ctl, planned)
        self.assertFalse(ctl[0]["at_claimed_detection_limit"])

    def test_the_rule_is_named_and_limited(self):
        self.assertEqual(G.control_rule({"benchmark": "stopping-power"}), "shift-window/1")
        with self.assertRaises(G.BenchmarkError):
            G.control_rule({"benchmark": "multiple-scattering-reference", "control_rule": "window/2"})
        with self.assertRaises(G.BenchmarkError):
            G.control_rule({"benchmark": "stopping-power", "control_rule": "declared-size/1"})


def write_dump(path: Path, theta: float, seed: int, n: int = 20000) -> None:
    rng = random.Random(seed)
    rows = ["event_id,track_id,plane_id,dx,dy,dz"]
    for e in range(n):
        rows.append(f"{e},1,1,1.0,{math.tan(rng.gauss(0, theta))},{math.tan(rng.gauss(0, theta))}")
    path.write_text("\n".join(rows) + "\n", encoding="utf-8")


def write_record(path: Path, density: float) -> str:
    hx = float.hex
    rec = {"artifact_id": path.stem, "extension": {"simulation": {"effective_config": {"geometry": {"tree": {
        "materials": [{"name": "Si", "density_g_cm3": hx(density)}],
        "logical_volumes": [{"name": "Slab", "material": "Si", "solid": {"parameters": {"half_x_mm": hx(0.15)}}}]}}}}}}
    path.write_text(json.dumps(rec), encoding="utf-8")
    return path.name


class Wiring(unittest.TestCase):
    def test_run_detector_benchmark_applies_the_declared_rule(self):
        """Nominal and +-13 % density controls whose widths follow Lynch and Dahl: with declared-size/1 the result
        carries the rule, the planned limit, each control's expected shift and sized flag, and claims the demonstrated
        limit; without it the window rule's fields are unchanged."""
        p = B["momentum_MeV"]
        theta = G.lynch_dahl_theta0(14, 28.0855, 0.3 / 10 * 2.329, p, p / math.hypot(p, 938.27208943))
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            (d / "spec.json").write_text(json.dumps({"elements": [{"name": "Slab"}, {"name": "Plane"}]}),
                                         encoding="utf-8")
            write_dump(d / "nominal.csv", theta, 21)
            ncs = []
            for name, inj, seed in (("up", 0.13, 22), ("down", -0.13, 23)):
                write_dump(d / f"{name}.csv", theta * (1 + G.ms_expected_shift(B, STUDY, inj)), seed)
                ncs.append({"crossings": f"{name}.csv", "run_record": write_record(d / f"{name}.json", 2.329 * (1 + inj)),
                            "injected": f"density x {1 + inj}", "injected_relative": inj})
            b = dict(B, run_record=write_record(d / "nominal.json", 2.329), slab="Slab", negative_controls=ncs)
            declared = G.run_detector_benchmark(dict(b, control_rule="declared-size/1"), STUDY, d)
            window = G.run_detector_benchmark(b, STUDY, d)
        nc = declared["negative_control"]
        self.assertEqual(nc["control_rule"], "declared-size/1")
        self.assertEqual(nc["status"], "caught", nc)
        self.assertTrue(all(c["sized"] for c in nc["controls"]))
        self.assertEqual(nc["at_claimed_detection_limit"], all(c["status"] == "caught" for c in nc["controls"]))
        self.assertAlmostEqual(nc["detection_limit_relative"],
                               max(c["demonstrated_detection_limit_relative"] for c in nc["controls"]))
        self.assertNotIn("control_rule", window["negative_control"])
        self.assertNotIn("sized", window["negative_control"]["controls"][0])


class PlanControls(unittest.TestCase):
    def test_injections_for_the_target_shift(self):
        """From a nominal dump alone: the planned DL and the +- injections whose expected shift is 1.25 x it."""
        p = B["momentum_MeV"]
        theta = G.lynch_dahl_theta0(14, 28.0855, 0.3 / 10 * 2.329, p, p / math.hypot(p, 938.27208943))
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            (d / "spec.json").write_text(json.dumps({"elements": [{"name": "Slab"}, {"name": "Plane"}]}),
                                         encoding="utf-8")
            rng = random.Random(11)
            rows = ["event_id,track_id,plane_id,dx,dy,dz"]
            for e in range(20000):
                rows.append(f"{e},1,1,1.0,{math.tan(rng.gauss(0, theta))},{math.tan(rng.gauss(0, theta))}")
            (d / "nominal.csv").write_text("\n".join(rows) + "\n", encoding="utf-8")
            (d / "study.json").write_text(json.dumps(STUDY), encoding="utf-8")
            (d / "bench.json").write_text(json.dumps({"schema": "geant4-benchmarks/1", "study_spec": "study.json",
                                                       "benchmarks": [B]}), encoding="utf-8")
            import contextlib
            import io
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                code = G.main(["plan-controls", "--config", str(d / "bench.json")])
            out = json.loads(buf.getvalue())
        self.assertEqual(code, 0, out)
        dlp = out["planned_detection_limit_relative"]
        self.assertGreater(dlp, out["nominal"]["tolerance"])
        plus, minus = out["controls"]
        self.assertEqual((plus["sign"], minus["sign"]), ("+", "-"))
        self.assertGreater(plus["injected_relative"], 0)
        self.assertLess(minus["injected_relative"], 0)
        for c, sign in ((plus, 1), (minus, -1)):
            self.assertAlmostEqual(c["expected_shift_relative"], sign * 1.25 * dlp, delta=1e-5)
            self.assertLessEqual(abs(c["expected_shift_relative"]), 1.5 * dlp)  # sized by construction


if __name__ == "__main__":
    unittest.main()
