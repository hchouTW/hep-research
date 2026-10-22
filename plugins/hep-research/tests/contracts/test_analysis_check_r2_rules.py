"""Cross-artifact check Phase 2, release R2 rule fixes that need more than a gap probe. r-aux.use 1.1.0 (G5, DR-3):
an observation is its source identity (an envelope's artifact_id, else the item's frozen digest) plus pointer.
A3 (check-context 1.1.0): an outcome that read a bundle-supplied coverage contract is declaration-based.
r-run.blinding 1.1.0 (G7, G13): data leaves of the lineage and the project's blinded list. r-run.campaign 1.1.0 (G6):
the campaign's inputs (result binding 1.1.0) match their sources and reach the analysis. r-comp.factor_values 1.1.0
(G4, DR-6), whose relative tolerance comes from declared significant digits and never from the factor table. A table
whose values are the true values rounded to the declared digits passes for any powers (the bound sum|power| * u);
a real break, an undeclared table and a declaration the values contradict get the 1e-9 default. Synthetic numbers
only; the rule is called on a minimal environment."""
from __future__ import annotations

import random
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))


class Env:
    def __init__(self, powers: dict, doc: dict):
        self.catalog = {"compositions": [{"composition_id": "c", "parent": "p",
                                          "children": [{"effect": e, "power": w} for e, w in powers.items()]}]}
        self.items = {"t": {"role": "calibration", "doc": doc}}


def table(parent, children: dict, digits=None, tolerance=None) -> dict:
    doc = {"factor_table_version": "1.0.0", "factors": {"p": {"values": parent}, **{e: {"values": v} for e, v in children.items()}}}
    if digits is not None:
        doc["significant_digits"] = digits
    if tolerance is not None:
        doc["tolerance"] = {"relative": tolerance}
    return doc


def run(powers: dict, doc: dict) -> dict:
    from contracts.analysis_checks.rules import r_comp_factor_values
    return r_comp_factor_values({"subject": {"composition": "c", "factor_table": "t"}}, Env(powers, doc))


def rounded(x: float, d: int) -> float:
    return float(f"{x:.{d - 1}e}")


class FactorTolerance(unittest.TestCase):
    def test_rounded_tables_pass_and_a_real_break_fails(self):
        rng = random.Random(20261023)
        for trial in range(400):
            d = rng.randint(2, 7)
            powers = {f"e{i}": rng.choice([-2, -1, 1, 2]) for i in range(rng.randint(1, 3))}
            true = {e: [10 ** rng.uniform(-3, 3) for _ in range(6)] for e in powers}
            parent = [1.0] * 6
            for e, w in powers.items():
                parent = [a * b ** w for a, b in zip(parent, true[e])]
            children = {e: [rounded(x, d) for x in v] for e, v in true.items()}
            with self.subTest(trial=trial, d=d, powers=powers):
                o = run(powers, table([rounded(x, d) for x in parent], children, digits=d))
                self.assertEqual(o["state"], "satisfied", o["message"])
                broken = [rounded(x, d) for x in parent]
                broken[3] = rounded(broken[3] * (1 + 4 * o["tolerance"]["relative"]), d)
                self.assertEqual(run(powers, table(broken, children, digits=d))["state"], "violated")

    def test_undeclared_digits_use_the_default(self):
        o = run({"a": 1, "b": 1}, table([1.0, 3.0], {"a": [0.5, 1.0], "b": [2.0, 2.0]}))
        self.assertEqual((o["state"], o["tolerance"]["relative"]), ("violated", 1e-9))
        o = run({"a": 1}, table([0.333], {"a": [1 / 3]}))
        self.assertEqual(o["state"], "violated")

    def test_the_tables_own_tolerance_is_not_used(self):
        o = run({"a": 1, "b": 1}, table([1.0, 3.0], {"a": [0.5, 1.0], "b": [2.0, 2.0]}, tolerance=0.6))
        self.assertEqual(o["state"], "violated")
        self.assertIn("own tolerance is not used", o["message"])

    def test_a_declaration_the_values_contradict_is_not_used(self):
        # 0.3333 against 0.3333 passes at 4 declared digits; against 0.33333 (5 digits) the declaration is false
        self.assertEqual(run({"a": 1}, table([0.3333], {"a": [0.3333]}, digits=4))["state"], "satisfied")
        o = run({"a": 1}, table([0.3333], {"a": [0.33333]}, digits=4))
        self.assertEqual(o["state"], "violated")
        self.assertIn("more than the declared 4", o["tolerance"]["basis"])

    def test_one_digit_tables_tolerate_what_one_digit_cannot_resolve(self):
        # the probe table at 1 declared digit: 3 = 1 x 2 cannot be refuted by values rounded to one digit
        o = run({"a": 1, "b": 1}, table([1.0, 3.0], {"a": [0.5, 1.0], "b": [2.0, 2.0]}, digits=1))
        self.assertEqual(o["state"], "satisfied")
        self.assertAlmostEqual(o["tolerance"]["relative"], 1.5)

    def test_powers_count_by_absolute_value(self):
        from contracts.analysis_checks.rules import _factor_tolerance
        comp = {"children": [{"effect": "a", "power": -2}, {"effect": "b", "power": 1}]}
        tol, _ = _factor_tolerance({"significant_digits": 3}, comp, {"p": [1.0], "a": [1.0], "b": [1.0]})
        self.assertAlmostEqual(tol, 4 * 0.5e-2)

    def test_significant_digits_shape(self):
        from contracts.analysis_check import factor_table_shape
        base = table([1.0], {"a": [1.0]})
        self.assertEqual(factor_table_shape(dict(base, significant_digits=3)), [])
        for bad in (0, 18, 2.5, True, "3"):
            with self.subTest(bad=bad):
                self.assertIn("significant_digits is an integer from 1 to 17", factor_table_shape(dict(base, significant_digits=bad)))

    def test_significant_digits_of_written_numbers(self):
        from contracts.analysis_checks.rules import _significant_digits
        for x, n in ((2.0, 1), (0.5, 1), (0.3333, 4), (1200, 2), (1.25e-7, 3), (1 / 3, 16), (-0.0750, 2)):
            with self.subTest(x=x):
                self.assertEqual(_significant_digits(x), n)



class ObservationIdentity(unittest.TestCase):
    def test_envelopes_compare_by_artifact_id_and_other_files_by_digest(self):
        from contracts.analysis_checks.model import _overlap, _source
        view = {"items": {
            "a": {"sha256": "1" * 64, "doc": {"lumi": 1.0}},
            "a-copy": {"sha256": "1" * 64, "doc": {"lumi": 1.0}},
            "a-plus": {"sha256": "2" * 64, "doc": {"lumi": 1.0, "note": "one key more"}},
            "env": {"sha256": "3" * 64, "doc": {"contract_version": "3.7.0", "artifact_id": "lumi-2026", "x": 1}},
            "env-edit": {"sha256": "4" * 64, "doc": {"contract_version": "3.7.0", "artifact_id": "lumi-2026", "x": 2}},
            "bin": {"sha256": "5" * 64, "doc": None}}}
        self.assertEqual(_overlap(("a", "/lumi"), ("a-copy", "/lumi"), view), "same")
        self.assertEqual(_overlap(("a", ""), ("a-copy", "/lumi"), view), "overlap")
        self.assertEqual(_overlap(("a", "/lumi"), ("a-copy", "/trig"), view), "distinct")
        self.assertEqual(_overlap(("env", "/x"), ("env-edit", "/x"), view), "same")  # one source, values never compared
        self.assertEqual(_overlap(("a", "/lumi"), ("a-plus", "/lumi"), view), "distinct")  # known limitation (DR-3)
        self.assertEqual(_source(view, "bin"), ("digest", "5" * 64))
        self.assertEqual(_source(view, "missing"), ("item", "missing"))
        self.assertEqual(_overlap(("a", "/lumi"), ("a-copy", "/lumi")), "distinct")  # without a view: item IDs (1.0.0)



def _case_modules():
    sys.path.insert(0, str(ROOT / "tests" / "contracts"))
    import analysis_check_cases as cases
    import analysis_check_runs as runs
    return cases, runs


def _report(bundle: Path, root: Path) -> dict:
    from contracts import analysis_check as ac
    view, diags = ac.load_subject(bundle, root)
    return ac.evaluate(view, diags)


class BundleCoverageFlag(unittest.TestCase):
    def setUp(self):
        import tempfile
        self.td = tempfile.TemporaryDirectory()
        self.addCleanup(self.td.cleanup)

    def outcomes(self, name, *variants):
        cases, _ = _case_modules()
        root = Path(self.td.name) / name
        return _report(cases.positive_case(root, cases.both(*variants)), root)["obligations"]

    def test_outcomes_on_bundle_coverage_are_declaration_based_in_1_1_0(self):
        cases, _ = _case_modules()
        bundled = lambda c: cases.custom_table(c, "differential-flux-x", None, None)  # noqa: E731
        obs = self.outcomes("a", bundled, cases.context_1_1)
        flagged = [o for o in obs if "coverage-contract:differential-flux-x" in o["declarations"]]
        self.assertTrue(flagged)
        self.assertTrue(all(o["declaration_based"] and o["state"] in ("satisfied", "not_applicable") for o in flagged))
        self.assertIn("r-real.description", {o["rule_id"] for o in flagged})
        self.assertNotIn("r-inv.root", {o["rule_id"] for o in flagged})  # reads no coverage
        plugin = self.outcomes("b", cases.context_1_1)  # the plugin's own coverage contract: no flag
        self.assertFalse([o for o in plugin if any(d.startswith("coverage-contract:") for d in o["declarations"])])
        old = self.outcomes("c", bundled)  # a 1.0.0 context keeps its outcomes (P3)
        self.assertFalse([o for o in old if any(d.startswith("coverage-contract:") for d in o["declarations"])])


class BlindingLineage(unittest.TestCase):
    def setUp(self):
        import tempfile
        self.td = tempfile.TemporaryDirectory()
        self.addCleanup(self.td.cleanup)
        self.n = 0

    def blinding(self, project=None, **kw) -> tuple[str, str]:
        _, runs = _case_modules()
        self.n += 1
        post = runs.run_chain(Path(self.td.name) / f"r{self.n}", spec_variant=kw.pop("spec_variant", _blinded), **kw)
        o = next(x for x in post.check(project=project)["obligations"] if x["rule_id"] == "r-run.blinding")
        return o["state"], o["reason"]

    def test_lineage_outcomes(self):
        self.assertEqual(self.blinding(data_status="synthetic"), ("satisfied", "check.blinding_permitted"))
        self.assertEqual(self.blinding(data_status="simulated"), ("satisfied", "check.blinding_permitted"))
        self.assertEqual(self.blinding(project={"allowed_outputs": []}, data_status="published"),
                         ("violated", "check.blinded_result_cited"))
        self.assertEqual(self.blinding(data_status="published"), ("unverified", "check.blinding_policy_unknown"))
        self.assertEqual(self.blinding(with_data=False), ("unverified", "check.lineage_no_data"))

    def test_an_external_data_entry_has_no_dataset_status(self):
        _, runs = _case_modules()
        post = runs.run_chain(Path(self.td.name) / "ext", spec_variant=_blinded)
        post.binding["runs"][0]["inputs"].append({"path": "data/raw.bin", "source": {"external": {"item": "m", "entry": "raw.bin"}}})
        o = next(x for x in post.check(project={"allowed_outputs": []})["obligations"] if x["rule_id"] == "r-run.blinding")
        self.assertEqual((o["state"], o["reason"]), ("unverified", "check.lineage_status_unknown"))

    def test_the_project_list_applies_by_artifact_id_only(self):
        def unblinded(c):
            c.doc("spec")["extension"]["blinding"] = {"blinded": False}
        self.assertEqual(self.blinding(spec_variant=unblinded, data_status="published"), ("not_applicable", "check.not_blinded"))
        spec_id = _spec_id()
        self.assertEqual(self.blinding({"blinded": [spec_id], "allowed_outputs": []}, spec_variant=unblinded,
                                       data_status="published"), ("violated", "check.blinded_result_cited"))
        self.assertEqual(self.blinding({"blinded": ["spec.json", "another-spec"], "allowed_outputs": []},
                                       spec_variant=unblinded, data_status="published"), ("not_applicable", "check.not_blinded"))



class CampaignClosure(unittest.TestCase):
    def setUp(self):
        import tempfile
        self.td = tempfile.TemporaryDirectory()
        self.addCleanup(self.td.cleanup)
        self.n = 0

    def campaign(self, after=None, project=None) -> dict:
        _, runs = _case_modules()
        self.n += 1
        rep = runs.run_campaign(Path(self.td.name) / f"c{self.n}", after=after).check(project=project)
        return {o["rule_id"]: (o["state"], o["reason"]) for o in rep["obligations"] if o["rule_id"].startswith("r-run.")}

    def test_campaign_inputs(self):
        def inputs(edit):
            def after(post, cdir):
                edit(post.binding["campaigns"][0])
            return after
        self.assertEqual(self.campaign()["r-run.campaign"], ("satisfied", "check.campaign_recorded"))
        self.assertEqual(self.campaign(inputs(lambda c: c.pop("inputs")))["r-run.campaign"],
                         ("unverified", "check.campaign_inputs_unbound"))

        def tampered(c):
            c["inputs"][0]["path"] = "recipe.json"  # recipe bytes under the spec's source
        self.assertEqual(self.campaign(inputs(tampered))["r-run.campaign"], ("violated", "check.closure_mismatch"))

        def ghost(c):  # a product of a run the binding does not have: its digest cannot match
            c["inputs"] = [{"path": "results/merged.json", "source": {"product": {"run": "nowhere", "output": "x"}}}]
        self.assertEqual(self.campaign(inputs(ghost))["r-run.campaign"], ("violated", "check.closure_mismatch"))

    def test_a_verified_closure_without_an_analysis_item_is_unverified(self):
        import hashlib
        from contracts.analysis_checks.runs import _campaign_closure
        data = b"upstream product"

        class E:  # one upstream run whose recorded output matches the campaign's input
            items: dict = {}
            view: dict = {}

            def read(self, rel, base=""):
                return data

            def known_bytes(self):
                return set()

            def run(self, rid):
                return {}, {"extension": {"output_hashes": {"out.json": hashlib.sha256(data).hexdigest()}}}, None
        product = {"path": "in.json", "source": {"product": {"run": "run-a", "output": "out.json"}}}
        self.assertEqual(_campaign_closure(E(), {"inputs": [product]})[:2],
                         ("unverified", "check.campaign_closure_no_analysis"))

    def test_a_campaign_result_is_judged_by_its_inputs_lineage(self):
        def blinded(post, cdir):
            pass
        _, runs = _case_modules()
        post = runs.run_campaign(Path(self.td.name) / "b", spec_variant=_blinded)
        o = next(x for x in post.check()["obligations"] if x["rule_id"] == "r-run.blinding")
        self.assertEqual((o["state"], o["reason"]), ("satisfied", "check.blinding_permitted"))
        post.binding["campaigns"][0].pop("inputs")
        o = next(x for x in post.check()["obligations"] if x["rule_id"] == "r-run.blinding")
        self.assertEqual((o["state"], o["reason"]), ("unverified", "check.blinding_label_only"))


def _blinded(c):
    c.doc("spec")["extension"]["blinding"] = {"blinded": True}


def _spec_id() -> str:
    import tempfile
    cases, _ = _case_modules()
    with tempfile.TemporaryDirectory() as td:
        return cases.positive_case(Path(td) / "s", freeze=False).doc("spec")["artifact_id"]


if __name__ == "__main__":
    unittest.main()
