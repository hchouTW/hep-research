"""core/calibration/use (simulator calibration phase 0): the evidence-grade decision table of Part B Appendix C.

1. calib_use agrees with the reference implementation calib_use_decision_table.py (the version attached to v7.37.4,
   SHA-256 c5279adf...) input by input over Appendix C's exhaustive scope: assign, effective, allowed_uses,
   variation_upstream_admissible.
2. It passes the same set of tests: the reference's exhaustive invariant check, run with calib_use's functions in place
   of the reference's, finds no violation; the reference's own mutant check catches every mutant.
3. The "outcome already determined" lookup (section 10.2 rule 0, D63, D13), which the reference does not contain, is
   compared over the same scope with an independently written enumeration (C.2 then C.3), and the mutant that looks up
   C.2 only (Appendix C mutant 25) is caught.
4. The named cases of sections 15.3.12, 15.3.15 and the use part of 15.3.17.
"""
from __future__ import annotations

import contextlib
import hashlib
import importlib.util
import io
import itertools
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from core.calibration import deps, use  # noqa: E402

REFERENCE = ROOT / "docs" / "dev" / "simulator-calibration" / "reference" / "calib_use_decision_table.py"
REFERENCE_SHA256 = "c5279adf41acfcfb21e8aa67295756d1a551361e6a9aa5fa68d98bb4f17a3de3"


def load_reference():
    reference_bytes = REFERENCE.read_bytes()
    got = hashlib.sha256(reference_bytes).hexdigest()
    if got != REFERENCE_SHA256:
        raise AssertionError(f"reference decision table has SHA-256 {got}, not the v7.37.4 version")
    spec = importlib.util.spec_from_file_location("calib_use_decision_table_ref", REFERENCE)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


REF = load_reference()


def outcome(fn, *args):
    try:
        return ("ok", fn(*args))
    except ValueError:
        return ("rejected", None)


# The unit suite runs a fixed strided slice of Appendix C's scope (31.6 million cases); the full scope, sharded, is
# the phase-0 gate run of tests/core/calibration_exhaustive.py (simcal-tasks/phase-0.md).
SLICE = 2000          # every 2000th case of the reference's cases() order, from the first
LOOKUP_SLICE = 23    # coprime to the 4 upstream variants and 7 undecided subsets the scope cycles through


class AgreesWithReference(unittest.TestCase):
    def test_input_by_input_slice(self):
        import calibration_exhaustive as ex
        detail, ok = ex.run_agree(REF, use, deps, 1, SLICE)
        self.assertTrue(ok, detail["disagreements"])
        self.assertGreater(detail["cases"], 15000)
        for g in use.GRADES + ("incomplete",):
            for fs in REF.FLAG_SETS:
                self.assertEqual(use.allowed_uses(g, fs), REF.allowed_uses(g, fs))

    def test_reference_invariants_hold_for_calib_use_slice(self):
        import calibration_exhaustive as ex
        detail, ok = ex.run_invariants(REF, use, deps, 1, SLICE)
        self.assertTrue(ok, detail["violations"])

    def test_reference_mutants_slice(self):
        """Each mutant must be caught by the full scope (gate run); on the slice, the mutants known to be caught there
        must be, so a weakened invariant shows up in the unit suite too."""
        import calibration_exhaustive as ex
        detail, ok = ex.run_mutants(REF, use, deps, 1, SLICE)
        self.assertEqual(len(detail["mutants"]), ex.REFERENCE_MUTANTS)
        self.assertTrue(ok, detail["not_caught"])


# ------------------------------------------------------------------ outcome already determined (independent)
def independent_lookup(c, ups, undecided, c2_only=False):
    """Written apart from use.outcome_determined: enumerate outcomes, grade with C.2, cap by central upstreams and
    grade-limiting flags, match uses (C.3), resolving pending inputs both ways."""
    choices = []
    if "mandatory-gate" in undecided:
        choices.append([{"mandatory_gate_failed": x} for x in (False, True)])
    if c["vmode"] != "none":
        if "p7" in undecided:
            choices.append([{"p7_failed": x} for x in (False, True)])
        if "v" in undecided:
            choices.append([{"v_pass": True, "power_ok": True, "testable_ok": True}, {"v_pass": False}])
    central = [u for u in ups if u["usages"] & {"phi-center", "nuisance-posterior", "xi", "fixed-value"}]
    flags = set(c["own_flags"]) | {f for u in central for f in u["flags"]} | {
        f for u in ups for f in u["flags"] if f in ("preliminary", "provisional-thresholds")}
    order = ["failed", "projection", "calibrated-unvalidated", "validated-in-scope"]
    seen = set()
    for combo in itertools.product(*choices):
        d = dict(c, incomplete=False)
        for part in combo:
            d.update(part)
        res_set = set()
        efrs = ["final", "none"] if d["earlier_failure_record"] == "pending" else [d["earlier_failure_record"]]
        reus = ["fit", "none"] if d["validation_data_reuse"] == "fit-pending" else [d["validation_data_reuse"]]
        for a, b in itertools.product(efrs, reus):
            g = REF.assign(dict(d, earlier_failure_record=a, validation_data_reuse=b))
            if g == "incomplete":
                res_set.add(("incomplete", frozenset()))
                continue
            r = order.index(g)
            if not c2_only:
                for u in central:
                    r = min(r, order.index(u["effective_grade"]))
                if flags & {"outside-validated-range", "closure-not-tested"}:
                    r = min(r, 2)
            uses_ = {"diagnostics"} | ({"design-study"} if r >= 1 else set()) | (
                {"systematic-variation"} if r >= 2 else set()) | ({"production", "publication"} if r == 3 else set())
            if flags & {"preliminary", "provisional-thresholds"}:
                uses_.discard("publication")
            res_set.add((order[r], frozenset(uses_)))
        seen.add(next(iter(res_set)) if len(res_set) == 1 else ("incomplete", frozenset()))
    return len(seen) == 1, seen


CAPPED_CENTRAL = [dict(usages={"phi-center"}, effective_grade=g, flags=set())
                  for g in ("failed", "projection", "calibrated-unvalidated")]


def lookup_scope():
    """Every own combination of Appendix C's scope with at least one undecided input, with and without a capped
    central upstream (section 15.3.12, last case)."""
    for c in REF.own_cases():
        if not c["incomplete"]:
            continue                       # an undecided input is an incomplete one (consistency rule of the lookup)
        subsets = [("mandatory-gate",)] if c["vmode"] == "none" else [
            s for k in (1, 2, 3) for s in itertools.combinations(use.UNDECIDED, k)]
        for und in subsets:
            for ups in [[]] + [[u] for u in CAPPED_CENTRAL]:
                yield c, ups, und


class OutcomeAlreadyDetermined(unittest.TestCase):
    def test_against_independent_enumeration_slice(self):
        """Also mutant 25: the lookup evaluated with C.2 only differs on the slice, so it is caught."""
        import calibration_exhaustive as ex
        detail, ok = ex.run_lookup(REF, use, deps, 1, LOOKUP_SLICE)
        self.assertTrue(ok, detail["disagreements"])
        self.assertGreater(detail["cases"], 10000)
        self.assertGreater(detail["mutant_c2_only_caught_in"], 0)


def base(**kw):
    c = dict(incomplete=False, mandatory_gate_failed=False, real_data=True, vmode="holdout", design_only=False,
             p7_failed=False, v_pass=True, power_ok=True, testable_ok=True, validation_data_reuse="none",
             validation_data_simulated=False, earlier_failure_record="none", own_flags=set())
    c.update(kw)
    return c


class NamedCases(unittest.TestCase):
    """Sections 15.3.12 (outcome already determined), 15.3.15 (grade rules), 15.3.17 (use)."""

    def test_outcome_already_determined_cases(self):
        failed_up = [dict(usages={"phi-center"}, effective_grade="failed", flags=set())]
        r = use.outcome_determined(base(incomplete=True), failed_up, ["mandatory-gate"])
        self.assertTrue(r["determined"])
        self.assertEqual(r["effective_grade"], "failed")
        self.assertFalse(use.outcome_determined(base(incomplete=True), [], ["mandatory-gate"])["determined"])
        r = use.outcome_determined(base(incomplete=True, real_data=False), [], ["mandatory-gate"])
        self.assertFalse(r["determined"])                                   # failed versus projection
        self.assertEqual({g for g, _ in r["outcomes"]}, {"failed", "projection"})
        r = use.outcome_determined(base(incomplete=True, real_data=False), [], ["v"])
        self.assertEqual((r["determined"], r["effective_grade"]), (True, "projection"))   # not opened
        r = use.outcome_determined(base(incomplete=True, real_data=False), [], ["p7", "v"])
        self.assertEqual(r["effective_grade"], "projection")
        # k0 = 0 known before opening: P7 and V are no-testable-direction (decided, testable_ok False), so the
        # unconfirmed lineage leaves nothing undecided
        r = use.outcome_determined(base(testable_ok=False), [], [])
        self.assertTrue(r["determined"])
        r = use.outcome_determined(base(incomplete=True, own_flags={"closure-not-tested"}), [], ["v"])
        self.assertEqual((r["determined"], r["effective_grade"]), (True, "calibrated-unvalidated"))
        r = use.outcome_determined(base(incomplete=True, p7_failed=True), [], ["v"])      # P7 power insufficient (3b)
        self.assertEqual((r["determined"], r["effective_grade"]), (True, "calibrated-unvalidated"))
        # cross-validation k1 with power lower bound 0.6: not computed, no read; k2 on the same units is free
        k1 = use.outcome_determined(base(incomplete=True, vmode="cross-validation", p7_failed=True), [], ["v"])
        self.assertEqual(k1["effective_grade"], "calibrated-unvalidated")
        k2 = use.judge(base(vmode="cross-validation"), [])
        self.assertEqual(k2["effective_grade"], "validated-in-scope")

    def test_grade_rule_cases(self):
        self.assertEqual(use.assign(base(v_pass=False)), "calibrated-unvalidated")
        self.assertEqual(use.assign(base(vmode="none", design_only=True)), "projection")
        self.assertEqual(use.assign(base(p7_failed=True)), "calibrated-unvalidated")
        self.assertEqual(use.assign(base(mandatory_gate_failed=True)), "failed")      # G8 fails in holdout
        env = dict(usages={"envelope"}, effective_grade="calibrated-unvalidated", flags=set())
        self.assertEqual(use.judge(base(), [env])["effective_grade"], "validated-in-scope")
        env_prov = dict(env, flags={"provisional-thresholds"})
        j = use.judge(base(), [env_prov])
        self.assertIn("provisional-thresholds", j["flags"])
        self.assertNotIn("publication", j["uses"])

    def test_use_rule_cases(self):
        proj = use.judge(base(real_data=False), [])
        self.assertNotIn("production", proj["uses"])
        j = use.judge(base(mandatory_gate_failed=True, own_flags={"outside-validated-range"}), [])
        self.assertEqual(j["effective_grade"], "failed")
        self.assertEqual(use.judge(base(own_flags={"closure-not-tested"}), [])["effective_grade"],
                         "calibrated-unvalidated")
        var = dict(usages={"envelope"}, effective_grade="validated-in-scope", flags={"outside-validated-range"})
        j = use.judge(base(), [var])
        self.assertEqual((j["effective_grade"], j["variation_flags"]), ("validated-in-scope", ["outside-validated-range"]))
        cen = dict(var, usages={"phi-center"})
        self.assertEqual(use.judge(base(), [cen])["effective_grade"], "calibrated-unvalidated")
        prelim = dict(usages={"variation-set"}, effective_grade="validated-in-scope", flags={"preliminary"})
        self.assertNotIn("publication", use.judge(base(), [prelim])["uses"])

    def test_lookup_refuses_inconsistent_undecided_inputs(self):
        """F1 of the phase-0 review: the undecided list matches the incomplete input; mode none has only gates."""
        with self.assertRaises(ValueError):
            use.outcome_determined(base(incomplete=True), [], [])      # incomplete with nothing undecided
        with self.assertRaises(ValueError):
            use.outcome_determined(base(), [], ["v"])                    # undecided but not incomplete
        with self.assertRaises(ValueError):
            use.outcome_determined(base(vmode="none", incomplete=True), [], ["p7", "v"])
        r = use.outcome_determined(base(incomplete=True, p7_failed=True), [], ["v"])
        self.assertEqual(r["inputs_when_not_opened"], {"v_pass": False, "incomplete": False})

    def test_rejections(self):
        with self.assertRaises(ValueError):
            use.judge(base(), [dict(usages={"envelope"}, effective_grade="projection", flags=set())])
        with self.assertRaises(ValueError):
            use.judge(base(), [dict(usages={"envelope"}, effective_grade="incomplete", flags=set())])
        with self.assertRaises(ValueError):
            use.assign(base(earlier_failure_record="pending"))
        with self.assertRaises(ValueError):
            use.check_inputs(dict(base(), vmode="kfold"))
        j = use.judge(base(vmode="cross-validation", earlier_failure_record="pending"), [])
        self.assertEqual((j["effective_grade"], j["own_grade"], j["uses"]), ("incomplete", None, []))
        self.assertEqual(len(j["resolutions"]), 2)


class IncompleteAggregation(unittest.TestCase):
    """Rule 0 aggregation (section 10.2; owner calib_use, section 15.3a 'incomplete aggregation')."""

    def gates(self, **kw):
        g = {x: "passed" for x in use.MANDATORY}
        g.update({k.replace("_", "-"): v for k, v in kw.items()})
        return g

    def test_all_passed(self):
        r = use.aggregate(self.gates(), "passed", "passed", "holdout")
        self.assertEqual((r["inputs"]["incomplete"], r["inputs"]["mandatory_gate_failed"], r["undecided"]),
                         (False, False, []))
        self.assertEqual(use.judge(base(**r["inputs"]), [])["effective_grade"], "validated-in-scope")

    def test_15_3_15_g8_fails_later_stages_not_applicable(self):
        g = self.gates(G8="failed")
        for x in use.STAGES["D"] + use.STAGES["E"]:
            g[x] = "not-run"
        r = use.aggregate(g, "not-applicable", "not-applicable", "holdout")
        self.assertEqual((r["inputs"]["mandatory_gate_failed"], r["inputs"]["incomplete"]), (True, False))
        self.assertEqual(use.judge(base(**r["inputs"]), [])["effective_grade"], "failed")

    def test_not_applicable_not_counted_missing_counted(self):
        r = use.aggregate(self.gates(P0="not-applicable", P6="not-applicable", G4="not-applicable"), "passed",
                          "passed", "holdout")
        self.assertFalse(r["inputs"]["incomplete"])
        g = self.gates()
        del g["G5"]                                                    # not executed: incomplete
        r = use.aggregate(g, "passed", "passed", "holdout")
        self.assertEqual((r["inputs"]["incomplete"], r["undecided"]), (True, ["mandatory-gate"]))
        r = use.aggregate(self.gates(G1="incomplete"), "incomplete", "incomplete", "cross-validation")
        self.assertEqual(r["undecided"], ["mandatory-gate", "p7", "v"])
        self.assertEqual(use.judge(base(**r["inputs"], vmode="cross-validation"), [])["effective_grade"], "incomplete")

    def test_v_and_p7_states(self):
        self.assertFalse(use.aggregate(self.gates(), "passed", "failed", "holdout")["inputs"]["incomplete"])
        r = use.aggregate(self.gates(), "passed", "no-testable-direction", "holdout")
        self.assertEqual(use.judge(base(**r["inputs"]), [])["effective_grade"], "calibrated-unvalidated")
        r = use.aggregate(self.gates(), "no-testable-direction", "no-testable-direction", "holdout")
        self.assertEqual((r["inputs"]["incomplete"], r["inputs"]["testable_ok"]), (False, False))
        r = use.aggregate(self.gates(), "passed", "insufficient-power", "holdout")
        self.assertEqual(use.judge(base(**r["inputs"]), [])["effective_grade"], "calibrated-unvalidated")
        r = use.aggregate(self.gates(G8="closure-not-tested"), "passed", "passed", "holdout")
        self.assertEqual(r["flags"], ["closure-not-tested"])
        self.assertFalse(r["inputs"]["incomplete"])
        r = use.aggregate(self.gates(), "not-applicable", "not-applicable", "none")
        self.assertEqual(use.judge(base(**r["inputs"], vmode="none", design_only=True), [])["effective_grade"],
                         "projection")
        with self.assertRaises(ValueError):
            use.aggregate(self.gates(), "passed", "passed", "none")
        with self.assertRaises(ValueError):
            use.aggregate(self.gates(G99="passed"), "passed", "passed", "holdout")


if __name__ == "__main__":
    unittest.main()
