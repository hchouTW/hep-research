"""Phase 0 foundations of the cross-artifact check (docs/dev/cross-artifact-check/cross-artifact-check-architecture.en.md, section
9.1; release R1): V72 version guard and rule source digests, V73 status and exit code (P6), V74 checker identity,
V75 cheap check-report refusals, V76 mutation-testing skeleton; plus default snapshots and assessment.plugin_release.
No rule outcome changes in Phase 0. Synthetic and public example content only."""
import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests" / "contracts"))
import analysis_check_mutations as mutations  # noqa: E402
import analysis_check_cases as cases  # noqa: E402

CLI = [sys.executable, str(ROOT / "contracts" / "analysis_check.py")]


def ac():
    from contracts import analysis_check
    return analysis_check


def report(bundle: Path, root: Path, **kw) -> dict:
    view, diags = ac().load_subject(bundle, root)
    return ac().evaluate(view, diags, **kw)


class Base(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.addCleanup(self.td.cleanup)
        self.n = 0

    def root(self) -> Path:
        self.n += 1
        return Path(self.td.name) / f"f{self.n}"


class V72VersionGuard(Base):
    def test_unimplemented_rule_version_is_not_run(self):
        from contracts.analysis_checks import rules
        r = self.root()
        view, _ = ac().load_subject(cases.positive_case(r, cases.context_1_1), r)
        obs = view["context"]["obligations"]["items"]
        out = rules.evaluate(view, [dict(o, rule_version="2.0.0") for o in obs])
        self.assertEqual({(o["state"], o["reason"]) for o in out}, {("unverified", "check.rule_not_run")})
        self.assertEqual([o["state"] for o in rules.evaluate(view, obs)].count("unverified"), 0)

    def test_every_suite_rule_is_implemented_at_its_version(self):
        # or retired in the registry (release R2): a retired version is not run (check.rule_not_run), never run with
        # the new code; the newest pre-release of each suite names implemented versions only
        from contracts import rule_registry as rr
        from contracts.analysis_checks.rules import IMPLEMENTED
        from contracts.semver import precedence
        retired = {(r["rule_id"], r["version"]) for r in json.loads(rr.REGISTRY.read_text())["rules"] if r["lifecycle"] == "retired"}
        newest: dict[str, tuple] = {}
        for p in sorted((ROOT / "contracts" / "rules" / "suites").glob("*.json")):
            suite = json.loads(p.read_text())
            keys = {(rule["rule_id"], rule["version"]) for rule in suite["rules"]}
            for key in keys:
                self.assertTrue(key in IMPLEMENTED or key in retired, f"{p.name}: {key}")
            if suite["suite_id"] not in newest or precedence(suite["version"]) > newest[suite["suite_id"]][0]:
                newest[suite["suite_id"]] = (precedence(suite["version"]), keys)
        for sid, (_, keys) in newest.items():
            self.assertLessEqual(keys, set(IMPLEMENTED), sid)
        self.assertFalse(retired & set(IMPLEMENTED))

    def test_unsupported_generator_is_refused_at_freeze_and_missing_at_check(self):
        from contracts.analysis_bundle import BundleRefused
        from contracts.analysis_checks import obligations
        r = self.root()
        bundle = cases.positive_case(r)
        saved = set(obligations.GENERATORS)
        obligations.GENERATORS.clear()
        try:
            rep = report(bundle, r)
            self.assertIn("definition.generator_unsupported", [d["code"] for d in rep["input_diagnostics"]])
            self.assertNotEqual(rep["status"], "complete")
            with self.assertRaises(BundleRefused) as cm:
                cases.positive_case(self.root())
            self.assertEqual(cm.exception.code, "bundle.generator_unsupported")
        finally:
            obligations.GENERATORS.update(saved)

    def test_input_checks_follow_the_context_version(self):
        from contracts.analysis_checks.context import INPUT_CHECKS, input_check_enabled
        self.assertTrue(input_check_enabled("1.0.0", "spec.duplicate_effect_id"))
        self.assertFalse(input_check_enabled("1.0.0", "a.check.added.later"))
        self.assertEqual(set(INPUT_CHECKS), {"1.0.0", "1.1.0"})  # 1.1.0: release R2 (test_analysis_check_r2_formats)
        self.assertLessEqual(INPUT_CHECKS["1.0.0"], INPUT_CHECKS["1.1.0"])

    def test_registry_records_current_source_digests(self):
        from contracts import rule_registry as rr
        doc = json.loads(rr.REGISTRY.read_text())
        self.assertEqual(doc["registry_version"], "1.2.0")
        self.assertTrue(rr.check(doc).ok, [f.as_dict() for f in rr.check(doc).findings])
        changed = copy.deepcopy(doc)
        rule = next(x for x in changed["rules"] if x["kind"] != "legacy")
        rule["source_sha256"] = "0" * 64
        codes = [f.code for f in rr.check(changed).findings]
        self.assertIn("registry.rule_source_changed", codes)
        del rule["source_sha256"]
        self.assertIn("registry.source_digest_missing", [f.code for f in rr.check(changed).findings])
        rule["version"] = "9.0.0"
        self.assertIn("registry.rule_not_implemented", [f.code for f in rr.check(changed).findings])

    def test_source_digest_ignores_formatting_but_not_code(self):
        from contracts.analysis_checks.source_digest import normalized
        a = "def f(x):\n    '''doc'''\n    return (x +\n            1)  # one\n"
        b = "def f(x):\n    return (x + 1)\n"
        c = "def f(x):\n    return (x + 2)\n"
        self.assertEqual(normalized(a), normalized(b))
        self.assertNotEqual(normalized(b), normalized(c))

    def test_a_helper_change_reaches_the_rules_that_use_it(self):
        from contracts.analysis_checks import source_digest
        from contracts.analysis_checks.rules import IMPLEMENTED
        rep = IMPLEMENTED[("r-rep.repetition", "1.1.0")]
        names = source_digest.closure(rep)
        self.assertIn("contracts.analysis_checks.rules._pair", names)
        self.assertIn("contracts.analysis_checks.scope.compare_scopes", names)


class V73StatusAndExitCode(Base):
    def test_lock_differences_without_snapshot_are_never_complete(self):
        r = self.root()
        bundle = cases.positive_case(r)
        view, diags = ac().load_subject(bundle, r)
        lock = copy.deepcopy(view["lock"])
        lock["definitions"] = [dict(d, digest="0" * 64) if d["kind"] == "rule-registry" else d for d in lock["definitions"]]
        rep = ac().evaluate(dict(view, lock=lock), diags)
        self.assertTrue(rep["lock_differences"])
        self.assertNotEqual(rep["status"], "complete")
        self.assertEqual(ac().exit_code(rep), 3)

    def test_complete_only_with_exit_zero(self):
        r = self.root()
        rep = report(cases.positive_case(r, cases.context_1_1), r)
        self.assertEqual((rep["status"], ac().exit_code(rep)), ("complete", 0))


class V74CheckerIdentity(Base):
    def test_identity_includes_loaded_modules_and_generator_files(self):
        r = self.root()
        rep = report(cases.positive_case(r), r)
        files = rep["checker"]["files"]
        self.assertTrue(set(ac().CHECKER_FILES) <= set(files))
        self.assertIn("contracts/validate.py", files)  # loaded by the legacy findings
        self.assertTrue(all(f.split("/")[0] in ("contracts", "core") for f in files))
        expected = {f: ac()._file_sha(f) for f in ac().GENERATOR_FILES}
        from contracts.release_manifest import canonical_sha256
        self.assertEqual(ac().generator_code_digest(), canonical_sha256(expected))

    def test_assessment_records_the_plugin_release(self):
        from core.protected.identity import plugin_release
        r = self.root()
        rep = report(cases.positive_case(r), r)
        self.assertEqual(rep["assessment"]["plugin_release"], plugin_release())


class V75CheapRefusals(Base):
    def setUp(self):
        super().setUp()
        self.r = self.root()
        self.bundle_path = cases.positive_case(self.r)
        self.bundle = json.loads(self.bundle_path.read_text())
        self.rep = report(self.bundle_path, self.r)

    def codes(self, rep):
        from contracts.permit import cheap_refusals
        return [x["code"] for x in cheap_refusals(rep, self.bundle, self.r, "$")]

    def test_clean_report_has_no_cheap_refusal(self):
        self.assertEqual(self.codes(self.rep), [])

    def test_dependency_missing(self):
        rep = dict(self.rep, input_diagnostics=[{"kind": "dependency-missing", "code": "x.y", "message": "m"}])
        self.assertIn("permit.report_dependency_missing", self.codes(rep))

    def test_inventory_digest_mismatch(self):
        self.assertIn("permit.report_inventory_mismatch", self.codes(dict(self.rep, inventory_digest="0" * 64)))

    def test_unreadable_frozen_inventory(self):
        (self.r / "check-context.json").unlink()
        self.assertIn("permit.report_inventory_mismatch", self.codes(self.rep))


class V76MutationSkeleton(Base):
    def test_operators_keep_their_invariants_on_the_chain_case(self):
        if not cases.HAVE_AMS:
            self.skipTest("the public AMS example artifacts are not installed")
        base = cases.chain_case(self.root(), freeze=False)
        original_root = self.root()
        orig = copy.deepcopy(base)
        orig.root = original_root
        original = report(orig.freeze(), original_root)
        for name, (_, invariant) in sorted(mutations.OPERATORS.items()):
            with self.subTest(operator=name):
                m = mutations.mutate(base, name)
                m.root = self.root()
                mutant = report(m.freeze(), m.root)
                self.assertEqual(mutations.violations(original, mutant, invariant), [])

    def test_pending_operators_are_named(self):
        self.assertEqual(set(mutations.PENDING) & set(mutations.OPERATORS), set())
        self.assertEqual(len(mutations.PENDING) + len(mutations.OPERATORS), 9)


class DefaultSnapshots(Base):
    def draft(self):
        c = cases.positive_case(self.root(), freeze=False)
        c.write()
        (c.root / "items.json").write_text(json.dumps(c.items))
        (c.root / "context.json").write_text(json.dumps(c.context))
        return c

    def freeze_cli(self, c, *extra):
        return subprocess.run(CLI + ["freeze", "--root", str(c.root), "--analysis", "a", "--items", str(c.root / "items.json"),
                                     "--context", str(c.root / "context.json"), "--out", str(c.root / "bundle.json"), *extra],
                              capture_output=True, text=True, timeout=120)

    def test_freeze_writes_snapshots_and_the_bundle_index(self):
        c = self.draft()
        res = self.freeze_cli(c)
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
        store = c.root / ".hep-research" / "snapshots"
        self.assertTrue(list(store.glob("*.json")))
        index = json.loads((c.root / ".hep-research" / "bundles.json").read_text())
        self.assertEqual(index["bundles"], [{"path": "bundle.json",
                                             "bundle_digest": json.loads((c.root / "bundle.json").read_text())["bundle_digest"]}])

    def test_no_snapshots_flag(self):
        c = self.draft()
        res = self.freeze_cli(c, "--no-snapshots")
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
        self.assertFalse((c.root / ".hep-research" / "snapshots").exists())

    def test_gc_keeps_referenced_and_lists_unreferenced(self):
        c = self.draft()
        self.assertEqual(self.freeze_cli(c).returncode, 0)
        store = c.root / ".hep-research" / "snapshots"
        kept = sorted(p.name for p in store.glob("*.json"))
        stray = store / ("f" * 64 + ".json")
        stray.write_text("{}\n")
        dry = ac().snapshots_gc(c.root)
        self.assertEqual((dry["status"], dry["unreferenced"]), ("dry-run", ["f" * 64]))
        self.assertTrue(stray.exists())
        done = ac().snapshots_gc(c.root, apply=True)
        self.assertEqual(done["deleted"], ["f" * 64])
        self.assertEqual(sorted(p.name for p in store.glob("*.json")), kept)

    def test_gc_refuses_when_an_indexed_bundle_is_unreadable(self):
        c = self.draft()
        self.assertEqual(self.freeze_cli(c).returncode, 0)
        (c.root / "bundle.json").unlink()
        res = subprocess.run(CLI + ["snapshots", "gc", "--root", str(c.root), "--apply"], capture_output=True, text=True,
                             timeout=120)
        self.assertEqual(res.returncode, 1, res.stdout)
        self.assertEqual(json.loads(res.stdout)["deleted"], [])

    def test_check_reproduces_drift_from_the_default_store(self):
        c = self.draft()
        self.assertEqual(self.freeze_cli(c).returncode, 0)
        view, diags = ac().load_subject(c.root / "bundle.json", c.root)
        lock = view["lock"]
        registry = next(d for d in lock["definitions"] if d["kind"] == "rule-registry")
        self.assertTrue((c.root / ".hep-research" / "snapshots" / f"{registry['digest']}.json").is_file())


if __name__ == "__main__":
    unittest.main()
