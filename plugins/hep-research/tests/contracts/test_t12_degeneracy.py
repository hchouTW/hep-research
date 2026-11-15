"""T12 stage 6: A37 and plan section 9.6 in T12 (T12-18, the g x E degeneracy; T12-19, the weak-mode witness; R31, R37).

Identifiability tests on synthetic fixtures: no constant is derived from data and no alignment or calibration quality is claimed (R31).
Every expectation and tolerance below is fixed in docs/dev/detector-reconstruction/t12-stage-plan.md ("Stage 6") before the harness was
written; the expected values are computed here in closed form or read from T07's record, not taken from the harness. The control rules
the reprocessing runs under are not qualified (G07, mode M1).

The built class (WitnessBuilt) runs the frozen T07 binaries on fixtures 7003 and 7004 and needs two variables: HEP_ACTS_TRACKING_BUILD
(a folder with acts_tracking_driver and t07_cai_fixture_generator at their pinned SHA-256) and HEP_T07_CAI_RECORD (job 7546791's
cai-refit.log). Without them it skips; the job of record sets both and counts a skip as a failure.

Run from the plugin root: python -m unittest tests.contracts.test_t12_degeneracy -v
"""
from __future__ import annotations

import hashlib
import io
import json
import math
import os
import re
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "skills" / "hep-computing" / "scripts"))
sys.path.insert(0, str(ROOT / "adapters" / "timing-pid" / "assets" / "fixture_tools"))
import t10_a37  # noqa: E402
from contracts.conditions import payload_identity  # noqa: E402
from control_layer_support import derivation as dv  # noqa: E402
from tests.contracts import t12_degeneracy as harness  # noqa: E402

HARNESS = ROOT / "tests" / "contracts" / "t12_degeneracy.py"

# ---- t12-stage-plan.md, "Stage 6", fixed before the harness.
RELATIVE = 1e-12                 # t10_a37.GAUGE_TOLERANCE (t10-timing-stage-plan.md section 6.1)
CONVERGED = 1e-20                # t10_a37.CONVERGED
G_TRUE, E_TRUE, OBSERVATIONS = 1.25, 2.0, 6
GAUGE = 3.0
GAINS = [1.0 + 0.05 * c for c in range(8)]
ENERGIES = [1.0, 2.0, 3.0, 5.0, 8.0]
REFERENCE_EVENT = 2
CONSTRAINT = "constraint.external-energy-reference"
GAIN_MODE = "mode.global-gain-scale"
GXE_PLANTS = {"report-absolute": ["G2"], "holdout-as-validation": ["G4"], "constraint-as-validation": ["G6"],
              "unnamed-constraint": ["G5", "G6"]}

K_WEAK, WEAK_N_SIGMA = 4.5, 4.5          # CAI-T07-4 (test_acts_cai_refit.K_WEAK, WEAK_N_SIGMA)
STATED_SIGMA_QOP = 0.00412
DRIVER_SHA256 = "7556beb828f3a9029a79a34f41c938e7f9ff328281855800d21d655649ece958"      # Freeze B
GENERATOR_SHA256 = "f1c7309a804ba71a8e54a1ff55f16685a4255703142e130624fe290e77888931"   # job 7546791's build
T07_RECORD_SHA256 = "0f60e9ac0ebe9114c0ba1f64369926027b7b130d9c43884ddcd458bf73316a90"   # t10_a37.T07_LOG_SHA256
RATIO_PRECISION, CHI2_PRECISION = 1e-4, 1e-5
STEPS = ["nominal-alignment", "generate-7003", "refit-7003", "generate-7004", "refit-7004", "witness"]
SAGITTA_MODE = "mode.sagitta-like-deformation"
WITNESS_PLANTS = {"no-deformation": ["W4", "W5", "W6", "W8"], "visible-chi2": ["W4", "W5", "W6", "W8"],
                  "card-without-constraint": ["W7", "W8"], "constraint-as-validation": ["W7", "W8"], "reuse-across-data": ["W3"]}
WITNESS_CLAIMS = {"label": "synthetic", "quality": "none",
                  "a37": "weak-mode witness reproduced in a T12 reprocessing (identifiability); no alignment quality",
                  "control_rules": "not qualified (G07, mode M1)"}
NOT_SATISFYING = ("placeholder", "convergence", "same-type holdout")
CELL_LINE = re.compile(r"CAI-T07-4 cell charge ([+-]1) bending bin (\d+) tracks (\d+) and (\d+) change in q/p ([-+0-9.]+) per-track sigmas "
                       r"\(se [-+0-9.]+, sigma [-+0-9.]+ per GeV\), ([-+0-9.]+) stated sigmas; change in mean chi2/ndf ([-+0-9.]+) \(se ([-+0-9.]+)\)")


def relative(a, b) -> float:
    return abs(a - b) / max(abs(a), abs(b), 1e-300)


def run_cli(*arguments) -> tuple:
    finished = subprocess.run([sys.executable, str(HARNESS), *[str(a) for a in arguments]], capture_output=True, text=True, timeout=3600,
                              cwd=str(ROOT))
    lines = [line for line in finished.stdout.splitlines() if line.startswith("{")]
    return finished.returncode, (json.loads(lines[-1]) if lines else {"stderr": finished.stderr[-2000:]})


def t07_cells(text: str) -> dict:
    """CAI-T07-4's eight cells from T07's record, parsed here (not by the harness)."""
    cells = {}
    for match in CELL_LINE.finditer(text):
        charge, bending_bin, deformed, clean, ratio, stated, chi2, se = match.groups()
        cells[f"{int(charge):+d}/{int(bending_bin)}"] = {"tracks": [int(deformed), int(clean)], "ratio": float(ratio),
                                                          "ratio_stated": float(stated), "chi2_change": float(chi2), "chi2_se": float(se)}
    return cells


# ================================================================ T12-18: the g x E degeneracy

class GxeRecord(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rec = harness.gxe_run()
        cls.two = cls.rec["cases"]["two-parameter"]
        cls.form = cls.rec["cases"]["t10-form"]

    def test_g1_rank_without_and_with_the_named_constraint(self):
        self.assertEqual(self.two["parameters"], 2)
        self.assertEqual(self.two["rank"], {"without": 1, "with": 2})
        self.assertEqual(self.form["parameters"], 13)
        self.assertEqual(self.form["rank"], {"without": 12, "with": 13})
        # independently, with T10's own tools (the shared fixture form)
        self.assertEqual(t10_a37.exact_rank(t10_a37.gxe_design(1, 1) * OBSERVATIONS), 1)
        self.assertEqual(t10_a37.exact_rank(t10_a37.gxe_design(8, 5)), 12)
        self.assertEqual(t10_a37.exact_rank(t10_a37.gxe_design(8, 5) + [[0] * 8 + [int(j == REFERENCE_EVENT) for j in range(5)]]), 13)

    def test_g2_only_identifiable_combinations_are_reported_without_a_constraint(self):
        fit = self.two["fit"]
        self.assertEqual(set(fit["reported"]), {"gE"})
        self.assertLessEqual(relative(fit["reported"]["gE"], G_TRUE * E_TRUE), RELATIVE)
        self.assertEqual(fit["unidentified"], ["g", "E"])
        self.assertEqual(fit["gauge"], "g -> a g, E -> E / a")
        self.assertIsNone(fit["identified_by"])
        fit = self.form["fit"]
        self.assertEqual(set(fit["reported"]), {"ratios", "products"})
        for got, want in zip(fit["reported"]["ratios"], [g / GAINS[0] for g in GAINS], strict=True):
            self.assertLessEqual(relative(got, want), RELATIVE)
        for row, gain in zip(fit["reported"]["products"], GAINS, strict=True):
            for got, energy in zip(row, ENERGIES, strict=True):
                self.assertLessEqual(relative(got, gain * energy), RELATIVE)
        self.assertEqual(fit["unidentified"], ["g", "E"])
        self.assertIsNone(fit["identified_by"])

    def test_g3_two_gauges_converge_alike_so_convergence_identifies_nothing(self):
        for case in (self.two, self.form):
            gauges = case["gauges"]
            self.assertEqual(gauges["gauge"], GAUGE)
            self.assertLessEqual(gauges["largest_relative_y"], RELATIVE)
            self.assertEqual(len(gauges["residuals"]), 2)
            self.assertTrue(all(r <= CONVERGED for r in gauges["residuals"]), gauges)
            self.assertLessEqual(abs(gauges["scale_difference"] - math.log(GAUGE)), RELATIVE)
            self.assertLessEqual(gauges["reported_relative"], RELATIVE)

    def test_g4_a_same_type_holdout_closes_in_both_gauges_and_is_not_validation(self):
        for case in (self.two, self.form):
            self.assertEqual(len(case["holdout"]["residuals"]), 2)
            self.assertTrue(all(r <= CONVERGED for r in case["holdout"]["residuals"]), case["holdout"])
            # fix round 1, m2: the two holdout fits are in two gauges, ln g_0 apart by ln a
            self.assertEqual(len(case["holdout"]["ln_g0"]), 2)
            self.assertLessEqual(abs(case["holdout"]["ln_g0"][1] - case["holdout"]["ln_g0"][0] - math.log(GAUGE)), RELATIVE)
        # fix round 1, m1: a constraint the fit used identifies the scale and never validates it
        refused = {(claim["claim"], claim["by"]) for claim in self.rec["claims_refused"]}
        self.assertEqual(refused, {("absolute scale validated", "holdout"), ("absolute scale identified", "convergence"),
                                   ("absolute scale validated", CONSTRAINT)})
        accepted = [(claim["claim"], claim["by"]) for claim in self.rec["claims_judged"] if claim["accepted"]]
        self.assertEqual(accepted, [("absolute scale identified", CONSTRAINT)])
        self.assertEqual(self.rec["holdout_statement"], "same-type holdout: not validation (A37)")

    def test_g4_g5_the_assessment_reads_the_holdout_gauges_and_the_validated_claim(self):
        """Fix round 1 (m1, m2): each clause changed alone fails its expectation alone."""
        rec = json.loads(json.dumps(self.rec))
        rec["cases"]["t10-form"]["holdout"]["ln_g0"][1] = rec["cases"]["t10-form"]["holdout"]["ln_g0"][0]
        self.assertEqual(harness.assess_gxe(rec), ["G4"])
        rec = json.loads(json.dumps(self.rec))
        for claim in rec["claims_judged"]:
            if claim["claim"] == "absolute scale validated" and claim["by"] == CONSTRAINT:
                claim["accepted"] = True
        self.assertEqual(harness.assess_gxe(rec), ["G5"])
        judged = harness.judge_claims([{"claim": "absolute scale validated", "by": CONSTRAINT},
                                       {"claim": "absolute scale identified", "by": CONSTRAINT}], CONSTRAINT)
        self.assertEqual([claim["accepted"] for claim in judged], [False, True])

    def test_g5_only_a_named_external_constraint_identifies_g_and_e(self):
        fit = self.two["constrained"]
        self.assertEqual(set(fit["reported"]), {"gE", "g", "E"})
        self.assertLessEqual(relative(fit["reported"]["g"], G_TRUE), RELATIVE)
        self.assertLessEqual(relative(fit["reported"]["E"], E_TRUE), RELATIVE)
        self.assertEqual(fit["identified_by"], CONSTRAINT)
        self.assertEqual(fit["unidentified"], [])
        fit = self.form["constrained"]
        self.assertEqual(fit["identified_by"], CONSTRAINT)
        for got, want in zip(fit["reported"]["g"], GAINS, strict=True):
            self.assertLessEqual(relative(got, want), RELATIVE)
        for got, want in zip(fit["reported"]["E"], ENERGIES, strict=True):
            self.assertLessEqual(relative(got, want), RELATIVE)
        unnamed = harness.gxe_fit(1, 1, OBSERVATIONS, [G_TRUE], [E_TRUE], constraint="the energy is known")
        self.assertIsNone(unnamed["identified_by"])
        self.assertEqual(set(unnamed["reported"]), {"gE"})

    def test_g6_the_payload_sidecars_record_mode_and_constraint(self):
        free, bound = self.rec["sidecars"]["unconstrained"], self.rec["sidecars"]["constrained"]
        for sidecar in (free, bound):
            self.assertEqual(sidecar["schema"], "conditions-payload/1")
            self.assertEqual(sidecar["payload_id"], payload_identity(sidecar))
            self.assertNotIn(CONSTRAINT, sidecar["independent_validation"])
            self.assertFalse(any("holdout" in item for item in sidecar["independent_validation"]))
        self.assertEqual(free["unconstrained_modes"], [GAIN_MODE])
        self.assertEqual(free["constraints_used"], [])
        self.assertEqual(bound["unconstrained_modes"], [])
        self.assertEqual(bound["constraints_used"], [CONSTRAINT])
        self.assertEqual(self.rec["validation_claim_codes"], ["conditions.constraint_as_validation"])

    def test_the_honest_record_meets_every_expectation(self):
        self.assertEqual(harness.assess_gxe(self.rec), [])
        self.assertEqual(self.rec["claims"]["quality"], "none")

    def test_each_planted_defect_fails_exactly_its_set(self):
        for plant, expected in GXE_PLANTS.items():
            with self.subTest(plant=plant):
                self.assertEqual(harness.assess_gxe(harness.gxe_run(plant)), expected)

    def test_a_missing_field_fails_its_expectation(self):
        rec = json.loads(json.dumps(self.rec))
        del rec["cases"]["two-parameter"]["holdout"]
        self.assertEqual(harness.assess_gxe(rec), ["G4"])


class GxeCommandLine(unittest.TestCase):
    def test_exit_codes(self):
        with tempfile.TemporaryDirectory() as folder:
            out = Path(folder) / "gxe.json"
            code, result = run_cli("gxe", "--out", out)
            self.assertEqual((code, result["status"]), (0, "ok"), result)
            self.assertEqual(result["sha256"], hashlib.sha256(out.read_bytes()).hexdigest())
            self.assertEqual(json.loads(out.read_text())["assessment"], {"failed": []})
            code, result = run_cli("gxe", "--out", out)
            self.assertEqual((code, result["status"]), (2, "rejected"))          # a record is never overwritten
            code, result = run_cli("gxe", "--plant", "report-absolute", "--out", Path(folder) / "plant.json")
            self.assertEqual((code, result["status"], result["failed"]), (1, "failed", ["G2"]))
            code, result = run_cli("gxe", "--plant", "nonsense", "--out", Path(folder) / "x.json")
            self.assertEqual((code, result["status"]), (2, "rejected"))
            code, result = run_cli("gxe", "--out", Path(folder) / "missing" / "x.json")
            self.assertEqual((code, result["status"]), (2, "rejected"))

    def test_a_crash_is_incomplete(self):
        with tempfile.TemporaryDirectory() as folder, redirect_stdout(io.StringIO()) as printed:
            original = harness.gxe_run
            harness.gxe_run = lambda plant=None: (_ for _ in ()).throw(RuntimeError("boom"))
            try:
                code = harness.main(["gxe", "--out", str(Path(folder) / "x.json")])
            finally:
                harness.gxe_run = original
        self.assertEqual(code, 3)
        self.assertEqual(json.loads(printed.getvalue())["status"], "incomplete")


# ================================================================ T12-19: the method card

class MethodCard(unittest.TestCase):
    def test_w7_the_card_lists_the_sagitta_mode_with_its_named_constraint(self):
        card = harness.method_card()
        self.assertEqual(card["format"], "t12-method-card/1")
        modes = {mode["mode"]: mode for mode in card["unconstrained_modes"]}
        self.assertIn(SAGITTA_MODE, modes)
        mode = modes[SAGITTA_MODE]
        self.assertIn("sagitta-like deformation", mode["description"])
        self.assertIn("constraint.vertex-or-beam", [item["id"] for item in mode["constraining_information"]])
        self.assertTrue(mode["independent_observables"])
        self.assertEqual(mode["constraints_used"], [])
        self.assertIn("T12", mode["witness"])
        for words in NOT_SATISFYING:
            self.assertTrue(any(words in item for item in card["not_satisfying_a37"]), words)
        self.assertEqual(harness.card_check(card), ("pass", None))

    def test_the_card_rules_refuse_each_broken_card(self):
        def broken(change):
            card = harness.method_card()
            change(next(m for m in card["unconstrained_modes"] if m["mode"] == SAGITTA_MODE))
            return harness.card_check(card)
        cases = {
            "no constraint": lambda m: m.update(constraining_information=[]),
            "no observable": lambda m: m.update(independent_observables=[]),
            "no witness": lambda m: m.update(witness=""),
            "constraint as observable": lambda m: m["independent_observables"].append(dict(m["constraining_information"][0])),
            "used constraint as observable": lambda m: m.update(constraints_used=[m["independent_observables"][0]["id"]]),
            "foreign constraint used": lambda m: m.update(constraints_used=["constraint.not-this-mode"]),
        }
        for name, change in cases.items():
            with self.subTest(case=name):
                result, reason = broken(change)
                self.assertEqual(result, "fail")
                self.assertTrue(reason)
        # the sagitta-like mode must be listed: a card whose only mode is another, otherwise valid, is refused (mutation round 1)
        card = harness.method_card()
        card["unconstrained_modes"][0]["mode"] = "mode.some-other-mode"
        self.assertEqual(harness.card_check(card)[0], "fail")
        card = harness.method_card()
        card["unconstrained_modes"][0]["description"] = "a curvature offset"
        self.assertEqual(harness.card_check(card)[0], "fail")


# ================================================================ T12-19: the reprocessing, with the toy executor (plumbing only)

class WitnessToy(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.executor = harness.ToyExecutor(seed=61)
        cls.rec = harness.Reprocessing(cls.executor).execute()

    def test_the_contract_is_valid_and_has_no_round_family(self):
        spec = harness.witness_contract()
        log = dv.Log()
        log.append("session", "C", mode="M1")
        log.append("contract", "agent", spec=spec)
        self.assertTrue(dv.has_contract(log))
        self.assertEqual(spec["families"], {})
        self.assertEqual(spec["steps"]["witness"].upstream, ("refit-7004", "refit-7003"))
        self.assertTrue(spec["steps"]["witness"].checked)
        self.assertEqual(len(spec["steps"]["witness"].required), 2)
        self.assertEqual({did: d.step for did, d in spec["deliverables"].items()}, {"weak-mode-witness": "witness"})
        self.assertEqual(spec["deliverables"]["weak-mode-witness"].target, "T2")

    def test_an_honest_toy_run_fails_only_what_needs_the_binaries_and_the_record(self):
        self.assertEqual(harness.assess_witness(self.rec), ["W1", "W5"])
        self.assertEqual(self.rec["executor"], "toy")
        self.assertIsNone(self.rec["t07_record"])

    def test_w2_records_and_order(self):
        rec = self.rec
        self.assertEqual(rec["order"], STEPS)
        self.assertTrue(all(step["computed"] == 1 for step in rec["steps"].values()))
        for step, fixture_id in (("generate-7003", 7003), ("generate-7004", 7004)):
            fixture = rec["fixtures"][step]
            self.assertEqual((fixture["fixture_id"], fixture["block"], fixture["strata"], fixture["events"]), (fixture_id, 1, [0, 1, 2, 3], 3000))
        nominal = rec["payload"]
        self.assertEqual(nominal["origin"], "nominal")
        self.assertEqual(nominal["kind"], "alignment-parameters")
        for step in ("refit-7003", "refit-7004"):
            product = rec["products"][step]
            self.assertEqual(product["conditions_used"], [{"slot": "alignment", "tag": nominal["tag"], "payload_id": nominal["payload_id"],
                                                           "origin": "nominal", "round": None}])
            self.assertEqual(product["check_used_errors"], [])
            self.assertEqual(product["failed"], [])
            self.assertEqual(product["tracks"], 12000)
            # fix round 1, m3: what the driver applied, per stratum, from the native header (none: no payload argument)
            self.assertEqual(product["alignment_header"], [None, None, None, None])
            self.assertEqual(product["applied"], "driver nominal geometry, no payload argument")
        # fix round 1, n2: the nominal sidecar's planes come from the nominal geometry text
        planes = int(next(line for line in harness.alignment_payload.nominal_geometry_text().splitlines() if line.startswith("planes ")).split()[1])
        self.assertEqual([d["structure"] for d in nominal["alignment"]["degrees_of_freedom"]], [f"plane-{p}" for p in range(1, planes + 1)])
        self.assertNotEqual(rec["steps"]["refit-7003"]["consumed"]["generate-7003"], rec["steps"]["refit-7004"]["consumed"]["generate-7004"])

    def test_w3_the_cache_keys_on_data_and_payload(self):
        self.assertEqual(self.rec["cache"], [{"for": "refit-7004", "cached": "refit-7003", "same_input": False, "conditions_reuse": True,
                                              "same_native": True, "hit": False, "acted": None}])
        control = self.rec["reuse_control"]
        self.assertTrue(control["decision"]["hit"])
        self.assertEqual(control["decision"]["acted"], "reused")
        self.assertEqual(control["state"], "reused")
        self.assertEqual(control["source"], self.rec["steps"]["refit-7004"]["artifact"])
        self.assertIn("reuse source is not a usable, current output", self.rec["reuse_across_steps"])

    def test_m4_a_changed_native_identity_is_no_hit(self):
        """Fix round 1, m4: the native identity is read afresh at each step and keys the cache."""
        executor = harness.ToyExecutor(seed=61)
        run = harness.Reprocessing(executor)
        run.execute()
        self.assertEqual(len(run.cache_lookup("refit-7004")), 1)      # unchanged identity: a hit on refit-7004's own product
        executor.identity = {"driver_sha256": "1" * 64, "generator_sha256": None}
        before = len(run.cache)
        self.assertEqual(run.cache_lookup("refit-7004"), [])
        own = [entry for entry in run.cache[before:] if entry["cached"] == "refit-7004"]
        self.assertEqual([(entry["same_input"], entry["conditions_reuse"], entry["same_native"], entry["hit"]) for entry in own],
                         [(True, True, False, False)])

    def test_w4_w6_w8_on_toys(self):
        cells = self.rec["witness"]["cells"]
        self.assertEqual(sorted(cells), sorted(f"{q:+d}/{b}" for q in (-1, 1) for b in range(4)))
        for key, cell in cells.items():
            with self.subTest(cell=key):
                self.assertGreaterEqual(cell["ratio"], K_WEAK)
                self.assertGreaterEqual(cell["ratio_stated"], K_WEAK)
                self.assertLessEqual(abs(cell["chi2_change"]), WEAK_N_SIGMA * cell["chi2_se"])
        self.assertEqual(self.rec["chi2_judge"]["result"], "pass")
        self.assertEqual({step: entry["label"] for step, entry in self.rec["steps"].items()}, {step: "ok" for step in STEPS})
        self.assertEqual(self.rec["published"], {"weak-mode-witness": self.rec["steps"]["witness"]["artifact"]})
        self.assertEqual(self.rec["claims"], WITNESS_CLAIMS)
        self.assertEqual({k: v["result"] for k, v in self.rec["checks"].items()}, {"weak-mode": "pass", "card": "pass"})

    def test_the_cells_are_t07s_arithmetic(self):
        """The witness cells are weak_mode_self_check's (imported from T07's test module), not a new formula."""
        from tests.adapters import test_acts_cai_refit as t07
        deformed, clean = self.executor.arrays("cai-sagitta"), self.executor.arrays("cai-clean")
        verdict = t07.weak_mode_self_check(deformed, clean)
        for (charge, bending_bin), cell in verdict["cells"].items():
            mine = self.rec["witness"]["cells"][f"{charge:+d}/{bending_bin}"]
            self.assertEqual(mine["ratio"], cell["ratio"])
            self.assertEqual(mine["chi2_change"], cell["chi2_change"])
        self.assertEqual((t07.K_WEAK, t07.WEAK_N_SIGMA), (K_WEAK, WEAK_N_SIGMA))

    def test_the_assessment_reads_w1_and_w8_clause_by_clause(self):
        """Mutation round 1: a toy record given the pinned native identities meets W1; each clause, changed alone, fails it alone."""
        native = {"driver_sha256": DRIVER_SHA256, "generator_sha256": GENERATOR_SHA256}

        def pinned():
            rec = json.loads(json.dumps(self.rec))
            rec["native"].update(native)
            for step in ("generate-7003", "refit-7003", "generate-7004", "refit-7004"):
                rec["steps"][step]["native"] = dict(native)
            return rec
        self.assertEqual(harness.assess_witness(pinned()), ["W5"])
        rec = pinned()
        rec["native"]["geometry_id"] = "0" * 64
        self.assertEqual(harness.assess_witness(rec), ["W1", "W5"])
        rec = pinned()
        rec["steps"]["refit-7004"]["native"]["driver_sha256"] = "0" * 64
        self.assertEqual(harness.assess_witness(rec), ["W1", "W5"])
        rec = pinned()
        rec["steps"]["refit-7003"]["label"] = "unchecked"
        self.assertEqual(harness.assess_witness(rec), ["W5", "W8"])
        rec = pinned()
        rec["products"]["refit-7004"]["alignment_header"][2] = {"content_sha256": "0" * 64}   # fix round 1, m3
        self.assertEqual(harness.assess_witness(rec), ["W2", "W5"])
        rec = pinned()
        rec["claims"]["quality"] = "alignment validated"
        self.assertEqual(harness.assess_witness(rec), ["W5", "W8"])

    def test_w5_reads_the_zero_payload_line_of_t07s_record(self):
        """Fix round 1 (m3, mutation round 2): a toy record given a T07 record equal to its own cells meets W5 unless the record lacks
        T07's zero-payload line."""
        rec = json.loads(json.dumps(self.rec))
        rec["t07_record"] = {"sha256": T07_RECORD_SHA256, "zero_payload_equal": True,
                             "cells": {key: {name: cell[name] for name in ("tracks", "ratio", "ratio_stated", "chi2_change", "chi2_se")}
                                       for key, cell in rec["witness"]["cells"].items()}}
        self.assertEqual(harness.assess_witness(rec), ["W1"])
        rec["t07_record"]["zero_payload_equal"] = False
        self.assertEqual(harness.assess_witness(rec), ["W1", "W5"])
        line = "CAI-T07-3 zero payload through the placement route: /1 records equal to the plain geometry's (asserted)\n"
        self.assertTrue(harness.parse_t07_record(line)["zero_payload_equal"])
        self.assertFalse(harness.parse_t07_record(line.replace("equal", "DIFFERENT"))["zero_payload_equal"])

    def test_each_planted_defect_fails_exactly_its_set(self):
        for plant, expected in WITNESS_PLANTS.items():
            with self.subTest(plant=plant):
                rec = harness.Reprocessing(self.executor, plant).execute()
                self.assertEqual(harness.assess_witness(rec), sorted(set(expected) | {"W1", "W5"}))
                if "W8" in expected:
                    self.assertEqual(rec["steps"]["witness"]["label"], "held")
                    self.assertEqual(rec["published"], {})
                    self.assertIn("deliverable not met", rec["publish_refused"]["weak-mode-witness"])


class WitnessCommandLine(unittest.TestCase):
    """Refusals before any step (rejected, exit 2)."""

    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        base = Path(self.folder.name)
        self.build, self.work, self.record = base / "build", base / "work", base / "cai-refit.log"
        self.build.mkdir()
        self.work.mkdir()
        for name in ("acts_tracking_driver", "t07_cai_fixture_generator"):
            (self.build / name).write_bytes(b"#!/bin/sh\nexit 0\n")
            (self.build / name).chmod(0o755)
        self.record.write_text("not T07's record\n")

    def arguments(self, **change):
        values = {"--build": self.build, "--t07-record": self.record, "--work": self.work, "--out": Path(self.folder.name) / "w.json"}
        values.update(change)
        return ["witness"] + [str(item) for pair in values.items() for item in pair]

    def test_binaries_that_are_not_the_pinned_bytes_are_refused(self):
        code, result = run_cli(*self.arguments())
        self.assertEqual((code, result["status"]), (2, "rejected"), result)
        self.assertIn("sha256", result["reason"].lower())
        self.assertEqual(list(self.work.iterdir()), [])

    def test_other_refusals(self):
        (self.work / "left").write_text("x")
        self.assertEqual(run_cli(*self.arguments())[0], 2)                                       # a work folder that is not empty
        self.assertEqual(run_cli(*self.arguments(**{"--build": Path(self.folder.name) / "nowhere"}))[0], 2)
        (Path(self.folder.name) / "w.json").write_text("{}")
        self.assertEqual(run_cli(*self.arguments())[0], 2)                                       # an output that exists
        self.assertEqual(run_cli(*(self.arguments() + ["--plant", "nonsense"]))[0], 2)


# ================================================================ T12-19: the reprocessing of 7003 and 7004, built

BUILD = os.environ.get("HEP_ACTS_TRACKING_BUILD", "")
RECORD = os.environ.get("HEP_T07_CAI_RECORD", "")
BUILT = bool(BUILD) and (Path(BUILD) / "acts_tracking_driver").is_file() and (Path(BUILD) / "t07_cai_fixture_generator").is_file() \
    and bool(RECORD) and Path(RECORD).is_file()
NOT_BUILT = "HEP_ACTS_TRACKING_BUILD and HEP_T07_CAI_RECORD name no frozen binaries and T07 record: the job of record runs this"


@unittest.skipUnless(BUILT, NOT_BUILT)
class WitnessBuilt(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.folder = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.folder.cleanup)
        base = Path(cls.folder.name)
        (base / "work").mkdir()
        cls.out = base / "witness.json"
        cls.code, cls.result = run_cli("witness", "--build", BUILD, "--t07-record", RECORD, "--work", base / "work", "--out", cls.out)
        cls.rec = json.loads(cls.out.read_text()) if cls.out.exists() else {}
        cls.t07 = t07_cells(Path(RECORD).read_text(encoding="utf-8"))
        print(f"T12-19 witness command exit {cls.code}: {json.dumps(cls.result, sort_keys=True)[:600]}", flush=True)
        for key, cell in sorted(cls.rec.get("witness", {}).get("cells", {}).items()):
            print(f"T12-19 cell {key} tracks {cell['tracks']} change in q/p {cell['ratio']:.4f} per-track sigmas, {cell['ratio_stated']:.4f} stated; "
                  f"change in mean chi2/ndf {cell['chi2_change']:+.5f} (se {cell['chi2_se']:.5f}); T07 record {cls.t07.get(key)}", flush=True)

    def test_the_command_meets_every_expectation(self):
        self.assertEqual((self.code, self.result.get("status")), (0, "ok"), self.result)
        self.assertEqual(self.rec["assessment"], {"failed": []})
        self.assertEqual(self.rec["executor"], "native")

    def test_w1_native_identity(self):
        native = self.rec["native"]
        self.assertEqual((native["driver_sha256"], native["generator_sha256"]), (DRIVER_SHA256, GENERATOR_SHA256))
        self.assertEqual(hashlib.sha256((Path(BUILD) / "acts_tracking_driver").read_bytes()).hexdigest(), DRIVER_SHA256)
        self.assertEqual(native["geometry_id"], self.rec["payload"]["derived_against"]["geometry_id"])
        for step in ("generate-7003", "refit-7003", "generate-7004", "refit-7004"):
            self.assertEqual(self.rec["steps"][step]["native"], {"driver_sha256": DRIVER_SHA256, "generator_sha256": GENERATOR_SHA256})

    def test_w4_w5_the_weak_mode_reproduces_t07s_record(self):
        self.assertEqual(hashlib.sha256(Path(RECORD).read_bytes()).hexdigest(), T07_RECORD_SHA256)
        self.assertEqual(len(self.t07), 8)
        cells = self.rec["witness"]["cells"]
        self.assertEqual(sorted(cells), sorted(self.t07))
        for key, want in self.t07.items():
            got = cells[key]
            with self.subTest(cell=key):
                self.assertEqual(got["tracks"], want["tracks"])
                self.assertLessEqual(abs(got["ratio"] - want["ratio"]), RATIO_PRECISION)
                self.assertLessEqual(abs(got["ratio_stated"] - want["ratio_stated"]), RATIO_PRECISION)
                self.assertLessEqual(abs(got["chi2_change"] - want["chi2_change"]), CHI2_PRECISION)
                self.assertLessEqual(abs(got["chi2_se"] - want["chi2_se"]), CHI2_PRECISION)
                self.assertGreaterEqual(got["ratio"], K_WEAK)
                self.assertGreaterEqual(got["ratio_stated"], K_WEAK)
                self.assertLessEqual(abs(got["chi2_change"]), WEAK_N_SIGMA * got["chi2_se"])

    def test_m3_the_t07_record_shows_the_zero_payload_equal_to_the_plain_geometry(self):
        self.assertTrue(self.rec["t07_record"]["zero_payload_equal"])
        for step in ("refit-7003", "refit-7004"):
            self.assertEqual(self.rec["products"][step]["alignment_header"], [None, None, None, None])

    def test_w6_chi2_is_blind_to_the_mode(self):
        judge = self.rec["chi2_judge"]
        self.assertEqual(judge["result"], "pass")
        self.assertLessEqual(abs(judge["chi2_change"]), WEAK_N_SIGMA * judge["chi2_se"])
        self.assertTrue(all(cell["ratio"] >= K_WEAK for cell in self.rec["witness"]["cells"].values()))

    def test_w2_every_track_is_fitted_and_the_records_hold(self):
        for step in ("refit-7003", "refit-7004"):
            product = self.rec["products"][step]
            self.assertEqual((product["failed"], product["tracks"], product["check_used_errors"]), ([], 12000, []))
        self.assertEqual(self.rec["order"], STEPS)

    def test_a_planted_defect_on_the_native_run_is_detected(self):
        base = Path(self.folder.name)
        (base / "work-plant").mkdir()
        code, result = run_cli("witness", "--build", BUILD, "--t07-record", RECORD, "--work", base / "work-plant", "--plant", "no-deformation",
                               "--out", base / "plant.json")
        self.assertEqual((code, result["status"], result["failed"]), (1, "failed", WITNESS_PLANTS["no-deformation"]))


if __name__ == "__main__":
    unittest.main()
