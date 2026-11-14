"""Tests of the shipped eic evidence ledger with core/evidence/ledger.py and render_index.py.
The shipped ledger must pass; mutation tests start from the shipped data, introduce one defect, and assert the
diagnostic. Run from the profile folder: python3 -m unittest discover -s tests -t tests -v"""
import copy
import re
import sys
import unittest
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.parents[2]))
from core.evidence import ledger as vel  # noqa: E402
from core.evidence import render_index as rsi  # noqa: E402

sys.path.insert(0, str(ROOT / "scripts"))
import number_rules as nr  # noqa: E402

NS = "eic"
SOURCES, CLAIMS, INDEX = ROOT / "evidence" / "sources.json", ROOT / "evidence" / "claims.json", ROOT / "evidence" / "index.md"
MODULES = sorted((ROOT / "modules").rglob("*.md"))
CONTENT_MODULES = [p for p in MODULES if p.parent.name in ("facility", "detector")]
# Frozen set (task Q14): S10 and C10-C37 stay as they were added for reference:geometry-cases; the rules below apply
# to every other claim. The locked records S04, S05, C08 and C09 are checked field for field outside these tests.
FROZEN_CLAIMS = {f"eic:C{n:02d}" for n in range(10, 38)}
ATLAS_FIELDS = ("experiment", "subsystem", "quantity", "value", "unit", "kind", "valid_for", "conditions")
KIND_SCOPE = {"requirement": ("eic facility:", "EIC"), "design-target": ("eic facility:", "EIC"),
              "design-value": ("epic:", "ePIC"), "proposal": ("epic:", None)}


def ledger():
    s, c = vel.load_ledger(SOURCES, CLAIMS)
    return copy.deepcopy(s), copy.deepcopy(c)


def today(sources):
    """The latest verification date in the ledger: reproducible, and never earlier than any read."""
    return max(date.fromisoformat(s["verification_date"]) for s in sources if s.get("verification_date") not in (None, "unknown"))


def run(sources, claims):
    return vel.check_ledger(sources, claims, today(sources), 365, NS)


def codes(report, kind="errors"):
    return {e["code"] for e in report[kind]}


def ruled(claims):
    """Claims outside the frozen set."""
    return [c for c in claims if c["id"] not in FROZEN_CLAIMS]


def numeric(claims):
    return [c for c in ruled(claims) if c["numeric_quotation_allowed"]]


def has_performance_word(text):
    return any(word in text.lower() for word in nr.PERFORMANCE_WORDS)


def number_kind_problems(sources, claims):
    """(b) numeric claims are detector_fact with a number_kind; atlas block except for proposals; no
    performance_number outside the frozen set."""
    problems = []
    for c in ruled(claims):
        if "performance_number" in c["claim_types"]:
            problems.append((c["id"], "performance_number outside the frozen set"))
    for c in numeric(claims):
        kind = c["scope"].get("number_kind")
        if c["claim_types"] != ["detector_fact"]:
            problems.append((c["id"], "numeric claim is not typed detector_fact"))
        if kind not in nr.NUMBER_KINDS:
            problems.append((c["id"], f"numeric claim without a valid number_kind: {kind}"))
        elif kind == "proposal" and "atlas" in c:
            problems.append((c["id"], "proposal claim carries an atlas block"))
        elif kind != "proposal" and "atlas" not in c:
            problems.append((c["id"], "numeric claim without an atlas block"))
    for c in ruled(claims):
        if not c["numeric_quotation_allowed"] and ("atlas" in c or c["scope"].get("number_kind")):
            problems.append((c["id"], "non-numeric claim carries a number_kind or an atlas block"))
    return problems


def atlas_problems(sources, claims):
    """(c) atlas blocks: exact fields, kind design, experiment matching the scope, value numbers in the sentence,
    no performance word in the quantity."""
    problems = []
    for c in ruled(claims):
        block = c.get("atlas")
        if block is None:
            continue
        if tuple(sorted(block)) != tuple(sorted(ATLAS_FIELDS)):
            problems.append((c["id"], "atlas block fields differ from the atlas fields"))
            continue
        if block["kind"] != "design":
            problems.append((c["id"], "atlas kind is not design"))
        expected = "EIC" if c["scope"]["text"].lower().startswith("eic facility") else "ePIC"
        if block["experiment"] != expected:
            problems.append((c["id"], f"atlas experiment {block['experiment']} does not match the scope prefix"))
        for value in nr.tokens(str(block["value"])):
            if not nr.contains_number(c["claim"], value):
                problems.append((c["id"], f"atlas value number {value:g} is not in the claim sentence"))
        if has_performance_word(block["quantity"]):
            problems.append((c["id"], "performance word in the atlas quantity"))
    return problems


def read_level_problems(sources, claims):
    """(d) read level of numeric claims: page only when every source is a web page, otherwise full-text."""
    by_id = {s["id"]: s for s in sources}
    problems = []
    for c in numeric(claims):
        web = all(by_id[s].get("formal_status") == "web page" for s in c["source_ids"])
        expected = "page" if web else "full-text"
        if c["verification_strength"] != expected:
            problems.append((c["id"], f"read level {c['verification_strength']}, expected {expected}"))
    return problems


def absence_search_problems(sources, claims):
    """(e) absence_search claims say search-limited and quote no number."""
    problems = []
    for c in ruled(claims):
        if c.get("support_kind") == "absence_search":
            if "search-limited" not in c["scope"]["text"]:
                problems.append((c["id"], "absence_search claim does not say search-limited"))
            if c["numeric_quotation_allowed"]:
                problems.append((c["id"], "absence_search claim allows numeric quotation"))
    return problems


def low_tier_problems(sources, claims):
    """(f) a claim with no Tier 1-2 source is third_party_context or absence_search."""
    tiers = {s["id"]: s["tier"] for s in sources}
    return [(c["id"], f"no Tier 1-2 source but support_kind {c.get('support_kind')}") for c in ruled(claims)
            if min(tiers[s] for s in c["source_ids"]) > 2
            and c.get("support_kind") not in ("third_party_context", "absence_search")]


def performance_word_problems(sources, claims):
    """(g) no numeric claim text contains a performance word."""
    return [(c["id"], "performance word in a numeric claim") for c in numeric(claims) if has_performance_word(c["claim"])]


def kind_scope_problems(sources, claims):
    """(h) number_kind and scope prefix (and atlas experiment) are tied."""
    problems = []
    for c in numeric(claims):
        kind = c["scope"].get("number_kind")
        if kind not in KIND_SCOPE:
            continue
        prefix, experiment = KIND_SCOPE[kind]
        if not c["scope"]["text"].lower().startswith(prefix):
            problems.append((c["id"], f"number_kind {kind} needs scope prefix {prefix}"))
        if experiment and c.get("atlas", {}).get("experiment") != experiment:
            problems.append((c["id"], f"number_kind {kind} needs atlas experiment {experiment}"))
    return problems


def bullet_problems(texts):
    """(a) every bullet of a facility/ or detector/ module cites a full eic:Cnn; General method has no bullets."""
    problems = []
    for name, text in texts.items():
        for number, line in enumerate(text.splitlines(), 1):
            if line.startswith("- ") and not nr.CITATION_PATTERN.search(line):
                problems.append((name, number, "bullet without a full eic:Cnn citation"))
        for number, line in nr.general_method_lines(text):
            if re.match(r"^\s*[-*]\s", line):
                problems.append((name, number, "bullet inside the General method section"))
    return problems


def module_texts():
    return {p.relative_to(ROOT / "modules").as_posix(): p.read_text(encoding="utf-8") for p in CONTENT_MODULES}


LEDGER_RULES = (number_kind_problems, atlas_problems, read_level_problems, absence_search_problems,
                low_tier_problems, performance_word_problems, kind_scope_problems)


class ShippedLedgerTests(unittest.TestCase):
    def test_shipped_ledger_passes(self):
        sources, claims = ledger()
        rep = run(sources, claims)
        self.assertEqual(rep["status"], "pass", rep["errors"] + rep["warnings"])
        self.assertGreaterEqual(rep["counts"]["sources"], 4)
        self.assertGreaterEqual(rep["counts"]["claims"], 6)

    def test_every_source_has_a_level_and_a_verification_date(self):
        for s in ledger()[0]:
            self.assertIn(s["verification_level"], vel.STRENGTH, s["id"])
            self.assertRegex(s["verification_date"], r"^\d{4}-\d{2}-\d{2}$", s["id"])
            self.assertIn("publication_date", s, s["id"])
            self.assertNotEqual(s["publication_date"], s["verification_date"], s["id"])

    def test_no_claim_is_called_measured(self):
        for c in ledger()[1]:
            self.assertNotIn("measured", c["claim"].lower(), c["id"])
            self.assertTrue(c["scope"]["text"], c["id"])
            self.assertTrue(c.get("limitations"), c["id"])

    def test_numeric_claims_have_a_number_kind_and_an_atlas_block(self):
        self.assertEqual(number_kind_problems(*ledger()), [])

    def test_atlas_blocks_follow_the_atlas_fields(self):
        self.assertEqual(atlas_problems(*ledger()), [])

    def test_read_level_of_numeric_claims(self):
        self.assertEqual(read_level_problems(*ledger()), [])

    def test_absence_search_claims_are_search_limited_and_non_numeric(self):
        self.assertEqual(absence_search_problems(*ledger()), [])

    def test_claims_without_a_tier_1_or_2_source_are_context_or_absence(self):
        self.assertEqual(low_tier_problems(*ledger()), [])

    def test_no_performance_word_in_numeric_claims(self):
        self.assertEqual(performance_word_problems(*ledger()), [])

    def test_number_kind_and_scope_are_tied(self):
        self.assertEqual(kind_scope_problems(*ledger()), [])

    def test_module_citations_resolve(self):
        sources, claims = ledger()
        sids, cids = {s["id"] for s in sources}, {c["id"] for c in claims}
        for path in MODULES:
            text = path.read_text(encoding="utf-8")
            for sid in set(re.findall(r"\bS\d\d\b", text)):
                self.assertIn(f"{NS}:{sid}", sids, (path.name, sid))
            for cid in set(re.findall(r"\bC\d\d\b", text)):
                self.assertIn(f"{NS}:{cid}", cids, (path.name, cid))

    def test_facility_and_detector_bullets_each_cite_a_claim(self):
        self.assertGreaterEqual(len(CONTENT_MODULES), 3)
        self.assertEqual(bullet_problems(module_texts()), [])

    def test_facility_claims_cite_facility_sources_and_epic_claims_cite_epic_sources(self):
        _, claims = ledger()
        for c in claims:
            scope = c["scope"]["text"].lower()
            self.assertTrue(scope.startswith("eic facility") or scope.startswith("epic"), c["id"])

    def test_proceedings_source_is_context_only(self):
        sources, claims = ledger()
        s05 = next(s for s in sources if s["id"] == "eic:S05")
        self.assertEqual((s05["tier"], s05["verification_level"]), (3, "abstract+metadata"))
        self.assertIn("osti.gov", s05["url"])
        self.assertIn("10.1051/epjconf/202429503011", s05["dois"])
        citing = [c for c in claims if "eic:S05" in c["source_ids"]]
        self.assertEqual([c["id"] for c in citing], ["eic:C09"])
        self.assertEqual(citing[0]["support_kind"], "third_party_context")
        self.assertFalse(citing[0]["numeric_quotation_allowed"])


class DefectTests(unittest.TestCase):
    def test_namespace_is_required(self):
        sources, claims = ledger()
        sources[0]["id"] = "S01"
        self.assertIn("source.bad_id", codes(run(sources, claims)))

    def test_numeric_quotation_needs_a_read_source(self):
        sources, claims = ledger()
        s = sources[0]
        s["verification_level"] = "metadata-only"
        rep = run(sources, claims)
        self.assertTrue({"claim.stronger_than_sources", "claim.numeric_without_reading"} & codes(rep), rep["errors"])

    def test_claim_cannot_outrank_its_source(self):
        sources, claims = ledger()
        claims[0]["verification_strength"] = "full-text"
        self.assertIn("claim.stronger_than_sources", codes(run(sources, claims)))

    def test_primary_claim_needs_tier_1_or_2(self):
        sources, claims = ledger()
        for s in sources:
            s["tier"] = 3
            s["tier_text"] = "3"
        self.assertIn("claim.no_primary_source", codes(run(sources, claims)))

    def test_future_verification_date_rejected(self):
        sources, claims = ledger()
        sources[0]["verification_date"] = "2099-01-01"
        rep = vel.check_ledger(sources, claims, date(2026, 10, 4), 365, NS)
        self.assertIn("source.future_access_date", codes(rep))


class RuleDefectTests(unittest.TestCase):
    """One injected defect per rule of the task's register 15 (TST-2): each must be reported."""

    def claim(self, claims, cid):
        return next(c for c in claims if c["id"] == cid)

    def assert_reported(self, rule, sources, claims, needle):
        found = rule(sources, claims)
        self.assertTrue(any(needle in message for _, message in found), (rule.__name__, found))

    def test_numeric_claim_without_number_kind(self):
        sources, claims = ledger()
        del self.claim(claims, "eic:C03")["scope"]["number_kind"]
        self.assert_reported(number_kind_problems, sources, claims, "without a valid number_kind")

    def test_numeric_claim_without_atlas_block(self):
        sources, claims = ledger()
        del self.claim(claims, "eic:C03")["atlas"]
        self.assert_reported(number_kind_problems, sources, claims, "without an atlas block")

    def test_performance_number_outside_frozen_set(self):
        sources, claims = ledger()
        self.claim(claims, "eic:C04")["claim_types"] = ["performance_number"]
        self.assert_reported(number_kind_problems, sources, claims, "performance_number outside")

    def test_frozen_claims_are_exempt(self):
        sources, claims = ledger()
        self.assertTrue(any("performance_number" in c["claim_types"] for c in claims if c["id"] in FROZEN_CLAIMS))
        self.assertEqual(number_kind_problems(sources, claims), [])

    def test_atlas_kind_and_experiment(self):
        sources, claims = ledger()
        self.claim(claims, "eic:C03")["atlas"]["kind"] = "achieved"
        self.assert_reported(atlas_problems, sources, claims, "not design")
        sources, claims = ledger()
        self.claim(claims, "eic:C03")["atlas"]["experiment"] = "EIC"
        self.assert_reported(atlas_problems, sources, claims, "does not match the scope prefix")

    def test_atlas_value_not_in_sentence(self):
        sources, claims = ledger()
        self.claim(claims, "eic:C03")["atlas"]["value"] = "1.8"
        self.assert_reported(atlas_problems, sources, claims, "not in the claim sentence")

    def test_atlas_extra_field_and_performance_quantity(self):
        sources, claims = ledger()
        self.claim(claims, "eic:C03")["atlas"]["note"] = "x"
        self.assert_reported(atlas_problems, sources, claims, "fields differ")
        sources, claims = ledger()
        self.claim(claims, "eic:C03")["atlas"]["quantity"] = "momentum resolution"
        self.assert_reported(atlas_problems, sources, claims, "performance word in the atlas quantity")

    def test_numeric_claim_on_a_paper_needs_full_text(self):
        sources, claims = ledger()
        next(s for s in sources if s["id"] == "eic:S01")["formal_status"] = "journal article"
        self.assert_reported(read_level_problems, sources, claims, "expected full-text")

    def test_absence_search_wording_and_numbers(self):
        sources, claims = ledger()
        c = self.claim(claims, "eic:C04")
        c["support_kind"], c["numeric_quotation_allowed"] = "absence_search", True
        self.assert_reported(absence_search_problems, sources, claims, "search-limited")
        self.assert_reported(absence_search_problems, sources, claims, "allows numeric quotation")

    def test_low_tier_claim_must_be_context(self):
        sources, claims = ledger()
        for s in sources:
            if s["id"] == "eic:S01":
                s["tier"] = 3
        self.assert_reported(low_tier_problems, sources, claims, "no Tier 1-2 source")

    def test_performance_word_in_numeric_claim(self):
        sources, claims = ledger()
        self.claim(claims, "eic:C03")["claim"] += " with a field resolution of 1.7"
        self.assert_reported(performance_word_problems, sources, claims, "performance word")

    def test_kind_and_scope_tie(self):
        sources, claims = ledger()
        self.claim(claims, "eic:C03")["scope"]["number_kind"] = "requirement"
        self.assert_reported(kind_scope_problems, sources, claims, "needs scope prefix")

    def test_bullet_without_full_id(self):
        texts = module_texts()
        name = "detector/epic-detector-context.md"
        texts[name] = texts[name].replace("(eic:C01)", "(C01)", 1)
        self.assertTrue(bullet_problems(texts))
        texts = module_texts()
        texts[name] += "\n## General method\n\n- a bullet (eic:C01)\n"
        self.assertTrue(any("General method" in p[2] for p in bullet_problems(texts)))


class RenderTests(unittest.TestCase):
    def test_index_in_sync(self):
        sources, claims = ledger()
        ok, detail = rsi.check_index(INDEX.read_text(encoding="utf-8"), sources, claims)
        self.assertTrue(ok, detail)

    def test_edited_claim_is_detected(self):
        sources, claims = ledger()
        claims[0]["claim"] += " (edited)"
        ok, detail = rsi.check_index(INDEX.read_text(encoding="utf-8"), sources, claims)
        self.assertFalse(ok)
        self.assertIn(claims[0]["id"], detail)


if __name__ == "__main__":
    unittest.main()
