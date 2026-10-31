"""measurement-spec content semantics (hep-measurement audit 2026-10-13, ANA-P1-1).

The audit found that contracts/validate.py enforced almost none of the hep-measurement SKILL.md invariants: 30 specs that
break them passed with and without --strict. Contracts 2.6.0 report them natively; a 2.5.0 artifact keeps its outcome
and gets them with --strict. All fixtures SYNTHETIC."""
import copy
import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests" / "contracts"))

from contracts import CONTRACTS_VERSION  # noqa: E402
from core.interpreter_guard import child_flags  # noqa: E402
from contracts import validate as v  # noqa: E402

ART = ROOT / "contracts" / "fixtures" / "artifacts"
CASES = json.loads((ART / "cases.json").read_text())
CURRENT = json.loads((ART / "valid" / "measurement_v26.json").read_text())
MEAS_INVALID = sorted(n for n in CASES["invalid"] if n.startswith("measurement_v26_"))
MEAS_UNRESOLVED = sorted(n for n in CASES["unresolved"] if n.startswith("measurement_v26_"))
TEMPLATE = ROOT / "skills" / "hep-measurement" / "assets" / "measurement_spec.template.json"


def load(path):
    return json.loads(Path(path).read_text())


def codes(rep, level="error"):
    return {f.code for f in rep.findings if f.severity == level}


def legacy(doc, version="2.5.0"):
    d = copy.deepcopy(doc)
    d["contract_version"] = version
    d["versions"]["contracts"] = version
    return d


class MeasurementRules(unittest.TestCase):
    def test_gate_is_this_minor(self):
        self.assertEqual(v.MEASUREMENT_SEMANTICS_FROM, "2.6.0")
        self.assertEqual(CURRENT["contract_version"], CONTRACTS_VERSION)

    def test_valid_spec_has_no_findings(self):
        rep = v.validate_artifact(CURRENT)
        self.assertEqual(rep.findings, [], rep.as_dict())

    def test_one_fixture_per_rule_fails_with_exactly_its_code(self):
        self.assertGreaterEqual(len(MEAS_INVALID), 25)
        for name in MEAS_INVALID:
            with self.subTest(name=name):
                rep = v.validate_artifact(load(ART / "invalid" / name))
                self.assertFalse(rep.ok)
                self.assertEqual(codes(rep), set(CASES["invalid"][name]), rep.as_dict())

    def test_unresolved_fixtures_are_valid_but_open(self):
        self.assertEqual(len(MEAS_UNRESOLVED), 2)
        for name in MEAS_UNRESOLVED:
            with self.subTest(name=name):
                rep = v.validate_artifact(load(ART / "unresolved" / name))
                self.assertTrue(rep.ok, rep.as_dict())
                self.assertEqual(codes(rep, "unresolved"), set(CASES["unresolved"][name]))

    def test_legacy_artifacts_keep_their_outcome_unless_strict(self):
        for name in MEAS_INVALID:
            with self.subTest(name=name):
                doc = legacy(load(ART / "invalid" / name))
                plain = v.validate_artifact(doc)
                self.assertTrue(plain.ok, plain.as_dict())
                self.assertFalse(codes(plain) & set(CASES["invalid"][name]))
                strict = v.validate_artifact(doc, strict=True)
                self.assertTrue(set(CASES["invalid"][name]) <= codes(strict), strict.as_dict())

    def test_warnings(self):
        cases = {
            "measurement.selection_validation_partial":
                lambda d, e: e["selections"][0].update(validation={"metric": "efficiency ratio"}),
            "measurement.cancellation_unverified":
                lambda d, e: e.update(ratio={"numerator": "a", "denominator": "b", "cancellations": [
                    {"effect": "exposure", "treatment": "cancels", "correlation_model": "same exposure"}]}),
            "measurement.unknown_key": lambda d, e: e["backgrounds"][0].update(colour="blue"),
        }
        for code, fn in cases.items():
            with self.subTest(code=code):
                d = copy.deepcopy(CURRENT)
                fn(d, d["extension"])
                rep = v.validate_artifact(d)
                self.assertTrue(rep.ok, rep.as_dict())
                self.assertIn(code, codes(rep, "warning"))

    def test_factorized_efficiency_chain_and_namespaced_terms_pass(self):
        d = copy.deepcopy(CURRENT)
        d["extension"]["corrections"] = [
            {"effect_id": "trigger", "category": "trigger_efficiency", "applied_in": "estimator"},
            {"effect_id": "reco", "category": "reconstruction_efficiency", "applied_in": "estimator"},
            {"effect_id": "sel", "category": "selection_efficiency", "applied_in": "estimator"},
            {"effect_id": "custom", "category": "synthetic-ns:special_factor", "applied_in": "estimator"},
            {"effect_id": "zero", "category": "fakes", "applied_in": "estimator", "value": 0, "exact_zero": True}]
        self.assertEqual(v.validate_artifact(d).findings, [])

    def test_namespaced_efficiency_next_to_bare_efficiency_warns(self):
        """Found but unfixed after 0.23.0: a bare 'efficiency' next to a namespaced '<ns>:efficiency' (the same
        efficiency counted twice) passed with no finding, because the repeated-category error compares names with the
        namespace kept and the bare-efficiency error needs a '_efficiency' suffix. A warning with a stable code, so no
        artifact changes outcome (no contracts major); the existing errors are unchanged."""
        pairs = (("efficiency", "synthetic-ns:efficiency"), ("synthetic-ns:efficiency", "efficiency"),
                 ("synthetic-ns:efficiency", "other-ns:efficiency"))
        for first, second in pairs:
            with self.subTest(categories=(first, second)):
                rep = self._edited(lambda e, a=first, b=second: e.update(corrections=[
                    {"effect_id": "total-eff", "category": a, "applied_in": "estimator"},
                    {"effect_id": "profile-eff", "category": b, "applied_in": "estimator"}]))
                self.assertTrue(rep.ok, rep.as_dict())
                self.assertEqual(codes(rep, "warning"), {"measurement.efficiency_counted_twice_namespaced"})
        # one efficiency term, namespaced or not, next to non-efficiency factors: no finding
        for cats in (("efficiency", "synthetic-ns:special_factor"), ("synthetic-ns:efficiency", "fakes")):
            with self.subTest(categories=cats):
                rep = self._edited(lambda e, cats=cats: e.update(corrections=[
                    {"effect_id": f"c{i}", "category": c, "applied_in": "estimator"} for i, c in enumerate(cats)]))
                self.assertEqual(rep.findings, [])
        # the existing error is unchanged and is not doubled by the warning
        for cats in (("efficiency", "trigger_efficiency"), ("efficiency", "synthetic-ns:trigger_efficiency"),
                     ("efficiency", "synthetic-ns:efficiency", "trigger_efficiency")):
            with self.subTest(categories=cats):
                rep = self._edited(lambda e, cats=cats: e.update(corrections=[
                    {"effect_id": f"c{i}", "category": c, "applied_in": "estimator"} for i, c in enumerate(cats)]))
                self.assertFalse(rep.ok)
                self.assertIn("measurement.correction_category_repeated", codes(rep))
                self.assertNotIn("measurement.efficiency_counted_twice_namespaced", codes(rep, "warning"))

    def test_unknown_marker_in_unresolved_inputs_is_unresolved(self):
        d = copy.deepcopy(CURRENT)
        d["extension"]["selections"][0]["conditional_denominator"] = "unknown"
        d["unresolved_inputs"] = ["selections[0].conditional_denominator: control sample not chosen"]
        rep = v.validate_artifact(d)
        self.assertTrue(rep.ok, rep.as_dict())
        self.assertIn("measurement.input_unresolved", codes(rep, "unresolved"))

    def _edited(self, fn):
        d = copy.deepcopy(CURRENT)
        fn(d["extension"])
        return v.validate_artifact(d)

    def test_placeholder_denominator_warns(self):
        """Triage T11: null, a number or 'n/a' as conditional denominator passed with no finding. A warning (stable code
        measurement.denominator_placeholder), so older specs keep their outcome; a blank string stays an error."""
        for den in (None, 0, False, "n/a", " N/A ", "none", "TBD", "-", "?"):
            with self.subTest(den=den):
                rep = self._edited(lambda e, den=den: e["selections"][0].update(conditional_denominator=den))
                self.assertTrue(rep.ok, rep.as_dict())
                self.assertEqual(codes(rep, "warning"), {"measurement.denominator_placeholder"})
        for den in ("generated events in the truth bin", "nan-free sample"):
            with self.subTest(den=den):
                rep = self._edited(lambda e, den=den: e["selections"][0].update(conditional_denominator=den))
                self.assertEqual(rep.findings, [])
        rep = self._edited(lambda e: e["selections"][0].update(conditional_denominator="  "))
        self.assertEqual((rep.ok, codes(rep), codes(rep, "warning")), (False, {"measurement.denominator_blank"}, set()))

    def test_placeholder_no_backgrounds_reason_warns(self):
        """Triage T12: backgrounds [] with no_backgrounds_reason 'n/a' passed with no finding."""
        for reason in ("n/a", "None", " tbd "):
            with self.subTest(reason=reason):
                rep = self._edited(lambda e, reason=reason: e.update(backgrounds=[], no_backgrounds_reason=reason))
                self.assertTrue(rep.ok, rep.as_dict())
                self.assertEqual(codes(rep, "warning"), {"measurement.no_backgrounds_reason_placeholder"})

    def test_blinding_mask_naming_nothing_warns(self):
        """Triage T14: a blinded spec passed with mask {'regions': ['']}, which names no region."""
        empty = ({"regions": [""]}, {"regions": ["  "], "intervals": []}, {"intervals": [{"variable": " "}]},
                 {"regions": [""], "intervals": [{"variable": ""}]})
        for mask in empty:
            with self.subTest(mask=mask):
                rep = self._edited(lambda e, mask=mask: e.update(blinding={"blinded": True, "mask": mask}))
                self.assertTrue(rep.ok, rep.as_dict())
                self.assertEqual(codes(rep, "warning"), {"measurement.blinding_mask_empty"})
        for mask in ({"regions": ["", "signal region"]}, {"intervals": [{"variable": "x", "low": 0.9}]}):
            with self.subTest(mask=mask):
                rep = self._edited(lambda e, mask=mask: e.update(blinding={"blinded": True, "mask": mask}))
                self.assertEqual(rep.findings, [], rep.as_dict())
        rep = self._edited(lambda e: e.update(blinding={"blinded": True, "mask": {}}))
        self.assertEqual(codes(rep), {"measurement.blinding_mask_missing"})

    def test_no_backgrounds_with_a_reason_passes(self):
        d = copy.deepcopy(CURRENT)
        d["extension"]["backgrounds"] = []
        d["extension"]["no_backgrounds_reason"] = "SYNTHETIC: signal-only toy"
        self.assertTrue(v.validate_artifact(d).ok)


class ShippedSpecs(unittest.TestCase):
    def test_template_validates_strictly(self):
        doc = load(TEMPLATE)
        self.assertEqual(doc["contract_version"], CONTRACTS_VERSION)
        rep = v.validate_artifact(doc, strict=True)
        self.assertTrue(rep.ok, rep.as_dict())
        self.assertEqual(codes(rep, "warning"), set())

    def test_examples_validate_with_their_profiles(self):
        from contracts.vocab import Vocabulary
        for ex, profile in (("collider-angular", "synthetic-collider"), ("ams-flux-ratio", "ams-02")):
            with self.subTest(example=ex):
                spec = ROOT / "examples" / ex / "output" / "artifacts" / "measurement_spec.json"
                profile_json = ROOT / "profiles" / "experiments" / profile / "profile.json"
                if not (spec.exists() and profile_json.exists()):
                    continue  # the AMS-optional check runs this suite without the AMS profile and its example
                doc = load(spec)
                self.assertEqual(doc["contract_version"], CONTRACTS_VERSION)
                vocab = Vocabulary.with_profiles([load(ROOT / "profiles" / "experiments" / profile / "profile.json")])
                rep = v.validate_artifact(doc, vocab, strict=True)
                self.assertTrue(rep.ok, rep.as_dict())


class ValidatorCli(unittest.TestCase):
    def run_cli(self, *args):
        return subprocess.run([sys.executable, *child_flags(), "-I", str(ROOT / "contracts" / "validate.py"), *args],
                              capture_output=True, text=True, timeout=60)

    def test_flags_before_the_artifact(self):
        p = self.run_cli("--strict", str(TEMPLATE))
        self.assertEqual(p.returncode, 0, p.stdout)

    def test_help_lists_the_measurement_rules(self):
        p = self.run_cli("--help")
        self.assertEqual(p.returncode, 0)
        self.assertIn("measurement-spec rules of contracts 2.6.0", " ".join(p.stdout.split()))


if __name__ == "__main__":
    unittest.main()
