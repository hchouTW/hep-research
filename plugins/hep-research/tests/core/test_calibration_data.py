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
from core.calibration import data, use  # noqa: E402

X = frozenset(f"x{i}" for i in range(10))
Y = frozenset(f"y{i}" for i in range(10))
Z = frozenset(f"z{i}" for i in range(10))


def k(name):
    return data.kappa_id(F.h(f"contract-{name}"), F.h(f"plan-{name}"), "0.1.0")


def rel(name):
    return F.h(f"release-{name}")


def ch(name):
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
        led = data.Ledger()
        led.open_validation(k("1"), rel("v-original"), X, Y, ch("1"))
        led.apply_decision({"kappa": k("1"), "outcome": "pass"})
        led.open_validation(k("2"), rel("v-rebinned-csv"), X, Z, ch("2"))
        self.assertEqual(led.c1_inputs(k("2"), "holdout", X, Z)["validation_data_reuse"], "validation")
        self.assertEqual(grade(led, k("2"), "holdout", X, Z), "calibrated-unvalidated")
        self.assertEqual(grade(led, k("1"), "holdout", X, Y), "validated-in-scope")     # recomputation, same kappa


class OpeningPreconditions_15_3_11(unittest.TestCase):
    def test_lineage_unconfirmed_not_opened(self):
        led = data.Ledger()
        r = {rel("v"): {}}
        with self.assertRaises(data.DataError) as cm:
            led.open_validation(k("1"), rel("v"), data.raw_units(rel("v"), r), X, ch("1"))
        self.assertEqual(cm.exception.code, "open.lineage_unconfirmed")
        self.assertEqual((led.state["events"], led.state["failure_records"]), ([], []))
        self.assertEqual(led.c1_inputs(k("1"), "holdout", Y, X, has_validation_read=False),
                         {"validation_data_reuse": "none", "earlier_failure_record": "none"})
        self.assertEqual(grade(led, k("1"), "holdout", Y, X, opened=False, incomplete=True), "incomplete")

    def test_k0_zero_no_read(self):
        led = data.Ledger()
        self.assertEqual(grade(led, k("1"), "holdout", Y, X, opened=False, testable_ok=False),
                         "calibrated-unvalidated")
        self.assertEqual(led.state["failure_records"], [])


class ReadsAndEligibility_15_3_13(unittest.TestCase):
    def test_version_2_after_version_1(self):
        for change in ("again", "plan", "engine"):
            with self.subTest(change):
                led = data.Ledger()
                led.open_validation(k("1"), rel("v"), Y, X, ch("1"))
                led.apply_decision({"kappa": k("1"), "outcome": "pass"})
                led.open_validation(k(f"2-{change}"), rel("v"), Y, X, ch("1"))
                self.assertEqual(grade(led, k(f"2-{change}"), "holdout", Y, X), "calibrated-unvalidated")
                self.assertEqual(grade(led, k("1"), "holdout", Y, X), "validated-in-scope")
        led = data.Ledger()                       # version 2 merges Y into its calibration data and cross-validates
        led.open_validation(k("1"), rel("v"), Y, X, ch("1"))
        led.apply_decision({"kappa": k("1"), "outcome": "pass"})
        led.open_validation(k("2"), rel("xy"), X | Y, X | Y, ch("2"))
        self.assertEqual(grade(led, k("2"), "cross-validation", X | Y, X | Y), "calibrated-unvalidated")

    def test_role_swap(self):
        def start():
            led = data.Ledger()
            led.fit_read(rel("x"), X, ch("1"), k("1"))                  # k1 calibrates with X
            led.open_validation(k("1"), rel("y"), Y, X, ch("1"))         # holds out Y
            led.apply_decision({"kappa": k("1"), "outcome": "fail"})
            led.fit_read(rel("y"), Y, ch("2"), k("2"))                  # k2 calibrates with Y
            return led
        led = start()
        led.open_validation(k("2"), rel("x"), X, Y, ch("2"))            # holds out X, fit-read by k1
        self.assertEqual(grade(led, k("2"), "holdout", X, Y), "calibrated-unvalidated")
        led = start()
        led.open_validation(k("2"), rel("z"), Z, Y, ch("2"))            # holds out Z, never read
        self.assertEqual(grade(led, k("2"), "holdout", Z, Y), "validated-in-scope")
        led = start()
        led.open_validation(k("2"), rel("x"), X, X, ch("2"))            # cross-validates on X alone
        self.assertEqual(led.c1_inputs(k("2"), "cross-validation", X, X)["earlier_failure_record"], "final")
        self.assertEqual(grade(led, k("2"), "cross-validation", X, X), "calibrated-unvalidated")   # 3f

    def test_exploration_read_before_lock(self):
        led = data.Ledger()
        chan = led.register_draft("series-a")
        self.assertEqual(chan, {"series": "series-a", "draft": 1})
        led.fit_read(rel("v"), Y, chan)                                  # A0 or exploration through a draft
        led.open_validation(k("1"), rel("v"), Y, X, ch("1"))
        self.assertEqual(grade(led, k("1"), "holdout", Y, X), "calibrated-unvalidated")       # fit -> 3d holdout
        with self.assertRaises(data.DataError):
            led.fit_read(rel("v"), Y, {"series": "series-a", "draft": 7})
        auto = led._channel({"series": "series-b"})                      # first provision registers the draft
        self.assertEqual(auto, {"series": "series-b", "draft": 1})

    def test_cross_validation_fit_reads_do_not_cap(self):
        led = data.Ledger()
        led.fit_read(rel("x"), X, ch("1"), k("1"))
        led.open_validation(k("1"), rel("x"), X, X, ch("1"))
        self.assertEqual(led.c1_inputs(k("1"), "cross-validation", X, X)["validation_data_reuse"], "fit")
        self.assertEqual(grade(led, k("1"), "cross-validation", X, X), "validated-in-scope")    # I22


class FailureRecords_15_3_14(unittest.TestCase):
    def test_state_transitions(self):
        for outcome, trig, want in (("abandoned", False, "final"), ("fail", False, "final"), ("pass", False, "withdrawn"),
                                    ("no-testable-direction", False, "withdrawn"),
                                    ("no-testable-direction", True, "final"), ("pass", True, "final")):
            with self.subTest((outcome, trig)):
                led = data.Ledger()
                led.open_validation(k("1"), rel("v"), Y, X, ch("1"))
                self.assertEqual({r["status"] for r in led.state["failure_records"]}, {"pending"})
                got = led.apply_decision({"kappa": k("1"), "outcome": outcome, "data_side_check_triggered": trig})
                self.assertEqual(got, want)
                self.assertEqual(len(led.state["failure_records"]), len(X))   # records change state, never vanish
                with self.assertRaises(data.DataError):                       # no second state change
                    led.apply_decision({"kappa": k("1"), "outcome": "abandoned"})

    def test_new_series_cross_validates_after_holdout_failure(self):
        led = data.Ledger()
        led.open_validation(k("1"), rel("v"), Y, X, ch("1"))
        led.apply_decision({"kappa": k("1"), "outcome": "fail"})
        led.open_validation(k("new-series"), rel("x"), X, X, ch("new"))
        self.assertEqual(grade(led, k("new-series"), "cross-validation", X, X), "calibrated-unvalidated")

    def test_interleaving(self):
        led = data.Ledger()
        s1 = led.open_validation(k("1"), rel("v"), Y, X, ch("1"))         # k1 opens the holdout: seq 1
        s2 = led.open_validation(k("2"), rel("x"), X, X, ch("2"))         # k2 first T_cv: seq 2
        self.assertEqual((s1, s2), (1, 2))
        self.assertEqual(grade(led, k("2"), "cross-validation", X, X), "incomplete")
        led.apply_decision({"kappa": k("1"), "outcome": "fail"})        # seq 3
        self.assertEqual({r["seq"] for r in led.state["failure_records"] if r["kappa"] == k("1")}, {1})
        self.assertEqual(grade(led, k("2"), "cross-validation", X, X), "calibrated-unvalidated")

    def test_reverse_order(self):
        led = data.Ledger()
        led.open_validation(k("2"), rel("x"), X, X, ch("2"))              # k2 first T_cv: seq 1
        led.open_validation(k("1"), rel("v"), Y, X, ch("1"))              # k1 opens: seq 2
        led.apply_decision({"kappa": k("1"), "outcome": "fail"})
        self.assertEqual(grade(led, k("2"), "cross-validation", X, X), "validated-in-scope")
        self.assertEqual([c["kappa"] for c in led.concurrent_configurations(k("2"), X)], [k("1")])

    def test_withdrawn_does_not_affect(self):
        led = data.Ledger()
        led.open_validation(k("1"), rel("v"), Y, X, ch("1"))
        led.apply_decision({"kappa": k("1"), "outcome": "pass"})
        led.open_validation(k("2"), rel("x"), X, X, ch("2"))
        self.assertEqual(grade(led, k("2"), "cross-validation", X, X), "validated-in-scope")

    def test_same_sequence_number_counts_as_earlier(self):
        led = data.Ledger()
        led.state["failure_records"].append({"unit": "x1", "kappa": k("1"), "seq": 5, "status": "final"})
        led.state["events"].append({"unit": "x1", "release_sha256": rel("x"), "channel": ch("2"), "kappa": k("2"),
                                    "kind": "validation", "seq": 5})
        self.assertEqual(led.failure_record_input(k("2"), X), "final")

    def test_pending_then_resolutions(self):
        def setup():
            led = data.Ledger()
            led.open_validation(k("1"), rel("v"), Y, X, ch("1"))
            led.open_validation(k("2"), rel("x"), X, X, ch("2"))
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
        led.open_validation(k("4"), rel("z"), Z, X, ch("4"))
        self.assertEqual(grade(led, k("4"), "holdout", Z, X), "validated-in-scope")

    def test_final_and_pending(self):
        led = data.Ledger()
        led.open_validation(k("1"), rel("v1"), Y, X, ch("1"))
        led.apply_decision({"kappa": k("1"), "outcome": "fail"})
        led.open_validation(k("3"), rel("v3"), Z, X, ch("3"))
        led.open_validation(k("2"), rel("x"), X, X, ch("2"))
        self.assertEqual(led.failure_record_input(k("2"), X), "final")
        self.assertEqual(grade(led, k("2"), "cross-validation", X, X), "calibrated-unvalidated")

    def test_later_record_does_not_affect(self):
        led = data.Ledger()
        led.open_validation(k("2"), rel("x"), X, X, ch("2"))
        led.apply_decision({"kappa": k("2"), "outcome": "pass"})
        led.open_validation(k("1"), rel("v"), Y, X, ch("1"))
        led.apply_decision({"kappa": k("1"), "outcome": "fail"})
        self.assertEqual(grade(led, k("2"), "cross-validation", X, X), "validated-in-scope")


class IngestionAndSealing_15_3_3(unittest.TestCase):
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


class Kappa(unittest.TestCase):
    def test_kappa_changes_with_each_part(self):
        base = data.kappa_id(F.h("c"), F.h("p"), "0.1.0")
        self.assertNotEqual(base, data.kappa_id(F.h("c2"), F.h("p"), "0.1.0"))
        self.assertNotEqual(base, data.kappa_id(F.h("c"), F.h("p2"), "0.1.0"))
        self.assertNotEqual(base, data.kappa_id(F.h("c"), F.h("p"), "0.1.1"))
        self.assertEqual(len(base), len(hashlib.sha256().hexdigest()))


if __name__ == "__main__":
    unittest.main()
