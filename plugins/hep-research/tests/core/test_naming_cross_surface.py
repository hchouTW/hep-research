"""Semantic naming engine, contract and cross-surface parts (spec §12, P3-P4): targets between surfaces, derived shape
histograms, the correlation inventory read from a measurement-spec, glossary identifiers across surfaces, record
deduplication and cross-surface change sets, on synthetic inventories."""
from __future__ import annotations

import hashlib
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from core.naming import engine as E  # noqa: E402
from core.naming.declarations import correlation_inventory  # noqa: E402
from tests.core.test_naming_engine import GLOSSARY, REGISTRY, SURFACES, ent, inv, judge, result  # noqa: E402


def nuisance(name, container, *, targets=None, line=10, file="cards/a.txt"):
    e = ent(name, "N10", "nuisance", container, line, file=file)
    if targets:
        e["targets"] = targets
    return e


def shape(name, file="cards/shapes.root"):
    return ent(name, "N3", "shape_histogram", "/", 0, file=file)


def derived(name, file="cards/shapes.root"):
    return {"surface": "N3", "name": name, "file": file, "container": "/", "kind": "shape-histogram", "derived": True}


class TargetTests(unittest.TestCase):
    def test_missing_down_variation_is_a_pairing_violation(self):
        jes = nuisance("jes", "ch_a", targets=[derived("ttbar_jesUp"), derived("ttbar_jesDown")])
        j = judge(inv("N10", jes), inv("N3", shape("ttbar_jesUp")))
        r = result(j, "jes", "naming.n10.shape-pairing")
        self.assertEqual((r["state"], r["reason_code"]), ("violated", "naming.pair_missing"))
        self.assertIn("ttbar_jesDown", r["issue"])

    def test_without_the_n3_inventory_the_pairing_is_unverified(self):
        jes = nuisance("jes", "ch_a", targets=[derived("ttbar_jesUp"), derived("ttbar_jesDown")])
        r = result(judge(inv("N10", jes)), "jes", "naming.n10.shape-pairing")
        self.assertEqual((r["state"], r["reason_code"]), ("unverified", "naming.inventory_missing"))

    def test_complete_pair_links_the_histograms_to_the_nuisance(self):
        jes = nuisance("jes", "ch_a", targets=[derived("ttbar_jesUp"), derived("ttbar_jesDown")])
        up, down = shape("ttbar_jesUp"), shape("ttbar_jesDown")
        j = judge(inv("N10", jes), inv("N3", up, down))
        self.assertEqual(result(j, "jes", "naming.n10.shape-pairing")["state"], "satisfied")
        self.assertIn({"from": jes["entity_id"], "kind": "shape-histogram"}, up["references"])

    def test_dangling_label_reference(self):
        label = ent("fig:spectrum", "N14", "label", "paper/main.tex", 3, file="paper/main.tex")
        ref = ent("fig:missing", "N14", "label_reference", "paper/main.tex", 5, file="paper/main.tex")
        ref["targets"] = [{"surface": "N14", "name": "fig:missing", "kind": "label", "entity_kind": "label"}]
        r = result(judge(inv("N14", label, ref)), "fig:missing", "naming.common.reference")
        self.assertEqual((r["state"], r["reason_code"]), ("violated", "naming.target_missing"))

    def test_figure_target_needs_the_n2_inventory(self):
        fig = ent("figs/spectrum", "N14", "figure_file", "paper/main.tex", 2, file="paper/main.tex")
        fig["targets"] = [{"surface": "N2", "name": "spectrum.pdf", "kind": "includes"}]
        r = result(judge(inv("N14", fig)), "figs/spectrum", "naming.common.reference")
        self.assertEqual((r["state"], r["reason_code"]), ("unverified", "naming.target_inventory_missing"))


SPEC = {"artifact_type": "measurement-spec", "artifact_id": "ms1", "extension": {"systematics": [
    {"name": "lumi", "correlation_key": "lumi", "era_correlation": "uncorrelated", "nuisance_names": ["lumi_2017", "lumi_2018"]},
    {"name": "jes", "correlation_key": "jes"}, {"name": "jes_flavor", "correlation_key": "jes"},
    {"name": "pileup", "era_correlation": "partial"}]}}


class ScopeTests(unittest.TestCase):
    def test_a_narrowed_scope_never_gives_complete_references(self):
        loop = ent("i", "N1", "local", "f", refs=["a.py:2"], cov=["N1:sub/**"])
        narrowed = inv("N1", loop)
        narrowed["scope_roots"] = ["sub"]
        j = judge(narrowed)
        self.assertEqual((loop["references_status"], loop["contract_level"]), ("partial", "C2"))
        self.assertEqual(result(j, "i", "naming.common.reference")["state"], "unverified")


class DeclarationTests(unittest.TestCase):
    def test_measurement_spec_becomes_the_correlation_inventory(self):
        d = correlation_inventory(SPEC)
        by = {s["id"]: s for s in d["sources"]}
        self.assertEqual(by["lumi"], {"id": "lumi", "correlated": False, "members": ["lumi_2017", "lumi_2018"]})
        self.assertEqual(by["jes"]["members"], ["jes", "jes_flavor"])
        self.assertEqual(d["left_out"], ["pileup"])

    def test_era_decorrelated_names_satisfy(self):
        j = judge(inv("N10", nuisance("lumi_2017", "ch_a"), nuisance("lumi_2018", "ch_b")),
                  declarations={"correlation-inventory": correlation_inventory(SPEC)})
        self.assertEqual(result(j, "lumi_2017", "naming.n10.declared-correlation")["state"], "satisfied")

    def test_one_name_for_two_correlated_systematics_differs(self):
        j = judge(inv("N10", nuisance("jes", "ch_a"), nuisance("jes_flavor", "ch_b")),
                  declarations={"correlation-inventory": correlation_inventory(SPEC)})
        r = result(j, "jes", "naming.n10.declared-correlation")
        self.assertEqual((r["state"], r["reason_code"]), ("violated", "naming.correlated_names_differ"))

    def test_same_name_in_two_channels_of_one_uncorrelated_member_is_not_a_violation(self):
        d = {"declaration": "correlation-inventory", "sources": [{"id": "lumi", "correlated": False, "members": ["lumi"]}]}
        j = judge(inv("N10", nuisance("lumi", "ch_a"), nuisance("lumi", "ch_b", line=11)),
                  declarations={"correlation-inventory": d})
        self.assertEqual(result(j, "lumi", "naming.n10.declared-correlation")["state"], "satisfied")

    def test_other_documents_are_refused(self):
        with self.assertRaises(ValueError):
            correlation_inventory({"artifact_type": "statistical-result"})


GLOSS = {"glossary_version": "1.0.0", "entries": GLOSSARY["entries"] + [
    {"id": "pt", "concept": "transverse momentum", "preferred": {"en": "transverse momentum"},
     "aliases": {"en": ["trans mom"]}, "abbreviations": [], "definition": "momentum transverse to the beam",
     "identifiers": ["pt"]}]}


class GlossaryIdentifierTests(unittest.TestCase):
    def test_other_spelling_of_a_declared_concept_is_caught_on_every_surface(self):
        code = ent("muon_transverse_momentum", "N1", "module_public", "<module>")
        column = ent("mu_pt", "N4", "project_column", "Events", file="data.root")
        j = judge(inv("N1", code), inv("N4", column), glossary=GLOSS)
        r = result(j, "muon_transverse_momentum", "naming.cross.glossary-identifier")
        self.assertEqual((r["state"], r["extra"]["proposed"]), ("violated", "muon_pt"))
        self.assertEqual(result(j, "mu_pt", "naming.cross.glossary-identifier")["state"], "satisfied")
        self.assertEqual(column["meaning"]["concept_id"], "term:pt")

    def test_without_identifiers_the_rule_does_not_apply(self):
        j = judge(inv("N1", ent("muon_transverse_momentum", "N1", "module_public", "<module>")))
        self.assertEqual(result(j, "muon_transverse_momentum", "naming.cross.glossary-identifier")["state"], "not_applicable")


class DedupTests(unittest.TestCase):
    def test_one_record_under_two_keys(self):
        a = ent("A2015", "N15", "bib_key", "refs.bib", 1, file="refs.bib")
        b = ent("B2015", "N15", "bib_key", "refs.bib", 5, file="refs.bib")
        a["meaning"]["concept_id"] = b["meaning"]["concept_id"] = "doi:10.1/x"
        j = judge(inv("N15", a, b))
        r = result(j, "A2015", "naming.n15.duplicate-record")
        self.assertEqual(r["state"], "violated")
        action, _ = E.action_for(r, a, REGISTRY, in_request=True)
        self.assertEqual(action, "fix-with-change-set")  # deduplication is the one rename N15 allows

    def test_other_n15_findings_are_report_only(self):
        a = ent("tmp", "N15", "bib_key", "refs.bib", 1, file="refs.bib")
        r = result(judge(inv("N15", a)), "tmp", "naming.common.forbidden")
        self.assertEqual(E.action_for(r, a, REGISTRY, in_request=True)[0], "report-only")

    def test_reference_and_label_of_one_name_are_not_duplicates(self):
        label = ent("fig:a", "N14", "label", "m.tex", 1, file="m.tex")
        ref = ent("fig:a", "N14", "label_reference", "m.tex", 2, file="m.tex")
        self.assertEqual(result(judge(inv("N14", label, ref)), "fig:a", "naming.common.uniqueness")["state"], "satisfied")


class ReviewRoundThreeTests(unittest.TestCase):
    """Bypasses the third review round of the spec found (R869ec87b88), closed in the engine."""

    def test_dedup_rename_of_one_record_under_two_keys_passes_check_one(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "refs.bib").write_text("@article{B2015,}\n")
            a = ent("A2015", "N15", "bib_key", "refs.bib", 1, file="refs.bib")
            b = ent("B2015", "N15", "bib_key", "refs.bib", 5, file="refs.bib")
            a["meaning"]["concept_id"] = b["meaning"]["concept_id"] = "doi:10.1/x"
            E.classify([a, b], {"N15": ["."]}, SURFACES)
            cs = {"change_set_id": "c", "entity_id": b["entity_id"], "current": "B2015", "proposed": "A2015",
                  "contract_level": "C2", "rename_policy": "dedup-only", "replacements": [], "inventory_digests": {},
                  "source_sha256": {"refs.bib": hashlib.sha256((root / "refs.bib").read_bytes()).hexdigest()},
                  "verify": ["check"], "trigger": {"rule_id": "naming.n15.duplicate-record", "predicate": "uniqueness"}}
            self.assertEqual(E.validate_change_set(cs, [a, b], SURFACES, root, {"N15"})["exit_code"], 0)
            cs["trigger"] = {"rule_id": "naming.common.forbidden", "predicate": "forbidden"}
            out = E.validate_change_set(cs, [a, b], SURFACES, root, {"N15"})
            self.assertEqual((out["exit_code"], out["code"]), (1, "naming.rename_not_dedup"))

    def test_waiver_without_the_line_survives_an_edit_above(self):
        e = ent("tmp", "N1", "local", "f", 7)
        waiver = {"rule_id": "naming.common.forbidden", "entity_ids": [e["entity_id"].rsplit("@", 1)[0]],
                  "reason": "r", "recorded_by": "u"}
        r = result(judge(inv("N1", e), waivers=[waiver]), "tmp", "naming.common.forbidden")
        self.assertEqual(r["reason_code"], "naming.waived")


class CrossSurfaceChangeSetTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "cards").mkdir()
        (self.root / "cards/a.txt").write_text("jes shape 1\n")
        self.sha = hashlib.sha256((self.root / "cards/a.txt").read_bytes()).hexdigest()
        self.jes = nuisance("jes", "ch_a", targets=[derived("ttbar_jesUp"), derived("ttbar_jesDown")])
        self.up, self.down = shape("ttbar_jesUp"), shape("ttbar_jesDown")

    def tearDown(self):
        self.tmp.cleanup()

    def validate(self, replacements, supplied=("N10", "N3")):
        entities = [self.jes] + ([self.up, self.down] if "N3" in supplied else [])
        E.link_targets(entities)
        E.classify(entities, {"N10": ["."], "N3": ["."]}, SURFACES)
        cs = {"change_set_id": "cs1", "entity_id": self.jes["entity_id"], "current": "jes", "proposed": "jes_flavor",
              "contract_level": "C3", "rename_policy": "matrix", "approval": {"required": True, "by": "user", "at": "now"},
              "handoff": {"owner": "hep-statistics", "rerun": ["fit"]}, "replacements": replacements,
              "inventory_digests": {}, "source_sha256": {"cards/a.txt": self.sha}, "verify": ["check"]}
        return E.validate_change_set(cs, entities, SURFACES, self.root, set(supplied))

    def test_nuisance_rename_needs_the_n3_inventory(self):
        out = self.validate([], supplied=("N10",))
        self.assertEqual((out["exit_code"], out["code"]), (3, "naming.inventory_missing"))

    def test_derived_histograms_must_be_renamed_with_the_nuisance(self):
        out = self.validate([{"location": self.up["entity_id"], "old": "ttbar_jesUp", "new": "ttbar_jes_flavorUp"}])
        self.assertEqual((out["exit_code"], out["code"]), (1, "naming.replacement_missing"))

    def test_complete_cross_surface_change_set_passes(self):
        reps = [{"location": x["entity_id"], "old": x["name"], "new": x["name"].replace("jes", "jes_flavor")}
                for x in (self.up, self.down)]
        out = self.validate(reps)
        self.assertEqual(out["exit_code"], 0, out)


if __name__ == "__main__":
    unittest.main()
