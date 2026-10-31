"""Reconstruction v12 B2: receipts, checks executed through the runner with their result bound to the run, and the
G1-G6 qualification tests with capability declarations refused at admission unless qualified (CAP-01, VAL-06,
STATE-01 receipt fields). All inputs are SYNTHETIC."""
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[3]
SCRIPTS = PLUGIN / "skills" / "hep-computing" / "scripts"
RUNNER = SCRIPTS / "run_workflow.py"
CAPS = SCRIPTS / "executor_capabilities.py"


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def canonical(d) -> bytes:
    return json.dumps(d, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def run(*args, timeout=600):
    p = subprocess.run([sys.executable, "-B", *map(str, args)], capture_output=True, text=True, timeout=timeout)
    return p.returncode, json.loads(p.stdout)


CHECK_PY = """import hashlib, json, sys
crit = json.load(open('criteria.json'))
val = float(open('target.txt').read())
res = 'pass' if abs(val - crit['expected']) < crit['tolerance'] else 'fail'
json.dump({'check_digest': sys.argv[1], 'criterion_digest': sys.argv[2], 'target_artifact_digest': sys.argv[3],
           'result': res, 'reason': f'|{val} - expected| vs tolerance', 'samples': sys.argv[4:]}, open('result.json', 'w'))
"""


class Base(unittest.TestCase):
    def setUp(self):
        self._t = tempfile.TemporaryDirectory()
        self.root = Path(self._t.name)
        self.work = self.root / "work"
        self.work.mkdir()

    def tearDown(self):
        self._t.cleanup()

    def write_workflow(self, steps):
        p = self.root / "wf.json"
        p.write_text(json.dumps({"workflow": "b2", "steps": steps}), encoding="utf-8")
        return p


class Receipts(Base):
    def test_receipt_fields_and_records_unchanged(self):
        steps = [{"id": "s", "argv": ["{python}", "-c", "open('o.txt','w').write('1')"], "outputs": ["o.txt"]}]
        code, out = run(RUNNER, self.write_workflow(steps), "--work", self.work, "--created", "2026-10-29",
                        "--receipt-dir", self.root / "receipts", "--attempt-prefix", "w1/")
        self.assertEqual(code, 0, out)
        rec = json.loads((self.root / "receipts" / "w1" / "s.receipt.json").read_text())
        self.assertEqual((rec["attempt"], rec["end_status"], rec["termination"]), ("w1/s", "success", "confirmed"))
        self.assertEqual(rec["outputs"], [{"logical": "o.txt", "location": "o.txt", "location_kind": "attempt-owned",
                                           "sha256": sha(b"1")}])
        self.assertEqual(rec["artifact_digest"], sha(canonical({"o.txt": sha(b"1")})))
        self.assertEqual(rec["observed_inputs"]["observable"], False)
        self.assertIsNone(rec["conditions_resolution"])
        self.assertEqual(rec["environment_ref"]["sha256"],
                         sha((self.work / "runs" / "s.computational-run.json").read_bytes()))
        self.assertGreaterEqual(rec["usage"]["wall_s"], 0)
        self.assertGreaterEqual(rec["usage"]["cpu_s"], 0)
        self.assertFalse(any(self.work.rglob("*.receipt.json")))  # receipts stay out of the work folder

    def test_an_attempt_id_is_used_once(self):
        """A receipt identifies one attempt: a rerun with the same prefix is refused before it runs and the earlier
        receipt is kept; a new prefix runs (positive control)."""
        receipts = self.root / "receipts"
        steps = [{"id": "s", "argv": ["{python}", "-c", "open('o.txt','w').write('1')"], "outputs": ["o.txt"]}]
        self.assertEqual(run(RUNNER, self.write_workflow(steps), "--work", self.work, "--receipt-dir", receipts,
                             "--attempt-prefix", "a1:")[0], 0)
        first = (receipts / "a1:s.receipt.json").read_bytes()
        steps[0]["argv"][-1] = "open('o.txt','w').write('2')"
        code, out = run(RUNNER, self.write_workflow(steps), "--work", self.work, "--receipt-dir", receipts,
                        "--attempt-prefix", "a1:")
        self.assertEqual((code, out["status"]), (2, "rejected"), out)
        self.assertIn("a1:s", out["error"])
        self.assertEqual((receipts / "a1:s.receipt.json").read_bytes(), first)
        self.assertEqual((self.work / "o.txt").read_text(), "1")  # the second attempt did not run
        code, out = run(RUNNER, self.write_workflow(steps), "--work", self.work, "--receipt-dir", receipts,
                        "--attempt-prefix", "a2:")
        self.assertEqual(code, 0, out)
        self.assertEqual(json.loads((receipts / "a2:s.receipt.json").read_text())["attempt"], "a2:s")

    def test_no_receipt_without_the_option(self):
        steps = [{"id": "s", "argv": ["{python}", "-c", "open('o.txt','w').write('1')"], "outputs": ["o.txt"]}]
        self.assertEqual(run(RUNNER, self.write_workflow(steps), "--work", self.work)[0], 0)
        self.assertFalse(any(self.root.rglob("*.receipt.json")))


class CheckBinding(Base):
    """A check runs through the runner; its result counts only when bound to the run (VAL-06)."""

    def setUp(self):
        super().setUp()
        (self.work / "check.py").write_text(CHECK_PY)
        (self.work / "criteria.json").write_text(json.dumps({"expected": 1.0, "tolerance": 0.1}))
        (self.work / "target.txt").write_text("1.02")
        self.check_d = sha((self.work / "check.py").read_bytes())
        self.crit_d = sha((self.work / "criteria.json").read_bytes())
        self.target_d = sha(canonical({"value.txt": sha(b"1.02")}))

    def step(self, args=None, **over):
        chk = {"check_digest": self.check_d, "criterion_digest": self.crit_d, "target_artifact_digest": self.target_d,
               "criteria_file": "criteria.json", "result_file": "result.json",
               "target_manifest": {"value.txt": "target.txt"}, "role": "closure", "type": "performance-estimate",
               "samples": ["CR"]}
        chk.update(over)
        argv = ["{python}", "check.py", *(args or [self.check_d, self.crit_d, self.target_d, "CR"])]
        return [{"id": "chk", "argv": argv, "inputs": ["check.py", "criteria.json", "target.txt"],
                 "outputs": ["result.json"], "check": chk}]

    def runit(self, steps):
        code, out = run(RUNNER, self.write_workflow(steps), "--work", self.work)
        rec = json.loads((self.work / "runs" / "chk.computational-run.json").read_text())
        return code, out, rec["extension"].get("check_result")

    def test_bound_result_counts(self):
        code, out, res = self.runit(self.step())
        self.assertEqual(code, 0, out)
        self.assertEqual((res["bound"], res["result"], res["samples"]), (True, "pass", ["CR"]))

    def test_a_check_digest_of_another_program_is_not_bound(self):
        code, _, res = self.runit(self.step(check_digest="f" * 64))
        self.assertEqual((code, res["bound"]), (1, False))
        self.assertIn("check digest", " ".join(res["problems"]))

    def test_a_criterion_digest_of_another_file_is_not_bound(self):
        code, _, res = self.runit(self.step(criterion_digest="e" * 64))
        self.assertEqual((code, res["bound"]), (1, False))

    def test_a_target_that_was_not_staged_is_not_bound(self):
        code, _, res = self.runit(self.step(target_artifact_digest="d" * 64))
        self.assertEqual((code, res["bound"]), (1, False))

    def test_a_sample_outside_the_read_list_is_not_bound(self):
        code, _, res = self.runit(self.step(args=[self.check_d, self.crit_d, self.target_d, "CONF"]))
        self.assertEqual((code, res["bound"]), (1, False))

    def producer_digest(self, files: dict) -> str:
        """Run a producer step in its own work folder; return the artifact digest its run record holds."""
        prod = self.root / "producer"
        code = ";".join(f"open({n!r}, 'w').write({t!r})" for n, t in files.items())
        steps = [{"id": "reco", "argv": ["{python}", "-c", code], "outputs": sorted(files)}]
        rc, out = run(RUNNER, self.write_workflow(steps), "--work", prod)
        self.assertEqual(rc, 0, out)
        return json.loads((prod / "runs" / "reco.computational-run.json").read_text())["extension"]["artifact_digest"]

    def test_the_producers_artifact_digest_binds(self):
        """Control §4: the artifact is the manifest {logical name: digest}; the runner's logical name of an output is
        its path in the producer's work folder, and target_manifest maps those names to the staged copies. A digest
        copied from the producer's record binds, whatever the staged file is called."""
        digest = self.producer_digest({"value.txt": "1.02"})
        self.assertEqual(digest, self.target_d)
        code, out, res = self.runit(self.step(args=[self.check_d, self.crit_d, digest, "CR"],
                                              target_artifact_digest=digest))
        self.assertEqual((code, res["bound"]), (0, True), out)

    def test_a_target_staged_in_part_does_not_bind(self):  # every output of the target must be staged
        digest = self.producer_digest({"value.txt": "1.02", "extra.txt": "x"})
        code, _, res = self.runit(self.step(args=[self.check_d, self.crit_d, digest, "CR"],
                                            target_artifact_digest=digest))
        self.assertEqual((code, res["bound"]), (1, False))

    def test_a_failing_check_is_a_bound_fail(self):  # the result is recorded as it is, never upgraded
        (self.work / "target.txt").write_text("1.5")
        target_d = sha(canonical({"value.txt": sha(b"1.5")}))
        code, _, res = self.runit(self.step(args=[self.check_d, self.crit_d, target_d, "CR"],
                                            target_artifact_digest=target_d))
        self.assertEqual((code, res["bound"], res["result"]), (0, True, "fail"))


class Capabilities(unittest.TestCase):
    """G1-G6 qualification tests; a capability without a passing qualification is refused at admission (CAP-01)."""

    @classmethod
    def setUpClass(cls):
        cls._t = tempfile.TemporaryDirectory()
        cls.root = Path(cls._t.name)
        cls.qual, cls.decl = cls.root / "qual.json", cls.root / "decl.json"
        cls.q_code, cls.q_out = run(CAPS, "qualify", "--out", cls.qual)
        cls.d_code, cls.d_out = run(CAPS, "declare", "--qualification", cls.qual, "--out", cls.decl)

    @classmethod
    def tearDownClass(cls):
        cls._t.cleanup()

    @unittest.skipUnless(os.name == "posix", "G1/G2 are qualified on POSIX hosts (tested on Linux)")
    def test_g1_g2_pass_and_the_rest_are_unsupported(self):
        self.assertEqual(self.q_code, 0, self.q_out)
        self.assertEqual(self.q_out["tests"], {"G1": "pass", "G2": "pass", "G3": "unsupported", "G4": "unsupported",
                                               "G5": "unsupported", "G6": "unsupported"})
        qual = json.loads(self.qual.read_text())
        self.assertTrue(all(c["passed"] for c in qual["tests"]["G1"]["cases"]))
        self.assertEqual(self.d_out["declared"], ["G1", "G2"])

    @unittest.skipUnless(os.name == "posix", "G1/G2 are qualified on POSIX hosts")
    def test_admission(self):
        self.assertEqual(run(CAPS, "admit", "--declaration", self.decl, "--qualification", self.qual,
                             "--require", "G1,G2")[0], 0)
        self.assertEqual(run(CAPS, "admit", "--declaration", self.decl, "--qualification", self.qual,
                             "--mode", "M1")[0], 0)
        code, out = run(CAPS, "admit", "--declaration", self.decl, "--qualification", self.qual, "--mode", "M2")
        self.assertEqual(code, 1)
        self.assertEqual(sorted(out["refused"]), ["G5"])

    @unittest.skipUnless(os.name == "posix", "G1/G2 are qualified on POSIX hosts")
    def test_fabricated_or_stale_declarations_are_refused(self):
        decl = json.loads(self.decl.read_text())
        forged = self.root / "forged.json"
        forged.write_text(json.dumps({**decl, "capabilities": {**decl["capabilities"],
                                                               "G5": {"qualification_sha256": "0" * 64}}}))
        code, out = run(CAPS, "admit", "--declaration", forged, "--qualification", self.qual, "--require", "G5")
        self.assertEqual((code, list(out["refused"])), (1, ["G5"]))
        qual = json.loads(self.qual.read_text())
        stale = self.root / "stale.json"
        stale.write_text(json.dumps({**qual, "runner_sha256": "1" * 64}))
        code, out = run(CAPS, "admit", "--declaration", self.decl, "--qualification", stale, "--require", "G1")
        self.assertEqual(code, 1)  # the declaration no longer cites this record
        self.assertEqual(run(CAPS, "admit", "--declaration", self.decl, "--qualification", self.qual,
                             "--require", "G9")[0], 2)


if __name__ == "__main__":
    unittest.main()
