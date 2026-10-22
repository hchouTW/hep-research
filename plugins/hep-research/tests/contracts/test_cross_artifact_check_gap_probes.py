"""Gap probes G1-G22 of the cross-artifact check architecture (docs/dev/cross-artifact-check/cross-artifact-check-architecture.en.md,
section 6). Each probe states the intended behaviour. Gaps fixed in Phase 0 (G10, G11, G18, the diagnostic part of
G19, G20) pass; gaps scheduled for Phase 2 are expected failures until their fix lands (an unexpected success fails
the suite, so a fix must flip its probe); assurance-plane gaps (G9) and the classification item G21 are skipped with
their reason. Rebuilt on 2026-10-22 from the gap register: the original probe file of the architecture review is not
in this repository. Synthetic and public example content only."""
import copy
import json
import math
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests" / "contracts"))
import analysis_check_cases as cases  # noqa: E402
import analysis_check_runs as runs  # noqa: E402

PHASE2 = unittest.expectedFailure  # scheduled for Phase 2 (R2/R3); the fix flips the probe


def ac():
    from contracts import analysis_check
    return analysis_check


def report(bundle: Path, root: Path, extra_diags=(), **kw) -> dict:
    view, diags = ac().load_subject(bundle, root)
    return ac().evaluate(view, list(diags) + list(extra_diags), **kw)


def by_rule(rep: dict, rule_id: str) -> list[dict]:
    return [o for o in rep["obligations"] if o["rule_id"] == rule_id]


def exposure_table(values_parent, values_acc, values_live, tolerance=None) -> dict:
    doc = {"factor_table_version": "1.0.0", "factors": {"exposure": {"values": values_parent},
                                                        "acceptance": {"values": values_acc},
                                                        "livetime": {"values": values_live}}}
    if tolerance is not None:
        doc["tolerance"] = {"relative": tolerance}
    return doc


def with_factor_table(doc: dict, key: str = "exposure"):
    def v(c):
        c.add("calibration", "exp-factors", "exposure-factors.json", doc)
        c.context["recipe_instances"][0]["calibrations"] = {key: "exp-factors"}
    return v


class Probe(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.addCleanup(self.td.cleanup)
        self.n = 0

    def root(self) -> Path:
        self.n += 1
        return Path(self.td.name) / f"p{self.n}"

    def positive(self, variant=None, **kw) -> dict:
        r = self.root()
        return report(cases.positive_case(r, variant), r, **kw)


class ChainProbes(Probe):
    def test_baseline_positive_case_is_complete(self):
        # the reference the probes perturb: the reduced positive case is complete and consistent
        rep = self.positive()
        self.assertEqual((rep["status"], rep["consistency"]), ("complete", "consistent"))

    @PHASE2
    def test_g1_fewer_spec_corrections_do_not_complete(self):
        # G1 (DR-8, V86): a recipe step realizes selection efficiency the spec no longer describes: r-real.undescribed
        def drop(c):
            c.doc("spec")["extension"]["corrections"] = [x for x in c.doc("spec")["extension"]["corrections"]
                                                         if x["effect_id"] != "selection_efficiency"]
        rep = self.positive(drop)
        self.assertNotEqual(rep["status"], "complete", "an undescribed applied correction leaves the check complete")

    @PHASE2
    def test_g2_required_false_cannot_hide_a_violation(self):
        # G2 (DR-2, V78): a root marked required:false whose output conflicts is not silently not_applicable
        def hide(c):
            c.context["roots"][0]["quantity"] = "integrated_flux"
            c.context["roots"][0]["required"] = False
        rep = self.positive(hide)
        self.assertEqual(by_rule(rep, "r-inv.root")[0]["state"], "violated")

    @PHASE2
    def test_g4_a_factor_table_does_not_choose_its_tolerance(self):
        # G4 (DR-6, V79): exposure 3.0 against acceptance x livetime 2.0 is a violation whatever tolerance the table sets
        rep = self.positive(with_factor_table(exposure_table([1.0, 3.0], [0.5, 1.0], [2.0, 2.0], tolerance=0.6)))
        self.assertEqual(by_rule(rep, "r-comp.factor_values")[0]["state"], "violated")

    def test_g4_reference_default_tolerance_finds_the_violation(self):
        rep = self.positive(with_factor_table(exposure_table([1.0, 3.0], [0.5, 1.0], [2.0, 2.0])))
        self.assertEqual(by_rule(rep, "r-comp.factor_values")[0]["state"], "violated")

    @PHASE2
    def test_g14_factor_obligation_does_not_depend_on_the_mapping_key(self):
        # G14 (V87): a factor table bound under a child key (acceptance) still produces the factor obligation
        rep = self.positive(with_factor_table(exposure_table([1.0, 3.0], [0.5, 1.0], [2.0, 2.0]), key="acceptance"))
        self.assertTrue(by_rule(rep, "r-comp.factor_values"), "no factor obligation for a table under a child key")

    @PHASE2
    def test_g15_two_bundle_coverage_contracts_for_one_table(self):
        # G15 (V81): two different bundle coverage contracts for one table are input-invalid, not first-wins
        def two(c):
            cases.custom_table(c, "differential-flux-x", None, None)
            second = copy.deepcopy(c.doc("differential-flux-x-coverage"))
            second["operators"][0]["covers"] = []
            c.add("coverage-contract", "differential-flux-x-coverage-2", "differential-flux-x.coverage-2.json", second)
        rep = self.positive(two)
        self.assertEqual(rep["input_validity"], "invalid", [d["code"] for d in rep["input_diagnostics"]])

    @PHASE2
    def test_g16_a_nan_tolerance_is_input_invalid(self):
        # G16 (V79): a NaN tolerance makes every comparison false; it must not yield satisfied
        rep = self.positive(with_factor_table(exposure_table([1.0, 3.0], [0.5, 1.0], [2.0, 2.0], tolerance="nan")))
        self.assertNotEqual(by_rule(rep, "r-comp.factor_values")[0]["state"], "satisfied")

    @PHASE2
    def test_g17_exclusion_does_not_depend_on_declaration_order(self):
        # G17 (V77): one contradicting and one exclusive partition declaration for the same scopes: same answer both ways
        from contracts.analysis_checks import rules
        a, b = "source:x/sel:1", "source:x/sel:2"
        contra = {"declaration_id": "d-contra", "type": "partition_exclusive",
                  "content": {"subsets": [{"scope": a, "selection": "s"}, {"scope": b, "selection": "s"}]}}
        excl = {"declaration_id": "d-excl", "type": "partition_exclusive",
                "content": {"subsets": [{"scope": a, "selection": "s1"}, {"scope": b, "selection": "s2"}]}}

        class Env:
            def __init__(self, decls):
                self._d = decls

            def decls(self, dtype):
                return [d for d in self._d if d["type"] == dtype]
        first = rules._exclusion(Env([contra, excl]), a, b)[0]
        second = rules._exclusion(Env([excl, contra]), a, b)[0]
        self.assertEqual(first, second)

    @PHASE2
    def test_g22_freeze_refuses_an_empty_or_placeholder_unit(self):
        # G22 (V89): a root's unit must be stated; freeze refuses an empty or placeholder unit
        from contracts.analysis_bundle import BundleRefused
        for unit in ("", "TODO"):
            def v(c, unit=unit):
                c.context["roots"][0]["unit"] = unit
            with self.subTest(unit=unit), self.assertRaises(BundleRefused):
                cases.positive_case(self.root(), v)


class RatioProbes(Probe):
    @PHASE2
    def test_g3_validation_record_order_does_not_decide(self):
        # G3 (V77): an agreeing and a contradicting validation record give the same outcome whatever their item IDs
        def two(first_id, second_id):
            def v(c):
                rec = copy.deepcopy(c.doc("vr-selection"))
                c.remove("vr-selection")
                c.add("validation-record", first_id, f"{first_id}.json", rec)
                bad = copy.deepcopy(rec)
                bad["claim"]["relation"] = "fully_correlated"
                c.add("validation-record", second_id, f"{second_id}.json", bad)
            return v
        states = []
        for ids in (("vr-a", "vr-b"), ("vr-b", "vr-a")):
            r = self.root()
            rep = report(cases.ratio_case(r, two(*ids)), r)
            states.append(by_rule(rep, "r-ratio.correlation")[0]["state"])
        self.assertEqual(states[0], states[1], states)


class ModelProbes(Probe):
    def model(self, variant):
        r = self.root()
        return report(cases.model_case(r, variant), r)

    @PHASE2
    def test_g5_a_copied_observation_file_is_the_same_observation(self):
        # G5 (DR-3, V85): a byte copy of the auxiliary-input file bound under a second aux_id is the same observation
        def copy_file(c):
            card = c.doc("card-sr-cr")
            card["samples"][2]["modifiers"][1] = {"type": "constrained-normalization", "parameter": "lumi_cr"}
            card["constraints"].append({"parameter": "lumi_cr", "kind": "auxiliary-measurement", "aux_id": "lumi-copy",
                                        "form": "gaussian", "width": 0.02})
            c.add("calibration", "aux-copy", "aux/inputs-copy.json", copy.deepcopy(cases.OBS))
            c.context["bindings"].append(cases.observes("obs-copy", "sr-cr", "lumi-copy", item="aux-copy"))
        rep = self.model(copy_file)
        self.assertEqual(next(o for o in rep["obligations"] if o["obligation_id"] == "r-aux.use:fit#sr-cr/lumi-copy")["state"],
                         "violated")

    @PHASE2
    def test_g12_shared_parameters_within_one_model_do_not_hide_v07(self):
        # G12 (V80): sharing two parameters of one model merges two constraint terms and hides a repeated observation
        def hide(c):
            card = c.doc("card-sr-cr")
            card["samples"][2]["modifiers"][1] = {"type": "constrained-normalization", "parameter": "lumi_cr"}
            card["constraints"].append({"parameter": "lumi_cr", "kind": "auxiliary-measurement", "aux_id": "lumi-copy",
                                        "form": "gaussian", "width": 0.02})
            c.context["bindings"].append(cases.observes("obs-copy", "sr-cr", "lumi-copy"))
            c.context["evaluations"][0]["shared_parameters"] = [
                {"parameter_id": "lumi", "members": [{"model": "sr-cr", "parameter": "lumi"},
                                                     {"model": "sr-cr", "parameter": "lumi_cr"}]}]
        try:
            rep = self.model(hide)
        except Exception:  # noqa: BLE001  refused at freeze: the intended input-invalid outcome
            return
        self.assertNotEqual(rep["status"], "complete")


class RunProbes(Probe):
    def blinded_spec(self, c):
        c.doc("spec")["extension"]["blinding"] = {"blinded": True}

    @PHASE2
    def test_g6_campaign_closure_reaches_the_analysis(self):
        # G6 (V82): a campaign whose inputs include no analysis item is not campaign-recorded for the analysis
        post = runs.run_campaign(self.root())
        rep = post.check()
        self.assertEqual(by_rule(rep, "r-run.campaign")[0]["state"], "unverified")

    @PHASE2
    def test_g7_a_self_reported_synthetic_label_is_not_blinding_permission(self):
        # G7 (DR-7, V83): a blinded spec's result whose only permission is its own 'synthetic' label is unverified
        post = runs.run_chain(self.root(), spec_variant=self.blinded_spec)
        rep = post.check()
        self.assertEqual(by_rule(rep, "r-run.blinding")[0]["state"], "unverified")

    @PHASE2
    def test_g8_a_self_declared_person_keeps_the_declaration_flag(self):
        # G8 (DR-1, V88): asserted_by.kind 'person' written by the agent does not remove the declaration flag
        def person(post):
            post.binding["asserted_by"] = {"kind": "person", "id": "someone"}
        rep = runs.run_chain(self.root(), person).check()
        self.assertTrue(by_rule(rep, "r-run.binding")[0]["declaration_based"])

    @unittest.skip("G9 is an assurance-plane gap (section 5.1): design only until its preconditions hold")
    def test_g9_hand_edited_result_binding_section(self):
        pass

    @PHASE2
    def test_g13_project_blinded_list_applies_without_the_spec_flag(self):
        # G13 (DR-9, V84): the project's blinded list names the spec by artifact_id; blinding applies even though the
        # spec's own flag says it is not blinded
        def unblinded(c):
            c.doc("spec")["extension"]["blinding"] = {"blinded": False}
        post = runs.run_chain(self.root(), spec_variant=unblinded, status=("observed",))
        spec_id = json.loads((post.root / "spec.json").read_text())["artifact_id"]
        rep = post.check(project={"blinded": [spec_id], "allowed_outputs": []})
        self.assertNotEqual(by_rule(rep, "r-run.blinding")[0]["state"], "not_applicable")


class Phase0Probes(Probe):
    """Fixed in Phase 0 (R1); these pass."""

    def test_g10_checker_identity_covers_loaded_modules(self):
        # G10/A1 (V74): the checker identity names every plugin module the check loaded, not a fixed list
        self.positive()
        files = ac().checker_identity()["files"]
        for f in ("contracts/schema.py", "contracts/analysis_bundle.py", "contracts/release_manifest.py",
                  "core/protected/identity.py"):
            self.assertIn(f, files)
        self.assertNotEqual(ac().generator_code_digest(), ac()._file_sha("contracts/analysis_checks/obligations.py"))

    def test_g11_dropped_report_obligation_is_refused(self):
        # G11 (V75): a report with an obligation dropped (summary recomputed) no longer matches the frozen inventory
        from contracts.analysis_checks.outcomes import formal_view, summarize
        from contracts.permit import cheap_refusals
        r = self.root()
        bundle_path = cases.positive_case(r)
        rep = report(bundle_path, r)
        bundle = json.loads(bundle_path.read_text())
        self.assertEqual(cheap_refusals(rep, bundle, r, "$"), [])
        edited = copy.deepcopy(rep)
        edited["obligations"] = edited["obligations"][1:]
        s = summarize(edited["obligations"], True)
        edited.update(coverage=s["coverage"], consistency=s["consistency"], counts=s["counts"],
                      formal_use_view=formal_view(edited["obligations"], True))
        codes = [x["code"] for x in cheap_refusals(edited, bundle, r, "$")]
        self.assertIn("permit.report_inventory_mismatch", codes)

    def test_g18_rule_versions_are_guarded(self):
        # G18 (V72): an obligation of a rule version this checker does not implement is never evaluated
        from contracts.analysis_checks import rules
        r = self.root()
        view, _ = ac().load_subject(cases.positive_case(r), r)
        ob = dict(view["context"]["obligations"]["items"][0], rule_version="9.9.9")
        out = rules.evaluate(view, [ob])[0]
        self.assertEqual((out["state"], out["reason"]), ("unverified", "check.rule_not_run"))
        self.assertIn("9.9.9", out["message"])

    def test_g19_drift_and_forged_suite_are_refused(self):
        # G19 diagnostic part (V75): lock differences and a suite other than the frozen one are cheap refusals
        from contracts.permit import cheap_refusals
        r = self.root()
        bundle_path = cases.positive_case(r)
        rep = report(bundle_path, r)
        bundle = json.loads(bundle_path.read_text())
        drifted = dict(rep, lock_differences=[{"kind": "suite", "id": "suite", "locked": None, "current": None}])
        self.assertIn("permit.report_lock_differences", [x["code"] for x in cheap_refusals(drifted, bundle, r, "$")])
        forged = copy.deepcopy(rep)
        forged["assessment"]["suites"] = [{"id": "ratio-subset", "version": "1.0.0"}]
        self.assertIn("permit.report_inventory_mismatch", [x["code"] for x in cheap_refusals(forged, bundle, r, "$")])
        pre = copy.deepcopy(rep)
        pre["assessment"]["suites"] = [{"id": "counting-chain", "version": "1.1.0-dev.1"}]
        self.assertIn("permit.report_prerelease_suite", [x["code"] for x in cheap_refusals(pre, bundle, r, "$")])

    def test_g20_status_agrees_with_the_exit_code(self):
        # G20 (P6, V73): a dependency-missing diagnostic never leaves the status complete
        r = self.root()
        missing = {"kind": "dependency-missing", "code": "definition.coverage_missing", "message": "synthetic"}
        rep = report(cases.positive_case(r), r, extra_diags=[missing])
        self.assertEqual(ac().exit_code(rep), 3)
        self.assertNotEqual(rep["status"], "complete")

    @unittest.skip("G21 is classified in docs/dev/cross-artifact-check/g21-classification.md; a fix needs its own decision")
    def test_g21_tool_recipe_fragments_compose(self):
        pass


if __name__ == "__main__":
    unittest.main()
