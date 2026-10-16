"""v6.3 D10: the advisory report check of contracts/permit.py and scoped exceptions (V26, V60 pre-execution parts,
V65, V66). A check report counts only when an accepted, bound attestation review lists it as evidence; it must be
about the permit's bundle, internally consistent (a hand-edited pass fails), from the suites and checker the purpose
policy names, complete and without violation. The output is advisory (formal_use_allowed false); the custodian's gate
decides. With the chain and ratio suites only there is no post-execution report, so a policy that does not accept a
pre-execution report refuses it. Synthetic data only."""
import contextlib
import copy
import datetime
import hashlib
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
from contracts.release_manifest import canonical_sha256  # noqa: E402

NOW = datetime.datetime(2026, 10, 16, 12, 0, 0, tzinfo=datetime.UTC)
REV = {"as_of": "2026-10-16T11:30:00Z", "source": "synthetic-gate", "revoked": []}
NEEDS_AMS = unittest.skipUnless(cases.HAVE_AMS, "the AMS example is not in this copy")


def ac():
    from contracts import analysis_check
    return analysis_check


def codes(refusals):
    return {r["code"] for r in refusals}


@NEEDS_AMS
class ReportCheck(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.addCleanup(self.td.cleanup)
        self.root = Path(self.td.name) / "c"
        bundle_path = cases.ratio_case(self.root)
        self.bundle = json.loads(bundle_path.read_text())
        view, diags = ac().load_subject(bundle_path, self.root)
        self.report = ac().evaluate(view, diags)
        self.recipe = json.loads((self.root / "recipe.json").read_text())
        self.policy = {"policy_version": "1.0.0", "purposes": {"formal-analysis": {
            "suites": [{"id": "counting-chain", "version": "1.0.0"}, {"id": "ratio-subset", "version": "1.0.0"}],
            "checker_digests": [self.report["assessment"]["checker"]], "accept_pre_execution_only": True}}}
        self.permit = {"subject": {"analysis_bundle_sha256": self.bundle["bundle_digest"], "analysis_bundle_ref": "bundle.json",
                                   "artifacts": ["0" * 64]}}

    def attest(self, report=None, conclusion="accepted", include_report=True, purposes=("formal-analysis",)):
        report = self.report if report is None else report
        ev = self.root / "evidence"
        ev.mkdir(exist_ok=True)
        (ev / "report.json").write_text(json.dumps(report))
        (ev / "closure.json").write_text('{"closure": "synthetic"}')
        evidence = [{"ref": "evidence/closure.json", "sha256": hashlib.sha256((ev / "closure.json").read_bytes()).hexdigest()}]
        if include_report:
            evidence.append({"ref": "evidence/report.json", "sha256": hashlib.sha256((ev / "report.json").read_bytes()).hexdigest()})
        scope = {"observable": "synthetic He/p ratio", "data": ["synthetic"],
                 "recipe": {"recipe_id": self.recipe["recipe_id"], "sha256": canonical_sha256(self.recipe)},
                 "calibrations": [], "assumptions": ["synthetic"], "purposes": list(purposes)}
        review = {"reviewer": "synthetic reviewer", "role": "analysis-reviewer", "date": "2026-10-15",
                  "bundle_sha256": self.bundle["bundle_digest"], "scope_sha256": canonical_sha256(scope),
                  "evidence": evidence, "conclusion": conclusion, "record_ref": "review-record-1"}
        return {"attestation_version": "1.0.0", "attestation_id": "att-v63",
                "subject": {"bundle_sha256": self.bundle["bundle_digest"], "scope": scope},
                "capability": {"required_capabilities": []}, "review": {"reviews": [review]},
                "lifecycle": {"state": "active", "effective": "2026-10-15T00:00:00Z", "expires": "2026-11-15T00:00:00Z",
                              "revocation_ref": "rev-att-v63", "status_source": "synthetic-gate", "max_status_age_s": 3600}}

    def check(self, att, policy=None, permit=None, purpose="formal-analysis"):
        from contracts.permit import report_check
        return report_check(att, self.bundle, self.root, self.root, self.policy if policy is None else policy, purpose,
                            permit=self.permit if permit is None else permit, now=NOW, revocations=REV,
                            roles=["analysis-reviewer"])

    def test_v65_accepted_review_with_report(self):
        self.assertTrue(any(o["declaration_based"] for o in self.report["obligations"]))
        self.assertEqual(self.report["formal_use_view"]["coverage"]["value"], "partial")
        self.assertEqual(self.check(self.attest()), [])

    def test_v66_no_accepted_review(self):
        self.assertIn("permit.report_unreviewed", codes(self.check(self.attest(conclusion="rejected"))))
        self.assertIn("permit.report_missing", codes(self.check(self.attest(include_report=False))))

    def test_v60_wrong_bindings(self):
        edited = copy.deepcopy(self.report)
        edited["obligations"][0]["state"] = "violated"  # a hand edit that the summary fields no longer match
        self.assertIn("permit.report_inconsistent", codes(self.check(self.attest(edited))))
        forged = copy.deepcopy(self.report)
        forged["status"] = "complete"
        forged["assessment"]["settings"] = {"forged": True}
        self.assertIn("permit.report_inconsistent", codes(self.check(self.attest(forged))))
        wrong_suite = copy.deepcopy(self.policy)
        wrong_suite["purposes"]["formal-analysis"]["suites"].append({"id": "model-card", "version": "1.0.0"})
        self.assertIn("permit.report_wrong_suite", codes(self.check(self.attest(), policy=wrong_suite)))
        stale = copy.deepcopy(self.policy)
        stale["purposes"]["formal-analysis"]["checker_digests"] = ["f" * 64]
        self.assertIn("permit.report_stale_assessment", codes(self.check(self.attest(), policy=stale)))
        other = copy.deepcopy(self.permit)
        other["subject"]["analysis_bundle_sha256"] = "e" * 64
        self.assertIn("permit.report_wrong_subject", codes(self.check(self.attest(), permit=other)))
        strict = copy.deepcopy(self.policy)
        strict["purposes"]["formal-analysis"]["accept_pre_execution_only"] = False
        self.assertIn("permit.report_pre_execution_only", codes(self.check(self.attest(), policy=strict)))
        both = self.attest(purposes=("formal-analysis", "validation"))
        self.assertIn("permit.report_policy_missing", codes(self.check(both, purpose="validation")))
        self.assertIn("permit.report_unreviewed", codes(self.check(self.attest(), purpose="validation")))

    def test_incomplete_or_violated(self):
        partial = copy.deepcopy(self.report)
        partial["obligations"][0].update(state="unverified", reason="check.rule_not_run")
        from contracts.analysis_checks.outcomes import formal_view, summarize
        s = summarize(partial["obligations"], True)
        partial.update(coverage=s["coverage"], consistency=s["consistency"], counts=s["counts"], status="incomplete",
                       formal_use_view=formal_view(partial["obligations"], True))
        self.assertIn("permit.report_incomplete", codes(self.check(self.attest(partial))))

    def test_cli(self):
        from contracts import permit
        att = self.attest()
        (self.root / "att.json").write_text(json.dumps(att))
        (self.root / "policy.json").write_text(json.dumps(self.policy))
        (self.root / "permit.json").write_text(json.dumps(self.permit))
        (self.root / "rev.json").write_text(json.dumps(REV))
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = permit.main(["check-report", str(self.root / "att.json"), "--bundle", str(self.root / "bundle.json"),
                                "--root", str(self.root), "--policy", str(self.root / "policy.json"),
                                "--permit", str(self.root / "permit.json"), "--revocations", str(self.root / "rev.json"),
                                "--required-roles", "analysis-reviewer", "--now", "2026-10-16T12:00:00Z"])
        out = json.loads(buf.getvalue())
        self.assertEqual((code, out["status"], out["formal_use_allowed"]), (0, "checked", False))


@NEEDS_AMS
class V26Exceptions(unittest.TestCase):
    """V26: a scoped exception keeps the original finding; a non-waivable item is rejected."""

    def test_scoped_exception(self):
        with tempfile.TemporaryDirectory() as td:
            def unfolding(c):
                next(x for x in c.doc("spec")["extension"]["corrections"] if x["category"] == "migration")["applied_in"] = "unfolding"
            root = Path(td) / "c"
            view, diags = ac().load_subject(cases.chain_case(root, unfolding), root)
            base = ac().evaluate(view, diags)
            exceptions = [
                {"obligation_id": "r-resp.response_use:proton-p1", "finding": "check.response_use_conflict",
                 "rationale": "synthetic: the unfolding is done in a separate, reviewed step",
                 "decided_by": {"kind": "person", "id": "synthetic custodian"}, "expires": "2027-01-01"},
                {"obligation_id": "r-inv.root:flux-proton-p1", "finding": "check.root_complete", "rationale": "x",
                 "decided_by": {"kind": "person", "id": "synthetic custodian"}, "expires": "2027-01-01"},
                {"obligation_id": "r-resp.response_use:helium-p1", "finding": "check.response_use_conflict", "rationale": "x",
                 "decided_by": {"kind": "agent", "id": "claude-code"}, "expires": "2027-01-01"}]
            rep = ac().evaluate(view, diags, exceptions=exceptions, now="2026-10-16")
        states = lambda r: {o["obligation_id"]: o["state"] for o in r["obligations"]}  # noqa: E731
        self.assertEqual(states(rep), states(base))
        self.assertEqual((rep["consistency"], rep["status"]), (base["consistency"], base["status"]))
        verdicts = {e["obligation_id"]: (e["status"], e.get("reason")) for e in rep["exceptions"]}
        self.assertEqual(verdicts["r-resp.response_use:proton-p1"], ("accepted", None))
        self.assertEqual(verdicts["r-inv.root:flux-proton-p1"], ("rejected", "exception.not_waivable"))
        self.assertEqual(verdicts["r-resp.response_use:helium-p1"], ("rejected", "exception.not_a_person"))


if __name__ == "__main__":
    unittest.main()
