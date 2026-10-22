"""Cross-artifact check Phase 2, release R2 formats (architecture sections 8.1 and 9.4): SemVer pre-releases, the
registry key (rule_id, version) with retired versions, check-context 1.1.0 (DR-2: no 'required') paired with 1.1.0
pre-release suites, and the context conversion 1.0.0 -> 1.1.0 (V90). No rule outcome changes here: the 1.1.0-dev.1
suites list the 1.0.0 rules."""
from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import analysis_check_cases as cases  # noqa: E402

DEV = "1.1.0-dev.1"


def to_1_1(c) -> None:
    """A draft context in format 1.1.0 on the 1.1.0-dev.1 suites (what the converter writes)."""
    c.context["context_version"] = "1.1.0"
    c.context["suite"] = dict(c.context["suite"], version=DEV)
    c.context["suites"] = [dict(s, version=DEV) for s in c.context.get("suites", [])]
    for key in ("roots", "ratio_roots"):
        for r in c.context.get(key, []):
            r.pop("required", None)


def states(bundle: Path, root: Path) -> dict:
    from contracts import analysis_check as ac
    view, diags = ac.load_subject(bundle, root)
    rep = ac.evaluate(view, diags)
    return {o["obligation_id"]: (o["state"], o["reason"]) for o in rep["obligations"]}


class SemverPrerelease(unittest.TestCase):
    def test_full_versions_parse_and_order_by_semver_precedence(self):
        from contracts import semver
        self.assertEqual(semver.parse_full(DEV), (1, 1, 0, ("dev", 1)))
        self.assertTrue(semver.is_prerelease(DEV))
        self.assertFalse(semver.is_prerelease("1.1.0"))
        order = ["1.0.0", "1.1.0-0", "1.1.0-alpha", "1.1.0-dev.1", "1.1.0-dev.2", "1.1.0-dev.10", "1.1.0", "1.1.1"]
        self.assertEqual(sorted(reversed(order), key=semver.precedence), order)

    def test_release_parse_and_ranges_still_refuse_prereleases(self):
        from contracts import semver
        with self.assertRaises(ValueError):
            semver.parse(DEV)
        with self.assertRaises(ValueError):
            semver.satisfies(DEV, ">=1.0.0")

    def test_malformed_versions_are_refused(self):
        from contracts import semver
        for bad in ("1.1.0-", "01.1.0", "1.1", "1.1.0-dev..1", "1.1.0-01", "1.1.0+build"):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                semver.parse_full(bad)


class RegistryKey(unittest.TestCase):
    def registry(self) -> dict:
        from contracts import rule_registry
        return json.loads(rule_registry.REGISTRY.read_text(encoding="utf-8"))

    @staticmethod
    def live(doc) -> dict:
        return next(r for r in doc["rules"] if r["kind"] != "legacy")

    def codes(self, doc) -> list[str]:
        from contracts import rule_registry
        return [f.code for f in rule_registry.check(doc).findings if f.severity == "error"]

    def test_the_shipped_registry_passes(self):
        self.assertEqual(self.codes(self.registry()), [])

    def test_registry_1_2_0_keys_rules_by_id_and_version(self):
        doc = self.registry()
        doc["registry_version"] = "1.2.0"
        old = copy.deepcopy(self.live(doc))
        old.update(version="0.9.0", lifecycle="retired")
        old.pop("source_sha256", None)
        doc["rules"].append(old)
        self.assertEqual(self.codes(doc), [])
        doc["rules"].append(copy.deepcopy(self.live(doc)))
        self.assertIn("registry.duplicate_rule", self.codes(doc))

    def test_registry_1_1_0_keeps_one_entry_per_rule(self):
        doc = self.registry()
        old = copy.deepcopy(self.live(doc))
        old.update(version="0.9.0", lifecycle="retired")
        doc["rules"].append(old)
        self.assertIn("registry.duplicate_rule", self.codes(doc))

    def test_a_retired_version_needs_no_implementation_but_a_live_one_does(self):
        doc = self.registry()
        doc["registry_version"] = "1.2.0"
        ghost = copy.deepcopy(self.live(doc))
        ghost.update(version="0.9.0", lifecycle="shadow")
        ghost.pop("source_sha256", None)
        doc["rules"].append(ghost)
        self.assertIn("registry.rule_not_implemented", self.codes(doc))
        ghost["lifecycle"] = "retired"
        self.assertEqual(self.codes(doc), [])

    def test_prerelease_rule_versions_are_valid(self):
        from contracts.schema import validate
        doc = self.registry()
        self.live(doc)["version"] = DEV
        self.assertNotIn("schema.pattern", [f.code for f in validate(doc, "rule_registry.json").errors])


class Context110(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_dev_suites_exist_for_every_suite_with_the_same_rules(self):
        from contracts import analysis_check as ac
        for sid in ("counting-chain", "ratio-subset", "model-card", "run-lineage"):
            old, dev = ac.load_suite(sid, "1.0.0"), ac.load_suite(sid, DEV)
            self.assertEqual(dev["version"], DEV)
            self.assertEqual((dev["rules"], dev["generator"], dev.get("mode")), (old["rules"], old["generator"], old.get("mode")))

    def test_a_1_1_0_context_on_dev_suites_gives_the_1_0_0_outcomes(self):
        a, b = self.tmp / "a", self.tmp / "b"
        self.assertEqual(states(cases.ratio_case(b, to_1_1), b), states(cases.ratio_case(a), a))

    def test_freeze_refuses_required_in_a_1_1_0_context(self):
        from contracts.analysis_bundle import BundleRefused

        def v(c):
            to_1_1(c)
            c.context["roots"][0]["required"] = False
        with self.assertRaises(BundleRefused) as cm:
            cases.positive_case(self.tmp / "r", v)
        self.assertEqual(cm.exception.code, "bundle.context_version")

    def test_freeze_refuses_mismatched_context_and_suite_versions(self):
        from contracts.analysis_bundle import BundleRefused

        def new_context_old_suite(c):
            to_1_1(c)
            c.context["suite"]["version"] = "1.0.0"

        def old_context_new_suite(c):
            c.context["suite"]["version"] = DEV
        for name, v in (("new-old", new_context_old_suite), ("old-new", old_context_new_suite)):
            with self.subTest(name), self.assertRaises(BundleRefused) as cm:
                cases.positive_case(self.tmp / name, v)
            self.assertEqual(cm.exception.code, "bundle.context_version")

    def test_check_reports_the_same_pairing_as_input_invalid(self):
        from contracts.analysis_checks.context import version_findings
        ctx = {"context_version": "1.1.0", "suite": {"id": "counting-chain", "version": "1.0.0"},
               "roots": [{"root_id": "a", "required": True}]}
        self.assertEqual(sorted(f["code"] for f in version_findings(ctx)),
                         ["context.required_removed", "context.suite_version"])
        self.assertEqual(version_findings({"context_version": "1.0.0", "suite": {"id": "x", "version": "1.0.0"},
                                           "roots": [{"root_id": "a", "required": False}]}), [])

    def test_check_report_refuses_a_dev_suite_report(self):
        from contracts import analysis_check as ac
        from contracts import permit
        r = self.tmp / "p"
        bundle = cases.positive_case(r, to_1_1)
        view, diags = ac.load_subject(bundle, r)
        rep = ac.evaluate(view, diags)
        codes = [f["code"] for f in permit.cheap_refusals(rep, json.loads(bundle.read_text()), r, "$")]
        self.assertIn("permit.report_prerelease_suite", codes)


class V90ContextConversion(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_a_1_0_0_context_converts_to_1_1_0_with_the_same_outcomes(self):
        from contracts import migrate
        src, dst = self.tmp / "src", self.tmp / "dst"
        bundle = cases.ratio_case(src)
        res = migrate.migrate(src, bundle, dst, [{"item": "check-context", "converter": "context-1.0.0-to-1.1.0"}])
        self.assertEqual(res["status"], "complete", res["diagnostics"])
        new = json.loads(Path(res["bundle"]).read_text())
        ctx_ref = next(i["ref"] for i in new["items"] if i["role"] == "context")
        ctx = json.loads((dst / ctx_ref).read_text())
        self.assertEqual(ctx["context_version"], "1.1.0")
        self.assertEqual({s["version"] for s in [ctx["suite"]] + ctx.get("suites", [])}, {DEV})
        self.assertEqual(states(Path(res["bundle"]), dst), states(bundle, src))
        marker = json.loads(Path(res["marker"]).read_text())
        self.assertEqual(marker["conversions"][0]["converter"], "context-1.0.0-to-1.1.0")

    def test_a_deferred_root_is_not_converted(self):
        from contracts import migrate

        def deferred(c):
            c.context["roots"][0]["required"] = False
        src, dst = self.tmp / "src", self.tmp / "dst"
        bundle = cases.positive_case(src, deferred)
        res = migrate.migrate(src, bundle, dst, [{"item": "check-context", "converter": "context-1.0.0-to-1.1.0"}])
        self.assertEqual(res["status"], "refused")
        self.assertEqual(res["diagnostics"][0]["code"], "migrate.converter_failed")
        self.assertIn("exception", res["diagnostics"][0]["message"])
        self.assertFalse((dst / migrate.MARKER).exists())

    def test_required_true_is_dropped(self):
        from contracts.migrate import context_1_0_to_1_1
        ctx = {"context_version": "1.0.0", "suite": {"id": "counting-chain", "version": "1.0.0"},
               "roots": [{"root_id": "a", "required": True}]}
        out = context_1_0_to_1_1(ctx)
        self.assertNotIn("required", out["roots"][0])
        self.assertEqual(ctx["roots"][0]["required"], True)


if __name__ == "__main__":
    unittest.main()
