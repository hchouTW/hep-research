"""adapters/acts-tracking, D4 build E2: the T07 Freeze-B scorer of the noise-fixture fake rate, and its runner (freeze-b-proposal.md, section 4 row E2).

Sections cited are of t04-values-v4.md. The scorer is assets/fixture_tools/t07_fake_rate.py, on the scoring side: it reads truth, and no recipe file
imports it. From a run's finding records and truth files, on any block the Freeze-B run may use and any event count, it gives per noise bin the fake
count by section 7's match rule and section 5.2's rate rule: `r_dev`, `L_dev`, `U_dev`, `k`, `n`, `N_ev`, `DEFF_hat`, and the check `U_dev <= C` with
`C` = 0.005 (section 8.3, "Value at Freeze A"). If `U_dev` exceeds `C` the record says "evaluation does not start" (section 8.3) and the check exits 1.
U-B7 (decisions.md, "Freeze B proposal: the user's answers to section 5.1"): `L_dev` and the counts are recorded beside `r_dev`. U-B11: each noise
data file is deleted after its SHA-256 matches the finding record's `data_sha256` and the truth file's, and never otherwise.

Every test here runs on hand-made events and counts; none needs a build. Two classes read files from outside this module and skip without them, and
the build job counts a skip as a failure:
- FrozenCodingAgreement: the frozen coding of the same rule, `calc-rate-rule.py` (t04-values-v4.md section 18, row A, `a70704dc...`), named by
  HEP_T04_CALC_RATE_RULE. Its function `bound` is called, never edited or copied.
- RecordedRunAgreement: a runner's output folder (HEP_ACTS_TRACKING_FAKE_RATE_RUN) with the frozen coding: on block-1 counts the two agree.

Expectations, fixed before the first run (the D4 E2 report, "Predictions"):
- The rate rule's bounds equal the hand computations below to 1e-12 relative (beta quantiles against a bisection of the binomial tail or of
  scipy.special.betainc), and `DEFF_hat` equals its hand value exactly in binary64 or to 1e-15.
- The scorer's `U_dev` equals the frozen `bound` exactly (==) on every count set, since both evaluate the same expressions in the same order.

Run from the plugin root: python -m unittest tests.adapters.test_acts_fake_rate -v
"""
from __future__ import annotations

import ast
import hashlib
import importlib.util
import math
import os
import re
import stat
import sys
import tempfile
import unittest
from pathlib import Path

import numpy
from scipy import special

ROOT = Path(__file__).resolve().parents[2]
ADAPTER = ROOT / "adapters" / "acts-tracking"
ASSETS = ADAPTER / "assets"
NATIVE = ASSETS / "native"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ASSETS / "fixture_tools"))

import acts_finding_record as finding_record  # noqa: E402
import t07_fake_rate as fake_rate  # noqa: E402
import t07_fixture_files as fixture_files  # noqa: E402
import t07_truth_files as truth_files  # noqa: E402

FROZEN_CODING = os.environ.get("HEP_T04_CALC_RATE_RULE", "")
FROZEN_CODING_SHA256 = "a70704dcd6aa6df67c42e5ac4779bb2172aa68150bb1c98efff72335205995c9"  # t04-values-v4.md section 18, row A: a70704dcd6aa6df6
RECORDED_RUN = os.environ.get("HEP_ACTS_TRACKING_FAKE_RATE_RUN", "")
HAND_TOLERANCE = 1e-12


# ---- Hand computations, standard library only: the Clopper-Pearson bounds as roots of the binomial tail, by bisection.

def binomial_cdf(k: int, n: int, p: float) -> float:
    return math.fsum(math.comb(n, i) * p ** i * (1.0 - p) ** (n - i) for i in range(k + 1))


def bisect(function, low: float, high: float) -> float:
    """The root of a monotone function on [low, high], to the last bit."""
    for _ in range(200):
        middle = 0.5 * (low + high)
        if (function(middle) > 0.0) == (function(low) > 0.0):
            low = middle
        else:
            high = middle
    return 0.5 * (low + high)


def upper_by_hand(k: int, n: int, level: float = 0.95) -> float:
    """One-sided upper bound: the p at which P(X <= k) = 1 - level."""
    return bisect(lambda p: binomial_cdf(k, n, p) - (1.0 - level), 0.0, 1.0)


def lower_by_hand(k: int, n: int, level: float = 0.95) -> float:
    """One-sided lower bound: the p at which P(X >= k) = 1 - level."""
    return bisect(lambda p: (1.0 - binomial_cdf(k - 1, n, p)) - (1.0 - level), 0.0, 1.0)


def close(case: unittest.TestCase, found: float, expected: float, tolerance: float = HAND_TOLERANCE) -> None:
    case.assertLessEqual(abs(found - expected), tolerance * abs(expected), f"{found!r} against {expected!r}")


# ---- Hand-made fixture files, for the runner's checks.

def truth_file_bytes(events, data_sha256: str, stratum: int = 0, block: int = 1, fixture_id: int = 7002) -> bytes:
    """A truth file: events are lists of particles, each a list of eight hit keys (truth_files.NO_HIT_KEY where the plane has none)."""
    header = numpy.zeros(1, dtype=truth_files.TRUTH_HEADER)
    header["magic"], header["role"], header["generator"] = truth_files.TRUTH_MAGIC, truth_files.TRUTH_ROLE.encode(), b"hand-made"
    header["fixture_id"], header["block"], header["stratum"], header["event_count"] = fixture_id, block, stratum, len(events)
    header["sigma_loc0_mm"] = header["sigma_loc1_mm"] = 0.02
    header["data_sha256"] = numpy.frombuffer(bytes.fromhex(data_sha256), dtype="V32")[0]
    pieces = [header.tobytes()]
    for index, particles in enumerate(events):
        head = numpy.zeros(1, dtype=truth_files.TRUTH_EVENT)
        head["event_index"], head["occupancy_level"], head["track_count"] = index, stratum % 3, len(particles)
        tracks = numpy.zeros(len(particles), dtype=truth_files.TRACK)
        for position, keys in enumerate(particles):
            tracks[position]["particle_key"] = position
            tracks[position]["hit_keys"] = keys
        pieces += [head.tobytes(), tracks.tobytes()]
    return b"".join(pieces)


def keys_of(*keys) -> list:
    """Eight hit keys, the given ones on the first planes and none on the rest."""
    return list(keys) + [truth_files.NO_HIT_KEY] * (8 - len(keys))


def record_text(events_tracks, data_sha256: str, product_id: str = "hand-made") -> str:
    """acts-tracking-finding-record/1 of hand-made events: each event a list of selected tracks, each a list of hit keys."""
    configuration = {name: "1" for name in finding_record.CONFIGURATION_KEYS}
    events = []
    for ordinal, tracks in enumerate(events_tracks):
        found = [{"key": f"event-{ordinal}-candidate-{index}", "ordinal": ordinal, "seed_planes": "1-2-3", "outcome": "selected", "failure_category": "none",
                  "search_truncated": False, "measurements": len(keys), "holes": 0, "search_chi2": 1.0, "q_over_p": 0.25, "fit_chi2": 1.0,
                  "fit_coordinates": 2 * len(keys), "hit_keys": list(keys)} for index, keys in enumerate(tracks)]
        events.append({"ordinal": ordinal, "hit_count": 64, "seeds_found": len(found), "seeds_run": len(found), "seeds_skipped": 0, "seeds_failed": 0,
                       "seeds_without_candidate": 0, "seeds_truncated": 0, "seed_budget_reached": 0, "ambiguity_budget_reached": 0, "candidates": len(found),
                       "selected": len(found), "failure_category": "none" if found else "seed-or-finding", "found": found})
    header = {"recipe": finding_record.FINDING_RECIPE, "stage": finding_record.FINDING_STAGE, "evidence_class": finding_record.FINDING_EVIDENCE_CLASS,
              "product_id": product_id, "data_sha256": data_sha256, "product_events": 0, "configuration_sha256": "c" * 64}
    return finding_record.format_record({"header": header, "configuration": configuration, "events": events})


# Two hand-made noise events: event 0 has a true track (keys 0-5 of particle 0) and a fake (two hits of each particle and two noise hits);
# event 1 has one true track of particle 1 with one noise hit (5 of 6: matched). So m = (2, 1), y = (1, 0).
HAND_PARTICLES = [[keys_of(0, 1, 2, 3, 4, 5, 6, 7), keys_of(8, 9, 10, 11, 12, 13, 14, 15)], [keys_of(0, 1, 2, 3, 4, 5), keys_of(6, 7, 8, 9, 10, 11)]]
HAND_TRACKS = [[[0, 1, 2, 3, 4, 5], [6, 7, 8, 9, 20, 21]], [[6, 7, 8, 9, 10, 30]]]


def hand_made_data(events: int = 2) -> bytes:
    hits = [(1 + key % 8, fixture_files.on_hit_grid(0.5 * key).item(), 0.0) for key in range(32)]
    return fixture_files.encode_data_file(0.02, [hits] * events)


def frozen_module():
    spec = importlib.util.spec_from_file_location("frozen_calc_rate_rule", FROZEN_CODING)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# ---- Section 7's match rule.

class MatchRuleFakes(unittest.TestCase):
    """A track matches a particle if more than 50 % of its measurements, noise hits included, come from it; a fake matches none. Denominator: all
    reconstructed tracks of the bin's events."""

    def test_a_track_with_most_of_its_hits_from_one_particle_matches(self):
        self.assertEqual(fake_rate.event_counts([[0, 1, 2, 3, 4, 50]], [[0, 1, 2, 3, 4, 5]]), (1, 0))

    def test_exactly_half_is_a_fake(self):
        self.assertEqual(fake_rate.event_counts([[0, 1, 2, 50, 51, 52]], [[0, 1, 2, 3, 4, 5]]), (1, 1))

    def test_noise_hits_count_in_the_denominator(self):
        # 4 of 8 from the particle: half, so a fake, though every non-noise hit is the particle's.
        self.assertEqual(fake_rate.event_counts([[0, 1, 2, 3, 60, 61, 62, 63]], [[0, 1, 2, 3, 4, 5, 6, 7]]), (1, 1))

    def test_two_particles_at_half_each_match_neither(self):
        self.assertEqual(fake_rate.event_counts([[0, 1, 2, 10, 11, 12]], [[0, 1, 2, 3], [10, 11, 12, 13]]), (1, 1))

    def test_an_event_with_no_track_counts_nothing(self):
        self.assertEqual(fake_rate.event_counts([], [[0, 1, 2, 3, 4, 5]]), (0, 0))

    def test_duplicates_are_not_fakes(self):
        # Two tracks of one particle: both match it; section 8.3, "Duplicates do not share it".
        self.assertEqual(fake_rate.event_counts([[0, 1, 2, 3, 4, 5], [0, 1, 2, 3, 4, 70]], [[0, 1, 2, 3, 4, 5, 6, 7]]), (2, 0))

    def test_a_hit_key_owned_twice_is_refused(self):
        with self.assertRaises(ValueError):
            fake_rate.event_counts([[0, 1, 2]], [[0, 1, 2], [2, 3, 4]])

    def test_the_counts_agree_with_the_development_scoring(self):
        """The same rule as tests/adapters/test_acts_finding.py's scored_event, which printed the block-1 readings of job 7551619."""
        from tests.adapters import test_acts_finding as finding_tests
        for tracks, particles in zip(HAND_TRACKS, HAND_PARTICLES):
            own = [[key for key in keys if key != truth_files.NO_HIT_KEY] for keys in particles]
            scored = finding_tests.scored_event([{"hit_keys": keys, "chi2": 1.0, "ndf": 1} for keys in tracks], [{"hit_keys": keys} for keys in own])
            self.assertEqual(fake_rate.event_counts(tracks, own), (scored["reconstructed"], scored["fakes"]))


# ---- Section 5.2's rate rule, against hand computation.

class RateRuleByHand(unittest.TestCase):
    def test_events_without_a_track_count_in_n_ev(self):
        found = fake_rate.rate_rule([6, 0, 6, 0], [0, 0, 1, 0])
        self.assertEqual((found["events"], found["events_without_tracks"], found["tracks"]), (4, 2, 12))

    def test_the_level_of_l_dev_is_freeze_a_s(self):
        """O1, ruled: one-sided 95 % on both bounds, as Freeze A's closed form of F2 (t04-v4 calc-closed-form.py lines 194-199: 2.326 = 1.645 x sqrt 2)."""
        self.assertIn("calc-closed-form.py lines 194-199", fake_rate.RATE_RULE)
        self.assertIsNone(re.search(r"/ceph|/var/tmp|/tmp/|/dicos|/home/|/sharedfs", fake_rate.RATE_RULE))

    def test_k_0(self):
        """At k = 0, DEFF_hat is 1 by definition and U = 1 - 0.05^(1/N_ev) (section 5.2, "At k = 0 this is 1 - 0.05^(1/N_ev)"); L_dev and r_dev are 0."""
        found = fake_rate.rate_rule([6] * 3000, [0] * 3000)
        self.assertEqual((found["fakes"], found["tracks"], found["events"]), (0, 18000, 3000))
        self.assertEqual((found["deff_hat"], found["design_effect"], found["l_dev"], found["r_dev"]), (1.0, 1.0, 0.0, 0.0))
        close(self, found["u_dev"], 1.0 - 0.05 ** (1.0 / 3000))
        self.assertEqual(found["u_dev"], found["u_b"])
        close(self, found["u_a"], 1.0 - 0.05 ** (1.0 / 18000))

    def test_k_1(self):
        """N_ev 2, m = (1, 9), y = (0, 1): p = 0.1, residuals (-0.1, 0.1), var = 2 x 0.02 / 100 = 4e-4, p(1-p)/n = 9e-3, DEFF_hat = 2/45, so D = 1.
        U_A is the plain one-sided bound of 1 in 10, L_dev = 1 - 0.95^(1/10); U_B has k_eff 0.2 on 2 events."""
        found = fake_rate.rate_rule([1, 9], [0, 1])
        close(self, found["deff_hat"], 2.0 / 45.0, 1e-15)
        self.assertEqual(found["design_effect"], 1.0)
        close(self, found["u_a"], upper_by_hand(1, 10))
        close(self, found["l_dev"], 1.0 - 0.95 ** 0.1)
        close(self, found["l_dev"], lower_by_hand(1, 10))
        close(self, special.betainc(1.2, 1.8, found["u_b"]), 0.95)
        self.assertEqual(found["u_dev"], max(found["u_a"], found["u_b"]))
        self.assertEqual(found["r_dev"], 0.1)

    def test_k_1_with_equal_objects_per_event(self):
        """Equal m: by hand DEFF_hat = n/(n - 1) at k = 1 (sum of squared residuals (N-1)/N, so var = 1/n^2). A block-1 o3 bin's shape."""
        found = fake_rate.rate_rule([36] * 3000, [1] + [0] * 2999)
        n = 108000
        close(self, found["deff_hat"], n / (n - 1), 1e-13)
        close(self, found["design_effect"], n / (n - 1), 1e-13)
        close(self, special.betainc(1.0 / 36 + 1.0, 3000 - 1.0 / 36, found["u_b"]), 0.95)
        d = n / (n - 1)
        close(self, special.betainc(1.0 / d + 1.0, n / d - 1.0 / d, found["u_a"]), 0.95)
        self.assertEqual(found["u_dev"], found["u_b"])

    def test_k_3_with_d_1(self):
        """N_ev 4, m = 2 each, y = (1, 1, 1, 0): p = 3/8, sum of squared residuals 0.75, var = 4/3 x 0.75 / 64 = 1/64, p(1-p)/n = 15/512, DEFF_hat = 8/15."""
        found = fake_rate.rate_rule([2, 2, 2, 2], [1, 1, 1, 0])
        close(self, found["deff_hat"], 8.0 / 15.0, 1e-15)
        self.assertEqual(found["design_effect"], 1.0)
        close(self, found["u_a"], upper_by_hand(3, 8))
        close(self, found["l_dev"], lower_by_hand(3, 8))
        close(self, special.betainc(2.5, 2.5, found["u_b"]), 0.95)
        self.assertEqual(found["r_dev"], 3 / 8)

    def test_k_3_with_d_above_1(self):
        """y = (2, 1, 0, 0) on m = 2 each: squared residuals 1.5625 + 0.0625 + 0.5625 + 0.5625 = 2.75, DEFF_hat = (11/192) / (15/512) = 88/45. Set A
        uses k/D, n/D (section 5.2, U_A and step 1)."""
        found = fake_rate.rate_rule([2, 2, 2, 2], [2, 1, 0, 0])
        close(self, found["deff_hat"], 88.0 / 45.0, 1e-15)
        d = found["design_effect"]
        self.assertEqual(d, found["deff_hat"])
        close(self, special.betainc(3.0 / d + 1.0, 8.0 / d - 3.0 / d, found["u_a"]), 0.95)
        close(self, 1.0 - special.betainc(3.0 / d, 8.0 / d - 3.0 / d + 1.0, found["l_dev"]), 0.95)

    def test_the_cap_of_30_on_set_b(self):
        """U_B takes min(k, 30)/m (section 5.2). With 40 fakes in 40 events of 10, k_eff is 3, not 4."""
        found = fake_rate.rate_rule([10] * 400, [1] * 40 + [0] * 360)
        close(self, special.betainc(3.0 + 1.0, 400 - 3.0, found["u_b"]), 0.95)

    def test_a_bin_with_no_track_or_only_fakes_is_refused(self):
        with self.assertRaises(ValueError):
            fake_rate.rate_rule([0, 0], [0, 0])
        with self.assertRaises(ValueError):
            fake_rate.rate_rule([2, 1], [2, 1])
        with self.assertRaises(ValueError):
            fake_rate.rate_rule([2], [0])  # one event: N_ev/(N_ev - 1) is undefined
        with self.assertRaises(ValueError):
            fake_rate.rate_rule([2, 2], [3, 0])  # more fakes than tracks in an event

    def test_the_reader_s_bounds_follow_from_the_recorded_counts(self):
        for m, y in (([6] * 3000, [0] * 3000), ([1, 9], [0, 1]), ([2, 2, 2, 2], [2, 1, 0, 0])):
            found = fake_rate.rate_rule(m, y)
            again = fake_rate.bounds_of(found["fakes"], found["tracks"], found["events"], found["deff_hat"])
            for name in again:
                self.assertEqual(again[name], found[name], name)


class LimitCheck(unittest.TestCase):
    """Section 8.3: C(o) = max(0.005, 5 f_ref(o)), 0.005 at all three levels at Freeze A; "If U_dev exceeds C at the Freeze-B run, evaluation does not start"."""

    def test_c_is_freeze_a_s_value(self):
        self.assertEqual(fake_rate.LIMIT_OF_LEVEL, (0.005, 0.005, 0.005))

    def test_u_dev_above_c_refuses_and_says_evaluation_does_not_start(self):
        document = honest_rate_document()
        document["bins"][1] = fake_rate.bin_line_values(1, fake_rate.rate_rule([10] * 3000, [1] * 300 + [0] * 2700), hashes())
        self.assertGreater(document["bins"][1]["u_dev"], 0.005)
        self.assertEqual(document["bins"][1]["within_limit"], "no")
        text = fake_rate.format_rate_record(document)
        parsed = fake_rate.parse_rate_record(text)
        passed, line = fake_rate.evaluation_verdict(parsed)
        self.assertFalse(passed)
        self.assertIn("evaluation does not start", line)
        self.assertIn("stratum 1", line)
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "rate.record"
            path.write_text(text, encoding="utf-8")
            self.assertEqual(fake_rate.main(["check", str(path)]), 1)

    def test_u_dev_at_or_below_c_passes(self):
        passed, line = fake_rate.evaluation_verdict(fake_rate.parse_rate_record(fake_rate.format_rate_record(honest_rate_document())))
        self.assertTrue(passed, line)
        self.assertIn("U_dev <= C", line)

    def test_a_freeze_b_record_without_every_noise_bin_refuses(self):
        """Review M1: at blocks 2 to 5, r_dev and the check are per noise bin, 12 values (v4 8.3); a record of fewer strata does not let evaluation start."""
        document = honest_rate_document()
        document["header"]["block"] = 2
        passed, line = fake_rate.evaluation_verdict(fake_rate.parse_rate_record(fake_rate.format_rate_record(document)))
        self.assertFalse(passed)
        self.assertIn("not every noise bin", line)
        self.assertIn("missing strata [3, 4, 5, 6, 7, 8, 9, 10, 11]", line)
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "rate.record"
            path.write_text(fake_rate.format_rate_record(document), encoding="utf-8")
            self.assertEqual(fake_rate.main(["check", str(path)]), 1)
        document["bins"] = [fake_rate.bin_line_values(stratum, fake_rate.rate_rule([6] * 3000, [0] * 3000), hashes()) for stratum in range(12)]
        self.assertTrue(fake_rate.evaluation_verdict(fake_rate.parse_rate_record(fake_rate.format_rate_record(document)))[0])

    def test_a_block_1_record_names_its_missing_strata_and_passes(self):
        passed, line = fake_rate.evaluation_verdict(fake_rate.parse_rate_record(fake_rate.format_rate_record(honest_rate_document())))
        self.assertTrue(passed)
        self.assertIn("missing strata [3, 4, 5, 6, 7, 8, 9, 10, 11]", line)

    def test_u_dev_equal_to_c_passes(self):
        self.assertTrue(fake_rate.within_limit(0.005, 0))
        self.assertFalse(fake_rate.within_limit(math.nextafter(0.005, 1.0), 0))


# ---- The record and its reader.

def hashes() -> dict:
    return {"data_sha256": "1" * 64, "truth_sha256": "2" * 64, "record_sha256": "3" * 64, "counts_sha256": "4" * 64}


def honest_rate_document() -> dict:
    header = {"recipe": finding_record.FINDING_RECIPE, "configuration_sha256": "5" * 64, "vertex_configuration_sha256": "none", "fixture_id": 7002, "block": 1,
              "events_per_bin": 3000}
    bins = [fake_rate.bin_line_values(stratum, fake_rate.rate_rule([6] * 3000, ([1] if stratum == 2 else [0]) + [0] * 2999), hashes()) for stratum in (0, 1, 2)]
    return {"header": header, "bins": bins}


class RateRecordReader(unittest.TestCase):
    def setUp(self):
        self.text = fake_rate.format_rate_record(honest_rate_document())

    def refused(self, text: str) -> None:
        with self.assertRaises(fake_rate.RateRecordError):
            fake_rate.parse_rate_record(text)

    def replaced(self, before: str, after: str) -> str:
        self.assertIn(before, self.text)
        return self.text.replace(before, after, 1)

    def test_round_trip_and_the_stated_fields(self):
        parsed = fake_rate.parse_rate_record(self.text)
        self.assertEqual(fake_rate.format_rate_record(parsed), self.text)
        self.assertEqual(self.text.split("\n")[0], "t07-noise-fake-rate/1")
        for name in ("match_rule", "rate_rule", "limit_rule"):
            self.assertIn(f"\n{name} ", self.text)
        for field in ("fakes", "tracks", "events", "events_without_tracks", "deff_hat", "l_dev", "u_dev", "r_dev", "limit", "within_limit"):
            self.assertIn(f" {field} ", self.text)
        self.assertEqual(parsed["bins"][2]["fakes"], 1)

    def test_a_truncated_record_or_text_after_its_end_is_refused(self):
        self.refused(self.text[:self.text.index("\nend ") + 1])
        self.refused(self.text + "bin 3\n")
        self.refused(self.text[:-1])

    def test_another_format_or_rule_version_is_refused(self):
        self.refused(self.replaced("t07-noise-fake-rate/1", "t07-noise-fake-rate/2"))
        self.refused(self.replaced("section 5.2", "section 5.3"))
        self.refused(self.replaced("confidence 0.95", "confidence 0.9"))
        self.refused(self.replaced("k_cap 30", "k_cap 40"))
        self.refused(self.replaced(f"recipe {finding_record.FINDING_RECIPE}", "recipe reco.track.other/1"))

    def test_a_header_field_missing_doubled_or_unknown_is_refused(self):
        self.refused("\n".join(line for line in self.text.split("\n") if not line.startswith("block ")))
        self.refused(self.replaced("block 1\n", "block 1\nblock 1\n"))
        self.refused(self.replaced("block 1\n", "block 1\nseed 7\n"))

    def test_a_block_the_freeze_b_run_may_not_use_is_refused(self):
        for block in (6, 11, 12):
            with self.subTest(block=block):
                self.refused(self.replaced("block 1\n", f"block {block}\n"))

    def test_a_count_that_disagrees_with_its_bounds_is_refused(self):
        line = next(line for line in self.text.split("\n") if line.startswith("bin 2 "))
        tokens = line.split(" ")
        for field in ("fakes", "tracks", "events", "deff_hat", "u_a", "u_b", "u_dev", "l_dev", "r_dev", "design_effect", "objects_per_event"):
            with self.subTest(field=field):
                changed = list(tokens)
                position = changed.index(field) + 1
                changed[position] = str(int(changed[position]) + 1) if field in ("fakes", "tracks", "events") else repr(float(changed[position]) * (1 + 1e-9))
                self.refused(self.text.replace(line, " ".join(changed)))

    def test_deff_hat_other_than_1_at_k_0_is_refused(self):
        line = next(line for line in self.text.split("\n") if line.startswith("bin 0 "))
        self.refused(self.text.replace(line, line.replace(" deff_hat 1.0 ", " deff_hat 1.5 ")))

    def test_a_limit_or_its_check_that_is_not_section_8_3_s_is_refused(self):
        line = next(line for line in self.text.split("\n") if line.startswith("bin 0 "))
        self.refused(self.text.replace(line, line.replace(" limit 0.005 ", " limit 0.01 ")))
        self.refused(self.text.replace(line, line.replace(" within_limit yes ", " within_limit no ")))
        self.refused(self.replaced("beyond_limit 0", "beyond_limit 1"))

    def test_a_bin_doubled_missing_its_field_or_with_another_stratum_is_refused(self):
        line = next(line for line in self.text.split("\n") if line.startswith("bin 0 "))
        self.refused(self.text.replace(line, line + "\n" + line).replace("end bins 3", "end bins 4"))
        self.refused(self.text.replace(line, line.replace(" counts_sha256 " + "4" * 64, "")))
        self.refused(self.text.replace(line, line + " extra 1"))
        self.refused(self.text.replace(line, line.replace("bin 0 level 0", "bin 12 level 0")))
        self.refused(self.text.replace(line, line.replace("bin 0 level 0", "bin 0 level 1")))
        self.refused(self.text.replace(line, line.replace(" events 3000 ", " events 2999 ")))  # not events_per_bin
        self.refused(self.text.replace(line, line.replace("1" * 64, "x" * 64)))

    def test_events_without_tracks_beyond_the_events_is_refused(self):
        line = next(line for line in self.text.split("\n") if line.startswith("bin 0 "))
        self.assertIn(" events_without_tracks 0 ", line)
        self.refused(self.text.replace(line, line.replace(" events_without_tracks 0 ", " events_without_tracks 3001 ")))

    def test_a_non_finite_number_is_refused(self):
        line = next(line for line in self.text.split("\n") if line.startswith("bin 2 "))
        tokens = line.split(" ")
        tokens[tokens.index("u_dev") + 1] = "nan"
        self.refused(self.text.replace(line, " ".join(tokens)))

    def test_the_check_command_rejects_a_malformed_record(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "rate.record"
            path.write_text(self.text.replace("end bins 3", "end bins 2"), encoding="utf-8")
            self.assertEqual(fake_rate.main(["check", str(path)]), 2)
            path.write_text(self.text, encoding="utf-8")
            self.assertEqual(fake_rate.main(["check", str(path)]), 0)


class CountsFile(unittest.TestCase):
    def test_round_trip_and_refusals(self):
        rows = [(4, 6, 0), (0, 5, 1), (9, 0, 0)]
        text = fake_rate.format_counts(rows)
        self.assertEqual(fake_rate.parse_counts(text), rows)
        for bad in (text.replace("t07-noise-fake-rate-counts/1", "x"), text[:-1], text.replace("\nend 3\n", "\nend 4\n"), text.replace("0 5 1", "0 5 6"),
                    text.replace("4 6 0", "4 6 0 1"), text.replace("9 0 0", "4 0 0")):
            with self.subTest(bad=bad):
                with self.assertRaises(fake_rate.RateRecordError):
                    fake_rate.parse_counts(bad)


# ---- U-B11: deletion after a hash match only.

class DeletionAfterAHashMatch(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.path = Path(self.folder.name) / "noise.t07data"
        self.path.write_bytes(hand_made_data())
        self.digest = hashlib.sha256(self.path.read_bytes()).hexdigest()

    def test_the_streamed_hash_is_the_file_s(self):
        self.assertEqual(fake_rate.stream_sha256(self.path), self.digest)

    def test_deleted_when_every_expected_hash_matches(self):
        result = fake_rate.delete_after_hash_match(self.path, [self.digest, self.digest])
        self.assertEqual((result["deleted"], result["sha256"]), (True, self.digest))
        self.assertFalse(self.path.exists())

    def test_kept_when_one_expected_hash_differs(self):
        other = "0" * 64
        for expected in ([other], [self.digest, other], [other, self.digest]):
            with self.subTest(expected=expected):
                result = fake_rate.delete_after_hash_match(self.path, expected)
                self.assertFalse(result["deleted"])
                self.assertTrue(self.path.exists())
                self.assertIn("differs", result["reason"])

    def test_kept_when_the_file_changed_by_one_byte(self):
        raw = bytearray(self.path.read_bytes())
        raw[-1] ^= 1
        self.path.write_bytes(bytes(raw))
        self.assertFalse(fake_rate.delete_after_hash_match(self.path, [self.digest])["deleted"])
        self.assertTrue(self.path.exists())

    def test_no_expected_hash_or_a_malformed_one_is_refused_and_keeps_the_file(self):
        for expected in ([], ["abc"], [self.digest.upper()], [self.digest + "0"]):
            with self.subTest(expected=expected):
                with self.assertRaises(ValueError):
                    fake_rate.delete_after_hash_match(self.path, expected)
                self.assertTrue(self.path.exists())

    def test_a_truth_file_is_never_deleted(self):
        truth = Path(self.folder.name) / "noise.t07truth"
        truth.write_bytes(b"x")
        with self.assertRaises(ValueError):
            fake_rate.delete_after_hash_match(truth, [hashlib.sha256(b"x").hexdigest()])
        self.assertTrue(truth.exists())


# ---- The runner, with stand-in programs on hand-made files: the finder sees the data file alone, and deletion follows the checks.

STUB_GENERATOR = """#!{python}
import shutil, sys
arguments = dict(zip(sys.argv[2::2], sys.argv[3::2]))
shutil.copyfile({data!r}, arguments["--data-file"])
shutil.copyfile({truth!r}, arguments["--truth-file"])
with open({log!r}, "a") as log:
    log.write("generator " + " ".join(sys.argv[1:]) + "\\n")
"""
STUB_FINDER = """#!{python}
import hashlib, sys
arguments = dict(zip(sys.argv[1::2], sys.argv[2::2]))
with open({log!r}, "a") as log:
    log.write("finder " + " ".join(sys.argv[1:]) + "\\n")
digest = {wrong!r} or hashlib.sha256(open(arguments["--data-file"], "rb").read()).hexdigest()
text = open({record!r}).read().replace("DATA_SHA256", digest).replace("PRODUCT_ID", arguments["--product-id"])
open(arguments["--record-file"], "w").write(text)
open(arguments["--product-file"], "w").write("hand-made product\\n")
"""


class RunnerOnHandMadeFiles(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.work = Path(self.folder.name)
        self.source_data = self.work / "source.t07data"
        self.source_data.write_bytes(hand_made_data())
        digest = hashlib.sha256(self.source_data.read_bytes()).hexdigest()
        self.truth = self.work / "source.t07truth"
        self.truth.write_bytes(truth_file_bytes(HAND_PARTICLES, digest))
        self.record_template = self.work / "record.template"
        self.record_template.write_text(record_text(HAND_TRACKS, "DATA_SHA256", "PRODUCT_ID"), encoding="utf-8")
        self.log = self.work / "programs.log"

    def programs(self, wrong: str = "") -> tuple:
        generator, finder = self.work / "generator", self.work / "finder"
        generator.write_text(STUB_GENERATOR.format(python=sys.executable, data=str(self.source_data), truth=str(self.truth), log=str(self.log)), encoding="utf-8")
        finder.write_text(STUB_FINDER.format(python=sys.executable, log=str(self.log), wrong=wrong, record=str(self.record_template)), encoding="utf-8")
        for program in (generator, finder):
            program.chmod(program.stat().st_mode | stat.S_IXUSR)
        return generator, finder

    def run_runner(self, wrong: str = "", delete: bool = True, block: int = 1, events: int = 2, strata: str = "0") -> tuple:
        generator, finder = self.programs(wrong)
        out = self.work / f"run-{len(list(self.work.glob('run-*')))}"
        arguments = ["run", "--generator", str(generator), "--finder", str(finder), "--fixture", "noise", "--block", str(block), "--strata", strata,
                     "--events-per-bin", str(events), "--out", str(out), "--workers", "1"] + (["--delete-noise-data"] if delete else [])
        return fake_rate.main(arguments), out

    def test_the_finder_is_given_the_data_file_alone(self):
        code, out = self.run_runner()
        self.assertEqual(code, 1, (out / "run.log").read_text())  # 1 fake in 3 tracks: U_dev > C, so the run refuses (below)
        finder_lines = [line for line in self.log.read_text().splitlines() if line.startswith("finder ")]
        self.assertEqual(len(finder_lines), 1)
        self.assertNotIn(".t07truth", finder_lines[0])
        self.assertNotIn("truth", finder_lines[0].replace("--", " "))
        self.assertIn("--data-file", finder_lines[0])
        self.assertIn(f"--vertex-recipe {finding_record.VERTEX_RECIPE}", finder_lines[0])

    def test_the_record_scores_the_hand_made_bin(self):
        code, out = self.run_runner()
        self.assertEqual(code, 1)
        self.assertIn("evaluation does not start", (out / "run.log").read_text(encoding="utf-8"))
        parsed = fake_rate.parse_rate_record((out / "noise-b1.rate.record").read_text(encoding="utf-8"))
        only = parsed["bins"][0]
        self.assertEqual((only["stratum"], only["events"], only["tracks"], only["fakes"]), (0, 2, 3, 1))
        self.assertEqual(only["r_dev"], 1 / 3)
        counts = (out / "noise-b1-s0.counts").read_text(encoding="utf-8")
        self.assertEqual(fake_rate.parse_counts(counts), [(0, 2, 1), (1, 1, 0)])
        self.assertEqual(only["counts_sha256"], hashlib.sha256(counts.encode()).hexdigest())
        self.assertEqual(only["within_limit"], "no")  # 1 fake in 3 tracks: far above C

    def test_the_data_file_is_deleted_after_its_hash_matched(self):
        code, out = self.run_runner()
        self.assertFalse((out / "noise-b1-s0.t07data").exists())
        self.assertTrue((out / "noise-b1-s0.t07truth").exists())
        listing = (out / "noise-b1.listing").read_text(encoding="utf-8")
        self.assertIn(f"noise-b1-s0.t07data {hashlib.sha256(self.source_data.read_bytes()).hexdigest()} ", listing)
        self.assertIn(" deleted-after-hash-match", listing)

    def test_the_data_file_is_kept_when_the_record_names_another(self):
        code, out = self.run_runner(wrong="9" * 64)
        self.assertEqual(code, 1)
        self.assertTrue((out / "noise-b1-s0.t07data").exists())
        self.assertFalse((out / "noise-b1.rate.record").exists())
        self.assertIn("data_sha256", (out / "run.log").read_text(encoding="utf-8"))

    def test_the_data_file_is_kept_without_the_deletion_option(self):
        code, out = self.run_runner(delete=False)
        self.assertTrue((out / "noise-b1-s0.t07data").exists())
        self.assertIn(" kept", (out / "noise-b1.listing").read_text(encoding="utf-8"))

    def test_a_truth_file_of_another_bin_is_refused(self):
        self.truth.write_bytes(truth_file_bytes(HAND_PARTICLES, hashlib.sha256(self.source_data.read_bytes()).hexdigest(), stratum=3))
        code, out = self.run_runner()
        self.assertEqual(code, 1)
        self.assertTrue((out / "noise-b1-s0.t07data").exists())

    def test_the_block_and_the_event_count_are_arguments_and_reach_the_generator(self):
        code, out = self.run_runner(events=2)
        line = next(line for line in self.log.read_text().splitlines() if line.startswith("generator "))
        self.assertIn("--block 1 --stratum 0 --first-event 0 --count 2 ", line + " ")

    def test_a_block_outside_the_freeze_b_runs_is_rejected_before_any_program(self):
        for block in (6, 11, 12):
            with self.subTest(block=block):
                code, out = self.run_runner(block=block)
                self.assertEqual(code, 2)
                self.assertFalse(self.log.exists())

    def test_a_wrong_event_count_is_refused(self):
        code, out = self.run_runner(events=3)  # the hand-made truth holds 2 events
        self.assertEqual(code, 1)

    def test_a_block_2_run_reaches_the_generator_and_the_record(self):
        """Review M4: the block argument is not fixed at 1 anywhere in the runner."""
        self.truth.write_bytes(truth_file_bytes(HAND_PARTICLES, hashlib.sha256(self.source_data.read_bytes()).hexdigest(), block=2))
        code, out = self.run_runner(block=2)
        line = next(line for line in self.log.read_text().splitlines() if line.startswith("generator "))
        self.assertIn("--block 2 --stratum 0 ", line)
        parsed = fake_rate.parse_rate_record((out / "noise-b2.rate.record").read_text(encoding="utf-8"))
        self.assertEqual(parsed["header"]["block"], 2)
        self.assertTrue((out / "noise-b2-s0.t07truth").exists())

    def test_no_data_file_is_deleted_when_another_bin_fails(self):
        """Review M2: deletion is a second pass, after the rate record is written and read back; a failed bin leaves every data file."""
        code, out = self.run_runner(strata="0-1")  # the hand-made truth is of stratum 0, so stratum 1 is refused
        self.assertEqual(code, 1)
        self.assertTrue((out / "noise-b1-s0.t07data").exists())
        self.assertFalse((out / "noise-b1.rate.record").exists())
        listing = (out / "noise-b1.listing").read_text(encoding="utf-8")
        self.assertNotIn("deleted-after-hash-match", listing)
        self.assertIn("no data file deleted", (out / "run.log").read_text(encoding="utf-8"))

    def test_the_record_counts_events_without_a_track(self):
        """Review M5 (O2): every generated event is in N_ev, and the record says how many had no delivered track."""
        code, out = self.run_runner()
        only = fake_rate.parse_rate_record((out / "noise-b1.rate.record").read_text(encoding="utf-8"))["bins"][0]
        self.assertEqual(only["events_without_tracks"], 0)
        self.assertIn("events_without_tracks 0", (out / "run.log").read_text(encoding="utf-8"))


# ---- No truth reaches the recipe.

class NoTruthReachesTheRecipe(unittest.TestCase):
    def test_the_finder_command_holds_no_truth_and_refuses_a_truth_file(self):
        command = fake_rate.finder_command(Path("finder"), Path("a.t07data"), "one", Path("a.product"), Path("a.record"), 50)
        self.assertEqual(command[:3], ["finder", "--data-file", "a.t07data"])
        self.assertFalse(any("truth" in str(item) for item in command))
        with self.assertRaises(ValueError):
            fake_rate.finder_command(Path("finder"), Path("a.t07truth"), "one", Path("a.product"), Path("a.record"), 50)

    def test_no_recipe_source_names_the_scorer(self):
        sources = [ASSETS / "acts_tracking.py"] + sorted(NATIVE.glob("*.cpp")) + sorted(NATIVE.glob("*.hpp")) + sorted(NATIVE.glob("*.cmake")) + [NATIVE / "CMakeLists.txt"]
        for source in sources:
            with self.subTest(source=source.name):
                text = source.read_text(encoding="utf-8")
                self.assertNotIn("t07_fake_rate", text)
                self.assertNotIn("t07_negative_cases", text)

    def test_no_data_side_module_imports_the_scorer(self):
        from tests.adapters import test_acts_tracking as tracking_tests
        self.assertIn("t07_fake_rate", tracking_tests.GENERATOR_SIDE_PYTHON)
        self.assertTrue(tracking_tests.generator_side_imports("import t07_fake_rate\n"))
        for module in ASSETS.rglob("*.py"):
            if module.stem in tracking_tests.GENERATOR_SIDE_PYTHON:
                continue
            with self.subTest(module=module.name):
                imported = [alias.name for node in ast.walk(ast.parse(module.read_text(encoding="utf-8"))) if isinstance(node, (ast.Import, ast.ImportFrom))
                            for alias in (node.names if isinstance(node, ast.Import) else [ast.alias(node.module or "")])]
                self.assertNotIn("t07_fake_rate", imported)


# ---- The frozen coding of the same rule (read and run against, never edited or copied).

def hand_made_count_sets() -> list:
    """Count sets, fixed by hand: k = 0, 1, 3 and the cases above, equal and unequal objects per event, and the cap of 30."""
    sets = [([6] * 3000, [0] * 3000), ([1, 9], [0, 1]), ([36] * 3000, [1] + [0] * 2999), ([2, 2, 2, 2], [1, 1, 1, 0]), ([2, 2, 2, 2], [2, 1, 0, 0]),
            ([10] * 400, [1] * 40 + [0] * 360), ([12] * 12000, [0] * 12000), ([36] * 12000, [0] * 11997 + [1, 1, 1]), ([10] * 300, [1] * 30 + [0] * 270)]
    uneven = [1 + (7 * index) % 13 for index in range(500)]
    sets.append((uneven, [1 if index % 50 == 0 else 0 for index in range(500)]))
    sets.append((uneven, [min(3, m) if index % 9 == 0 else 0 for index, m in enumerate(uneven)]))
    return sets


@unittest.skipUnless(FROZEN_CODING and Path(FROZEN_CODING).is_file(), "HEP_T04_CALC_RATE_RULE names no frozen calc-rate-rule.py")
class FrozenCodingAgreement(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        raw = Path(FROZEN_CODING).read_bytes()
        cls.digest = hashlib.sha256(raw).hexdigest()
        cls.frozen = frozen_module()

    def test_the_frozen_file_is_section_18_s(self):
        self.assertEqual(self.digest, FROZEN_CODING_SHA256)
        self.assertEqual(self.frozen.K_CAP, fake_rate.K_CAP)

    def test_u_agrees_exactly_on_hand_made_counts(self):
        for index, (m, y) in enumerate(hand_made_count_sets()):
            with self.subTest(case=index):
                frozen = float(self.frozen.bound(numpy.asarray(m), numpy.asarray(y)))
                found = fake_rate.rate_rule(m, y)["u_dev"]
                print(f"AGREE-HAND case {index} k {sum(y)} n {sum(m)} events {len(m)} frozen {frozen!r} scorer {found!r} difference {found - frozen!r}", flush=True)
                self.assertEqual(found, frozen)


@unittest.skipUnless(FROZEN_CODING and RECORDED_RUN and Path(RECORDED_RUN).is_dir(), "needs HEP_T04_CALC_RATE_RULE and HEP_ACTS_TRACKING_FAKE_RATE_RUN (the build job)")
class RecordedRunAgreement(unittest.TestCase):
    """On a runner's block-1 output: every rate record reads, every bin's counts file is the one it names, the scorer's rule on those counts gives the
    record's numbers, and the frozen coding's U equals U_dev exactly."""

    @classmethod
    def setUpClass(cls):
        cls.frozen = frozen_module()
        cls.records = sorted(Path(RECORDED_RUN).glob("*.rate.record"))

    def test_every_bin_agrees_with_the_frozen_coding(self):
        self.assertTrue(self.records)
        bins = 0
        for record in self.records:
            parsed = fake_rate.parse_rate_record(record.read_text(encoding="utf-8"))
            self.assertEqual(parsed["header"]["block"], 1)
            for item in parsed["bins"]:
                with self.subTest(record=record.name, stratum=item["stratum"]):
                    counts_path = record.parent / f"{record.name[:-len('.rate.record')]}-s{item['stratum']}.counts"
                    text = counts_path.read_text(encoding="utf-8")
                    self.assertEqual(hashlib.sha256(text.encode()).hexdigest(), item["counts_sha256"])
                    rows = fake_rate.parse_counts(text)
                    m = numpy.array([row[1] for row in rows])
                    y = numpy.array([row[2] for row in rows])
                    again = fake_rate.rate_rule(m, y)
                    for name in ("events", "events_without_tracks", "tracks", "fakes", "deff_hat", "u_a", "u_b", "u_dev", "l_dev", "r_dev"):
                        self.assertEqual(again[name], item[name], name)
                    frozen = float(self.frozen.bound(m, y))
                    print(f"AGREE-BLOCK1 {record.name} stratum {item['stratum']} k {item['fakes']} n {item['tracks']} events {item['events']} "
                          f"frozen {frozen!r} scorer {item['u_dev']!r} difference {item['u_dev'] - frozen!r}", flush=True)
                    self.assertEqual(item["u_dev"], frozen)
                    bins += 1
        print(f"AGREE-BLOCK1 bins {bins}", flush=True)
        expected = os.environ.get("HEP_ACTS_TRACKING_FAKE_RATE_BINS", "")
        if expected:  # review N2: the job names how many bins each run holds
            self.assertEqual(bins, int(expected))


if __name__ == "__main__":
    unittest.main()
