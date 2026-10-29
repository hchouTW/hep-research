"""Reconstruction v12 C1: the control-layer helper's task record, CLI, receipt adapter, human-decision guard and
completion report (CTRL-01, AUTH-01, ADM-01, CAP-01, VAL-06, FLOW-01; Delivery §5.1 contract tests at the JSON level).
The derivation itself is tested against the reference model in test_control_layer_model.py. All inputs are
SYNTHETIC. The control rules did not pass S0 (N1); these tests check the helper, not the rules."""
import hashlib
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[3]
SCRIPTS = PLUGIN / "skills" / "hep-computing" / "scripts"
CONTROL_CLI = SCRIPTS / "control_layer.py"
RUNNER = SCRIPTS / "run_workflow.py"
sys.path.insert(0, str(SCRIPTS))
from control_layer_support import derivation as dv  # noqa: E402
from control_layer_support import task_record as tr  # noqa: E402
from control_layer_support.task_record import TaskRecord  # noqa: E402

AGENT_MARKERS = ("CLAUDECODE", "CLAUDE_CODE_ENTRYPOINT", "AI_AGENT")
CHECK_PY = """import json, sys
crit = json.load(open('criteria.json'))
val = float(open('target.txt').read())
res = 'pass' if abs(val - crit['expected']) < crit['tolerance'] else 'fail'
json.dump({'check_digest': sys.argv[1], 'criterion_digest': sys.argv[2], 'target_artifact_digest': sys.argv[3],
           'result': res, 'reason': f'|{val} - expected| vs tolerance', 'samples': sys.argv[4:]}, open('result.json', 'w'))
"""


def sha(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def canonical(value) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def agent_free_env():
    return {k: v for k, v in os.environ.items() if k not in AGENT_MARKERS}


def control_cli(*args, env=None):
    proc = subprocess.run([sys.executable, "-B", str(CONTROL_CLI), *map(str, args)], capture_output=True, text=True,
                          timeout=600, env=env)
    try:
        out = json.loads(proc.stdout)
    except ValueError:
        raise AssertionError(f"not JSON (exit {proc.returncode}): {proc.stdout[-500:]} {proc.stderr[-800:]}") from None
    return proc.returncode, out


def contract_json(check_d, crit_d, **reco_over):
    reco = {"program": "pReco", "environment": "py3.13", "upstream": ["raw"], "checked": True,
            "required_checks": [[check_d, crit_d]]}
    reco.update(reco_over)
    return {"steps": {"raw": {"program": "pRaw", "environment": "py3.13"}, "reco": reco},
            "deliverables": {"D": {"step": "reco", "target": "T2"}}, "families": {},
            "samples": {"CR": "control", "S": "confirmation"}, "budget": None}


class Base(unittest.TestCase):
    def setUp(self):
        self._scratch = tempfile.TemporaryDirectory()
        self.root = Path(self._scratch.name)
        self.task_log = self.root / "hep-research-artifacts" / "demo" / "task-log" / "task-log.jsonl"
        qual = {"kind": "executor-qualification", "executor": "local-run_workflow",
                "runner_sha256": sha(RUNNER.read_bytes()), "platform": {"system": "synthetic"},
                "tests": {"G1": {"status": "pass", "cases": []}, "G2": {"status": "pass", "cases": []},
                          **{g: {"status": "unsupported", "reason": "synthetic"} for g in ("G3", "G4", "G5", "G6")}}}
        self.qual = self.root / "qual.json"
        self.qual.write_text(json.dumps(qual))
        import executor_capabilities as caps  # noqa: PLC0415
        self.decl = self.root / "decl.json"
        self.decl.write_text(json.dumps(caps.declare(qual)))
        self.check_py = CHECK_PY.encode()
        self.criteria = json.dumps({"expected": 1.0, "tolerance": 0.1}).encode()
        self.check_d, self.crit_d = sha(self.check_py), sha(self.criteria)

    def tearDown(self):
        self._scratch.cleanup()

    def head(self):
        return TaskRecord(self.task_log).read().log.head

    def call(self, *args, env=None):
        return control_cli(*args, "--task-log", self.task_log, env=env)

    def write(self, *args, env=None, expect=None):
        return self.call(*args, "--expect-head", self.head() if expect is None else expect, env=env)

    def init_and_contract(self, mode="M1", **reco_over):
        self.assertEqual(self.call("init", "--mode", mode)[0], 0)
        path = self.root / "contract.json"
        path.write_text(json.dumps(contract_json(self.check_d, self.crit_d, **reco_over)))
        return self.write("contract", "--file", path)

    def admit(self, attempt, *args):
        return self.write("admit", "--attempt", attempt, "--declaration", self.decl, "--qualification", self.qual,
                          *args)

    def run_step(self, attempt_prefix, step_id, argv, inputs=None, outputs=("o.txt",), stage=None, check=None):
        """One run_workflow.py invocation of one step in a fresh work folder, with a receipt."""
        work = self.root / "work" / attempt_prefix.strip(":")
        work.mkdir(parents=True)
        for name, content in (stage or {}).items():
            (work / name).write_bytes(content)
        step = {"id": step_id, "argv": argv, "inputs": list(inputs or []), "outputs": list(outputs)}
        if check:
            step["check"] = check
        wf = self.root / f"{attempt_prefix.strip(':')}.workflow.json"
        wf.write_text(json.dumps({"workflow": "c1", "steps": [step]}))
        receipts = self.root / "receipts"
        proc = subprocess.run([sys.executable, "-B", str(RUNNER), str(wf), "--work", str(work), "--created",
                               "2026-10-29", "--receipt-dir", str(receipts), "--attempt-prefix", attempt_prefix],
                              capture_output=True, text=True, timeout=600)
        return proc, work, receipts / f"{attempt_prefix}{step_id}.receipt.json"


class EndToEnd(Base):
    """A full T2 path: contract, admission, runner receipts, a bound check, publish, report."""

    def test_full_path_publishes_and_reports_the_limitation(self):
        code, out = self.init_and_contract()
        self.assertEqual((code, out["contract_status"]), (0, "effective"), out)
        code, out = self.admit("a1:raw", "--step", "raw", "--cost", "0")
        self.assertEqual(code, 0, out)
        proc, work, receipt = self.run_step("a1:", "raw", ["{python}", "-c", "open('o.txt','w').write('1.02')"])
        self.assertEqual(proc.returncode, 0, proc.stdout)
        code, out = self.write("receipt", "--receipt", receipt, "--work", work)
        self.assertEqual(code, 0, out)
        raw_digest = out["written"][0]["fields"]["outputs"][0]
        self.assertEqual(raw_digest, sha(canonical({"o.txt": sha(b"1.02")})))
        code, out = self.admit("b1:reco", "--step", "reco", "--cost", "0")
        self.assertEqual(code, 0, out)
        self.assertEqual(out["written"][0]["fields"]["inputs"], {"raw": raw_digest})
        proc, work, receipt = self.run_step("b1:", "reco", ["{python}", "-c",
                                                            "open('o.txt','w').write('%.3f' % float(open('in.txt').read()))"],
                                            inputs=["in.txt"], stage={"in.txt": b"1.02"})
        self.assertEqual(proc.returncode, 0, proc.stdout)
        code, out = self.write("receipt", "--receipt", receipt, "--work", work)
        reco_digest = out["written"][0]["fields"]["outputs"][0]
        self.assertEqual(reco_digest, sha(canonical({"o.txt": sha(b"1.020")})))
        code, out = self.call("status")
        self.assertEqual(out["deliverables"]["D"]["artifact_label"], None)
        self.assertEqual(out["steps"]["reco"]["artifacts"][0]["label"], "unchecked")
        code, out = self.write("publish", "--deliverable", "D")
        self.assertEqual((code, out["status"]), (1, "refused"), out)
        code, out = self.admit("c1:chk", "--check", self.check_d, "--criterion", self.crit_d, "--target",
                               reco_digest, "--cost", "0", "--read", "CR")
        self.assertEqual(code, 0, out)
        self.assertEqual([f["kind"] for f in out["written"]], ["intent", "exposure"])
        check = {"check_digest": self.check_d, "criterion_digest": self.crit_d, "target_artifact_digest": reco_digest,
                 "criteria_file": "criteria.json", "result_file": "result.json",
                 "target_manifest": {"o.txt": "target.txt"}, "role": "closure", "type": "performance-estimate",
                 "samples": ["CR"]}
        proc, work, receipt = self.run_step(
            "c1:", "chk", ["{python}", "check.py", self.check_d, self.crit_d, reco_digest, "CR"],
            inputs=["check.py", "criteria.json", "target.txt"], outputs=["result.json"],
            stage={"check.py": self.check_py, "criteria.json": self.criteria, "target.txt": b"1.020"}, check=check)
        self.assertEqual(proc.returncode, 0, proc.stdout)
        code, out = self.write("receipt", "--receipt", receipt, "--work", work)
        self.assertEqual([f["kind"] for f in out["written"]], ["receipt", "check_result"], out)
        self.assertNotIn("warning", out)
        self.assertEqual(out["written"][1]["fields"]["sample"], "CR")
        code, out = self.call("status")
        self.assertEqual((out["deliverables"]["D"]["state"], out["deliverables"]["D"]["achieved"]), ("done", "T2"))
        code, out = self.write("publish", "--deliverable", "D")
        self.assertEqual(code, 0, out)
        fields = out["written"][0]["fields"]
        self.assertEqual((fields["digest"], fields["achieved"], fields["chain_artifacts"], fields["derivation"]),
                         (reco_digest, "T2", 2, dv.DERIVATION_VERSION))
        code, rep = self.call("report")
        self.assertEqual((code, rep["overall"], rep["unsettled_attempts"]), (0, "complete", []))
        self.assertIn("did NOT pass the S0", rep["5_limitations"][0])
        self.assertEqual(rep["2_computation"]["steps"]["reco"]["artifacts"][0]["kind"], "attested (declared inputs)")
        code, rep = self.call("report", "--format", "markdown")
        self.assertIn("did NOT pass the S0", rep["markdown"])
        self.assertEqual(self.call("verify")[1]["head"], self.head())


class TaskRecordFile(Base):
    """CTRL-01: append only through the helper, digest chain, compare-and-set, whole-batch validation."""

    def test_stale_head_writes_nothing(self):
        self.init_and_contract()
        before = self.task_log.read_bytes()
        code, out = self.write("exposure", "--sample", "CR", expect=1)
        self.assertEqual((code, out["status"]), (1, "rerun-required"), out)
        code, out = self.write("exposure", "--sample", "CR", "--expect-digest", "0" * 64)
        self.assertEqual((code, out["status"]), (1, "rerun-required"), out)
        self.assertEqual(self.task_log.read_bytes(), before)

    def test_operation_id_is_idempotent(self):
        self.init_and_contract()
        head = self.head()
        code, out = self.write("exposure", "--sample", "CR", "--op", "look-1", expect=head)
        self.assertEqual(code, 0)
        code, again = self.write("exposure", "--sample", "CR", "--op", "look-1", expect=head)
        self.assertEqual((code, again.get("replayed"), again["head"]), (0, True, head + 1), again)
        code, other = self.write("exposure", "--sample", "S", "--op", "look-1", expect=head + 1)
        self.assertEqual(code, 2, other)
        self.assertEqual(self.head(), head + 1)

    def test_lines_are_chained_canonical_and_verified_on_load(self):
        self.init_and_contract()
        self.write("exposure", "--sample", "CR")
        code, out = self.write("exposure", "--sample", "CR")
        anchor = out["head_digest"]
        raws = self.task_log.read_bytes().split(b"\n")[:-1]
        lines = [json.loads(r) for r in raws]
        self.assertEqual([x["seq"] for x in lines], list(range(len(lines))))
        self.assertIsNone(lines[0]["prev"])
        for prev, line in zip(raws, lines[1:]):
            self.assertEqual(line["prev"], sha(prev))
        self.assertEqual((lines[0]["kind"], lines[0]["writer"]), ("session", "C"))
        good = self.task_log.read_bytes()
        edited = good.replace(b'"sample":"CR"', b'"sample":"S"', 1)
        reordered = b"\n".join([raws[0], raws[2], raws[1], raws[3]]) + b"\n"
        dropped = b"\n".join([raws[0], raws[2], raws[3]]) + b"\n"
        for bad in (edited, reordered, dropped, good[:-5], good.replace(b'{"batch"', b'{ "batch"', 1)):
            self.task_log.write_bytes(bad)
            code, out = self.call("verify")
            self.assertEqual(code, 2, out)
            self.assertIn("CorruptRecord", out["error"])
        last_edited = good[:good.rindex(b'"sample":"CR"')] + good[good.rindex(b'"sample":"CR"'):].replace(
            b'"sample":"CR"', b'"sample":"S"')
        self.task_log.write_bytes(last_edited)
        self.assertEqual(self.call("verify")[0], 0)  # no later line commits to the last one ...
        code, out = self.call("verify", "--anchor-digest", anchor)
        self.assertEqual(code, 2, out)               # ... only a digest kept outside the record catches it
        self.task_log.write_bytes(good)
        self.assertEqual(self.call("verify", "--anchor-digest", anchor)[0], 0)

    def test_a_rechained_record_with_an_invalid_fact_is_refused(self):
        self.init_and_contract()
        loaded = TaskRecord(self.task_log).read()
        log = loaded.log
        log.append("exposure", "agent", log.head, sample="CR")
        content = tr.dump_log(log)
        forged = content.replace(b'"writer":"agent"', b'"writer":"human"')
        lines, prev, out = forged.split(b"\n")[:-1], None, []
        for raw in lines:  # re-chain the forged lines so that only the replay catches them
            line = json.loads(raw)
            line["prev"] = prev
            raw = canonical(line)
            out.append(raw)
            prev = sha(raw)
        with self.assertRaises(tr.CorruptRecord) as caught:
            tr.load_bytes(b"".join(r + b"\n" for r in out))
        self.assertIn("may not write", str(caught.exception))

    def test_a_batch_is_validated_before_anything_is_written(self):
        self.init_and_contract()
        record = TaskRecord(self.task_log)
        before = self.task_log.read_bytes()

        def bad_batch(log):
            log.append_batch([("exposure", "agent", {"sample": "CR"}), ("exposure", "agent", {"sample": ["S"]})],
                             log.head)
        with self.assertRaises(dv.Rejected):
            record.transact(bad_batch, self.head())
        self.assertEqual(self.task_log.read_bytes(), before)

    def test_init_refuses_an_existing_record(self):
        self.assertEqual(self.call("init")[0], 0)
        self.assertEqual(self.call("init")[0], 2)


class ContractFormat(Base):
    """Delivery §5.1 contract row at the JSON level (the derivation-level rows run as the model's scenarios)."""

    def contract_file(self, document):
        path = self.root / "c.json"
        path.write_text(json.dumps(document) if not isinstance(document, str) else document)
        return path

    def test_malformed_contracts_are_rejected_and_nothing_is_written(self):
        self.assertEqual(self.call("init")[0], 0)
        good = contract_json(self.check_d, self.crit_d)
        bad_docs = []
        for mutate in (lambda c: c.update(alternatives={}), lambda c: c.pop("budget"),
                       lambda c: c["steps"]["reco"].update(checked="yes"),
                       lambda c: c["steps"]["reco"].update(rerun_allowed=1),
                       lambda c: c["steps"]["reco"].update(extra_field=True),
                       lambda c: c["steps"]["reco"].pop("environment"),
                       lambda c: c["steps"]["reco"].update(required_checks=[]),
                       lambda c: c["steps"]["reco"].update(required_checks=[["a", "b"], ["a", "b"]]),
                       lambda c: c["steps"]["reco"].update(upstream="raw"),
                       lambda c: c["steps"]["reco"].update(round=True, family="f"),
                       lambda c: c["deliverables"]["D"].update(required="no"),
                       lambda c: c["deliverables"]["D"].update(target="T4"),
                       lambda c: c["samples"].update(S="holdout-ish"),
                       lambda c: c.update(budget=-1),
                       lambda c: c["steps"].update(__x={"program": "p", "environment": "e"})):
            doc = json.loads(json.dumps(good))
            mutate(doc)
            bad_docs.append(doc)
        bad_docs.append(json.dumps(good).replace('"budget": null', '"budget": NaN'))
        bad_docs.append(json.dumps(good).replace('"budget": null', '"budget": Infinity'))
        before = self.task_log.read_bytes()
        for doc in bad_docs:
            with self.subTest(doc=str(doc)[:120]):
                code, out = self.write("contract", "--file", self.contract_file(doc))
                self.assertEqual((code, out["status"]), (2, "rejected"), out)
        self.assertEqual(self.task_log.read_bytes(), before)

    def test_iteration_family_rules_hold_whatever_the_listing_order(self):
        self.assertEqual(self.call("init")[0], 0)
        conv, mode = "c" * 64, "d" * 64
        req = [[conv, "k"], [mode, "k"]]

        def family_contract(order, twin):
            steps = {"al1": {"program": "p", "environment": "e", "family": "al", "round": 1},
                     "al2": {"program": "p", "environment": "e", "family": "al", "round": 2, "upstream": ["al1"],
                             "checked": True, "required_checks": req}}
            if twin:
                steps["twin"] = {"program": "q", "environment": "e", "family": "al", "round": 2, "upstream": ["al1"],
                                 "checked": True, "required_checks": req}
            names = list(steps) if order else list(reversed(steps))
            return {"steps": {n: steps[n] for n in names}, "deliverables": {},
                    "families": {"al": {"final_round": 2, "convergence_check": conv, "mode_check": mode}},
                    "samples": {}, "budget": None}
        for order in (True, False):
            code, out = self.write("contract", "--file", self.contract_file(family_contract(order, True)), "--dry-run")
            self.assertEqual(code, 2, out)
            code, out = self.write("contract", "--file", self.contract_file(family_contract(order, False)),
                                   "--dry-run")
            self.assertEqual((code, out["would_be"]), (0, "effective"), out)

    def test_loosening_waits_for_a_human_and_takes_effect_after_approval(self):
        code, out = self.init_and_contract()
        loose = contract_json(self.check_d, self.crit_d, required_checks=[[self.check_d, "f" * 64]])
        code, out = self.write("contract", "--file", self.contract_file(loose))
        self.assertEqual((code, out["contract_status"]), (0, "pending_approval"))
        ref = out["written"][0]["seq"]
        tight = contract_json(self.check_d, self.crit_d, required_checks=[[self.check_d, self.crit_d],
                                                                          ["e" * 64, "f" * 64]])
        code, out = self.write("contract", "--file", self.contract_file(tight), "--dry-run")
        self.assertEqual(out["would_be"], "effective")
        code, out = self.write("decide", "--action", "approve_contract", "--ref", ref, "--confirm-human",
                               env=agent_free_env())
        self.assertEqual(code, 0, out)
        code, st = self.call("status")
        self.assertEqual([c["status"] for c in st["contracts"]], ["superseded", "effective"])

    def test_the_contract_round_trips_through_the_json_form(self):
        spec = tr.decode_contract(contract_json(self.check_d, self.crit_d))
        self.assertIsInstance(spec["steps"]["reco"], dv.StepSpec)
        self.assertEqual(spec["steps"]["reco"].required, frozenset({(self.check_d, self.crit_d)}))
        self.assertEqual(tr.decode_contract(tr.encode_contract(spec)), spec)
        self.assertTrue(math.isnan(json.loads('{"b": NaN}')["b"]))  # why the record parser refuses NaN tokens
        with self.assertRaises(tr.CorruptRecord):
            tr.parse_line(b'{"b":NaN}', 0)


class Decisions(Base):
    """DEC-14: decisions only through `decide`, which is a guard (not an enforcement)."""

    def test_the_guard_refuses_an_agent_shell_and_a_missing_confirmation(self):
        self.init_and_contract()
        before = self.task_log.read_bytes()
        env = {**agent_free_env(), "CLAUDECODE": "1"}
        code, out = self.write("decide", "--action", "unblind", "--sample", "S", "--confirm-human", env=env)
        self.assertEqual((code, out["status"]), (1, "refused"), out)
        self.assertIn("guard, not an enforcement", out["reason"])
        code, out = self.write("decide", "--action", "unblind", "--sample", "S", env=agent_free_env())
        self.assertEqual((code, out["status"]), (1, "refused"), out)
        self.assertEqual(self.task_log.read_bytes(), before)
        code, out = self.write("decide", "--action", "unblind", "--sample", "S", "--confirm-human",
                               "--basis", "PI approval", env=agent_free_env())
        self.assertEqual(code, 0, out)
        self.assertEqual(out["written"][0]["writer"], "human")

    def test_decision_fields_are_validated(self):
        self.init_and_contract()
        code, out = self.write("decide", "--action", "abandon", "--confirm-human", env=agent_free_env())
        self.assertEqual(code, 2, out)
        code, out = self.write("decide", "--action", "approve_contract", "--confirm-human", env=agent_free_env())
        self.assertEqual(code, 2, out)

    def test_agents_cannot_write_decisions_or_receipts_through_the_library(self):
        log = dv.Log()
        for kind, writer in (("decision", "agent"), ("receipt", "agent"), ("check_result", "agent"),
                             ("intent", "agent"), ("publish", "agent"), ("contract", "human")):
            with self.assertRaises(dv.Rejected):
                log.append(kind, writer, attempt="z", action="abandon", end="success", termination="confirmed")


class AdmissionAndCapabilities(Base):
    """CAP-01 and ADM-01 through the CLI."""

    def test_m2_first_contract_waits_and_admission_refuses_without_g5(self):
        code, out = self.init_and_contract(mode="M2")
        self.assertEqual(out["contract_status"], "pending_approval")
        code, out = self.admit("a1:raw", "--step", "raw", "--cost", "0")
        self.assertEqual((code, out["reason"]), (1, "no effective contract"), out)
        code, out = self.write("decide", "--action", "approve_contract", "--ref", 1, "--confirm-human",
                               env=agent_free_env())
        self.assertEqual(code, 0, out)
        code, out = self.admit("a2:raw", "--step", "raw", "--cost", "0")
        self.assertEqual(code, 1, out)
        self.assertIn("G5", out["reason"])
        self.assertEqual(out["written"][0]["kind"], "admission_rejected")

    def test_a_capability_without_a_current_qualification_is_refused(self):
        self.init_and_contract()
        qual = json.loads(self.qual.read_text())
        qual["runner_sha256"] = "0" * 64
        self.qual.write_text(json.dumps(qual))
        code, out = self.admit("a1:raw", "--step", "raw", "--cost", "0")
        self.assertEqual(code, 1, out)
        self.assertIn("capability", out["reason"])

    def test_admission_computes_identity_and_rejects_by_the_rules(self):
        self.init_and_contract()
        code, out = self.admit("a1:reco", "--step", "reco", "--cost", "0")
        self.assertEqual((code, out["reason"]), (1, "missing upstream"))
        code, out = self.admit("a1:reco", "--step", "raw", "--cost", "0")
        self.assertEqual(code, 2, out)  # a rejected attempt id is never admitted later
        code, out = self.admit("a2:raw", "--step", "raw", "--cost", "nan")
        self.assertEqual(code, 1, out)
        code, out = self.admit("a3:raw", "--step", "raw", "--cost", "0", "--read", "S")
        self.assertIn("confirmation sample S may be read only by a check attempt", out["reason"])
        code, out = self.admit("a4:raw", "--step", "raw", "--cost", "0")
        self.assertEqual(code, 0, out)
        identity = out["written"][0]["fields"]["identity"]
        self.assertEqual(len(identity), 64)
        code, out = self.admit("a5:raw", "--step", "raw", "--cost", "0")
        self.assertIn("same identity", out["reason"])


class ReceiptAdapter(Base):
    """VAL-06, EXEC-02: run_workflow.py receipts become receipt / check_result facts written by the adapter."""

    def admitted_raw(self, attempt="a1:raw"):
        self.init_and_contract()
        self.assertEqual(self.admit(attempt, "--step", "raw", "--cost", "0")[0], 0)

    def test_an_unconfirmed_termination_becomes_unknown(self):
        self.admitted_raw()
        proc, work, receipt = self.run_step("a1:", "raw", ["{python}", "-c", "open('o.txt','w').write('1')"])
        doc = json.loads(receipt.read_text())
        doc["termination"] = "unconfirmed"
        receipt.write_text(json.dumps(doc))
        code, out = self.write("receipt", "--receipt", receipt, "--work", work)
        self.assertEqual(code, 0, out)
        fields = out["written"][0]["fields"]
        self.assertEqual((fields["termination"], fields["outputs"], out["written"][0]["writer"]),
                         ("unknown", [], "adapter"))
        code, st = self.call("status")
        self.assertEqual(st["attempts"][0]["state"], "unknown")
        self.assertEqual(st["pending_for_humans"][0]["kind"], "abandon or reconcile")
        code, rep = self.call("report")
        self.assertEqual((rep["overall"], rep["unsettled_attempts"]), ("partial completion", ["a1:raw"]))
        code, out = self.admit("a2:raw", "--step", "raw", "--cost", "0")
        self.assertIn("same identity already ran or is running", out["reason"])  # checked before the unknown rule
        changed = contract_json(self.check_d, self.crit_d)
        changed["steps"]["raw"]["program"] = "pRaw2"
        (self.root / "changed.json").write_text(json.dumps(changed))
        self.assertEqual(self.write("contract", "--file", self.root / "changed.json")[1]["contract_status"],
                         "effective")
        code, out = self.admit("a3:raw", "--step", "raw", "--cost", "0")
        self.assertEqual((code, out["reason"]),
                         (1, "same side effect has an unknown attempt; reconcile or abandon first"))

    def test_a_receipt_needs_an_admitted_attempt_and_a_matching_run_record(self):
        self.init_and_contract()
        proc, work, receipt = self.run_step("x1:", "raw", ["{python}", "-c", "open('o.txt','w').write('1')"])
        code, out = self.write("receipt", "--receipt", receipt, "--work", work)
        self.assertEqual(code, 2, out)
        self.assertIn("no intent written by C", out["error"])
        self.assertEqual(self.admit("x1:raw", "--step", "raw", "--cost", "0")[0], 0)
        record = work / "runs" / "raw.computational-run.json"
        record.write_text(record.read_text() + " ")
        code, out = self.write("receipt", "--receipt", receipt, "--work", work)
        self.assertEqual(code, 2, out)
        self.assertIn("run record", out["error"])

    def test_a_second_receipt_for_a_terminated_attempt_is_refused(self):
        self.admitted_raw()
        proc, work, receipt = self.run_step("a1:", "raw", ["{python}", "-c", "open('o.txt','w').write('1')"])
        self.assertEqual(self.write("receipt", "--receipt", receipt, "--work", work)[0], 0)
        code, out = self.write("receipt", "--receipt", receipt, "--work", work)
        self.assertEqual(code, 2, out)

    def test_a_step_the_runner_refused_is_a_failed_draw_with_termination_confirmed(self):
        self.admitted_raw()
        work = self.root / "work" / "refused"
        work.mkdir(parents=True)
        wf = self.root / "refused.workflow.json"
        wf.write_text(json.dumps({"workflow": "c1", "steps": [{"id": "raw", "argv": ["{python}", "-c", "pass"],
                                                                "outputs": [str(self.root / "abs.txt")]}]}))
        proc = subprocess.run([sys.executable, "-B", str(RUNNER), str(wf), "--work", str(work)], capture_output=True,
                              text=True, timeout=600)
        self.assertEqual(proc.returncode, 2)
        runner_out = self.root / "runner-out.json"
        runner_out.write_text(proc.stdout)
        code, out = self.write("receipt", "--not-started", "--attempt", "a1:raw", "--runner-output", runner_out)
        self.assertEqual(code, 0, out)
        code, st = self.call("status")
        self.assertEqual(st["attempts"][0]["state"], "failed")
        code, rep = self.call("report")
        self.assertEqual(rep["1_deliverables"]["D"]["failed_draws"], [["raw", "a1:raw", "failed"]])

    def test_usage_from_the_receipt_is_charged_and_checked_against_the_declared_cost(self):
        self.admitted_raw()
        proc, work, receipt = self.run_step("a1:", "raw", ["{python}", "-c", "open('o.txt','w').write('1')"])
        code, out = self.write("receipt", "--receipt", receipt, "--work", work, "--usage", "wall_s")
        self.assertEqual(code, 0, out)
        usage = out["written"][0]["fields"]["usage"]
        self.assertGreater(usage, 0)
        code, st = self.call("status")
        self.assertEqual(st["accounts"]["used"], usage)
        self.assertFalse(st["attempts"][0]["attested"])  # usage above the declared cost 0: not attested
        self.assertEqual(st["steps"]["raw"]["artifacts"][0]["label"], "not_usable")


class ReportShape(Base):
    def test_partial_completion_is_never_reported_as_complete(self):
        self.init_and_contract()
        code, rep = self.call("report")
        self.assertEqual(rep["overall"], "partial completion")
        self.assertEqual(rep["1_deliverables"]["D"]["state"], "not started")
        self.assertTrue(any("did NOT pass" in x for x in rep["5_limitations"]))
        out_file = self.root / "report.md"
        code, out = self.call("report", "--format", "markdown", "--out", out_file)
        self.assertEqual(code, 0, out)
        self.assertIn("partial completion", out_file.read_text())

    def test_status_of_a_record_without_an_effective_contract(self):
        self.assertEqual(self.call("init", "--mode", "M3")[0], 0)
        code, st = self.call("status")
        self.assertEqual((code, st["mode"], st["effective_contract"]), (0, "M3", False))


@unittest.skipUnless(shutil.which("true"), "POSIX host")
class Concurrency(Base):
    """Two writers deriving from the same head: compare-and-set lets exactly one append."""

    def test_only_one_of_two_writers_from_the_same_head_appends(self):
        self.init_and_contract()
        head = self.head()
        procs = [subprocess.Popen([sys.executable, "-B", str(CONTROL_CLI), "exposure", "--task-log", str(self.task_log),
                                   "--sample", sample, "--expect-head", str(head)], stdout=subprocess.PIPE, text=True)
                 for sample in ("CR", "S")]
        codes = sorted(p.wait(timeout=120) for p in procs)
        for p in procs:
            p.stdout.close()
        self.assertEqual(codes, [0, 1])
        self.assertEqual(self.head(), head + 1)


if __name__ == "__main__":
    unittest.main()
