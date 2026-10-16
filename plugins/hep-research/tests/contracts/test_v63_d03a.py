"""v6.3 D03a: namespace ownership, the alias contract (V13, V29) and consumers that respect profile load errors.

Every consumer of profile loading results in the D01 inventory (docs/dev/v6.3/m0-baseline.md §4) has a
failing-profile case here: a profile the registry reports as incompatible is never used. Profiles are synthetic
stand-ins (tests/contracts/make_registry_fixtures.py) written to temporary folders outside the plugin."""
import copy
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests" / "contracts"))
from make_registry_fixtures import profile, write_profile  # noqa: E402

from contracts.vocab import Vocabulary  # noqa: E402

FIX = ROOT / "contracts" / "fixtures"
INCOMPATIBLE = FIX / "registry" / "incompatible_version" / "profiles" / "experiments" / "a"
SPEC = FIX / "artifacts" / "valid" / "measurement_ratio.json"
REVIEW = ROOT / "skills" / "hep-measurement" / "scripts" / "review_measurement_spec.py"
BAD_ID = "experiment:fixture-exp-a"


def run(*args, cwd=ROOT):
    p = subprocess.run([sys.executable, *map(str, args)], capture_output=True, text=True, cwd=cwd, timeout=300)
    return p.returncode, p.stdout, p.stderr


def project(root: Path, pid: str = BAD_ID, local=("local-profiles/exp-a",), copy_bad=True) -> Path:
    if copy_bad:
        shutil.copytree(INCOMPATIBLE, root / "local-profiles" / "exp-a")
    cfg = {"schema_version": "1.0.0", "plugin_version": ">=0.11,<1.0",
           "experiments": [{"profile": pid, "version": "1.0.0"}], "local_profile_paths": list(local)}
    path = root / "hep-research.project.json"
    path.write_text(json.dumps(cfg), encoding="utf-8")
    return path


def alias(**kw):
    rec = {"owner": "experiment:fixture-exp-a", "vocabulary": "convention_keys", "alias": "fxa:old_key",
           "target": "fxa:new_key", "rationale": "renamed key, same meaning", "versions": ">=1.0",
           "introduced": "0.12.0", "retire_not_before": None}
    rec.update(kw)
    return rec


def owners():
    return {"fxa": "experiment:fixture-exp-a", "fxb": "experiment:fixture-exp-b"}


def vocab():
    v = Vocabulary()
    v.extend("convention_keys", ["fxa:new_key", "fxa:old_key", "fxa:other"], ["fxa"])
    v.extend("convention_keys", ["fxb:key"], ["fxb"])
    v.extend("levels", ["fxa:instrument"], ["fxa"])
    return v


class V13AliasKeys(unittest.TestCase):
    """V13: old and new alias keys with equal values resolve the same; a conflict is rejected with both sources; the
    input and its file are unchanged."""

    @unittest.expectedFailure  # V13 (D03a): contracts.resolve does not exist yet
    def test_equal_values_merge_and_conflicts_are_rejected(self):
        from contracts import resolve
        aliases = [alias()]
        self.assertEqual(resolve.check_aliases(aliases, owners(), vocab()), [])
        self.assertEqual(resolve.canonical_term("fxa:old_key", "convention_keys", aliases), "fxa:new_key")
        with tempfile.TemporaryDirectory() as td:
            f = Path(td) / "conventions.json"
            f.write_text(json.dumps({"fxa:old_key": "pc/Ze", "fxa:new_key": "pc/Ze", "fxa:other": 1}))
            before = f.read_bytes()
            doc = json.loads(before)
            snapshot = copy.deepcopy(doc)
            view = resolve.canonicalize_keys(doc, "convention_keys", aliases)
            self.assertEqual(view["status"], "ok")
            self.assertEqual(view["view"], {"fxa:new_key": "pc/Ze", "fxa:other": 1})
            self.assertEqual(view["sources"]["fxa:new_key"], ["fxa:new_key", "fxa:old_key"])
            conflict = resolve.canonicalize_keys({"fxa:old_key": "pc/Ze", "fxa:new_key": "E/Z"}, "convention_keys",
                                                 aliases)
            self.assertEqual(conflict["status"], "rejected")
            self.assertIsNone(conflict["view"])
            [finding] = conflict["findings"]
            self.assertEqual(finding["code"], "alias.key_conflict")
            self.assertEqual(finding["sources"], {"fxa:new_key": "E/Z", "fxa:old_key": "pc/Ze"})
            self.assertEqual(doc, snapshot)
            self.assertEqual(f.read_bytes(), before)


class V29AliasContract(unittest.TestCase):
    """V29: an alias taking over another owner's name, or a cycle, is rejected; so are ambiguity, a missing target and
    an alias that would need a numeric conversion (that is a comparison mapping)."""

    def codes(self, aliases):
        from contracts import resolve
        return {f["code"] for f in resolve.check_aliases(aliases, owners(), vocab())}

    @unittest.expectedFailure  # V29 (D03a): contracts.resolve does not exist yet
    def test_cross_owner_takeover(self):
        self.assertIn("alias.cross_owner", self.codes([alias(owner="experiment:fixture-exp-b")]))
        self.assertIn("alias.cross_owner", self.codes([alias(alias="frame", target="fxa:new_key")]))

    @unittest.expectedFailure  # V29 (D03a)
    def test_cycle(self):
        self.assertIn("alias.cycle", self.codes([alias(alias="fxa:old_key", target="fxa:other"),
                                                 alias(alias="fxa:other", target="fxa:old_key")]))

    @unittest.expectedFailure  # V29 (D03a)
    def test_ambiguous_missing_target_conversion_and_malformed(self):
        self.assertIn("alias.ambiguous", self.codes([alias(), alias(target="fxa:other")]))
        self.assertIn("alias.target_missing", self.codes([alias(target="fxa:absent")]))
        self.assertIn("alias.needs_conversion", self.codes([alias(conversion={"factor": 2})]))
        self.assertIn("alias.bad_record", self.codes([{"alias": "fxa:old_key"}]))

    @unittest.expectedFailure  # V29 (D03a)
    def test_a_promotion_by_the_owner_passes(self):
        # the original owner aliases its namespaced term to a base term (the D03b promotion pattern)
        self.assertEqual(self.codes([alias(vocabulary="levels", alias="fxa:instrument", target="detector")]), set())


class NamespaceOwnership(unittest.TestCase):
    """Each namespace of the visible closure (public registry, project local profiles, --local profiles) has exactly
    one owner; a second declaring profile is reported as profile.namespace_collision and neither is used."""

    @unittest.expectedFailure  # D03a: no ownership check at load time yet
    def test_two_local_profiles_sharing_a_namespace(self):
        from contracts.registry import load_registry
        with tempfile.TemporaryDirectory() as td:
            a = profile("experiment:fixture-ns-a", "experiment", "fxshared")
            b = profile("experiment:fixture-ns-b", "experiment", "fxshared")
            write_profile(Path(td), "a", a)
            write_profile(Path(td), "b", b)
            res = load_registry(None, [Path(td) / "a", Path(td) / "b"])
        self.assertIn("profile.namespace_collision", {f.code for f in res.report.errors})
        self.assertNotIn("experiment:fixture-ns-a", res.profiles)
        self.assertNotIn("experiment:fixture-ns-b", res.profiles)

    def test_composition_check_stays_as_second_line(self):
        from contracts.comparison.composition import compose
        a = profile("experiment:fixture-ns-a", "experiment", "fxshared")
        b = profile("experiment:fixture-ns-b", "experiment", "fxshared")
        self.assertIn("compose.namespace_collision", {e["code"] for e in compose([a, b])["errors"]})


class ConsumersRespectLoadErrors(unittest.TestCase):
    """One failing-profile case per consumer of the D01 inventory."""

    @unittest.expectedFailure  # D03a: validate_registry keeps the profile as loaded
    def test_registry_resolver_returns_an_explicit_failure(self):
        from contracts.registry import load_registry
        res = load_registry(INCOMPATIBLE.parents[1] / "registry.json")
        self.assertNotIn(BAD_ID, res.profiles)
        self.assertIn("profile.incompatible_version", res.rejected[BAD_ID])

    def test_registry_cli_output_is_unchanged(self):
        code, out, _ = run("contracts/registry.py", "--registry", INCOMPATIBLE.parents[1] / "registry.json")
        doc = json.loads(out)
        self.assertEqual((code, doc["ok"], doc["profiles"]), (1, False, [BAD_ID]))

    @unittest.expectedFailure  # D03a: load_project binds the incompatible profile
    def test_load_project_does_not_bind_it(self):
        from contracts.project import load_project
        with tempfile.TemporaryDirectory() as td:
            proj = load_project(project(Path(td)))
        self.assertEqual(proj.profiles, [])
        self.assertIn("project.profile_rejected", {f.code for f in proj.report.errors})
        self.assertEqual(proj.bound_ids, [BAD_ID])

    @unittest.expectedFailure  # D03a: resolve_context returns the configured IDs of an invalid project
    def test_project_resolve_context(self):
        from contracts.project import load_project, resolve_context
        with tempfile.TemporaryDirectory() as td:
            proj = load_project(project(Path(td)))
        r = resolve_context({}, proj, needs_profile=True)
        self.assertEqual((r["decision"], r["experiments"]), ("invalid", []))

    @unittest.expectedFailure  # D03a: review_measurement_spec.py ignores the load report
    def test_review_measurement_spec_refuses(self):
        with tempfile.TemporaryDirectory() as td:
            code, out, err = run(REVIEW, SPEC, "--profiles-from", project(Path(td)))
        self.assertEqual(code, 2, out)
        self.assertIn("profile.incompatible_version", err)

    def test_validate_cli_already_fails(self):
        with tempfile.TemporaryDirectory() as td:
            code, out, _ = run("contracts/validate.py", SPEC, "--profiles-from", project(Path(td)))
        self.assertEqual(code, 1)
        self.assertIn("profile.incompatible_version", {f["code"] for f in json.loads(out)["findings"]})

    @unittest.expectedFailure  # D03a: communication_project downgrades the load errors to warnings
    def test_communication_project_fails_and_binds_nothing(self):
        from contracts import communication_project as cproj
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            project(root)
            (root / "record.json").write_text("{}", encoding="utf-8")
            ctx = cproj.resolve_context(root / "record.json", root)
            code, _, _ = run("contracts/communication_project.py", root / "record.json", "--root", root)
        self.assertEqual(ctx["profiles"], [])
        sev = {f["code"]: f["severity"] for f in ctx["findings"]}
        self.assertEqual(sev.get("resolution.project_config_invalid"), "error")
        self.assertEqual(code, 1)

    def test_load_blinding_already_refuses(self):
        from contracts.project import load_blinding
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(ValueError):
                load_blinding(project(Path(td)))


if __name__ == "__main__":
    unittest.main()
