"""Malformed-input robustness: validators and the gate report problems instead of raising.

All fixtures are synthetic structural stand-ins."""
from __future__ import annotations

import contextlib
import copy
import io
import json
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

FIX = ROOT / "contracts" / "fixtures"
VALID = FIX / "artifacts" / "valid"
REG = FIX / "registry"


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
