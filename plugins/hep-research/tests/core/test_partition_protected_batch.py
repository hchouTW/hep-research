"""Batch commands in protected mode (HC-10, HC-16; review of P6.2, 2026-10-14). In a protected project the commands
that reach a scheduler or settle a submission's outcome are refused before any scheduler call, with
protected.batch_needs_trusted_submitter: a real submit, resubmit or cancel, and confirm, abandon, reset and
clear-orphans in any form. Dry runs, planning, polling, reconcile, merge and report are unchanged. The switch is
protected mode itself (the project's agent_policy, DP-2), never the campaign config. Outside protected mode nothing
changes. Synthetic data only."""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests" / "core"))
from core.partition import campaign as cp  # noqa: E402
from core.protected.guard import ProtectedUseRefused  # noqa: E402
from partition_helpers import ScriptedExecutor, make_campaign  # noqa: E402
from tests.protected_fixture import ProtectedProject  # noqa: E402

CODE = "protected.batch_needs_trusted_submitter"
CONFIG = {"max_attempts": 2}


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.pp = ProtectedProject(self.tmp.name).start()
        cdir, _, _ = make_campaign(self.pp.project / "work")
        self.cdir = Path(cdir)
        self.ex = ScriptedExecutor({})

    def tearDown(self):
        self.pp.stop()
        self.pp.cleanup_modes()
        self.tmp.cleanup()

    def refused(self, fn) -> set[str]:
        with self.assertRaises(ProtectedUseRefused) as cm:
            fn()
        return {r["code"] for r in cm.exception.refusals}

    def commands(self):
        """(name, call) for every command that is refused in protected mode."""
        c, ex = self.cdir, self.ex
        return [
            ("submit --submit", lambda: cp.submit(c, ex, CONFIG, approved=True)),
            ("resubmit --submit", lambda: cp.resubmit(c, ex, CONFIG, approved=True)),
            ("cancel --approve-cancel", lambda: cp.cancel(c, ex, approved=True)),
            ("confirm", lambda: cp.confirm_submission(c, "s1", {"a": "j"}, ex)),
            ("abandon", lambda: cp.abandon_submission(c, "s1", "no jobs found")),
            ("reset", lambda: cp.reset(c, ["c0"], "fixed")),
            ("clear-orphans", lambda: cp.clear_orphan_risk(c, ex, "s1", "all final")),
        ]


class ProtectedProjectRefuses(Base):
    def test_every_command_is_refused_before_the_scheduler(self):
        for name, call in self.commands():
            with self.subTest(command=name):
                self.assertEqual(self.refused(call), {CODE})
        self.assertEqual(self.ex.calls, [], "no scheduler call may happen")

    def test_dry_runs_and_observation_still_work(self):
        rep = cp.submit(self.cdir, self.ex, CONFIG, approved=False)
        self.assertNotIn("submitted", {k for k, v in rep.items() if v is True})
        cp.cancel(self.cdir, self.ex, approved=False)
        cp.poll(self.cdir, self.ex)
        cp.report(self.cdir)
        self.assertNotIn("submit", [c[0] for c in self.ex.calls])

    def test_broken_protected_inputs_are_refused_first(self):
        """abandon, reset, cancel and clear-orphans had no guard call before: they now check the protected inputs too."""
        self.pp.fail("stale")
        for name, call in self.commands():
            with self.subTest(command=name):
                codes = self.refused(call)
                self.assertTrue(codes and CODE not in codes, codes)

    def test_the_campaign_config_cannot_switch_it_off(self):
        for key in ({"submitter": "in-process"}, {"submitter": "trusted"}, {"protected": False}):
            with self.subTest(config=key):
                self.assertEqual(self.refused(lambda: cp.submit(self.cdir, self.ex, dict(CONFIG, **key), approved=True)),
                                 {CODE})


class OutsideProtectedModeNothingChanges(Base):
    def setUp(self):
        super().setUp()
        import json
        cfg_path = self.pp.project / "hep-research.project.json"
        cfg = json.loads(cfg_path.read_text())
        cfg.pop("agent_policy")
        cfg_path.write_text(json.dumps(cfg))

    def test_real_submit_reaches_the_executor(self):
        cp.submit(self.cdir, self.ex, CONFIG, approved=True)
        self.assertIn("submit", [c[0] for c in self.ex.calls])

    def test_no_command_is_refused_by_the_guard(self):
        for name, call in self.commands():
            with self.subTest(command=name):
                try:
                    call()
                except ProtectedUseRefused as exc:  # pragma: no cover - the failure being tested
                    self.fail(f"{name} refused outside protected mode: {exc}")
                except Exception:  # noqa: BLE001  placeholder arguments may fail for their own reasons
                    pass


if __name__ == "__main__":
    unittest.main()
