"""Statistical-result semantics, publication gate and migration (hep-statistics audit F04; checks T06-T08).

The audit (commit b5c3a55) mutated the valid scan fixture: p > 1, unordered expected bands, a coverage note instead of
coverage, trials_method removed. All four passed validation with no finding. Contracts 2.2.0 reject or flag them:
natively for artifacts of contract 2.2.0, and under --strict for older ones, which otherwise keep their promised
outcome. The publication gate refuses what is not established. All fixtures SYNTHETIC."""
import copy
import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import contracts  # noqa: E402
from contracts import CONTRACTS_VERSION  # noqa: E402
from contracts import migrate_statistical_result as mig  # noqa: E402
from contracts import validate as v  # noqa: E402

ART = ROOT / "contracts" / "fixtures" / "artifacts"
BASE = json.loads((ART / "valid" / "statres_scan_global.json").read_text())

MUTATIONS = {
    "p_greater_than_one": (lambda d: d["extension"]["significance"].update(local_p=2.0, global_p=3.0), "error", "stats.p_out_of_range"),
    "unordered_expected_bands": (lambda d: d["extension"].update(expected={"median": 4, "band_1sigma": [9, 1], "band_2sigma": [8]}),
                                 "error", "stats.bands_unordered"),
    "band_cardinality": (lambda d: d["extension"].update(expected={"median": 4, "band_1sigma": [3, 5], "band_2sigma": [8]}),
                         "error", "stats.band_cardinality"),
    "cl_above_one": (lambda d: d["extension"].update(coverage={"check": "toys", "n_toys": 100, "cl": 1.5}), "error", "stats.cl_out_of_range"),
    "global_below_local": (lambda d: d["extension"]["significance"].update(local_p=0.02, global_p=0.001), "error", "stats.global_below_local"),
    "coverage_placeholder": (lambda d: d["extension"].update(coverage={"note": "not checked"}), "unresolved", "stats.coverage_untyped"),
    "missing_trials_method": (lambda d: d["extension"]["significance"].pop("trials_method", None), "unresolved", "stats.trials_method_missing"),
    "fit_diagnostics_failed": (lambda d: d["extension"].update(fit_diagnostics={"status": "failed"}), "error", "stats.fit_status_mismatch"),
}


def mutated(name, version=None):
    d = copy.deepcopy(BASE)
    MUTATIONS[name][0](d)
    if version:
        d["contract_version"] = version
        d["versions"]["contracts"] = version
    return d


def codes(rep, severity=None):
    return {f.code for f in rep.findings if severity is None or f.severity == severity}


def current(doc):
    d = copy.deepcopy(doc)
    d["contract_version"] = CONTRACTS_VERSION
    d["versions"]["contracts"] = CONTRACTS_VERSION
    d["required_capabilities"] = ["stats:result-semantics"]
    return d


PUBLISHABLE = current(BASE)
PUBLISHABLE["status"] = ["observed"]  # 'asimov' fails the gate from contracts 2.6.0 (gate.not_observed_data)
PUBLISHABLE["extension"]["seeds"] = {"toys": 1, "coverage": 2}
PUBLISHABLE["extension"]["coverage"] = {"check": "toys", "method": "seeded toys of the full procedure", "n_toys": 20000, "coverage": 0.951, "interval": [0.948, 0.954],
                                        "cl": 0.95, "ensemble": "fixed-auxiliary", "failure_policy": "count-as-noncovering", "failures": 0}
PUBLISHABLE["extension"]["likelihood"] = {"form": "poisson", "backend": "core.stats.likelihood_limits", "model_sha256": "0" * 64}
PUBLISHABLE["extension"]["significance"]["global_n_toys"] = 10000


class T06Semantics(unittest.TestCase):
    def test_contract_version_is_minor_bump(self):
        self.assertEqual(CONTRACTS_VERSION, "3.14.0")

    def test_audit_mutations_rejected_natively_at_2_2(self):
        for name, (_, level, code) in MUTATIONS.items():
            with self.subTest(name=name):
                rep = v.validate_artifact(mutated(name, CONTRACTS_VERSION))
                self.assertIn(code, codes(rep, level))
                self.assertEqual(rep.ok, level != "error")

    def test_legacy_artifact_keeps_its_outcome_and_strict_reports(self):
        for name, (_, level, code) in MUTATIONS.items():
            with self.subTest(name=name):
                legacy = v.validate_artifact(mutated(name))          # contract 1.1.0
                self.assertTrue(legacy.ok)
                self.assertNotIn(code, codes(legacy))
                strict = v.validate_artifact(mutated(name), strict=True)
                self.assertIn(code, codes(strict, level))

    def test_unmutated_fixture_in_strict_mode(self):
        # no error; its coverage {"toys": 0, "note": "fixture"} is an untyped placeholder, which strict mode names, and
        # (contracts 2.6.0) its toy-calibrated construction and toy goodness of fit record no seed
        rep = v.validate_artifact(BASE, strict=True)
        self.assertTrue(rep.ok)
        self.assertEqual(codes(rep), {"stats.coverage_untyped", "stats.seed_missing"})

    def test_non_finite_numbers_are_errors(self):
        for bad in (float("nan"), float("inf")):
            d = current(BASE)
            d["extension"]["significance"]["local_p"] = bad
            self.assertIn("number.non_finite", codes(v.validate_artifact(d), "error"))

    def test_p_bound_is_a_separate_typed_field(self):
        d = current(BASE)
        sig = d["extension"]["significance"]
        del sig["global_p"]
        sig["global_p_bound"] = {"kind": "upper", "value": 0.0295, "cl": 0.95, "convention": "clopper-pearson", "k": 0, "n": 100}
        self.assertTrue(v.validate_artifact(d).ok)
        sig["global_p"] = 0.0
        self.assertIn("stats.p_value_and_bound", codes(v.validate_artifact(d), "error"))
        del sig["global_p"]
        sig["global_p_bound"]["kind"] = "approximately"
        self.assertIn("schema.enum", codes(v.validate_artifact(d), "error"))

    def test_strict_flag_on_the_cli(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "a.json"
            p.write_text(json.dumps(mutated("p_greater_than_one")))
            with redirect_stdout(io.StringIO()):
                self.assertEqual(v.main([str(p)]), 0)
                self.assertEqual(v.main([str(p), "--strict"]), 1)


class T07PublicationGate(unittest.TestCase):
    def test_complete_result_passes(self):
        g = v.publication_gate(PUBLISHABLE)
        self.assertEqual(g["status"], "passed", g["reasons"])

    def test_archival_artifact_is_valid_but_not_publishable(self):
        self.assertTrue(v.validate_artifact(BASE).ok)
        g = v.publication_gate(BASE)  # an 'asimov' fixture: valid, and never a result on data (contracts 2.6.0)
        self.assertEqual(g["status"], "failed")
        self.assertIn("gate.not_observed_data", {r["code"] for r in g["reasons"]})
        relabelled = copy.deepcopy(BASE)
        relabelled["status"] = ["observed"]
        self.assertEqual(v.publication_gate(relabelled)["status"], "unresolved")

    def test_each_gap_blocks(self):
        cases = {
            "empty_coverage_note": (lambda d: d["extension"].update(coverage={"note": "x"}), "unresolved", "gate.coverage_not_established"),
            "coverage_not_checked": (lambda d: d["extension"].update(coverage={"check": "not-checked"}), "unresolved", "gate.coverage_not_established"),
            "trials_method_removed": (lambda d: d["extension"]["significance"].pop("trials_method"), "unresolved", "gate.global_not_established"),
            "global_p_removed": (lambda d: d["extension"]["significance"].pop("global_p"), "unresolved", "gate.global_not_established"),
            "failed_fit": (lambda d: (d["extension"].update(fit_status="failed"), d["status"].append("failed")), "failed", "gate.fit_not_converged"),
            "diagnostics_incomplete": (lambda d: d["extension"].update(fit_diagnostics={"status": "incomplete"}), "unresolved", "gate.fit_diagnostics"),
            "no_backend": (lambda d: d["extension"]["likelihood"].pop("backend"), "unresolved", "gate.model_provenance_missing"),
            "no_model": (lambda d: d["extension"]["likelihood"].pop("model_sha256"), "unresolved", "gate.model_provenance_missing"),
            "unvalidated": (lambda d: d["status"].append("unvalidated"), "unresolved", "gate.status_label"),
            "p_out_of_range": (lambda d: d["extension"]["significance"].update(global_p=3.0), "failed", "stats.p_out_of_range"),
        }
        for name, (change, status, code) in cases.items():
            with self.subTest(name=name):
                d = copy.deepcopy(PUBLISHABLE)
                change(d)
                g = v.publication_gate(d)
                self.assertEqual(g["status"], status, g["reasons"])
                self.assertIn(code, {r["code"] for r in g["reasons"]})

    def test_gate_on_the_cli(self):
        with tempfile.TemporaryDirectory() as tmp:
            good, bad = Path(tmp) / "g.json", Path(tmp) / "b.json"
            good.write_text(json.dumps(PUBLISHABLE))
            bad.write_text(json.dumps(BASE))
            with redirect_stdout(io.StringIO()) as buf:
                self.assertEqual(v.main([str(good), "--gate", "publication"]), 0)
            self.assertEqual(json.loads(buf.getvalue())["gate"]["status"], "passed")
            with redirect_stdout(io.StringIO()):
                self.assertEqual(v.main([str(bad), "--gate", "publication"]), 1)
                self.assertEqual(v.main([str(bad), "--gate", "other"]), 2)


class ReviewFindings(unittest.TestCase):
    """An independent review found that typed 2.2 fields changed the outcome of older artifacts, and that the gate let
    recorded undercoverage and empty coverage evidence pass."""

    def test_typed_fields_do_not_change_legacy_outcomes(self):
        legacy = copy.deepcopy(BASE)
        legacy["contract_version"] = legacy["versions"]["contracts"] = "2.1.0"
        for change in ({"coverage": {"n_toys": "1000"}}, {"coverage": {"cl": 0}}, {"likelihood": {"backend": {"name": "pyhf"}}},
                       {"fit_diagnostics": {"status": "converged"}}, {"likelihood": {"model_card": {}}}):
            with self.subTest(change=change):
                d = copy.deepcopy(legacy)
                d["extension"].update(change)
                self.assertTrue(v.validate_artifact(d).ok)
                self.assertFalse(v.validate_artifact(d, strict=True).ok)
                self.assertFalse(v.validate_artifact(current(d)).ok)

    def test_gate_rejects_weak_coverage_evidence(self):
        cases = {
            "undercoverage": ({"check": "toys", "method": "toys", "n_toys": 20000, "coverage": 0.80, "cl": 0.95}, "failed", "gate.undercoverage"),
            "no_value": ({"check": "toys", "method": "toys", "n_toys": 1, "cl": 0.95}, "unresolved", "stats.coverage_value_missing"),
            "no_nominal": ({"check": "toys", "method": "toys", "n_toys": 100, "coverage": 0.95}, "unresolved", "gate.coverage_nominal_missing"),
            "bare_analytic": ({"check": "analytic"}, "unresolved", "stats.coverage_justification_missing"),
        }
        for name, (cov, status, code) in cases.items():
            with self.subTest(name=name):
                d = copy.deepcopy(PUBLISHABLE)
                d["extension"]["coverage"] = cov
                g = v.publication_gate(d)
                self.assertEqual(g["status"], status, g["reasons"])
                self.assertIn(code, {r["code"] for r in g["reasons"]})

    def test_global_toys_and_bound_below_local(self):
        d = copy.deepcopy(PUBLISHABLE)
        d["extension"]["significance"].update(trials_method="toys")
        del d["extension"]["significance"]["global_n_toys"]
        self.assertIn("stats.global_toys_missing", codes(v.validate_artifact(d), "unresolved"))
        d = copy.deepcopy(PUBLISHABLE)
        sig = d["extension"]["significance"]
        del sig["global_p"]
        sig["local_p"] = 0.01
        sig["global_p_bound"] = {"kind": "upper", "value": 1e-4, "cl": 0.95, "convention": "clopper-pearson"}
        self.assertIn("stats.global_below_local", codes(v.validate_artifact(d), "error"))

    def test_capability_declaration_warning(self):
        d = copy.deepcopy(PUBLISHABLE)
        d.pop("required_capabilities")
        self.assertIn("stats.capability_not_declared", codes(v.validate_artifact(d), "warning"))
        self.assertNotIn("stats.capability_not_declared", codes(v.validate_artifact(PUBLISHABLE)))


class Contracts26Hardening(unittest.TestCase):
    """STH-T1.8: the 2.6.0 rules are native from 2.6.0; a 2.2-2.5 artifact keeps its default outcome, gets them under
    --strict, and the migrator brings it to 2.6.0 or refuses it with the rule's code (never repairing a number or
    inventing a seed)."""
    CASES = json.loads((ART / "cases.json").read_text())

    def _v26(self, kind):
        return {n: c for n, c in self.CASES[kind].items() if n.startswith("statres_v26_")}

    @staticmethod
    def _as(doc, version):
        d = copy.deepcopy(doc)
        d["contract_version"] = d["versions"]["contracts"] = version
        return d

    def test_valid_fixtures_are_current_and_pass(self):
        for name in ("statres_v26.json", "statres_v26_bayesian.json"):
            with self.subTest(name):
                d = json.loads((ART / "valid" / name).read_text())
                self.assertEqual(d["contract_version"], CONTRACTS_VERSION)
                rep = v.validate_artifact(d)
                self.assertTrue(rep.ok)
                self.assertFalse(codes(rep, "unresolved"), [f.as_dict() for f in rep.findings])

    def test_legacy_outcome_kept_and_strict_reports(self):
        for kind in ("invalid", "unresolved"):
            for name, expected in self._v26(kind).items():
                with self.subTest(name):
                    legacy = self._as(json.loads((ART / kind / name).read_text()), "2.5.0")
                    rep = v.validate_artifact(legacy)
                    self.assertTrue(rep.ok, [f.as_dict() for f in rep.errors])
                    self.assertFalse(set(expected) & codes(rep))
                    self.assertTrue(set(expected) <= codes(v.validate_artifact(legacy, strict=True)))

    def test_migrator_refuses_each_new_error(self):
        errors = self._v26("invalid")
        self.assertEqual(len(errors), 8)
        for name, expected in errors.items():
            with self.subTest(name):
                new, rep = mig.migrate(self._as(json.loads((ART / "invalid" / name).read_text()), "2.5.0"))
                self.assertIsNone(new)
                self.assertEqual(rep["status"], "refused")
                self.assertTrue(set(expected) <= {r["code"] for r in rep["refusals"]}, rep)

    def test_migrator_brings_2_5_to_2_6_without_inventing_evidence(self):
        d = self._as(json.loads((ART / "unresolved" / "statres_v26_seed_missing.json").read_text()), "2.5.0")
        new, rep = mig.migrate(d)
        self.assertEqual((rep["status"], new["contract_version"], new["versions"]["contracts"]), ("migrated", CONTRACTS_VERSION, CONTRACTS_VERSION))
        self.assertNotIn("seeds", new["extension"])
        self.assertIn("stats.seed_missing", {x["code"] for x in rep["diagnostics"]})
        self.assertEqual(new["extension"], d["extension"])  # only the version moved
        same, rep2 = mig.migrate(new)
        self.assertEqual(rep2["status"], "unchanged")


class T08Migration(unittest.TestCase):
    def test_old_reader_refuses_the_new_capability(self):
        old = frozenset(contracts.KNOWN_CAPABILITIES - {"stats:result-semantics"})
        doc = copy.deepcopy(PUBLISHABLE)  # a 2.x artifact, so the 2.1 reader sees a newer minor, not a newer major
        doc["contract_version"] = doc["versions"]["contracts"] = "2.13.0"
        with mock.patch.object(contracts, "KNOWN_CAPABILITIES", old), mock.patch.object(contracts, "CONTRACTS_VERSION", "2.1.0"):
            rep = v.validate_artifact(doc)
        self.assertIn("contract.unknown_capability", codes(rep, "error"))
        self.assertIn("contract.newer_minor", codes(rep))

    def test_unknown_capability_is_refused(self):
        d = copy.deepcopy(PUBLISHABLE)
        d["required_capabilities"].append("stats:not-yet-defined")
        self.assertIn("contract.unknown_capability", codes(v.validate_artifact(d), "error"))

    def test_all_legacy_fixtures_keep_their_outcome(self):
        cases = json.loads((ART / "cases.json").read_text())
        for name in cases["valid"]:
            self.assertTrue(v.validate_artifact(json.loads((ART / "valid" / name).read_text())).ok, name)
        for name, expected in cases["invalid"].items():
            rep = v.validate_artifact(json.loads((ART / "invalid" / name).read_text()))
            self.assertFalse(rep.ok, name)
            self.assertTrue(set(expected) <= codes(rep), name)

    def test_migration_of_a_clean_legacy_result(self):
        new, rep = mig.migrate(BASE)
        self.assertEqual(rep["status"], "migrated")
        self.assertEqual(new["contract_version"], CONTRACTS_VERSION)
        self.assertIn("stats:result-semantics", new["required_capabilities"])
        self.assertEqual(new["extension"]["coverage"], {**BASE["extension"]["coverage"], "check": "not-checked"})
        self.assertIn("migrate.coverage_untyped", {x["code"] for x in rep["diagnostics"]})
        self.assertTrue(v.validate_artifact(new).ok)
        self.assertEqual(v.publication_gate(new)["status"], "failed")  # the fixture is labelled 'asimov'
        new["status"] = ["observed"]
        self.assertEqual(v.publication_gate(new)["status"], "unresolved")

    def test_migration_refuses_and_names_the_rule(self):
        for name, code in (("p_greater_than_one", "stats.p_out_of_range"), ("unordered_expected_bands", "stats.bands_unordered")):
            with self.subTest(name=name):
                new, rep = mig.migrate(mutated(name))
                self.assertIsNone(new)
                self.assertEqual(rep["status"], "refused")
                self.assertIn(code, {r["code"] for r in rep["refusals"]})

    def test_migration_keeps_unresolved_trials_method(self):
        new, rep = mig.migrate(mutated("missing_trials_method"))
        self.assertEqual(rep["status"], "migrated")
        self.assertNotIn("trials_method", new["extension"]["significance"])
        self.assertIn("stats.trials_method_missing", {x["code"] for x in rep["diagnostics"]})

    def test_migration_cli(self):
        with tempfile.TemporaryDirectory() as tmp:
            src, out = Path(tmp) / "old.json", Path(tmp) / "new.json"
            src.write_text(json.dumps(BASE))
            with redirect_stdout(io.StringIO()):
                self.assertEqual(mig.main([str(src), "--out", str(out)]), 0)
            self.assertEqual(json.loads(out.read_text())["contract_version"], CONTRACTS_VERSION)
            src.write_text(json.dumps(mutated("p_greater_than_one")))
            with redirect_stdout(io.StringIO()):
                self.assertEqual(mig.main([str(src)]), 1)
            src.write_text(json.dumps({"artifact_type": "prediction"}))
            with redirect_stdout(io.StringIO()):
                self.assertEqual(mig.main([str(src)]), 2)


if __name__ == "__main__":
    unittest.main()
