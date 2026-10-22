"""v6.3 D07/D08 model part (M2b, suite model-card/v1): the O03 pairings (P1-P3, everything else unsupported), R-AUX
observation use within a joint evaluation, and cross-model sharing, on the synthetic cases CASE-MODEL, MODEL-USAGE and
MODEL-SHARING (tests/contracts/analysis_check_cases.py). V06, V07, V08, V46, V47 and the model parts of V11, V15, V18, V24, V25,
V64. The pyhf-combine adapter confirms structure only (V06), never independence. Synthetic data only.
Cases run on check-context 1.1.0 and the newest 1.1.0 pre-release suites (release R2): the 1.0.0 suites name
r-aux.use 1.0.0, which this checker no longer runs."""
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


def ac():
    from contracts import analysis_check
    return analysis_check


def get(rep, oid):
    return next(o for o in rep["obligations"] if o["obligation_id"] == oid)


def states(rep):
    return {o["obligation_id"]: (o["state"], o["reason"]) for o in rep["obligations"]}


class ModelCase(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.addCleanup(self.td.cleanup)
        self.n = 0

    def root(self) -> Path:
        self.n += 1
        return Path(self.td.name) / f"m{self.n}"

    def run_case(self, variant=None, builder=None):
        root = self.root()
        b = (builder or cases.model_case)(root, cases.both(variant, cases.context_1_1))  # the 1.1.0 rules (release R2)
        view, diags = ac().load_subject(b, root)
        return ac().evaluate(view, diags)

    def test_v06_positive_shared_parameter(self):
        # V06: a shared parameter acts on several channels with one auxiliary observation: satisfied
        rep = self.run_case()
        self.assertEqual((rep["status"], rep["consistency"]), ("complete", "consistent"), states(rep))
        self.assertIn({"id": "model-card", "version": cases.DEV_SUITE}, rep["assessment"]["suites"])
        self.assertEqual(sorted(states(rep)), ["r-aux.use:fit#sr-cr/lumi-2026", "r-model.pairing:sr-cr#lumi",
                                               "r-model.pairing:sr-cr#mu", "r-model.pairing:sr-cr#mu_b",
                                               "r-model.root:mu-fit"])
        lumi = get(rep, "r-model.pairing:sr-cr#lumi")
        self.assertEqual((lumi["state"], lumi["pairing"], lumi["channels"], lumi["constraints"]),
                         ("satisfied", "P3", ["CR", "SR"], 1))
        self.assertEqual(get(rep, "r-model.pairing:sr-cr#mu")["pairing"], "P1")
        self.assertEqual(get(rep, "r-model.pairing:sr-cr#mu_b")["pairing"], "P2")
        self.assertEqual(get(rep, "r-aux.use:fit#sr-cr/lumi-2026")["reason"], "check.aux_single_use")

    def test_v06_consistent_with_the_adapter(self):
        # V06: the adapter's structural mapping agrees: one normsys per shared constrained parameter, one per channel
        sys.path.insert(0, str(ROOT / "adapters" / "pyhf-combine" / "assets"))
        import model_card as mc
        card = cases.sr_cr_card()
        ws = mc.to_pyhf(card)
        mods = [(ch["name"], m["name"], m["type"]) for ch in ws["channels"] for s in ch["samples"] for m in s["modifiers"]]
        self.assertEqual(sorted({ch for ch, n, t in mods if n == "lumi"}), ["CR", "SR"])
        self.assertEqual({t for _, n, t in mods if n == "lumi"}, {"normsys"})
        rep = self.run_case()
        pairing = {o["obligation_id"].split("#")[1]: o for o in rep["obligations"] if o["rule_id"] == "r-model.pairing"}
        self.assertEqual(set(pairing), {n for _, n, _ in mods})
        backend = {"P1": "normfactor", "P2": "normfactor", "P3": "normsys"}
        self.assertEqual({k: backend[o["pairing"]] for k, o in pairing.items()}, {n: t for _, n, t in mods})

    def test_v07_two_aux_ids_one_observation(self):
        # V07: the same observation enters one likelihood under two aux IDs: violated; a missing binding: unverified
        def twice(c):
            card = c.doc("card-sr-cr")
            card["samples"][2]["modifiers"][1] = {"type": "constrained-normalization", "parameter": "lumi_cr"}
            card["constraints"].append({"parameter": "lumi_cr", "kind": "auxiliary-measurement", "aux_id": "lumi-copy",
                                        "form": "gaussian", "width": 0.02})
            c.context["bindings"].append(cases.observes("obs-copy", "sr-cr", "lumi-copy"))
        rep = self.run_case(twice)
        self.assertEqual(states(rep)["r-aux.use:fit#sr-cr/lumi-copy"], ("violated", "check.aux_repeated"))
        self.assertEqual(get(rep, "r-aux.use:fit#sr-cr/lumi-2026")["reason"], "check.aux_repeated")
        self.assertEqual(rep["consistency"], "inconsistent")

        def unbound(c):
            twice(c)
            c.context["bindings"] = c.context["bindings"][:1]
        rep = self.run_case(unbound)
        self.assertEqual(states(rep)["r-aux.use:fit#sr-cr/lumi-copy"], ("unverified", "check.aux_unbound"))
        self.assertEqual(states(rep)["r-aux.use:fit#sr-cr/lumi-2026"], ("unverified", "check.aux_repeat_unknown"))

    def test_v07_same_aux_id_twice(self):
        # one aux_id constraining two parameters is the same observation entering twice
        def dup(c):
            card = c.doc("card-sr-cr")
            card["samples"][2]["modifiers"][1] = {"type": "constrained-normalization", "parameter": "lumi_cr"}
            card["constraints"].append({"parameter": "lumi_cr", "kind": "auxiliary-measurement", "aux_id": "lumi-2026",
                                        "form": "gaussian", "width": 0.02})
        rep = self.run_case(dup)
        self.assertEqual(states(rep)["r-aux.use:fit#sr-cr/lumi-2026"], ("violated", "check.aux_repeated"))

    def test_v08_two_components_of_one_file(self):
        # V08: two different observation components of one file (one digest) are not merged
        def two(c):
            card = c.doc("card-sr-cr")
            card["samples"][0]["modifiers"].append({"type": "constrained-normalization", "parameter": "trig"})
            card["constraints"].append({"parameter": "trig", "kind": "auxiliary-measurement", "aux_id": "trig-2026",
                                        "form": "gaussian", "width": 0.01})
            c.context["bindings"].append(cases.observes("obs-trig", "sr-cr", "trig-2026", pointer="/trigger"))
        rep = self.run_case(two)
        self.assertEqual(states(rep)["r-aux.use:fit#sr-cr/lumi-2026"], ("satisfied", "check.aux_single_use"))
        self.assertEqual(states(rep)["r-aux.use:fit#sr-cr/trig-2026"], ("satisfied", "check.aux_single_use"))
        self.assertEqual(rep["status"], "complete")

        def overlap(c):
            two(c)
            c.context["bindings"][-1]["from"]["pointer"] = ""
        rep = self.run_case(overlap)
        self.assertEqual(states(rep)["r-aux.use:fit#sr-cr/trig-2026"], ("unverified", "check.aux_overlap_unknown"))

    def test_v46_alternative_models_versus_joint(self):
        # V46: alternative models reusing an observation are not a repeat; a joint likelihood multiplying it again is
        rep = self.run_case(lambda c: cases.two_models(c, joint=False))
        self.assertEqual(states(rep)["r-aux.use:fit-a#alt-a/lumi-2026"], ("satisfied", "check.aux_single_use"))
        self.assertEqual(states(rep)["r-aux.use:fit-b#alt-b/lumi-2026"], ("satisfied", "check.aux_single_use"))
        self.assertEqual((rep["status"], rep["consistency"]), ("complete", "consistent"))
        rep = self.run_case(lambda c: cases.two_models(c, joint=True))
        self.assertEqual(states(rep)["r-aux.use:joint#alt-a/lumi-2026"], ("violated", "check.aux_repeated"))
        self.assertEqual(states(rep)["r-share.parameters:joint#combination"], ("unsupported", "check.joint_unsupported"))

        def unknown(c):
            cases.two_models(c, joint=True)
            c.context["bindings"] = c.context["bindings"][:1]
        rep = self.run_case(unknown)
        self.assertEqual(states(rep)["r-aux.use:joint#alt-a/lumi-2026"], ("unverified", "check.aux_repeat_unknown"))
        self.assertEqual(states(rep)["r-aux.use:joint#alt-b/lumi-2026"], ("unverified", "check.aux_unbound"))

    def test_v47_cross_model_sharing(self):
        # V47: incompatible shared parameters: merge rejected; compatible: unsupported (no combiner); unknown: unverified
        rep = self.run_case(lambda c: cases.two_models(c, joint=True, width_b=0.05, shared=cases.shared_lumi()))
        self.assertEqual(states(rep)["r-share.parameters:joint#lumi"], ("violated", "check.share_incompatible"))
        rep = self.run_case(lambda c: cases.two_models(c, joint=True, shared=cases.shared_lumi()))
        self.assertEqual(states(rep)["r-share.parameters:joint#lumi"], ("unsupported", "check.share_unsupported"))
        # one shared constraint term: the observation enters once
        self.assertEqual(states(rep)["r-aux.use:joint#alt-a/lumi-2026"], ("satisfied", "check.aux_single_use"))
        rep = self.run_case(lambda c: cases.two_models(c, joint=True, shared=cases.shared_lumi("lumi_x")))
        self.assertEqual(states(rep)["r-share.parameters:joint#lumi"], ("unverified", "check.share_unbound"))
        self.assertNotEqual(rep["status"], "complete")

    def test_v18_unsupported_pairings(self):
        # V18: an unlisted pairing is unsupported, never a pass inferred from the absence of a legacy finding
        def shape(c):
            c.doc("card-sr-cr")["samples"][0]["modifiers"].append({"type": "shapesys", "parameter": "jes"})
        rep = self.run_case(shape)
        self.assertEqual(states(rep)["r-model.pairing:sr-cr#jes"], ("unsupported", "check.pairing_unsupported"))
        self.assertEqual(rep["input_validity"], "valid")
        self.assertNotEqual(rep["status"], "complete")
        for form in ("poisson", "lognormal"):
            rep = self.run_case(lambda c, form=form: c.doc("card-sr-cr")["constraints"][0].update(form=form))
            self.assertEqual(states(rep)["r-model.pairing:sr-cr#lumi"], ("unsupported", "check.pairing_unsupported"), form)
        rep = self.run_case(lambda c: c.doc("card-sr-cr")["constraints"][0].update(kind="prior"))
        self.assertEqual(states(rep)["r-model.pairing:sr-cr#lumi"], ("unsupported", "check.pairing_unsupported"))
        self.assertEqual(states(rep)["r-aux.use:fit#sr-cr/lumi-2026"], ("not_applicable", "check.aux_prior"))

    def test_pairing_violations(self):
        def unconstrained(c):
            c.doc("card-sr-cr")["constraints"] = []
        rep = self.run_case(unconstrained)
        self.assertEqual(states(rep)["r-model.pairing:sr-cr#lumi"], ("violated", "check.pairing_invalid"))

        def disagree(c):
            for s in c.doc("card-sr-cr")["samples"]:
                for m in s["modifiers"]:
                    if m["parameter"] == "lumi":
                        m.update(hi=1.05, lo=0.95)
        rep = self.run_case(disagree)
        self.assertEqual(states(rep)["r-model.pairing:sr-cr#lumi"], ("violated", "check.pairing_invalid"))

    def test_root_intent(self):
        def wrong_poi(c):
            c.context["model_roots"][0]["poi"]["parameter"] = "mu_b"
        rep = self.run_case(wrong_poi)
        self.assertEqual(states(rep)["r-model.root:mu-fit"], ("violated", "check.model_root_mismatch"))


class ModelVParts(unittest.TestCase):
    """The model parts of V11, V15, V24, V25 and V64."""

    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.addCleanup(self.td.cleanup)

    def check(self, root, variant=None):
        b = cases.model_case(root, cases.both(variant, cases.context_1_1))
        view, diags = ac().load_subject(b, root)
        return ac().evaluate(view, diags)

    def test_v11_missing_observation_binding(self):
        # V11: the obligation is kept and coverage is partial; a deleted frozen file is invalid input
        rep = self.check(Path(self.td.name) / "a", lambda c: c.context.update(bindings=[]))
        self.assertEqual(states(rep)["r-aux.use:fit#sr-cr/lumi-2026"], ("unverified", "check.aux_unbound"))
        self.assertEqual(rep["coverage"]["value"], "partial")
        root = Path(self.td.name) / "b"
        b = cases.model_case(root)
        (root / "models" / "sr_cr.card.json").unlink()
        view, diags = ac().load_subject(b, root)
        rep = ac().evaluate(view, diags)
        self.assertEqual(rep["input_validity"], "invalid")

    def test_v15_renaming_and_reordering(self):
        # V15: renamed files and reordered enumerations keep the verdict and the obligation IDs
        base = self.check(Path(self.td.name) / "a")

        def shuffled(c):
            card = c.doc("card-sr-cr")
            card["samples"].reverse()
            card["channels"].reverse()
            for s in card["samples"]:
                s["modifiers"].reverse()
            for it in c.items:
                if it["id"] == "card-sr-cr":
                    c.files["models/renamed.json"] = c.files.pop(it["ref"])
                    it["ref"] = "models/renamed.json"
        rep = self.check(Path(self.td.name) / "b", shuffled)
        self.assertEqual(states(rep), states(base))
        self.assertEqual(rep["inventory_digest"], base["inventory_digest"])

    def test_v24_masking_a_binding(self):
        # V24: masking a binding keeps every obligation and never raises coverage; removing a listed file fails integrity
        base = self.check(Path(self.td.name) / "a")
        masked = self.check(Path(self.td.name) / "b", lambda c: c.context.update(bindings=[]))
        self.assertEqual(sorted(states(masked)), sorted(states(base)))
        self.assertLessEqual(masked["coverage"]["completed"], base["coverage"]["completed"])
        root = Path(self.td.name) / "c"
        b = cases.model_case(root)
        (root / "aux" / "inputs.json").unlink()
        view, diags = ac().load_subject(b, root)
        self.assertEqual(ac().evaluate(view, diags)["input_validity"], "invalid")

    def test_v25_waiver_not_counted(self):
        # V25: a context declaration that a rule does not apply is not counted
        def waiver(c):
            c.context["bindings"] = []
            c.context["declarations"] = [{"declaration_id": "skip-aux", "type": "not_applicable",
                                          "asserted_by": dict(cases.AGENT), "basis": {"rationale": "trust me"},
                                          "content": {"rule": "r-aux.use"}}]
        rep = self.check(Path(self.td.name) / "a", waiver)
        self.assertEqual(states(rep)["r-aux.use:fit#sr-cr/lumi-2026"], ("unverified", "check.aux_unbound"))
        self.assertIn("declaration.rule_waiver_not_counted", {f["code"] for f in rep["context_findings"]})

    def test_v64_declaration_based_binding(self):
        # V64: an observation bound only by an agent's declaration is flagged and is unverified for formal use
        def declared(c):
            c.context["bindings"] = []
            c.context["declarations"] = [{"declaration_id": "lumi-source", "type": "provenance_binding",
                                          "asserted_by": dict(cases.AGENT),
                                          "basis": {"rationale": "the luminosity constraint encodes this component"},
                                          "content": {"model": "sr-cr", "aux_id": "lumi-2026", "item": "aux-inputs",
                                                      "pointer": "/luminosity"}}]
        rep = self.check(Path(self.td.name) / "a", declared)
        o = get(rep, "r-aux.use:fit#sr-cr/lumi-2026")
        self.assertEqual((o["state"], o["declaration_based"], o["declarations"]), ("satisfied", True, ["lumi-source"]))
        self.assertEqual(rep["formal_use_view"]["coverage"]["value"], "partial")


class ModelBundle(unittest.TestCase):
    def test_roles_and_lock(self):
        from contracts.analysis_bundle import BundleRefused
        with tempfile.TemporaryDirectory() as td:
            c = cases.model_case(Path(td) / "a", freeze=False)
            c.items = [i for i in c.items if i["role"] != "model-card"]
            with self.assertRaises(BundleRefused) as cm:
                c.freeze()
            self.assertEqual(cm.exception.code, "bundle.roles")
            root = Path(td) / "b"
            b = cases.model_case(root)
            lock = json.loads((root / "semantic-lock.json").read_text())
            self.assertIn("pairing-contract", {d["kind"] for d in lock["definitions"]})
            view, diags = ac().load_subject(b, root)
            changed = copy.deepcopy(view)
            changed["pairings"] = dict(view["pairings"], pairings_version="9.9.9")
            rep = ac().evaluate(changed, diags)
            self.assertEqual(get(rep, "r-model.pairing:sr-cr#lumi")["reason"], "check.semantics_unreproducible")


if __name__ == "__main__":
    unittest.main()
