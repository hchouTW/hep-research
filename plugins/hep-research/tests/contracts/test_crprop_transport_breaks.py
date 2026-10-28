"""cr-propagation B1X (decision A1.7, still contracts 3.14.0 with validate.CRPROP_FROM; acceptance B1X-1): the transport
block can express a high break (R_break_gv, delta_above, s) next to the low break, the local bubble radius and the
source beta exponent.

Criteria fixed before the change (VALIDATION.md, CRPROP-B1X): a block with a high break validates (positive fixture
theory_spec_crprop_high_break.json); a half-specified break is refused with theory.transport_break_incomplete and a
break of unknown kind with theory.transport_break_kind_unknown (one negative fixture each); both rules apply natively
from CRPROP_FROM only, to an older artifact only under --strict; no committed theory-spec gets a new finding, default
or strict (the A2-1 comparison). All SYNTHETIC."""
import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from contracts import validate as v  # noqa: E402

ART = ROOT / "contracts" / "fixtures" / "artifacts"
CASES = json.loads((ART / "cases.json").read_text())
HIGH = json.loads((ART / "valid" / "theory_spec_crprop_high_break.json").read_text())
B1X_CODES = {"theory.transport_break_incomplete", "theory.transport_break_kind_unknown"}


def codes(rep, level="error"):
    return {f.code for f in rep.findings if f.severity == level}


def with_breaks(breaks, version=v.CRPROP_FROM):
    doc = copy.deepcopy(HIGH)
    doc["contract_version"] = version
    doc["versions"]["contracts"] = version
    doc["extension"]["transport"]["diffusion"]["breaks"] = breaks
    return doc


LOW = {"kind": "low", "R_break_gv": 5.0, "delta_below": 0.15, "s": 0.05, "s_convention": "usine"}
HIGH_BREAK = {"kind": "high", "R_break_gv": 300.0, "delta_above": 0.3, "s": 0.05, "s_convention": "usine"}


class HighBreak(unittest.TestCase):
    def test_positive_fixture(self):
        tr = HIGH["extension"]["transport"]
        self.assertEqual([b["kind"] for b in tr["diffusion"]["breaks"]], ["low", "high"])
        self.assertIn("delta_above", tr["diffusion"]["breaks"][1])
        self.assertIn("local_bubble_radius_kpc", tr["geometry"])
        self.assertIn("eta", tr["sources"]["injection"][0])
        for strict in (False, True):
            rep = v.validate_artifact(HIGH, strict=strict)
            self.assertTrue(rep.ok, rep.as_dict())
            self.assertFalse(codes(rep) & B1X_CODES)

    def test_high_break_alone_validates(self):
        self.assertTrue(v.validate_artifact(with_breaks([HIGH_BREAK])).ok)

    def test_half_specified_breaks_are_refused(self):
        cases = {
            "high without delta_above": {k: x for k, x in HIGH_BREAK.items() if k != "delta_above"},
            "high without s": {k: x for k, x in HIGH_BREAK.items() if k != "s"},
            "high with the slope of a low break": dict({k: x for k, x in HIGH_BREAK.items() if k != "delta_above"},
                                                       delta_below=0.3),
            "high with both slopes": dict(HIGH_BREAK, delta_below=0.1),
            "low without delta_below": {k: x for k, x in LOW.items() if k != "delta_below"},
            "low with delta_above": dict(LOW, delta_above=0.2),
        }
        for why, brk in cases.items():
            with self.subTest(why):
                rep = v.validate_artifact(with_breaks([LOW, brk] if brk["kind"] == "high" else [brk]))
                self.assertIn("theory.transport_break_incomplete", codes(rep), rep.as_dict())

    def test_non_number_slope_is_a_schema_error(self):
        rep = v.validate_artifact(with_breaks([dict(HIGH_BREAK, delta_above=True)]))
        self.assertIn("schema.type", codes(rep))

    def test_unknown_kind(self):
        rep = v.validate_artifact(with_breaks([dict(HIGH_BREAK, kind="middle")]))
        self.assertEqual(codes(rep) & B1X_CODES, {"theory.transport_break_kind_unknown"})

    def test_schema_keeps_the_canonical_names(self):
        doc = with_breaks([dict(HIGH_BREAK, slope_above=0.3)])
        self.assertIn("schema.additional", codes(v.validate_artifact(doc)))
        doc = copy.deepcopy(HIGH)
        doc["extension"]["transport"]["geometry"]["local_bubble_radius_kpc"] = -0.1
        self.assertFalse(v.validate_artifact(doc).ok)


class NegativeFixtures(unittest.TestCase):
    def test_each_code_has_one_negative_fixture(self):
        for code in sorted(B1X_CODES):
            with self.subTest(code):
                names = [n for n, c in CASES["invalid"].items() if code in c]
                self.assertEqual(len(names), 1, names)
                rep = v.validate_artifact(json.loads((ART / "invalid" / names[0]).read_text()))
                self.assertEqual(codes(rep), {code}, rep.as_dict())


class Gating(unittest.TestCase):
    """Native from CRPROP_FROM (no new gate); an older artifact gets the rules only under --strict."""

    def test_older_artifact_keeps_its_outcome(self):
        for name in ("theory_crprop_high_break_incomplete.json", "theory_crprop_break_kind_unknown.json"):
            doc = json.loads((ART / "invalid" / name).read_text())
            self.assertTrue(codes(v.validate_artifact(doc)) & B1X_CODES)
            for version in ("3.13.0", v.THEORY_SEMANTICS_FROM):
                with self.subTest(name=name, version=version):
                    old = copy.deepcopy(doc)
                    old["contract_version"] = version
                    old["versions"]["contracts"] = version
                    self.assertFalse(codes(v.validate_artifact(old)) & B1X_CODES)
                    self.assertTrue(codes(v.validate_artifact(old, strict=True)) & B1X_CODES)


class CommittedSpecsUnchanged(unittest.TestCase):
    """A2-1 rerun for B1X: no committed theory-spec outside the B1X fixtures gets a B1X finding, default or strict (the
    full before/after table is in VALIDATION.md, CRPROP-B1X)."""

    def test_no_new_finding(self):
        own = {"theory_spec_crprop_high_break.json", "theory_crprop_high_break_incomplete.json",
               "theory_crprop_break_kind_unknown.json"}
        seen = 0
        for base in ("contracts/fixtures", "examples", "profiles"):
            for p in sorted((ROOT / base).rglob("*.json")):
                if p.name in own:
                    continue
                try:
                    doc = json.loads(p.read_text())
                except ValueError:
                    continue
                if not (isinstance(doc, dict) and doc.get("artifact_type") == "theory-spec"):
                    continue
                seen += 1
                for strict in (False, True):
                    with self.subTest(path=str(p.relative_to(ROOT)), strict=strict):
                        self.assertFalse(codes(v.validate_artifact(doc, strict=strict)) & B1X_CODES)
        self.assertGreater(seen, 0)


if __name__ == "__main__":
    unittest.main()
