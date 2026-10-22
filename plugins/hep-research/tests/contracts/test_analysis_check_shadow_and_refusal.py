"""v6.3 D09: shadow integration and the reader refusal matrix (V31, V59). The new check runs beside the old entry points
without changing them; every legacy finding and every new violation gets a class in the difference review, and none
stays unclassified. contracts/rules/refusal_matrix.json states what each old entry point does with each new format;
the current-tree column is checked here (the 0.11.0 column is measured in docs/dev/cross-artifact-check/refusal-matrix.md)."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests" / "contracts"))
import analysis_check_cases as cases  # noqa: E402
from test_analysis_check_chain_rules import PRE_STEPS, add_instance, keyed  # noqa: E402

NEEDS_AMS = unittest.skipUnless(cases.HAVE_AMS, "the AMS example is not in this copy")
MATRIX = json.loads((ROOT / "contracts" / "rules" / "refusal_matrix.json").read_text())
SCOPE = "species:proton/period:synthetic-period-1"


def ac():
    from contracts import analysis_check
    return analysis_check


def run(*args):
    p = subprocess.run([sys.executable, *map(str, args)], capture_output=True, text=True, cwd=ROOT, timeout=300)
    try:
        out = json.loads(p.stdout)
    except ValueError:
        out = None
    return p.returncode, out, p.stderr


def regression(keys_a, keys_b):
    def variant(c):
        r = c.doc("flux-reduced")
        r["recipe_version"] = "1.1.0"
        r["steps"] = [{"step_id": "background", "operator": "subtract_background"},
                      dict({"step_id": "eff-a", "operator": "correct_efficiency"}, **({"effect_keys": keys_a} if keys_a else {})),
                      dict({"step_id": "eff-b", "operator": "correct_efficiency"}, **({"effect_keys": keys_b} if keys_b else {})),
                      {"step_id": "exposure", "operator": "divide_exposure"},
                      {"step_id": "bin-width", "operator": "divide_bin_width"}]
        c.doc("spec")["extension"]["corrections"][0].pop("application_id")
    return variant


def unfolding(c):
    next(x for x in c.doc("spec")["extension"]["corrections"] if x["category"] == "migration")["applied_in"] = "unfolding"


SHADOW_CASES = {
    "positive": (cases.positive_case, None),
    "case-chain": (cases.chain_case, None),
    "case-chain-v34": (cases.chain_case, unfolding),
    "ratio": (cases.ratio_case, None),
    "v21": (cases.positive_case, regression(keyed(SCOPE, "a" * 64), keyed(SCOPE, "b" * 64))),
    "v22": (cases.positive_case, regression(keyed("species:proton"), None)),
    "v16": (cases.positive_case, regression(keyed("region-a"), keyed("region-b"))),
    "v03": (cases.positive_case, lambda c: add_instance(c, "proton-p1-pre", "flux-pre", PRE_STEPS, feeds="proton-p1")),
}


@NEEDS_AMS
class ShadowDifferenceReview(unittest.TestCase):
    def test_zero_unclassified(self):
        with tempfile.TemporaryDirectory() as td:
            for name, (builder, variant) in SHADOW_CASES.items():
                with self.subTest(case=name):
                    root = Path(td) / name
                    view, diags = ac().load_subject(builder(root, variant), root)
                    review = ac().difference_review(view, ac().evaluate(view, diags))
                    self.assertEqual(review["unclassified"], 0, [r for r in review["rows"] if r["class"] == "unclassified"])
                    if name == "v21":
                        self.assertIn("agrees", review["counts"])
                    if name == "case-chain-v34":
                        self.assertIn("new-only", review["counts"])

    def test_v31_old_contract_version(self):
        with tempfile.TemporaryDirectory() as td:
            def old(c):
                spec = c.doc("spec")
                spec["contract_version"] = "2.5.0"
                spec["versions"]["contracts"] = "2.5.0"
            root = Path(td) / "old"
            bundle = cases.positive_case(root, old)
            code, out, _ = run("contracts/validate.py", root / "spec.json")
            view, diags = ac().load_subject(bundle, root)
            report = ac().evaluate(view, diags)
        self.assertFalse([f for f in out["findings"] if f["code"].startswith("check.")])
        self.assertFalse([f for f in out["findings"] if f["code"].startswith("measurement.")],
                         "the old non-strict reading applies no measurement semantics")
        self.assertTrue(report["obligations"])
        self.assertEqual(report["status"], "complete")


class ModelAndRunShadowReview(unittest.TestCase):
    """The shadow review on the model and run cases (added for the G-ENFORCE inputs, docs/dev/cross-artifact-check/shadow-review.md):
    zero unclassified; the legacy model-card errors that decide the same question as a new rule agree with it."""

    def test_zero_unclassified(self):
        import analysis_check_runs as runs

        def dup(c):
            card = c.doc("card-sr-cr")
            card["samples"][2]["modifiers"][1] = {"type": "constrained-normalization", "parameter": "lumi_cr"}
            card["constraints"].append({"parameter": "lumi_cr", "kind": "auxiliary-measurement", "aux_id": "lumi-2026",
                                        "form": "gaussian", "width": 0.02})
        model = {"positive": (None, {}), "same-aux-id": (dup, {"agrees": 2}),
                 "unconstrained": (lambda c: c.doc("card-sr-cr").update(constraints=[]), {"agrees": 4}),
                 "prior": (lambda c: c.doc("card-sr-cr")["constraints"][0].update(kind="prior"), {"artifact-local": 1}),
                 "joint": (lambda c: cases.two_models(c, joint=True), {"new-only": 2})}
        with tempfile.TemporaryDirectory() as td:
            for name, (variant, counts) in model.items():
                with self.subTest(case=name):
                    root = Path(td) / name
                    view, diags = ac().load_subject(cases.model_case(root, variant), root)
                    review = ac().difference_review(view, ac().evaluate(view, diags))
                    self.assertEqual((review["unclassified"], review["counts"]), (0, counts))
            for name, build in (("run-chain", runs.run_chain), ("run-campaign", runs.run_campaign)):
                with self.subTest(case=name):
                    post = build(Path(td) / name)
                    view, diags = ac().load_subject(post.bundle_path, post.root)
                    rep = ac().evaluate(view, diags, results=json.loads(post.save().read_text()))
                    self.assertEqual(ac().difference_review(view, rep)["unclassified"], 0)


@NEEDS_AMS
class V59RefusalMatrix(unittest.TestCase):
    """V59: the matrix exposes old readers that do not refuse a new format; each such row is a release blocker."""

    @classmethod
    def setUpClass(cls):
        cls.td = tempfile.TemporaryDirectory()
        cls.root = Path(cls.td.name) / "r"
        cls.bundle = cases.ratio_case(cls.root)
        view, diags = ac().load_subject(cls.bundle, cls.root)
        (cls.root / "report.json").write_text(json.dumps(ac().evaluate(view, diags)))
        up = json.loads((cls.root / "spec.json").read_text())
        up["extension"]["corrections"] = [{"effect_id": "efficiency", "category": "selection_efficiency",
                                           "applied_in": "estimator", "target_scope": SCOPE, "calibration_digest": "none",
                                           "variation_id": "nominal", "stage": "estimator"}]
        (cls.root / "upstream-cap.json").write_text(json.dumps(up))
        (cls.root / "upstream-cap-v9.json").write_text(json.dumps(dict(up, required_capabilities=["measurement:correction-keys-v9"])))
        (cls.root / "result-binding.json").write_text(json.dumps(  # M2c's result binding, a synthetic minimal one
            {"binding_version": "1.0.0", "kind": "result-binding", "analysis_bundle_sha256": "a" * 64,
             "semantic_lock_sha256": "b" * 64, "asserted_by": {"kind": "agent", "id": "claude-code"},
             "runs": [], "campaigns": [], "results": []}))

    @classmethod
    def tearDownClass(cls):
        cls.td.cleanup()

    def observe(self, row) -> str:
        r, fmt, entry = self.root, row["format"], row["entry_point"]
        files = {"check-context 1.0.0": r / "check-context.json", "semantic-lock 1.0.0": r / "semantic-lock.json",
                 "check report 1.0.0": r / "report.json", "validation record 1.0.0": r / "validation-selection.json",
                 "measurement-spec with measurement:correction-keys-v1": r / "spec.json",
                 "result binding 1.0.0": r / "result-binding.json"}
        if entry == "contracts/analysis_bundle.py verify":
            code, out, _ = run(entry.split()[0], "verify", self.bundle, "--root", r)
            return "refuses" if code == 1 and out["status"] == "invalid" else "accepts"
        if entry == "contracts/validate.py":
            code, out, _ = run(entry, files[fmt])
            if code == 1 and any(f["code"] in ("schema.required", "contract.unknown_capability") for f in out["findings"]):
                return "refuses"
            return "implements" if not any(f["code"] == "measurement.unknown_key" for f in out["findings"]) else "accepts"
        if entry.endswith("review_measurement_spec.py"):
            code, _, err = run(entry, files[fmt])
            return "refuses" if code == 2 and "not a measurement-spec" in err else "accepts"
        if entry == "contracts/dependencies.py":
            code, out, _ = run(entry, files[fmt], "--root", r)
            return "accepts" if code == 0 and out["status"] == "ok" else "refuses"
        if entry == "contracts/recipe_semantics.py --upstream":
            def found(upstream):
                _, out, _ = run("contracts/recipe_semantics.py", ROOT / "contracts" / "semantics" / "recipes" /
                                "flux_from_counts.json", "--upstream", upstream)
                return {f["code"] for rec in out["recipes"] for f in rec["findings"]}
            known, unknown = found(r / "upstream-cap.json"), found(r / "upstream-cap-v9.json")
            reads_keys = bool({"semantics.repeat_undetermined", "semantics.repeated_correction"} & known)
            if reads_keys and "semantics.upstream_unknown_capability" in unknown:
                return "implements"
            return "exposes" if reads_keys else "refuses"
        if entry == "contracts/attestation.py (bundle digest)":
            from contracts.attestation import _bundle_digest
            bundle = json.loads(self.bundle.read_text())
            return "implements" if _bundle_digest(bundle) == bundle["bundle_digest"] else "refuses"
        raise AssertionError(f"no observation for {entry}")

    def test_current_column(self):
        for row in MATRIX["rows"]:
            with self.subTest(format=row["format"], entry=row["entry_point"]):
                self.assertEqual(self.observe(row), row["current"])

    def test_non_refusing_rows_are_blockers(self):
        for row in MATRIX["rows"]:
            self.assertEqual(row["blocker"], row["current"] in ("accepts", "exposes"), row)


if __name__ == "__main__":
    unittest.main()
