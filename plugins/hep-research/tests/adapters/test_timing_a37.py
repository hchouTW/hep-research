"""adapters/timing-pid, T10 stage 2: A37 and plan section 9.6 for T10 (t10-timing-stage-plan.md section 6.1, row A37-T10, and the
fix round 1 notes in section 6.4).

The artificial g x E degeneracy (section 9.6's own example y = g E), the T07 weak-mode witness read from its run record (CAI-T07-4,
job 7546791, whose SHA-256 the tool itself pins), and the method card that lists each unconstrained mode with its named external
constraint, the two kept apart by item identifiers. Hand-made inputs only: a hand-made log is never T07's record, so the witness
fails on its source here; the job reads T07's pinned log. A placeholder never satisfies A37. Synthetic; no calibration or alignment
quality claim.

Run from the plugin root: python -m unittest tests.adapters.test_timing_a37 -v
"""
from __future__ import annotations

import copy
import hashlib
import json
import math
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / "adapters" / "timing-pid" / "assets"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ASSETS / "fixture_tools"))
sys.path.insert(0, str(ASSETS))

from timing_recipe import method_card, time_chain, timing_payload  # noqa: E402
import t10_a37  # noqa: E402

GAINS = [1.0, 1.3, 0.8]
ENERGIES = [5.0, 7.0, 9.0, 11.0]
T07_SHA256 = "0f60e9ac0ebe9114c0ba1f64369926027b7b130d9c43884ddcd458bf73316a90"   # calibration-alignment-interfaces.md, T10 stage 2


class GainTimesEnergy(unittest.TestCase):
    def test_design_has_one_null_mode(self):
        rows = t10_a37.gxe_design(3, 4)
        self.assertEqual(len(rows), 12)
        self.assertEqual(t10_a37.exact_rank(rows), 3 + 4 - 1)
        null = [1] * 3 + [-1] * 4
        self.assertTrue(all(sum(a * b for a, b in zip(row, null)) == 0 for row in rows))
        self.assertEqual(t10_a37.exact_rank(rows + [[0] * 3 + [1, 0, 0, 0]]), 3 + 4)   # one known energy: full rank

    def test_check_passes_and_the_scale_is_identified_only_with_the_constraint(self):
        result = t10_a37.gxe_check(GAINS, ENERGIES, gauge=2.0, reference_event=0)
        self.assertEqual(result["verdict"], "PASS", json.dumps(result, indent=1))
        self.assertEqual(sorted(result["items"]), ["claims", "constraint", "convergence", "gauge", "holdout", "identifiable", "rank"])
        self.assertFalse(result["identified_without_constraint"])
        self.assertTrue(result["identified_with_constraint"])
        self.assertEqual(result["rank"], {"without": 6, "with": 7, "parameters": 7})

    def test_two_gauges_give_identical_amplitudes(self):
        a = 2.0
        y1 = [g * e for g in GAINS for e in ENERGIES]
        y2 = [(a * g) * (e / a) for g in GAINS for e in ENERGIES]
        for u, v in zip(y1, y2):
            self.assertLessEqual(abs(u - v), 1e-12 * u)
        result = t10_a37.gxe_check(GAINS, ENERGIES, gauge=a, reference_event=0)
        self.assertLessEqual(result["largest_relative"]["gauge"], 1e-12)

    def test_a_claim_of_identification_by_holdout_or_convergence_is_refused(self):  # fix round 1, M3
        for by in ("holdout", "convergence"):
            result = t10_a37.gxe_check(GAINS, ENERGIES, gauge=2.0, reference_event=0,
                                       claims=[{"claim": "absolute scale identified", "by": by}])
            with self.subTest(by=by):
                self.assertEqual(result["verdict"], "FAIL")
                self.assertEqual(result["items"]["claims"]["verdict"], "FAIL")
        named = t10_a37.gxe_check(GAINS, ENERGIES, gauge=2.0, reference_event=0,
                                  claims=[{"claim": "absolute scale identified", "by": "constraint.known-energy-event"}])
        self.assertEqual(named["verdict"], "PASS")


class ChainGauge(unittest.TestCase):  # fix round 1, M2: stage 1's walk follows the amplitude gauge
    def test_scaled_amplitudes_with_scaled_walk_coefficients_give_identical_times(self):
        scale = 4.0
        source = "T10 stage 2 hand-made constants; no measurement (R31)"
        walks = [0.5, 0.6, 0.7, 0.8]

        def payloads(walk_values):
            return {step: timing_payload.read(timing_payload.payload_bytes(step, list(values), 4, 1, "nominal", source))
                    for step, values in (("offset", (1.0, 2.0, 3.0, 4.0)), ("walk", walk_values), ("propagation", (15.0, 15.0, 16.0, 16.0)))}

        rows = [(10, 1, 0, 40.0, 100.0, 30.0, 300.0), (11, 2, 1, 45.0, 64.0, 50.0, 320.0), (12, 3, 2, 50.0, 25.0, 10.0, 350.0),
                (13, 4, 3, 42.0, 400.0, 80.0, 310.0)]

        def hits(amplitude_scale):
            return [{"hit_id": h, "track_id": t, "counter": c, "raw_time_ns": r, "amplitude": a * amplitude_scale, "position_cm": d,
                     "path_length_cm": l} for h, t, c, r, a, d, l in rows]

        plain = time_chain.correct(hits(1.0), payloads(walks))
        gauged = time_chain.correct(hits(scale), payloads([w * math.sqrt(scale) for w in walks]))
        for p, g in zip(plain, gauged):
            self.assertLessEqual(abs(p["corrected_time_ns"] - g["corrected_time_ns"]), 1e-12)


def cell_line(charge, bin_, qp, chi2, se):
    return (f"CAI-T07-4 cell charge {charge:+d} bending bin {bin_} tracks 1500 and 1500 change in q/p {qp:.4f} per-track sigmas "
            f"(se 0.0360, sigma 0.004050 per GeV), 4.9000 stated sigmas; change in mean chi2/ndf {chi2:+.5f} (se {se:.5f}); expected 5.003")


def log_text(cells=None, outcome=True):
    cells = cells or [(q, b, 5.0, 0.001, 0.0155) for q in (-1, 1) for b in range(4)]
    head = "test_cai_t07_4_self_check (tests.adapters.test_acts_cai_refit.CaiRefitRun.test_cai_t07_4_self_check) ... "
    lines = [cell_line(*c) for c in cells]
    lines[0] = head + lines[0]
    tail = ["CAI-T07-4 most-affected cell (-1, 3), k 4.5, n 4.5; all tracks"]
    if outcome:
        tail += ["ok", "", "-" * 70, "Ran 18 tests in 118.409s", "", "OK"]
    return "\n".join(["noise line"] + lines + tail) + "\n"


def pinned_to(text):
    """The tool pins T07's hash; a test of the pass path patches the pin to the hand-made text's own hash."""
    return mock.patch.object(t10_a37, "T07_LOG_SHA256", hashlib.sha256(text.encode()).hexdigest())


class WeakModeWitness(unittest.TestCase):
    def test_the_tool_pins_t07s_record(self):  # fix round 1, I2
        self.assertEqual((t10_a37.T07_LOG_SHA256, t10_a37.T07_JOB), (T07_SHA256, 7546791))

    def test_parses_the_eight_cells(self):
        cells = t10_a37.parse_t07_witness(log_text())
        self.assertEqual(len(cells), 8)
        self.assertEqual(cells[0], {"charge": -1, "bin": 0, "qp_sigmas": 5.0, "chi2_change": 0.001, "chi2_se": 0.0155})

    def test_a_hand_made_log_is_not_t07s_record(self):  # fix round 1, I2: any other hash fails on the source
        result = t10_a37.witness_check(log_text())
        self.assertEqual(result["verdict"], "FAIL")
        self.assertEqual(result["items"]["source"]["verdict"], "FAIL")
        self.assertEqual(result["items"]["weak"]["verdict"], "PASS")

    def test_the_pass_path_with_the_pin_patched(self):
        text = log_text()
        with pinned_to(text):
            self.assertEqual(t10_a37.witness_check(text)["verdict"], "PASS")

    def test_the_placeholder_control_is_a_real_placeholder_text(self):  # fix round 1, I2
        text = t10_a37.placeholder_text()
        self.assertEqual(len(t10_a37.parse_t07_witness(text)), 8)            # valid-looking cells
        result = t10_a37.witness_check(text)
        self.assertEqual(result["verdict"], "FAIL")
        self.assertEqual(result["items"]["source"]["verdict"], "FAIL")
        self.assertEqual(t10_a37.witness_check(log_text(), plant="placeholder-witness")["items"]["source"]["verdict"], "FAIL")

    def test_the_record_must_show_its_own_outcome(self):  # fix round 1, M9
        text = log_text(outcome=False)
        with pinned_to(text):
            result = t10_a37.witness_check(text)
        self.assertEqual(result["verdict"], "FAIL")
        self.assertEqual(result["items"]["outcome"]["verdict"], "FAIL")

    def test_a_cell_that_is_not_weak_fails(self):
        for cells in ([(q, b, 4.0 if (q, b) == (1, 2) else 5.0, 0.001, 0.0155) for q in (-1, 1) for b in range(4)],
                      [(q, b, 5.0, 0.2 if (q, b) == (-1, 1) else 0.001, 0.0155) for q in (-1, 1) for b in range(4)]):
            text = log_text(cells)
            with self.subTest(cells=cells[:1]), pinned_to(text):
                self.assertEqual(t10_a37.witness_check(text)["verdict"], "FAIL")

    def test_seven_cells_are_not_a_witness(self):
        text = log_text([(q, b, 5.0, 0.001, 0.0155) for q in (-1, 1) for b in range(4)][:7])
        with pinned_to(text):
            self.assertEqual(t10_a37.witness_check(text)["verdict"], "FAIL")


def ids(items):
    return {item["id"] for item in items}


class MethodCard(unittest.TestCase):
    def test_the_card_lists_each_mode_with_its_named_constraint(self):
        card = method_card.load()
        method_card.check(card)
        self.assertEqual(card["format"], "timing-method-card/2")
        modes = {m["mode"]: m for m in card["unconstrained_modes"]}
        self.assertEqual(sorted(modes), ["mode.amplitude-scale", "mode.common-time-offset", "mode.curvature-offset"])
        self.assertIn("constraint.vertex-or-beam", ids(modes["mode.curvature-offset"]["constraining_information"]))
        self.assertIn("CAI-T07-4", modes["mode.curvature-offset"]["witness"])
        self.assertIn("constraint.external-start-time", ids(modes["mode.common-time-offset"]["constraining_information"]))
        for mode in modes.values():
            self.assertTrue(mode["constraining_information"] and mode["independent_observables"] and mode["witness"])
            self.assertFalse(ids(mode["constraining_information"]) & ids(mode["independent_observables"]))   # fix round 1, I3
            self.assertTrue(all(i.startswith("constraint.") for i in ids(mode["constraining_information"])))
            self.assertTrue(all(i.startswith("observable.") for i in ids(mode["independent_observables"])))

    def test_card_refusals(self):
        def no_constraint(card):
            card["unconstrained_modes"][0]["constraining_information"] = []

        def overlap(card):  # fix round 1, I3: the same item as constraint and as validation
            mode = card["unconstrained_modes"][2]
            mode["independent_observables"].append(copy.deepcopy(mode["constraining_information"][0]))

        def used_as_validation(card):
            mode = card["unconstrained_modes"][0]
            mode["constraints_used"] = [mode["independent_observables"][0]["id"]]

        def no_witness(card):
            card["unconstrained_modes"][1]["witness"] = ""

        def unknown_used(card):
            card["unconstrained_modes"][0]["constraints_used"] = ["constraint.not-on-this-card"]

        def no_id(card):
            del card["unconstrained_modes"][0]["independent_observables"][0]["id"]

        for name, change in {"no constraint": no_constraint, "overlap": overlap, "used as validation": used_as_validation,
                             "no witness": no_witness, "unknown used constraint": unknown_used, "item without id": no_id}.items():
            card = copy.deepcopy(method_card.load())
            change(card)
            with self.subTest(case=name), self.assertRaises(method_card.InputError):
                method_card.check(card)

    def test_a_used_constraint_is_accepted_and_never_validates(self):  # fix round 1, I3: a non-empty constraints_used
        card = copy.deepcopy(method_card.load())
        mode = card["unconstrained_modes"][2]
        mode["constraints_used"] = ["constraint.vertex-or-beam"]
        method_card.check(card)

    def test_cai_t06_3_contract_part_agrees(self):
        """The P1 part of A37 is CAI-T06-3 (T06): a constraint used in a payload's derivation is not its independent validation."""
        from contracts.conditions import check_validation_claim
        from tests.contracts.reconstruction_fixtures import alignment_payload, code_list
        self.assertIn("conditions.constraint_as_validation",
                      code_list(check_validation_claim(alignment_payload(), "constraint.track-straightness")))


class Tool(unittest.TestCase):
    def test_cli_a37_on_a_hand_made_log_fails_on_the_witness(self):
        script = ASSETS / "fixture_tools" / "t10_stage2.py"
        text = log_text()
        with tempfile.TemporaryDirectory() as scratch:
            log = Path(scratch) / "cai-refit.log"
            log.write_text(text)
            base = [sys.executable, "-B", str(script), "a37", "--t07-log", str(log)]
            p = subprocess.run(base + ["--out", str(Path(scratch) / "hand")], capture_output=True, text=True, timeout=120)
            self.assertEqual(p.returncode, 1, p.stdout + p.stderr)
            self.assertIn("RESULT t10-a37 FAIL failed items witness plant none", p.stdout)
            doc = json.loads((Path(scratch) / "hand" / "t10-a37.json").read_text())
            self.assertEqual((doc["format"], doc["status_label"]), ("t10-a37-record/1", "synthetic"))
            q = subprocess.run(base + ["--out", str(Path(scratch) / "h"), "--plant", "holdout-as-proof"], capture_output=True, text=True,
                               timeout=120)
            self.assertEqual(q.returncode, 1, q.stdout + q.stderr)
            self.assertIn("PLANT holdout-as-proof item gxe FAIL", q.stdout)
            other = subprocess.run(base + ["--expected-sha256", "0" * 64, "--out", str(Path(scratch) / "x")], capture_output=True,
                                   text=True, timeout=120)
            self.assertEqual(other.returncode, 2)                                   # only T07's own hash may be named
            self.assertIn('"status": "rejected"', other.stdout)
            missing = subprocess.run([sys.executable, "-B", str(script), "a37", "--t07-log", str(Path(scratch) / "none.log"),
                                      "--out", str(Path(scratch) / "m")], capture_output=True, text=True, timeout=120)
            self.assertEqual(missing.returncode, 2)
            self.assertIn('"status": "rejected"', missing.stdout)


if __name__ == "__main__":
    unittest.main()
