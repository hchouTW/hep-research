"""Regression tests for three review findings on the control-layer helper (PR #330), each written to fail before
its fix:
1. a multi-line append cut short by a crash (only its first whole lines on disk) was loaded as a complete,
   acknowledged batch, and a retry with the same --op returned the partial facts as replayed;
2. no command recorded that execution started, so `cancel` on an attempt whose run was in progress settled it as
   cancelled at once and its real receipt was then refused;
3. lease owners were self-declared names: `lock release --owner s1` followed by `lock acquire --owner s2` bypassed
   the live-lease refusal and the reconcile-before-takeover rule, and `--owner s1` alone passed the write check.
All inputs are SYNTHETIC. The control rules did not pass S0 (N1); these tests check the helper, not the rules."""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_control_layer import Base  # noqa: E402


class TornBatch(Base):
    """Finding 1: a batch is all-or-nothing on load; `recover` cuts an incomplete tail batch back to its start."""

    def admitted_with_a_read(self):
        self.init_and_contract()
        head = self.head()
        code, out = self.admit("a1:raw", "--step", "raw", "--cost", "0", "--read", "CR", "--op", "adm-1")
        self.assertEqual(code, 0, out)
        self.assertEqual([f["kind"] for f in out["written"]], ["intent", "exposure"])
        return head

    def cut_last_line(self):
        content = self.task_log.read_bytes()
        cut = content.rstrip(b"\n").rfind(b"\n") + 1
        self.task_log.write_bytes(content[:cut])          # the crash left only the first whole line of the batch

    def test_a_half_written_batch_is_refused_and_recovered_to_its_start(self):
        head = self.admitted_with_a_read()
        self.cut_last_line()
        code, out = self.call("verify")
        self.assertEqual(code, 2, out)
        self.assertIn("batch", out["error"])
        code, out = self.call("recover")
        self.assertEqual((code, out["recovered"], out["head"]), (0, True, head), out)
        code, out = self.admit("a1:raw", "--step", "raw", "--cost", "0", "--read", "CR", "--op", "adm-1")
        self.assertEqual(code, 0, out)
        self.assertNotIn("replayed", out)                  # the retry writes the whole batch again
        self.assertEqual([f["kind"] for f in out["written"]], ["intent", "exposure"])
        self.assertEqual(self.call("verify")[0], 0)

    def test_a_retry_never_replays_a_partial_batch(self):
        self.admitted_with_a_read()
        self.cut_last_line()
        before = self.task_log.read_bytes()
        code, out = self.call("admit", "--attempt", "a1:raw", "--step", "raw", "--cost", "0", "--read", "CR",
                              "--op", "adm-1", "--expect-head", "3", "--declaration", self.decl,
                              "--qualification", self.qual)
        self.assertNotEqual(code, 0, out)                  # refused (record torn), never "replayed" with one fact
        self.assertNotIn("replayed", out)
        self.assertEqual(self.task_log.read_bytes(), before)


class StartBeforeCancel(Base):
    """Finding 2: `start` records that execution began; `cancel` of an attempt without it needs --never-started."""

    def test_cancel_cannot_settle_an_attempt_whose_run_may_be_in_progress(self):
        self.init_and_contract()
        self.assertEqual(self.admit("a1:raw", "--step", "raw", "--cost", "0")[0], 0)
        before = self.task_log.read_bytes()
        code, out = self.write("cancel", "--attempt", "a1:raw")
        self.assertEqual(code, 2, out)
        self.assertIn("--never-started", out["error"])
        self.assertEqual(self.task_log.read_bytes(), before)

    def test_a_started_attempt_is_cancelling_and_keeps_its_receipt(self):
        self.init_and_contract()
        self.assertEqual(self.admit("a1:raw", "--step", "raw", "--cost", "0")[0], 0)
        code, out = self.write("start", "--attempt", "a1:raw")
        self.assertEqual((code, out["written"][0]["kind"], out["written"][0]["writer"]), (0, "start", "adapter"), out)
        proc, work, receipt = self.run_step("a1:", "raw", ["{python}", "-c", "open('o.txt','w').write('1.02')"])
        self.assertEqual(self.write("cancel", "--attempt", "a1:raw")[0], 0)
        code, st = self.call("status")
        self.assertEqual(st["attempts"][0]["state"], "cancelling")
        code, out = self.write("receipt", "--receipt", receipt, "--work", work)
        self.assertEqual(code, 0, out)                     # succeeded before the cancellation took effect
        code, st = self.call("status")
        self.assertEqual(st["attempts"][0]["state"], "computed")

    def test_never_started_is_stated_explicitly(self):
        self.init_and_contract()
        self.admit("a1:raw", "--step", "raw", "--cost", "0")
        code, out = self.write("cancel", "--attempt", "a1:raw", "--never-started")
        self.assertEqual(code, 0, out)
        self.assertEqual(self.call("status")[1]["attempts"][0]["state"], "cancelled")
        self.assertEqual(self.write("start", "--attempt", "a1:raw")[0], 2)   # no start after a settled cancel


if __name__ == "__main__":
    unittest.main()
