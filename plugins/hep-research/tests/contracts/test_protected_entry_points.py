"""P1.3 bypass suite (C07, plugin half; HC-09, K08): every formal-use entry point of R5.4 §13.3 refuses protected use when
the revocation or qualification input is missing, empty, truncated, replaced, stale or writable by the running account,
when the qualification is expired, when the project's agent_policy was edited away from its authoritative copy, when an
input is revoked, and when an artifact needs an unknown capability; the lower-level functions refuse when called
directly. Each case has a valid control in the same synthetic protected project, so a refusal is caused by the defect
and nothing else. Formal-use entry points (publication) refuse even the control until permits exist. Synthetic data only.

The custodian-written files are modeled by evaluating them for another account (tests/protected_fixture.py)."""
from __future__ import annotations

import contextlib
import hashlib
import importlib.util
import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from core.protected.guard import ProtectedUseRefused  # noqa: E402
from tests.protected_fixture import ProtectedProject  # noqa: E402

FIXTURE = ROOT / "contracts" / "fixtures" / "artifacts" / "valid" / "computational_run.json"
MODES = ("missing", "empty", "truncated", "replaced", "stale", "writable", "no-qualification", "expired-qualification",
         "edited-policy")
REFUSAL_PREFIXES = ("protected.", "source.", "revocation.")
# entry points refused even with valid protected inputs, and the one code expected there (consumers of this suite,
# such as the deployment's live C07 check, read it): batch commands that reach a scheduler or settle a submission
BATCH = "protected.batch_needs_trusted_submitter"
REFUSED_IN_CONTROL = {f"lib:campaign.{n}": {BATCH} for n in
                      ("submit(approved)", "confirm_submission", "abandon_submission", "reset", "cancel(approved)",
                       "clear_orphan_risk")}


def load_script(rel: str):
    path = ROOT / rel
    name = "protected_suite_" + rel.replace("/", "_").replace("-", "_").removesuffix(".py")
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def codes_of(result) -> set[str]:
    """Finding codes of a Report, a Project, a report dict or a refusal dict."""
    rep = getattr(result, "report", result)
    if hasattr(rep, "findings"):
        return {f.code for f in rep.findings}
    if isinstance(result, dict):
        return {f.get("code") for f in result.get("findings", []) if isinstance(f, dict)}
    return set()


def outcome_lib(fn) -> tuple[str, set[str]]:
    try:
        res = fn()
    except ProtectedUseRefused as exc:
        return "refused", {r["code"] for r in exc.refusals}
    except Exception:  # noqa: BLE001  the control may fail on synthetic placeholder arguments: it was not refused
        return "ran", set()
    codes = codes_of(res)
    refused = {c for c in codes if isinstance(c, str) and c.startswith(REFUSAL_PREFIXES)}
    return ("refused", refused) if refused else ("ran", codes)


def outcome_cli(main, argv) -> tuple[str, set[str]]:
    out = io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
        try:
            code = main(list(argv))
        except SystemExit as exc:
            code = exc.code
        except ProtectedUseRefused as exc:  # an entry point must never let this escape its command line
            return "escaped", {r["code"] for r in exc.refusals}
        except Exception:  # noqa: BLE001
            return "ran", set()
    text = out.getvalue()
    if code == 3 and '"entry_point"' in text:
        doc = json.loads(text[text.index("{"):])
        return "refused", {r["code"] for r in doc["refusals"]}
    return "ran", set()


class Env:
    """Paths and inputs inside the protected project."""

    def __init__(self, pp: ProtectedProject):
        self.pp = pp
        self.proj = pp.project
        doc = json.loads(FIXTURE.read_text())
        self.doc = doc
        self.art = pp.artifact("art.json", doc)
        self.cap_doc = dict(doc, required_capabilities=["core:not-implemented-anywhere"])
        self.cap_art = pp.artifact("cap.json", self.cap_doc)
        self.changes = pp.artifact("changes.json", {"changes": [{"id": "c1", "parameter": "p", "motivation": "control sample",
                                                                "looked_at": ["control-region data"]}]})
        self.campaign = self.proj / "campaign"
        self.campaign.mkdir(exist_ok=True)
        self.state = self.proj / "state"
        self.state.mkdir(exist_ok=True)
        self.batch_cfg = pp.artifact("batch.json", {"campaign_dir": str(self.campaign)})
        spec = {"manifest": {"manifest_hash": "0" * 64, "chunks": [{"id": "c0", "start": 0, "stop": 1, "seed": 1}]},
                "cmd": f"{sys.executable} -c pass"}
        self.spec = pp.artifact("spec.json", spec)
        self.out = self.proj / "runner-out"


def cli_entries(env: Env):
    """(name, main, argv, reads_artifacts, formal) for every command-line entry point."""
    a = str(env.art)
    return [
        ("contracts/validate.py", load_script("contracts/validate.py").main, [a], True, False),
        ("contracts/dependencies.py", load_script("contracts/dependencies.py").main, [a, "--root", str(env.proj)], True, False),
        ("contracts/comparison/gate.py", load_script("contracts/comparison/gate.py").main, [a, a], True, False),
        ("contracts/project.py", load_script("contracts/project.py").main, [str(env.proj)], False, False),
        ("combine_measurements.py", load_script("skills/hep-statistics/scripts/combine_measurements.py").main, [a], True, False),
        ("hepdata_export.py", load_script("adapters/hepdata/assets/hepdata_export.py").main, [a], True, True),
        ("hepdata_record.py", load_script("adapters/hepdata/assets/hepdata_record.py").main, [a], True, False),
        ("batch_campaign.py", load_script("adapters/batch-schedulers/batch_campaign.py").main,
         ["status", "--config", str(env.batch_cfg)], False, False),
        ("local_partition.py", load_script("skills/hep-computing/scripts/local_partition.py").main, [a], False, False),
        ("bayes_diagnostics.py", load_script("skills/hep-statistics/scripts/bayes_diagnostics.py").main, [a], False, False),
        ("core/stats/template_fit.py", load_script("core/stats/template_fit.py").main, [a], False, False),
        ("mask_blinded_bins.py", load_script("skills/hep-measurement/scripts/mask_blinded_bins.py").main, [a], False, False),
        ("review_analysis_change.py", load_script("skills/hep-measurement/scripts/review_analysis_change.py").main,
         [str(env.changes)], False, False),
        ("environment_manifest.py", load_script("skills/hep-computing/scripts/environment_manifest.py").main,
         ["record", "--inputs", a], False, False),
        ("core/evidence/ledger.py", load_script("core/evidence/ledger.py").main, [a], False, False),
        ("core/evidence/query.py", load_script("core/evidence/query.py").main, [a], False, False),
        ("check_manuscript.py", load_script("skills/hep-communication/scripts/check_manuscript.py").main,
         [str(env.proj)], False, False),
    ]


def lib_entries(env: Env):
    """(name, callable, formal) for the lower-level functions, called directly with placeholder arguments: the guard
    runs before any argument is used."""
    from contracts import dependencies, project, validate
    from contracts.comparison import combination, gate, model_set
    from core.blinding import blinding
    from core.evidence import ledger, query
    from core.partition import campaign, engine
    from core.stats import template_fit
    comb = load_script("skills/hep-statistics/scripts/combine_measurements.py")
    hx = load_script("adapters/hepdata/assets/hepdata_export.py")
    hr = load_script("adapters/hepdata/assets/hepdata_record.py")
    bd = load_script("skills/hep-statistics/scripts/bayes_diagnostics.py")
    rac = load_script("skills/hep-measurement/scripts/review_analysis_change.py")
    em = load_script("skills/hep-computing/scripts/environment_manifest.py")
    region = {"variable": "m", "low": 1.0, "high": 2.0}
    c = env.campaign
    return [
        ("validate.validate_artifact", lambda: validate.validate_artifact(env.doc), False),
        ("dependencies.validate_dependencies", lambda: dependencies.validate_dependencies(env.art, env.proj), False),
        ("gate.gate", lambda: gate.gate({}, {}), False),
        ("gate.check", lambda: gate.check(env.doc, env.doc), False),
        ("combination.plan_combination", lambda: combination.plan_combination([]), False),
        ("model_set.model_set", lambda: model_set.model_set([]), False),
        ("model_set.envelope", lambda: model_set.envelope({}, {}), False),
        ("combine_measurements.combine", lambda: comb.combine({}), False),
        ("hepdata_export.build_tables", lambda: hx.build_tables(env.doc, env.proj, "t", "d"), True),
        ("hepdata_record.build", lambda: hr.build(None), False),
        ("campaign.submit", lambda: campaign.submit(c, None, {}), False),
        ("campaign.resubmit", lambda: campaign.resubmit(c, None, {}), False),
        ("campaign.confirm_submission", lambda: campaign.confirm_submission(c, "s", {}), False),
        ("campaign.submit(approved)", lambda: campaign.submit(c, None, {}, approved=True), False),
        ("campaign.abandon_submission", lambda: campaign.abandon_submission(c, "s", "r"), False),
        ("campaign.reset", lambda: campaign.reset(c, [], "r"), False),
        ("campaign.cancel(approved)", lambda: campaign.cancel(c, None, approved=True), False),
        ("campaign.clear_orphan_risk", lambda: campaign.clear_orphan_risk(c, None, "s", "r"), False),
        ("campaign.merge", lambda: campaign.merge(c), False),
        ("engine.run", lambda: engine.run({}, env.state, None), False),
        ("engine.merge", lambda: engine.merge({}, env.state), False),
        ("template_fit.bb_fit", lambda: template_fit.bb_fit({}), False),
        ("template_fit.bb_toys", lambda: template_fit.bb_toys({}, 1, 1), False),
        ("template_fit.wbb_fit", lambda: template_fit.wbb_fit({}), False),
        ("template_fit.wbb_toys", lambda: template_fit.wbb_toys({}, 1, 1), False),
        ("bayes_diagnostics.diagnose", lambda: bd.diagnose([], (0.5,), 1.01, 100), False),
        ("review_analysis_change.review", lambda: rac.review({"id": "c1"}), False),
        ("blinding.mask_binned", lambda: blinding.mask_binned([0, 1, 2, 3], [1, 2, 3], region), False),
        ("blinding.mask_ratio", lambda: blinding.mask_ratio([1], [1], [False]), False),
        ("blinding.seal", lambda: blinding.seal([0, 1, 2, 3], [1, 2, 3], region), False),
        ("blinding.scan_paths", lambda: blinding.scan_paths([str(env.art)], [7.0]), False),
        ("blinding.check_figure", lambda: blinding.check_figure(None, region), False),
        ("blinding.load_project_blinding", lambda: blinding.load_project_blinding(env.proj / "hep-research.project.json"), False),
        ("project.load_project", lambda: project.load_project(env.proj), False),
        ("environment_manifest.record", lambda: em.record([]), False),
        ("ledger.check_ledger", lambda: ledger.check_ledger([], []), False),
        ("query.query_ledger", lambda: query.query_ledger(b"[]", b"[]", {}), False),
    ]


def runner_outcome(env: Env) -> tuple[str, set[str]]:
    runner = load_script("core/partition/runner.py")
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        code = runner.main(["--spec", str(env.spec), "--out-dir", str(env.out), "--chunk", "c0", "--attempt", "a0"])
    return ("refused", {"runner"}) if code == 3 else ("ran", set())


class ProtectedEntryPointTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.pp = ProtectedProject(self.tmp.name).start()
        self.env = Env(self.pp)
        self.cwd = os.getcwd()
        os.chdir(self.pp.project)

    def tearDown(self):
        os.chdir(self.cwd)
        self.pp.stop()
        self.pp.cleanup_modes()
        self.tmp.cleanup()

    def break_inputs(self, mode: str) -> None:
        if mode == "edited-policy":  # the agent points the project copy at its own files: it no longer matches
            cfg_path = self.pp.project / "hep-research.project.json"
            cfg = json.loads(cfg_path.read_text())
            cfg["agent_policy"]["protected_inputs"]["revocation_log"] = str(self.pp.project / "my-log.jsonl")
            cfg_path.write_text(json.dumps(cfg))
        else:
            self.pp.fail(mode)

    def all_outcomes(self):
        out = {}
        for name, main, argv, _, _ in cli_entries(self.env):
            out["cli:" + name] = outcome_cli(main, argv)
        for name, fn, _ in lib_entries(self.env):
            out["lib:" + name] = outcome_lib(fn)
        out["cli:core/partition/runner.py"] = runner_outcome(self.env)
        return out

    def formal_names(self):
        return ({"cli:" + n for n, *_, f in cli_entries(self.env) if f}
                | {"lib:" + n for n, _, f in lib_entries(self.env) if f})

    def test_control_runs_every_entry_point_except_formal_use(self):
        formal = self.formal_names()
        for name, (state, codes) in self.all_outcomes().items():
            with self.subTest(entry=name):
                if name in formal:
                    self.assertEqual((state, codes), ("refused", {"protected.formal_use_unavailable"}))
                elif name in REFUSED_IN_CONTROL:
                    self.assertEqual((state, codes), ("refused", REFUSED_IN_CONTROL[name]))
                else:
                    self.assertEqual(state, "ran", f"{name} refused a valid protected context: {codes}")

    def test_every_failure_mode_is_refused_everywhere(self):
        for mode in MODES:
            with self.subTest(mode=mode):
                self.tearDown()
                self.setUp()
                self.break_inputs(mode)
                for name, (state, codes) in self.all_outcomes().items():
                    with self.subTest(mode=mode, entry=name):
                        self.assertEqual(state, "refused", f"{name} ran with {mode} protected inputs")
                        self.assertTrue(codes, name)

    def test_revoked_input_is_refused(self):
        sha = hashlib.sha256(self.env.art.read_bytes()).hexdigest()
        self.pp.revoke("artifact", sha256=sha)
        for name, main, argv, _, _ in cli_entries(self.env):
            if str(self.env.art) not in argv:
                continue
            with self.subTest(entry=name):
                state, codes = outcome_cli(main, argv)
                self.assertEqual(state, "refused")
                self.assertIn("protected.input_revoked", codes)  # before formal use is even considered
        from contracts import dependencies
        rep = dependencies.validate_dependencies(self.env.art, self.env.proj)
        self.assertIn("protected.input_revoked", codes_of(rep))
        from core.blinding import blinding
        with self.assertRaises(ProtectedUseRefused):
            blinding.scan_paths([str(self.env.art)], [7.0])

    def test_unknown_capability_is_refused(self):
        for name, main, argv, reads, _ in cli_entries(self.env):
            if not reads:
                continue
            with self.subTest(entry=name):
                state, codes = outcome_cli(main, [str(self.env.cap_art) if x == str(self.env.art) else x for x in argv])
                self.assertEqual(state, "refused")
                self.assertTrue(codes & {"protected.unknown_capability", "protected.formal_use_unavailable"}, codes)
        from contracts import validate
        self.assertIn("contract.unknown_capability", codes_of(validate.validate_artifact(self.env.cap_doc)))

    def test_revoked_qualification_is_refused(self):
        self.pp.revoke("qualification", ref="qual-synthetic-1")
        state, codes = outcome_lib(lambda: __import__("contracts.project", fromlist=["x"]).load_project(self.env.proj))
        self.assertEqual((state, codes), ("refused", {"protected.qualification_revoked"}))

    def test_qualification_for_another_plugin_or_policy_is_refused(self):
        from contracts import project
        self.pp.write_qualification(plugin={"release": "9.9.9", "digest": "9" * 64})
        self.assertIn("protected.qualification_other_plugin", outcome_lib(lambda: project.load_project(self.env.proj))[1])
        self.pp.write_qualification(policy_sha256="8" * 64)
        self.assertIn("protected.qualification_other_policy", outcome_lib(lambda: project.load_project(self.env.proj))[1])

    def test_outside_protected_mode_nothing_changes(self):
        """The same calls in a project without agent_policy never see a protected-use finding."""
        cfg_path = self.pp.project / "hep-research.project.json"
        cfg = json.loads(cfg_path.read_text())
        cfg.pop("agent_policy")
        cfg_path.write_text(json.dumps(cfg))
        self.pp.fail("missing")  # broken inputs do not matter outside protected mode
        for name, (state, codes) in self.all_outcomes().items():
            with self.subTest(entry=name):
                self.assertEqual(state, "ran", f"{name}: {codes}")


if __name__ == "__main__":
    unittest.main()


class SchemaAgreementTests(unittest.TestCase):
    """core cannot use the schema engine, so core.protected writes the record rules out; they must agree with the
    schemas on valid records and on single-field mutations of them."""

    def mutations(self, rec: dict):
        yield rec
        for k in list(rec):
            yield {x: v for x, v in rec.items() if x != k}
            for bad in ("", 0, None, [], "x" * 3, True):
                yield dict(rec, **{k: bad})
            if isinstance(rec[k], dict):
                for sub in self.mutations(rec[k]):
                    yield dict(rec, **{k: sub})
        yield dict(rec, extra=1)

    def agree(self, schema, problem, rec):
        from contracts.schema import validate
        for m in self.mutations(rec):
            with self.subTest(record=json.dumps(m, sort_keys=True)[:160]):
                self.assertEqual(validate(m, schema).ok, problem(m) is None)

    def test_qualification(self):
        from core.protected.guard import qualification_problem
        with tempfile.TemporaryDirectory() as d:
            pp = ProtectedProject(d)
            rec = json.loads(pp.qual.read_text())
        self.agree("qualification_record.json", qualification_problem, rec)

    def test_revocation_records(self):
        from core.protected import revocation_log as rl
        g = rl.genesis("log", "custodian", "2026-10-14T08:00:00Z")
        ev = rl.next_event([g], {"kind": "artifact", "sha256": "a" * 64, "ref": "art.json"}, "r", "c", "2026-10-14T09:00:00Z")
        self.agree({"$ref": "revocation_event.json#/$defs/genesis"}, rl.genesis_problem, g)
        self.agree("revocation_event.json", rl.event_problem, ev)
        self.agree("revocation_head.json", rl.head_problem, rl.head_of([g, ev], "src", "2026-10-14T10:00:00Z"))


class ReviewFindingTests(unittest.TestCase):
    """Regressions for the review of the first implementation: each case failed open or raised before the fix."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.pp = ProtectedProject(Path(self.tmp.name) / "p").start()
        self.env = Env(self.pp)
        self.outside = Path(self.tmp.name) / "outside"
        self.outside.mkdir()

    def tearDown(self):
        self.pp.stop()
        self.pp.cleanup_modes()
        self.tmp.cleanup()

    def guard_codes(self, **kw):
        from core.protected.guard import guard
        try:
            guard("test", **kw)
        except ProtectedUseRefused as exc:
            return {r["code"] for r in exc.refusals}
        return set()

    def test_anchor_digest_follows_the_launcher(self):
        """hep-claude (deployment) anchors agent_policy by the canonical JSON SHA-256 of the policy without
        authoritative_copy; the root-owned copy may be formatted freely and may name itself."""
        import hashlib as hl
        from core.protected.revocation_log import canonical_sha256 as csha
        pol = dict(self.pp.policy)
        self.pp._write(self.pp.policy_file, json.dumps(dict(pol, authoritative_copy={"location": "x", "sha256": "y"}),
                                                       indent=4, sort_keys=False).encode())
        self.assertEqual(self.guard_codes(paths=[self.env.art]), set())
        cfg_path = self.pp.project / "hep-research.project.json"
        cfg = json.loads(cfg_path.read_text())
        cfg["agent_policy"]["authoritative_copy"]["sha256"] = hl.sha256(self.pp.policy_file.read_bytes()).hexdigest()
        cfg_path.write_text(json.dumps(cfg))  # the byte digest is not the anchor
        self.assertIn("protected.policy_anchor_mismatch", self.guard_codes(paths=[self.env.art]))
        self.assertNotEqual(csha(pol), cfg["agent_policy"]["authoritative_copy"]["sha256"])

    def test_qualification_revoked_by_digest(self):
        from core.protected.revocation_log import canonical_sha256
        q = json.loads(self.pp.qual.read_text())
        self.pp.revoke("qualification", sha256=canonical_sha256(q))
        self.assertIn("protected.qualification_revoked", self.guard_codes(paths=[self.env.art]))

    def test_link_from_outside_the_project_is_detected(self):
        link = self.outside / "x.json"
        link.symlink_to(self.env.art)
        self.pp.fail("empty")
        cwd = os.getcwd()
        os.chdir(self.outside)
        try:
            self.assertIn("revocation.empty", self.guard_codes(paths=[link]))
        finally:
            os.chdir(cwd)

    def test_unreadable_config_fails_closed(self):
        (self.outside / "hep-research.project.json").write_text('{"agent_policy": {"policy_version": ')
        (self.outside / "a.json").write_text("{}")
        self.assertIn("protected.config_unreadable", self.guard_codes(paths=[self.outside / "a.json"]))
        (self.outside / "hep-research.project.json").write_text("{not json")  # no sign of a policy: unchanged
        from core.protected.guard import detect
        cwd = os.getcwd()
        os.chdir(self.outside)
        try:
            self.assertFalse(detect([self.outside / "a.json"])[0])
        finally:
            os.chdir(cwd)

    def test_revoked_by_canonical_digest_ref_and_upper_case(self):
        from core.protected.revocation_log import canonical_sha256
        self.pp.revoke("artifact", sha256=canonical_sha256(self.env.doc))  # the file itself is indented JSON
        self.assertIn("protected.input_revoked", self.guard_codes(paths=[self.env.art]))
        self.tearDown()
        self.setUp()
        self.pp.revoke("artifact", ref="art.json")
        self.assertIn("protected.input_revoked", self.guard_codes(paths=[self.env.art]))
        from contracts import dependencies
        down = self.pp.artifact("down.json", dict(self.env.doc, artifact_id="down", inputs=[
            {"ref": "art.json", "sha256": hashlib.sha256(self.env.art.read_bytes()).hexdigest(),
             "status": self.env.doc.get("status", [])}]))
        self.assertIn("dependency.revoked", codes_of(dependencies.validate_dependencies(down, self.env.proj)))
        self.tearDown()
        self.setUp()
        self.pp.revoke("artifact", sha256="ab" * 32)
        self.assertIn("protected.input_revoked", self.guard_codes(paths=[self.env.cap_art], digests=["AB" * 32]))

    def test_unreadable_input_is_refused(self):
        os.chmod(self.env.art, 0)
        try:
            if os.access(self.env.art, os.R_OK):
                self.skipTest("running with privileges that read any file")
            self.assertIn("protected.input_unreadable", self.guard_codes(paths=[self.env.art]))
        finally:
            os.chmod(self.env.art, 0o644)

    def test_malformed_protected_input_is_a_refusal_not_a_crash(self):
        self.pp.policy["policy_version"] = "1.0.0"
        body = b'{"bad": "\\ud800"}'
        self.pp._write(self.pp.qual, body)
        self.assertTrue(self.guard_codes(paths=[self.env.art]))
        self.pp._write(self.pp.log, b'[' * 100000 + b'\n')
        self.assertTrue(self.guard_codes(paths=[self.env.art]))

    def test_exposure_record_written_by_the_session_is_not_trusted_in_protected_mode(self):
        from contracts.lineage import load_exposure
        from core.protected.guard import CURRENT, establish
        rec = self.pp.artifact("records/exposure.json", {"record_version": "1.0.0", "analysis": "a",
                                                          "source": {"snapshot_id": "s", "sha256": "1" * 64},
                                                          "previous_sha256": None, "entries": []})
        os.chmod(rec, 0o666)  # writable by the session's account (the fixture models other files as custodian-owned)
        self.assertIsNotNone(load_exposure(rec))  # outside a protected command: read as given
        token = CURRENT.set(establish([rec]))
        try:
            self.assertIsNone(load_exposure(rec))  # inside: replaceable by the session, so unknown
        finally:
            CURRENT.reset(token)
