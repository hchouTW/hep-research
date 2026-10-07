"""Malformed-input robustness: validators and the gate report problems instead of raising.

All fixtures are synthetic structural stand-ins."""
from __future__ import annotations

import contextlib
import copy
import io
import json
import os
import random
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from contracts.comparison import gate as gate_cli  # noqa: E402
from contracts.comparison.gate import gate  # noqa: E402
from contracts.registry import validate_registry  # noqa: E402
from contracts.semver import valid_spec  # noqa: E402
from contracts import validate as validate_cli  # noqa: E402
from contracts.validate import validate_artifact  # noqa: E402
from contracts.vocab import Vocabulary  # noqa: E402
from core.evidence.ledger import check_ledger  # noqa: E402
from tests.contracts.mutations import random_mutation, single_mutations  # noqa: E402

FIX = ROOT / "contracts" / "fixtures"
VALID = FIX / "artifacts" / "valid"
REG = FIX / "registry"
SLOW = os.environ.get("HEP_SLOW_TESTS") == "1"


def load(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))


def run(main, args):
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        rc = main(args)
    return rc, json.loads(out.getvalue())


class ValidateTypeErrorTests(unittest.TestCase):
    """Type-invalid fields are schema findings, never a traceback from the semantic rules."""

    def test_type_invalid_fields_reported(self):
        base = load(VALID / "dataset_record.json")
        cases = {"covariance": lambda d: d["extension"].__setitem__("covariance", "present"),
                 "normalization": lambda d: d["extension"]["observable"].__setitem__("normalization", "lumi"),
                 "edges": lambda d: d["extension"]["data"].__setitem__("edges", [0, "a", 2]),
                 "inputs": lambda d: d.__setitem__("inputs", ["x"])}
        for name, mutate in cases.items():
            with self.subTest(name=name):
                doc = copy.deepcopy(base)
                mutate(doc)
                rep = validate_artifact(doc)
                self.assertFalse(rep.ok)
                self.assertIn("schema.type", {f.code for f in rep.errors})

    def test_profiles_from_without_value_is_usage_error(self):
        rc, out = run(validate_cli.main, [str(VALID / "dataset_record.json"), "--profiles-from"])
        self.assertEqual(rc, 2)
        self.assertFalse(out["ok"])

    def test_profiles_from_invalid_config_reported(self):
        with tempfile.TemporaryDirectory() as td:
            cfg = Path(td) / "hep-research.project.json"
            cfg.write_text(json.dumps({"plugin_version": 3}), encoding="utf-8")
            rc, out = run(validate_cli.main, [str(VALID / "dataset_record.json"), "--profiles-from", str(cfg)])
        self.assertEqual(rc, 1)
        self.assertTrue(any(f["path"].startswith("config") for f in out["findings"]))


class GateIncompleteTransformationTests(unittest.TestCase):
    def test_incomplete_transformations_refused(self):
        obs = {"quantity": "q", "unit": "pb", "level": "parton", "bin_semantics": "bin-integrated",
               "variables": [{"name": "x", "unit": "1", "edges": [0.0, 1.0, 2.0]}]}
        side = {"observable": obs, "status": [], "uncertainties": [], "corrections": []}
        for t in ({"kind": "fiducial-restriction", "variable": "x"}, {"kind": "fiducial-restriction", "variable": "x", "range": [0.0]},
                  {"kind": "level-identification", "from": "parton"}, {"kind": "unit-conversion", "from": "pb", "factor": 1.0},
                  {"kind": "rebin"}, {"kind": "variable-change", "from": "x", "jacobian": "1"}):
            with self.subTest(kind=t["kind"], fields=sorted(t)):
                r = gate(side, side, [{**t, "owner": "hep-theory", "justification": "synthetic"}], [], {})
                self.assertFalse(r["comparable"])
                self.assertIn("incomplete", " ".join(m["reason"] for m in r["mismatches"]))

    def test_cli_reports_incomplete_transformation(self):
        with tempfile.TemporaryDirectory() as td:
            pred = load(VALID / "prediction.json")
            pred["extension"].pop("allowed_transformations", None)
            (Path(td) / "pred.json").write_text(json.dumps(pred), encoding="utf-8")
            plan = Path(td) / "plan.json"
            plan.write_text(json.dumps({"transformations": [{"kind": "level-identification", "owner": "hep-theory",
                                                        "justification": "synthetic", "from": "particle-fiducial"}]}), encoding="utf-8")
            rc, out = run(gate_cli.main, [str(Path(td) / "pred.json"), str(VALID / "dataset_record.json"), "--plan", str(plan)])
        self.assertEqual(rc, 1)
        self.assertFalse(out["comparable"])


class GateMalformedInputTests(unittest.TestCase):
    """Schema-valid or malformed input gives findings with a field path and a code, never a traceback (T05)."""

    def pair(self):
        return load(VALID / "prediction.json"), load(VALID / "dataset_record.json")

    def test_one_sided_cuts_with_null_bounds(self):
        pred, meas = self.pair()
        cuts = [{"variable": "pt", "unit": "GeV", "low": 20.0, "high": None},
                {"variable": "pt", "unit": "GeV", "low": None, "high": 100.0}]
        for doc in (pred, meas):
            doc["extension"]["observable"]["phase_space"] = {"definition": "x", "fiducial": True, "cuts": copy.deepcopy(cuts)}
            self.assertTrue(validate_artifact(doc).ok, validate_artifact(doc).as_dict())
        res = gate_cli.check(pred, meas, {})
        self.assertNotIn("phase_space", {m["field"] for m in res["mismatches"]})
        meas["extension"]["observable"]["phase_space"]["cuts"][1]["high"] = 90.0
        res = gate_cli.check(pred, meas, {})
        self.assertIn("phase_space.cuts", {m["field"] for m in res["mismatches"]})

    def test_explicit_null_phase_space_and_normalization(self):
        pred, meas = self.pair()
        pred["extension"]["observable"]["phase_space"] = None
        pred["extension"]["observable"]["normalization"] = None
        self.assertEqual(gate_cli.check(pred, meas, {})["status"], "refused")  # the schema types both as objects
        res = gate(gate_cli.side_from_artifact(pred), gate_cli.side_from_artifact(meas))  # combination and model sets
        self.assertIn("phase_space.fiducial", {m["field"] for m in res["mismatches"]})
        self.assertIn("normalization.kind", {m["field"] for m in res["mismatches"]})

    def test_wrongly_typed_artifact_is_refused_with_paths(self):
        pred, meas = self.pair()
        meas["extension"]["observable"] = ["not", "an", "object"]
        pred["artifact_type"] = ["prediction"]
        res = gate_cli.check(pred, meas, {})
        self.assertEqual(res["status"], "refused")
        paths = {f["path"] for f in res["findings"]}
        self.assertIn("measurement:$.extension.observable", paths)
        self.assertIn("prediction:$.artifact_type", paths)
        with tempfile.TemporaryDirectory() as td:
            (Path(td) / "p.json").write_text(json.dumps(pred), encoding="utf-8")
            (Path(td) / "m.json").write_text(json.dumps(meas), encoding="utf-8")
            rc, out = run(gate_cli.main, [str(Path(td) / "p.json"), str(Path(td) / "m.json")])
        self.assertEqual(rc, 2)
        self.assertEqual(out["refusal"], "invalid-input")

    def test_malformed_plan_entries_are_findings_and_not_applied(self):
        pred, meas = self.pair()
        plan = {"transformations": ["rebin", {"kind": "rebin", "owner": "x", "edges": [0, "a"]}],
                "mappings": [{"action": "equivalent"}], "measurement_conditions": [1, 2]}
        res = gate_cli.check(pred, meas, plan)
        malformed = {m["field"] for m in res["mismatches"] if m["kind"] == "malformed"}
        self.assertEqual(malformed, {"transformations[0]", "transformations[1].edges", "mappings[0]", "measurement_conditions"})
        self.assertEqual(res["transformations"], [])
        self.assertEqual(gate_cli.check(pred, meas, ["not a plan"])["status"], "refused")

    def test_artifact_type_of_the_wrong_json_type(self):
        for bad in (["prediction"], {"a": 1}, 3):
            doc = load(VALID / "prediction.json")
            doc["artifact_type"] = bad
            rep = validate_artifact(doc)
            self.assertFalse(rep.ok)
            self.assertIn("$.artifact_type", {f.path for f in rep.errors})


class MutationFuzzTests(unittest.TestCase):
    """Seeded mutation fuzzing of every valid artifact fixture, a gate plan and the ledgers (T09): no input raises.

    Fast tier: every node of every fixture mutated four ways (null, type swap, list wrap, deletion), one at a time.
    Slow tier: 10,000 random multi-mutations through the validator, the gate and the ledger checker."""

    PLAN = {"transformations": [
        {"kind": "level-identification", "owner": "hep-theory", "justification": "j", "from": "parton", "to": "particle-fiducial"},
        {"kind": "fiducial-restriction", "owner": "hep-theory", "variable": "cos_theta", "range": [-0.5, 0.5]},
        {"kind": "rebin", "owner": "hep-theory", "edges": [-1.0, 0.0, 1.0]},
        {"kind": "unit-conversion", "owner": "hep-theory", "justification": "j", "from": "pb", "to": "fb", "factor": 1000.0},
        {"kind": "bin-integrate", "owner": "hep-theory"},
        {"kind": "multiply-by-normalization", "owner": "hep-analysis", "normalization_kind": "integrated-luminosity",
         "value": 1.0, "unit_in": "fb", "unit_out": "1"},
        {"kind": "forward-fold", "owner": "detector-response", "truth_edges": [-1.0, 0.0, 1.0], "reco_edges": [-1.0, 1.0],
         "truth_level": "particle-fiducial", "includes": ["efficiency"]},
        {"kind": "apply-correction", "owner": "hep-analysis", "justification": "j", "effect": "acceptance"}],
        "mappings": [{"field": "process", "action": "equivalent", "justification": "j"},
                     {"key": "x:y", "action": "irrelevant", "justification": "j"}],
        "measurement_conditions": {"sqrt_s": 91.2}}

    @classmethod
    def setUpClass(cls):
        cls.docs = {p.name: load(p) for p in sorted(VALID.glob("*.json"))}
        cls.pred, cls.meas = load(VALID / "prediction.json"), load(VALID / "dataset_record.json")
        cls.ledgers = [(load(d / "sources.json"), load(d / "claims.json")) for d in sorted((ROOT / "profiles").glob("*/*/evidence"))]

    def test_every_single_mutation_of_every_fixture(self):
        n = 0
        for name, doc in self.docs.items():
            for what, mutated in single_mutations(doc):
                n += 1
                try:
                    validate_artifact(mutated)
                    gate_cli.check(mutated, self.meas, {})
                    gate_cli.check(self.pred, mutated, {})
                except Exception as exc:  # noqa: BLE001 - the point is to report any exception with its input
                    self.fail(f"{name}: {what}: {type(exc).__name__}: {exc}")
        self.assertGreater(n, 1000)

    def test_every_single_mutation_of_the_plan_and_a_ledger_record(self):
        for what, plan in single_mutations(self.PLAN):
            try:
                gate_cli.check(self.pred, self.meas, plan)
            except Exception as exc:  # noqa: BLE001
                self.fail(f"plan {what}: {type(exc).__name__}: {exc}")
        sources, claims = self.ledgers[0]
        for what, rec in single_mutations({"source": sources[0], "claim": claims[0]}):
            try:
                check_ledger([rec.get("source")] + sources[1:], [rec.get("claim")] + claims[1:])
            except Exception as exc:  # noqa: BLE001
                self.fail(f"ledger {what}: {type(exc).__name__}: {exc}")

    @unittest.skipUnless(SLOW, "slow: set HEP_SLOW_TESTS=1")
    def test_ten_thousand_random_mutations(self):
        rng = random.Random(20261007)
        docs = list(self.docs.values())
        for i in range(10000):
            k = rng.choice((1, 1, 2, 3))
            doc = random_mutation(rng.choice(docs), rng, k)
            plan = self.PLAN if rng.random() < 0.5 else random_mutation(self.PLAN, rng, k)
            sources, claims = rng.choice(self.ledgers)
            if rng.random() < 0.5:
                sources = random_mutation(sources, rng, k)
            else:
                claims = random_mutation(claims, rng, k)
            try:
                validate_artifact(doc)
                gate_cli.check(doc, self.meas, plan)
                gate_cli.check(self.pred, doc, plan)
                check_ledger(sources, claims)
            except Exception as exc:  # noqa: BLE001
                self.fail(f"mutation {i}: {type(exc).__name__}: {exc}")


class RegistryRobustnessTests(unittest.TestCase):
    def test_local_profile_without_id_reported(self):
        with tempfile.TemporaryDirectory() as td:
            local = Path(td) / "local"
            shutil.copytree(REG / "valid" / "profiles" / "experiments" / "a", local)
            prof = load(local / "profile.json")
            del prof["id"]
            (local / "profile.json").write_text(json.dumps(prof), encoding="utf-8")
            rep, _ = validate_registry(REG / "valid" / "profiles" / "registry.json", [local])
        self.assertIn("schema.required", {f.code for f in rep.errors})

    def test_capability_test_outside_plugin_tests_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            pkg = Path(td) / "pkg"
            shutil.copytree(REG / "valid", pkg)
            (Path(td) / "outside_test.py").write_text("", encoding="utf-8")
            pj = pkg / "profiles" / "experiments" / "a" / "profile.json"
            prof = load(pj)
            prof["capabilities"] = [{"name": "c", "status": "demonstrated-on-synthetic-data", "scope": "fixture",
                                     "tests": ["../../../../outside_test.py"]}]
            pj.write_text(json.dumps(prof), encoding="utf-8")
            rep, _ = validate_registry(pkg / "profiles" / "registry.json")
        self.assertIn("profile.path_escapes", {f.code for f in rep.errors})

    def test_shipped_plugin_tests_still_accepted(self):
        rep, _ = validate_registry()
        self.assertTrue(rep.ok, [f.as_dict() for f in rep.findings])


class SpecAndVocabTests(unittest.TestCase):
    def test_empty_version_spec_invalid(self):
        for spec in ("", "  ", ","):
            self.assertFalse(valid_spec(spec), spec)
        self.assertTrue(valid_spec(">=0.1,<1.0"))

    def test_with_profiles_surfaces_extension_problems(self):
        good = {"id": "experiment:a", "evidence_namespace": "fxa", "vocabulary_extensions": {"levels": ["fxa:instrument"]}}
        bad = {"id": "experiment:b", "evidence_namespace": "fxb", "vocabulary_extensions": {"levels": ["other:x"], "nope": ["fxb:y"]}}
        self.assertEqual(Vocabulary.with_profiles([good]).problems, [])
        v = Vocabulary.with_profiles([good, bad])
        self.assertTrue(v.has("levels", "fxa:instrument"))
        self.assertEqual(len(v.problems), 2)
        self.assertTrue(all(p.startswith("experiment:b") for p in v.problems))


if __name__ == "__main__":
    unittest.main()
