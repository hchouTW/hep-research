"""Reconstruction v12 B1: run_workflow.py output freshness, the complete output contract, safe output destinations and
termination (BUG-01..BUG-04; OUT-01, CACHE-01, EXEC-02). Each gap has a negative case that failed before the fix and a
positive control that must keep working. BUG-02 is tested with a pinned known release digest: with the digest unknown
INC-03 never skips, which would make the test pass falsely. All inputs are SYNTHETIC."""
import contextlib
import hashlib
import importlib.util
import io
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[3]
RUNNER = PLUGIN / "skills" / "hep-computing" / "scripts" / "run_workflow.py"
sys.path.insert(0, str(PLUGIN))
from tests._platform import needs  # noqa: E402

KNOWN = {"release": "b1-test", "digest": "b" * 64, "source": "pinned by the test"}
POSIX = os.name == "posix"


def load_runner():
    spec = importlib.util.spec_from_file_location("run_workflow_b1", RUNNER)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.plugin_release = lambda root=None: dict(KNOWN)
    return mod


def call(mod, wf: dict, work: Path, *extra):
    path = work.parent / f"wf-{time.monotonic_ns()}.json"
    path.write_text(json.dumps(wf), encoding="utf-8")
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = mod.main([str(path), "--work", str(work), "--created", "2026-10-29", *extra])
    return code, json.loads(buf.getvalue())


def run(wf: dict, work: Path, *extra):
    path = work.parent / f"wf-{time.monotonic_ns()}.json"
    path.write_text(json.dumps(wf), encoding="utf-8")
    p = subprocess.run([sys.executable, "-B", str(RUNNER), str(path), "--work", str(work), "--created", "2026-10-29",
                        *extra], capture_output=True, text=True, timeout=300)
    return p.returncode, json.loads(p.stdout)


def step(sid, code, outputs, **kw):
    return {"id": sid, "argv": ["{python}", "-c", code], "outputs": outputs, **kw}


def write(name, text="x"):
    return f"open({name!r}, 'w').write({text!r})"


def record(work: Path, sid: str) -> dict:
    return json.loads((work / "runs" / f"{sid}.computational-run.json").read_text(encoding="utf-8"))


class Base(unittest.TestCase):
    def setUp(self):
        self._t = tempfile.TemporaryDirectory()
        self.root = Path(self._t.name)
        self.work = self.root / "work"

    def tearDown(self):
        self._t.cleanup()


class StaleOutput(Base):
    """BUG-01: an exit-0 command that writes no new result must not be judged a success because of an old file."""

    def test_stale_same_name_output_fails(self):
        self.work.mkdir()
        (self.work / "out.txt").write_text("stale")
        code, out = run({"workflow": "b1", "steps": [step("s", "pass", ["out.txt"])]}, self.work)
        self.assertEqual((code, out["status"]), (1, "failed"), out)
        rec = record(self.work, "s")
        self.assertEqual(rec["extension"]["output_hashes"], {})
        self.assertIn("failed", rec["status"])
        self.assertIn("not written by this run", out["steps"][0]["stderr_tail"])

    def test_rewriting_an_existing_output_counts(self):  # positive control: a rerun in the same folder
        wf = {"workflow": "b1", "steps": [step("s", write("out.txt", "same"), ["out.txt"])]}
        self.assertEqual(run(wf, self.work)[0], 0)
        first = (self.work / "runs" / "s.computational-run.json").read_bytes()
        code, out = run(wf, self.work)
        self.assertEqual((code, out["status"]), (0, "ok"), out)
        self.assertEqual((self.work / "runs" / "s.computational-run.json").read_bytes(), first)


class OutputContract(Base):
    """BUG-02: after a new required output is added, --incremental must not skip (release digest pinned)."""

    def setUp(self):
        super().setUp()
        self.mod = load_runner()

    def test_added_output_is_not_skipped(self):
        one = {"workflow": "b2", "steps": [step("s", write("a.txt"), ["a.txt"])]}
        self.assertEqual(call(self.mod, one, self.work)[0], 0)
        two = {"workflow": "b2", "steps": [step("s", write("a.txt"), ["a.txt", "b.txt"])]}
        code, out = call(self.mod, two, self.work, "--incremental")
        self.assertFalse(out["steps"][0]["skipped"], out)
        self.assertEqual(code, 1, out)  # it reran and did not write b.txt
        self.assertFalse((self.work / "b.txt").exists())

    def test_removed_output_is_not_skipped(self):
        both = {"workflow": "b2", "steps": [step("s", write("a.txt") + ";" + write("b.txt"), ["a.txt", "b.txt"])]}
        self.assertEqual(call(self.mod, both, self.work)[0], 0)
        one = {"workflow": "b2", "steps": [step("s", write("a.txt") + ";" + write("b.txt"), ["a.txt"])]}
        code, out = call(self.mod, one, self.work, "--incremental")
        self.assertEqual(code, 0, out)
        self.assertFalse(out["steps"][0]["skipped"], out)

    def test_unchanged_contract_still_skips(self):  # positive control (INC-02 keeps working)
        wf = {"workflow": "b2", "steps": [step("s", write("a.txt") + ";" + write("b.txt"), ["a.txt", "b.txt"])]}
        self.assertEqual(call(self.mod, wf, self.work)[0], 0)
        code, out = call(self.mod, wf, self.work, "--incremental")
        self.assertEqual(code, 0, out)
        self.assertTrue(out["steps"][0]["skipped"], out)
        self.assertEqual(record(self.work, "s")["extension"]["output_contract"], ["a.txt", "b.txt"])


class Destinations(Base):
    """BUG-03: absolute, `..` and symlinked destinations are refused before any step runs."""

    def assert_refused(self, wf):
        code, out = run(wf, self.work)
        self.assertEqual((code, out["status"]), (2, "rejected"), out)
        self.assertFalse((self.work / "runs" / "s.computational-run.json").exists())

    def test_absolute_output_to_an_old_file(self):
        old = self.root / "old.txt"
        old.write_text("old result")
        self.assert_refused({"workflow": "b3", "steps": [step("s", "pass", [str(old)])]})

    def test_dotdot_output_and_input(self):
        (self.root / "old.txt").write_text("old result")
        self.assert_refused({"workflow": "b3", "steps": [step("s", "pass", ["../old.txt"])]})
        self.assert_refused({"workflow": "b3", "steps": [step("s", write("o.txt"), ["o.txt"], inputs=["../old.txt"])]})

    def test_absolute_stdout(self):
        self.assert_refused({"workflow": "b3", "steps": [step("s", "print(1)", [], stdout=str(self.root / "o"))]})

    @unittest.skipUnless(POSIX, "symlinks")
    def test_output_through_a_symlink(self):
        outside = self.root / "outside"
        outside.mkdir()
        (outside / "res.txt").write_text("old result")
        self.work.mkdir()
        (self.work / "link").symlink_to(outside, target_is_directory=True)
        self.assert_refused({"workflow": "b3", "steps": [step("s", "pass", ["link/res.txt"])]})

    @unittest.skipUnless(POSIX, "symlinks")
    def test_a_parent_the_step_turns_into_a_symlink(self):
        """Checked again after the step: a parent directory the step makes a symlink to a folder outside the work
        folder does not get the outside file recorded as an output, and the runner writes nothing through it."""
        outside = self.root / "outside"
        outside.mkdir()
        link = f"import os; os.symlink({str(outside)!r}, 'sub'); "
        code, out = run({"workflow": "b3", "steps": [step("s", link + write("sub/out.txt"), ["sub/out.txt"])]},
                        self.work)
        self.assertEqual((code, out["status"]), (1, "failed"), out)
        self.assertEqual(record(self.work, "s")["extension"]["output_hashes"], {})
        self.assertIn("symlink", out["steps"][0]["stderr_tail"])
        code, out = run({"workflow": "b3", "steps": [step("t", link.replace("'sub'", "'log'") + "print(1)", [],
                                                          stdout="log/t.txt")]}, self.root / "work2")
        self.assertEqual(code, 1, out)
        self.assertFalse((outside / "t.txt").exists())  # the runner did not write the stdout file outside

    @unittest.skipUnless(POSIX, "symlinks")
    def test_a_runs_folder_the_step_replaces_with_a_symlink(self):
        outside = self.root / "outside"
        outside.mkdir()
        code, out = run({"workflow": "b3", "steps": [step("s", "import os, shutil; shutil.rmtree('runs'); "
                                                          f"os.symlink({str(outside)!r}, 'runs'); " + write("o.txt"),
                                                          ["o.txt"])]}, self.work)
        self.assertNotEqual(code, 0, out)
        self.assertEqual(list(outside.iterdir()), [])  # no run record written outside the work folder

    def test_relative_output_runs(self):  # positive control
        code, out = run({"workflow": "b3", "steps": [step("s", "import os; os.makedirs('d', exist_ok=True);"
                                                               + write("d/r.txt"), ["d/r.txt"])]}, self.work)
        self.assertEqual((code, out["status"]), (0, "ok"), out)
        self.assertEqual(list(record(self.work, "s")["extension"]["output_hashes"]), ["d/r.txt"])


class StepIds(Base):
    """A step id names the run record and the receipt: an id that is not one plain path component is refused before
    any step runs (OUT-01), so neither file can leave its folder."""

    def test_unsafe_step_ids_are_refused(self):
        for sid in ("../../x", "a/../../y", "a/b", "/abs", ".", "..", "a\\b", " ", "-x", "a\nb"):
            with self.subTest(sid=sid):
                ran = self.root / "ran.txt"
                wf = {"workflow": "ids", "steps": [step("first", f"open({str(ran)!r}, 'w').write('x')", []),
                                                   step(sid, "pass", [], needs=["first"])]}
                code, out = run(wf, self.work, "--receipt-dir", self.root / "receipts" / "r")
                self.assertEqual((code, out["status"]), (2, "rejected"), out)
                self.assertIn("step id", out["error"])
                self.assertFalse(ran.exists())  # refused before any step ran
                self.assertFalse((self.root / "x").exists() or (self.root / "y").exists())

    def test_plain_ids_run(self):  # positive control: the ids the shipped workflows and adapters use
        steps = [step(sid, "pass", []) for sid in ("generate", "CALC-CC-B", "scan-000", "__check__", "a.b_c")]
        code, out = run({"workflow": "ids", "steps": steps}, self.work)
        self.assertEqual(code, 0, out)


@needs("process_groups")  # DEC-04: only POSIX is claimed, tested on Linux
class Termination(Base):
    """BUG-04: a timeout leaves a run record, stops the process tree and confirms it is gone."""

    LATE = ("import subprocess, sys; subprocess.Popen([sys.executable, '-c', "
            "'import time; time.sleep(2.5); open(\"late.txt\", \"w\").write(\"x\")']); ")

    def test_timeout_stops_the_tree_and_records(self):
        wf = {"workflow": "b4", "steps": [step("s", self.LATE + "import time; time.sleep(60)", ["o.txt"],
                                               timeout_s=1)]}
        t0 = time.monotonic()
        code, out = run(wf, self.work)
        self.assertLess(time.monotonic() - t0, 30)
        self.assertEqual((code, out["status"]), (1, "failed"), out)
        rec = record(self.work, "s")
        self.assertEqual((rec["extension"]["end_status"], rec["extension"]["termination"]), ("timeout", "confirmed"))
        self.assertEqual(rec["extension"]["output_hashes"], {})
        time.sleep(4)
        self.assertFalse((self.work / "late.txt").exists())

    def test_leftover_background_process_fails_the_step(self):
        wf = {"workflow": "b4", "steps": [step("s", "import subprocess, sys; subprocess.Popen([sys.executable, "
                                               "'-c', 'import time; time.sleep(2.5); open(\"late.txt\", \"w\")"
                                               ".write(\"x\")'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL"
                                               "); " + write("o.txt"), ["o.txt"])]}
        code, out = run(wf, self.work)
        self.assertEqual(code, 1, out)
        ext = record(self.work, "s")["extension"]
        self.assertEqual(ext["termination"], "confirmed")
        self.assertEqual(len(ext["leftover_processes"]), 1, ext)  # recorded, not silently stopped
        time.sleep(4)
        self.assertFalse((self.work / "late.txt").exists())

    @needs("proc_fs")  # the environment token is found through /proc (Linux)
    def test_a_process_that_leaves_the_group_is_found(self):
        """A child that starts its own session and outlives the step (as a daemonized helper: an ssh ControlPersist
        master, gpg-agent, a compiler-cache server) is found by its token, stopped and recorded; the step fails."""
        wf = {"workflow": "b4", "steps": [step("s", "import subprocess, sys; subprocess.Popen([sys.executable, "
                                               "'-c', 'import time; time.sleep(2.5); "
                                               "open(\"late.txt\", \"w\").write(\"x\")'], start_new_session=True, "
                                               "stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); "
                                               + write("o.txt"), ["o.txt"])]}
        code, out = run(wf, self.work)
        self.assertEqual(code, 1, out)
        self.assertEqual(len(record(self.work, "s")["extension"]["leftover_processes"]), 1)
        self.assertIn("left processes running", out["steps"][0]["stderr_tail"])
        time.sleep(4)
        self.assertFalse((self.work / "late.txt").exists())

    def test_a_child_that_ends_just_after_the_step_does_not_fail_it(self):
        """A child still exiting when the step's main process ends belongs to the step: the runner waits a short grace
        period for the step's processes to end on their own before it counts survivors."""
        wf = {"workflow": "b4", "steps": [step("s", "import subprocess, sys; subprocess.Popen([sys.executable, '-c', "
                                               "'import time; time.sleep(0.3)'], stdout=subprocess.DEVNULL, "
                                               "stderr=subprocess.DEVNULL); " + write("o.txt"), ["o.txt"])]}
        code, out = run(wf, self.work)
        self.assertEqual(code, 0, out)
        ext = record(self.work, "s")["extension"]
        self.assertEqual((ext["termination"], ext["leftover_processes"]), ("confirmed", []))

    @unittest.skipUnless(Path("/proc/self/stat").is_file() and sys.platform.startswith("linux"),
                         "a child subreaper (prctl) stands in for a container init that never reaps")
    def test_an_unreaped_zombie_does_not_fail_the_step(self):
        """A zombie has ended: it cannot write. Run under a subreaper that never reaps orphans (as a runner that is
        PID 1 of a container), the step's exited child stays a zombie in its process group."""
        wrapper = self.root / "subreaper.py"
        wrapper.write_text("import ctypes, runpy, sys\n"
                           "assert ctypes.CDLL(None, use_errno=True).prctl(36, 1, 0, 0, 0) == 0\n"
                           f"sys.argv = [{str(RUNNER)!r}, *sys.argv[1:]]\n"
                           f"runpy.run_path({str(RUNNER)!r}, run_name='__main__')\n")
        wf = self.root / "wf.json"
        wf.write_text(json.dumps({"workflow": "b4", "steps": [step(
            "s", "import subprocess, sys, time; subprocess.Popen([sys.executable, '-c', 'pass']); time.sleep(1); "
            + write("o.txt"), ["o.txt"])]}))
        p = subprocess.run([sys.executable, "-B", str(wrapper), str(wf), "--work", str(self.work)],
                           capture_output=True, text=True, timeout=120)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertEqual(record(self.work, "s")["extension"]["termination"], "confirmed")

    @needs("proc_fs")  # the environment token is found through /proc (Linux)
    def test_a_nested_runner_does_not_hide_its_steps(self):
        """A step that runs run_workflow.py: the inner runner's step starts its own session, and the inner runner adds
        its token to the marker instead of replacing it, so the outer runner still finds and stops that step when the
        outer step ends and leaves it running."""
        started, late = self.root / "started.txt", self.root / "late.txt"
        inner = self.root / "inner.json"
        inner.write_text(json.dumps({"workflow": "inner", "steps": [step(
            "i", f"import time; open({str(started)!r}, 'w').write('x'); time.sleep(3); "
                 f"open({str(late)!r}, 'w').write('x')", [])]}))
        outer = (f"import os, subprocess, sys, time; subprocess.Popen([sys.executable, {str(RUNNER)!r}, "
                 f"{str(inner)!r}, '--work', {str(self.root / 'inner-work')!r}], stdout=subprocess.DEVNULL, "
                 f"stderr=subprocess.DEVNULL)\nwhile not os.path.exists({str(started)!r}): time.sleep(0.05)\n"
                 "os._exit(0)")
        code, out = run({"workflow": "b4", "steps": [step("outer", outer, [], timeout_s=60)]}, self.work)
        self.assertTrue(started.exists())
        self.assertEqual(code, 1, out)  # the outer step left processes running
        ext = record(self.work, "outer")["extension"]
        self.assertEqual(ext["termination"], "confirmed")
        time.sleep(4)
        self.assertFalse(late.exists())  # the inner step was stopped with the outer one

    @needs("proc_fs")  # the environment token is found through /proc (Linux)
    def test_the_record_names_what_termination_observed(self):
        code, out = run({"workflow": "b4", "steps": [step("s", write("o.txt"), ["o.txt"])]}, self.work)
        self.assertEqual(code, 0, out)
        self.assertEqual(record(self.work, "s")["extension"]["termination_scope"],
                         ["process-group", "environment-marker"])

    def test_unconfirmed_termination_is_recorded_and_fails(self):
        mod = load_runner()
        real_stop = mod._stop
        mod._stop = lambda pgid, token, proc: real_stop(pgid, token, proc) and False  # stopped, but not confirmed
        wf = {"workflow": "b4", "steps": [step("s", "import time; time.sleep(60)", ["o.txt"], timeout_s=1)]}
        code, out = call(mod, wf, self.work)
        self.assertEqual((code, out.get("termination")), (1, "unconfirmed"), out)
        rec = record(self.work, "s")
        self.assertEqual((rec["extension"]["termination"], rec["extension"]["output_hashes"]), ("unconfirmed", {}))

    def test_bad_timeout_values_are_refused(self):
        for bad in (0, -1, "10", True, float("inf")):
            with self.subTest(timeout=bad):
                wf = {"workflow": "b4", "steps": [step("s", "pass", [], timeout_s=bad)]}
                path = self.root / "wf.json"
                path.write_text(json.dumps(wf), encoding="utf-8")  # inf is written as Infinity, which json reads
                p = subprocess.run([sys.executable, "-B", str(RUNNER), str(path), "--work", str(self.work)],
                                   capture_output=True, text=True, timeout=60)
                self.assertEqual(p.returncode, 2, p.stdout)


class RecordFields(Base):
    def test_record_carries_contract_end_termination_and_artifact_digest(self):
        from contracts.validate import validate_artifact
        wf = {"workflow": "rf", "steps": [step("s", write("a.txt") + ";" + write("b.txt", "y"), ["b.txt", "a.txt"])]}
        code, out = run(wf, self.work)
        self.assertEqual(code, 0, out)
        rec = record(self.work, "s")
        ext = rec["extension"]
        self.assertEqual(ext["output_contract"], ["a.txt", "b.txt"])
        self.assertEqual((ext["end_status"], ext["termination"]), ("success", "confirmed"))
        canon = json.dumps(ext["output_hashes"], sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        self.assertEqual(ext["artifact_digest"], hashlib.sha256(canon.encode("utf-8")).hexdigest())
        rep = validate_artifact(rec)
        self.assertTrue(rep.ok, rep.as_dict())


class CheckFields(Base):
    """After A2: a check step's declared identity is validated before any step runs."""

    def check(self, **over):
        c = {"check_digest": "c" * 64, "criterion_digest": "d" * 64, "target_artifact_digest": "e" * 64,
             "criteria_file": "criteria.json", "result_file": "result.json", "target_manifest": {"t.txt": "t.txt"},
             "role": "closure", "type": "performance-estimate", "samples": []}
        c.update(over)
        return c

    def write_workflow(self, chk):
        self.work.mkdir(exist_ok=True)
        for f in ("criteria.json", "t.txt"):
            (self.work / f).write_text("{}")
        return {"workflow": "cf", "steps": [step("s", write("result.json", "{}"), ["result.json"],
                                                 inputs=["criteria.json", "t.txt"], check=chk)]}

    def test_valid_check_is_recorded(self):  # its result is not bound (no check program): B2 fails the step
        code, out = run(self.write_workflow(self.check()), self.work)
        self.assertEqual(code, 1, out)
        ext = record(self.work, "s")["extension"]
        self.assertEqual((ext["check"]["role"], ext["check_result"]["bound"]), ("closure", False))

    def test_invalid_checks_are_refused(self):
        bad = [self.check(extra=1), self.check(role="confirmation"), self.check(check_digest="x"),
               self.check(criteria_file="other.json"), self.check(result_file="nope.json"),
               self.check(target_manifest={"t.txt": "missing.txt"}), self.check(samples="S")]
        for c in bad:
            with self.subTest(check=c):
                self.assertEqual(run(self.write_workflow(c), self.work)[0], 2)


if __name__ == "__main__":
    unittest.main()
