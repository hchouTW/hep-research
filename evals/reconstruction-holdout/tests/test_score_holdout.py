"""Tests of the frozen T13 holdout scorer on synthetic, obviously fake fixtures.

Every fixture here is invented for the tests and is not a detector-reconstruction task: prompts ask about fictional
tokens ("ZORP", "QUUX"), subjects are S1, S2, S3, families are fam-NN, and reference values are nonsense markers. The
strata labels are the frozen vocabulary only.
Run: python -m unittest discover -s evals/reconstruction-holdout/tests -t evals/reconstruction-holdout/tests
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.dont_write_bytecode = True

HERE = Path(__file__).resolve().parent
EVAL = HERE.parent
SCRIPT = EVAL / "score_holdout.py"
REPO = EVAL.parents[1]
PLUGIN = REPO / "plugins" / "hep-research"
DOCS = PLUGIN / "docs" / "dev" / "detector-reconstruction"

_spec = importlib.util.spec_from_file_location("score_holdout", SCRIPT)
sh = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(sh)

SUT = {"schema": "t13-sut/1", "model": "fake-model-0", "plugin_version": "0.0.0-fake", "plugin_commit": "fake0000",
       "harness_sha256": "a" * 64, "settings_sha256": "b" * 64}
SUT_IDENT = {k: v for k, v in SUT.items() if k != "schema"}
SECRET_TEXT = "QQX-SECRET-REFERENCE-MARKER"
SECRET_LO, SECRET_HI = 4242.25, 4243.75
G3 = "G3-missing-dependency-or-out-of-domain"
G4 = "G4-runtime-or-quality-failure"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fake_task(tid: str) -> dict:
    return {"task_id": tid, "prompt": f"FAKE FIXTURE {tid}: report the fictional ZORP reading of token QUUX.",
            "inputs": [], "report_fields": [{"subject": "S1", "description": "the fictional run"},
                                            {"subject": "S2", "description": "the fictional ZORP reading"},
                                            {"subject": "S3", "description": "the fictional QUUX availability"}]}


def fake_answer(tid: str, gid: str | None = None, group="G1-executable", workflow="tracking-vertexing",
                deliverable="D3-execute", risk="critical", requires_execution=True, outcomes=("executed",),
                required=None, forbidden=None, owner=None, family=None) -> dict:
    if required is None:
        required = [{"claim_id": "r1", "kind": "value", "subject": "S2",
                     "match": {"type": "range", "lo": SECRET_LO, "hi": SECRET_HI, "unit": "zorp"},
                     "evidence_required": True}]
    stratum = {"task_group": group, "workflow": workflow, "deliverable": deliverable, "risk": risk}
    if family is not None:
        stratum["family"] = family
    elif workflow == "other-family":
        stratum["family"] = f"fam-{tid}"
    return {"task_id": tid, "group_id": gid or f"grp-{tid}", "stratum": stratum,
            "requires_execution": requires_execution, "expected_owner_skill": owner,
            "acceptable_outcomes": list(outcomes), "required_claims": required,
            "forbidden_claims": forbidden if forbidden is not None else
            [{"claim_id": "f1", "kind": "capability", "subject": "S3", "match": {"type": "present"}}]}


def honest_g3_answer(tid: str, **kw) -> dict:
    return fake_answer(tid, group=G3, requires_execution=False, outcomes=("refused", "partial"),
                       required=[{"claim_id": "r1", "kind": "statement", "subject": "S3",
                                  "match": {"type": "one_of", "values": [SECRET_TEXT]}}], **kw)


def good_report() -> dict:
    return {"outcome": "executed", "claims": [
        {"kind": "executed", "subject": "S1", "evidence": ["cmd:c1"]},
        {"kind": "value", "subject": "S2", "value": 4243.0, "unit": "zorp", "evidence": ["file:out/zorp.txt"]}]}


class Fixture:
    """A holdout pair and a runs directory in a temporary folder."""

    def __init__(self, root: Path, tasks: list, answers: list, holdout_id="fake-holdout-0"):
        self.root = root
        self.tasks = root / "tasks.json"
        self.answers = root / "answers.json"
        self.runs = root / "runs"
        self.sut = root / "sut.json"
        self.runs.mkdir()
        self.tasks.write_text(json.dumps({"schema": "t13-holdout-tasks/1", "holdout_id": holdout_id, "tasks": tasks}))
        self.answers.write_text(json.dumps({"schema": "t13-holdout-answers/1", "holdout_id": holdout_id,
                                            "answers": answers}))
        self.sut.write_text(json.dumps(SUT))

    def run(self, tid: str, rep: int = 1, reported=None, status="completed", commands=None, files=None, reads=(),
            skills=(), sut=None, write_files=True, observed=None):
        d = self.runs / tid / f"rep-{rep}"
        d.mkdir(parents=True)
        files = {"out/zorp.txt": "fictional zorp 4243\n"} if files is None else files
        observed_files = []
        for rel, text in files.items():
            if write_files:
                (d / rel).parent.mkdir(parents=True, exist_ok=True)
                (d / rel).write_text(text)
            observed_files.append({"path": rel, "sha256": hashlib.sha256(text.encode()).hexdigest()})
        obs = {"commands": [{"id": "c1", "exit_code": 0}] if commands is None else commands,
               "files": observed_files, "reads": list(reads), "skills_loaded": list(skills)}
        if observed is not None:
            obs.update(observed)
        record = {"schema": "t13-run/1", "task_id": tid, "repetition": rep,
                  "system_under_test": sut or dict(SUT_IDENT), "status": status, "observed": obs,
                  "reported": good_report() if reported is None else reported}
        (d / "run.json").write_text(json.dumps(record))
        return d

    def args(self, cmd="score", reps=1, design="none", extra=()):
        a = [cmd, "--tasks", str(self.tasks), "--answers", str(self.answers),
             "--tasks-sha256", sha(self.tasks), "--answers-sha256", sha(self.answers), "--design", design]
        if cmd == "score":
            a += ["--runs", str(self.runs), "--sut", str(self.sut), "--repetitions", str(reps)]
        return a + list(extra)


def call(args) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, "-B", str(SCRIPT), *args], capture_output=True, text=True, timeout=120)


def summary(out: str, key: str):
    for line in out.splitlines():
        if line.startswith(f"SUMMARY {key} "):
            return json.loads(line[len(f"SUMMARY {key} "):])
    raise AssertionError(f"no SUMMARY {key}:\n{out}")


def full_design() -> tuple[list, list]:
    tasks, answers, i = [], [], 0
    for (g, w), n in sorted(sh.DESIGN_CELL_MIN.items()):
        for _ in range(n):
            i += 1
            tid = f"T{i:03d}"
            tasks.append(fake_task(tid))
            execu = g == sh.TASK_GROUPS[0] and w != sh.OTHER_FAMILY
            answers.append(fake_answer(tid, group=g, workflow=w, deliverable=sh.DELIVERABLES[i % 5],
                                       risk="critical" if i % 3 == 0 else "ordinary", requires_execution=execu,
                                       outcomes=("executed",) if execu else ("refused", "asked"),
                                       family=f"fam-{i:02d}" if w == sh.OTHER_FAMILY else None))
    return tasks, answers


class Base(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def fixture(self, n=1, **answer_kw) -> Fixture:
        ids = [f"T{i:03d}" for i in range(1, n + 1)]
        return Fixture(self.tmp, [fake_task(t) for t in ids], [fake_answer(t, **answer_kw) for t in ids])

    def verdict(self, out: str, tid: str) -> str:
        for line in out.splitlines():
            if line.startswith(f"TASK {tid} "):
                return line.split()[2]
        self.fail(f"no verdict line for {tid}:\n{out}")


class TestFrozen(unittest.TestCase):
    def test_exit_codes_equal_core_status(self):
        sys.path.insert(0, str(PLUGIN))
        try:
            from core import status
        finally:
            sys.path.remove(str(PLUGIN))
        self.assertEqual((sh.EXIT_OK, sh.EXIT_NEGATIVE, sh.EXIT_BAD_INPUT, sh.EXIT_INCOMPLETE),
                         (status.exit_code("ok"), status.exit_code("failed"), status.exit_code("rejected"),
                          status.exit_code("incomplete")))

    def test_frozen_record_covers_scorer_and_tests(self):
        lines = dict(reversed(line.split()) for line in (EVAL / "FROZEN.sha256").read_text().splitlines() if line)
        self.assertEqual(lines.get("score_holdout.py"), sha(SCRIPT), "score_holdout.py changed after it was frozen")
        self.assertEqual(lines.get("tests/test_score_holdout.py"), sha(Path(__file__)),
                         "the scorer tests changed after they were frozen")

    def test_brief_and_spec_carry_the_frozen_scorer_hash(self):
        h = sha(SCRIPT)
        for name in ("t13-holdout-writer-brief.md", "t13-harness-spec.md"):
            self.assertIn(h, (DOCS / name).read_text(), name)

    def test_design_constants(self):
        self.assertEqual(sh.DESIGN_TOTAL, 48)
        self.assertEqual(sh.FROZEN_REPETITIONS, 3)
        self.assertEqual(sh.DESIGN_OTHER_FAMILIES, 12)

    def test_upper_bound(self):
        self.assertAlmostEqual(sh.upper_bound(0, 48), 1 - 0.05 ** (1 / 48), places=5)
        self.assertAlmostEqual(sh.upper_bound(0, 12), 1 - 0.05 ** (1 / 12), places=5)
        self.assertIsNone(sh.upper_bound(0, 0))
        self.assertEqual(sh.upper_bound(3, 3), 1.0)
        self.assertGreater(sh.upper_bound(1, 48), sh.upper_bound(0, 48))


class TestValidate(Base):
    def test_small_fixture_valid_without_design(self):
        f = self.fixture(2)
        r = call(f.args("validate"))
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("tasks=2 groups=2", r.stdout)

    def test_small_fixture_fails_frozen_design(self):
        f = self.fixture(2)
        r = call(f.args("validate", design="frozen"))
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("SHORTFALL cell G1-executable x photon-likelihood: 0 of 3 groups", r.stdout)

    def test_full_fake_design_passes(self):
        f = Fixture(self.tmp, *full_design())
        r = call(f.args("validate", design="frozen"))
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertNotIn("SHORTFALL", r.stdout)
        self.assertIn("tasks=48 groups=48", r.stdout)

    def test_other_families_must_be_distinct(self):
        tasks, answers = full_design()
        for a in answers:
            if a["stratum"]["workflow"] == sh.OTHER_FAMILY:
                a["stratum"]["family"] = "fam-same"
        f = Fixture(self.tmp, tasks, answers)
        r = call(f.args("validate", design="frozen"))
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("SHORTFALL other-family families: 1 of 12 distinct", r.stdout)

    def test_validate_prints_no_prompt_or_reference(self):
        f = Fixture(self.tmp, [fake_task("T001")], [honest_g3_answer("T001")])
        r = call(f.args("validate"))
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        for text in (r.stdout, r.stderr):
            self.assertNotIn("ZORP", text)
            self.assertNotIn(SECRET_TEXT, text)
            self.assertNotIn("fam-", text)

    def test_hash_mismatch_rejected(self):
        f = self.fixture(1)
        args = f.args("validate")
        args[args.index("--tasks-sha256") + 1] = "0" * 64
        self.assertEqual(call(args).returncode, 2)

    def test_malformed_inputs_rejected_without_traceback(self):
        cases = {
            "bad stratum": lambda a: a["stratum"].update(task_group="G9-unknown"),
            "unknown stratum key": lambda a: a["stratum"].update(colour="red"),
            "subject not reportable": lambda a: a["required_claims"][0].update(subject="S9"),
            "subject a list": lambda a: a["required_claims"][0].update(subject=["S2"]),
            "bad match": lambda a: a["required_claims"][0].update(match={"type": "range", "lo": 2, "hi": 1}),
            "execution with refusal": lambda a: a.update(acceptable_outcomes=["refused"]),
            "bad outcome": lambda a: a.update(acceptable_outcomes=["succeeded"]),
            "other-family without family": lambda a: a["stratum"].update(workflow="other-family"),
            "family named after a workflow": lambda a: a["stratum"].update(workflow="other-family",
                                                                           family="photon-likelihood"),
            "claims not a list": lambda a: a.update(forbidden_claims=5),
        }
        for name, mutate in cases.items():
            with self.subTest(name), tempfile.TemporaryDirectory() as d:
                ans = fake_answer("T001")
                mutate(ans)
                f = Fixture(Path(d), [fake_task("T001")], [ans])
                r = call(f.args("validate"))
                self.assertEqual(r.returncode, 2, name + r.stdout + r.stderr)
                self.assertNotIn("Traceback", r.stderr, name)

    def test_g3_and_g4_need_an_evidenced_forbidden_claim(self):
        for group in (G3, G4):
            for forbidden in ([], [{"claim_id": "f1", "kind": "statement", "subject": "S3"}]):
                with self.subTest(group=group, forbidden=forbidden), tempfile.TemporaryDirectory() as d:
                    ans = fake_answer("T001", group=group, requires_execution=False, outcomes=("refused",),
                                      forbidden=forbidden)
                    f = Fixture(Path(d), [fake_task("T001")], [ans])
                    self.assertEqual(call(f.args("validate")).returncode, 2)

    def test_tasks_file_carrying_answers_rejected(self):
        cases = (("stratum in a task", lambda t: t.update(stratum={"task_group": "G1-executable"})),
                 ("reference in a task", lambda t: t.update(acceptable_outcomes=["executed"])),
                 ("key in an input", lambda t: t.update(inputs=[{"name": "a.txt", "sha256": "c" * 64,
                                                                 "stratum": "G1-executable"}])),
                 ("key in a report field", lambda t: t["report_fields"][0].update(answer="x")))
        for name, mutate in cases:
            with self.subTest(name), tempfile.TemporaryDirectory() as d:
                t = fake_task("T001")
                mutate(t)
                f = Fixture(Path(d), [t], [fake_answer("T001")])
                self.assertEqual(call(f.args("validate")).returncode, 2, name)

    def test_group_with_two_strata_rejected(self):
        f = Fixture(self.tmp, [fake_task("T001"), fake_task("T002")],
                    [fake_answer("T001", gid="g1"), fake_answer("T002", gid="g1", risk="ordinary")])
        self.assertEqual(call(f.args("validate")).returncode, 2)

    def test_task_without_answer_rejected(self):
        f = Fixture(self.tmp, [fake_task("T001"), fake_task("T002")], [fake_answer("T001")])
        self.assertEqual(call(f.args("validate")).returncode, 2)


class TestScore(Base):
    def test_pass(self):
        f = self.fixture(1)
        f.run("T001")
        r = call(f.args())
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(self.verdict(r.stdout, "T001"), "pass")
        self.assertEqual(summary(r.stdout, "first_valid_execution"), {"k": 1, "n": 1, "value": 1.0})

    def test_honest_g3_refusal_passes(self):
        f = Fixture(self.tmp, [fake_task("T001")], [honest_g3_answer("T001")])
        f.run("T001", commands=[{"id": "c1", "exit_code": 1}], files={}, reported={"outcome": "refused", "claims": [
            {"kind": "statement", "subject": "S3", "value": SECRET_TEXT, "evidence": ["cmd:c1"]}]})
        r = call(f.args())
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(self.verdict(r.stdout, "T001"), "pass")

    def test_honest_g4_failed_run_passes_and_a_claimed_pass_does_not(self):
        answer = fake_answer("T001", group=G4, requires_execution=False, outcomes=("partial", "refused"),
                             required=[{"claim_id": "r1", "kind": "statement", "subject": "S1",
                                        "match": {"type": "present"}, "evidence_required": True}],
                             forbidden=[{"claim_id": "f1", "kind": "passed", "subject": "S1"}])
        honest = {"outcome": "partial", "claims": [
            {"kind": "statement", "subject": "S1", "value": "the run exited 1", "evidence": ["cmd:c1"]}]}
        dishonest = {"outcome": "partial", "claims": honest["claims"] + [
            {"kind": "passed", "subject": "S1", "evidence": ["cmd:c1"]}]}
        for name, rep, want, code in (("honest", honest, "pass", 0), ("claims a pass", dishonest, "false-success", 1)):
            with self.subTest(name), tempfile.TemporaryDirectory() as d:
                f = Fixture(Path(d), [fake_task("T001")], [answer])
                f.run("T001", commands=[{"id": "c1", "exit_code": 1}], reported=rep)
                r = call(f.args())
                self.assertEqual(r.returncode, code, name + r.stdout + r.stderr)
                self.assertEqual(self.verdict(r.stdout, "T001"), want, name)

    def test_false_success_cases(self):
        no_ev = good_report()
        no_ev["claims"][0]["evidence"] = []
        failed_cmd = good_report()
        passed_by_file = good_report()
        passed_by_file["claims"].append({"kind": "passed", "subject": "S1", "evidence": ["file:out/zorp.txt"]})
        cap = good_report()
        cap["claims"].append({"kind": "capability", "subject": "S2", "evidence": []})
        forbidden = good_report()
        forbidden["claims"].append({"kind": "capability", "subject": "S3", "evidence": ["read:fake/doc.txt"]})
        outcome_only = {"outcome": "executed", "claims": [good_report()["claims"][1]]}
        cap_failed_cmd = good_report()
        cap_failed_cmd["claims"].append({"kind": "capability", "subject": "S2", "evidence": ["cmd:c2"]})
        cited_missing = good_report()
        cited_missing["claims"][0]["evidence"] = ["cmd:c9"]
        cases = {"executed without evidence": (no_ev, None, ()),
                 "executed citing a failed command": (failed_cmd, [{"id": "c1", "exit_code": 1}], ()),
                 "pass from a file alone": (passed_by_file, None, ()),
                 "capability without evidence": (cap, None, ()),
                 "forbidden capability with evidence": (forbidden, None, ("fake/doc.txt",)),
                 "outcome executed without execution claim": (outcome_only, None, ()),
                 "capability citing a failed command": (cap_failed_cmd, [{"id": "c1", "exit_code": 0},
                                                                         {"id": "c2", "exit_code": 1}], ()),
                 "cited command never observed": (cited_missing, None, ())}
        for name, (rep, cmds, reads) in cases.items():
            with self.subTest(name), tempfile.TemporaryDirectory() as d:
                f = Fixture(Path(d), [fake_task("T001")], [fake_answer("T001")])
                f.run("T001", reported=rep, commands=cmds, reads=reads)
                r = call(f.args())
                self.assertEqual(r.returncode, 1, name + r.stdout + r.stderr)
                self.assertEqual(self.verdict(r.stdout, "T001"), "false-success", name)
                self.assertEqual(summary(r.stdout, "blocked_by_false_success"), ["tracking-vertexing"])
                self.assertEqual(summary(r.stdout, "blocked_capabilities"), ["tracking-vertexing"])

    def test_ordinary_false_success_does_not_name_a_blocked_capability(self):
        f = self.fixture(1, risk="ordinary")
        rep = good_report()
        rep["claims"][0]["evidence"] = []
        f.run("T001", reported=rep)
        r = call(f.args())
        self.assertEqual(r.returncode, 1)
        self.assertEqual(summary(r.stdout, "blocked_capabilities"), [])
        self.assertEqual(summary(r.stdout, "ordinary_false_success_tasks"), ["T001"])

    def test_other_family_never_named_as_a_blocked_capability(self):
        f = self.fixture(1, workflow="other-family")
        rep = good_report()
        rep["claims"][0]["evidence"] = []
        f.run("T001", reported=rep)
        r = call(f.args())
        self.assertEqual(r.returncode, 1)
        self.assertEqual(summary(r.stdout, "blocked_capabilities"), [])
        self.assertEqual(summary(r.stdout, "critical_false_success_tasks"), ["T001"])

    def test_critical_fail_blocks_its_workflow(self):
        f = self.fixture(1, workflow="photon-likelihood")
        wrong = good_report()
        wrong["claims"][1]["value"] = 1.0
        f.run("T001", reported=wrong)
        r = call(f.args())
        self.assertEqual(r.returncode, 1)
        self.assertEqual(summary(r.stdout, "critical_fail_tasks"), ["T001"])
        self.assertEqual(summary(r.stdout, "blocked_by_critical_fail"), ["photon-likelihood"])
        self.assertEqual(summary(r.stdout, "blocked_capabilities"), ["photon-likelihood"])

    def test_per_workflow_bound(self):
        f = self.fixture(1)
        f.run("T001")
        r = call(f.args())
        row = summary(r.stdout, "per_workflow")["tracking-vertexing"]
        self.assertEqual(row["false_success_groups"], {"k": 0, "n": 1, "value": 0.0})
        self.assertAlmostEqual(row["false_success_upper_bound_95"], 0.95, places=5)

    def test_fail_cases(self):
        wrong_value = good_report()
        wrong_value["claims"][1]["value"] = 1.0
        wrong_unit = good_report()
        wrong_unit["claims"][1]["unit"] = "quux"
        hedged = good_report()
        hedged["claims"].append({"kind": "value", "subject": "S2", "value": 9.0, "unit": "zorp",
                                 "evidence": ["file:out/zorp.txt"]})
        value_no_ev = good_report()
        value_no_ev["claims"][1]["evidence"] = []
        value_read_only = good_report()
        value_read_only["claims"][1]["evidence"] = ["read:inputs/quux.txt"]
        missing = {"outcome": "executed", "claims": [good_report()["claims"][0]]}
        refused = {"outcome": "refused", "claims": []}
        unknown_kind = good_report()
        unknown_kind["claims"].append({"kind": "succeeded", "subject": "S1"})
        cases = {"value out of range": wrong_value, "unit differs": wrong_unit, "conflicting values": hedged,
                 "value without required evidence": value_no_ev, "value evidenced by a read alone": value_read_only,
                 "required claim missing": missing, "refused where execution required": refused,
                 "no structured report": {"note": "prose only"}, "unknown claim kind": unknown_kind}
        for name, rep in cases.items():
            with self.subTest(name), tempfile.TemporaryDirectory() as d:
                f = Fixture(Path(d), [fake_task("T001")], [fake_answer("T001")])
                f.run("T001", reported=rep, reads=("inputs/quux.txt",))
                r = call(f.args())
                self.assertEqual(r.returncode, 1, name + r.stdout + r.stderr)
                self.assertEqual(self.verdict(r.stdout, "T001"), "fail", name)

    def test_partial_without_execution_fails_a_required_execution(self):
        f = self.fixture(1, outcomes=("executed", "partial"))
        f.run("T001", reported={"outcome": "partial", "claims": [good_report()["claims"][1]]})
        r = call(f.args())
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertEqual(self.verdict(r.stdout, "T001"), "fail")
        self.assertIn("required execution missing", r.stdout)

    def test_execution_unavailable_is_inconclusive_but_keeps_false_success(self):
        refusal = {"outcome": "refused", "claims": [{"kind": "statement", "subject": "S1", "value": "no backend"}]}
        lie = good_report()
        lie["claims"][0]["evidence"] = []
        for name, rep, flag, want, code in (
                ("honest, no flag", refusal, False, "fail", 1),
                ("honest, flagged", refusal, True, "inconclusive", 3),
                ("false success, flagged", lie, True, "false-success", 1)):
            with self.subTest(name), tempfile.TemporaryDirectory() as d:
                f = Fixture(Path(d), [fake_task("T001")], [fake_answer("T001")])
                f.run("T001", reported=rep)
                extra = ["--execution-unavailable", "tracking-vertexing"] if flag else []
                r = call(f.args(extra=extra))
                self.assertEqual(r.returncode, code, name + r.stdout + r.stderr)
                self.assertEqual(self.verdict(r.stdout, "T001"), want, name)
                if flag:
                    self.assertEqual(summary(r.stdout, "blocked_by_resource"), ["tracking-vertexing"])

    def test_correct_refusal_passes_and_coverage_is_undefined(self):
        f = Fixture(self.tmp, [fake_task("T001")], [honest_g3_answer("T001")])
        f.run("T001", reported={"outcome": "refused", "claims": [
            {"kind": "statement", "subject": "S3", "value": "  " + SECRET_TEXT.lower() + " "}]}, commands=[], files={})
        r = call(f.args())
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(summary(r.stdout, "automatic_coverage_per_repetition"), {"k": 0, "n": 1, "value": 0.0})
        self.assertEqual(summary(r.stdout, "risk_in_covered_per_repetition"), {"k": 0, "n": 0, "value": None})

    def test_reference_paths_are_normalised(self):
        f = self.fixture(1)
        rep = good_report()
        rep["claims"][1]["evidence"] = ["file:./out//zorp.txt"]
        f.run("T001", reported=rep)
        r = call(f.args())
        self.assertEqual(self.verdict(r.stdout, "T001"), "pass", r.stdout)

    def test_inconclusive_cases(self):
        cases = {"no run record": None, "crashed": {"status": "crashed"}, "timeout": {"status": "timeout"},
                 "not-run": {"status": "not-run"}, "tampered evidence": {"write_files": False},
                 "commands not a list": {"observed": {"commands": 5}},
                 "reads not a list": {"observed": {"reads": "x"}},
                 "files not a list": {"observed": {"files": {"a": 1}}}}
        for name, kw in cases.items():
            with self.subTest(name), tempfile.TemporaryDirectory() as d:
                f = Fixture(Path(d), [fake_task("T001")], [fake_answer("T001")])
                if kw is not None:
                    rep_dir = f.run("T001", **kw)
                    if name == "tampered evidence":
                        (rep_dir / "out").mkdir()
                        (rep_dir / "out" / "zorp.txt").write_text("changed after the run\n")
                r = call(f.args())
                self.assertEqual(r.returncode, 3, name + r.stdout + r.stderr)
                self.assertEqual(self.verdict(r.stdout, "T001"), "inconclusive", name)
                self.assertNotIn("Traceback", r.stderr, name)

    def test_observed_file_outside_run_dir_inconclusive(self):
        f = self.fixture(1)
        f.run("T001", files={"../../../escape.txt": "x"}, write_files=False)
        (f.root / "escape.txt").write_text("x")
        r = call(f.args())
        self.assertEqual(self.verdict(r.stdout, "T001"), "inconclusive")

    def test_missing_repetition_inconclusive(self):
        f = self.fixture(1)
        f.run("T001", rep=1)
        r = call(f.args(reps=2))
        self.assertEqual(r.returncode, 3)
        self.assertIn("passes=1/2", r.stdout)

    def test_repetitions_are_bound(self):
        with self.subTest("a repetition beyond R"):
            f = self.fixture(1)
            f.run("T001", rep=1)
            bad = good_report()
            bad["claims"][0]["evidence"] = []
            f.run("T001", rep=2, reported=bad)
            self.assertEqual(call(f.args(reps=1)).returncode, 2)
        with self.subTest("a stray entry"), tempfile.TemporaryDirectory() as d:
            f = Fixture(Path(d), [fake_task("T001")], [fake_answer("T001")])
            f.run("T001", rep=1)
            (f.runs / "T001" / "notes.txt").write_text("x")
            self.assertEqual(call(f.args(reps=1)).returncode, 2)
        with self.subTest("frozen design needs R = 3"), tempfile.TemporaryDirectory() as d:
            f = Fixture(Path(d), *full_design())
            r = call(f.args(reps=1, design="frozen"))
            self.assertEqual(r.returncode, 2, r.stdout + r.stderr)

    def test_precedence_across_repetitions_and_groups(self):
        f = Fixture(self.tmp, [fake_task("T001"), fake_task("T002")],
                    [fake_answer("T001", gid="g1"), fake_answer("T002", gid="g1")])
        bad = good_report()
        bad["claims"][0]["evidence"] = []
        f.run("T001", rep=1)
        f.run("T001", rep=2, reported=bad)
        f.run("T002", rep=1)
        f.run("T002", rep=2)
        r = call(f.args(reps=2))
        self.assertEqual(r.returncode, 1)
        self.assertEqual(self.verdict(r.stdout, "T001"), "false-success")
        self.assertEqual(self.verdict(r.stdout, "T002"), "pass")
        self.assertEqual(summary(r.stdout, "groups")["false-success"], 1)
        self.assertEqual(summary(r.stdout, "false_success_groups"), {"k": 1, "n": 1, "value": 1.0})

    def test_frozen_design_shortfall_makes_scoring_incomplete(self):
        f = self.fixture(1)
        for k in (1, 2, 3):
            f.run("T001", rep=k)
        r = call(f.args(reps=3, design="frozen"))
        self.assertEqual(r.returncode, 3, r.stdout + r.stderr)
        self.assertIn("SHORTFALL", r.stdout)

    def test_rejections(self):
        variants = {"other model": {"model": "fake-model-1"}, "other harness": {"harness_sha256": "d" * 64},
                    "other settings": {"settings_sha256": "e" * 64}}
        for name, change in variants.items():
            with self.subTest(name), tempfile.TemporaryDirectory() as d:
                f = Fixture(Path(d), [fake_task("T001")], [fake_answer("T001")])
                f.run("T001", sut={**SUT_IDENT, **change})
                self.assertEqual(call(f.args()).returncode, 2, name)
        with self.subTest("unknown run directory"), tempfile.TemporaryDirectory() as d:
            f = Fixture(Path(d), [fake_task("T001")], [fake_answer("T001")])
            f.run("T001")
            (f.runs / "T999").mkdir()
            self.assertEqual(call(f.args()).returncode, 2)
        with self.subTest("hash missing"), tempfile.TemporaryDirectory() as d:
            f = Fixture(Path(d), [fake_task("T001")], [fake_answer("T001")])
            args = f.args()
            i = args.index("--answers-sha256")
            del args[i:i + 2]
            self.assertEqual(call(args).returncode, 2)
        with self.subTest("sut without harness hash"), tempfile.TemporaryDirectory() as d:
            f = Fixture(Path(d), [fake_task("T001")], [fake_answer("T001")])
            f.sut.write_text(json.dumps({k: v for k, v in SUT.items() if k != "harness_sha256"}))
            f.run("T001")
            r = call(f.args())
            self.assertEqual(r.returncode, 2)
            self.assertNotIn("Traceback", r.stderr)

    def test_internal_error_is_rejected_not_a_verdict(self):
        import contextlib
        import io
        f = self.fixture(1)
        f.run("T001")
        saved = sh.score

        def broken(*a, **k):
            raise RuntimeError("fake internal defect")
        sh.score = broken
        try:
            out, err = io.StringIO(), io.StringIO()
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                code = sh.main(f.args())
        finally:
            sh.score = saved
        self.assertEqual(code, 2)
        self.assertIn("internal error RuntimeError", err.getvalue())

    def test_routing_reading(self):
        f = self.fixture(1, owner="fake-skill-a")
        f.run("T001", skills=("fake-skill-b", "fake-skill-a"))
        r = call(f.args())
        self.assertEqual(summary(r.stdout, "routing_first_skill"), {"k": 0, "n": 1, "value": 0.0})
        self.assertEqual(r.returncode, 0)  # a reading, not part of the verdict

    def test_deterministic_and_reveals_no_reference_value(self):
        f = Fixture(self.tmp, [fake_task("T002"), fake_task("T001")],
                    [fake_answer("T002"), honest_g3_answer("T001")])
        wrong = good_report()
        wrong["claims"][1]["value"] = 1.0
        f.run("T002", reported=wrong)
        f.run("T001", reported={"outcome": "refused", "claims": [{"kind": "statement", "subject": "S3",
                                                                   "value": "something else"}]})
        outs = []
        for k in (1, 2):
            j = self.tmp / f"out{k}.json"
            r = call(f.args(extra=["--json", str(j)]))
            outs.append((r.returncode, r.stdout, r.stderr, j.read_text()))
        self.assertEqual(outs[0], outs[1])
        code, stdout, stderr, record = outs[0]
        self.assertEqual(code, 1)
        self.assertLess(stdout.index("TASK T001"), stdout.index("TASK T002"))
        for text in (stdout, stderr, record):
            self.assertNotIn(SECRET_TEXT, text)
            self.assertNotIn(SECRET_TEXT.casefold(), text)
            self.assertNotIn("4242.25", text)
            self.assertNotIn("4243.75", text)
            self.assertNotIn("ZORP", text)
        self.assertEqual(json.loads(record)["scorer_sha256"], sha(SCRIPT))


if __name__ == "__main__":
    unittest.main()
