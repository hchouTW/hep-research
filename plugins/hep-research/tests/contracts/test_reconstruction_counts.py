"""Witness W6 of the reconstruction contracts (plan Section 12, contract-map.md): counts, thresholds and exposure, and
the contract parts of A19 (count or threshold only), A23 (prompt-delayed) and A24 (counting and energy-resolving photon
sensors). contracts/schemas/exposure_record.json records who saw which released data, so it is a different thing and is
not reused for live exposure. Passing proves the stated contract behaviour only. Synthetic documents only."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from contracts.reconstruction import observed_intervals, read_sidecar  # noqa: E402
from contracts.schema import validate  # noqa: E402
from tests.contracts.reconstruction_fixtures import code_list, coincidence_witness, count_product, count_witness, seconds  # noqa: E402


class Presence(unittest.TestCase):
    def setUp(self):
        self.counts = count_witness()

    def refused(self):
        return code_list(read_sidecar(count_product(self.counts)))

    def test_witness_is_read(self):
        self.assertEqual(self.refused(), [])

    def test_zero_stays_an_observation_and_absent_does_not(self):
        observed = {item["interval_id"]: item["count"] for item in observed_intervals(count_product(self.counts))}
        self.assertEqual(observed, {"interval-1": 0, "interval-3": 3})

    def test_absent_filled_with_zero_is_caught(self):
        self.counts["intervals"][1]["count"] = 0
        self.assertIn("reconstruction.counts.absent_filled", self.refused())

    def test_present_without_a_count_is_caught(self):
        del self.counts["intervals"][0]["count"]
        self.assertIn("reconstruction.counts.count_missing", self.refused())

    def test_interval_of_an_unknown_channel_is_caught(self):
        self.counts["intervals"][0]["channel"] = "channel-z"
        self.assertIn("reconstruction.counts.unknown_channel", self.refused())


class Denominators(unittest.TestCase):
    def setUp(self):
        self.counts = count_witness()

    def refused(self):
        return code_list(read_sidecar(count_product(self.counts)))

    def test_run_time_for_both_channels_is_caught(self):
        for rate in self.counts["rates"]:
            rate["denominator"] = {"source": "run-time", "value": 100, "unit": "s"}
        self.assertIn("reconstruction.counts.run_time_denominator", self.refused())

    def test_another_channels_exposure_is_caught(self):
        self.counts["rates"][1]["denominator"]["value"] = 80
        self.assertIn("reconstruction.counts.exposure_mismatch", self.refused())

    def test_another_channels_response_is_caught(self):
        self.counts["rates"][1]["response_ref"] = "native:response-a"
        self.assertIn("reconstruction.counts.response_mismatch", self.refused())

    def test_negative_exposure_is_caught(self):
        self.counts["channels"][0]["valid_exposure"] = seconds(-1)
        self.assertIn("reconstruction.counts.negative_exposure", self.refused())

    def test_one_exposure_in_two_units_agrees(self):
        """Re-review 2 minor 10, K05."""
        self.counts["rates"][0]["denominator"].update({"value": 80000, "unit": "ms"})
        self.assertEqual(self.refused(), [])

    def test_exposure_above_the_run_is_caught_across_units(self):
        """Re-review 2 minor 10."""
        self.counts["channels"][0]["valid_exposure"] = {"value": 200000, "unit": "ms"}
        self.counts["rates"][0]["denominator"].update({"value": 200000, "unit": "ms"})
        self.assertEqual(self.refused(), ["reconstruction.counts.exposure_above_run_time"])

    def test_exposure_cannot_exceed_the_run(self):
        self.counts["channels"][0]["valid_exposure"] = seconds(120)
        self.assertIn("reconstruction.counts.exposure_above_run_time", self.refused())

    def test_exposure_record_is_a_different_thing(self):
        self.assertFalse(validate(self.counts["channels"][0], "exposure_record.json").ok)


class CountModel(unittest.TestCase):
    def setUp(self):
        self.counts = count_witness()

    def refused(self):
        return code_list(read_sidecar(count_product(self.counts)))

    def test_poisson_from_an_integer_type_is_caught(self):
        self.counts["count_model"] = {"kind": "poisson", "premises": [], "inferred_from": "integer-type"}
        self.assertIn("reconstruction.counts.poisson_from_integer", self.refused())

    def test_poisson_with_premises_is_accepted(self):
        self.counts["count_model"] = {"kind": "poisson", "premises": ["sampling stated", "dead time stated"], "inferred_from": None}
        self.assertEqual(self.refused(), [])

    def test_any_model_needs_its_premises(self):
        self.counts["count_model"]["premises"] = []
        self.assertIn("reconstruction.counts.model_without_premises", self.refused())


class Selection(unittest.TestCase):
    """M5: zero, absent, exposure and selection are distinguishable; a rate is formed with its channel's selection."""

    def setUp(self):
        self.counts = count_witness()

    def refused(self):
        return code_list(read_sidecar(count_product(self.counts)))

    def test_channel_states_its_selection(self):
        del self.counts["channels"][0]["selection_ref"]
        self.assertTrue(self.refused())

    def test_unknown_selection_is_caught(self):
        self.counts["channels"][0]["selection_ref"] = "selection.unknown"
        self.assertIn("reconstruction.counts.unknown_selection", self.refused())

    def test_rate_of_another_selection_is_caught(self):
        self.counts["rates"][0]["selection_ref"] = "selection.threshold-high"
        self.assertIn("reconstruction.counts.selection_mismatch", self.refused())

    def test_threshold_states_its_value(self):
        self.counts["selections"][0]["threshold"] = None
        self.assertIn("reconstruction.counts.threshold_missing", self.refused())

    def test_selection_content_matches_its_kind(self):
        """Re-review minor 7; W6: selection is distinguishable, so a record says what it selected. A threshold beside a window is allowed."""
        window = {"start": 0, "end": 1, "unit": "us"}
        cases = ({"kind": "none"}, {"kind": "window"}, {"kind": "native-rule"})
        for change in cases:
            self.counts = count_witness()
            self.counts["selections"][0].update(change)
            self.assertEqual(self.refused(), ["reconstruction.counts.selection_incomplete"], change)
        for change in ({"kind": "window", "window": window}, {"kind": "native-rule", "reference": "native:selection"}):
            self.counts = count_witness()
            self.counts["selections"][0].update(change)
            self.assertEqual(self.refused(), [], change)

    def test_no_selection_is_a_statement(self):
        self.counts["selections"][0] = {"selection_id": "selection.threshold-low", "kind": "none", "threshold": None}
        self.assertEqual(self.refused(), [])


class Capabilities(unittest.TestCase):
    """A19, A24: a counting sensor delivers counts and rates and never a per-event energy."""

    def setUp(self):
        self.counts = count_witness()

    def refused(self):
        return code_list(read_sidecar(count_product(self.counts)))

    def test_energy_without_an_energy_observable_is_caught(self):
        self.counts["per_event_energy"] = True
        self.assertIn("reconstruction.counts.energy_without_observable", self.refused())

    def test_energy_resolving_sensor_has_an_energy_observable(self):
        self.counts.update({"capability": "energy-resolving", "observables": ["count", "energy-deposited"], "per_event_energy": True})
        self.assertEqual(self.refused(), [])

    def test_energy_loss_is_not_an_energy_observable(self):
        """Minor 8: K05 names the energy kinds, and energy loss is not one of them."""
        self.counts.update({"capability": "energy-resolving", "observables": ["energy-loss"], "per_event_energy": True})
        self.assertEqual(self.refused(), ["reconstruction.counts.energy_without_observable"])

    def test_a_counting_sensor_delivers_no_per_event_energy(self):
        """A24: capabilities and outputs stay distinct."""
        self.counts.update({"observables": ["count", "energy-deposited"], "per_event_energy": True})
        self.assertEqual(self.refused(), ["reconstruction.counts.capability_mismatch"])

    def test_capability_is_not_a_list_of_energy_kinds(self):
        """Re-review 2 minor 9: an uncalibrated pulse-height sensor, and a counting sensor with an energy observable it does not deliver."""
        self.counts.update({"capability": "energy-resolving", "observables": ["adc-value"]})
        self.assertEqual(self.refused(), [])
        self.counts = count_witness()
        self.counts["observables"] = ["count", "energy-deposited"]
        self.assertEqual(self.refused(), [])


class PromptDelayed(unittest.TestCase):
    """A23, contract part; the method and its quality are T11 and T10."""

    def test_full_record_is_read(self):
        counts = count_witness()
        counts["coincidence"] = coincidence_witness()
        self.assertEqual(code_list(read_sidecar(count_product(counts))), [])

    def test_windows_are_retained_not_judged(self):
        """Re-review 2 minor 11: A23 says retain the windows; no order or unit list is stated."""
        counts = count_witness()
        counts["coincidence"] = coincidence_witness()
        counts["coincidence"]["delayed_window"] = {"start": 0, "end": 5, "unit": "ps"}
        self.assertEqual(code_list(read_sidecar(count_product(counts))), [])

    def test_each_retained_item_is_required(self):
        for field in ("prompt_window", "delayed_window", "accidentals", "capture_escape", "denominators"):
            counts = count_witness()
            counts["coincidence"] = coincidence_witness()
            del counts["coincidence"][field]
            self.assertTrue(code_list(read_sidecar(count_product(counts))), field)


class ExposureUnits(unittest.TestCase):
    """Re-review 3 minor 5, W6 and K05: minutes and hours convert, and a unit the reader cannot convert leaves the exposure
    check undone, which is reported."""

    def setUp(self):
        self.counts = count_witness()

    def refused(self):
        return code_list(read_sidecar(count_product(self.counts)))

    def test_minutes_above_the_run_are_caught(self):
        self.counts["channels"][0]["valid_exposure"] = {"value": 200, "unit": "min"}
        self.counts["rates"][0]["denominator"].update({"value": 200, "unit": "min"})
        self.assertEqual(self.refused(), ["reconstruction.counts.exposure_above_run_time"])

    def test_one_minute_is_sixty_seconds_and_an_hour_is_a_run(self):
        self.counts["channels"][0]["valid_exposure"] = {"value": 1, "unit": "min"}
        self.counts["rates"][0]["denominator"].update({"value": 60, "unit": "s"})
        self.assertEqual(self.refused(), [])
        self.counts["run_time"] = {"value": 1, "unit": "h"}
        self.counts["channels"][1]["valid_exposure"] = {"value": 3600, "unit": "s"}
        self.counts["rates"][1]["denominator"].update({"value": 3600, "unit": "s"})
        self.assertEqual(self.refused(), [])

    def test_an_unknown_unit_is_reported_as_not_compared(self):
        self.counts["channels"][0]["valid_exposure"] = {"value": 2, "unit": "fortnight"}
        self.counts["rates"][0]["denominator"].update({"value": 2, "unit": "fortnight"})
        report = read_sidecar(count_product(self.counts))
        self.assertEqual(code_list(report), [])
        self.assertEqual([finding.code for finding in report.findings], ["reconstruction.counts.exposure_not_compared"])

    def test_a_fully_live_channel_in_another_unit_is_not_above_the_run(self):
        """Re-review 4 minor 2, K05: 0.555 h is 1998 s and 2e12 ns is 2000 s, so neither exceeds its run."""
        for run, exposure in ((1998, {"value": 0.555, "unit": "h"}), (2000, {"value": 2e12, "unit": "ns"})):
            counts = count_witness()
            counts["run_time"] = {"value": run, "unit": "s"}
            counts["channels"][0]["valid_exposure"] = exposure
            counts["rates"][0]["denominator"].update(exposure)
            self.assertEqual(code_list(read_sidecar(count_product(counts))), [], exposure)

    def test_a_day_and_the_greek_microsecond_convert(self):
        """Re-review 4 minor 4: `d`, and U+03BC beside U+00B5."""
        self.counts["run_time"] = {"value": 2, "unit": "d"}
        self.counts["channels"][0]["valid_exposure"] = {"value": 1, "unit": "d"}
        self.counts["rates"][0]["denominator"].update({"value": 86400, "unit": "s"})
        self.counts["channels"][1]["valid_exposure"] = {"value": 50, "unit": "μs"}
        self.counts["rates"][1]["denominator"].update({"value": 50, "unit": "us"})
        self.assertEqual([finding.code for finding in read_sidecar(count_product(self.counts)).findings], [])


if __name__ == "__main__":
    unittest.main()
