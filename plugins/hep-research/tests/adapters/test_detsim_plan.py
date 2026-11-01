"""T-PLAN (docs/dev/detector-simulation/TASK.md 16.1) and the W3a command line of detsim.py.

Plan assembly and the rebuild comparison (run step 3) with the simulator-free backend
tests/adapters/detsim_backend_synthetic.py: the same plan from different working folders and from a moved project; a
replaced input, changed backend or shared-layer code, a changed environment record or another profile -> plan-stale
with the mismatched fields; one extra argv or a one-byte change in a rendered file -> plan-stale; a wrong
--plan-digest -> digest-mismatch; another profile -> another plan_digest. The command line (describe, check, prepare,
prepare --digest-only) runs as a subprocess with the backend injected, answers one JSON object with a status and a
stable error_code and exits 0-3 only (run and inspect are tested in test_detsim_run.py). SYNTHETIC inputs; no
simulator is run; passes with a TMPDIR whose name has spaces and non-ASCII characters.
"""
import base64
import contextlib
import copy
import hashlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / "adapters" / "detector-simulation" / "assets"
HERE = Path(__file__).resolve().parent
for _entry in (str(ROOT), str(ASSETS), str(HERE)):
    if _entry not in sys.path:
        sys.path.insert(0, _entry)

import detsim  # noqa: E402
import detsim_backend_synthetic as synthetic  # noqa: E402
import detsim_canonical as canonical  # noqa: E402
import detsim_plan  # noqa: E402
import detsim_profile  # noqa: E402
from detsim_plan import DetsimError  # noqa: E402
from tests._platform import needs  # noqa: E402

MACOS = detsim_profile.profile("macos-g0")
LINUX = detsim_profile.profile("linux-g0")
# argv[1:4] = plugin root, assets, tests/adapters; argv[4] = modules to hide ("-" for none); the rest is detsim's argv
HARNESS = ("import sys; sys.dont_write_bytecode = True; sys.path[:0] = sys.argv[1:4]; "
           "[sys.modules.__setitem__(m, None) for m in sys.argv[4].split(',') if m != '-']; "
           "import detsim, detsim_backend_synthetic as backend; "
           "sys.exit(detsim.main(sys.argv[5:], backends=dict(detsim.DEFAULT_BACKENDS, synthetic=backend)))")


def run_cli(args, cwd=None, hide="-"):
    """detsim with the synthetic backend in a fresh interpreter: (exit code, parsed JSON answer, stderr)."""
    proc = subprocess.run([sys.executable, "-I", "-c", HARNESS, str(ROOT), str(ASSETS), str(HERE), hide, *args],
                          capture_output=True, text=True, timeout=120, cwd=cwd or tempfile.gettempdir())
    return proc.returncode, json.loads(proc.stdout), proc.stderr


def run_file(args, cwd=None):
    """The real adapters/detector-simulation/assets/detsim.py file, default backends only."""
    proc = subprocess.run([sys.executable, "-I", str(ASSETS / "detsim.py"), *args], capture_output=True, text=True,
                          timeout=120, cwd=cwd or tempfile.gettempdir())
    return proc.returncode, json.loads(proc.stdout), proc.stderr


def task_of(project: Path) -> dict:
    return json.loads((project / "task.json").read_text(encoding="utf-8"))


class ProjectCase(unittest.TestCase):
    def setUp(self):
        self.scratch = tempfile.TemporaryDirectory()
        self.addCleanup(self.scratch.cleanup)
        self.project = synthetic.make_project(Path(self.scratch.name) / "project é 漢")

    def assemble(self, profile=MACOS, project=None, **kw):
        project = project or self.project
        return detsim_plan.assemble_plan(task_of(project), project, synthetic, profile, **kw)

    def assert_stale(self, plan, fields, profile=MACOS, **kw):
        with self.assertRaises(DetsimError) as ctx:
            detsim_plan.rebuild_comparison(plan, self.project, synthetic, profile, **kw)
        answer = ctx.exception.answer()
        self.assertEqual((answer["status"], answer["error_code"]), ("refused", "plan-stale"), answer)
        for field in fields:
            self.assertTrue(any(f == field or f.startswith(field + "/") for f in answer["mismatched_fields"]),
                            (field, answer["mismatched_fields"]))
        return answer


class PlanAssembly(ProjectCase):
    def test_deterministic_and_rebuildable(self):
        plan, digest = self.assemble()
        again, digest_again = self.assemble()
        self.assertEqual(digest, digest_again)
        self.assertEqual(canonical.canonical_bytes(plan), canonical.canonical_bytes(again))
        self.assertEqual(digest, hashlib.sha256(canonical.canonical_bytes(plan)).hexdigest())
        self.assertEqual(detsim_plan.rebuild_comparison(plan, self.project, synthetic, MACOS), digest)
        self.assertEqual(detsim_plan.check_plan_digest(plan, digest), digest)
        self.assertEqual(detsim_plan.check_plan_digest(plan, None), digest)

    def test_moved_project_gives_the_same_plan(self):
        plan, digest = self.assemble()
        moved = Path(self.scratch.name) / "elsewhere" / "copy"
        shutil.copytree(self.project, moved)
        self.assertEqual(self.assemble(project=moved)[1], digest)
        self.assertNotIn(str(self.project), json.dumps(plan, ensure_ascii=False))
        self.assertNotIn(self.scratch.name, json.dumps(plan, ensure_ascii=False))

    def test_another_profile_gives_another_plan_digest(self):
        plan, digest = self.assemble(MACOS)
        linux_plan, linux_digest = self.assemble(LINUX)
        self.assertNotEqual(digest, linux_digest)
        self.assert_stale(plan, ["/profile/id", "/profile/guarantees"], profile=LINUX)

    def test_replaced_input_is_stale(self):
        plan, _ = self.assemble()
        config = self.project / "inputs" / "run config.conf"
        raw = bytearray(config.read_bytes())
        raw[0] ^= 1  # same size, one bit changed
        config.write_bytes(bytes(raw))
        answer = self.assert_stale(plan, ["/inputs/0/sha256"])
        self.assertNotIn("/inputs/0/size", answer["mismatched_fields"])

    def test_missing_input_cannot_be_rebuilt(self):
        plan, _ = self.assemble()
        (self.project / "inputs" / "run config.conf").unlink()
        answer = self.assert_stale(plan, ["/inputs"])
        self.assertEqual(answer["rebuild_error"]["error_code"], "input-missing")

    def test_changed_backend_code_is_stale(self):
        plan, _ = self.assemble()
        changed = Path(self.scratch.name) / "backend" / "detsim_backend_synthetic.py"
        changed.parent.mkdir()
        changed.write_bytes(Path(synthetic.__file__).read_bytes() + b"# one more line\n")
        with mock.patch.object(synthetic, "code_files", lambda capability: [("detsim_backend_synthetic.py", changed)]):
            self.assert_stale(plan, ["/code/backend/detsim_backend_synthetic.py"])

    def test_changed_shared_layer_code_is_stale(self):
        plan, _ = self.assemble()
        copy_dir = Path(self.scratch.name) / "assets copy"
        shutil.copytree(ASSETS, copy_dir, ignore=shutil.ignore_patterns("__pycache__"))
        self.assertEqual(detsim_plan.rebuild_comparison(plan, self.project, synthetic, MACOS, assets_dir=copy_dir),
                         canonical.digest(plan))  # an identical copy rebuilds the same plan
        target = copy_dir / "detsim_plan.py"
        raw = bytearray(target.read_bytes())
        raw[-2:-1] = b" "  # one byte
        target.write_bytes(bytes(raw))
        self.assert_stale(plan, ["/code/shared_layer/detsim_plan.py"], assets_dir=copy_dir)
        (copy_dir / "detsim_extra.py").write_text("# a new shared-layer module\n", encoding="utf-8")
        self.assert_stale(plan, ["/code/shared_layer/detsim_extra.py"], assets_dir=copy_dir)

    def test_changed_environment_record_is_stale(self):
        plan, _ = self.assemble()
        synthetic.write_env_record(self.project, variables=dict(synthetic.VARIABLES, PATH="ENV_ROOT/bin2"))
        self.assert_stale(plan, ["/environment/variables/PATH", "/execution/environment/PATH"])

    def test_corrupt_environment_record_is_stale(self):
        plan, _ = self.assemble()
        path = detsim_plan.env_record_path(detsim_plan.artifacts_root(self.project), plan["environment"]["env_identity"])
        record = json.loads(path.read_text(encoding="utf-8"))
        record["identity"]["backend_version"] = "2.0.0"  # identity no longer matches the record's name
        path.write_text(json.dumps(record), encoding="utf-8")
        answer = self.assert_stale(plan, ["/environment"])
        self.assertEqual(answer["rebuild_error"]["error_code"], "environment-record-invalid")

    def test_extra_argv_is_stale(self):
        plan, _ = self.assemble()
        plan["execution"]["argv"].append("--fast")
        self.assert_stale(plan, ["/execution/argv"])

    def test_one_byte_in_a_rendered_file_is_stale(self):
        plan, _ = self.assemble()
        entry = plan["execution"]["files"][0]
        raw = bytearray(base64.b64decode(entry["content"]))
        raw[0] = ord("S") if raw[0] != ord("S") else ord("s")
        entry["content"] = base64.b64encode(bytes(raw)).decode("ascii")
        entry["sha256"] = hashlib.sha256(bytes(raw)).hexdigest()  # a consistent but different file
        self.assert_stale(plan, ["/execution/files/0/content", "/execution/files/0/sha256"])

    def test_edited_task_is_stale(self):
        plan, _ = self.assemble()
        changed = copy.deepcopy(plan)
        changed["capability"]["descriptor_sha256"] = "00" * 32
        self.assert_stale(changed, ["/capability/descriptor_sha256"])

    def test_plan_digest_check(self):
        plan, digest = self.assemble()
        with self.assertRaises(DetsimError) as ctx:
            detsim_plan.check_plan_digest(plan, "00" * 32)
        self.assertEqual((ctx.exception.status, ctx.exception.error_code), ("refused", "digest-mismatch"))
        self.assertEqual(ctx.exception.details["actual"], digest)
        for bad in ("00" * 31, digest.upper(), "x" * 64):
            with self.subTest(bad=bad), self.assertRaises(DetsimError) as ctx:
                detsim_plan.check_plan_digest(plan, bad)
            self.assertEqual((ctx.exception.status, ctx.exception.error_code), ("rejected", "digest-format"))

    def test_input_resolution(self):
        task = task_of(self.project)
        outside = Path(self.scratch.name) / "outside.conf"
        outside.write_text("x", encoding="utf-8")
        link = self.project / "inputs" / "link.conf"
        try:
            link.symlink_to(outside)
        except OSError:
            self.skipTest("needs symlinks")
        for path, code in (("inputs/link.conf", "input-outside-project"), ("inputs/none.conf", "input-missing"),
                           ("inputs", "input-not-a-file")):
            with self.subTest(path=path):
                task["inputs"][0]["path"] = path
                with self.assertRaises(DetsimError) as ctx:
                    detsim_plan.assemble_plan(copy.deepcopy(task), self.project, synthetic, MACOS)
                self.assertEqual((ctx.exception.status, ctx.exception.error_code), ("rejected", code))

    def test_project_config_names_the_artifacts_directory(self):
        _, digest = self.assemble()
        (self.project / "hep-research.project.json").write_text(json.dumps({"artifacts_dir": "elsewhere"}), "utf-8")
        with self.assertRaises(DetsimError) as ctx:
            self.assemble()
        self.assertEqual(ctx.exception.error_code, "environment-not-validated")
        synthetic.write_env_record(self.project)
        self.assertEqual(self.assemble()[1], digest)  # the artifacts location is not in the hash scope

    def test_backend_spec_with_a_host_path_is_an_error(self):
        original = synthetic.build_spec
        broken = lambda *a: dict(original(*a), argv=["/usr/local/bin/sim"])  # noqa: E731
        with mock.patch.object(synthetic, "build_spec", broken), self.assertRaises(DetsimError) as ctx:
            self.assemble()
        self.assertEqual((ctx.exception.status, ctx.exception.error_code), ("error", "internal"))
        self.assertEqual(ctx.exception.details["reason"], "plan-invalid")


@needs("process_groups")
class CommandLine(ProjectCase):
    def test_prepare_from_different_working_folders(self):
        other = Path(self.scratch.name) / "cwd b"
        other.mkdir()
        digests = set()
        for cwd, workspace in ((self.scratch.name, str(self.project)), (str(other), str(self.project)),
                               (str(self.project), "."), (str(self.project.parent), self.project.name)):
            with self.subTest(cwd=cwd, workspace=workspace):
                code, answer, err = run_cli(["--backend", "synthetic", "prepare", "--workspace", workspace,
                                             "--task", "task.json"], cwd=cwd)
                self.assertEqual((code, answer["status"]), (0, "ok"), answer)
                self.assertEqual(answer["plan_digest"], canonical.digest(answer["plan"]))
                digests.add(answer["plan_digest"])
        self.assertEqual(len(digests), 1)
        self.assertEqual(digests, {detsim_plan.assemble_plan(task_of(self.project), self.project, synthetic,
                                                             detsim_profile.profile(detsim_profile.host_profile_id()))[1]})

    def test_digest_only(self):
        base = ["--backend", "synthetic", "prepare", "--workspace", str(self.project), "--task", "task.json"]
        _, full, _ = run_cli(base)
        answers = {}
        for replicate in (None, "0", "1", "4294967295"):
            code, answer, _ = run_cli(base + ["--digest-only"] + ([] if replicate is None else ["--replicate", replicate]))
            self.assertEqual(code, 0)
            self.assertEqual(set(answer), {"status", "parameter_digest"})
            expected = hashlib.sha256(b"detsim-run/1\x00" + bytes.fromhex(full["plan_digest"])
                                      + int(replicate or 0).to_bytes(4, "big")).hexdigest()
            self.assertEqual(answer["parameter_digest"], expected)
            answers[replicate] = answer["parameter_digest"]
        self.assertEqual(answers[None], answers["0"])
        self.assertNotEqual(answers["0"], answers["1"])
        for bad in ("-1", "4294967296", "01", "x", "1.5"):
            with self.subTest(replicate=bad):
                code, answer, _ = run_cli(base + ["--digest-only", "--replicate", bad])
                self.assertEqual((code, answer["status"], answer["error_code"]), (2, "rejected", "replicate-range"))
        code, answer, _ = run_cli(base + ["--replicate", "1"])
        self.assertEqual((code, answer["status"], answer["error_code"]), (2, "rejected", "usage"))

    def test_check(self):
        code, answer, _ = run_cli(["--backend", "synthetic", "check", "--workspace", str(self.project), "--task",
                                   "task.json"])
        self.assertEqual((code, answer["status"]), (0, "ok"), answer)
        self.assertEqual(answer["capability"], {"id": "synthetic.echo", "version": "1.0.0"})
        self.assertEqual(answer["inputs"][0]["path"], "inputs/run config.conf")
        shutil.rmtree(self.project / "hep-research-artifacts")
        code, answer, _ = run_cli(["--backend", "synthetic", "check", "--workspace", str(self.project), "--task",
                                   "task.json"])
        self.assertEqual((code, answer["status"], answer["error_code"]), (3, "incomplete", "environment-not-validated"))

    def test_status_table(self):
        """W3a rows of TASK.md 11.3: each answer is one JSON object; exits are 0-3 only."""
        def task_file(name, mutate=None, text=None):
            path = self.project / name
            if text is None:
                task = task_of(self.project)
                mutate(task)
                text = json.dumps(task)
            path.write_text(text, encoding="utf-8")
            return name

        ws = ["--workspace", str(self.project)]
        rows = [
            (["check", *ws, "--task", task_file("unknown.json", lambda t: t.update(replicate=1))],
             2, "rejected", "task-invalid"),
            (["prepare", *ws, "--task", task_file("float.json", lambda t: t["parameters"].update(seed=1.0))],
             2, "rejected", "task-invalid"),
            (["prepare", *ws, "--task", task_file("dup.json", text='{"schema": "a", "schema": "b"}')],
             2, "rejected", "task-unreadable"),
            (["prepare", *ws, "--task", task_file("nan.json", text='{"x": NaN}')], 2, "rejected", "task-unreadable"),
            (["prepare", *ws, "--task", "missing.json"], 2, "rejected", "task-unreadable"),
            (["prepare", "--workspace", str(self.project / "none"), "--task", "task.json"], 2, "rejected",
             "workspace-missing"),
            (["check", *ws, "--task", task_file("params.json", lambda t: t["parameters"].update(colour="red"))],
             2, "rejected", "parameters-invalid"),
            (["check", *ws, "--task", task_file("decimal.json", lambda t: t["parameters"].update(
                threshold={"value": "1_000", "unit": "e"}))], 2, "rejected", "task-invalid"),
            (["check", *ws, "--task", task_file("cap.json", lambda t: t.update(capability_id="synthetic.other"))],
             2, "rejected", "unknown-capability"),
            (["check", *ws, "--task", task_file("role.json", lambda t: t["inputs"][0].update(role="field"))],
             2, "rejected", "input-role-missing"),
            (["prepare", *ws, "--task", task_file("ood.json", lambda t: t["parameters"].update(
                point={"value": "5", "unit": "V/cm"}))], 1, "refused", "out-of-domain"),
            (["check", *ws, "--task", "task.json", "--probe"], 2, "rejected", "usage"),  # --probe needs --env-root
            (["run", *ws, "--plan", "missing-plan.json"], 2, "rejected", "plan-unreadable"),
            (["inspect", *ws, "--view", "state"], 2, "rejected", "usage"),  # --view state needs --run
            (["frobnicate"], 2, "rejected", "usage"),
            (["prepare", *ws], 2, "rejected", "usage"),
        ]
        for argv, exit_expected, status, error_code in rows:
            with self.subTest(argv=argv[:1] + argv[-2:]):
                code, answer, err = run_cli(["--backend", "synthetic", *argv])
                self.assertEqual((code, answer["status"], answer.get("error_code")), (exit_expected, status, error_code),
                                 answer)
                self.assertIn(code, (0, 1, 2, 3))
                self.assertNotIn("Traceback", err)

    def test_allow_outside_validated_range(self):
        task_file = self.project / "ood.json"
        task = task_of(self.project)
        task["parameters"]["point"] = {"value": "5", "unit": "V/cm"}
        task_file.write_text(json.dumps(task), encoding="utf-8")
        base = ["--backend", "synthetic", "prepare", "--workspace", str(self.project), "--task", "ood.json"]
        code, answer, _ = run_cli(base)
        self.assertEqual((code, answer["error_code"]), (1, "out-of-domain"))
        self.assertEqual(answer["issues"][0]["valid_range"]["unit"], "V/cm")
        code, answer, _ = run_cli(base + ["--allow-outside-validated-range"])
        self.assertEqual((code, answer["status"]), (0, "ok"), answer)
        self.assertIs(answer["plan"]["task"]["parameters"]["allow_outside_validated_range"], True)
        self.assertEqual(answer["plan"]["task"]["parameters"]["point"]["value"], "5e0")
        # the option is a task parameter: the same task written with it gives the same plan
        task["parameters"]["allow_outside_validated_range"] = True
        task_file.write_text(json.dumps(task), encoding="utf-8")
        self.assertEqual(run_cli(base)[1]["plan_digest"], answer["plan_digest"])

    def test_describe(self):
        code, answer, _ = run_cli(["describe"])
        self.assertEqual((code, answer["status"]), (0, "ok"))
        self.assertEqual(answer["backends"]["allpix-squared"], "present")  # W4A
        self.assertEqual(answer["backends"]["synthetic"], "in-process module")
        self.assertEqual(sorted(answer["contracts"]), ["detector-plan/1", "detector-task/1", "detsim-completeness/1",
                                                       "detsim-observables/1"])
        self.assertEqual(answer["profiles"]["linux-g0"]["guarantees"]["no_network"], "unsupported")
        code, answer, _ = run_cli(["--backend", "synthetic", "describe"])
        self.assertEqual((code, answer["capabilities"][0]["id"]), (0, "synthetic.echo"))
        code, answer, _ = run_cli(["--backend", "nope", "describe"])
        self.assertEqual((code, answer["status"], answer["error_code"]), (2, "rejected", "usage"))

    def test_real_file_without_backends(self):
        code, answer, err = run_file(["describe"])
        self.assertEqual((code, answer["status"]), (0, "ok"), err)
        self.assertEqual(answer["backends"]["garfieldpp"], "present")  # W4G
        code, answer, _ = run_file(["--backend", "allpix-squared", "check", "--workspace", str(self.project), "--task",
                                    "task.json"])  # W4A: the backend exists; a synthetic task is not its capability
        self.assertEqual((code, answer["status"], answer["error_code"]), (2, "rejected", "unknown-capability"))
        code, answer, _ = run_file(["--backend", "garfieldpp", "check", "--workspace", str(self.project), "--task",
                                    "task.json"])  # a synthetic task: the Garfield++ backend has no such capability
        self.assertEqual((code, answer["status"], answer["error_code"]), (2, "rejected", "unknown-capability"))
        code, answer, _ = run_file(["--backend", "allpix-squared", "check", "--workspace", "/nonexistent/x", "--task",
                                    "/nonexistent/x/task.json"])
        self.assertEqual((code, answer["status"], answer["error_code"]), (2, "rejected", "workspace-missing"))

    def test_exception_inside_detsim_is_json_error(self):
        def boom():
            raise RuntimeError("injected")
        broken = types.SimpleNamespace(NAME="broken", capabilities=boom)
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = detsim.main(["--backend", "broken", "describe"], backends={"broken": broken})
        answer = json.loads(out.getvalue())
        self.assertEqual((code, answer["status"], answer["error_code"]), (2, "error", "internal"))
        self.assertIn("injected", answer["message"])

    def test_unsupported_platform_is_missing_dependency(self):
        out = io.StringIO()
        with mock.patch.object(detsim_profile.hostcaps, "on_windows", return_value=True), \
                contextlib.redirect_stdout(out):
            code = detsim.main(["--backend", "synthetic", "prepare", "--workspace", str(self.project), "--task",
                                "task.json"], backends={"synthetic": synthetic})
        answer = json.loads(out.getvalue())
        self.assertEqual((code, answer["status"], answer["error_code"]), (3, "missing-dependency",
                                                                          "unsupported-platform"))

    def test_hostile_tmpdir_name(self):
        """The project and the working folder under a name with spaces and non-ASCII characters (R-07 (o))."""
        self.assertIn(" ", str(self.project))
        hostile = Path(self.scratch.name) / "dir with space é漢"
        hostile.mkdir()
        code, answer, _ = run_cli(["--backend", "synthetic", "prepare", "--workspace", str(self.project), "--task",
                                   "task.json", "--digest-only"], cwd=str(hostile))
        self.assertEqual((code, answer["status"]), (0, "ok"))
        self.assertTrue(os.path.isdir(hostile))



class ReviewRoundOne(unittest.TestCase):
    """W3a independent review round 1: F1 (unencodable answer), F2 (fullmatch everywhere), F3 (host paths and '..'
    in variables), F6 (a sibling module run as a file)."""

    def test_unencodable_answer_is_internal_error(self):
        broken = types.SimpleNamespace(NAME="broken", capabilities=lambda: (_ for _ in ()).throw(
            detsim_plan.DetsimError("refused", "x", "y", location=Path("/tmp"))))
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = detsim.main(["--backend", "broken", "describe"], backends={"broken": broken})
        answer = json.loads(out.getvalue())
        self.assertEqual((code, answer["status"], answer["error_code"]), (2, "error", "internal"))

    def test_trailing_newline_is_refused_in_completeness_and_plan(self):
        import detsim_schemas
        doc = {"schema": "detsim-completeness/1", "state": "partial", "missing_outputs": ["ATTEMPT_ROOT/x\n"],
               "evidence": [{"check": "outputs", "result": "fail"}]}
        self.assertIn("pattern.fullmatch", {f["code"] for f in detsim_schemas.check_completeness(doc)})
        findings = detsim_schemas._pattern_walk({"capability": {"id": "synthetic.echo\n"}},
                                                detsim_schemas.load_schema("detector_plan.json"),
                                                "detector_plan.json", "$")
        self.assertTrue(any(f["path"] == "$.capability.id" for f in findings), findings)

    def test_host_path_and_parent_segment_in_variables(self):
        import detsim_schemas
        found = detsim_schemas.host_path_findings([("v", "ENV_ROOT/lib:/usr/lib"), ("a", "INPUT_ROOT/../x"),
                                                   ("ok", "ENV_ROOT/lib")])
        self.assertEqual(sorted((f["path"], f["code"]) for f in found),
                         [("a", "execution.parent_segment"), ("v", "execution.host_path")])

    def test_module_run_as_a_file(self):
        script = ASSETS / "detsim_plan.py"
        help_run = subprocess.run([sys.executable, str(script), "--help"], capture_output=True, text=True, timeout=300)
        self.assertEqual(help_run.returncode, 0)
        bad = subprocess.run([sys.executable, str(script), "--frobnicate"], capture_output=True, text=True, timeout=300)
        self.assertEqual((bad.returncode, json.loads(bad.stdout)["status"]), (2, "rejected"))
        optimized = subprocess.run([sys.executable, "-OO", str(script), "--help"], capture_output=True, text=True, timeout=300)
        self.assertEqual(optimized.returncode, 0, optimized.stderr)


class ReviewRoundTwo(unittest.TestCase):
    """W3a independent review round 2: N1 (malformed budget), F9 / N6 (declared shared-layer modules)."""

    def test_malformed_budget_is_a_finding_not_a_crash(self):
        import detsim_schemas
        for budget in ("x", [1], 5):
            with self.subTest(budget=budget):
                findings = detsim_schemas.check_plan({"schema": "detector-plan/1", "task": {"budget": budget}})
                self.assertTrue(findings)

    def test_undeclared_or_missing_module_is_refused(self):
        with tempfile.TemporaryDirectory() as work_dir:
            assets = Path(work_dir) / "assets"
            shutil.copytree(ASSETS, assets)
            shutil.copy(ASSETS.parent / "adapter.json", Path(work_dir) / "adapter.json")
            (assets / "detsim_extra.py").write_text("")
            with self.assertRaises(detsim_plan.DetsimError) as caught:
                detsim_plan.shared_layer_modules(assets)
            self.assertEqual(caught.exception.details["reason"], "undeclared-module")
            (assets / "detsim_extra.py").unlink()
            (assets / "detsim_runner.py").unlink()
            with self.assertRaises(detsim_plan.DetsimError) as caught:
                detsim_plan.shared_layer_modules(assets)
            self.assertEqual(caught.exception.details["reason"], "declared-module-missing")


class ReviewRoundThree(ProjectCase):
    """W3a independent review round 3 (M1): regression tests for three round-2 behaviours."""

    def _record_path(self):
        env_identity = task_of(self.project)["environment_ref"]
        return detsim_plan.env_record_path(detsim_plan.artifacts_root(self.project), env_identity), env_identity

    def test_not_a_detsim_env_document_is_rejected(self):
        path, env_identity = self._record_path()
        good = json.loads(path.read_text(encoding="utf-8"))
        for broken in ([], dict(good, format="other/1"), dict(good, identity=[1]), dict(good, variables={"1X": "a"}),
                       dict(good, variables={"PATH": 5})):
            with self.subTest(broken=str(broken)[:40]):
                path.write_text(json.dumps(broken), encoding="utf-8")
                with self.assertRaises(DetsimError) as ctx:
                    detsim_plan.load_env_record(detsim_plan.artifacts_root(self.project), env_identity)
                self.assertEqual((ctx.exception.status, ctx.exception.error_code),
                                 ("rejected", "environment-record-unreadable"))

    def test_host_paths_in_record_variables_are_refused(self):
        path, env_identity = self._record_path()
        good = json.loads(path.read_text(encoding="utf-8"))
        for value in ("ENV_ROOT/bin:/usr/bin", "~", "ENV_ROOT/../x"):
            with self.subTest(value=value):
                path.write_text(json.dumps(dict(good, variables=dict(good["variables"], PATH=value))),
                                encoding="utf-8")
                with self.assertRaises(DetsimError) as ctx:
                    detsim_plan.load_env_record(detsim_plan.artifacts_root(self.project), env_identity)
                self.assertEqual((ctx.exception.status, ctx.exception.error_code),
                                 ("refused", "environment-record-invalid"))

    def test_trusted_code_fault_during_rebuild_is_internal(self):
        plan, _ = self.assemble()
        original = synthetic.build_spec
        broken = lambda *a: dict(original(*a), argv=["/usr/bin/x"])  # noqa: E731
        with mock.patch.object(synthetic, "build_spec", broken), self.assertRaises(DetsimError) as ctx:
            detsim_plan.rebuild_comparison(plan, self.project, synthetic, MACOS)
        self.assertEqual((ctx.exception.status, ctx.exception.error_code), ("error", "internal"))


if __name__ == "__main__":
    unittest.main()
