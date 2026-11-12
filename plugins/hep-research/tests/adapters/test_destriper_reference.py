"""adapters/destriper, T10 replay stage 3 (docs/dev/detector-reconstruction/t10-replay-stage-plan.md, section 4): the independently
written exact rational reference and the comparator with its drafted tolerance and the tolerance-halving check. Hand-made systems
only; the fixture is run in the stage 4 job. Expectations R1-R5 and C1-C5 are fixed in the stage plan.

The reference's results are checked here by their defining equations (the normal equations and the constraint, in exact Fractions,
summed by this test), never by calling the solver.
Run from the plugin root: python -m unittest tests.adapters.test_destriper_reference -v
"""
from __future__ import annotations

import ast
import copy
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from fractions import Fraction
from pathlib import Path

import numpy

ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / "adapters" / "destriper" / "assets"
TOOLS = ASSETS / "fixture_tools"
REFERENCE = TOOLS / "t10_exact_reference.py"
COMPARATOR = TOOLS / "t10_comparator.py"
TOLERANCE = ASSETS / "t10-replay.tolerance.json"
NOISELESS_TOLERANCE = ASSETS / "t10-replay-noiseless.tolerance.json"
LADDER = [1e-2, 1e-3, 1e-4, 1e-5, 1e-6]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(TOOLS))
sys.path.insert(0, str(ASSETS))

import t10_comparator  # noqa: E402
import t10_exact_reference  # noqa: E402
import t10_fixture  # noqa: E402
import t10_replay  # noqa: E402
from destripe_recipe import product, solver, timestream  # noqa: E402
from tests.adapters.test_destriper import CARD, hand_made, kkt_reference, noisy_values, numbers  # noqa: E402

PY = sys.executable
STDLIB_ONLY = {"__future__", "argparse", "fractions", "hashlib", "json", "sys"}


def exact_equations(document: dict, reference: dict):
    """A^T (y - A x) and c^T x in exact Fractions, from the timestream and the reference's exact strings."""
    pixels, length = document["pixels"], document["baseline_length"]
    m = [Fraction(item["exact"]) for item in reference["map"]]
    a = [Fraction(item["exact"]) for item in reference["baselines"]]
    gradient = [Fraction(0)] * (pixels + len(a))
    for t, (p, y) in enumerate(zip(document["pixel"], document["value"])):
        residual = Fraction(y) - m[p] - a[t // length]
        gradient[p] += residual
        gradient[pixels + t // length] += residual
    return gradient, sum(a, Fraction(0))


def write(folder: Path, name: str, document) -> Path:
    path = folder / name
    path.write_text(json.dumps(document), encoding="utf-8")
    return path


def solved(document: dict, stopping: float, constraint="zero-sum") -> dict:
    stream = timestream.read(document)
    return product.build(stream, solver.solve(stream, stopping=stopping), constraint=constraint, product_id="product.hand-made",
                         input_sha256="0" * 64, card_path=CARD)


def tolerance_for(document: dict, stopping=1e-10, state="frozen", safety=10.0, ladder=None) -> dict:
    """A record for a hand-made system: the noisy record's keys, its own kappa and G; no ladder unless one is given."""
    kappa, gain = numbers(document)
    record = json.loads(TOLERANCE.read_text(encoding="utf-8"))
    record.update({"state": state, "stopping": stopping, "safety": safety, "kappa": float(kappa), "map_gain": float(gain),
                   "tau_baselines": float(safety * kappa * stopping) * 1.01, "tau_map": float(safety * gain * kappa * stopping) * 1.01,
                   "ladder": ladder, "min_informative_steps": 2 if ladder else None})
    return record


def float_reference(document: dict) -> dict:
    """A reference record from the test's NumPy KKT solve (not the pinned exact reference), its baselines' exact mean removed so they
    sum to zero exactly; multiplier 0. Good to about 1e-14, far below the ladder's differences."""
    sky, offsets = kkt_reference(document)
    exact = [Fraction(float(v)) for v in offsets]
    mean = sum(exact, Fraction(0)) / len(exact)
    entry = lambda value: {"exact": f"{value.numerator}/{value.denominator}", "float": float(value)}  # noqa: E731
    return {"format": "t10-exact-reference/1", "map": [entry(Fraction(float(v)) + mean) for v in sky],
            "baselines": [entry(v - mean) for v in exact], "multiplier": "0/1"}


class ReferenceTests(unittest.TestCase):
    def test_r1_the_reference_imports_only_the_standard_library(self):
        tree = ast.parse(REFERENCE.read_text(encoding="utf-8"))
        names = {alias.name.split(".")[0] for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names}
        names |= {(node.module or "").split(".")[0] for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)}
        self.assertLessEqual(names, STDLIB_ONLY)

    def test_r2_two_pixels_two_baselines_by_hand(self):
        # baseline 0 sees pixels 0, 1; baseline 1 sees pixels 1, 0. y = m + a with m = (5, 1), a = (2, -2): consistent, and
        # sum a = 0, so the constrained solution is exactly that.
        document = hand_made(pixels=2, length=2, baselines=2, pointing=[0, 1, 1, 0], values=[7, 3, -1, 3])
        result = t10_exact_reference.solve_exact(document)
        self.assertEqual([Fraction(item["exact"]) for item in result["map"]], [5, 1])
        self.assertEqual([Fraction(item["exact"]) for item in result["baselines"]], [2, -2])

    def test_r3_noisy_dyadic_input_satisfies_the_constrained_normal_equations_exactly(self):
        document = hand_made()
        document["value"] = [round(v * 64) / 64 for v in noisy_values(document)]
        result = t10_exact_reference.solve_exact(document)
        gradient, total = exact_equations(document, result)
        self.assertEqual(total, 0)
        multiplier = Fraction(result["multiplier"])
        self.assertEqual(gradient[:4], [0] * 4)
        self.assertEqual(gradient[4:], [multiplier] * 8)

    def test_r4_disconnected_input_is_refused(self):
        split = hand_made(pointing=[(b % 2) * 2 + (j // 2) for b in range(8) for j in range(4)])
        with self.assertRaises(t10_exact_reference.Singular):
            t10_exact_reference.solve_exact(split)
        with tempfile.TemporaryDirectory() as folder:
            source = write(Path(folder), "split.json", split)
            proc = subprocess.run([PY, "-I", "-B", str(REFERENCE), "solve", "--timestream", str(source), "--out", str(Path(folder) / "r.json")],
                                  capture_output=True, text=True, timeout=120)
            self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
            self.assertEqual(json.loads(proc.stdout)["status"], "refused")
            self.assertFalse((Path(folder) / "r.json").exists())

    def test_r6_noiseless_reference_equals_the_truth_exactly(self):
        document = hand_made(pixels=2, length=2, baselines=2, pointing=[0, 1, 1, 0], values=[7, 3, -1, 3])
        result = t10_exact_reference.solve_exact(document)
        truth = {"format": "destriper-truth/1", "map": [5, 1], "baselines": [2, -2]}
        self.assertTrue(t10_replay.reference_equals_truth(result, truth))
        self.assertFalse(t10_replay.reference_equals_truth(result, dict(truth, map=[5, 2])))
        self.assertFalse(t10_replay.reference_equals_truth(result, dict(truth, baselines=[2])))

    def test_r5_floats_are_nearest_and_hashes_recorded(self):
        document = hand_made()
        document["value"] = noisy_values(document)
        with tempfile.TemporaryDirectory() as folder:
            source = write(Path(folder), "t.json", document)
            target = Path(folder) / "r.json"
            proc = subprocess.run([PY, "-I", "-B", str(REFERENCE), "solve", "--timestream", str(source), "--out", str(target)],
                                  capture_output=True, text=True, timeout=120)
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            result = json.loads(target.read_text(encoding="utf-8"))
            self.assertEqual(result["format"], "t10-exact-reference/1")
            self.assertEqual(result["input_sha256"], hashlib.sha256(source.read_bytes()).hexdigest())
            self.assertEqual(result["reference_sha256"], hashlib.sha256(REFERENCE.read_bytes()).hexdigest())
            for item in result["map"] + result["baselines"]:
                self.assertEqual(item["float"], float(Fraction(item["exact"])))


class ComparatorTests(unittest.TestCase):
    def setUp(self):
        self.document = hand_made()
        self.document["value"] = noisy_values(self.document)
        self.reference = t10_exact_reference.solve_exact(self.document)
        self.nominal = solved(self.document, 1e-10)

    def test_c1_within_passes_and_a_moved_baseline_fails(self):
        result = t10_comparator.compare(self.document, self.nominal, self.reference, tolerance_for(self.document))
        self.assertEqual(result["status"], "passed", result)
        size = float(numpy.linalg.norm([float(Fraction(i["exact"])) for i in self.reference["baselines"]]))
        moved = copy.deepcopy(self.nominal)
        moved["baselines"][3] += 2 * tolerance_for(self.document)["tau_baselines"] * size
        result = t10_comparator.compare(self.document, moved, self.reference, tolerance_for(self.document))
        self.assertEqual(result["status"], "failed")

    def test_c2_a_drafted_tolerance_gives_no_verdict(self):
        result = t10_comparator.compare(self.document, self.nominal, self.reference, tolerance_for(self.document, state="drafted"))
        self.assertEqual(result["status"], "incomplete")
        with tempfile.TemporaryDirectory() as folder:
            folder = Path(folder)
            source = write(folder, "t.json", self.document)
            digest = hashlib.sha256(source.read_bytes()).hexdigest()
            self.nominal["input"]["sha256"] = digest
            args = ["--timestream", source, "--product", write(folder, "p.json", self.nominal),
                    "--reference", write(folder, "r.json", dict(self.reference, input_sha256=digest)),
                    "--tolerance", write(folder, "tol.json", tolerance_for(self.document, state="drafted"))]
            proc = subprocess.run([PY, "-I", "-B", str(COMPARATOR), "compare", *map(str, args)], capture_output=True, text=True, timeout=120)
            self.assertEqual(proc.returncode, 3, proc.stdout + proc.stderr)
            self.assertIn("DRAFT READING", proc.stdout)
            self.assertNotIn("PASS", proc.stdout)
            self.assertNotIn("FAIL", proc.stdout)

    def test_c3_the_tolerance_is_checked_against_its_derivation(self):
        low = tolerance_for(self.document)
        low["tau_baselines"] /= 2
        with self.assertRaises(t10_comparator.ToleranceError):
            t10_comparator.compare(self.document, self.nominal, self.reference, low)
        low = tolerance_for(self.document)
        low["tau_map"] /= 2
        with self.assertRaises(t10_comparator.ToleranceError):
            t10_comparator.compare(self.document, self.nominal, self.reference, low)
        other = tolerance_for(self.document, stopping=1e-9)
        with self.assertRaises(t10_comparator.ToleranceError):
            t10_comparator.compare(self.document, self.nominal, self.reference, other)
        floor = tolerance_for(self.document, stopping=1e-17)
        floor_product = copy.deepcopy(self.nominal)
        floor_product["solver"]["stopping"] = 1e-17
        with self.assertRaises(t10_comparator.ToleranceError):
            t10_comparator.compare(self.document, floor_product, self.reference, floor)

    def test_c3_the_record_safety_kappa_and_gain_and_the_reference_multiplier(self):
        cases = {"safety below 10": dict(tolerance_for(self.document, safety=5.0)),
                 "kappa off": dict(tolerance_for(self.document), kappa=tolerance_for(self.document)["kappa"] + 0.02),
                 "gain off": dict(tolerance_for(self.document), map_gain=tolerance_for(self.document)["map_gain"] + 2e-4)}
        for name, record in cases.items():
            with self.subTest(case=name), self.assertRaises(t10_comparator.ToleranceError):
                t10_comparator.compare(self.document, self.nominal, self.reference, record)
        with self.assertRaises(t10_comparator.ToleranceError):
            t10_comparator.compare(self.document, self.nominal, dict(self.reference, multiplier="1/3"), tolerance_for(self.document))

    def test_c4_ladder_on_a_real_run_is_informative_and_passes(self):
        # the pointing of the generator at seed 20262 (not the fixture's seed 20260): kappa about 15, 14 distinct eigenvalues
        document, _ = t10_fixture.generate("noisy", 20262)
        reference = float_reference(document)
        record = tolerance_for(document, ladder=LADDER)
        rungs = [solved(document, eps) for eps in LADDER]
        result = t10_comparator.compare(document, solved(document, 1e-10), reference, record, ladder=rungs)
        self.assertEqual(result["status"], "passed", result)
        self.assertGreaterEqual(result["ladder"]["informative_steps"], 2)
        self.assertTrue(result["ladder"]["passed"])
        for step in result["ladder"]["steps"]:
            self.assertIn("map_smaller", step)  # a reading
        self.assertIn("bound", result["a_posteriori"])
        self.assertIn("baselines_relative", result["a_posteriori"])

    def rung(self, eps: float, iterations: int, factor: float, map_factor: float | None = None) -> dict:
        """A ladder product: the moved nominal's differences scaled by factor (the map's by map_factor, default factor)."""
        built = copy.deepcopy(self.base)
        built["solver"]["stopping"], built["solver"]["iterations"] = eps, iterations
        for key, scale in (("map", factor if map_factor is None else map_factor), ("baselines", factor)):
            exact = [float(Fraction(item["exact"])) for item in self.reference[key]]
            built[key] = [x + scale * (v - x) for v, x in zip(built[key], exact)]
        return built

    def constructed_ladder(self, plan) -> dict:
        size = float(numpy.linalg.norm([float(Fraction(i["exact"])) for i in self.reference["baselines"]]))
        self.base = copy.deepcopy(self.nominal)
        self.base["baselines"] = [v + 1e-8 * size * (-1) ** k for k, v in enumerate(self.base["baselines"])]
        self.base["map"] = [v + 1e-8 * size for v in self.base["map"]]
        rungs = [self.rung(eps, *step) for eps, step in zip(LADDER, plan)]
        return t10_comparator.compare(self.document, self.nominal, self.reference, tolerance_for(self.document, ladder=LADDER), ladder=rungs)

    def test_c4_ladder_rules_on_constructed_products(self):
        good = self.constructed_ladder([(1, 1.0), (2, 0.5), (3, 0.25), (3, 0.25), (4, 0.1)])
        self.assertEqual(good["status"], "passed", good["ladder"])
        self.assertEqual(good["ladder"]["informative_steps"], 3)
        few = self.constructed_ladder([(1, 1.0), (2, 0.5), (2, 0.5), (2, 0.5), (2, 0.5)])
        self.assertEqual(few["status"], "incomplete")
        self.assertTrue(few["ladder"]["passed"])
        self.assertFalse(few["ladder"]["enough"])
        for name, plan in {"more iterations, not smaller": [(1, 1.0), (2, 1.0), (3, 0.5), (4, 0.25), (5, 0.1)],
                           "same iterations, other values": [(1, 1.0), (1, 0.5), (2, 0.25), (3, 0.1), (4, 0.05)],
                           "fewer iterations": [(2, 1.0), (1, 0.5), (3, 0.25), (4, 0.1), (5, 0.05)],
                           "a rung outside its bound": [(1, 1e9), (2, 0.5), (3, 0.25), (4, 0.1), (5, 0.05)],
                           "a baseline rung outside its bound, the map inside": [(1, 1e9, 1.0), (2, 0.5), (3, 0.25), (4, 0.1), (5, 0.05)],
                           "a map rung outside its bound, the baselines inside": [(1, 1.0, 1e9), (2, 0.5), (3, 0.25), (4, 0.1), (5, 0.05)]}.items():
            with self.subTest(case=name):
                result = self.constructed_ladder(plan)
                self.assertFalse(result["ladder"]["passed"])
                self.assertEqual(result["status"], "failed")
        with self.assertRaises(t10_comparator.ToleranceError):
            t10_comparator.compare(self.document, self.nominal, self.reference, tolerance_for(self.document, ladder=LADDER),
                                   ladder=[solved(self.document, eps) for eps in LADDER[:4]])
        missing = t10_comparator.compare(self.document, self.nominal, self.reference, tolerance_for(self.document, ladder=LADDER))
        self.assertEqual(missing["status"], "incomplete")

    def test_c4_the_eps_half_run_is_a_reading_only(self):
        worse = copy.deepcopy(self.nominal)
        worse["solver"]["stopping"] = 1e-10 / 2
        worse["baselines"] = [v + 1e-12 for v in worse["baselines"]]
        result = t10_comparator.compare(self.document, self.nominal, self.reference, tolerance_for(self.document), halved=worse)
        self.assertEqual(result["status"], "passed")
        self.assertIn("bit_identical", result["halving_reading"])
        self.assertFalse(result["halving_reading"]["bit_identical"])
        self.assertNotIn("halving", result["checks"])
        same = solved(self.document, 1e-10 / 2)
        result = t10_comparator.compare(self.document, self.nominal, self.reference, tolerance_for(self.document), halved=same)
        self.assertEqual(result["halving_reading"]["bit_identical"], same["baselines"] == self.nominal["baselines"])

    def test_c5_zero_sum_of_the_product_and_the_reference(self):
        self.assertEqual(sum(Fraction(i["exact"]) for i in self.reference["baselines"]), 0)
        shifted = copy.deepcopy(self.nominal)
        shifted["baselines"] = [v + 1e-9 for v in shifted["baselines"]]
        result = t10_comparator.compare(self.document, shifted, self.reference, tolerance_for(self.document))
        self.assertFalse(result["zero_sum"]["passed"])
        self.assertEqual(result["status"], "failed")

    @staticmethod
    def state_holds(record: dict) -> bool:
        """Fix round 2: a record is drafted (no frozen_by), or frozen by a named person (a non-empty frozen_by string)."""
        if record["state"] == "drafted":
            return record["frozen_by"] is None
        return record["state"] == "frozen" and isinstance(record["frozen_by"], str) and bool(record["frozen_by"].strip())

    def test_c_the_records_hold_the_stage_plan_values(self):
        for bad in ({"state": "frozen", "frozen_by": None}, {"state": "frozen", "frozen_by": " "}, {"state": "drafted", "frozen_by": "x"},
                    {"state": "proposed", "frozen_by": "x"}):
            self.assertFalse(self.state_holds(bad), bad)
        record = json.loads(TOLERANCE.read_text(encoding="utf-8"))
        self.assertTrue(self.state_holds(record), (record["state"], record["frozen_by"]))
        self.assertEqual((record["stopping"], record["safety"], record["tau_baselines"], record["tau_map"]), (1e-10, 10, 2.5e-8, 2.2e-8))
        self.assertEqual((record["kappa"], record["map_gain"]), (24.47, 0.8757))
        self.assertEqual((record["ladder"], record["min_informative_steps"], record["zero_sum_relative"]), (LADDER, 2, 1e-13))
        noiseless = json.loads(NOISELESS_TOLERANCE.read_text(encoding="utf-8"))
        self.assertTrue(self.state_holds(noiseless), (noiseless["state"], noiseless["frozen_by"]))
        self.assertEqual((noiseless["stopping"], noiseless["safety"], noiseless["tau_baselines"], noiseless["tau_map"], noiseless["ladder"],
                          noiseless["min_informative_steps"], noiseless["zero_sum_relative"], noiseless["kappa"], noiseless["map_gain"]),
                         (1e-13, 10, 2.5e-11, 2.2e-11, None, None, 1e-13, 24.47, 0.8757))
        self.assertEqual(set(noiseless), set(record))

if __name__ == "__main__":
    unittest.main()
