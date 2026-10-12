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
PUBLISHABLE["status"] = ["asimov"]
PUBLISHABLE["extension"]["coverage"] = {"check": "toys", "method": "seeded toys of the full procedure", "n_toys": 20000, "coverage": 0.951, "interval": [0.948, 0.954],
                                        "cl": 0.95, "ensemble": "fixed-auxiliary", "failure_policy": "count-as-noncovering", "failures": 0}
PUBLISHABLE["extension"]["likelihood"] = {"form": "poisson", "backend": "core.stats.likelihood_limits", "model_sha256": "0" * 64}
PUBLISHABLE["extension"]["significance"]["global_n_toys"] = 10000


class T06Semantics(unittest.TestCase):
    def test_contract_version_is_minor_bump(self):
        self.assertEqual(CONTRACTS_VERSION, "2.2.0")

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
        # no error; its coverage {"toys": 0, "note": "fixture"} is an untyped placeholder, which strict mode names
        rep = v.validate_artifact(BASE, strict=True)
        self.assertTrue(rep.ok)
        self.assertEqual(codes(rep), {"stats.coverage_untyped"})

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
        self.assertEqual(v.publication_gate(BASE)["status"], "unresolved")

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


class T08Migration(unittest.TestCase):
    def test_old_reader_refuses_the_new_capability(self):
        old = frozenset(contracts.KNOWN_CAPABILITIES - {"stats:result-semantics"})
        with mock.patch.object(contracts, "KNOWN_CAPABILITIES", old), mock.patch.object(contracts, "CONTRACTS_VERSION", "2.1.0"):
            rep = v.validate_artifact(PUBLISHABLE)
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
