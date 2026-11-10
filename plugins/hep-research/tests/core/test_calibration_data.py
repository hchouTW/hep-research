"""core/calibration/data (simulator calibration phase 0): raw-unit lineage, read events, failure records and the reuse
and failure-record inputs of Appendix C.1, judged end to end with core/calibration/use.

Named cases of sections 15.3.11 (opening preconditions, lineage), 15.3.13 (validation reads and holdout eligibility),
15.3.14 (failure records; the state transitions use hand-written decision-record stubs, section 17: calib_validate.py
arrives in phase 2) and 15.3a (lineage and failure records on raw units); ingestion and sealing of section 15.3.3."""
from __future__ import annotations

import hashlib
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import calibration_fixtures as F  # noqa: E402
from core.calibration import data_release as data  # noqa: E402
from core.calibration import use  # noqa: E402

X = frozenset(f"x{i}" for i in range(10))
Y = frozenset(f"y{i}" for i in range(10))
Z = frozenset(f"z{i}" for i in range(10))


def k(name):
    return data.kappa_id(F.h(f"contract-{name}"), F.h(f"plan-{name}"), "0.1.0")


def rel(name):
    return F.h(f"release-{name}")


def channel_of(name):
    return {"contract_sha256": F.h(f"contract-{name}")}


def grade(led, kappa, vmode, val_units, cal_units, opened=True, **kw):
    c = dict(incomplete=False, mandatory_gate_failed=False, real_data=True, vmode=vmode, design_only=False,
             p7_failed=False, v_pass=True, power_ok=True, testable_ok=True, validation_data_simulated=False,
             own_flags=set())
    c.update(led.c1_inputs(kappa, vmode, val_units, cal_units, has_validation_read=opened))
    c.update(kw)
    return use.judge(c, [])["effective_grade"]


class Lineage(unittest.TestCase):
    def test_raw_units_and_derivation(self):
        r = {rel("p"): {"lineage": {"raw_units": sorted(X | Y)}},
             rel("sel"): {"lineage": {"derived_from": [rel("p")], "raw_units": sorted(X)}},
             rel("bad"): {"lineage": {"derived_from": [rel("p")], "raw_units": sorted(X | Z)}},
             rel("orphan"): {"lineage": {"derived_from": [rel("missing")], "raw_units": ["x1"]}},
             rel("none"): {}}
        self.assertEqual(data.raw_units(rel("sel"), r), X)
        for bad in ("bad", "orphan", "none"):
            self.assertIsNone(data.raw_units(rel(bad), r), bad)

    def test_15_3a_reformatting_does_not_reset_reads(self):
        """Raw validation data whose hash changes after a metadata change, reordering, rebinning or format
        conversion still cannot be upgraded by a new kappa."""
        r = {rel("v-original"): {"lineage": {"raw_units": sorted(X)}},
             rel("v-rebinned-csv"): {"lineage": {"derived_from": [rel("v-original")], "raw_units": sorted(X)},
                                     "representation_format": "csv, rebinned"},
             rel("y"): {"lineage": {"raw_units": sorted(Y)}}, rel("z"): {"lineage": {"raw_units": sorted(Z)}}}
        led = data.Ledger()
        u1 = data.opening_units("holdout", [rel("y")], [rel("v-original")], r)
        led.open_validation(k("1"), rel("v-original"), u1["validation_units"], u1["calibration_units"], channel_of("1"))
        led.apply_decision({"kappa": k("1"), "outcome": "pass"})
        u2 = data.opening_units("holdout", [rel("z")], [rel("v-rebinned-csv")], r)
        self.assertEqual(u2["validation_units"], X)                     # a new hash, the same raw units
        led.open_validation(k("2"), rel("v-rebinned-csv"), u2["validation_units"], u2["calibration_units"], channel_of("2"))
        self.assertEqual(led.c1_inputs(k("2"), "holdout", X, Z)["validation_data_reuse"], "validation")
        self.assertEqual(grade(led, k("2"), "holdout", X, Z), "calibrated-unvalidated")
        self.assertEqual(grade(led, k("1"), "holdout", X, Y), "validated-in-scope")     # recomputation, same kappa


GOOD = {c: True for c in data.OPENING_PRECONDITIONS}


class OpeningPreconditions(unittest.TestCase):
    def refused(self, **failing):
        led = data.Ledger()
        with self.assertRaises(data.DataError) as cm:
            led.open_validation(k("1"), rel("v"), Y, X, channel_of("1"), conditions=dict(GOOD, **failing))
        self.assertEqual(cm.exception.code, "open.precondition")
        self.assertEqual((led.state["events"], led.state["failure_records"], led.state["seq"]), ([], [], 0))
        self.assertEqual(led.c1_inputs(k("1"), "holdout", Y, X, has_validation_read=False),
                         {"validation_data_reuse": "none", "earlier_failure_record": "none"})
        return led

    def test_lineage_unconfirmed_not_opened(self):
        led = data.Ledger()
        units = data.opening_units("holdout", [rel("x")], [rel("v")], {rel("x"): {"lineage": {"raw_units": ["x1"]}},
                                                                         rel("v"): {}})
        self.assertIsNone(units["validation_units"])
        with self.assertRaises(data.DataError) as cm:
            led.open_validation(k("1"), rel("v"), units["validation_units"], units["calibration_units"], channel_of("1"))
        self.assertEqual(cm.exception.code, "open.lineage_unconfirmed")
        self.assertEqual((led.state["events"], led.state["failure_records"]), ([], []))
        # the result: V incomplete (lineage is part of V not yet decided), aggregated by calib_use
        agg = use.aggregate({g: "passed" for g in use.MANDATORY}, "passed", "incomplete", "holdout")
        self.assertEqual(agg["undecided"], ["v"])
        self.assertEqual(grade(led, k("1"), "holdout", Y, X, opened=False, **agg["inputs"]), "incomplete")

    def test_p7_incomplete_not_opened(self):
        self.refused(p7_not_incomplete=False)

    def test_toy_replicas_not_generated(self):
        self.refused(toy_replicas_ready=False)
        agg = use.aggregate({g: "passed" for g in use.MANDATORY}, "passed", "incomplete", "holdout")
        self.assertTrue(agg["inputs"]["incomplete"])                    # V incomplete, not opened

    def test_k0_zero_no_read(self):
        led = self.refused(k0_positive=False)
        agg = use.aggregate({g: "passed" for g in use.MANDATORY}, "no-testable-direction", "no-testable-direction",
                            "holdout")
        self.assertFalse(agg["inputs"]["incomplete"])                   # no-testable-direction, not incomplete
        self.assertEqual(grade(led, k("1"), "holdout", Y, X, opened=False, **agg["inputs"]), "calibrated-unvalidated")

    def test_pre_opening_ratio_test(self):
        self.refused(pre_opening_ratio_test_passed=False)
        led = data.Ledger()                                              # passes after the summed redo: opened
        self.assertEqual(led.open_validation(k("1"), rel("v"), Y, X, channel_of("1"), conditions=GOOD), 1)

    def test_holdout_sharing_rechecked_before_opening(self):
        r = {rel("x"): {"lineage": {"raw_units": sorted(X)}}, rel("v"): {"lineage": {"raw_units": sorted(X | Y)}}}
        with self.assertRaises(data.DataError) as cm:
            data.opening_units("holdout", [rel("x")], [rel("v")], r)
        self.assertEqual(cm.exception.code, "open.holdout_shares_units")
        cv = data.opening_units("cross-validation", [rel("x")], [], r)
        self.assertEqual((cv["validation_units"], cv["calibration_units"]), (X, X))

    def test_unknown_condition_refused(self):
        with self.assertRaises(data.DataError):
            data.unmet_preconditions({"looks_fine": True})


class ReadsAndEligibility(unittest.TestCase):
    def test_version_2_after_version_1(self):
        for change in ("again", "plan", "engine"):
            with self.subTest(change):
                led = data.Ledger()
                led.open_validation(k("1"), rel("v"), Y, X, channel_of("1"))
                led.apply_decision({"kappa": k("1"), "outcome": "pass"})
                led.open_validation(k(f"2-{change}"), rel("v"), Y, X, channel_of("1"))
                self.assertEqual(grade(led, k(f"2-{change}"), "holdout", Y, X), "calibrated-unvalidated")
                self.assertEqual(grade(led, k("1"), "holdout", Y, X), "validated-in-scope")
        led = data.Ledger()                       # version 2 merges Y into its calibration data and cross-validates
        led.open_validation(k("1"), rel("v"), Y, X, channel_of("1"))
        led.apply_decision({"kappa": k("1"), "outcome": "pass"})
        led.open_validation(k("2"), rel("xy"), X | Y, X | Y, channel_of("2"))
        self.assertEqual(grade(led, k("2"), "cross-validation", X | Y, X | Y), "calibrated-unvalidated")

    def test_role_swap(self):
        def start():
            led = data.Ledger()
            led.fit_read(rel("x"), X, channel_of("1"), k("1"))                  # k1 calibrates with X
            led.open_validation(k("1"), rel("y"), Y, X, channel_of("1"))         # holds out Y
            led.apply_decision({"kappa": k("1"), "outcome": "fail"})
            led.fit_read(rel("y"), Y, channel_of("2"), k("2"))                  # k2 calibrates with Y
            return led
        led = start()
        led.open_validation(k("2"), rel("x"), X, Y, channel_of("2"))            # holds out X, fit-read by k1
        self.assertEqual(grade(led, k("2"), "holdout", X, Y), "calibrated-unvalidated")
        led = start()
        led.open_validation(k("2"), rel("z"), Z, Y, channel_of("2"))            # holds out Z, never read
        self.assertEqual(grade(led, k("2"), "holdout", Z, Y), "validated-in-scope")
        led = start()
        led.open_validation(k("2"), rel("x"), X, X, channel_of("2"))            # cross-validates on X alone
        self.assertEqual(led.c1_inputs(k("2"), "cross-validation", X, X)["earlier_failure_record"], "final")
        self.assertEqual(grade(led, k("2"), "cross-validation", X, X), "calibrated-unvalidated")   # 3f

    def test_exploration_read_before_lock(self):
        led = data.Ledger()
        chan = led.register_draft("series-a")
        self.assertEqual(chan, {"series": "series-a", "draft": 1})
        led.fit_read(rel("v"), Y, chan)                                  # A0 or exploration through a draft
        led.open_validation(k("1"), rel("v"), Y, X, channel_of("1"))
        self.assertEqual(grade(led, k("1"), "holdout", Y, X), "calibrated-unvalidated")       # fit -> 3d holdout
        with self.assertRaises(data.DataError):
            led.fit_read(rel("v"), Y, {"series": "series-a", "draft": 7})
        auto = led._channel({"series": "series-b"})                      # first provision registers the draft
        self.assertEqual(auto, {"series": "series-b", "draft": 1})

    def test_cross_validation_fit_reads_do_not_cap(self):
        led = data.Ledger()
        led.fit_read(rel("x"), X, channel_of("1"), k("1"))
        led.open_validation(k("1"), rel("x"), X, X, channel_of("1"))
        self.assertEqual(led.c1_inputs(k("1"), "cross-validation", X, X)["validation_data_reuse"], "fit")
        self.assertEqual(grade(led, k("1"), "cross-validation", X, X), "validated-in-scope")    # I22


class FailureRecords(unittest.TestCase):
    def test_state_transitions(self):
        for outcome, trig, want in (("abandoned", False, "final"), ("fail", False, "final"), ("pass", False, "withdrawn"),
                                    ("no-testable-direction", False, "withdrawn"),
                                    ("no-testable-direction", True, "final"), ("pass", True, "final")):
            with self.subTest((outcome, trig)):
                led = data.Ledger()
                led.open_validation(k("1"), rel("v"), Y, X, channel_of("1"))
                self.assertEqual({r["status"] for r in led.state["failure_records"]}, {"pending"})
                got = led.apply_decision({"kappa": k("1"), "outcome": outcome, "data_side_check_triggered": trig})
                self.assertEqual(got, want)
                self.assertEqual(len(led.state["failure_records"]), len(X))   # records change state, never vanish
                with self.assertRaises(data.DataError):                       # no second state change
                    led.apply_decision({"kappa": k("1"), "outcome": "abandoned"})

    def test_new_series_cross_validates_after_holdout_failure(self):
        led = data.Ledger()
        led.open_validation(k("1"), rel("v"), Y, X, channel_of("1"))
        led.apply_decision({"kappa": k("1"), "outcome": "fail"})
        led.open_validation(k("new-series"), rel("x"), X, X, channel_of("new"))
        self.assertEqual(grade(led, k("new-series"), "cross-validation", X, X), "calibrated-unvalidated")

    def test_interleaving(self):
        led = data.Ledger()
        s1 = led.open_validation(k("1"), rel("v"), Y, X, channel_of("1"))         # k1 opens the holdout: seq 1
        s2 = led.open_validation(k("2"), rel("x"), X, X, channel_of("2"))         # k2 first T_cv: seq 2
        self.assertEqual((s1, s2), (1, 2))
        self.assertEqual(grade(led, k("2"), "cross-validation", X, X), "incomplete")
        led.apply_decision({"kappa": k("1"), "outcome": "fail"})        # seq 3
        self.assertEqual({r["seq"] for r in led.state["failure_records"] if r["kappa"] == k("1")}, {1})
        self.assertEqual(grade(led, k("2"), "cross-validation", X, X), "calibrated-unvalidated")

    def test_reverse_order(self):
        led = data.Ledger()
        led.open_validation(k("2"), rel("x"), X, X, channel_of("2"))              # k2 first T_cv: seq 1
        led.open_validation(k("1"), rel("v"), Y, X, channel_of("1"))              # k1 opens: seq 2
        led.apply_decision({"kappa": k("1"), "outcome": "fail"})
        self.assertEqual(grade(led, k("2"), "cross-validation", X, X), "validated-in-scope")
        self.assertEqual([c["kappa"] for c in led.concurrent_configurations(k("2"), X)], [k("1")])

    def test_withdrawn_does_not_affect(self):
        led = data.Ledger()
        led.open_validation(k("1"), rel("v"), Y, X, channel_of("1"))
        led.apply_decision({"kappa": k("1"), "outcome": "pass"})
        led.open_validation(k("2"), rel("x"), X, X, channel_of("2"))
        self.assertEqual(grade(led, k("2"), "cross-validation", X, X), "validated-in-scope")

    def test_same_sequence_number_counts_as_earlier(self):
        led = data.Ledger()
        led.state["failure_records"].append({"unit": "x1", "kappa": k("1"), "seq": 5, "status": "final"})
        led.state["events"].append({"unit": "x1", "release_sha256": rel("x"), "channel": channel_of("2"), "kappa": k("2"),
                                    "kind": "validation", "seq": 5})
        self.assertEqual(led.failure_record_input(k("2"), X), "final")

    def test_pending_then_resolutions(self):
        def setup():
            led = data.Ledger()
            led.open_validation(k("1"), rel("v"), Y, X, channel_of("1"))
            led.open_validation(k("2"), rel("x"), X, X, channel_of("2"))
            return led
        led = setup()
        self.assertEqual(grade(led, k("2"), "cross-validation", X, X), "incomplete")
        self.assertEqual(len(led.waiting_records(k("2"), X)), len(X))
        led.apply_decision({"kappa": k("1"), "outcome": "abandoned"})
        self.assertEqual(grade(led, k("2"), "cross-validation", X, X), "calibrated-unvalidated")
        led = setup()
        led.apply_decision({"kappa": k("1"), "outcome": "pass"})
        self.assertEqual(grade(led, k("2"), "cross-validation", X, X), "validated-in-scope")
        led = setup()                                                    # k2's own V fails: directly capped
        self.assertEqual(grade(led, k("2"), "cross-validation", X, X, v_pass=False), "calibrated-unvalidated")
        led = setup()                                                    # a design study in mode none: projection
        self.assertEqual(grade(led, k("3"), "none", X, X, opened=False, design_only=True), "projection")
        led = setup()                                                    # holdout on new units: not affected
        led.open_validation(k("4"), rel("z"), Z, X, channel_of("4"))
        self.assertEqual(grade(led, k("4"), "holdout", Z, X), "validated-in-scope")

    def test_regeneration_fails_without_trigger(self):
        """After opening, the data-side check does not trigger and regenerating the toys fails: incomplete, record
        pending (no decision record is written)."""
        led = data.Ledger()
        led.open_validation(k("1"), rel("v"), Y, X, channel_of("1"))
        agg = use.aggregate({g: "passed" for g in use.MANDATORY}, "passed", "incomplete", "holdout")
        self.assertEqual(grade(led, k("1"), "holdout", Y, X, **agg["inputs"]), "incomplete")
        self.assertEqual({r["status"] for r in led.state["failure_records"]}, {"pending"})

    def test_capped_by_upstream_or_flag_with_pending(self):
        """Another kappa pending; a central upstream at calibrated-unvalidated as phi center, or own
        outside-validated-range: directly calibrated-unvalidated (not incomplete)."""
        led = data.Ledger()
        led.open_validation(k("1"), rel("v"), Y, X, channel_of("1"))
        led.open_validation(k("2"), rel("x"), X, X, channel_of("2"))
        c = dict(incomplete=False, mandatory_gate_failed=False, real_data=True, vmode="cross-validation",
                 design_only=False, p7_failed=False, v_pass=True, power_ok=True, testable_ok=True,
                 validation_data_simulated=False, own_flags=set(), **led.c1_inputs(k("2"), "cross-validation", X, X))
        self.assertEqual(c["earlier_failure_record"], "pending")
        up = dict(usages={"phi-center"}, effective_grade="calibrated-unvalidated", flags=set())
        j = use.judge(c, [up])
        self.assertEqual(j["effective_grade"], "calibrated-unvalidated")
        self.assertEqual(j["uses"], sorted(use.allowed_uses("calibrated-unvalidated", set())))
        self.assertEqual(use.judge(dict(c, own_flags={"outside-validated-range"}), [])["effective_grade"],
                         "calibrated-unvalidated")

    def test_recomputation_same_kappa_not_restricted(self):
        led = data.Ledger()
        s1 = led.open_validation(k("1"), rel("v"), Y, X, channel_of("1"))
        led.apply_decision({"kappa": k("1"), "outcome": "pass"})
        s2 = led.open_validation(k("1"), rel("v"), Y, X, channel_of("1"))       # recomputation (review F9)
        self.assertGreater(s2, s1)
        self.assertEqual(led.opening_seq(k("1")), s1)
        self.assertEqual(len(led.state["failure_records"]), len(X))    # no new records
        self.assertEqual(grade(led, k("1"), "holdout", Y, X), "validated-in-scope")

    def test_final_and_pending(self):
        led = data.Ledger()
        led.open_validation(k("1"), rel("v1"), Y, X, channel_of("1"))
        led.apply_decision({"kappa": k("1"), "outcome": "fail"})
        led.open_validation(k("3"), rel("v3"), Z, X, channel_of("3"))
        led.open_validation(k("2"), rel("x"), X, X, channel_of("2"))
        self.assertEqual(led.failure_record_input(k("2"), X), "final")
        self.assertEqual(grade(led, k("2"), "cross-validation", X, X), "calibrated-unvalidated")

    def test_later_record_does_not_affect(self):
        led = data.Ledger()
        led.open_validation(k("2"), rel("x"), X, X, channel_of("2"))
        led.apply_decision({"kappa": k("2"), "outcome": "pass"})
        led.open_validation(k("1"), rel("v"), Y, X, channel_of("1"))
        led.apply_decision({"kappa": k("1"), "outcome": "fail"})
        self.assertEqual(grade(led, k("2"), "cross-validation", X, X), "validated-in-scope")


class IngestionAndSealing(unittest.TestCase):
    def test_ingestion_requires_declarations(self):
        r = F.releases()[F.CAL]
        self.assertEqual(data.ingestion_findings(r), [])
        del r["declarations"]["uncertainty_sources"]
        self.assertIn("ingestion.missing_uncertainty_sources", {f["code"] for f in data.ingestion_findings(r)})

    def test_sealed_components(self):
        r = {"content": {"systematic": [0.1], "observed": [0.2], "expected": [0.2], "values": [1.0]}}
        self.assertEqual(data.provide(r, "systematic", opened=False, role="validation"), [0.1])
        for comp in ("observed", "expected"):
            with self.assertRaises(data.DataError):
                data.provide(r, comp, opened=True, role="calibration")
        with self.assertRaises(data.DataError):
            data.provide(r, "values", opened=False, role="validation")
        self.assertEqual(data.provide(r, "values", opened=False, role="calibration"), [1.0])


class ReleaseHash(unittest.TestCase):
    def test_declared_hash_verified(self):
        r = F.releases()[F.CAL]
        h = data.release_hash(r)
        self.assertEqual(data.release_hash(dict(r, release_sha256=h)), h)
        with self.assertRaises(data.DataError) as cm:
            data.release_hash(dict(r, release_sha256=F.h("not-this-one")))
        self.assertEqual(cm.exception.code, "release.hash_mismatch")


class Kappa(unittest.TestCase):
    def test_kappa_changes_with_each_part(self):
        base = data.kappa_id(F.h("c"), F.h("p"), "0.1.0")
        self.assertNotEqual(base, data.kappa_id(F.h("c2"), F.h("p"), "0.1.0"))
        self.assertNotEqual(base, data.kappa_id(F.h("c"), F.h("p2"), "0.1.0"))
        self.assertNotEqual(base, data.kappa_id(F.h("c"), F.h("p"), "0.1.1"))
        self.assertEqual(len(base), len(hashlib.sha256().hexdigest()))


if __name__ == "__main__":
    unittest.main()
