"""v6.3 D05c: evaluation adapter, aggregation, report, assessment identity and CLI exit codes. V27, V51, V52 and the
D05c parts of V15, V24, V25, V68; the rule-dependent parts of V11, V12, V18, V64 and V69 are in test_v63_d06.py.
Cases are built by tests/contracts/v63_cases.py in temporary folders."""
import contextlib
import copy
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests" / "contracts"))
import v63_cases as cases  # noqa: E402

NEEDS_AMS = unittest.skipUnless(cases.HAVE_AMS, "the AMS example is not in this copy")


def ac():
    from contracts import analysis_check
    return analysis_check


def check(bundle: Path, root: Path, *extra) -> tuple[int, dict]:
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = ac().main(["check", str(bundle), "--root", str(root), *map(str, extra)])
    return code, json.loads(buf.getvalue())


def report(bundle: Path, root: Path, **kw) -> dict:
    view, diags = ac().load_subject(bundle, root)
    return ac().evaluate(view, diags, **kw)


def states(rep: dict) -> dict:
    return {o["obligation_id"]: (o["state"], o["reason"]) for o in rep["obligations"]}


def foreign_table(c):
    """A table no coverage contract covers: a missing external dependency."""
    from contracts.recipe_semantics import canonical_sha256
    table = c.doc("differential-flux")
    table["table_id"] = "differential-flux-foreign"
    for it in c.items:
        if it["role"] == "recipe":
            r = c.doc(it["id"])
            r["semantics"] = {"table_id": "differential-flux-foreign", "sha256": canonical_sha256(table)}


class Tmp(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.addCleanup(self.td.cleanup)
        self.root = Path(self.td.name)


@NEEDS_AMS
class V27ExitCodes(Tmp):
    """V27: 2 > 1 > 3 > 0, telling an unreadable top level, a missing frozen file and a missing dependency apart."""

    def test_each_cause_and_the_precedence(self):
        base = cases.chain_case(self.root / "a")
        code, rep = check(base, self.root / "a")
        self.assertEqual((code, rep["input_validity"]), (3, "valid"))
        code, _ = check(self.root / "a" / "absent.json", self.root / "a")
        self.assertEqual(code, 2)
        missing = cases.chain_case(self.root / "b")
        (self.root / "b" / "artifacts" / "response_proton_synthetic-period-1.json").unlink()
        code, rep = check(missing, self.root / "b")
        self.assertEqual((code, rep["input_validity"]), (1, "invalid"))
        dep = cases.chain_case(self.root / "c", foreign_table)
        code, rep = check(dep, self.root / "c")
        self.assertEqual(code, 3)
        self.assertIn("definition.coverage_missing", {d["code"] for d in rep["input_diagnostics"]})
        both = cases.chain_case(self.root / "d", foreign_table)
        (self.root / "d" / "artifacts" / "response_proton_synthetic-period-1.json").unlink()
        self.assertEqual(check(both, self.root / "d")[0], 1)
        self.assertEqual(check(both, self.root / "d", "--previous", self.root / "nothing.json")[0], 2)

    def test_report_outside_the_bundle(self):
        base = cases.chain_case(self.root / "a")
        self.assertEqual(check(base, self.root / "a", "--out", self.root / "a" / "check-context.json")[0], 2)
        out = self.root / "report.json"
        code, _ = check(base, self.root / "a", "--out", out)
        self.assertEqual(code, 3)
        self.assertEqual(check(base, self.root / "a", "--out", out)[0], 2, "a report is never overwritten")


@NEEDS_AMS
class V51V52Aggregation(Tmp):
    def test_rule_not_run(self):
        rep = report(cases.chain_case(self.root / "a"), self.root / "a", rules={})
        self.assertEqual({o["reason"] for o in rep["obligations"]}, {"check.rule_not_run"})
        self.assertEqual((rep["coverage"]["value"], rep["consistency"]), ("partial", "undetermined"))
        self.assertEqual(rep["coverage"]["completed"], 0)
        self.assertGreater(rep["coverage"]["total"], 0)

    def test_invalid_versus_inconsistent(self):
        from contracts.analysis_checks.rules import outcome
        bundle = cases.chain_case(self.root / "a")
        names = [r["rule_id"] for r in ac().load_suite("counting-chain", "1.0.0")["rules"]]
        stub = {n: (lambda ob, env: outcome("satisfied", "stub.ok")) for n in names}
        stub["r-inv.root"] = lambda ob, env: outcome("violated", "stub.bad")
        rep = report(bundle, self.root / "a", rules=stub)
        self.assertEqual((rep["input_validity"], rep["coverage"]["value"], rep["consistency"]), ("valid", "complete", "inconsistent"))
        self.assertEqual(ac().exit_code(rep), 1)
        (self.root / "a" / "artifacts" / "dataset_synthetic-period-1.json").unlink()
        rep = report(bundle, self.root / "a", rules=stub)
        self.assertEqual((rep["input_validity"], rep["coverage"]["value"], rep["consistency"]), ("invalid", "partial", "undetermined"))


@NEEDS_AMS
class Declarations(Tmp):
    def test_waiver_is_not_counted(self):
        def waive(c):
            c.context["declarations"].append({"declaration_id": "waive-resp", "type": "not_applicable",
                                              "asserted_by": dict(cases.AGENT), "basis": {"rationale": "not needed"},
                                              "content": {"rule": "r-resp.response_use"}})
        plain = report(cases.chain_case(self.root / "a"), self.root / "a")
        waived = report(cases.chain_case(self.root / "b", waive), self.root / "b")
        self.assertEqual(states(plain), states(waived))
        self.assertIn("declaration.rule_waiver_not_counted", {f["code"] for f in waived["context_findings"]})

    def test_masking_keeps_obligations(self):
        bundle = cases.chain_case(self.root / "a")
        view, diags = ac().load_subject(bundle, self.root / "a")
        full = ac().evaluate(copy.deepcopy(view), diags)
        view["context"]["declarations"] = []
        masked = ac().evaluate(view, diags)
        self.assertEqual(set(states(full)), set(states(masked)))
        self.assertLessEqual(masked["coverage"]["completed"], full["coverage"]["completed"])
        self.assertEqual(masked["coverage"]["total"], full["coverage"]["total"])

    def test_removing_a_file_fails_integrity(self):
        bundle = cases.chain_case(self.root / "a")
        (self.root / "a" / "artifacts" / "response_helium_synthetic-period-2.json").unlink()
        rep = report(bundle, self.root / "a")
        self.assertEqual(rep["input_validity"], "invalid")
        self.assertEqual({o["reason"] for o in rep["obligations"]}, {"check.input_invalid"})
        self.assertEqual(len(rep["obligations"]), rep["coverage"]["total"])


@NEEDS_AMS
class Identity(Tmp):
    def test_rename_and_reorder(self):
        def rename_and_reorder(c):
            for it in c.items:
                if it["role"] in ("response", "dataset-record"):
                    new = "renamed/" + it["ref"].replace("/", "_")
                    c.files[new] = c.files.pop(it["ref"])
                    it["ref"] = new
            c.items.reverse()
            for key in ("roots", "recipe_instances", "declarations"):
                c.context[key].reverse()
        a = report(cases.chain_case(self.root / "a"), self.root / "a")
        b = report(cases.chain_case(self.root / "b", rename_and_reorder), self.root / "b")
        self.assertEqual(states(a), states(b))
        self.assertNotEqual(a["subject_digest"], b["subject_digest"])
        self.assertEqual(a["inventory_digest"], b["inventory_digest"])

    def test_report_schema(self):
        from contracts.schema import validate
        rep = report(cases.chain_case(self.root / "a"), self.root / "a")
        res = validate(rep, "check_report.json")
        self.assertTrue(res.ok, [f.as_dict() for f in res.findings])

    def test_previous_report_and_assessment(self):
        bundle = cases.chain_case(self.root / "a")
        first = report(bundle, self.root / "a")
        again = report(bundle, self.root / "a")
        self.assertEqual(first["assessment_id"], again["assessment_id"])
        other = report(bundle, self.root / "a", settings={"strict": True})
        self.assertNotEqual(first["assessment_id"], other["assessment_id"])
        smaller = copy.deepcopy(first)
        smaller["obligations"] = smaller["obligations"][:-3]
        smaller["subject_digest"] = "0" * 64
        delta = report(bundle, self.root / "a", previous=smaller)["scope_delta"]
        self.assertTrue(delta["new_subject"])
        self.assertEqual(len(delta["added"]), 3)
        self.assertFalse(delta["inherits"])


if __name__ == "__main__":
    unittest.main()
