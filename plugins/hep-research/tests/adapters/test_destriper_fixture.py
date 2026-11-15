"""adapters/destriper, T10 replay stage 1 (docs/dev/detector-reconstruction/t10-replay-stage-plan.md, section 2): the fixture
generator t10-destripe/1 and its negative variants. Every expectation (F1-F8) is fixed in the stage plan before the generator was
written; the numbers of F4 are recomputed here with NumPy from the generated pointing, not read from the generator.
Run from the plugin root: python -m unittest tests.adapters.test_destriper_fixture -v
"""
from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

import numpy

ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / "adapters" / "destriper" / "assets"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ASSETS / "fixture_tools"))

import t10_fixture  # noqa: E402
from contracts.reconstruction import read_sidecar  # noqa: E402
from tests.contracts import reconstruction_fixtures  # noqa: E402

SEED = 20260
DATA_KEYS = {"format", "role", "unit", "pixels", "baseline_length", "noise_premise", "pixel", "value"}


def operators(timestream: dict):
    """P, F, M and the reduced operator D = F^T Z F, written here from the stage plan's model."""
    pixel = numpy.array(timestream["pixel"])
    samples, length, pixels = len(pixel), timestream["baseline_length"], timestream["pixels"]
    P = numpy.zeros((samples, pixels))
    P[numpy.arange(samples), pixel] = 1
    F = numpy.zeros((samples, samples // length))
    F[numpy.arange(samples), numpy.arange(samples) // length] = 1
    M = P.T @ P
    Z = numpy.eye(samples) - P @ numpy.linalg.inv(M) @ P.T
    return P, F, M, F.T @ Z @ F


def components(timestream: dict) -> list[set]:
    """Connected components of the pixel-baseline graph, as sets of ("p", i) and ("b", j)."""
    length = timestream["baseline_length"]
    edges = {(("p", p), ("b", t // length)) for t, p in enumerate(timestream["pixel"])}
    nodes = {node for edge in edges for node in edge}
    found, left = [], set(nodes)
    while left:
        stack, part = [left.pop()], set()
        while stack:
            node = stack.pop()
            part.add(node)
            for first, second in edges:
                for here, there in ((first, second), (second, first)):
                    if here == node and there in left:
                        left.discard(there)
                        stack.append(there)
        found.append(part)
    return found


class GeneratorTests(unittest.TestCase):
    def test_f1_same_seed_same_bytes_other_seed_other_pointing(self):
        with tempfile.TemporaryDirectory() as first, tempfile.TemporaryDirectory() as second:
            for variant in t10_fixture.VARIANTS:
                a = t10_fixture.write(variant, SEED, Path(first))
                b = t10_fixture.write(variant, SEED, Path(second))
                for left, right in zip(a, b):
                    self.assertEqual(Path(left).read_bytes(), Path(right).read_bytes(), variant)
        other, _ = t10_fixture.generate("noisy", SEED + 1)
        here, _ = t10_fixture.generate("noisy", SEED)
        self.assertNotEqual(other["pixel"], here["pixel"])

    def test_f2_data_side_file_holds_no_seed_truth_or_variant(self):
        for variant in t10_fixture.VARIANTS:
            timestream, truth = t10_fixture.generate(variant, SEED)
            self.assertEqual(set(timestream), DATA_KEYS)
            self.assertEqual(timestream["format"], "destriper-timestream/1")
            self.assertEqual(timestream["role"], "reconstruction-input")
            text = json.dumps(timestream)
            self.assertNotIn("seed", text)
            self.assertNotIn(str(SEED), text)
            self.assertNotIn(variant, text)
            self.assertEqual(truth["format"], "destriper-truth/1")
            self.assertEqual((truth["seed"], truth["variant"]), (SEED, variant))

    def test_f3_every_pixel_observed_and_one_component(self):
        timestream, _ = t10_fixture.generate("noisy", SEED)
        self.assertEqual((timestream["pixels"], timestream["baseline_length"], len(timestream["pixel"])), (16, 8, 256))
        hits = numpy.bincount(timestream["pixel"], minlength=16)
        self.assertEqual((int(hits.min()), int(hits.max())), (6, 28))
        self.assertEqual(len(components(timestream)), 1)

    def test_f4_condition_number_and_map_gain(self):
        timestream, _ = t10_fixture.generate("noisy", SEED)
        P, F, M, D = operators(timestream)
        eigenvalues = numpy.sort(numpy.linalg.eigvalsh(D))
        self.assertLess(abs(eigenvalues[0]), 1e-10)
        self.assertGreater(eigenvalues[1], 1e-3)
        self.assertAlmostEqual(eigenvalues[-1] / eigenvalues[1], 24.47, delta=0.01)
        self.assertAlmostEqual(numpy.linalg.norm(numpy.linalg.inv(M) @ P.T @ F, 2), 0.8757, delta=1e-4)

    def test_f5_noiseless_is_exact_and_values_away_from_zero(self):
        timestream, truth = t10_fixture.generate("noiseless", SEED)
        length = timestream["baseline_length"]
        for t, (p, y) in enumerate(zip(timestream["pixel"], timestream["value"])):
            self.assertEqual(y, truth["map"][p] + truth["baselines"][t // length])
        self.assertEqual(sum(truth["baselines"]), 0)
        for value in truth["map"] + truth["baselines"]:
            self.assertEqual(value, int(value))
            self.assertGreaterEqual(abs(value), 1)
        self.assertEqual(truth["sigma"], 0)

    def test_f6_noisy_residual_statistics(self):
        timestream, truth = t10_fixture.generate("noisy", SEED)
        length = timestream["baseline_length"]
        residual = numpy.array([y - truth["map"][p] - truth["baselines"][t // length]
                                for t, (p, y) in enumerate(zip(timestream["pixel"], timestream["value"]))])
        self.assertEqual(truth["sigma"], 1)
        self.assertTrue(0.85 <= residual.std(ddof=1) <= 1.15, residual.std(ddof=1))
        self.assertLess(abs(residual.mean()), 0.25)
        noiseless, _ = t10_fixture.generate("noiseless", SEED)
        self.assertEqual(noiseless["pixel"], timestream["pixel"])

    def test_f7_disconnected_has_two_components(self):
        timestream, _ = t10_fixture.generate("disconnected", SEED)
        found = sorted(components(timestream), key=lambda part: min(i for kind, i in part if kind == "p"))
        self.assertEqual(len(found), 2)
        self.assertEqual(found[0], {("p", i) for i in range(8)} | {("b", j) for j in range(16)})
        self.assertEqual(found[1], {("p", i) for i in range(8, 16)} | {("b", j) for j in range(16, 32)})
        self.assertEqual(int(numpy.bincount(timestream["pixel"], minlength=16).min()) > 0, True)


class NegativeVariantTests(unittest.TestCase):
    """F8: each negative variant is one change to a global scan block, refused by the contract with its code."""

    def test_f8_each_negative_variant_is_refused_with_its_code(self):
        good = reconstruction_fixtures.scan_product(reconstruction_fixtures.global_scan())
        self.assertTrue(read_sidecar(good).ok)
        self.assertEqual(set(t10_fixture.NEGATIVE_VARIANTS), {"jitter", "chunk-average", "unique-without-constraint"})
        for name, (change, code) in t10_fixture.NEGATIVE_VARIANTS.items():
            with self.subTest(variant=name):
                bad = copy.deepcopy(good)
                change(bad["scan"])
                codes = {finding.code for finding in read_sidecar(bad).errors}
                self.assertIn(code, codes)

    def test_f8_a_negative_variant_does_not_change_its_input(self):
        good = reconstruction_fixtures.scan_product(reconstruction_fixtures.global_scan())
        kept = copy.deepcopy(good)
        t10_fixture.negative_variant(good, "jitter")
        self.assertEqual(good, kept)


if __name__ == "__main__":
    unittest.main()
