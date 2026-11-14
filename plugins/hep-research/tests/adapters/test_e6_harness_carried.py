"""The evaluation harness defects carried from attempt 1 on block 11 (fix/harness-carried; the user, 2026-11-13: "do your recommendation").

From finish-plan/e6-result-lines-audit.md and jobs/evaluation-t08rerun/REVIEW.md:
(2) the single-photon refusal check of a T09 range task requires the main reader's own "rejected" status line, as the Freeze-B run's
    t09-ms.sh did, never any exit 2;
(3) a "status": "error" result line (photon_likelihood.py's and t09_truth_start.py's catch-alls, exit 2: an unexpected exception, an
    ImportError or a ModuleNotFoundError inside an operation) is a crash of the task (incomplete), never a negative result. The recipe files
    are frozen (Freeze B) and unchanged: the harness's classification reads the line;
(4) every RESULT_LINES entry names a script in this tree and matches at least one verdict line that script really prints, collected
    statically from its source (no hand-written example), and the REJECTED lines of t07_fake_rate.py run are read as its refusal, not a crash;
(I3) the T07 checks and T07 negative-cases tasks write the milestone draws-started before anything is read, so a failed check (exit 1 or 2)
    is NOT-REPEATABLE and stands, while a harness crash (exit 3) stays REPEATABLE under the user's ruling (2026-11-13, "Count it: block 1/6
    only").

Hand-made inputs and fake scripts only (as test_t04_evaluation_tasks); no fixture is drawn, no recipe runs, no Slurm job is submitted.
Run from the plugin root: python -m unittest tests.adapters.test_e6_harness_carried -v
"""
from __future__ import annotations

import ast
import functools
import hashlib
import io
import itertools
import json
import os
import re
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from tests.adapters import t04_evaluation_layout as layout  # noqa: E402
from tests.adapters import t04_evaluation_tasks as tasks  # noqa: E402
from tests.adapters import t07_evaluation_scoring as scoring  # noqa: E402

TEMPORARY_ROOT = os.environ.get("TMPDIR") or None
LIGHT = ROOT / "adapters" / "photon-likelihood" / "assets"

# A photon_likelihood.py stand-in: FAKE_MAIN_REFUSAL sets the status the main reader prints (exit 2) for the single-photon product; FAKE_ERROR
# names an operation that ends in the real catch-all's line ("status": "error", exit 2).
FAKE_LIKE = r'''
import json, os, sys
from pathlib import Path
args = sys.argv[1:]
def value(flag):
    return args[args.index(flag) + 1] if flag in args else None
if value("--product") and args[0] in ("fit", "topology"):
    Path(value("--product")).write_text("{}\n")
if os.environ.get("FAKE_ERROR") == args[0]:
    print(json.dumps({"exit_code": 2, "operation": args[0], "reason": "unexpected ModuleNotFoundError: No module named 'light_recipe'",
                      "status": "error"}, sort_keys=True)); sys.exit(2)
if args[0] == "check-product" and "--configuration" not in args and "single-photon" in (value("--product") or ""):
    print(json.dumps({"exit_code": 2, "operation": "check-product",
                      "reason": os.environ.get("FAKE_MAIN_REASON", "the product was made with another configuration than the one given"),
                      "status": os.environ.get("FAKE_MAIN_REFUSAL", "rejected")}, sort_keys=True)); sys.exit(2)
print(json.dumps({"exit_code": 0, "operation": args[0], "reason": "", "status": "ok"}, sort_keys=True))
'''

FAKE_TRUTH_START = r'''
import json, os, sys
from pathlib import Path
args = sys.argv[1:]
if os.environ.get("FAKE_TRUTH_ERROR"):
    print("ERROR truth-start: unexpected ModuleNotFoundError: No module named 'light_recipe'")
    print("RESULT " + json.dumps({"exit_code": 2, "operation": "fit", "reason": "unexpected ModuleNotFoundError", "status": "error"}, sort_keys=True))
    sys.exit(2)
Path(args[args.index("--out") + 1]).write_text("{}\n")
print("RESULT " + json.dumps({"exit_code": 0, "operation": "fit", "reason": "", "status": "ok"}, sort_keys=True))
'''


def sha(path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def run_main(argv) -> tuple:
    stream = io.StringIO()
    with redirect_stdout(stream):
        code = tasks.main([str(a) for a in argv])
    return code, stream.getvalue()


class RangeTask(unittest.TestCase):
    """A T09 range task of fixture 9001 in stratum T09_E1B_STRATUM (the one that runs the single-photon refusal), on hand-made range files."""

    def setUp(self):
        self.folder = tempfile.TemporaryDirectory(dir=TEMPORARY_ROOT)
        base = Path(self.folder.name)
        self.light = base / "light"
        (self.light / "fixture_tools").mkdir(parents=True)
        (self.light / "photon_likelihood.py").write_text(FAKE_LIKE)
        (self.light / "fixture_tools" / "t09_truth_start.py").write_text(FAKE_TRUTH_START)
        self.index = next(i for i, (fixture, stratum, _) in enumerate(tasks.T09_SAMPLES) if (fixture, stratum) == (9001, tasks.T09_E1B_STRATUM))
        fixture_id, stratum, label = tasks.T09_SAMPLES[self.index]
        self.generation = base / "generation"
        (self.generation / "ranges").mkdir(parents=True)
        ranges = []
        for span in tasks.T09_RANGES:
            files = tasks.t09_range_files(self.generation, span.first)
            files["readout"].write_bytes(f"readout {span.first}".encode())
            files["truth"].write_bytes(f"truth {span.first}".encode())
            ranges.append({"first": span.first, "count": span.count, "readout_sha256": sha(files["readout"]), "truth_sha256": sha(files["truth"])})
        (self.generation / "generation.json").write_text(json.dumps({"workflow": "T09", "fixture_id": fixture_id, "block": 11, "stratum": stratum,
                                                                     "label": label, "stratum_sha256": "f" * 64, "truth_sha256": "e" * 64,
                                                                     "ranges": ranges, "attempt": "1_0"}))
        self.out = base / "range-0"
        for name in ("FAKE_MAIN_REFUSAL", "FAKE_MAIN_REASON", "FAKE_ERROR", "FAKE_TRUTH_ERROR"):
            self.addCleanup(os.environ.pop, name, None)

    def tearDown(self):
        self.folder.cleanup()

    def run_task(self):
        return run_main(["t09-range", "--block", 11, "--index", self.index, "--range", 0, "--generation", self.generation, "--out", self.out,
                         "--light-assets", self.light])


class SinglePhotonRefusal(RangeTask):
    """(2) The main reader must refuse the single-photon product with its own "rejected" status line (the Freeze-B run's t09-ms.sh)."""

    def test_the_main_readers_rejected_line_passes(self):
        code, text = self.run_task()
        self.assertEqual(code, 0, text)
        self.assertTrue((self.out / "records" / "single-photon.json").exists())

    def test_an_exit_2_with_another_status_is_not_the_refusal(self):
        os.environ["FAKE_MAIN_REFUSAL"] = "refused"     # exit 2 with a line that matches the result pattern, but not "rejected"
        code, text = self.run_task()
        self.assertEqual(code, 1, text)
        self.assertIn("RESULT t09-range failed", text)
        self.assertIn("the main reader did not refuse the single-photon product", text)
        self.assertFalse((self.out / "records" / "single-photon.json").exists())

    def test_a_rejected_line_for_another_reason_is_not_the_refusal(self):
        """Review m1: the refusal is the one light_recipe/product.py:417 gives (the product of another configuration), not any rejection
        (no such input file, a product that does not read)."""
        os.environ["FAKE_MAIN_REASON"] = "no such input file: x"
        code, text = self.run_task()
        self.assertEqual(code, 1, text)
        self.assertIn("the main reader did not refuse the single-photon product", text)

    def test_the_catch_alls_error_is_never_the_refusal(self):
        os.environ["FAKE_MAIN_REFUSAL"] = "error"       # the catch-all of photon_likelihood.py:282 (exit 2): a crash, never a pass
        code, text = self.run_task()
        self.assertEqual(code, 3, text)
        self.assertIn("RESULT t09-range crashed", text)
        self.assertFalse((self.out / "records" / "single-photon.json").exists())


class ErrorStatusIsACrash(RangeTask):
    """(3) A "status": "error" line (exit 2) is a crash of the task, never a negative result: classify_script_run, then the range task."""

    def real_report_line(self, status: str) -> str:
        """photon_likelihood.report's own line, by the frozen function (imported without writing bytecode)."""
        import importlib
        saved = sys.dont_write_bytecode
        sys.dont_write_bytecode = True
        try:
            sys.path.insert(0, str(LIGHT))
            module = importlib.import_module("photon_likelihood")
        finally:
            sys.path.remove(str(LIGHT))
            sys.dont_write_bytecode = saved
        stream = io.StringIO()
        with redirect_stdout(stream):
            code = module.report("fit", status, "unexpected ModuleNotFoundError: No module named 'light_recipe'")
        self.assertEqual(code, 2)
        return stream.getvalue()

    def test_the_real_catch_all_line_is_a_crash(self):
        line = self.real_report_line("error")
        self.assertEqual(layout.classify_script_run(2, line, layout.RESULT_LINES["photon_likelihood.py"]),
                         ("crashed", 'the script\'s own status "error" (an unexpected exception: a crash, never a negative)'))

    def test_a_rejected_line_stays_negative(self):
        line = self.real_report_line("rejected")
        self.assertEqual(layout.classify_script_run(2, line, layout.RESULT_LINES["photon_likelihood.py"])[0], "negative")

    def test_the_truth_start_error_line_is_a_crash(self):
        text = 'ERROR truth-start: unexpected ImportError\nRESULT {"exit_code": 2, "operation": "fit", "reason": "x", "status": "error"}\n'
        self.assertEqual(layout.classify_script_run(2, text, layout.RESULT_LINES["t09_truth_start.py"])[0], "crashed")
        text = 'REFUSED truth-start: no such file\nRESULT {"exit_code": 2, "operation": "fit", "reason": "x", "status": "rejected"}\n'
        self.assertEqual(layout.classify_script_run(2, text, layout.RESULT_LINES["t09_truth_start.py"])[0], "negative")

    def test_a_fit_ending_in_error_crashes_the_range_task(self):
        os.environ["FAKE_ERROR"] = "fit"
        code, text = self.run_task()
        self.assertEqual(code, 3, text)
        self.assertIn("RESULT t09-range crashed", text)
        self.assertFalse((self.out / "stop.json").exists())

    def test_a_truth_start_ending_in_error_crashes_the_range_task(self):
        os.environ["FAKE_TRUTH_ERROR"] = "1"
        code, text = self.run_task()
        self.assertEqual(code, 3, text)
        self.assertIn("RESULT t09-range crashed", text)


# ---- (4) The verdict lines each script prints, collected statically from its source.

PLACEHOLDER = "x"
LIMIT = 4096


class _Lines:
    """Renders the lines a Python script prints from its AST: every string or f-string printed (print, say, write), appended or listed (the
    lines t08_cai.py and others print with "\\n".join), and each call of the script's own printing functions (report, result_line, _result,
    say) with its call site's arguments. An f-string's value is rendered from what the source fixes: a constant, both branches of a
    conditional, a module constant or the values of a module dict, a lambda's or a function's constant returns; anything else is "x"."""

    PRINTERS = ("print", "say", "write", "append")

    def __init__(self, path: Path):
        self.tree = ast.parse(path.read_text(encoding="utf-8"))
        self.constants, self.functions = {}, {}
        for node in ast.walk(self.tree):
            if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
                self.constants.setdefault(node.targets[0].id, node.value)
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                self.functions.setdefault(node.name, node)

    def render(self, node, env, depth=0) -> list:
        if depth > 6:
            return [PLACEHOLDER]
        if isinstance(node, ast.Constant):
            return [node.value if isinstance(node.value, str) else str(node.value)]
        if isinstance(node, ast.JoinedStr):
            parts = [self.render(v.value, env, depth + 1) if isinstance(v, ast.FormattedValue) else [v.value] for v in node.values]
            return ["".join(p) for p in itertools.islice(itertools.product(*parts), LIMIT)]
        if isinstance(node, ast.IfExp):
            return self.render(node.body, env, depth + 1) + self.render(node.orelse, env, depth + 1)
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
            return [a + b for a, b in itertools.islice(itertools.product(self.render(node.left, env, depth + 1), self.render(node.right, env, depth + 1)), LIMIT)]
        if isinstance(node, ast.Name):
            if node.id in env:
                return env[node.id]
            value = self.constants.get(node.id)
            if isinstance(value, (ast.Constant, ast.JoinedStr)):
                return self.render(value, env, depth + 1)
            return [PLACEHOLDER]
        if isinstance(node, ast.Subscript) and isinstance(node.value, ast.Name):
            value = self.constants.get(node.value.id)
            if isinstance(value, ast.Dict):
                return [r for v in value.values for r in self.render(v, {}, depth + 1)]
            return [PLACEHOLDER]
        if isinstance(node, ast.Call):
            name = node.func.id if isinstance(node.func, ast.Name) else (node.func.attr if isinstance(node.func, ast.Attribute) else None)
            if name == "dumps" and node.args and isinstance(node.args[0], ast.Dict):
                return self.render_json(node, env, depth)
            lam = self.constants.get(name)
            if isinstance(lam, ast.Lambda):
                return self.render(lam.body, {}, depth + 1)
            function = self.functions.get(name)
            if function is not None:
                returns = [n.value for n in ast.walk(function) if isinstance(n, ast.Return) and n.value is not None]
                if returns and all(isinstance(r, (ast.Constant, ast.IfExp)) for r in returns):
                    return [x for r in returns for x in self.render(r, {}, depth + 1)]
        return [PLACEHOLDER]

    def render_json(self, call, env, depth) -> list:
        keys, choices = [], []
        for key, value in zip(call.args[0].keys, call.args[0].values):
            if key is None or not isinstance(key, ast.Constant):     # **fields: its keys are not fixed by the source
                continue
            keys.append(key.value)
            choices.append(self.render(value, env, depth + 1))
        sort_keys = any(k.arg == "sort_keys" and isinstance(k.value, ast.Constant) and k.value.value for k in call.keywords)
        return [json.dumps(dict(zip(keys, combo)), sort_keys=sort_keys) for combo in itertools.islice(itertools.product(*choices), LIMIT)]

    def printing_functions(self) -> dict:
        """The script's own functions that print one of their parameters' renderings: name -> (parameter names, printed expressions)."""
        found = {}
        for name, function in self.functions.items():
            parameters = [a.arg for a in function.args.args]
            printed = [c.args[0] for c in ast.walk(function) if isinstance(c, ast.Call) and isinstance(c.func, ast.Name) and c.func.id == "print"
                       and c.args and any(isinstance(n, ast.Name) and n.id in parameters for n in ast.walk(c.args[0]))]
            if printed:
                found[name] = (parameters, printed)
        return found

    def lines(self) -> set:
        found = set()
        wrappers = self.printing_functions()
        for node in ast.walk(self.tree):
            if isinstance(node, ast.List):
                for element in node.elts:
                    if isinstance(element, (ast.Constant, ast.JoinedStr)):
                        found.update(r for r in self.render(element, {}) if isinstance(r, str))
            if not isinstance(node, ast.Call):
                continue
            name = node.func.id if isinstance(node.func, ast.Name) else (node.func.attr if isinstance(node.func, ast.Attribute) else None)
            if name in self.PRINTERS and node.args:
                found.update(self.render(node.args[0], {}))
            if name in wrappers:
                parameters, printed = wrappers[name]
                env = {p: [PLACEHOLDER] for p in parameters}
                for parameter, argument in zip(parameters, node.args):
                    env[parameter] = self.render(argument, {})
                for keyword in node.keywords:
                    if keyword.arg in env:
                        env[keyword.arg] = self.render(keyword.value, {})
                for expression in printed:
                    found.update(self.render(expression, env))
        return {line for text in found for line in text.splitlines()}


def script_of(key: str) -> Path:
    name = key.split()[0]
    found = [p for p in ROOT.rglob(name) if ".git" not in p.parts]
    if len(found) != 1:
        raise AssertionError(f"RESULT_LINES[{key!r}]: {len(found)} scripts named {name} in the plugin tree, not one")
    return found[0]


# The 268e5bd4 entry of t08_cai.py rereco (block-11 job 7613402 read its real verdict line as a crash): its only match in the script's
# source is the refusal line "REFUSED <label> <operation>: ...", so a check that asks for "a match" alone passes it (harness review I4).
RERECO_ENTRY_OF_ATTEMPT_1 = r"^(CAI-T08-2 .* RESULT (PASS|FAIL|RECORDED)|GATE |REFUSED )"
NOT_A_VERDICT = ("REFUSED ", "REJECTED ", "ERROR ")
NOT_A_VERDICT_STATUSES = ("rejected", "error", "missing-dependency")


def verdict_lines(key: str, pattern: str) -> list:
    """The lines of the key's script, collected from its source, that the pattern matches and that are a verdict of a run that ran: neither a
    refusal nor an error (no REFUSED, REJECTED or ERROR line; no JSON status rejected, error or missing-dependency)."""
    return sorted(line for line in _Lines(script_of(key)).lines() if re.search(pattern, line) and not line.startswith(NOT_A_VERDICT)
                  and layout.result_status(line) not in NOT_A_VERDICT_STATUSES)


class ResultLinesAreTheScriptsOwn(unittest.TestCase):
    def test_every_entry_matches_a_verdict_line_its_script_prints(self):
        """No hand-written example: each pattern is tried on the lines collected from its script's own source, and must match one that is
        the verdict of a run that ran, not a refusal or an error (harness review I4)."""
        for key, pattern in layout.RESULT_LINES.items():
            with self.subTest(key=key):
                self.assertTrue(verdict_lines(key, pattern), f"RESULT_LINES[{key!r}] matches no verdict line {script_of(key).name} prints")

    def test_the_attempt_1_rereco_entry_is_refused(self):
        """Review I4: the defective entry of attempt 1 matched only the refusal line; the check refuses it, and passes the current one."""
        lines = _Lines(script_of("t08_cai.py")).lines()
        self.assertTrue([line for line in lines if re.search(RERECO_ENTRY_OF_ATTEMPT_1, line)])        # "a match" alone would have passed it
        self.assertEqual(verdict_lines("t08_cai.py rereco", RERECO_ENTRY_OF_ATTEMPT_1), [])
        self.assertIn("CAI-T08-2 x RECORD recorded without a numeric assertion (R37)", verdict_lines("t08_cai.py rereco", layout.RESULT_LINES["t08_cai.py rereco"]))

    def test_the_collector_sees_the_rereco_verdict_and_not_the_invented_one(self):
        lines = _Lines(script_of("t08_cai.py")).lines()
        self.assertIn("CAI-T08-2 x RECORD recorded without a numeric assertion (R37)", lines)
        self.assertFalse([line for line in lines if re.search(r"CAI-T08-2 .* RESULT RECORDED", line)])

    def test_the_collector_renders_the_json_reporters(self):
        lines = _Lines(LIGHT / "photon_likelihood.py").lines()
        self.assertIn('{"exit_code": "x", "operation": "x", "reason": "unexpected x: x", "status": "error"}', lines)    # the catch-all, :282
        lines = _Lines(LIGHT / "fixture_tools" / "t09_truth_start.py").lines()
        self.assertIn('RESULT {"exit_code": "x", "operation": "x", "reason": "unexpected x: x", "status": "error"}', lines)

    def test_every_rejected_line_is_read_as_its_scripts_refusal(self):
        """Audit finding 4: a script's REJECTED line (exit 2) matches its entry, so a refused input reads negative, never crashed. A script
        that ends a refusal with its own matched "rejected" result line after the REJECTED line (t04_evaluation_tasks.py main: "REJECTED op:
        ..." then "RESULT op rejected") is judged by that line."""
        for key, pattern in layout.RESULT_LINES.items():
            lines = _Lines(script_of(key)).lines()
            if any(re.search(pattern, line) and re.search(r"\brejected\b", line) for line in lines):
                continue
            rejected = sorted(line for line in lines if line.startswith("REJECTED "))
            if key.split()[0] == "t07_fake_rate.py":
                self.assertTrue(rejected)
            for line in rejected:
                with self.subTest(key=key, line=line):
                    self.assertEqual(layout.classify_script_run(2, line + "\n", pattern), ("negative", line))

    def test_no_entry_for_a_script_outside_the_tree(self):
        """Audit finding 4: fbrun_tools.py (jobs/freeze-b-run) and check_generators.py (the frozen generators) are not in the tree and no
        run_script call starts them; their entries are removed rather than kept untested."""
        for key in layout.RESULT_LINES:
            with self.subTest(key=key):
                script_of(key)
        self.assertFalse([k for k in layout.RESULT_LINES if k.split()[0] in ("fbrun_tools.py", "check_generators.py")])


class IOFailureIsACrash(unittest.TestCase):
    """Harness review m2 (the coordinator: as I1, harness side only): a product the recipe could not write (photon_likelihood.py :158-160,
    :256-258 and calo_cluster.py :102 report it "rejected", exit 2: an OSError such as ENOSPC or EIO) is a crash, never a refusal."""

    def test_a_product_that_cannot_be_written_is_a_crash(self):
        line = '{"exit_code": 2, "operation": "fit", "reason": "product cannot be written: No space left on device", "status": "rejected"}'
        for key in ("photon_likelihood.py", "calo_cluster.py"):
            with self.subTest(key=key):
                self.assertEqual(layout.classify_script_run(2, line + "\n", layout.RESULT_LINES[key])[0], "crashed")
        line = '{"exit_code": 2, "operation": "fit", "reason": "no such input file: readout x", "status": "rejected"}'
        self.assertEqual(layout.classify_script_run(2, line + "\n", layout.RESULT_LINES["photon_likelihood.py"])[0], "negative")


# ---- (I3) The T07 check tasks' milestones; harness review I1 to I3.

FAKE_FINDER_KILLED = "#!/bin/sh\nkill -9 $$\n"                  # the frozen finder killed by a signal (SIGKILL: an OOM kill, a node fault)
FAKE_FINDER_EXIT_1 = "#!/bin/sh\necho 'a recipe failure' >&2\nexit 1\n"
FAKE_FINDER_TRUNCATED = "#!/bin/sh\nfor a in \"$@\"; do case \"$prev\" in --record-file|--record) printf 'acts-finding-record/1\\n{\"head' > \"$a\";; esac; prev=$a; done\nexit 0\n"


class T07CheckTasks(unittest.TestCase):
    """The T07 checks and T07 negative-cases tasks through their real commands (t07_evaluation_scoring main, the runner's main): draws-started
    before anything is read; a failed check is counted and yields the T07 fail; a crash of the harness or of the node is repeatable."""

    PASS = "Ran 3 tests in 0.1s\n\nOK\n"
    FAIL = "FAIL: test_x\nTraceback (most recent call last):\nAssertionError\nRan 3 tests in 0.1s\n\nFAILED (failures=1)\n"
    CRASH = "Traceback (most recent call last):\nKilled\n"
    KILLED = ("FAIL: test_finder\nTraceback (most recent call last):\nAssertionError: acts_tracking_finder exit -9: \nRan 3 tests in 0.1s\n\n"
              "FAILED (failures=1)\n")

    def setUp(self):
        self.base = Path(tempfile.mkdtemp(dir=TEMPORARY_ROOT, prefix="t07-marks-"))
        self.addCleanup(__import__("shutil").rmtree, self.base, True)

    def checks(self, out: Path, text_of) -> tuple:
        """The checks-task command with the real checks_task, each module's output given (no module runs)."""
        return checks_attempt(self.base, out, text_of)

    def verdict(self, out: Path, code: int, state=None) -> str:
        state = state or ("COMPLETED" if code == 0 else "FAILED")
        return layout.classify_attempt(state, code, "00:05:00", tasks.Milestones(out).names() if tasks.Milestones(out).path.exists() else None)[0]

    def test_the_checks_task_marks_draws_started_before_its_first_module(self):
        code, text, seen = self.checks(self.base / "pass", lambda m: self.PASS)
        self.assertEqual(code, 0, text)
        self.assertEqual(seen[0], [layout.EVENTS_ENTERED[0]])

    def test_a_failed_t07_check_is_counted_never_repeated(self):
        """Review I3: the failed attempt (exit 1, its checks file complete) is the counted one, so its fail reaches the summary; a later
        rerun that passes is never counted over it."""
        failed = self.base / "failed"
        code, text, _ = self.checks(failed, lambda m: self.FAIL if m.endswith("test_acts_finding") else self.PASS)
        self.assertEqual(code, 1, text)
        (failed / "t07-checks.log").write_text(text + "RESULT t07-checks failed\n")
        self.assertEqual(self.verdict(failed, code), "NOT-REPEATABLE")
        rerun = self.base / "rerun"
        self.assertEqual(self.checks(rerun, lambda m: self.PASS)[0], 0)
        (rerun / "t07-checks.log").write_text("RESULT t07-checks ok\n")
        states = {"901": ("FAILED", 1, "00:05:00"), "902": ("COMPLETED", 0, "00:05:00")}
        with redirect_stdout(io.StringIO()) as printed:
            found = tasks.counted_single({"T07 checks": [("901", failed), ("902", rerun)]}, "T07 checks", 11, states.get,
                                         standing=("t07-checks", "deterministic-checks.json"))
        self.assertEqual(found, failed)
        self.assertIn("CLASSIFY T07 checks attempt 1 (902): after the standing failure of attempt 0 (901), not counted", printed.getvalue())

    def test_a_failed_check_with_no_checks_file_is_not_a_standing_failure(self):
        failed = self.base / "failed"
        failed.mkdir()
        (failed / "milestones.txt").write_text("draws-started 2026-11-13T00:00:00Z\n")
        (failed / "t07-checks.log").write_text("RESULT t07-checks failed\n")
        with self.assertRaises(tasks.Incomplete):
            tasks.counted_single({"T07 checks": [("901", failed)]}, "T07 checks", 11, {"901": ("FAILED", 1, "00:05:00")}.get,
                                 standing=("t07-checks", "deterministic-checks.json"))

    def test_a_harness_crash_of_the_checks_stays_repeatable(self):
        crashed = self.base / "crashed"
        code, text, _ = self.checks(crashed, lambda m: self.CRASH)
        self.assertEqual(code, 3, text)
        self.assertEqual(self.verdict(crashed, code), "REPEATABLE")
        rerun = self.base / "rerun"
        self.assertEqual(self.checks(rerun, lambda m: self.PASS)[0], 0)
        states = {"901": ("FAILED", 3, "00:05:00"), "902": ("COMPLETED", 0, "00:05:00")}
        with redirect_stdout(io.StringIO()):
            self.assertEqual(tasks.counted_single({"T07 checks": [("901", crashed), ("902", rerun)]}, "T07 checks", 11, states.get), rerun)

    def test_a_signal_kill_inside_a_check_module_is_a_crash(self):
        """Review I1: the check modules' helpers say "<program> exit -9:" for a killed program; that failure is a crash (exit 3), not a
        failed check."""
        killed = self.base / "killed"
        code, text, _ = self.checks(killed, lambda m: self.KILLED if m.endswith("test_acts_finding") else self.PASS)
        self.assertEqual(code, 3, text)
        self.assertIn("RESULT t07-scoring checks-task incomplete", text)
        self.assertFalse((killed / "deterministic-checks.json").exists())
        self.assertEqual(self.verdict(killed, code), "REPEATABLE")

    def test_check_task_stops_of_slurm_are_repeatable(self):
        """Review I2 (the coordinator): TIMEOUT, OUT_OF_MEMORY, a deadline stop, CANCELLED and NODE_FAIL of a check task (blocks 1 and 6 only)
        are repeatable and the counted rerun is accepted; a recipe task keeps its rule."""
        rerun = self.base / "rerun"
        rerun.mkdir()
        (rerun / "milestones.txt").write_text("draws-started 2026-11-13T00:00:00Z\n")
        cases = {"TIMEOUT": ("TIMEOUT", 0, []), "OUT_OF_MEMORY": ("OUT_OF_MEMORY", 0, []), "deadline": ("FAILED", 3, [layout.STOPPED_AT_DEADLINE]),
                 "CANCELLED": ("CANCELLED by 1", 0, []), "NODE_FAIL": ("NODE_FAIL", 1, [])}
        for name, (state, code, extra) in cases.items():
            with self.subTest(case=name):
                stopped = self.base / f"stopped-{name}"
                stopped.mkdir()
                (stopped / "milestones.txt").write_text("".join(f"{m} 2026-11-13T00:00:00Z\n" for m in ["draws-started", *extra]))
                states = {"901": (state, code, "00:05:00"), "902": ("COMPLETED", 0, "00:05:00")}
                for task in ("T07 checks", "T07 negative cases", "T08 checks"):
                    with redirect_stdout(io.StringIO()):
                        self.assertEqual(tasks.counted_single({task: [("901", stopped), ("902", rerun)]}, task, 11, states.get), rerun)
                with self.assertRaises(layout.LayoutError):
                    tasks.counted_folder([("901", stopped), ("902", rerun)], 11, states.get)
                with self.assertRaises(tasks.Incomplete):
                    tasks.counted_single({"T09 fixed points": [("901", stopped), ("902", rerun)]}, "T09 fixed points", 11, states.get)

    def negative(self, out: Path, folder: Path) -> int:
        with redirect_stdout(io.StringIO()):
            return scoring.main(["negative-task", "--block", "11", "--build", str(self.base / "build"), "--folder", str(folder), "--out", str(out)])

    def test_a_refused_negative_cases_task_stands(self):
        """The kept case folder is checked first; its refusal (exit 2) comes after draws-started, so it is NOT-REPEATABLE (the user's)."""
        out = self.base / "negative"
        code = self.negative(out, self.base / "no-such-kept-folder")
        self.assertEqual(code, 2)
        self.assertEqual(tasks.Milestones(out).names(), [layout.EVENTS_ENTERED[0]])
        self.assertEqual(self.verdict(out, code), "NOT-REPEATABLE")

    def test_a_harness_defect_in_the_negative_cases_task_stays_repeatable(self):
        """An exit 3 from the runner's catch-all (an unexpected exception of the harness) after draws-started is REPEATABLE."""
        out = self.base / "negative-crash"
        original = scoring.check_negative_case_folder

        def crashing(folder):
            raise RuntimeError("planted defect of the harness")
        scoring.check_negative_case_folder = crashing
        try:
            code, text = run_main(["t07-negative-cases", "--block", 11, "--t07-build", self.base / "build", "--out", out])
        finally:
            scoring.check_negative_case_folder = original
        self.assertEqual(code, 3, text)
        self.assertIn("RESULT t07-negative-cases crashed", text)
        self.assertEqual(self.verdict(out, code), "REPEATABLE")

    def finder_run(self, script: str) -> tuple:
        build = self.base / "build"
        build.mkdir(exist_ok=True)
        finder = build / "acts_tracking_finder"
        finder.write_text(script)
        finder.chmod(0o755)
        out = self.base / f"negative-{abs(hash(script))}"
        with planted_kept_folder():
            code, text = run_main(["t07-negative-cases", "--block", 11, "--t07-build", build, "--out", out])
        return code, text, out

    def test_a_signal_kill_of_the_frozen_finder_is_a_crash(self):
        """Review I1: a negative return code (a signal: an OOM kill, a node fault) is a crash, exit 3, repeatable for a check task."""
        code, text, out = self.finder_run(FAKE_FINDER_KILLED)
        self.assertEqual(code, 3, text)
        self.assertIn("RESULT t07-scoring negative-task incomplete", text)
        self.assertIn("RESULT t07-negative-cases incomplete", text)
        self.assertEqual(self.verdict(out, code), "REPEATABLE")

    def test_an_ordinary_non_zero_exit_of_the_frozen_finder_stands(self):
        code, text, out = self.finder_run(FAKE_FINDER_EXIT_1)
        self.assertEqual(code, 1, text)
        self.assertIn("RESULT t07-negative-cases failed", text)
        self.assertEqual(self.verdict(out, code), "NOT-REPEATABLE")

    def test_a_truncated_finder_record_is_a_crash(self):
        """Review m2: the finder ended 0 but its record does not read (ENOSPC truncated it): a crash, exit 3, never a refusal."""
        code, text, out = self.finder_run(FAKE_FINDER_TRUNCATED)
        self.assertEqual(code, 3, text)
        self.assertEqual(self.verdict(out, code), "REPEATABLE")


class planted_kept_folder:
    """The kept negative-case folder's check replaced (its hashes are Freeze B's; the test has no kept folder)."""

    def __enter__(self):
        self.original = scoring.check_negative_case_folder
        scoring.check_negative_case_folder = lambda folder: {}
        return self

    def __exit__(self, *exc):
        scoring.check_negative_case_folder = self.original
        return False


def checks_attempt(base: Path, out: Path, text_of) -> tuple:
    """The checks-task command with the real checks_task, each module's output given by text_of (no module runs): (exit, output, the
    milestones seen at each module)."""
    seen = []

    def runner(module):
        seen.append(tasks.Milestones(out).names())
        return text_of(module)
    original = scoring.checks_task
    scoring.checks_task = functools.partial(original, module_runner=runner)
    try:
        with redirect_stdout(io.StringIO()) as printed:
            code = scoring.main(["checks-task", "--block", "11", "--build", str(base / "build"), "--out", str(out)])
    finally:
        scoring.checks_task = original
    return code, printed.getvalue(), seen


class FailedT07CheckReachesTheOutcome(unittest.TestCase):
    """Review I3, end to end through the T07 summary: the counted failed check yields the T07 fail (SUMMARY ... workflow fail with the check's
    REASON), never SUMMARY INCOMPLETE."""

    def setUp(self):
        from tests.adapters import test_t04_evaluation_tasks as base_tests
        self.base_tests = base_tests
        self.base = Path(tempfile.mkdtemp(dir=TEMPORARY_ROOT, prefix="t07-fail-"))
        self.addCleanup(__import__("shutil").rmtree, self.base, True)
        self.collection = self.base / "collection" / "collection.json"
        self.scores = self.base / "scores"
        base_tests.T07Markers.whole_state(self)          # every T07 harness task ended (hand-made), both checks tasks passed

    def summary(self, state_of):
        with redirect_stdout(io.StringIO()) as printed:
            code = tasks.t07_summary(11, self.scores, self.collection, self.base / "summary", attempts_file=self.base / "attempts.tsv", state_of=state_of)
        return code, printed.getvalue()

    def test_a_failed_check_then_a_rerun_gives_the_t07_fail(self):
        failed = self.base / "checks-failed"
        code, text, _ = checks_attempt(self.base, failed, lambda m: T07CheckTasks.FAIL if m.endswith("test_acts_finding") else T07CheckTasks.PASS)
        self.assertEqual(code, 1, text)
        (failed / "t07-checks.log").write_text(text + "RESULT t07-checks failed\n")   # the job's step log (lib.sh step), as the runner prints it
        rerun = self.base / "checks-rerun"
        code, text, _ = checks_attempt(self.base, rerun, lambda m: T07CheckTasks.PASS)
        (rerun / "t07-checks.log").write_text(text + "RESULT t07-checks ok\n")
        lines = [line for line in (self.base / "attempts.tsv").read_text().splitlines() if not line.startswith("T07 checks\t")]
        lines += [f"T07 checks\t901\t{failed}", f"T07 checks\t902\t{rerun}"]
        (self.base / "attempts.tsv").write_text("\n".join(lines) + "\n")
        states = {"901": ("FAILED", 1, "00:05:00")}
        code, text = self.summary(lambda job: states.get(job, ("COMPLETED", 0, "00:02:00")))
        self.assertEqual(code, 0, text)
        self.assertNotIn("SUMMARY INCOMPLETE", text)
        self.assertIn("SUMMARY T07 attempt 1: workflow fail", text)
        self.assertIn("REASON deterministic check A07: branches, revisions and counts traceable; refit never reported as finding does not pass", text)


if __name__ == "__main__":
    unittest.main()
