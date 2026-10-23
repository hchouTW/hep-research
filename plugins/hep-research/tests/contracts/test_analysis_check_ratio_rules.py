"""v6.3 D07 (M2b, ratio subset): R-RATIO on RATIO-FACTORS and RATIO-EVIDENCE (tests/contracts/analysis_check_cases.ratio_case) and
on the old-style ratio of CASE-CHAIN. V28, V44, V45. Factor cancellation is checked against a hand-computed oracle;
models stay unsupported until their suite exists (O03).
Cases run on check-context 1.1.0 and the newest 1.1.0 pre-release suites (release R2): the 1.0.0 suites name rule
versions this checker no longer runs."""
import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests" / "contracts"))
import analysis_check_cases as cases  # noqa: E402

NEEDS_AMS = unittest.skipUnless(cases.HAVE_AMS, "the AMS example is not in this copy")


def ac():
    from contracts import analysis_check
    return analysis_check


def get(rep, oid):
    return next(o for o in rep["obligations"] if o["obligation_id"] == oid)


def claim(c, effect) -> dict:
    return next(x for x in c.doc("spec")["extension"]["ratio"]["cancellations"] if x["effect"] == effect)


@NEEDS_AMS
class Ratio(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.addCleanup(self.td.cleanup)
        self.n = 0

    def run_case(self, builder=None, variant=None):
        self.n += 1
        root = Path(self.td.name) / f"r{self.n}"
        b = (builder or cases.ratio_case)(root, cases.both(cases.context_1_1, variant))  # the 1.1.0 rules (release R2)
        view, diags = ac().load_subject(b, root)
        return ac().evaluate(view, diags)

    def test_positive_ratio_case(self):
        rep = self.run_case()
        self.assertEqual((rep["status"], rep["consistency"]), ("complete", "consistent"))
        self.assertIn({"id": "ratio-subset", "version": cases.SUITE_1_1}, rep["assessment"]["suites"])
        self.assertEqual(get(rep, "r-ratio.operands:ratio-p1")["reason"], "check.ratio_operands_compatible")

    def test_v44_factors(self):
        rep = self.run_case()
        o = get(rep, "r-ratio.cancellation:ratio-p1#trigger_efficiency")
        self.assertEqual((o["state"], o["reason"], o["exact"]), ("satisfied", "check.cancellation_exact", True))
        holder = {}

        def selection_cancels(c):
            claim(c, "selection_efficiency")["treatment"] = "cancels"
            holder["cal"] = c.doc("eff-cal")
        rep = self.run_case(variant=selection_cancels)
        o = get(rep, "r-ratio.cancellation:ratio-p1#selection_efficiency")
        self.assertEqual((o["state"], o["reason"], o["exact"]), ("violated", "check.cancellation_not_exact", False))
        rows = holder["cal"]["factors"]["selection_efficiency"]["by_scope"]
        num = rows["species:helium/period:synthetic-period-1"]
        den = rows["species:proton/period:synthetic-period-1"]
        # hand oracle: (N1/e1)/(N2/e2) = (N1/N2) * (e2/e1); the residual is e2/e1 in every bin where it is not 1
        oracle = [k for k, (e1, e2) in enumerate(zip(num, den)) if abs(e2 / e1 - 1.0) > 1e-12]
        self.assertEqual(o["bins"], {"evaluated": len(num), "residual_bins": len(oracle), "first_residuals": oracle[:5]})
        self.assertEqual(rep["consistency"], "inconsistent")

        def zero(c):
            c.doc("eff-cal")["factors"]["trigger_efficiency"]["scalar"] = 0.0
        o = get(self.run_case(variant=zero), "r-ratio.cancellation:ratio-p1#trigger_efficiency")
        self.assertEqual((o["state"], o["reason"]), ("violated", "check.cancellation_domain"))

    def test_v45_evidence(self):
        def bare(c):
            c.remove("vr-selection")
            claim(c, "selection_efficiency")["verification"] = True
        o = get(self.run_case(variant=bare), "r-ratio.correlation:ratio-p1#selection_efficiency")
        self.assertEqual((o["state"], o["reason"]), ("unverified", "check.correlation_unsupported_claim"))

        def one_side(c):
            c.doc("vr-selection")["subjects"] = c.doc("vr-selection")["subjects"][:1] + [
                {"root": "flux-proton-p2", "version": "synthetic-1"}]
        o = get(self.run_case(variant=one_side), "r-ratio.correlation:ratio-p1#selection_efficiency")
        self.assertEqual(o["reason"], "check.correlation_evidence_incomplete")

        def contradicted(c):
            c.doc("vr-selection")["claim"]["relation"] = "correlated"
        o = get(self.run_case(variant=contradicted), "r-ratio.correlation:ratio-p1#selection_efficiency")
        self.assertEqual((o["state"], o["reason"]), ("violated", "check.correlation_contradicted"))

        def declared(c):
            c.remove("vr-selection")
            c.context["declarations"].append({"declaration_id": "corr-sel", "type": "correlation",
                                              "asserted_by": dict(cases.AGENT), "basis": {"source": "spec#/extension/selections"},
                                              "content": {"ratio_root": "ratio-p1", "effect": "selection_efficiency",
                                                          "relation": "independent"}})
        o = get(self.run_case(variant=declared), "r-ratio.correlation:ratio-p1#selection_efficiency")
        self.assertEqual((o["state"], o["declaration_based"]), ("satisfied", True))

    def test_v28_free_text_ratio(self):
        def ratio_suite(c):
            c.context["suites"] = [{"id": "ratio-subset", "version": cases.SUITE_1_1}]
        rep = self.run_case(cases.chain_case, ratio_suite)
        o = get(rep, "r-ratio.operands:spec")
        self.assertEqual((o["state"], o["reason"]), ("unverified", "check.ratio_operands_unbound"))
        self.assertEqual([x for x in self.run_case(cases.chain_case)["obligations"] if x["rule_id"].startswith("r-ratio")], [])

    def test_operand_scopes(self):
        def wrong_axis(c):
            c.context["ratio_roots"][0]["over_axis"] = "period"
        o = get(self.run_case(variant=wrong_axis), "r-ratio.operands:ratio-p1")
        self.assertEqual((o["state"], o["reason"]), ("violated", "check.ratio_operands_incompatible"))

        def same_species(c):
            c.context["ratio_roots"][0]["denominator"] = {"root": "flux-helium-p1"}
        o = get(self.run_case(variant=same_species), "r-ratio.operands:ratio-p1")
        self.assertEqual((o["state"], o["reason"]), ("violated", "check.ratio_operands_incompatible"))

    def test_model_suite_needs_a_model_bundle(self):
        # model-card/v1 exists (M2b model part), but it checks model bundles only: a chain bundle selecting it is refused
        def model_suite(c):
            c.context["suites"] = [{"id": "model-card", "version": cases.SUITE_1_1}]
        with self.assertRaises(Exception) as ctx:
            self.run_case(cases.positive_case, model_suite)
        self.assertEqual(getattr(ctx.exception, "code", None), "bundle.suite_mode")


if __name__ == "__main__":
    unittest.main()
