"""Cross-artifact check Phase 2, release R2 formats (architecture sections 8.1 and 9.4): SemVer pre-releases, the
registry key (rule_id, version) with retired versions, check-context 1.1.0 (DR-2: no 'required') paired with 1.1.0
pre-release suites, and the context conversion 1.0.0 -> 1.1.0 (V90). The 1.1.0-dev.1 suites list the 1.0.0 rules;
1.1.0-dev.2 replaces r-rep.repetition and r-ratio.correlation by 1.1.0 (G3, G17) and 1.1.0-dev.3 also
r-comp.factor_values (G4) and r-aux.use (G5), 1.1.0-dev.4 r-run.binding (G8), r-run.blinding (G7, G13) and r-run.campaign (G6),
so a 1.0.0 suite gives check.rule_not_run for them (section 8.2). On the reference cases the 1.1.0 rules give the 1.0.0 outcomes, which are
computed here with cases.r1_rules() in place of release R1."""
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

DEV = "1.1.0-dev.5"  # the last pre-release (release R2/R3 development); SUITE_1_1 is the stable 1.1.0
STABLE = cases.SUITE_1_1


to_1_1 = cases.context_1_1


def states(bundle: Path, root: Path, rules: dict | None = None) -> dict:
    from contracts import analysis_check as ac
    view, diags = ac.load_subject(bundle, root)
    rep = ac.evaluate(view, diags, rules=rules)
    return {o["obligation_id"]: (o["state"], o["reason"]) for o in rep["obligations"]}


class SemverPrerelease(unittest.TestCase):
    def test_full_versions_parse_and_order_by_semver_precedence(self):
        from contracts import semver
        self.assertEqual(semver.parse_full("1.1.0-dev.1"), (1, 1, 0, ("dev", 1)))
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
        doc["registry_version"] = "1.1.0"
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
        # each pre-release lists the 1.0.0 rules, those fixed by then at 1.1.0: dev.1 none, dev.2 G3/G17, dev.3 also
        # G4 and G5; the newest (DEV) names exactly the versions this checker implements
        from contracts import analysis_check as ac
        from contracts.analysis_checks.rules import VERSIONS
        fixed_by = {"1.1.0-dev.1": set(), "1.1.0-dev.2": {"r-rep.repetition", "r-ratio.correlation"},
                    "1.1.0-dev.3": {"r-rep.repetition", "r-ratio.correlation", "r-comp.factor_values", "r-aux.use"},
                    "1.1.0-dev.4": {"r-rep.repetition", "r-ratio.correlation", "r-comp.factor_values", "r-aux.use",
                                    "r-run.binding", "r-run.blinding", "r-run.campaign"},
                    "1.1.0-dev.5": {"r-rep.repetition", "r-ratio.correlation", "r-comp.factor_values", "r-aux.use",
                                    "r-run.binding", "r-run.blinding", "r-run.campaign"}}
        fixed_by[STABLE] = fixed_by[DEV]  # the stable suites are the last pre-release under its release version
        self.assertEqual(fixed_by[STABLE], {r for r, v in VERSIONS.items() if v == "1.1.0"})
        for sid in ("counting-chain", "ratio-subset", "model-card", "run-lineage"):
            old = ac.load_suite(sid, "1.0.0")
            for ver, fixed in fixed_by.items():
                with self.subTest(suite=sid, version=ver):
                    dev = ac.load_suite(sid, ver)
                    rules = [dict(r, version="1.1.0") if r["rule_id"] in fixed else r for r in old["rules"]]
                    gen = old["generator"]
                    if ver in ("1.1.0-dev.5", STABLE) and sid == "counting-chain":  # release R3: the new rule and generator (G1, G14)
                        k = next(i for i, r in enumerate(rules) if r["rule_id"] == "r-real.description")
                        rules.insert(k + 1, {"rule_id": "r-real.undescribed", "version": "1.0.0", "subject": "applied_effect"})
                        gen = dict(gen, version="1.1.0")
                    self.assertEqual((dev["rules"], dev["generator"], dev.get("mode")), (rules, gen, old.get("mode")))

    def test_a_1_1_0_context_on_dev_suites_gives_the_1_0_0_outcomes(self):
        # every 1.0.0 obligation keeps its outcome; the only additions are the release-R3 rule r-real.undescribed
        a, b = self.tmp / "a", self.tmp / "b"
        new, old = states(cases.ratio_case(b, to_1_1), b), states(cases.ratio_case(a), a, cases.r1_rules())
        self.assertEqual({k: v for k, v in new.items() if k in old}, old)
        self.assertEqual({k.split(":")[0] for k in set(new) - set(old)}, {"r-real.undescribed"})

    def test_a_1_0_0_suite_does_not_run_a_fixed_rule(self):
        # section 8.2: the stable 1.0.0 suites name the retired versions; they are not run, never run with new code
        out = states(cases.ratio_case(self.tmp / "a"), self.tmp / "a")
        from contracts.analysis_checks.rules import VERSIONS
        fixed = {k: v for k, v in out.items() if k.split(":")[0] in VERSIONS}
        self.assertTrue(fixed)
        self.assertEqual(set(fixed.values()), {("unverified", "check.rule_not_run")})
        self.assertNotIn(("unverified", "check.rule_not_run"),
                         {v for k, v in out.items() if k not in fixed})

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
        # a pre-release suite is refused; the stable 1.1.0 suite (release R3) is not
        from contracts import analysis_check as ac
        from contracts import permit
        for version, refused in ((DEV, True), (STABLE, False)):
            with self.subTest(suite=version):
                r = self.tmp / f"p-{version}"
                bundle = cases.positive_case(r, lambda c, v=version: to_1_1(c, v))
                view, diags = ac.load_subject(bundle, r)
                rep = ac.evaluate(view, diags)
                codes = [f["code"] for f in permit.cheap_refusals(rep, json.loads(bundle.read_text()), r, "$")]
                self.assertEqual("permit.report_prerelease_suite" in codes, refused, codes)


class InputChecks110(unittest.TestCase):
    """The input checks check-context 1.1.0 enables (G12, G15, G16, G22); a 1.0.0 context is not judged by them (P3)."""

    TABLE = {"factor_table_version": "1.0.0", "factors": {"exposure": {"values": [1.0, 2.0]},
                                                          "trigger_efficiency": {"scalar": 0.97},
                                                          "selection_efficiency": {"by_scope": {"species:p": [0.9, 0.8]}}},
             "tolerance": {"relative": 1e-6}}

    def shape(self, doc, version="1.1.0") -> list[str]:
        from contracts.analysis_check import shape_diagnostics
        items = {"cal": {"role": "calibration", "ref": "cal.json", "doc": copy.deepcopy(doc)}}
        return [d["code"] for d in shape_diagnostics(items, version)]

    def test_a_well_formed_factor_table_passes(self):
        self.assertEqual(self.shape(self.TABLE), [])

    def test_malformed_factor_tables_are_input_invalid_only_in_1_1_0(self):
        bad = []
        for path, value in ((("factors", "exposure", "values"), [1.0, "2"]), (("factors", "exposure", "values"), []),
                            (("factors", "trigger_efficiency", "scalar"), float("inf")), (("tolerance",), {"relative": -1}),
                            (("tolerance",), {"relative": "nan"}), (("tolerance",), {"relative": 1e-6, "absolute": 1}),
                            (("factor_table_version",), "2.0.0")):
            doc = copy.deepcopy(self.TABLE)
            target = doc
            for k in path[:-1]:
                target = target[k]
            target[path[-1]] = value
            bad.append(doc)
        two_forms = copy.deepcopy(self.TABLE)
        two_forms["factors"]["exposure"]["scalar"] = 1.0
        bad.append(two_forms)
        for doc in bad:
            with self.subTest(doc=doc):
                self.assertEqual(self.shape(doc), ["calibration.shape"])
                self.assertEqual(self.shape(doc, "1.0.0"), [])

    def test_auxiliary_inputs_of_model_cards_are_not_factor_tables(self):
        self.assertEqual(self.shape(cases.OBS), [])

    def test_different_bundle_coverage_contracts_for_one_table(self):
        from contracts.analysis_check import shape_diagnostics
        from contracts.effect_catalog import load_coverage
        a = load_coverage("differential-flux")
        b = copy.deepcopy(a)
        b["operators"] = b["operators"][1:]

        def items():
            return {"c1": {"role": "coverage-contract", "ref": "c1.json", "doc": copy.deepcopy(a)},
                    "c2": {"role": "coverage-contract", "ref": "c2.json", "doc": copy.deepcopy(b)}}
        it = items()
        self.assertIn("coverage.duplicate_contract", [d["code"] for d in shape_diagnostics(it, "1.1.0")])
        self.assertEqual((it["c1"]["doc"], it["c2"]["doc"]), (None, None))
        self.assertNotIn("coverage.duplicate_contract", [d["code"] for d in shape_diagnostics(items(), "1.0.0")])
        same = {"c1": {"role": "coverage-contract", "ref": "c1.json", "doc": copy.deepcopy(a)},
                "c2": {"role": "coverage-contract", "ref": "c2.json", "doc": copy.deepcopy(a)}}
        self.assertEqual(shape_diagnostics(same, "1.1.0"), [])

    def test_context_findings_follow_the_version(self):
        from contracts.analysis_checks.context import input_findings
        ctx = {"context_version": "1.1.0", "roots": [{"root_id": "a", "unit": "TODO"}, {"root_id": "b", "unit": "1/(m2 sr s GV)"}],
               "evaluations": [{"shared_parameters": [{"parameter_id": "lumi", "members": [
                   {"model": "m", "parameter": "x"}, {"model": "m", "parameter": "y"}]}]}]}
        self.assertEqual(sorted(f["code"] for f in input_findings(ctx)),
                         ["context.shared_within_model", "context.unit_placeholder"])
        self.assertEqual(input_findings(dict(ctx, context_version="1.0.0")), [])
        across = copy.deepcopy(ctx)
        across["roots"][0]["unit"] = "1"
        across["evaluations"][0]["shared_parameters"][0]["members"][1]["model"] = "n"
        self.assertEqual(input_findings(across), [])

    def test_check_reports_context_findings_as_input_invalid(self):
        from contracts import analysis_check as ac
        r = Path(self._tmp().name)
        bundle = cases.positive_case(r, to_1_1)
        doc = json.loads(bundle.read_text())
        ref = next(i["ref"] for i in doc["items"] if i["role"] == "context")
        ctx = json.loads((r / ref).read_text())
        ctx["roots"][0]["unit"] = "TODO"
        (r / ref).write_text(json.dumps(ctx))
        view, diags = ac.load_subject(bundle, r)
        self.assertIn("context.unit_placeholder", [d["code"] for d in diags if d["kind"] == "input-invalid"])

    def _tmp(self):
        t = tempfile.TemporaryDirectory()
        self.addCleanup(t.cleanup)
        return t


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
        self.assertEqual({s["version"] for s in [ctx["suite"]] + ctx.get("suites", [])}, {STABLE})  # newest installed
        new, old = states(Path(res["bundle"]), dst), states(bundle, src, cases.r1_rules())
        self.assertEqual({k: v for k, v in new.items() if k in old}, old)
        self.assertEqual({k.split(":")[0] for k in set(new) - set(old)}, {"r-real.undescribed"})
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
