"""T12 stage 2 (G05, A40; plan v9.2 Section 9.8): native inputs in run_workflow.py.

Every expectation is fixed in docs/dev/detector-reconstruction/t12-stage-plan.md ("Stage 2", N1-N6, R7, and its fix round 1, N1', N3',
N4', N7) before the runner change. The
"native binary" here is a small executable shell script written by the test, a stand-in: what matters is that it is not a .py script
and not the interpreter. The runner is loaded in this process with a pinned known release digest, as test_workflow_b1.py does: with the
digest unknown (a development tree), INC-03 never skips, and every skip test would fail for that reason alone. All inputs are SYNTHETIC.

Run from the plugin root: python -m unittest tests.skills.hep_computing.test_workflow_native -v
"""
import contextlib
import hashlib
import importlib.util
import io
import json
import os
import stat
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

PLUGIN = Path(__file__).resolve().parents[3]
RUNNER = PLUGIN / "skills" / "hep-computing" / "scripts" / "run_workflow.py"
SHIPPED = PLUGIN / "skills" / "hep-computing" / "assets" / "workflow" / "workflow.json"
TOOL = "#!/bin/sh\n# a stand-in for a native binary\nprintf 'made by the tool\\n' > \"$1\"\n"

# The extension keys of a run record and the keys of a receipt at 4c08da43, for a step with no native input and no check (N4).
OLD_EXTENSION_KEYS = {"input_manifest", "tools", "commands", "environment", "seeds", "tolerances", "exit_status", "output_hashes",
                      "argv", "script_sha256", "output_contract", "end_status", "termination", "termination_scope",
                      "leftover_processes", "artifact_digest"}
OLD_RECEIPT_KEYS = {"attempt", "step", "end_status", "termination", "outputs", "artifact_digest", "observed_inputs",
                    "conditions_resolution", "environment_ref", "started", "ended", "usage", "check_result"}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


KNOWN = {"release": "t12-stage2-test", "digest": "c" * 64, "source": "pinned by the test"}


def load_runner():
    spec = importlib.util.spec_from_file_location("run_workflow_t12s2", RUNNER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.plugin_release = lambda root=None: dict(KNOWN)
    return module


RUNNER_MODULE = load_runner()


def run(workflow: Path, work: Path, *extra):
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        code = RUNNER_MODULE.main([str(workflow), "--work", str(work), "--created", "2026-11-13", "--status", "synthetic",
                                   *map(str, extra)])
    return code, json.loads(buffer.getvalue())


class NativeInputs(unittest.TestCase):
    def setUp(self):
        self._scratch = tempfile.TemporaryDirectory()
        self.root = Path(self._scratch.name)
        self.work = self.root / "work"
        self.work.mkdir()
        self.tool = self.work / "native-tool"
        self.tool.write_text(TOOL)
        self.tool.chmod(self.tool.stat().st_mode | stat.S_IXUSR)

    def tearDown(self):
        self._scratch.cleanup()

    def workflow(self, declared=True, seeds=None, extra_inputs=()):
        step = {"id": "make", "argv": ["./native-tool", "out.txt"], "inputs": list(extra_inputs), "outputs": ["out.txt"]}
        if declared:
            step["native_inputs"] = ["native-tool"]
        if seeds is not None:
            step["seeds"] = seeds
        path = self.root / "wf.json"
        path.write_text(json.dumps({"workflow": "native", "steps": [step]}))
        return path

    def record(self):
        return json.loads((self.work / "runs" / "make.computational-run.json").read_text())

    def skipped(self, out):
        return [s.get("skipped", False) for s in out["steps"]]

    def test_n1_a_declared_native_input_is_hashed_into_the_record_and_the_receipt(self):
        code, out = run(self.workflow(), self.work, "--receipt-dir", self.root / "receipts", "--attempt-prefix", "a1:")
        self.assertEqual(code, 0, out)
        self.assertEqual(self.record()["extension"]["native_sha256"], {"native-tool": sha(self.tool)})
        self.assertNotIn("undeclared_native", self.record()["extension"])
        receipt = json.loads((self.root / "receipts" / "a1:make.receipt.json").read_text())
        self.assertEqual(receipt["native_inputs"], [{"path": "native-tool", "sha256": sha(self.tool)}])

    def test_n1_a_missing_native_input_is_rejected_before_any_step(self):
        self.tool.unlink()
        code, out = run(self.workflow(), self.work)
        self.assertEqual((code, out["status"]), (2, "rejected"), out)
        self.assertFalse((self.work / "out.txt").exists())

    def test_n2_an_unchanged_native_input_keeps_the_skip(self):
        wf = self.workflow()
        self.assertEqual(run(wf, self.work)[0], 0)
        code, out = run(wf, self.work, "--incremental")
        self.assertEqual((code, self.skipped(out)), (0, [True]), out)

    def test_n2_one_changed_byte_reruns_the_step(self):
        wf = self.workflow()
        self.assertEqual(run(wf, self.work)[0], 0)
        self.tool.write_text(TOOL + "# one more line\n")
        code, out = run(wf, self.work, "--incremental")
        self.assertEqual((code, self.skipped(out)), (0, [False]), out)
        self.assertEqual(self.record()["extension"]["native_sha256"], {"native-tool": sha(self.tool)})

    def test_n2_an_old_manifest_left_as_an_input_does_not_hide_a_changed_binary(self):
        """Section 9.8: rehashing a manifest from the last run is insufficient; the binary itself is hashed."""
        manifest = self.work / "native.manifest"
        manifest.write_text(f"{sha(self.tool)}  native-tool\n")
        wf = self.workflow(extra_inputs=["native.manifest"])
        self.assertEqual(run(wf, self.work)[0], 0)
        self.tool.write_text(TOOL + "# rebuilt\n")
        code, out = run(wf, self.work, "--incremental")
        self.assertEqual((code, self.skipped(out)), (0, [False]), out)

    def test_n3_an_undeclared_executable_is_recorded_and_never_skipped(self):
        wf = self.workflow(declared=False)
        self.assertEqual(run(wf, self.work)[0], 0)
        self.assertEqual(self.record()["extension"]["undeclared_native"], ["./native-tool"])
        self.assertNotIn("native_sha256", self.record()["extension"])
        code, out = run(wf, self.work, "--incremental")
        self.assertEqual((code, self.skipped(out)), (0, [False]), "nothing changed, but the closure is unknown: it reruns")

    def test_n6_a_changed_seed_reruns_and_an_unchanged_one_skips(self):
        self.assertEqual(run(self.workflow(seeds={"generator": 1}), self.work)[0], 0)
        code, out = run(self.workflow(seeds={"generator": 1}), self.work, "--incremental")
        self.assertEqual(self.skipped(out), [True], out)
        code, out = run(self.workflow(seeds={"generator": 2}), self.work, "--incremental")
        self.assertEqual((code, self.skipped(out)), (0, [False]), out)
        self.assertEqual(self.record()["extension"]["seeds"], {"generator": 2})

    def test_r7_a_skipped_step_writes_no_receipt_and_an_old_receipt_is_kept(self):
        wf = self.workflow()
        receipts = self.root / "receipts"
        self.assertEqual(run(wf, self.work, "--receipt-dir", receipts, "--attempt-prefix", "a1:")[0], 0)
        first = (receipts / "a1:make.receipt.json").read_bytes()
        code, out = run(wf, self.work, "--incremental", "--receipt-dir", receipts, "--attempt-prefix", "a2:")
        self.assertEqual(self.skipped(out), [True])
        self.assertFalse((receipts / "a2:make.receipt.json").exists(), "a skip is no new evidence")
        self.assertEqual((receipts / "a1:make.receipt.json").read_bytes(), first)


class ProgramsAndScripts(unittest.TestCase):
    """N3' (fix round 1, I1, I2): the program (through PATH) and an interpreter-run script are examined; other tokens are not."""

    def setUp(self):
        self._scratch = tempfile.TemporaryDirectory()
        self.root = Path(self._scratch.name)
        self.work = self.root / "work"
        self.work.mkdir()
        self.bin = self.root / "bin"
        self.bin.mkdir()
        self.path = mock.patch.dict(os.environ, {"PATH": f"{self.bin}{os.pathsep}{os.environ.get('PATH', '')}"})
        self.path.start()

    def tearDown(self):
        self.path.stop()
        self._scratch.cleanup()

    def program(self, name, text=TOOL):
        tool = self.bin / name
        tool.write_text(text)
        tool.chmod(tool.stat().st_mode | stat.S_IXUSR)
        return tool

    def workflow(self, argv, native=None, inputs=()):
        step = {"id": "make", "argv": argv, "inputs": list(inputs), "outputs": ["out.txt"]}
        if native is not None:
            step["native_inputs"] = native
        path = self.root / "wf.json"
        path.write_text(json.dumps({"workflow": "programs", "steps": [step]}))
        return path

    def extension(self):
        return json.loads((self.work / "runs" / "make.computational-run.json").read_text())["extension"]

    def twice(self, wf):
        self.assertEqual(run(wf, self.work)[0], 0)
        code, out = run(wf, self.work, "--incremental")
        self.assertEqual(code, 0, out)
        return out["steps"][0].get("skipped", False)

    def test_n3_a_program_found_through_path_is_undeclared(self):
        self.program("mytool")
        self.assertFalse(self.twice(self.workflow(["mytool", "out.txt"])))
        self.assertEqual(self.extension()["undeclared_native"], ["mytool"])

    def test_n3_a_declared_program_on_path_skips_and_reruns_when_changed(self):
        tool = self.program("mytool")
        wf = self.workflow(["mytool", "out.txt"], native=["{workflow}/bin/mytool"])
        self.assertTrue(self.twice(wf))
        self.assertNotIn("undeclared_native", self.extension())
        tool.write_text(TOOL + "# rebuilt\n")
        code, out = run(wf, self.work, "--incremental")
        self.assertEqual((code, out["steps"][0].get("skipped", False)), (0, False), out)

    def test_n3_a_shell_script_run_by_sh_is_undeclared(self):
        (self.work / "tool.sh").write_text("printf 'by sh\\n' > \"$1\"\n")
        self.assertFalse(self.twice(self.workflow(["sh", "tool.sh", "out.txt"])))
        self.assertEqual(self.extension()["undeclared_native"], ["tool.sh"])

    def test_n3_a_declared_shell_script_skips_and_reruns_when_changed(self):
        script = self.work / "tool.sh"
        script.write_text("printf 'by sh\\n' > \"$1\"\n")
        wf = self.workflow(["sh", "tool.sh", "out.txt"], native=["tool.sh"])
        self.assertTrue(self.twice(wf))
        script.write_text("printf 'by sh, changed\\n' > \"$1\"\n")
        code, out = run(wf, self.work, "--incremental")
        self.assertEqual(out["steps"][0].get("skipped", False), False, out)

    def test_n3_a_root_macro_with_arguments_is_its_script(self):
        self.program("root", "#!/bin/sh\nfor last; do :; done\nprintf 'by root\\n' > \"$last\"\n")
        (self.work / "macro.C").write_text("void macro(int n) {}\n")
        self.assertFalse(self.twice(self.workflow(["root", "-b", "-q", "macro.C(1)", "out.txt"])))
        self.assertEqual(self.extension()["undeclared_native"], ["macro.C(1)"])

    def test_n3_an_executable_given_as_an_option_value_keeps_the_old_skip(self):
        """The generated Geant4 scan's shape (probe P1 of the review): a .py wrapper with --exe /path/prog; nothing changed skips."""
        exe = self.program("g4exe")
        (self.work / "wrap.py").write_text("import sys\nopen(sys.argv[-1], 'w').write('wrapped\\n')\n")
        self.assertTrue(self.twice(self.workflow(["{python}", "wrap.py", "--exe", str(exe), "out.txt"])))
        self.assertNotIn("undeclared_native", self.extension())


class NativeInputChecks(unittest.TestCase):
    """N1', N7: native inputs are checked before the first step when they cannot be made by one; '~' is expanded; '..' is refused."""

    def setUp(self):
        self._scratch = tempfile.TemporaryDirectory()
        self.root = Path(self._scratch.name)
        self.work = self.root / "work"
        self.work.mkdir()

    def tearDown(self):
        self._scratch.cleanup()

    def workflow(self, second_native):
        steps = [{"id": "a", "argv": ["{python}", "-c", "open('a.txt', 'w').write('a')"], "outputs": ["a.txt"]},
                 {"id": "b", "needs": ["a"], "argv": ["{python}", "-c", "open('b.txt', 'w').write('b')"], "outputs": ["b.txt"],
                  "native_inputs": second_native}]
        path = self.root / "wf.json"
        path.write_text(json.dumps({"workflow": "two", "steps": steps}))
        return path

    def test_n1_an_absent_absolute_native_input_is_rejected_before_the_first_step(self):
        code, out = run(self.workflow([str(self.root / "absent" / "lib.so")]), self.work)
        self.assertEqual((code, out["status"]), (2, "rejected"), out)
        self.assertFalse((self.work / "a.txt").exists(), "nothing ran")
        self.assertFalse((self.work / "runs" / "a.computational-run.json").exists())

    def test_n1_an_absent_placeholder_native_input_is_rejected_before_the_first_step(self):
        code, out = run(self.workflow(["{workflow}/absent.so"]), self.work)
        self.assertEqual((code, out["status"]), (2, "rejected"), out)
        self.assertFalse((self.work / "a.txt").exists())

    def test_n1_a_work_relative_native_input_an_earlier_step_writes_is_allowed(self):
        code, out = run(self.workflow(["a.txt"]), self.work)
        self.assertEqual(code, 0, out)

    def test_n1_dot_dot_in_a_native_input_is_refused_at_load(self):
        code, out = run(self.workflow(["../outside.so"]), self.work)
        self.assertEqual((code, out["status"]), (2, "rejected"), out)
        self.assertFalse((self.work / "a.txt").exists())

    @unittest.skipIf(os.geteuid() == 0, "root reads every file")
    def test_n1_an_unreadable_native_input_is_rejected_not_a_traceback(self):
        lib = self.root / "lib.so"
        lib.write_text("x")
        lib.chmod(0)
        try:
            code, out = run(self.workflow([str(lib)]), self.work)
        finally:
            lib.chmod(0o600)
        self.assertEqual((code, out["status"]), (2, "rejected"), out)

    def test_n7_a_home_relative_native_input_is_expanded(self):
        lib = self.root / "lib.so"
        lib.write_text("x")
        with mock.patch.dict(os.environ, {"HOME": str(self.root)}):
            code, out = run(self.workflow(["~/lib.so"]), self.work)
        self.assertEqual(code, 0, out)
        record = json.loads((self.work / "runs" / "b.computational-run.json").read_text())
        self.assertEqual(record["extension"]["native_sha256"], {"~/lib.so": sha(lib)})


class OldRecipes(unittest.TestCase):
    """N4: a workflow without native inputs or executables gets no new key, and the interpreter and .py scripts are not 'native'."""

    def test_n4_the_shipped_workflow_records_and_receipts_have_only_the_old_keys(self):
        with tempfile.TemporaryDirectory() as scratch:
            work, receipts = Path(scratch) / "work", Path(scratch) / "receipts"
            code, out = run(SHIPPED, work, "--receipt-dir", receipts, "--attempt-prefix", "a1:")
            self.assertEqual(code, 0, out)
            for record in sorted((work / "runs").glob("*.computational-run.json")):
                with self.subTest(record=record.name):
                    self.assertEqual(set(json.loads(record.read_text())["extension"]), OLD_EXTENSION_KEYS)
            for receipt in sorted(receipts.glob("*.receipt.json")):
                with self.subTest(receipt=receipt.name):
                    self.assertEqual(set(json.loads(receipt.read_text())), OLD_RECEIPT_KEYS)
            code, out = run(SHIPPED, work, "--incremental")
            self.assertEqual([s.get("skipped", False) for s in out["steps"]], [True, True, True], out)


if __name__ == "__main__":
    unittest.main()
