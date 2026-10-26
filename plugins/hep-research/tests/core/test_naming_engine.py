"""Semantic naming engine (core/naming; spec §12): tokenizer, the predicates, waivers, contract levels, reporting scope,
disposition and change-set validation, on synthetic inventories."""
from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from contracts.rule_registry import state_for  # noqa: E402
from core.naming import engine as E  # noqa: E402
from core.naming.model import new_entity, new_inventory  # noqa: E402
from core.naming.tokens import tokenize  # noqa: E402
from core.naming.vocab import Vocabulary  # noqa: E402

RULES = json.loads((ROOT / "contracts/naming/rules.json").read_text())["rules"]
SURFACES = json.loads((ROOT / "contracts/naming/surfaces.json").read_text())["surfaces"]
REGISTRY = {s["surface_id"]: s for s in SURFACES}
X = {"id": "test", "version": "1.0.0"}
GLOSSARY = {"glossary_version": "1.0.0", "entries": [
    {"id": "term:tmp", "concept": "temperature", "preferred": {"en": "temperature"}, "aliases": {"en": ["tmp"]},
     "definition": "detector temperature", "abbreviations": [], "identifiers": ["tmp"]}]}


def ent(name, surface="N1", kind="local", container="f", line=1, *, file="a.py", change="added", refs=(), cov=None,
        source="project", status=None, ref_kind="in-scope"):
    cov = [f"{surface}:**"] + [f"{s['surface']}:**" for s in REGISTRY[surface]["referenced_by"]] if cov is None else cov
    return new_entity(surface, kind, name, file, container, (line, line), source=source, content=f"{name}@{line}",
                      extractor=X, references=[{"from": r, "kind": ref_kind} for r in refs], search_coverage=cov,
                      change=change, meaning={"status_label": status} if status else None)


def inv(surface, *entities, scanned=1):
    return new_inventory(surface, ["."], scanned, list(entities), "2026-10-26T00:00:00Z")


def judge(*inventories, glossary=None, **kw):
    kw.setdefault("report_all", True)
    return E.judge(list(inventories), RULES, SURFACES, vocab=Vocabulary(glossary), state_for=state_for, **kw)


def result(j, name, rule_id, idx=0):
    hits = [r for r in j["results"] if r["rule_id"] == rule_id and r["entity_id"]
            and j["context"].by_id[r["entity_id"]]["name"] == name]
    return hits[idx]


class TokenizerTests(unittest.TestCase):
    def test_spec_cases(self):
        vocab = Vocabulary()
        cases = {"chi2": ["chi2"], "p4": ["p4"], "TH1D": ["TH1D"], "DataLoader": ["DataLoader"],
                 "kElectronMassGeV": ["electron", "mass", "GeV"], "fig:rigidity_spectrum": ["rigidity", "spectrum"]}
        for name, want in cases.items():
            self.assertEqual(tokenize(name, vocab.protected()), want, name)
        self.assertEqual(tokenize("data_obs", vocab.protected(["data_obs"])), ["data_obs"])

    def test_protected_words_only_at_boundaries(self):
        self.assertEqual(tokenize("script_pt", Vocabulary().protected()), ["script", "pt"])
        self.assertEqual(tokenize("dimuon", Vocabulary().protected()), ["dimuon"])


class ForbiddenTests(unittest.TestCase):
    def test_violations(self):
        j = judge(inv("N1", ent("process_data", line=1), ent("tmp_data", line=2)))
        self.assertEqual(result(j, "process_data", "naming.common.forbidden")["state"], "violated")
        self.assertEqual(result(j, "tmp_data", "naming.common.forbidden")["state"], "violated")

    def test_not_violations(self):
        j = judge(inv("N1", ent("mass_dimuon_sr_data"), ent("DataLoader", kind="module_public", container="<module>", line=3)),
                  inv("N10", ent("data_obs", surface="N10", kind="observed_data", container="ch", file="card.txt")))
        for name in ("mass_dimuon_sr_data", "DataLoader", "data_obs"):
            self.assertEqual(result(j, name, "naming.common.forbidden")["state"], "satisfied", name)

    def test_glossary_never_overrides_the_table(self):
        j = judge(inv("N1", ent("data_tmp")), glossary=GLOSSARY)
        self.assertEqual(result(j, "data_tmp", "naming.common.forbidden")["state"], "violated")


class WaiverTests(unittest.TestCase):
    def test_explicit_entity_id_waives(self):
        e = ent("tmp")
        j = judge(inv("N1", e), waivers=[{"rule_id": "naming.common.forbidden", "entity_ids": [e["entity_id"]],
                                          "reason": "r", "recorded_by": "u"}])
        r = result(j, "tmp", "naming.common.forbidden")
        self.assertEqual((r["state"], r["reason_code"]), ("not_applicable", "naming.waived"))

    def test_pattern_waiver_is_rejected_by_the_schema(self):
        from contracts.schema import validate
        cfg = {"schema_version": "1.3.0", "plugin_version": ">=0.1", "naming": {"waivers": [
            {"rule_id": "naming.common.forbidden", "entity_ids": ["N1:*#*/tmp@*"], "reason": "r", "recorded_by": "u"}]}}
        self.assertFalse(validate(cfg, "project_config.json").ok)

    def test_non_waivable_rule_ignores_a_waiver(self):
        e = ent("final_spectrum", surface="N2", kind="output", container=".", file="final_spectrum.pdf", status="preliminary")
        j = judge(inv("N2", e), waivers=[{"rule_id": "naming.common.status-honesty", "entity_ids": [e["entity_id"]],
                                          "reason": "r", "recorded_by": "u"}])
        self.assertEqual(result(j, "final_spectrum", "naming.common.status-honesty")["state"], "violated")


class DeclaredCorrelationTests(unittest.TestCase):
    """N10: a name is a correlation (F14); the declaration decides, never the spelling (I1)."""

    def nuis(self, name, channel, line):
        return ent(name, surface="N10", kind="nuisance", container=channel, line=line, file=f"cards/{channel}.txt")

    def decl(self, *sources):
        return {"correlation-inventory": {"declaration": "correlation-inventory", "sources": [
            {"id": sid, "correlated": corr, "members": members} for sid, corr, members in sources]}}

    def test_declared_correlated_named_differently(self):
        j = judge(inv("N10", self.nuis("lumi_2018", "a", 1), self.nuis("lumi2018", "b", 2)),
                  declarations=self.decl(("lumi", True, ["a/lumi_2018", "b/lumi2018"])))
        r = result(j, "lumi2018", "naming.n10.declared-correlation")
        self.assertEqual((r["state"], r["reason_code"]), ("violated", "naming.correlated_names_differ"))

    def test_declared_uncorrelated_named_the_same(self):
        j = judge(inv("N10", self.nuis("lumi", "a", 1), self.nuis("lumi", "b", 2)),
                  declarations=self.decl(("lumi-a", True, ["a/lumi"]), ("lumi-b", True, ["b/lumi"])))
        self.assertEqual(result(j, "lumi", "naming.n10.declared-correlation")["reason_code"], "naming.decorrelated_names_equal")

    def test_declared_decorrelated_years(self):
        j = judge(inv("N10", self.nuis("lumi_2017", "a", 1), self.nuis("lumi_2018", "b", 2)),
                  declarations=self.decl(("lumi-2017", True, ["a/lumi_2017"]), ("lumi-2018", True, ["b/lumi_2018"])))
        self.assertEqual(result(j, "lumi_2017", "naming.n10.declared-correlation")["state"], "satisfied")

    def test_near_duplicate_without_declaration_is_a_question(self):
        j = judge(inv("N10", self.nuis("lumi_2018", "a", 1), self.nuis("lumi2018", "b", 2)))
        r = result(j, "lumi2018", "naming.n10.near-duplicate")
        self.assertEqual(r["state"], "unverified")
        self.assertIsNone(r["extra"].get("proposed"))
        self.assertEqual(result(j, "lumi2018", "naming.n10.declared-correlation")["reason_code"], "naming.declaration_missing")

    def test_near_duplicate_resolved_by_declaration_or_annotation(self):
        a, b = self.nuis("lumi_2018", "a", 1), self.nuis("lumi2018", "b", 2)
        j = judge(inv("N10", a, b), declarations=self.decl(("x", True, ["a/lumi_2018"]), ("y", True, ["b/lumi2018"])))
        self.assertEqual(result(j, "lumi2018", "naming.n10.near-duplicate")["reason_code"], "naming.declared_distinct")
        ann = {b["entity_id"]: {"entity_id": b["entity_id"], "confidence": "high", "evidence": [], "referrers_read": [],
                                "intended_distinct": [a["entity_id"]], "recorded_by": "u"}}
        j = judge(inv("N10", a, b), annotations=ann)
        self.assertEqual(result(j, "lumi2018", "naming.n10.near-duplicate")["reason_code"], "naming.annotated_distinct")

    def test_heuristic_rule_never_violates(self):
        rule = next(r for r in RULES if r["predicate"] == "similarity")
        self.assertEqual(rule["outcome_contract"]["violated"], [])


class PairingAndStatusTests(unittest.TestCase):
    def test_shape_histogram_with_only_up(self):
        h = ent("ttbar_jesUp", surface="N3", kind="shape_histogram", container="shapes.root", file="shapes.root")
        j = judge(inv("N3", h), inv("N10", scanned=1))
        self.assertEqual(result(j, "ttbar_jesUp", "naming.n3.shape-pairing")["state"], "violated")
        d = ent("ttbar_jesDown", surface="N3", kind="shape_histogram", container="shapes.root", file="shapes.root", line=2)
        j = judge(inv("N3", h, d), inv("N10", scanned=1))
        self.assertEqual(result(j, "ttbar_jesUp", "naming.n3.shape-pairing")["state"], "satisfied")

    def test_status_honesty(self):
        f = ent("final_spectrum.pdf", surface="N2", kind="output", container=".", file="final_spectrum.pdf", status="preliminary")
        j = judge(inv("N2", f))
        self.assertEqual(result(j, "final_spectrum.pdf", "naming.common.status-honesty")["state"], "violated")
        g = ent("final_spectrum.pdf", surface="N2", kind="output", container=".", file="final_spectrum.pdf")
        j = judge(inv("N2", g))
        self.assertEqual(result(j, "final_spectrum.pdf", "naming.common.status-honesty")["state"], "unverified")


class SemanticTests(unittest.TestCase):
    def ann(self, e, confidence, verdict="consistent", read=None):
        return {e["entity_id"]: {"entity_id": e["entity_id"], "semantic_verdict": verdict, "confidence": confidence,
                                 "evidence": ["a.py:1-9"], "recorded_by": "agent",
                                 "referrers_read": [r["from"] for r in e["references"]] if read is None else read}}

    def test_low_or_medium_is_unverified(self):
        e = ent("apply_cuts", refs=["a.py:5"])
        for c in ("low", "medium"):
            self.assertEqual(result(judge(inv("N1", e), annotations=self.ann(e, c)), "apply_cuts",
                                    "naming.common.semantic")["state"], "unverified")

    def test_high_decides(self):
        e = ent("apply_cuts", refs=["a.py:5"])
        self.assertEqual(result(judge(inv("N1", e), annotations=self.ann(e, "high")), "apply_cuts",
                                "naming.common.semantic")["state"], "satisfied")
        self.assertEqual(result(judge(inv("N1", e), annotations=self.ann(e, "high", "inconsistent")), "apply_cuts",
                                "naming.common.semantic")["state"], "violated")

    def test_high_without_every_referrer_read_is_unverified(self):
        e = ent("apply_cuts", refs=["a.py:5", "b.py:7"], ref_kind="uses")
        r = result(judge(inv("N1", e), annotations=self.ann(e, "high", read=["a.py:5"])), "apply_cuts", "naming.common.semantic")
        self.assertEqual((r["state"], r["reason_code"]), ("unverified", "naming.confidence_unsupported"))


class LevelTests(unittest.TestCase):
    def test_loop_index_is_c0(self):
        j = judge(inv("N1", ent("i", refs=["a.py:2"])))
        self.assertEqual(j["context"].by_id[j["entities"][0]["entity_id"]]["contract_level"], "C0")

    def test_unsearched_do_something(self):
        e = ent("do_something", cov=[])
        j = judge(inv("N1", e))
        r = result(j, "do_something", "naming.common.forbidden")
        self.assertEqual(r["state"], "violated")
        ent_ = j["context"].by_id[e["entity_id"]]
        self.assertEqual((ent_["references_status"], ent_["contract_level"]), ("not_searched", "C2"))
        action, _ = E.action_for(r, ent_, REGISTRY, in_request=True)
        self.assertNotEqual(action, "fix")

    def test_external_branch_is_c4(self):
        b = ent("muPt", surface="N4", kind="project_column", container="Events", source="external", file="nt.root")
        j = judge(inv("N4", b))
        self.assertEqual(j["entities"][0]["contract_level"], "C4")

    def test_c3_violation_is_proposed_with_handoff(self):
        n = ent("tmp", surface="N10", kind="nuisance", container="a", file="card.txt")
        j = judge(inv("N10", n))
        r = result(j, "tmp", "naming.common.forbidden")
        action, handoff = E.action_for(r, j["entities"][0], REGISTRY, in_request=True)
        self.assertEqual(action, "propose-then-change-set-after-approval")
        self.assertEqual(handoff["owner"], "hep-statistics")

    def test_fix_outside_the_request_becomes_a_proposal(self):
        e = ent("tmp", change="unchanged")
        j = judge(inv("N1", e))
        r = result(j, "tmp", "naming.common.forbidden")
        self.assertEqual(E.action_for(r, j["entities"][0], REGISTRY, in_request=False)[0], "propose")


class IdentityAndScopeTests(unittest.TestCase):
    def test_same_name_twice_in_a_container(self):
        a = ent("fit", kind="module_public", container="<module>", line=3)
        b = ent("fit", kind="module_public", container="<module>", line=30)
        self.assertNotEqual(a["entity_id"], b["entity_id"])
        self.assertEqual(result(judge(inv("N1", a, b)), "fit", "naming.common.uniqueness")["state"], "violated")

    def test_removed_name_still_referenced_is_reported(self):
        gone = ent("old_api", kind="module_public", container="<module>", change="removed", refs=["b.py:4"], ref_kind="uses")
        keep = ent("caller", kind="module_public", container="<module>", file="b.py", line=2, change="unchanged")
        j = judge(inv("N1", gone, keep), report_all=False)
        r = [x for x in j["reported"] if x["rule_id"] == "naming.common.reference"]
        self.assertEqual([x["state"] for x in r], ["violated"])
        self.assertEqual(r[0]["extra"]["locations"], ["b.py:4"])

    def test_modified_body_goes_to_semantic_review(self):
        e = ent("fit", change="modified")
        self.assertEqual(result(judge(inv("N1", e)), "fit", "naming.common.semantic")["reason_code"], "naming.not_reviewed")

    def test_zero_inputs_and_expected_surfaces_are_unsupported(self):
        j = judge(inv("N1", scanned=0), expect=["N3"])
        states = {(r["surface"], r["state"]) for r in j["results"]}
        self.assertIn(("N1", "unsupported"), states)
        self.assertIn(("N3", "unsupported"), states)


class ChangeSetTests(unittest.TestCase):
    def setUp(self):
        self.workdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.workdir.cleanup)
        self.root = Path(self.workdir.name)
        (self.root / "a.py").write_text("def process_data():\n    pass\n")
        (self.root / "b.py").write_text("from a import process_data\nprocess_data()\n")
        self.e = ent("process_data", kind="module_public", container="<module>", refs=["b.py:1", "b.py:2"], ref_kind="uses")

    def digest(self, name):
        return hashlib.sha256((self.root / name).read_bytes()).hexdigest()

    def change_set(self, **kw):
        cs = {"change_set_id": "cs1", "entity_id": self.e["entity_id"], "current": "process_data",
              "proposed": "apply_selection_cuts", "contract_level": "C2", "rename_policy": "matrix",
              "replacements": [{"location": loc, "old": "process_data", "new": "apply_selection_cuts"}
                               for loc in ("a.py:1", "b.py:1", "b.py:2")],
              "inventory_digests": {}, "source_sha256": {"a.py": self.digest("a.py"), "b.py": self.digest("b.py")},
              "verify": ["naming_check.py check"]}
        cs.update(kw)
        return cs

    def validate(self, cs, entities=None, supplied=("N1",)):
        ents = entities or [self.e]
        E.classify(ents, {"N1": ["."]}, SURFACES)
        return E.validate_change_set(cs, ents, SURFACES, self.root, set(supplied))

    def test_valid(self):
        self.assertEqual(self.validate(self.change_set())["exit_code"], 0)

    def test_missing_inventory_of_a_referring_surface(self):
        f = ent("plot.pdf", surface="N2", kind="output", container=".", file="plot.pdf")
        cs = self.change_set(entity_id=f["entity_id"], current="plot.pdf", replacements=[{"location": "x", "old": "a", "new": "b"}])
        ents = [f]
        E.classify(ents, {"N2": ["."]}, SURFACES)
        out = E.validate_change_set(cs, ents, SURFACES, self.root, {"N2"})
        self.assertEqual((out["exit_code"], out["check"]), (3, 3))

    def test_stale_source(self):
        cs = self.change_set()
        (self.root / "b.py").write_text("changed\n")
        self.assertEqual(self.validate(cs)["exit_code"], 3)

    def test_not_every_reference_replaced(self):
        out = self.validate(self.change_set(replacements=[{"location": "b.py:1", "old": "process_data", "new": "x"}]))
        self.assertEqual((out["exit_code"], out["check"]), (1, 5))

    def test_c4_entity(self):
        e = ent("muPt", surface="N4", kind="project_column", container="Events", source="external")
        ents = [e]
        E.classify(ents, {"N4": ["."]}, SURFACES)
        out = E.validate_change_set(self.change_set(entity_id=e["entity_id"]), ents, SURFACES, self.root, {"N4"})
        self.assertEqual((out["exit_code"], out["check"]), (1, 1))

    def test_c3_needs_approval(self):
        n = ent("lumi", surface="N10", kind="nuisance", container="a", file="a.py", refs=[], ref_kind="uses")
        ents = [n]
        E.classify(ents, {"N10": ["."]}, SURFACES)
        cs = self.change_set(entity_id=n["entity_id"], replacements=[{"location": "a.py:1", "old": "lumi", "new": "lumi_2018"}])
        out = E.validate_change_set(cs, ents, SURFACES, self.root, {"N10", "N3"})
        self.assertEqual((out["exit_code"], out["code"]), (1, "naming.approval_missing"))
        cs["approval"] = {"required": True, "by": "user", "at": "2026-10-26"}
        self.assertEqual(E.validate_change_set(cs, ents, SURFACES, self.root, {"N10", "N3"})["exit_code"], 0)


if __name__ == "__main__":
    unittest.main()
