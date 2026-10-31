"""Reconstruction v12 C2: resumption summary, restart reconciliation (reconcile, cancel, lost runs), lease lock with
takeover after reconciliation, torn-tail recovery, and the M2 path once G5 is qualified (Core §6.4, Control §3,
§5.5; CTRL-01, STATE-01, G5). The G5 fault-injection qualification itself runs in test_executor_b2. All inputs are
SYNTHETIC. The control rules did not pass S0 (N1); these tests check the helper, not the rules."""
import json
import sys
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_control_layer import SCRIPTS, Base, agent_free_env, contract_json  # noqa: E402

sys.path.insert(0, str(SCRIPTS))
import executor_capabilities as caps  # noqa: E402
from control_layer_support import lease as leases  # noqa: E402


class C2Base(Base):
    def raw_admitted_and_lost(self):
        self.init_and_contract()
        self.assertEqual(self.admit("a1:raw", "--step", "raw", "--cost", "0")[0], 0)
        code, out = self.write("receipt", "--lost", "--attempt", "a1:raw", "--reason", "session died")
        self.assertEqual(code, 0, out)
        self.assertEqual(out["written"][0]["fields"]["termination"], "unknown")

    def real_receipt(self, prefix="a1:", step="raw"):
        return self.run_step(prefix, step, ["{python}", "-c", "open('o.txt','w').write('1.02')"])


class Resume(C2Base):
    def test_a_fresh_session_learns_what_not_to_resubmit_and_what_to_do(self):
        self.raw_admitted_and_lost()
        code, first = self.call("resume")
        self.assertEqual(code, 0, first)
        self.assertEqual(first, self.call("resume")[1])                    # deterministic, facts only
        self.assertEqual(first["attempts_by_state"], {"unknown": ["a1:raw"]})
        self.assertEqual(first["do_not_resubmit"], ["a1:raw"])
        self.assertIn("did NOT pass the S0", first["limitation"])
        self.assertEqual(first["next_actions"][0]["attempt"], "a1:raw")
        self.assertIn("reconcile", first["next_actions"][0]["do"])
        self.assertEqual(first["contract"]["effective_seq"], 1)
        self.assertEqual(first["deliverables"]["D"]["state"], "not started")
        compute = [a for a in first["next_actions"] if a.get("do") == "compute"]
        self.assertEqual(compute[0]["step"], "raw")
        self.assertIn("same identity", compute[0]["admission"])

    def test_next_actions_follow_the_chain(self):
        self.init_and_contract()
        code, out = self.call("resume")
        self.assertEqual([(a["do"], a["step"], a["admission"]) for a in out["next_actions"]],
                         [("compute", "raw", "would be admitted")])
        self.admit("a1:raw", "--step", "raw", "--cost", "0")
        proc, work, receipt = self.real_receipt()
        self.write("receipt", "--receipt", receipt, "--work", work)
        self.admit("b1:reco", "--step", "reco", "--cost", "0")
        proc, work, receipt = self.run_step("b1:", "reco", ["{python}", "-c", "open('o.txt','w').write('2')"])
        self.write("receipt", "--receipt", receipt, "--work", work)
        code, out = self.call("resume")
        self.assertEqual(out["next_actions"][0]["do"], "admit the missing checks")
        self.assertEqual(out["next_actions"][0]["checks"], [[self.check_d, self.crit_d]])

    def test_pending_contracts_are_listed_for_a_human(self):
        self.init_and_contract()
        loose = contract_json(self.check_d, self.crit_d, required_checks=[[self.check_d, "f" * 64]])
        (self.root / "loose.json").write_text(json.dumps(loose))
        self.write("contract", "--file", self.root / "loose.json")
        code, out = self.call("resume")
        self.assertEqual(out["pending_for_humans"][0], {"kind": "approve_contract", "ref": 2, "why": out[
            "pending_for_humans"][0]["why"]})
        self.assertTrue(any(a["do"] == "ask a human: approve_contract" for a in out["next_actions"]))


class Reconciliation(C2Base):
    def test_reconcile_from_a_confirmed_receipt_after_unknown(self):
        self.raw_admitted_and_lost()
        proc, work, receipt = self.real_receipt()
        code, out = self.write("reconcile", "--receipt", receipt, "--work", work)
        self.assertEqual(code, 0, out)
        self.assertEqual((out["written"][0]["kind"], out["written"][0]["writer"]), ("reconcile", "adapter"))
        code, st = self.call("status")
        self.assertEqual(st["attempts"][0]["state"], "computed")
        self.assertEqual(st["steps"]["raw"]["artifacts"][0]["label"], "ok")
        code, out = self.write("reconcile", "--receipt", receipt, "--work", work)
        self.assertEqual(code, 2, out)                                     # only for unknown or abandoned

    def test_reconcile_after_a_human_abandon_moves_the_cost_to_used(self):
        self.raw_admitted_and_lost()
        code, out = self.write("decide", "--action", "abandon", "--attempt", "a1:raw", "--confirm-human",
                               env=agent_free_env())
        self.assertEqual(code, 0, out)
        proc, work, receipt = self.real_receipt()
        self.assertEqual(self.write("reconcile", "--receipt", receipt, "--work", work)[0], 0)
        code, st = self.call("status")
        self.assertEqual(st["attempts"][0]["state"], "abandoned_reconciled")
        self.assertEqual(st["steps"]["raw"]["artifacts"], [])               # an abandoned attempt is not a producer

    def test_an_unconfirmed_receipt_cannot_reconcile(self):
        self.raw_admitted_and_lost()
        proc, work, receipt = self.real_receipt()
        doc = json.loads(receipt.read_text())
        doc["termination"] = "unconfirmed"
        receipt.write_text(json.dumps(doc))
        code, out = self.write("reconcile", "--receipt", receipt, "--work", work)
        self.assertEqual(code, 2, out)

    def test_a_check_attempt_without_a_result_is_a_failed_check_draw(self):
        self.init_and_contract()
        self.admit("a1:raw", "--step", "raw", "--cost", "0")
        proc, work, receipt = self.real_receipt()
        self.write("receipt", "--receipt", receipt, "--work", work)
        self.admit("b1:reco", "--step", "reco", "--cost", "0")
        proc, work, receipt = self.run_step("b1:", "reco", ["{python}", "-c", "open('o.txt','w').write('2')"])
        reco = self.write("receipt", "--receipt", receipt, "--work", work)[1]["written"][0]["fields"]["outputs"][0]
        self.assertEqual(self.admit("c1:chk", "--check", self.check_d, "--criterion", self.crit_d, "--target", reco,
                                    "--cost", "0", "--read", "CR")[0], 0)
        self.assertEqual(self.write("receipt", "--lost", "--attempt", "c1:chk")[0], 0)
        code, rep = self.call("report")
        self.assertEqual(rep["1_deliverables"]["D"]["failed_check_draws"], [["reco", reco, "c1:chk", "unknown", ["CR"]]])
        self.assertEqual(len(rep["3_scientific_evidence"]["task_history"]["failed_check_draws"]), 1)

    def test_lost_is_only_for_an_unsettled_attempt(self):
        self.init_and_contract()
        code, out = self.write("receipt", "--lost", "--attempt", "never")
        self.assertEqual(code, 2, out)

    def test_cancel_before_start_and_after_end(self):
        self.init_and_contract()
        self.admit("a1:raw", "--step", "raw", "--cost", "0")
        code, out = self.write("cancel", "--attempt", "a1:raw", "--never-started")   # PR #330: stated explicitly
        self.assertEqual((code, out["written"][0]["kind"], out["written"][0]["writer"]), (0, "cancel_request", "C"))
        code, st = self.call("status")
        self.assertEqual(st["attempts"][0]["state"], "cancelled")
        self.assertEqual(self.write("cancel", "--attempt", "a1:raw")[0], 2)
        code, rep = self.call("report")
        self.assertEqual(rep["1_deliverables"]["D"]["failed_draws"], [["raw", "a1:raw", "cancelled"]])


class LeaseLock(C2Base):
    def lock(self, action, owner=None, lease_s=None):
        args = ["lock", action] + (["--owner", owner] if owner else []) + (["--lease-s", lease_s] if lease_s else [])
        return self.call(*args)

    def test_a_live_lease_serializes_writers_but_not_compare_and_set(self):
        self.init_and_contract()
        code, out = self.lock("acquire", "s1")
        self.assertEqual((code, out["event"]), (0, "acquire"))
        code, out = self.write("exposure", "--sample", "CR", "--owner", "s2")
        self.assertEqual((code, out["status"]), (1, "refused"))
        self.assertIn("lease", out["reason"])
        code, out = self.write("exposure", "--sample", "CR")
        self.assertEqual(code, 1, out)                                     # no owner: also refused
        code, out = self.write("exposure", "--sample", "CR", "--owner", "s1", expect=0)
        self.assertEqual((code, out["status"]), (1, "rerun-required"))     # the lease never replaces the CAS
        self.assertEqual(self.write("exposure", "--sample", "CR", "--owner", "s1")[0], 0)
        code, out = self.write("decide", "--action", "unblind", "--sample", "S", "--confirm-human",
                               env=agent_free_env())
        self.assertEqual(code, 0, out)                                     # a human decision is not blocked
        self.assertEqual(self.lock("acquire", "s1")[1]["event"], "renew")
        self.assertEqual(self.lock("release", "s2")[0], 1)
        self.assertEqual(self.lock("release", "s1")[1]["event"], "release")
        events = [e["event"] for e in self.lock("status")[1]["history"]]
        self.assertEqual(events, ["acquire", "renew", "release"])

    def test_takeover_only_when_expired_and_after_reconciliation(self):
        self.raw_admitted_and_lost()
        self.assertEqual(self.lock("acquire", "s1", 1)[0], 0)
        code, out = self.lock("acquire", "s2")
        self.assertIn("live lease", out["reason"])
        time.sleep(1.2)
        code, out = self.lock("acquire", "s2")
        self.assertEqual(code, 1)
        self.assertIn("reconcile first", out["reason"])
        proc, work, receipt = self.real_receipt()
        self.assertEqual(self.write("reconcile", "--receipt", receipt, "--work", work)[0], 0)
        code, out = self.lock("acquire", "s2")
        self.assertEqual((code, out["event"], out["owner"]), (0, "takeover", "s2"))
        last = self.lock("status")[1]["history"][-1]
        self.assertEqual((last["event"], last["previous_owner"]), ("takeover", "s1"))

    def test_m2_writes_need_the_lease(self):
        self.assertEqual(self.call("init", "--mode", "M2")[0], 0)
        (self.root / "c.json").write_text(json.dumps(contract_json(self.check_d, self.crit_d)))
        code, out = self.write("contract", "--file", self.root / "c.json")
        self.assertIn("under M2 every write holds a live lease", out["reason"])

    def test_a_tampered_lease_history_is_refused(self):
        self.init_and_contract()
        self.lock("acquire", "s1")
        self.lock("release", "s1")
        path = leases.history_path(self.task_log)
        path.write_bytes(path.read_bytes().replace(b'"s1"', b'"sX"', 1))
        code, out = self.lock("status")
        self.assertEqual(code, 2, out)


class TornTail(C2Base):
    def test_a_torn_last_line_is_recovered_and_kept_aside(self):
        self.init_and_contract()
        code, before = self.call("status")
        with open(self.task_log, "ab") as handle:
            handle.write(b'{"batch":3,"fields"')
        self.assertEqual(self.call("verify")[0], 2)
        code, out = self.call("recover")
        self.assertEqual((code, out["recovered"], out["torn_bytes"]), (0, True, 19))
        self.assertEqual(self.call("status")[1], before)
        self.assertEqual((self.task_log.parent / f"task-log.jsonl.torn-{out['torn_sha256']}").read_bytes(),
                         b'{"batch":3,"fields"')
        self.assertEqual(self.call("recover")[1]["recovered"], False)


class M2Path(C2Base):
    """With G5 qualified, M2 works through the session fact, a human approval of the first contract and the lease;
    receipts must carry usage (Control §2). M3 stays refused (G3, G4 unsupported)."""

    def setUp(self):
        super().setUp()
        qual = json.loads(self.qual.read_text())
        qual["tests"]["G5"] = {"status": "pass", "cases": [], "note": "synthetic for this test; the real G5 "
                                                                       "qualification runs in test_executor_b2"}
        qual["control_sha256"] = caps.control_digest()
        self.qual.write_text(json.dumps(qual))
        self.decl.write_text(json.dumps(caps.declare(qual)))

    def test_m2_admits_after_approval_and_receipts_carry_usage(self):
        code, out = self.init_and_contract(mode="M2")
        self.assertEqual(out["contract_status"], "pending_approval")
        self.assertEqual(self.write("decide", "--action", "approve_contract", "--ref", 1, "--confirm-human",
                                    env=agent_free_env())[0], 0)
        code, out = self.admit("a1:raw", "--step", "raw", "--cost", "600", "--owner", "s1")
        self.assertEqual(code, 0, out)
        proc, work, receipt = self.real_receipt()
        code, out = self.write("receipt", "--receipt", receipt, "--work", work, "--owner", "s1")
        self.assertEqual(code, 0, out)
        self.assertGreaterEqual(out["written"][0]["fields"]["usage"], 0)   # --usage auto: wall_s under M2
        code, st = self.call("status")
        self.assertEqual(st["steps"]["raw"]["artifacts"][0]["label"], "ok")

    def test_m3_stays_refused(self):
        self.init_and_contract(mode="M3")
        self.write("decide", "--action", "approve_contract", "--ref", 1, "--confirm-human", env=agent_free_env())
        code, out = self.admit("a1:raw", "--step", "raw", "--cost", "600", "--owner", "s1")
        self.assertEqual(code, 1, out)
        self.assertIn("G3", out["reason"])
        self.assertIn("G4", out["reason"])


if __name__ == "__main__":
    unittest.main()
