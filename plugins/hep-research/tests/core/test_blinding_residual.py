"""P4.3 counterexample suite (C02, plugin part): for each blinding mode of DP-3, the attacks of protected-data-architecture.md
§6.2 are carried out on synthetic data. Each is either detected by core.blinding.residual.residual_checks, refused by the
transform, or documented in core.blinding.transforms.LIMITS. The attacks show what a released file gives away; the
transforms never output key material. Synthetic values only."""
from __future__ import annotations

import json
import math
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from core.blinding import transforms as tf  # noqa: E402
from core.blinding.blinding import scan_text  # noqa: E402
from core.blinding.residual import residual_checks  # noqa: E402

EDGES = [0, 10, 20, 30, 40, 50]
COUNTS = [12.0, 30.0, 47.0, 25.0, 9.0]
REGION = {"variable": "m", "low": 20, "high": 30}
SHIFT = 3.7316   # synthetic secret offset
FACTOR = 1.8125  # synthetic secret scale


def codes(release, **context):
    return {r["code"] for r in residual_checks(release, context)}


class NoKeyMaterial(unittest.TestCase):
    def test_parameters_and_released_never_carry_the_key(self):
        off = tf.common_offset([1.25, 2.5, 7.75], SHIFT)
        sc = tf.common_scale([1.25, 2.5, 7.75], FACTOR)
        for rel, key in ((off, SHIFT), (sc, FACTOR)):
            text = json.dumps({"released": rel["released"], "parameters": rel["parameters"]})
            self.assertEqual(scan_text(text, [key]), [], "the key is in the release")
            self.assertIn(key, rel["sealed"])  # ... and is sealed for the custodian's output scan
            self.assertFalse(any(k in rel["parameters"] for k in ("shift", "factor", "offset", "scale")))
        mask = tf.binned_mask(EDGES, COUNTS, REGION, errors=[math.sqrt(c) for c in COUNTS])
        self.assertIsNone(mask["released"]["values"][2])
        self.assertIsNone(mask["released"]["errors"][2])  # rule 7: the error goes with the value
        self.assertIn(47.0, mask["sealed"])


class BinnedMaskCounterexamples(unittest.TestCase):
    def test_two_regions_reveal_the_difference(self):
        a = tf.binned_mask(EDGES, COUNTS, REGION)
        b = tf.binned_mask(EDGES, COUNTS, {"variable": "m", "low": 30, "high": 40})
        recovered = b["released"]["values"][2]  # bin 2 is masked in a, not in b
        self.assertEqual(recovered, COUNTS[2])
        self.assertIn("mask.region_mismatch_with_other", codes(a, other_releases=[b]))

    def test_sideband_total_is_public_by_definition(self):
        a = tf.binned_mask(EDGES, COUNTS, REGION)
        side = sum(v for v in a["released"]["values"] if v is not None)
        self.assertEqual(side, sum(COUNTS) - COUNTS[2])
        self.assertNotIn(side, a["sealed"])  # not sealed: one public data give it
        self.assertTrue(any("sideband" in t for t in tf.LIMITS["binned-mask"]))


class EventRemovalCounterexamples(unittest.TestCase):
    def setUp(self):
        self.events = [{"event_id": i, "m": m} for i, m in enumerate([3.0, 12.0, 21.0, 22.5, 26.0, 33.0, 41.0, 48.0])]

    def test_totals_elsewhere_give_the_removed_count(self):
        rel = tf.event_removal(self.events, "m", REGION, drop_fields=["event_id"])
        self.assertEqual(len(self.events) - len(rel["released"]["events"]), 3)  # with a visible total
        self.assertIn("removal.totals_elsewhere", codes(rel, visible_totals=True))
        self.assertNotIn("removal.totals_elsewhere", codes(rel))
        self.assertIn(3.0, rel["sealed"])  # the removed count is sealed

    def test_index_gaps(self):
        kept_ids = tf.event_removal(self.events, "m", REGION)
        ids = [e["event_id"] for e in kept_ids["released"]["events"]]
        gaps = sorted(set(range(min(ids), max(ids) + 1)) - set(ids))
        self.assertEqual(len(gaps), 3)  # the gaps count the removed events
        self.assertIn("removal.index_fields", codes(kept_ids))
        dropped = tf.event_removal(self.events, "m", REGION, drop_fields=["event_id"])
        self.assertNotIn("removal.index_fields", codes(dropped))
        self.assertTrue(all("event_id" not in e for e in dropped["released"]["events"]))
        for name in ("run", "luminosityBlock", "eventNumber", "evtNo", "entry"):  # repeated or camelCase names too
            evs = [{"m": e["m"], name: 7} for e in self.events]
            self.assertIn("removal.index_fields", codes(tf.event_removal(evs, "m", REGION)), name)
        ms = [e["m"] for e in dropped["released"]["events"]]
        self.assertEqual(ms, sorted(ms))  # input order is not kept either

    def test_subtraction_across_releases(self):
        a = tf.event_removal(self.events, "m", REGION, drop_fields=["event_id"])
        b = tf.event_removal(self.events, "m", {"variable": "m", "low": 25, "high": 35}, drop_fields=["event_id"])
        revealed = {e["m"] for e in b["released"]["events"]} - {e["m"] for e in a["released"]["events"]}
        self.assertEqual(revealed, {21.0, 22.5})
        self.assertIn("removal.region_mismatch_with_other", codes(a, other_releases=[b]))


class CommonOffsetCounterexamples(unittest.TestCase):
    def test_physical_boundary_bounds_the_offset(self):
        xs = [0.0, 0.8, 2.4, 5.1]  # a non-negative quantity whose minimum sits at the boundary
        rel = tf.common_offset(xs, SHIFT)
        self.assertAlmostEqual(min(rel["released"]["values"]), SHIFT)  # the minimum reveals the offset
        self.assertIn("offset.boundary", codes(rel, nonnegative=True))
        self.assertIn("offset.boundary", codes(rel, reference_points=[91.1876]))

    def test_counts_are_refused(self):
        """Poisson structure: variance about mean - c; so offsets on counts are refused outright."""
        with self.assertRaises(ValueError):
            tf.common_offset(COUNTS, SHIFT, kind="counts")

    def test_integer_residue(self):
        rel = tf.common_offset([3.0, 8.0, 14.0, 22.0], SHIFT)
        frac = {round(v % 1.0, 9) for v in rel["released"]["values"]}
        self.assertEqual(len(frac), 1)
        self.assertAlmostEqual(frac.pop(), SHIFT % 1.0)  # the offset's fractional part
        self.assertIn("offset.integer_residue", codes(rel))
        self.assertNotIn("offset.integer_residue", codes(tf.common_offset([3.1, 8.27, 14.9], SHIFT)))

    def test_uncertainties_before_the_offset(self):
        rel = tf.common_offset([1.5, 2.25, 4.0], SHIFT)
        self.assertEqual(rel["released"]["uncertainties"], "withheld")
        self.assertIn("offset.uncertainties", codes(rel, uncertainties_released=True))

    def test_integer_residue_at_large_values(self):
        rel = tf.common_offset([1.0e7, 2.5e7 + 3, 4.0e7 + 11], SHIFT)
        self.assertIn("offset.integer_residue", codes(rel))

    def test_two_offsets(self):
        xs = [1.5, 2.25, 4.0]
        a, b = tf.common_offset(xs, SHIFT), tf.common_offset(xs, SHIFT + 1.0)
        diff = {round(y - x, 9) for x, y in zip(a["released"]["values"], b["released"]["values"])}
        self.assertEqual(diff, {1.0})
        self.assertIn("offset.other_offset", codes(a, other_releases=[b]))


class CommonScaleCounterexamples(unittest.TestCase):
    def test_integer_quantization(self):
        rel = tf.common_scale(COUNTS, FACTOR)
        vals = rel["released"]["values"]
        self.assertAlmostEqual(min(vals) / 9.0, FACTOR)  # the smallest count is 9: its multiple gives the scale
        self.assertIn("scale.quantization", codes(rel))
        generic = [math.pi / 7, math.sqrt(2) / 3, math.e / 5, math.log(3) / 2]  # not multiples of a common unit
        self.assertNotIn("scale.quantization", codes(tf.common_scale(generic, FACTOR)))
        big = tf.common_scale([123457.0, 98765.0, 150001.0, 200003.0], FACTOR)  # high-statistics counts
        self.assertIn("scale.quantization", codes(big))
        # values printed to a few decimals are quantized too (multiples of 0.0001 times the scale): reported
        self.assertIn("scale.quantization", codes(tf.common_scale([0.137, 0.522, 0.9013, 0.311], FACTOR)))

    def test_per_event_weights_are_refused(self):
        with self.assertRaises(ValueError):
            tf.common_scale([1.0, 2.0], FACTOR, weights=[1.0, 1.0])

    def test_unscaled_companion(self):
        rel = tf.common_scale([0.137, 0.522, 0.9013], FACTOR)
        companion = [0.137, 0.522, 0.9013]  # e.g. a prediction normalized to the unscaled data
        self.assertAlmostEqual(rel["released"]["values"][0] / companion[0], FACTOR)
        self.assertIn("scale.companion", codes(rel, companions=[companion]))

    def test_unit_area_shape_hides_nothing(self):
        rel = tf.common_scale([0.25, 0.5, 0.25], FACTOR)
        shape = [v / sum(rel["released"]["values"]) for v in rel["released"]["values"]]
        self.assertEqual(shape, [0.25, 0.5, 0.25])  # normalizing removes the scale: shape is retained by design
        unit = tf.common_scale([0.25, 0.5, 0.25], FACTOR)
        unit["released"]["values"] = shape
        self.assertIn("scale.unit_area", codes(unit))


class LimitsAreStated(unittest.TestCase):
    def test_every_mode_states_its_limits(self):
        for mode in tf.MODES:
            self.assertTrue(tf.LIMITS[mode] and all(len(t) > 40 for t in tf.LIMITS[mode]), mode)
        readme = (ROOT / "core" / "blinding" / "README.md").read_text()
        for mode in tf.MODES:
            self.assertIn(f"`{mode}`", readme)

    def test_refused_inputs(self):
        with self.assertRaises(ValueError):
            tf.common_offset([1.0], 0.0)
        with self.assertRaises(ValueError):
            tf.common_scale([1.0], 1.0)
        with self.assertRaises(ValueError):
            tf.event_removal([{"x": 1}], "m", REGION)
        with self.assertRaises(ValueError):
            tf.apply("holdout")


if __name__ == "__main__":
    unittest.main()
