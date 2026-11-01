"""detector-simulation shared layer, execution and commit (work item W3b; TASK.md 10, 11, 16.1).

Every backend here is the simulator-free synthetic backend (tests/adapters/detsim_backend_synthetic.py) launching the
cooperative program tests/adapters/detsim_coop_program.py, whose behaviour comes from a mode file in the environment
root, so a test changes behaviour without changing the plan. Controllers that must be processes of their own (lock,
orphans, interruption, crash injection) run tests/adapters/detsim_synthetic_cli.py. Processes the tests start are the
tests' own; the shared layer itself never signals anything but its own unreaped child's group.

Tests needing Linux-only mechanisms (PR_SET_PDEATHSIG, renameat2) are skipped elsewhere and recorded "not run
(platform)"; each has a macOS counterpart for the soft path.
"""
from __future__ import annotations

import contextlib
import io
import json
import os
import shutil
import signal
import stat
import subprocess
import sys
import tempfile
import time
import types
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
ASSETS = ROOT / "adapters" / "detector-simulation" / "assets"
for _entry in (str(ROOT), str(ASSETS), str(HERE)):
    if _entry not in sys.path:
        sys.path.insert(0, _entry)
sys.dont_write_bytecode = True

import detsim  # noqa: E402
import detsim_backend_synthetic as synthetic  # noqa: E402
import detsim_canonical as canonical  # noqa: E402
import detsim_platform  # noqa: E402
import detsim_profile  # noqa: E402
import detsim_run  # noqa: E402
import detsim_runner  # noqa: E402

CLI = HERE / "detsim_synthetic_cli.py"
COOP = HERE / "detsim_coop_program.py"
ON_MAC = sys.platform == "darwin"
ON_LINUX = sys.platform.startswith("linux")


def wait_for(predicate, timeout=20.0):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if predicate():
            return True
        time.sleep(0.05)
    return False


class Base(unittest.TestCase):
    """A synthetic project with an environment root holding the cooperative program."""

    def setUp(self):
        if detsim_profile.host_profile_id() != "macos-g0":  # linux-g0 declares every guarantee unsupported (D-W1-3)
            self.skipTest("not run (platform): runs need a measured runner profile; only macos-g0 is measured")
        self.work_dir = Path(tempfile.mkdtemp(prefix="detsim run é "))
        self.addCleanup(shutil.rmtree, self.work_dir, True)
        self.env_root = self.work_dir / "env root"
        (self.env_root / "bin").mkdir(parents=True)
        (self.env_root / "share" / "synthetic").mkdir(parents=True)
        program = self.env_root / "bin" / "synthetic-sim"
        program.write_text(f"#!{sys.executable}\n" + COOP.read_text(encoding="utf-8"), encoding="utf-8")
        program.chmod(0o755)
        self.mode("ok")
        self.project = synthetic.make_project(self.work_dir / "project é", env_root=self.env_root)
        self.store = detsim_run.store_root(self.project)
        self.procs: list[subprocess.Popen] = []
        self.addCleanup(self._stop_own_processes)
        detsim_run.HOOKS.clear()
        self.addCleanup(detsim_run.HOOKS.clear)

    def _stop_own_processes(self):
        for proc in self.procs:  # processes this test started (allowed: TASK.md 4.1)
            if proc.poll() is None:
                proc.kill()
                proc.wait()
        for name in ("started", "grandchild", "member"):
            path = self.env_root / "share" / "synthetic" / name
            if path.is_file():  # a backend or grandchild the test's own controller started
                pid = int(path.read_text())
                with contextlib.suppress(ProcessLookupError, PermissionError):
                    os.kill(pid, signal.SIGKILL)

    def mode(self, text: str):
        (self.env_root / "share" / "synthetic" / "mode").write_text(text, encoding="utf-8")

    def set_task(self, **changes):
        path = self.project / "task.json"
        task = json.loads(path.read_text(encoding="utf-8"))
        for key, value in changes.items():
            if key in ("timeout_s", "max_output_bytes"):
                task["budget"][key] = value
            else:
                task["parameters"][key] = value
        path.write_text(json.dumps(task), encoding="utf-8")

    def call(self, *argv, backends=None):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = detsim.main(["--backend", "synthetic", *argv], backends=backends or {"synthetic": synthetic})
        return code, json.loads(out.getvalue())

    def prepare(self, backends=None):
        code, answer = self.call("prepare", "--workspace", str(self.project), "--task", "task.json",
                                 backends=backends)
        self.assertEqual(code, 0, answer)
        path = self.work_dir / f"plan-{answer['plan_digest'][:8]}.json"
        path.write_text(json.dumps(answer), encoding="utf-8")
        return path, answer["plan_digest"]

    def run_plan(self, plan_path, *extra, backends=None):
        return self.call("run", "--workspace", str(self.project), "--plan", str(plan_path), *extra,
                         backends=backends)

    def controller(self, plan_path, *extra, env=None):
        proc = subprocess.Popen([sys.executable, str(CLI), "--backend", "synthetic", "run", "--workspace",
                                 str(self.project), "--plan", str(plan_path), *extra],
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                                env=dict(os.environ, **(env or {})))
        self.procs.append(proc)
        return proc

    def started_pid(self):
        path = self.env_root / "share" / "synthetic" / "started"
        self.assertTrue(wait_for(path.is_file), "the backend did not start")
        return int(path.read_text())

    def tree(self):
        return {str(p.relative_to(self.store)): (p.stat().st_size, p.stat().st_mtime_ns)
                for p in self.store.rglob("*")} if self.store.is_dir() else {}

    def validate(self):
        out = subprocess.run([sys.executable, str(ROOT / "contracts" / "validate.py"),
                              str(detsim_run.plan_layer.artifacts_root(self.project))], capture_output=True, text=True)
        return out.returncode, out.stdout


class Idempotency(Base):  # T-IDEM
    def test_second_run_reuses_without_launching(self):
        plan, _ = self.prepare()
        code, first = self.run_plan(plan)
        self.assertEqual((code, first["status"], first["reused"]), (0, "ok", False), first)
        self.mode("fail")  # a launch would now fail
        code, second = self.run_plan(plan)
        self.assertEqual((code, second["status"], second["reused"], second["run_id"]), (0, "ok", True, first["run_id"]))

    def test_replicate_gives_a_new_run_id_and_identical_results(self):
        plan, digest = self.prepare()
        _, zero = self.run_plan(plan)
        _, one = self.run_plan(plan, "--replicate", "1")
        self.assertNotEqual(zero["run_id"], one["run_id"])
        self.assertEqual(one["run_id"], canonical.run_id(digest, 1))
        rows = [(self.store / "runs" / r / "observables.csv").read_text() for r in (zero["run_id"], one["run_id"])]
        self.assertEqual(rows[0], rows[1])

    def test_checked_then_committed_elsewhere_does_not_rerun(self):
        plan, _ = self.prepare()
        self.run_plan(plan)  # controller B committed
        self.mode("fail")
        original, calls = detsim_run._reuse, []

        def first_check_misses(*args):
            calls.append(args)
            return None if len(calls) == 1 else original(*args)  # A's step 5 saw nothing; step 7 sees B's result
        with mock.patch.object(detsim_run, "_reuse", first_check_misses):
            code, answer = self.run_plan(plan)
        self.assertEqual((code, answer["status"], answer["reused"]), (0, "ok", True))
        record = json.loads((self.store / ".pending" / f"{answer['run_id']}.lock").read_text())
        self.assertEqual((record["state"], record["terminal"]["reused"]), ("finished", True))


class Lock(Base):  # T-LOCK
    def test_second_controller_gets_in_progress(self):
        self.mode("sleep 4")
        plan, _ = self.prepare()
        first = self.controller(plan)
        self.started_pid()
        code, answer = self.run_plan(plan)
        self.assertEqual((code, answer["status"], answer["error_code"]), (3, "incomplete", "in-progress"))
        self.assertIn("controller_pid", answer["holder"])
        out, _ = first.communicate(timeout=60)
        self.assertEqual(json.loads(out)["status"], "ok")

    def test_refusal_after_the_lock_leaves_the_record_finished(self):
        plan, _ = self.prepare()
        run_id = canonical.run_id(json.loads(plan.read_text())["plan_digest"], 0)
        detsim_run.HOOKS["before_snapshot"] = lambda attempt: (self.project / "inputs" / "run config.conf").write_text(
            "changed after the rebuild comparison\n")
        code, answer = self.run_plan(plan)
        self.assertEqual((code, answer["status"], answer["error_code"]), (1, "refused", "input-changed"))
        record = json.loads((self.store / ".pending" / f"{run_id}.lock").read_text())
        self.assertEqual(record["state"], "finished")
        self.assertFalse((self.store / "runs").exists() and any((self.store / "runs").iterdir()))

    def test_killed_controller_is_stale(self):
        self.mode("sleep 30")
        plan, digest = self.prepare()
        proc = self.controller(plan)
        self.started_pid()
        proc.kill()  # the test's own controller process
        proc.wait()
        code, answer = self.call("inspect", "--workspace", str(self.project), "--run", canonical.run_id(digest, 0))
        self.assertEqual((code, answer["state"]), (0, "stale"))
        self.assertTrue(answer["orphans"] and answer["orphans"][0]["pid"])

    def test_backend_does_not_inherit_the_lock(self):
        lock = detsim_run.RunLock(self.work_dir / "x.lock")
        self.assertTrue(lock.acquire({"state": "preparing"}))
        import fcntl
        self.assertTrue(fcntl.fcntl(lock.fd, fcntl.F_GETFD) & fcntl.FD_CLOEXEC)
        self.assertFalse(os.get_inheritable(lock.fd))
        lock.release(state="finished")

    def test_leftovers_never_touch_lock_files(self):
        pending = self.store / ".pending"
        (pending / "abc.n1").mkdir(parents=True)
        (pending / "abc.lock").write_text("{}")
        (pending / "other.n2").mkdir()
        detsim_run.move_leftovers(pending, "abc", None)
        self.assertTrue((pending / "abc.lock").is_file())
        self.assertTrue((pending / "other.n2").is_dir())  # another run's folder is not moved
        self.assertTrue((pending / "orphans" / "abc-n1").is_dir())


class Orphans(Base):  # T-ORPHAN
    def test_controller_killed_backend_writes_only_into_its_old_folder(self):
        self.mode("late 2")
        plan, digest = self.prepare()
        proc = self.controller(plan)
        backend_pid = self.started_pid()
        proc.kill()
        proc.wait()
        (self.env_root / "share" / "synthetic" / "started").unlink()
        self.mode("ok")
        code, answer = self.run_plan(plan)
        self.assertEqual((code, answer["status"]), (0, "ok"), answer)
        moved = [o for o in answer["orphans_reported"] if "moved" in o]
        self.assertEqual(len(moved), 1)
        self.assertTrue(any(o.get("pid") == backend_pid for o in answer["orphans_reported"]))
        late = self.store / moved[0]["moved"] / "raw" / "late.txt"
        self.assertTrue(wait_for(late.is_file, 10) or not ON_MAC, "the orphan's late write landed elsewhere")
        self.assertFalse((self.store / "runs" / answer["run_id"] / "raw" / "late.txt").exists())

    @unittest.skipUnless(ON_LINUX, "not run (platform): PR_SET_PDEATHSIG is Linux only")
    def test_backend_dies_with_its_controller_on_linux(self):  # pragma: no cover - Linux only
        self.mode("sleep 30")
        plan, _ = self.prepare()
        proc = self.controller(plan)
        pid = self.started_pid()
        proc.kill()
        proc.wait()
        self.assertTrue(wait_for(lambda: not Path(f"/proc/{pid}").exists(), 10))


class NoKill(Base):  # T-NOKILL
    def test_live_pid_in_an_unfinished_record_is_never_signalled(self):
        plan, digest = self.prepare()
        run_id = canonical.run_id(digest, 0)
        survivor = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])
        self.procs.append(survivor)
        pending = self.store / ".pending"
        pending.mkdir(parents=True, exist_ok=True)
        (pending / f"{run_id}.lock").write_text(json.dumps({"state": "running", "pid": survivor.pid,
                                                            "pgid": survivor.pid, "started": "earlier"}))
        code, answer = self.run_plan(plan)
        self.assertEqual(code, 0, answer)
        self.assertIsNone(survivor.poll(), "the recorded process was signalled")
        self.assertTrue(any(o.get("pid") == survivor.pid for o in answer["orphans_reported"]))

    def test_unreadable_record_is_reported_unknown(self):
        plan, digest = self.prepare()
        pending = self.store / ".pending"
        pending.mkdir(parents=True, exist_ok=True)
        (pending / f"{canonical.run_id(digest, 0)}.lock").write_text("not json {")
        code, answer = self.run_plan(plan)
        self.assertEqual(code, 0)
        self.assertIn("unknown", json.dumps(answer["orphans_reported"]))

    def test_signals_only_to_the_own_unreaped_child(self):
        calls = []
        real = os.killpg

        def recording_killpg(pgid, sig):
            calls.append(("killpg", pgid, sig))
            return real(pgid, sig)
        self.set_task(timeout_s=1)
        self.mode("sleep 30")
        plan, _ = self.prepare()
        with mock.patch.object(detsim_runner, "KILL", recording_killpg), \
                mock.patch.object(os, "kill", lambda *a: calls.append(("kill",) + a)):
            code, answer = self.run_plan(plan)
        self.assertEqual((answer["status"], answer["error_code"]), ("failed", "timeout"))
        backend = int((self.env_root / "share" / "synthetic" / "started").read_text())
        self.assertTrue(calls and all(c[0] == "killpg" and c[1] == backend for c in calls), calls)

    def test_grandchild_of_a_normally_exiting_child_is_never_signalled(self):
        calls = []
        self.mode("grandchild")
        plan, _ = self.prepare()
        with mock.patch.object(detsim_runner, "KILL", lambda *a: calls.append(a)):
            code, answer = self.run_plan(plan)
        self.assertEqual((code, calls), (0, []))
        path = self.env_root / "share" / "synthetic" / "grandchild"
        self.assertTrue(wait_for(path.is_file))
        pid = int(path.read_text())
        alive = subprocess.run(["ps", "-p", str(pid), "-o", "pid="], capture_output=True, text=True).stdout.strip()
        self.assertEqual(alive, str(pid), "the grandchild should still run (reported, not killed)")


class Runner(Base):  # T-RUNNER
    def test_timeout_kills_the_process_group(self):
        self.set_task(timeout_s=1)
        self.mode("sleep 30")
        plan, _ = self.prepare()
        start = time.monotonic()
        code, answer = self.run_plan(plan)
        self.assertEqual((code, answer["status"], answer["error_code"]), (1, "failed", "timeout"))
        self.assertLess(time.monotonic() - start, 15)

    def test_term_ignored_then_killed(self):
        self.set_task(timeout_s=1)
        self.mode("ignore_term")
        plan, _ = self.prepare()
        code, answer = self.run_plan(plan)
        self.assertEqual((answer["error_code"], answer["signal"]), ("timeout", "SIGKILL"))

    def test_excess_output_aborts(self):
        self.set_task(max_output_bytes=1048576)
        self.mode("bigout")
        plan, _ = self.prepare()
        code, answer = self.run_plan(plan)
        self.assertEqual((code, answer["status"], answer["error_code"]), (1, "failed", "output-exceeded"))

    def test_input_hashes_equal_before_and_after(self):
        self.mode("modify_input")
        plan, _ = self.prepare()
        code, answer = self.run_plan(plan)
        self.assertEqual((answer["status"], answer["error_code"]), ("failed", "input-modified"))
        self.assertEqual((self.project / "inputs" / "run config.conf").read_text(),
                         "synthetic configuration\nmodel = toy\n")  # the project's own input is untouched

    def test_environment_is_exactly_the_plans(self):
        plan, _ = self.prepare()
        spec = json.loads(plan.read_text())["plan"]["execution"]
        self.assertEqual(sorted(spec["environment"]), ["PATH", "SYNTHETIC_DATA"])
        code, answer = self.run_plan(plan)
        self.assertEqual(code, 0)


class Commit(Base):  # T-COMMIT
    def test_crash_before_commit_then_rerun(self):
        plan, _ = self.prepare()
        proc = self.controller(plan, env={"DETSIM_TEST_CRASH": "before_commit"})
        proc.communicate(timeout=60)
        self.assertEqual(proc.returncode, -signal.SIGKILL)
        code, answer = self.run_plan(plan)
        self.assertEqual((code, answer["status"], answer["reused"]), (0, "ok", False))
        self.assertTrue(any("moved" in o for o in answer["orphans_reported"]))

    def test_crash_after_rename_returns_the_result(self):
        plan, _ = self.prepare()
        proc = self.controller(plan, env={"DETSIM_TEST_CRASH": "after_rename"})
        proc.communicate(timeout=60)
        self.mode("fail")
        code, answer = self.run_plan(plan)
        self.assertEqual((code, answer["status"], answer["reused"]), (0, "ok", True))

    def test_existing_target_is_never_replaced(self):
        for content in (None, "occupied"):
            with self.subTest(target="empty" if content is None else "not empty"):
                plan, digest = self.prepare()
                target = self.store / "runs" / canonical.run_id(digest, 0)

                def occupy(attempt, target_folder, content=content):  # between the existence check and the rename
                    target_folder.mkdir(parents=True, exist_ok=True)
                    if content:
                        (target_folder / "x.txt").write_text(content)
                detsim_run.HOOKS["before_rename"] = occupy
                with mock.patch.object(detsim_run, "_reuse", lambda *a: None):
                    code, answer = self.run_plan(plan)
                detsim_run.HOOKS.clear()
                self.assertEqual((code, answer["status"], answer["error_code"]), (1, "failed", "commit-conflict"))
                self.assertFalse((target / detsim_run.RECORD_NAME).exists())
                shutil.rmtree(target)
                self.set_task(seed=len(content or "") + 7)  # a new plan for the second case

    def test_sigint_during_commit_keeps_success(self):
        plan, _ = self.prepare()
        detsim_run.HOOKS["before_commit"] = lambda attempt: os.kill(os.getpid(), signal.SIGINT)  # the test process
        code, answer = self.run_plan(plan)
        self.assertEqual((code, answer["status"], answer["signals_during_commit"]), (0, "ok", ["SIGINT"]))

    def test_fsync_before_rename_order(self):
        plan, _ = self.prepare()
        detsim_platform.CALLS.clear()
        code, answer = self.run_plan(plan)
        self.assertEqual(code, 0)
        ops = [op for op, _ in detsim_platform.CALLS]
        rename = ops.index("rename_noreplace")
        file_sync = "F_FULLFSYNC" if ON_MAC else "fsync"
        self.assertIn(file_sync, ops[:rename])
        self.assertIn("fsync_dir", ops[:rename])
        self.assertIn("fsync_dir", ops[rename + 1:])  # parents after the rename
        self.assertNotIn(file_sync, ops[rename + 1:])

    def test_readers_never_look_into_pending(self):
        plan, digest = self.prepare()
        self.run_plan(plan)
        junk = self.store / ".pending" / f"{canonical.run_id(digest, 0)}.junk"
        junk.mkdir(parents=True)
        (junk / "observables.csv").write_text("not,a,result\n")
        code, summary = self.call("inspect", "--workspace", str(self.project), "--view", "summary")
        self.assertEqual(len(summary["runs"]), 1)
        self.assertNotIn("not", json.dumps(summary["runs"][0]["observables"]))


class FileSystem(Base):  # T-FS
    def test_unsupported_file_systems_are_rejected(self):
        plan, _ = self.prepare()
        for kind in ("nfs", "smbfs", "cifs", "fuse", "osxfuse", "s3fs", None, "weird"):
            with self.subTest(fs=kind), mock.patch.object(detsim_platform, "filesystem_type", lambda p, k=kind: k):
                code, answer = self.run_plan(plan)
                self.assertEqual((code, answer["status"], answer["error_code"]), (2, "rejected", "unsupported-fs"))

    def test_host_file_system_is_on_the_allowlist(self):
        kind = detsim_platform.filesystem_type(self.work_dir)
        self.assertIn(kind, detsim_platform.LOCAL_FILESYSTEMS[detsim_platform.platform_key()])


class Guarantees(Base):  # T-GUARANTEE, T-PLATFORM
    def _backend(self, required):
        capability = dict(synthetic.CAPABILITY, required_guarantees=required)
        return types.SimpleNamespace(**{k: getattr(synthetic, k) for k in ("NAME", "code_files", "check",
                                                                            "build_spec", "collect", "observables",
                                                                            "probe")},
                                     capabilities=lambda: {capability["id"]: json.loads(json.dumps(capability))})

    def test_no_network_hard_is_refused_under_g0(self):
        backend = self._backend({"no_network": "hard"})
        plan, _ = self.prepare(backends={"synthetic": backend})
        code, answer = self.run_plan(plan, backends={"synthetic": backend})
        self.assertEqual((code, answer["status"], answer["error_code"]), (1, "refused", "guarantee-insufficient"))
        self.assertFalse((self.store / "runs").exists())

    @unittest.skipUnless(ON_MAC, "not run (platform): the macos-g0 levels are measured on macOS")
    def test_macos_profile_levels(self):
        self.assertEqual(detsim_profile.host_profile_id(), "macos-g0")
        levels = detsim_profile.profile("macos-g0")["guarantees"]
        self.assertEqual(levels, {"backend_dies_with_controller": "soft", "commit_noreplace": "hard",
                                  "durable_commit": "soft", "local_fs_check": "hard", "inputs_unmodified": "hard",
                                  "timeout_kill": "hard", "output_size_abort": "soft", "descendants_killed": "soft",
                                  "no_network": "unsupported"})
        backend = self._backend({"backend_dies_with_controller": "hard"})  # hard here only on Linux
        plan, _ = self.prepare(backends={"synthetic": backend})
        code, answer = self.run_plan(plan, backends={"synthetic": backend})
        self.assertEqual(answer["error_code"], "guarantee-insufficient")

    def test_linux_profile_is_unsupported_until_measured(self):
        self.assertEqual(set(detsim_profile.profile("linux-g0")["guarantees"].values()), {"unsupported"})

    def test_achieved_levels_are_recorded(self):
        plan, _ = self.prepare()
        code, answer = self.run_plan(plan)
        record = json.loads((self.store / "runs" / answer["run_id"] / detsim_run.RECORD_NAME).read_text())
        detsim_facts = record["extension"]["detsim"]
        self.assertEqual(detsim_facts["profile"], detsim_profile.host_profile_id())
        self.assertIn("commit_noreplace", detsim_facts["achieved_guarantees"])


class ExitTable(Base):  # T-EXIT
    def test_rows(self):
        plan, digest = self.prepare()
        rows = []
        rows.append((self.run_plan(plan, "--plan-digest", "0" * 64), 1, "refused", "digest-mismatch"))
        rows.append((self.run_plan(plan, "--replicate", "-1"), 2, "rejected", "replicate-range"))
        rows.append((self.run_plan(plan, "--frob"), 2, "rejected", "usage"))
        self.mode("fail")
        rows.append((self.run_plan(plan), 1, "failed", "backend-failed"))
        self.mode("partial")
        rows.append((self.run_plan(plan, "--replicate", "2"), 1, "failed", "collect-partial"))
        self.mode("ok")
        rows.append((self.run_plan(plan), 0, "ok", None))
        rows.append((self.run_plan(plan), 0, "ok", None))  # reused
        (self.project / "inputs" / "run config.conf").write_text("edited\n")
        rows.append((self.run_plan(plan), 1, "refused", "plan-stale"))
        for (code, answer), exit_expected, status, error_code in rows:
            with self.subTest(status=status, error_code=error_code):
                self.assertEqual((code, answer["status"], answer.get("error_code")), (exit_expected, status, error_code))
                self.assertIn(code, (0, 1, 2, 3))

    def test_replicate_out_of_range(self):
        plan, _ = self.prepare()
        code, answer = self.run_plan(plan, "--replicate", str(2 ** 32))
        self.assertEqual((code, answer["status"]), (2, "rejected"))

    def test_injected_exception_is_internal(self):
        plan, _ = self.prepare()
        with mock.patch.object(detsim_run, "run", side_effect=RuntimeError("boom")):
            code, answer = self.run_plan(plan)
        self.assertEqual((code, answer["status"], answer["error_code"]), (2, "error", "internal"))

    def test_missing_dependency_before_the_lock(self):
        plan, digest = self.prepare()
        from core import hostcaps
        with mock.patch.object(hostcaps, "require", side_effect=hostcaps.UnsupportedPlatform(["process_groups"])):
            code, answer = self.run_plan(plan)
        self.assertEqual((code, answer["status"]), (3, "missing-dependency"))
        self.assertFalse((self.store / ".pending" / f"{canonical.run_id(digest, 0)}.lock").exists())

    def test_missing_program_after_the_lock_is_failed(self):
        plan, _ = self.prepare()
        (self.env_root / "bin" / "synthetic-sim").unlink()
        code, answer = self.run_plan(plan)
        self.assertEqual((code, answer["status"], answer["error_code"]), (1, "failed", "missing-dependency"))

    def test_interruption_is_cancelled(self):
        self.mode("sleep 30")
        plan, _ = self.prepare()
        proc = self.controller(plan)
        self.started_pid()
        proc.send_signal(signal.SIGINT)  # the test's own controller
        out, _ = proc.communicate(timeout=60)
        answer = json.loads(out)
        self.assertEqual((proc.returncode, answer["status"], answer["error_code"]), (1, "failed", "cancelled"))

    def test_run_id_collision(self):
        plan, digest = self.prepare()
        target = self.store / "runs" / canonical.run_id(digest, 0)
        target.mkdir(parents=True)
        (target / "plan.canonical.json").write_text('{"other": "plan"}')
        code, answer = self.run_plan(plan)
        self.assertEqual((code, answer["status"], answer["error_code"]), (1, "refused", "run-id-collision"))


class Contract(Base):  # T-CONTRACT, T-OUTPUT and contracts/validate.py after a success and a failure
    def test_success_record_and_validation(self):
        plan, digest = self.prepare()
        code, answer = self.run_plan(plan)
        folder = self.store / "runs" / answer["run_id"]
        record = json.loads((folder / detsim_run.RECORD_NAME).read_text())
        ext = record["extension"]
        self.assertEqual(ext["parameter_digest"], canonical.run_digest(digest, 0))
        self.assertEqual(ext["detsim"]["plan_digest"], digest)
        for sidecar in ("plan.canonical.json", "completeness.json", "manifests/inputs.json",
                        "manifests/outputs.json"):
            self.assertIn(f"detector-simulation/runs/{answer['run_id']}/{sidecar}", ext["sidecars"])
        completeness = json.loads((folder / "completeness.json").read_text())
        self.assertEqual(completeness["state"], "complete")  # collect fact, separate from execution facts
        self.assertEqual(ext["exit_status"], 0)
        header = (folder / "observables.csv").read_text().splitlines()[0].split(",")
        self.assertEqual(header, list(detsim_run.OBSERVABLE_COLUMNS))
        verify = subprocess.run([sys.executable, str(ROOT / "contracts" / "verify_run.py"),
                                 str(folder / detsim_run.RECORD_NAME)], capture_output=True, text=True)
        self.assertEqual(verify.returncode, 0, verify.stdout[-600:])
        code, out = self.validate()
        self.assertEqual(code, 0, out[-1500:])

    def test_failure_record_and_validation(self):
        self.mode("partial")
        plan, _ = self.prepare()
        code, answer = self.run_plan(plan)
        self.assertEqual(answer["status"], "failed")
        folder = self.store / answer["folder"]
        record = json.loads((folder / detsim_run.RECORD_NAME).read_text())
        self.assertIn("failed", record["status"])
        self.assertEqual(record["extension"]["exit_status"], 1)
        self.assertEqual(record["extension"]["detsim"]["native_exit_code"], 0)  # native success kept separately
        code, out = self.validate()
        self.assertEqual(code, 0, out[-1500:])

    def test_refusal_writes_no_record(self):
        plan, _ = self.prepare()
        self.run_plan(plan, "--plan-digest", "0" * 64)
        self.assertFalse((self.store / "runs").exists() and any((self.store / "runs").iterdir()))
        self.assertFalse((self.store / "failed").exists() and any((self.store / "failed").iterdir()))

    def test_empty_values_is_failed_and_inspect_writes_nothing(self):
        self.mode("empty")
        plan, digest = self.prepare()
        code, answer = self.run_plan(plan)
        self.assertEqual((answer["status"], answer["completeness"]), ("failed", "partial"))
        before = self.tree()
        run_id = canonical.run_id(digest, 0)
        for argv in (["--run", run_id, "--view", "state"], ["--view", "summary"],
                     ["--attempt", Path(answer["folder"]).name]):
            code, out = self.call("inspect", "--workspace", str(self.project), *argv)
            self.assertEqual(code, 0, out)
        self.assertEqual(self.tree(), before)


class Probe(Base):  # check --probe
    def test_probe_writes_the_environment_record(self):
        code, answer = self.call("check", "--workspace", str(self.project), "--probe", "--env-root",
                                 str(self.env_root))
        self.assertEqual((code, answer["status"]), (0, "ok"), answer)
        record = detsim_run.plan_layer.env_record_path(detsim_run.plan_layer.artifacts_root(self.project),
                                                        answer["env_identity"])
        doc = json.loads(record.read_text())
        self.assertEqual(doc["path_record"]["env_root"], str(self.env_root.resolve()))

    def test_same_environment_through_a_symlink_keeps_its_identity(self):
        _, first = self.call("check", "--workspace", str(self.project), "--probe", "--env-root", str(self.env_root))
        link = self.work_dir / "link to env"
        link.symlink_to(self.env_root, target_is_directory=True)
        _, second = self.call("check", "--workspace", str(self.project), "--probe", "--env-root", str(link))
        self.assertEqual(first["env_identity"], second["env_identity"])

    def test_missing_program_is_missing_dependency(self):
        (self.env_root / "bin" / "synthetic-sim").unlink()
        code, answer = self.call("check", "--workspace", str(self.project), "--probe", "--env-root",
                                 str(self.env_root))
        self.assertEqual((code, answer["status"]), (3, "missing-dependency"))


class ReviewRoundOne(Base):
    """W3b independent review round 1: tests that fail on the reviewed defects (M1-M7 and minor findings)."""

    def test_refusal_under_the_lock_records_its_terminal_status(self):  # M1
        plan, digest = self.prepare()
        detsim_run.HOOKS["before_snapshot"] = lambda attempt: (self.project / "inputs" / "run config.conf").write_text(
            "changed\n")
        self.run_plan(plan)
        record = json.loads((self.store / ".pending" / f"{canonical.run_id(digest, 0)}.lock").read_text())
        self.assertEqual(record["terminal"]["status"], "refused")
        self.assertEqual(record["terminal"]["error_code"], "input-changed")

    def test_inspect_shows_a_reported_orphan_after_the_next_run(self):  # M2
        plan, digest = self.prepare()
        run_id = canonical.run_id(digest, 0)
        survivor = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])
        self.procs.append(survivor)
        pending = self.store / ".pending"
        pending.mkdir(parents=True, exist_ok=True)
        (pending / f"{run_id}.lock").write_text(json.dumps({"state": "running", "pid": survivor.pid,
                                                            "pgid": survivor.pid, "started": "earlier"}))
        self.run_plan(plan)
        code, answer = self.call("inspect", "--workspace", str(self.project), "--run", run_id)
        self.assertTrue(any(o["pid"] == survivor.pid and o["process_with_that_pid_exists_now"]
                            for o in answer["orphans"]), answer)
        self.assertIsNone(survivor.poll())

    def test_commit_fallback_below_declared_fails_the_run(self):  # M3
        plan, _ = self.prepare()
        with mock.patch.object(detsim_platform, "probe_noreplace", lambda folder: False):
            code, answer = self.run_plan(plan)
        self.assertEqual((code, answer["status"], answer["error_code"]), (1, "failed", "guarantee-not-achieved"))
        record = json.loads((self.store / answer["folder"] / detsim_run.RECORD_NAME).read_text())
        facts = record["extension"]["detsim"]
        self.assertEqual(facts["achieved_guarantees"]["commit_noreplace"], "soft")
        self.assertEqual(facts["guarantees_below_declared"][0]["guarantee"], "commit_noreplace")

    def test_interruption_during_collect_is_cancelled(self):  # M4
        original = synthetic.collect

        def interrupted_collect(attempt, spec):
            os.kill(os.getpid(), signal.SIGINT)  # the test process itself
            return original(attempt, spec)
        plan, digest = self.prepare()
        with mock.patch.object(synthetic, "collect", interrupted_collect):
            code, answer = self.run_plan(plan)
        self.assertEqual((code, answer["status"], answer["error_code"]), (1, "failed", "cancelled"))
        self.assertFalse(list((self.store / ".pending").glob(f"{canonical.run_id(digest, 0)}.*/")))

    def test_large_input_never_changes_the_project_file(self):  # M6
        source = self.project / "inputs" / "run config.conf"
        mode_before = stat.S_IMODE(source.stat().st_mode)
        with mock.patch.dict(detsim_profile.POLICY, {"input_copy_threshold_bytes": 1}):
            plan, _ = self.prepare()
            code, answer = self.run_plan(plan)
        self.assertEqual(code, 0, answer)
        self.assertEqual(stat.S_IMODE(source.stat().st_mode), mode_before)
        self.assertEqual(source.stat().st_nlink, 1)
        record = json.loads((self.store / "runs" / answer["run_id"] / detsim_run.RECORD_NAME).read_text())
        self.assertEqual(record["extension"]["detsim"]["inputs_cloned"], ["inputs/run config.conf"])

    def test_timeout_kills_a_member_of_the_group(self):  # M7
        self.set_task(timeout_s=1)
        self.mode("group")
        plan, _ = self.prepare()
        code, answer = self.run_plan(plan)
        self.assertEqual(answer["error_code"], "timeout")
        member = int((self.env_root / "share" / "synthetic" / "member").read_text())
        gone = wait_for(lambda: subprocess.run(["ps", "-p", str(member), "-o", "stat="], capture_output=True,
                                               text=True).stdout.strip() in ("", "Z"), 10)
        self.assertTrue(gone, "a process of the backend's group survived the timeout")

    def test_signalled_backend_and_malformed_plan_rows(self):  # minor 16
        self.mode("selfkill")
        plan, _ = self.prepare()
        code, answer = self.run_plan(plan)
        self.assertEqual((code, answer["status"], answer["error_code"], answer["signal"]),
                         (1, "failed", "signalled", "SIGKILL"))
        bad = self.work_dir / "bad plan.json"
        bad.write_text('{"schema": "detector-plan/1", "task": {"budget": "x"}}')
        code, answer = self.run_plan(bad)
        self.assertEqual((code, answer["status"], answer["error_code"]), (2, "rejected", "plan-invalid"))

    def test_four_kinds_of_evidence_and_observables_rows(self):  # minors 5, 7, 17
        import csv
        import detsim_schemas
        plan, _ = self.prepare()
        code, answer = self.run_plan(plan)
        folder = self.store / "runs" / answer["run_id"]
        ext = json.loads((folder / detsim_run.RECORD_NAME).read_text())["extension"]
        self.assertEqual(sorted(ext["evidence"]), ["contracts", "physical_validity", "provenance", "raw_files"])
        self.assertEqual(ext["evidence"]["raw_files"], "complete")
        self.assertIn("detsim_run.py", ext["script_sha256"])
        rows = list(csv.DictReader(io.StringIO((folder / "observables.csv").read_text())))
        doc = {"schema": "detsim-observables/1", "rows": [
            {k: (v.split(";") if k == "labels" else int(v) if k == "point" else v) for k, v in r.items() if v != ""}
            for r in rows]}
        self.assertEqual(detsim_schemas.check_observables(doc), [])
        self.assertEqual({r["unit"] for r in rows}, {"e"})

    def test_empty_values_and_missing_output_are_told_apart(self):  # minor 15
        evidence = {}
        for mode in ("empty", "partial"):
            self.mode(mode)
            self.set_task(seed=len(mode))
            plan, _ = self.prepare()
            code, answer = self.run_plan(plan)
            evidence[mode] = json.loads((self.store / answer["folder"] / "completeness.json").read_text())
        self.assertEqual(evidence["empty"]["missing_outputs"], [])
        self.assertTrue(evidence["partial"]["missing_outputs"])

    def test_no_seed_parameter_invents_no_seed(self):  # minor 6
        seeds = detsim_run._seeds({"task": {"parameters": {"points": []}}})
        self.assertEqual(list(seeds), ["none"])

    def test_every_file_is_flushed_before_the_rename(self):  # minor 14
        plan, _ = self.prepare()
        detsim_platform.CALLS.clear()
        code, answer = self.run_plan(plan)
        calls = list(detsim_platform.CALLS)
        rename = [op for op, _ in calls].index("rename_noreplace")
        flushed = {Path(path).name for op, path in calls[:rename] if op in ("F_FULLFSYNC", "fsync")}
        committed = self.store / "runs" / answer["run_id"]
        self.assertTrue({p.name for p in committed.rglob("*") if p.is_file() and not p.is_symlink()} <= flushed)

    def test_no_signal_reaches_anything_but_the_own_group(self):  # minor 13
        calls = []
        self.set_task(timeout_s=1)
        self.mode("sleep 30")
        plan, _ = self.prepare()
        real = os.killpg
        with mock.patch.object(os, "killpg", lambda pgid, sig: (calls.append(("os.killpg", pgid)), real(pgid, sig))), \
                mock.patch.object(detsim_runner, "KILL", lambda pgid, sig: (calls.append(("KILL", pgid)),
                                                                            real(pgid, sig))), \
                mock.patch.object(os, "kill", lambda *a: calls.append(("os.kill",) + a)):
            self.run_plan(plan)
        backend = int((self.env_root / "share" / "synthetic" / "started").read_text())
        self.assertTrue(calls and all(c[0] == "KILL" and c[1] == backend for c in calls), calls)


if __name__ == "__main__":
    unittest.main()
