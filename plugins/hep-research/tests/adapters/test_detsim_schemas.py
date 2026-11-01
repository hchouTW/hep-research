"""T-SCHEMA (docs/dev/detector-simulation/TASK.md 16.1): the four detector-simulation contracts (contracts 3.18.0).

detector-task/1, detector-plan/1, detsim-completeness/1 and detsim-observables/1: positive fixtures pass, negative
ones fail with the expected finding; unknown keys are refused; quantities carry ASCII units and decimal strings; every
schema uses only the keywords contracts/schema.py implements and every pattern is anchored ^...$; because that
validator uses re.search (where $ also accepts a trailing newline) and ignores keywords it does not implement, the
code checks of detsim_schemas.py are shown to catch what the schema alone lets through; a float anywhere in a task or
a plan is refused. SYNTHETIC fixtures built in code (tests/adapters/detsim_backend_synthetic.py); standard library only.
"""
import base64
import copy
import hashlib
import json
import re
import sys
import tempfile
import unittest
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / "adapters" / "detector-simulation" / "assets"
for _entry in (str(ROOT), str(ASSETS), str(Path(__file__).resolve().parent)):
    if _entry not in sys.path:
        sys.path.insert(0, _entry)

import detsim_backend_synthetic as synthetic  # noqa: E402
import detsim_plan  # noqa: E402
import detsim_profile  # noqa: E402
import detsim_schemas as schemas  # noqa: E402
from contracts.schema import ANNOTATION_KEYWORDS, SUPPORTED_KEYWORDS, load_schema, validate  # noqa: E402

SCHEMA_NAMES = sorted(schemas.SCHEMA_FILES.values())
ENV = "ab" * 32


def codes(findings):
    return {f["code"] for f in findings}


def valid_task():
    return synthetic.task_document(ENV)


def valid_completeness():
    return {"schema": "detsim-completeness/1", "run_id": "0f" * 16, "state": "complete",
            "evidence": [{"check": "expected-outputs", "result": "pass"}, {"check": "values-rows", "result": "pass",
                                                                           "detail": "3 row(s)"}],
            "missing_outputs": [], "native_exit_code": 0}


def valid_observables():
    return {"schema": "detsim-observables/1", "run_id": "0f" * 16, "rows": [
        {"quantity": "pixel_charge", "unit": "e", "value": "1.25e4", "uncertainty_type": "none", "point_kind": "event",
         "point": 3, "detector": "detector1", "labels": ["synthetic"], "source_sha256": "12" * 32},
        {"quantity": "drift_velocity", "unit": "cm/ns", "value": "-5.1e-3", "uncertainty_type": "numerical",
         "uncertainty": "1e-15", "point_kind": "query_point", "point": 0, "component": "x",
         "labels": ["unvalidated", "outside-validated-range"], "source_sha256": "34" * 32}]}


class Keywords(unittest.TestCase):
    def walk(self, node, where="$"):
        if isinstance(node, dict):
            for key, item in node.items():
                yield key, item, f"{where}.{key}"
                if key in ("properties", "$defs") and isinstance(item, dict):
                    for name, sub in item.items():
                        yield from self.walk(sub, f"{where}.{key}.{name}")
                elif key not in ("enum", "const", "required"):
                    yield from self.walk(item, f"{where}.{key}")
        elif isinstance(node, list):
            for i, item in enumerate(node):
                yield from self.walk(item, f"{where}[{i}]")

    def test_only_supported_keywords_and_anchored_patterns(self):
        allowed = SUPPORTED_KEYWORDS | ANNOTATION_KEYWORDS
        patterns = 0
        for name in SCHEMA_NAMES:
            for key, item, where in self.walk(load_schema(name)):
                with self.subTest(schema=name, at=where):
                    self.assertIn(key, allowed)
                    if key == "pattern":
                        patterns += 1
                        self.assertTrue(item.startswith("^") and item.endswith("$"), item)
                        re.compile(item)
        self.assertGreaterEqual(patterns, 15)

    def test_the_validator_ignores_an_unsupported_keyword(self):
        """Why uniqueness is a code check: uniqueItems is not implemented, so a schema using it would pass duplicates."""
        self.assertNotIn("uniqueItems", SUPPORTED_KEYWORDS)
        self.assertTrue(validate([1, 1], {"type": "array", "uniqueItems": True}).ok)
        task = valid_task()
        task["inputs"].append(dict(task["inputs"][0]))
        self.assertEqual(validate(task, "detector_task.json").errors, [])  # the schema alone accepts the duplicate
        self.assertIn("inputs.duplicate_path", codes(schemas.check_task(task)))

    def test_search_versus_fullmatch(self):
        """contracts/schema.py applies pattern with re.search, where $ matches before a trailing newline."""
        obs = valid_observables()
        obs["rows"][0]["value"] = "1.25e4\n"
        self.assertTrue(validate(obs, "detsim_observables.json").ok)  # schema alone: accepted
        self.assertIn("pattern.fullmatch", codes(schemas.check_observables(obs)))
        task = valid_task()
        task["environment_ref"] = ENV + "\n"
        self.assertTrue(validate(task, "detector_task.json").ok)
        self.assertIn("pattern.fullmatch", codes(schemas.check_task(task)))


class TaskContract(unittest.TestCase):
    def test_valid(self):
        self.assertEqual(schemas.check_task(valid_task()), [])

    def test_negative_fixtures(self):
        def mutated(fn):
            task = valid_task()
            fn(task)
            return task
        cases = {
            "schema.additional": [lambda t: t.update(replicate=1), lambda t: t["budget"].update(memory_mb=10),
                                  lambda t: t["inputs"][0].update(sha256=ENV)],
            "schema.required": [lambda t: t.pop("budget"), lambda t: t.pop("environment_ref"),
                                lambda t: t["budget"].pop("timeout_s"), lambda t: t["inputs"][0].pop("role")],
            "schema.pattern": [lambda t: t.update(capability_id="Synthetic"), lambda t: t.update(environment_ref="AB" * 32),
                               lambda t: t["inputs"][0].update(path="/etc/passwd"),
                               lambda t: t["inputs"][0].update(path="inputs/é.conf"),
                               lambda t: t["inputs"][0].update(role="Config")],
            "schema.const": [lambda t: t.update(schema="detector-task/2")],
            "schema.type": [lambda t: t["budget"].update(timeout_s=60.0), lambda t: t.update(parameters=[])],
            "schema.minimum": [lambda t: t["budget"].update(timeout_s=0)],
            "path.dot_segment": [lambda t: t["inputs"][0].update(path="../outside.conf"),
                                 lambda t: t["inputs"][0].update(path="inputs/./a.conf")],
            "hash_scope.float": [lambda t: t["parameters"].update(gain=1.5)],
            "hash_scope.nan-or-infinity": [lambda t: t["parameters"].update(gain=float("nan"))],
            "hash_scope.non-ascii-key": [lambda t: t["parameters"].update({"é": 1})],
            "hash_scope.environment-reference": [lambda t: t.update(objective="read $HOME")],
            "quantity.value_not_string": [lambda t: t["parameters"].update(threshold={"value": 600, "unit": "e"})],
        }
        for code, mutations in cases.items():
            for i, fn in enumerate(mutations):
                with self.subTest(code=code, case=i):
                    self.assertIn(code, codes(schemas.check_task(mutated(fn))))

    def test_units_and_decimals(self):
        quantity = {"$ref": "detector_task.json#/$defs/quantity"}
        for unit in ("e", "um", "V/cm", "cm/ns", "1", "%", "keV", "e/um", "T", "m^2"):
            with self.subTest(unit=unit):
                self.assertTrue(validate({"value": "1.5", "unit": unit}, quantity).ok)
        for unit in ("", "µm", "V cm", "1 m", "-V", "/cm"):
            with self.subTest(unit=unit):
                self.assertFalse(validate({"value": "1.5", "unit": unit}, quantity).ok)
        for value in ("1500", "+1.50E+3", "-0", "0.000"):
            self.assertTrue(validate({"value": value, "unit": "e"}, quantity).ok, value)
        for bad in ({"value": ".5", "unit": "e"}, {"value": "1_000", "unit": "e"}, {"value": 1.5, "unit": "e"},
                    {"value": "1"}, {"unit": "e"}, {"value": "1", "unit": "e", "error": "0.1"}):
            with self.subTest(bad=bad):
                self.assertFalse(validate(bad, quantity).ok)


class PlanContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.scratch = tempfile.TemporaryDirectory()
        project = synthetic.make_project(Path(cls.scratch.name) / "project é")
        cls.plan, cls.digest = detsim_plan.assemble_plan(json.loads((project / "task.json").read_text("utf-8")),
                                                         project, synthetic, detsim_profile.profile("macos-g0"))

    @classmethod
    def tearDownClass(cls):
        cls.scratch.cleanup()

    def mutated(self, fn):
        plan = copy.deepcopy(self.plan)
        fn(plan)
        return plan

    def test_valid(self):
        self.assertEqual(schemas.check_plan(self.plan), [])
        self.assertEqual(self.plan["task"]["parameters"]["threshold"]["value"], "6e2")

    def test_negative_fixtures(self):
        def rendered(plan, raw):
            entry = plan["execution"]["files"][0]
            entry["content"] = base64.b64encode(raw).decode("ascii")
            entry["sha256"] = hashlib.sha256(raw).hexdigest()

        cases = {
            "schema.additional": [lambda p: p.update(replicate=0), lambda p: p["execution"].update(shell="sh"),
                                  lambda p: p["profile"].update(host="x")],
            "schema.pattern": [lambda p: p["execution"]["expected_outputs"].append("ATTEMPT_ROOT/../x"),
                               lambda p: p["execution"]["files"][0].update(path="/tmp/run.conf"),
                               lambda p: p["capability"].update(version="1.0")],
            "hash_scope.float": [lambda p: p["environment"]["identity"].update(gcc=11.5),
                                 lambda p: p["capability"]["required_guarantees"].update(x=0.5)],
            "schema.type": [lambda p: p["execution"].update(timeout_s=1.5)],
            "execution.executable_root": [lambda p: p["execution"]["argv"].__setitem__(0, "/usr/bin/sim")],
            "execution.host_path": [lambda p: p["execution"]["argv"].append("--out=/tmp/x"),
                                    lambda p: p["execution"]["environment"].update(G4LEDATA="/opt/data")],
            "execution.variable_name": [lambda p: p["execution"]["environment"].update({"1BAD": "x"})],
            "execution.file_hash": [lambda p: p["execution"]["files"][0].update(sha256="00" * 32)],
            "execution.base64": [lambda p: p["execution"]["files"][0].update(content="QUJ="),  # not canonical
                                 lambda p: p["execution"]["files"][0].update(content="QU*=")],
            "execution.file_too_large": [lambda p: rendered(p, b"x" * (1048576 + 1))],
            "execution.duplicate_path": [lambda p: p["execution"]["expected_outputs"].append(
                p["execution"]["expected_outputs"][0])],
            "quantity.not_normalized": [lambda p: p["task"]["parameters"]["threshold"].update(value="600")],
            "environment.identity_hash": [lambda p: p["environment"]["identity"].update(kind="other")],
            "schema.const": [lambda p: p["canonicalization"].update(decimal="decimal/2")],
        }
        for code, mutations in cases.items():
            for i, fn in enumerate(mutations):
                with self.subTest(code=code, case=i):
                    self.assertIn(code, codes(schemas.check_plan(self.mutated(fn))))


class CompletenessContract(unittest.TestCase):
    def test_valid(self):
        self.assertEqual(schemas.check_completeness(valid_completeness()), [])
        partial = valid_completeness()
        partial.update(state="partial", missing_outputs=["ATTEMPT_ROOT/raw/values.csv"])
        self.assertEqual(schemas.check_completeness(partial), [])

    def test_negative_fixtures(self):
        def mutated(fn):
            doc = valid_completeness()
            fn(doc)
            return doc
        cases = {
            "completeness.complete_with_failures": [lambda d: d["evidence"][0].update(result="fail"),
                                                    lambda d: d.update(missing_outputs=["ATTEMPT_ROOT/raw/x"])],
            "completeness.failure_without_evidence": [lambda d: d.update(state="invalid")],
            "completeness.duplicate_check": [lambda d: d["evidence"].append({"check": "values-rows", "result": "pass"})],
            "vocab.unknown_term": [lambda d: d["evidence"][0].update(result="maybe")],
            "schema.enum": [lambda d: d.update(state="done")],
            "schema.pattern": [lambda d: d.update(missing_outputs=["raw/values.csv"]), lambda d: d.update(run_id="0F" * 16)],
            "schema.min_items": [lambda d: d.update(evidence=[])],
            "schema.additional": [lambda d: d.update(observables=[])],
        }
        for code, mutations in cases.items():
            for i, fn in enumerate(mutations):
                with self.subTest(code=code, case=i):
                    self.assertIn(code, codes(schemas.check_completeness(mutated(fn))))


class ObservablesContract(unittest.TestCase):
    def test_valid(self):
        self.assertEqual(schemas.check_observables(valid_observables()), [])

    def test_negative_fixtures(self):
        def mutated(fn):
            doc = valid_observables()
            fn(doc)
            return doc
        cases = {
            "observables.uncertainty_missing": [lambda d: d["rows"][1].pop("uncertainty")],
            "observables.uncertainty_for_none": [lambda d: d["rows"][0].update(uncertainty="1e0")],
            "observables.uncertainty_negative": [lambda d: d["rows"][1].update(uncertainty="-1e-15")],
            "observables.duplicate_label": [lambda d: d["rows"][0].update(labels=["synthetic", "synthetic"])],
            "vocab.unknown_term": [lambda d: d["rows"][0].update(labels=["great"])],
            "schema.any_of": [lambda d: d["rows"][0].update(uncertainty_type="gaussian")],
            "schema.pattern": [lambda d: d["rows"][0].update(value="12500"), lambda d: d["rows"][0].update(unit="µm"),
                               lambda d: d["rows"][0].update(quantity="Pixel Charge"),
                               lambda d: d["rows"][0].update(source_sha256="12" * 31)],
            "schema.type": [lambda d: d["rows"][0].update(value=12500.0)],
            "schema.minimum": [lambda d: d["rows"][0].update(point=-1)],
            "schema.required": [lambda d: d["rows"][0].pop("unit"), lambda d: d["rows"][0].pop("source_sha256")],
            "schema.additional": [lambda d: d["rows"][0].update(error="1")],
        }
        for code, mutations in cases.items():
            for i, fn in enumerate(mutations):
                with self.subTest(code=code, case=i):
                    self.assertIn(code, codes(schemas.check_observables(mutated(fn))))


if __name__ == "__main__":
    unittest.main()
