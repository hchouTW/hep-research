"""cr-propagation A2 (contracts 3.14.0, validate.CRPROP_FROM; plan r3 sections A2 and 5.4): the optional theory-spec
transport block and object-form degenerate_directions entries.

Criteria fixed before the change (VALIDATION.md, CRPROP-A2): an object entry with a combination is not blank for
theory.degeneracy_missing (A2-3); the rules theory.degeneracy_evidence_missing, theory.degeneracy_range_missing and
theory.degeneracy_evidence_unknown each have a negative fixture (A2-2) and apply natively from CRPROP_FROM only, to
older artifacts only under --strict (A2-5); no committed theory-spec gets a new finding (A2-1). All SYNTHETIC."""
import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from contracts import validate as v  # noqa: E402
from contracts.semver import parse  # noqa: E402

ART = ROOT / "contracts" / "fixtures" / "artifacts"
CASES = json.loads((ART / "cases.json").read_text())
OBJECT_SPEC = json.loads((ART / "valid" / "theory_spec_crprop_object_degeneracy.json").read_text())
NEW_CODES = {"theory.degeneracy_evidence_missing", "theory.degeneracy_range_missing", "theory.degeneracy_evidence_unknown"}


def codes(rep, level="error"):
    return {f.code for f in rep.findings if f.severity == level}


def at_version(doc, version):
    doc = copy.deepcopy(doc)
    doc["contract_version"] = version
    doc["versions"]["contracts"] = version
    return doc


def with_entries(entries, version=v.CRPROP_FROM):
    doc = at_version(OBJECT_SPEC, version)
    doc["extension"]["degenerate_directions"] = entries
    return doc


class TransportBlock(unittest.TestCase):
    def test_plan_example_validates(self):
        rep = v.validate_artifact(OBJECT_SPEC)
        self.assertTrue(rep.ok, rep.as_dict())
        self.assertFalse({f.code for f in rep.findings if f.code.startswith("theory.")}, rep.as_dict())

    def test_parameter_blocks_take_canonical_names_only(self):
        for block, key in (("geometry", "L"), ("diffusion", "D0"), ("reacceleration", "vA"), ("convection", "Vc")):
            with self.subTest(block):
                doc = copy.deepcopy(OBJECT_SPEC)
                doc["extension"]["transport"][block][key] = 1.0
                self.assertIn("schema.additional", codes(v.validate_artifact(doc)))

    def test_unknown_transport_block_is_refused(self):
        doc = copy.deepcopy(OBJECT_SPEC)
        doc["extension"]["transport"]["halo"] = {"L_kpc": 4.0}
        self.assertIn("schema.additional", codes(v.validate_artifact(doc)))

    def test_physical_signs(self):
        for block, key, value in (("geometry", "L_kpc", 0.0), ("diffusion", "D0_cm2_s", -1.0),
                                  ("reacceleration", "V_A_kms", -1.0), ("convection", "V_c_kms", -1.0)):
            with self.subTest(key):
                doc = copy.deepcopy(OBJECT_SPEC)
                doc["extension"]["transport"][block][key] = value
                self.assertFalse(v.validate_artifact(doc).ok)


class ObjectEntries(unittest.TestCase):
    def test_object_only_list_is_not_blank(self):
        """A2-3, at CRPROP_FROM and at an older version (the _blank fix is not gated)."""
        for version in (v.CRPROP_FROM, v.THEORY_SEMANTICS_FROM):
            with self.subTest(version):
                rep = v.validate_artifact(with_entries([OBJECT_SPEC["extension"]["degenerate_directions"][0]], version))
                self.assertNotIn("theory.degeneracy_missing", codes(rep), rep.as_dict())

    def test_object_without_combination_is_blank(self):
        rep = v.validate_artifact(with_entries([{"combination": " ", "evidence": "posterior",
                                                 "valid_range": {"L_kpc": {"min": 2}}}]))
        self.assertIn("theory.degeneracy_missing", codes(rep))
        self.assertFalse(v._blank({"combination": "D0/L"}, entry_object=True))
        self.assertTrue(v._blank({"combination": "D0/L"}))  # other callers keep the string-only meaning

    def test_string_entries_keep_their_meaning(self):
        rep = v.validate_artifact(with_entries(["D0/L"]))
        self.assertTrue(rep.ok, rep.as_dict())
        self.assertFalse(codes(rep) & NEW_CODES)

    def test_each_evidence_term(self):
        for term in ("fisher-screen", "profile-scan", "posterior"):
            with self.subTest(term):
                entry = dict(OBJECT_SPEC["extension"]["degenerate_directions"][0], evidence=term)
                self.assertTrue(v.validate_artifact(with_entries([entry])).ok)

    def test_range_without_bounds_is_missing(self):
        for rng in ({}, {"L_kpc": {}}):
            with self.subTest(rng):
                entry = dict(OBJECT_SPEC["extension"]["degenerate_directions"][0], valid_range=rng)
                self.assertIn("theory.degeneracy_range_missing", codes(v.validate_artifact(with_entries([entry]))))

    def test_namespaced_evidence_is_unknown(self):
        entry = dict(OBJECT_SPEC["extension"]["degenerate_directions"][0], evidence="ams02:scan")
        self.assertIn("theory.degeneracy_evidence_unknown", codes(v.validate_artifact(with_entries([entry]))))


class NegativeFixtures(unittest.TestCase):
    def test_each_new_code_has_one_negative_fixture(self):
        """A2-2."""
        for code in sorted(NEW_CODES):
            with self.subTest(code):
                names = [n for n, c in CASES["invalid"].items() if code in c]
                self.assertEqual(len(names), 1, names)
                rep = v.validate_artifact(json.loads((ART / "invalid" / names[0]).read_text()))
                self.assertEqual(codes(rep), {code}, rep.as_dict())


class Gating(unittest.TestCase):
    """A2-5: native from CRPROP_FROM only; an older artifact gets the rules only under --strict."""

    def test_gate_constant(self):
        self.assertEqual(v.CRPROP_FROM, "3.14.0")
        self.assertGreater(parse(v.CRPROP_FROM), parse("3.13.0"))

    def test_older_artifact_keeps_its_outcome(self):
        for name in ("theory_crprop_degeneracy_evidence_missing.json", "theory_crprop_degeneracy_range_missing.json",
                     "theory_crprop_degeneracy_evidence_unknown.json"):
            doc = json.loads((ART / "invalid" / name).read_text())
            for version in ("3.13.0", "3.0.0", v.THEORY_SEMANTICS_FROM):
                with self.subTest(name=name, version=version):
                    old = at_version(doc, version)
                    self.assertFalse(codes(v.validate_artifact(old)) & NEW_CODES)
                    self.assertTrue(codes(v.validate_artifact(old, strict=True)) & NEW_CODES)
            self.assertTrue(codes(v.validate_artifact(doc)) & NEW_CODES)


class CommittedSpecsUnchanged(unittest.TestCase):
    """A2-1 (the before/after table is in VALIDATION.md): no committed theory-spec carries an object entry, so none
    gets a new finding, default or strict."""

    def test_no_new_finding(self):
        paths = [p for base in ("contracts/fixtures", "examples", "profiles") for p in sorted((ROOT / base).rglob("*.json"))
                 if "crprop" not in p.name]
        seen = 0
        for p in paths:
            try:
                doc = json.loads(p.read_text())
            except ValueError:
                continue
            if not (isinstance(doc, dict) and doc.get("artifact_type") == "theory-spec"):
                continue
            seen += 1
            for strict in (False, True):
                with self.subTest(path=str(p.relative_to(ROOT)), strict=strict):
                    self.assertFalse(codes(v.validate_artifact(doc, strict=strict)) & NEW_CODES)
        if (ROOT / "examples").is_dir():
            self.assertGreaterEqual(seen, 18)


if __name__ == "__main__":
    unittest.main()
