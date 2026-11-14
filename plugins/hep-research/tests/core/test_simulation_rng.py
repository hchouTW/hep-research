"""Random numbers of the response pipeline: known-answer vectors, endpoints, consumption rules, sampling moments and exact sums (Section 15.1, S4 rows)."""
from __future__ import annotations

import math
import statistics
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from core.simulation import rng  # noqa: E402

KNOWN_ANSWERS = (  # Random123, tests/kat_vectors: philox4x32 10
    ((0, 0, 0, 0), (0, 0), (0x6627E8D5, 0xE169C58D, 0xBC57AC4C, 0x9B00DBD8)),
    ((0xFFFFFFFF,) * 4, (0xFFFFFFFF,) * 2, (0x408F276D, 0x41C83B0E, 0xA20BC7C6, 0x6D5451FD)),
    ((0x243F6A88, 0x85A308D3, 0x13198A2E, 0x03707344), (0xA4093822, 0x299F31D0), (0xD16CFE09, 0x94FDCCEB, 0x5001E420, 0x24126EA1)),
)
KEY = rng.volume_key(12345, "quanta", 0)


def stream(identity=7, event=1, sub_index=0):
    return rng.SubStream(KEY, event, identity, sub_index)


class Philox(unittest.TestCase):
    def test_known_answers(self):
        for counter, key, wanted in KNOWN_ANSWERS:
            self.assertEqual(rng.philox4x32_10(counter, key), wanted)


class Uniforms(unittest.TestCase):
    def test_the_extremes_stay_inside_the_interval(self):
        self.assertEqual(rng.uniforms_of((0, 0, 0, 0)), (2.0 ** -53, 2.0 ** -53))
        high = rng.uniforms_of((0xFFFFFFFF,) * 4)
        self.assertEqual(high, (1.0 - 2.0 ** -53, 1.0 - 2.0 ** -53))
        self.assertLess(high[0], 1.0)

    def test_word_order_is_high_then_low(self):
        first, second = rng.uniforms_of((0x80000000, 0, 0, 0x80000000))
        self.assertAlmostEqual(first, 0.5, places=12)
        self.assertLess(second, 1e-9)


class Keys(unittest.TestCase):
    def test_two_readouts_get_different_channel_streams(self):
        left, right = (rng.channel_key(1, name, "noise", 0) for name in ("ecal", "hcal"))
        self.assertNotEqual(left, right)
        self.assertNotEqual(rng.SubStream(left, 0, 5).group(), rng.SubStream(right, 0, 5).group())

    def test_volume_streams_do_not_depend_on_a_readout(self):
        self.assertEqual(rng.SubStream(rng.volume_key(1, "s", 0), 0, 9).poisson(50.0), rng.SubStream(rng.volume_key(1, "s", 0), 0, 9).poisson(50.0))

    def test_repeated_keys_are_reported(self):
        self.assertEqual(rng.distinct_keys([(1, 2), (3, 4), (1, 2)]), [(1, 2)])

    def test_the_event_range_is_enforced(self):
        rng.check_event_range(2 ** 32 - 1, 1)
        with self.assertRaises(rng.RngError):
            rng.check_event_range(2 ** 32 - 1, 2)


class Consumption(unittest.TestCase):
    def test_each_draw_starts_a_new_output_group(self):
        s = stream()
        s.gaussian()
        s.exponential()
        self.assertEqual(s.groups_used, 2)

    def test_a_draw_depends_only_on_those_before_it_in_its_sub_stream(self):
        a, b = stream(), stream()
        a.poisson(4.0)
        b.gaussian()
        self.assertEqual(a.exponential(), b.exponential())
        self.assertEqual(stream(identity=3).gaussian(), stream(identity=3).gaussian())

    def test_sub_index_and_exhaustion_are_refused(self):
        with self.assertRaises(rng.RngError):
            stream(sub_index=2 ** 16)
        s = stream()
        s.groups_used = 2 ** 16
        with self.assertRaises(rng.RngError):
            s.group()


def draws(method, count, *arguments):
    return [getattr(rng.SubStream(KEY, at, 11), method)(*arguments) for at in range(count)]


class Moments(unittest.TestCase):
    def close(self, values, mean, variance):
        count = len(values)
        self.assertLess(abs(statistics.fmean(values) - mean), 5 * math.sqrt(variance / count))
        self.assertLess(abs(statistics.pvariance(values) / variance - 1), 0.05)

    def test_gaussian_and_exponential(self):
        self.close(draws("gaussian", 20000, 3.0, 2.0), 3.0, 4.0)
        self.close(draws("exponential", 20000), 1.0, 1.0)

    def test_poisson_on_both_sides_of_the_switch(self):
        for mean in (0.5, 7.0, 29.5, 30.0, 400.0):
            self.close(draws("poisson", 20000, mean), mean, mean)

    def test_binomial_on_both_sides_of_the_switch(self):
        for trials, p in ((20, 0.3), (100, 0.29), (200, 0.25), (1000, 0.5), (5000, 0.9), (100000, 0.001)):
            self.close(draws("binomial", 20000, trials, p), trials * p, trials * p * (1 - p))

    def test_gamma(self):
        self.close(draws("gamma", 20000, 4.0), 4.0, 4.0)

    def test_multinomial_conserves_its_trials(self):
        for at in range(200):
            self.assertEqual(sum(rng.SubStream(KEY, at, 2).multinomial(1000, [0.1, 0.25, 0.05])), 1000)


class Sums(unittest.TestCase):
    def test_the_vector_of_section_ten_two(self):
        self.assertEqual(rng.exact_sum([2.0 ** 53, 1.0, 2.0 ** -80]), 9007199254740994.0)

    def test_merging_partial_sums_keeps_one_rounding(self):
        chunks = [rng.partial_sums([2.0 ** 53, 1.0]), rng.partial_sums([2.0 ** -80])]
        self.assertEqual(rng.merge_partial_sums(chunks), 9007199254740994.0)

    def test_rounding_each_chunk_first_gives_the_wrong_answer(self):
        rounded = [math.fsum([2.0 ** 53, 1.0]), math.fsum([2.0 ** -80])]
        self.assertEqual(sum(rounded), 9007199254740992.0)

    def test_sums_agree_with_cpython(self):
        values = [(-1.0) ** at * 10.0 ** (at % 30 - 15) / (at + 1) for at in range(2000)]
        self.assertEqual(rng.exact_sum(values), math.fsum(values))
        self.assertEqual(rng.merge_partial_sums([rng.partial_sums(values[:700]), rng.partial_sums(values[700:])]), math.fsum(values))

    def test_summands_out_of_range_are_refused(self):
        for bad in (1e300, float("inf"), float("nan")):
            with self.assertRaises(rng.RngError):
                rng.exact_sum([1.0, bad])


if __name__ == "__main__":
    unittest.main()
