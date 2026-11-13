"""T12 stage 1: CAI-T12-1 and CAI-T12-2 of plan R37, the synthetic two-round outer loop (R36, Section 9.7, G06).

Interface tests with synthetic fixtures only: no constant is derived from data, the convergence and unconstrained-mode checks are
placeholders with no quality meaning, and they never satisfy A37. Every expectation and tolerance below is fixed in
docs/dev/detector-reconstruction/t12-stage-plan.md ("Stage 1") before the harness was written; the expected gains, metrics and labels
are computed here in closed form, not by the harness. The control rules the loop runs under are not qualified (G07, mode M1).

Run from the plugin root: python -m unittest tests.contracts.test_t12_outer_loop -v
"""
from __future__ import annotations

import inspect
import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "skills" / "hep-computing" / "scripts"))
from contracts.conditions import affected_payloads  # noqa: E402
from contracts.recipe_semantics import canonical_sha256  # noqa: E402
from unittest import mock  # noqa: E402
from control_layer_support import derivation as dv  # noqa: E402
from tests.contracts import t12_outer_loop as loop  # noqa: E402

CHANNELS = 8
HITS = 4
E_REF = 1.0
SPREAD = {"converging": 0.02, "non-converging": 0.20}
TAU = 0.01
RELATIVE = 1e-12
FAMILY = "t12-synthetic-gain"
TAG = "t12_synthetic_gain"
LOOP_STEPS = ("reco-r1", "derive-r1", "reco-r2", "derive-r2")
ALL_STEPS = ("nominal-gain",) + LOOP_STEPS + ("reco-final",)
PINNED = {  # t12-stage-plan.md, "Checks, fixed by digest" (fix round 1, M4): a changed check is a deliberate change here and there
    "convergence": ("b46a97f9e5648140ca50266cb6f97c36ae83102b4b0f0037b7315f964140eb11",
                    "c917f155c8e428fa8eff6c9cb487be3e93bb17a25d63c6ecb187716b651a6eed"),
    "mode": ("a386952dcd38dac23ef767c734f7617d35b71c099c80d4ab8e804a19f04d6399",
             "3b50666832ebdb8aadb2c04f4d4d8cdedfeefb4ca56aaf2443ae4ea006a76f10"),
    "record": ("5994228c8f69a70fc5c8e722b1d0584f6edcc19777012fb97ff1439c117fd994",
               "2588325e331c11c5608ce39d7e540bef63d3d83eea1d22b62b6c55f29537662a"),
}
LABELS = {"nominal-gain": "ok", "reco-r1": "superseded_by_iteration", "derive-r1": "superseded_by_iteration",
          "reco-r2": "iteration_internal", "derive-r2": "ok", "reco-final": "ok"}


def offsets(variant):
    spread = SPREAD[variant]
    return [spread * (c - 3.5) / 3.5 for c in range(CHANNELS)]


def round_gains(variant, n):
    """Closed form of the placeholder derivation: g_1 = 1 + d/2, g_2 = 1 + 3d/4."""
    return [1.0 + {0: 0.0, 1: 0.5, 2: 0.75}[n] * d for d in offsets(variant)]


def metric(variant):
    return max(abs(d) / 4 / (1 + d / 2) for d in offsets(variant))


def close(a, b):
    return abs(a - b) <= RELATIVE * max(abs(a), abs(b), 1.0)


_RECORDS = {}


def record(variant, plant=None):
    key = (variant, plant)
    if key not in _RECORDS:
        _RECORDS[key] = loop.run(variant, plant=plant)
    return _RECORDS[key]


class FixtureContract(unittest.TestCase):
    """The fixture contract fixes the final round at 2 and both checks by digest (R37, calibration reference)."""

    def test_the_fixture_constants_are_the_stage_plans(self):
        self.assertEqual((loop.CHANNELS, loop.HITS, loop.E_REF, loop.TAU, loop.FINAL_ROUND, loop.FAMILY, loop.TAG),
                         (CHANNELS, HITS, E_REF, TAU, 2, FAMILY, TAG))
        self.assertEqual(loop.SPREAD, SPREAD)

    def test_check_digests_are_the_pinned_values(self):
        self.assertEqual(loop.check_digests(), PINNED)

    def test_check_digests_are_the_check_functions_source(self):
        digests = loop.check_digests()
        for name, function in (("convergence", loop.convergence_check), ("mode", loop.unconstrained_mode_check),
                               ("record", loop.record_check)):
            with self.subTest(check=name):
                self.assertEqual(digests[name][0], canonical_sha256({"source": inspect.getsource(function)}))
        self.assertEqual(digests["convergence"][1], canonical_sha256({"tau": TAU}))

    def test_the_family_names_both_checks_and_the_final_round(self):
        spec = loop.contract_spec()
        family = spec["families"][FAMILY]
        digests = loop.check_digests()
        self.assertEqual((family.final_round, family.convergence_check, family.mode_check),
                         (2, digests["convergence"][0], digests["mode"][0]))
        final_step = spec["steps"]["derive-r2"]
        self.assertTrue(final_step.checked)
        self.assertEqual(final_step.required, frozenset({digests["convergence"], digests["mode"]}))
        self.assertEqual(final_step.na_allowed, frozenset())
        self.assertEqual({name: (s.family, s.round) for name, s in spec["steps"].items()},
                         {"nominal-gain": (None, None), "reco-r1": (FAMILY, 1), "derive-r1": (FAMILY, 1),
                          "reco-r2": (FAMILY, 2), "derive-r2": (FAMILY, 2), "reco-final": (None, None)})
        self.assertEqual(spec["steps"]["reco-final"].upstream, ("derive-r2",))
        self.assertEqual({did: d.step for did, d in spec["deliverables"].items()},
                         {"final-gain": "derive-r2", "final-product": "reco-final"})

    def test_the_contract_is_effective_under_m1(self):
        log = dv.Log()
        log.append("session", "C", mode="M1")
        log.append("contract", "agent", spec=loop.contract_spec())
        self.assertEqual(dv.contract(log)["families"][FAMILY].final_round, 2)

    def test_g06_contracts_that_break_the_final_round_rule_are_refused(self):
        """C1-C4, each by its rule's message. C3 (a round-1 deliverable) is refused by the checked-step rule, which implies the
        deliverable rule (only a checked step is deliverable, and only the final step is checked)."""
        digests = loop.check_digests()

        def no_round_one(s):
            s["steps"].update({name: _replace(s["steps"][name], family=None, round=None) for name in ("reco-r1", "derive-r1")})

        def two_checked(s):
            s["steps"]["reco-r2"] = _replace(s["steps"]["reco-r2"], checked=True, required=s["steps"]["derive-r2"].required)

        def round_one_deliverable(s):
            s["steps"]["derive-r1"] = _replace(s["steps"]["derive-r1"], checked=True, required=frozenset({digests["record"]}))
            s["deliverables"]["early"] = dv.Deliverable(step="derive-r1", target="T2")

        def convergence_not_applicable(s):
            s["steps"]["derive-r2"] = _replace(s["steps"]["derive-r2"], na_allowed=frozenset({digests["convergence"]}))

        cases = {"C1 no round 1": (no_round_one, r"rounds must be exactly 1\.\.final_round"),
                 "C2 two checked final steps": (two_checked, r"exactly one checked step"),
                 "C3 round-1 deliverable": (round_one_deliverable, r"only the family's final step is checked"),
                 "C4 not-applicable convergence": (convergence_not_applicable, r"cannot be not-applicable")}
        for name, (change, message) in cases.items():
            with self.subTest(case=name):
                spec = loop.contract_spec()
                change(spec)
                log = dv.Log()
                log.append("session", "C", mode="M1")
                with self.assertRaisesRegex(dv.Rejected, message):
                    log.append("contract", "agent", spec=spec)


def _replace(step, **fields):
    import dataclasses
    return dataclasses.replace(step, **fields)


class SyntheticFixture(unittest.TestCase):
    """The payloads follow the closed form; round-2 payloads differ (R37)."""

    def test_gains_follow_the_closed_form_in_both_variants(self):
        for variant in SPREAD:
            rec = record(variant)
            for step, n in (("nominal-gain", 0), ("derive-r1", 1), ("derive-r2", 2)):
                with self.subTest(variant=variant, step=step):
                    got = rec["payloads"][step]["gains"]
                    self.assertEqual(len(got), CHANNELS)
                    self.assertTrue(all(close(a, b) for a, b in zip(got, round_gains(variant, n))), (got, round_gains(variant, n)))

    def test_round_two_payloads_differ_under_one_tag(self):
        for variant in SPREAD:
            rec = record(variant)
            ids = [rec["payloads"][s]["payload_id"] for s in ("nominal-gain", "derive-r1", "derive-r2")]
            with self.subTest(variant=variant):
                self.assertEqual(len(set(ids)), 3)
                self.assertEqual({rec["payloads"][s]["tag"] for s in ("nominal-gain", "derive-r1", "derive-r2")}, {TAG})
                self.assertEqual([rec["payloads"][s]["round"] for s in ("nominal-gain", "derive-r1", "derive-r2")], [None, 1, 2])

    def test_round_payloads_name_the_previous_round_and_their_producing_step(self):
        """I5: derived_against.upstream_payloads and derived_from hold the previous round's payload; producer.step_id is the producing
        step's computational identity, recomputed here from Control section 4.2 (step, program, environment, external, consumed inputs)."""
        spec = loop.contract_spec()
        for variant in SPREAD:
            rec = record(variant)
            for step, previous in (("derive-r1", "nominal-gain"), ("derive-r2", "derive-r1")):
                with self.subTest(variant=variant, step=step):
                    document = rec["payloads"][step]["document"]
                    previous_id = rec["payloads"][previous]["payload_id"]
                    self.assertEqual(document["derived_against"], {"upstream_payloads": [previous_id]})
                    self.assertEqual(document["derived_from"], previous_id)
                    step_spec = spec["steps"][step]
                    identity = dv.digest_of({"kind": "computation", "step": step, "program": step_spec.program,
                                             "environment": step_spec.env, "external": list(step_spec.external),
                                             "inputs": dict(sorted(rec["steps"][step]["consumed"].items()))})
                    self.assertEqual(rec["steps"][step]["identity"], identity)
                    self.assertEqual(document["producer"], {"kind": "step", "step_id": identity})
            nominal = rec["payloads"]["nominal-gain"]["document"]
            self.assertEqual(nominal["derived_against"], {"upstream_payloads": []})
            self.assertNotIn("derived_from", nominal)

    def test_a_change_of_an_earlier_round_affects_the_later_ones(self):
        rec = record("converging")
        documents = [rec["payloads"][s]["document"] for s in ("nominal-gain", "derive-r1", "derive-r2")]
        ids = [d["payload_id"] for d in documents]
        self.assertEqual(affected_payloads([ids[1]], documents), [ids[2]])
        self.assertEqual(affected_payloads([ids[0]], documents), [ids[1], ids[2]])
        self.assertEqual(affected_payloads([ids[2]], documents), [])

    def test_the_convergence_metric_equals_the_closed_form(self):
        for variant in SPREAD:
            with self.subTest(variant=variant):
                self.assertTrue(close(record(variant)["checks"]["convergence"]["metric"], metric(variant)))
        self.assertLess(metric("converging"), TAU)
        self.assertGreater(metric("non-converging"), TAU)

    def test_the_record_states_no_quality_claim_and_no_a37(self):
        for variant in SPREAD:
            claims = record(variant)["claims"]
            with self.subTest(variant=variant):
                self.assertEqual(claims["label"], "synthetic")
                self.assertEqual(claims["quality"], "none")
                self.assertEqual(claims["a37"], "not satisfied by this fixture")


class ConvergingLoop(unittest.TestCase):
    """CAI-T12-1: both checks pass at round 2 and the final outputs are released (L1-L8)."""

    @classmethod
    def setUpClass(cls):
        cls.rec = record("converging")

    def test_l1_every_step_ran_once(self):
        self.assertEqual(set(self.rec["steps"]), set(ALL_STEPS))
        self.assertEqual({s: v["computed"] for s, v in self.rec["steps"].items()}, {s: 1 for s in ALL_STEPS})
        self.assertEqual(self.rec["order"], list(ALL_STEPS))

    def test_l2_each_product_records_the_payload_and_round_it_consumed(self):
        expected = {"reco-r1": ("nominal-gain", None), "reco-r2": ("derive-r1", 1), "reco-final": ("derive-r2", 2)}
        for product, (payload_step, rnd) in expected.items():
            with self.subTest(product=product):
                used = self.rec["products"][product]["conditions_used"]
                self.assertEqual(len(used), 1)
                self.assertEqual((used[0]["slot"], used[0]["payload_id"], used[0]["round"]),
                                 ("gain", self.rec["payloads"][payload_step]["payload_id"], rnd))
                self.assertEqual(self.rec["products"][product]["check_used_errors"], [])

    def test_l2_energies_are_reconstructed_with_the_consumed_payload(self):
        for product, n in (("reco-r1", 0), ("reco-r2", 1), ("reco-final", 2)):
            gains = round_gains("converging", n)
            truth = [1.0 + d for d in offsets("converging")]
            with self.subTest(product=product):
                got = self.rec["products"][product]["channel_means"]
                self.assertTrue(all(close(e, g_true * E_REF / g) for e, g_true, g in zip(got, truth, gains)))

    def test_l3_no_cached_result_is_reused_across_differing_payloads(self):
        decisions = {(d["for"], d["cached"]): d for d in self.rec["cache"]}
        self.assertEqual(set(decisions), {("reco-r2", "reco-r1"), ("reco-final", "reco-r1"), ("reco-final", "reco-r2")})
        for key, decision in decisions.items():
            with self.subTest(pair=key):
                self.assertFalse(decision["reuse"])
                self.assertEqual(decision["changed"], ["gain"])
                self.assertIsNone(decision["acted"], "nothing is acted on across differing payloads")

    def test_l3_the_same_payload_is_reused_through_a_reuse_fact(self):
        control = self.rec["reuse_control"]
        self.assertTrue(control["decision"]["reuse"])
        self.assertEqual(control["decision"]["acted"], "reused")
        self.assertEqual(control["state"], "reused")
        self.assertEqual(control["source"], self.rec["steps"]["reco-final"]["artifact"])

    def test_l3_the_control_layer_refuses_a_reuse_across_steps(self):
        self.assertIn("reuse source is not a usable, current output", self.rec["reuse_across_steps"])

    def test_l4_steps_outside_the_loop_consume_only_the_final_round(self):
        self.assertEqual(self.rec["steps"]["reco-final"]["consumed"],
                         {"derive-r2": self.rec["steps"]["derive-r2"]["artifact"]})

    def test_l5_labels_follow_the_calibration_reference(self):
        self.assertEqual({s: v["label"] for s, v in self.rec["steps"].items()}, LABELS)

    def test_l6_both_checks_pass_on_the_final_step(self):
        self.assertEqual({k: v["result"] for k, v in self.rec["checks"].items()},
                         {"convergence": "pass", "mode": "pass", "record": "pass"})

    def test_l7_both_deliverables_are_published(self):
        self.assertEqual(sorted(self.rec["published"]), ["final-gain", "final-product"])
        self.assertEqual(self.rec["published"]["final-gain"], self.rec["steps"]["derive-r2"]["artifact"])
        self.assertEqual(self.rec["published"]["final-product"], self.rec["steps"]["reco-final"]["artifact"])
        self.assertEqual(self.rec["publish_refused"], {})

    def test_the_assessment_holds(self):
        self.assertEqual(loop.assess(self.rec), [])


class NonConvergingLoop(unittest.TestCase):
    """CAI-T12-2: the convergence check fails; the final step is held and nothing is released (H1-H6)."""

    @classmethod
    def setUpClass(cls):
        cls.rec = record("non-converging")

    def test_h1_the_convergence_check_fails_and_the_mode_check_passes(self):
        self.assertEqual(self.rec["checks"]["convergence"]["result"], "fail")
        self.assertEqual(self.rec["checks"]["mode"]["result"], "pass")
        self.assertNotIn("record", self.rec["checks"])

    def test_h1_rounds_one_and_two_ran_with_their_payloads(self):
        self.assertEqual(set(self.rec["steps"]), set(ALL_STEPS) - {"reco-final"})
        self.assertEqual(self.rec["products"]["reco-r2"]["conditions_used"][0]["round"], 1)
        self.assertTrue(all(not d["reuse"] for d in self.rec["cache"]))

    def test_h2_the_final_step_is_held_and_nothing_is_released(self):
        self.assertEqual(self.rec["steps"]["derive-r2"]["label"], "held")
        self.assertNotIn("reco-final", self.rec["products"])
        self.assertEqual(self.rec["published"], {})
        self.assertEqual(sorted(self.rec["publish_refused"]), ["final-gain", "final-product"])
        self.assertTrue(all("deliverable not met" in r for r in self.rec["publish_refused"].values()))

    def test_h3_non_final_outputs_carry_the_iteration_status(self):
        self.assertEqual({s: self.rec["steps"][s]["label"] for s in ("reco-r1", "derive-r1", "reco-r2")},
                         {s: LABELS[s] for s in ("reco-r1", "derive-r1", "reco-r2")})

    def test_h4_the_non_convergence_stays_in_the_history(self):
        conv = loop.check_digests()["convergence"][0]
        failures = self.rec["history"]["prior_failures"]
        self.assertIn(["derive-r2", self.rec["steps"]["derive-r2"]["artifact"], conv, "fail"], failures)
        self.assertEqual(self.rec["rewrite_probe"]["label"], "held")

    def test_h5_forcing_the_outside_step_releases_nothing(self):
        forced = self.rec["forced_outside"]
        self.assertEqual(forced["label"], "blocked_upstream")
        self.assertIn("deliverable not met", forced["publish"])

    def test_h6_the_hold_is_the_expected_result(self):
        self.assertEqual(loop.assess(self.rec), [])


class PlantedDefects(unittest.TestCase):
    """P1-P4: each planted defect is detected by the assessment."""

    EXPECTED = {"wrong-round": {"L2"}, "reuse-across-payloads": {"L3"},
                "outside-consumes-round-1": {"L2", "L3", "L4", "L5", "L6", "L7"}, "skip-final-checks": {"L5", "L6", "L7"},
                "mode-unconstrained": {"L1", "L2", "L3", "L4", "L5", "L6", "L7"}}

    def test_each_planted_defect_is_detected_with_its_exact_set(self):
        self.assertEqual(set(loop.PLANTS), set(self.EXPECTED))
        for plant, ids in self.EXPECTED.items():
            with self.subTest(plant=plant):
                self.assertEqual(set(loop.assess(record("converging", plant))), ids)

    def test_p1_the_control_layer_still_publishes_a_wrong_round(self):
        """The open finding of I4: the loop's gating does not read R32 records; only check_used catches it (L2)."""
        self.assertEqual(sorted(record("converging", "wrong-round")["published"]), ["final-gain", "final-product"])

    def test_p2_a_tag_keyed_hit_goes_through_admission_and_is_refused(self):
        rec = record("converging", "reuse-across-payloads")
        decision = {(d["for"], d["cached"]): d for d in rec["cache"]}[("reco-r2", "reco-r1")]
        self.assertTrue(decision["reuse"])
        self.assertIn("reuse source is not a usable, current output", decision["acted"])
        self.assertEqual(rec["products"]["reco-r2"]["conditions_used"][0]["round"], 1, "the step was computed after the refusal")

    def test_p3_the_record_check_fails_on_the_unknown_payload(self):
        rec = record("converging", "outside-consumes-round-1")
        self.assertEqual(rec["checks"]["record"]["result"], "fail")
        self.assertIn("conditions.unknown_payload", rec["checks"]["record"]["errors"])
        self.assertEqual(sorted(rec["published"]), ["final-gain"])

    def test_p5_the_mode_check_holds_the_final_step(self):
        rec = record("converging", "mode-unconstrained")
        self.assertEqual({k: v["result"] for k, v in rec["checks"].items()}, {"convergence": "pass", "mode": "fail"})
        self.assertEqual(rec["steps"]["derive-r2"]["label"], "held")
        self.assertNotIn("reco-final", rec["steps"])
        self.assertEqual(rec["published"], {})

    def test_an_empty_record_fails_every_expectation(self):
        """The assessment judges positively: a record with nothing in it is not a pass."""
        self.assertEqual(set(loop.assess({"variant": "converging"})), {f"L{i}" for i in range(1, 9)})
        self.assertEqual(set(loop.assess({"variant": "non-converging"})), {f"H{i}" for i in range(1, 6)})

    def test_p1_the_round_mismatch_is_named(self):
        errors = record("converging", "wrong-round")["products"]["reco-r2"]["check_used_errors"]
        self.assertIn("conditions.round_mismatch", errors)

    def test_p3_the_outside_product_is_invalidated_and_not_published(self):
        rec = record("converging", "outside-consumes-round-1")
        self.assertEqual(rec["steps"]["reco-final"]["label"], "invalidated")
        self.assertNotIn("final-product", rec["published"])

    def test_p4_publish_refuses_without_the_checks(self):
        rec = record("converging", "skip-final-checks")
        self.assertEqual(rec["published"], {})
        self.assertEqual(rec["steps"]["derive-r2"]["label"], "unchecked")


class CommandLine(unittest.TestCase):
    """Exit codes follow core/status.py: 0, 1, 2 (3 when the harness cannot run)."""

    def main(self, *args):
        out = io.StringIO()
        with redirect_stdout(out):
            code = loop.main(list(args))
        return code, json.loads(out.getvalue().strip().splitlines()[-1])

    def test_exit_codes(self):
        with tempfile.TemporaryDirectory() as scratch:
            path = Path(scratch) / "loop.json"
            code, out = self.main("run", "--variant", "converging", "--out", str(path))
            self.assertEqual((code, out["status"]), (0, "ok"), out)
            written = json.loads(path.read_text())
            self.assertEqual(written["schema"], "t12-outer-loop/1")
            before = path.read_bytes()
            code, out = self.main("run", "--variant", "converging", "--out", str(path))
            self.assertEqual((code, out["status"]), (2, "rejected"))
            self.assertEqual(path.read_bytes(), before, "a record is never overwritten")
            code, out = self.main("run", "--variant", "non-converging", "--out", str(Path(scratch) / "held.json"))
            self.assertEqual((code, out["status"]), (0, "ok"), out)
            code, out = self.main("run", "--variant", "converging", "--plant", "wrong-round", "--out", str(Path(scratch) / "p1.json"))
            self.assertEqual((code, out["status"]), (1, "failed"), out)
            self.assertIn("L2", out["failed"])
            code, out = self.main("run", "--variant", "sideways", "--out", str(Path(scratch) / "x.json"))
            self.assertEqual((code, out["status"]), (2, "rejected"))
            code, out = self.main("run", "--variant", "converging", "--out", str(Path(scratch) / "missing" / "x.json"))
            self.assertEqual((code, out["status"]), (2, "rejected"))

    def test_incomplete_runs_exit_3(self):
        with tempfile.TemporaryDirectory() as scratch:
            with mock.patch.object(loop, "run", side_effect=RuntimeError("synthetic crash")):
                code, out = self.main("run", "--variant", "converging", "--out", str(Path(scratch) / "a.json"))
            self.assertEqual((code, out["status"]), (3, "incomplete"))
            with mock.patch.object(loop, "write_record", side_effect=OSError("synthetic write failure")):
                code, out = self.main("run", "--variant", "converging", "--out", str(Path(scratch) / "b.json"))
            self.assertEqual((code, out["status"]), (3, "incomplete"))


if __name__ == "__main__":
    unittest.main()
