"""The review-question tables that replaced the retired cross-artifact check (hep-measurement "Spec against
implementation", hep-statistics "Ratios of two results") stay usable as hep-review obligations: every row has an ID,
a question, a criterion and the input that makes it undetermined; a row built into an obligation validates against
hep-review's obligation definition; and the method names the tables give are method cards of hep-review. This test only
reads hep-review's files, so a change there shows up here first."""
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from contracts.schema import validate  # noqa: E402

TABLES = {
    "hep-measurement": (ROOT / "skills" / "hep-measurement" / "references" / "review-and-artifacts.md",
                        "## Spec against implementation", "M-"),
    "hep-statistics": (ROOT / "skills" / "hep-statistics" / "references" / "combinations.md",
                       "## Ratios of two results", "S-RATIO-"),
}
METHOD_CARDS = ROOT / "skills" / "hep-review" / "references" / "domains" / "index.md"


def section(path: Path, heading: str) -> str:
    text = path.read_text(encoding="utf-8")
    start = text.index(heading)
    nxt = text.find("\n## ", start + len(heading))
    return text[start:] if nxt < 0 else text[start:nxt]


def rows(body: str, prefix: str) -> list[list[str]]:
    out = []
    for line in body.splitlines():
        cells = [c.strip() for c in re.split(r"(?<!\\)\|", line.strip())[1:-1]]
        if cells and cells[0].startswith(prefix):
            out.append(cells)
    return out


def method_cards() -> set[str]:
    body = section(METHOD_CARDS, "## Method cards")
    firsts = (ln.strip().split("|")[1].strip() for ln in body.splitlines() if ln.startswith("|"))
    return {c for c in firsts if c and c != "Method" and not set(c) <= {"-"}}


class ReviewQuestionTables(unittest.TestCase):
    def test_every_row_is_complete_and_ids_are_unique(self):
        for owner, (path, heading, prefix) in TABLES.items():
            got = rows(section(path, heading), prefix)
            with self.subTest(owner=owner):
                self.assertGreaterEqual(len(got), 3)
                self.assertEqual(len({r[0] for r in got}), len(got))
                for r in got:
                    self.assertEqual(len(r), 4, r)
                    self.assertTrue(all(r), r)
                    self.assertTrue(r[1].endswith("?"), r[1])

    def test_rows_validate_as_hep_review_obligations(self):
        for owner, (path, heading, prefix) in TABLES.items():
            for oid, question, criterion, missing in rows(section(path, heading), prefix):
                ob = {"id": oid, "origin_requirement_ids": ["req-1"], "question": question, "targets": ["mat-1"],
                      "domain_refs": [owner], "criterion": criterion, "assumptions": [], "tolerances": [],
                      "adoption_policy": {"second_method_required": False, "verification_required": False,
                                          "qualifications": []},
                      "required_methods": ["assumption and convention check"],
                      "evidence_requirements": [f"the element named; if missing: {missing}"],
                      "independence_requirements": [], "required": True, "decision_required": False}
                rep = validate(ob, {"$ref": "hep_review_definitions.json#/$defs/obligation"}, doc_name="hep_review_plan.json")
                with self.subTest(obligation=oid):
                    self.assertTrue(rep.ok, [f.as_dict() for f in rep.errors])

    def test_named_methods_are_hep_review_method_cards(self):
        cards = method_cards()
        self.assertIn("assumption and convention check", cards)
        for owner, (path, heading, _) in TABLES.items():
            text = re.sub(r"\s+", " ", section(path, heading))
            for name in re.findall(r'the methods? "([^"]+)"(?: \(plus "([^"]+)")?', text):
                for method in filter(None, name):
                    with self.subTest(owner=owner, method=method):
                        self.assertIn(method, cards)


if __name__ == "__main__":
    unittest.main()
