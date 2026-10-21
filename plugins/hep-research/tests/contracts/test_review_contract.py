"""Independent review contract (contracts/review.py, docs/dev/independent-review-spec.md): the seven schemas, the
configuration rules (ranges, weak_config loose direction), the context-free record rules, the hash-chained log, and
acceptance criterion 5: the field table of spec section 5.3 matches contracts/schemas/review_record.json."""
from __future__ import annotations

import copy
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "skills" / "hep-authoring" / "scripts"))

from contracts import review as R  # noqa: E402
from contracts.schema import load_schema, validate  # noqa: E402
from review_lib.packet import example_record  # noqa: E402

SPEC = ROOT / "docs" / "dev" / "independent-review-spec.md"
SCHEMAS = ("review_config", "review_units", "review_manifest", "review_record", "review_event", "review_head",
           "review_observation", "review_filter_record")


def spec_section(title: str) -> str:
    text = SPEC.read_text(encoding="utf-8")
    start = text.index(f"### {title}")
    return text[start:text.index("\n### ", start + 4)]


def table(md: str) -> list[list[str]]:
    rows = [ln for ln in md.splitlines() if ln.startswith("|")]
    return [[c.strip() for c in r.strip("|").split("|")] for r in rows[2:]]


class SchemaFileTests(unittest.TestCase):
    def test_seven_schemas_load(self):
        for name in SCHEMAS:
            self.assertIn("$comment", load_schema(f"{name}.json"), name)

    def test_reads_refs_traceability_read_event(self):
        self.assertEqual(load_schema("review_record.json")["properties"]["reads"]["items"]["$ref"],
                         "ext_communication_traceability.json#/$defs/read_event")


class SpecTableConsistencyTests(unittest.TestCase):
    """Acceptance criterion 5."""

    @classmethod
    def setUpClass(cls):
        cls.rows = table(spec_section("5.3 Review record").split("All field names use")[0])
        cls.schema = load_schema("review_record.json")

    def fields(self):
        out = {}
        for cells in self.rows:
            for name in re.findall(r"`([a-z_0-9]+)(?:\[\])?`", cells[0]):
                out[name] = cells[1]
        return out

    def test_field_names_match(self):
        self.assertEqual(sorted(self.fields()), sorted(self.schema["properties"]))

    def test_required_and_optional(self):
        required = set(self.schema["required"])
        for name, text in self.fields().items():
            optional = bool(re.match(r"(Optional|Used on re-review|Used by arbiters)", text))
            with self.subTest(field=name):
                if optional:
                    self.assertNotIn(name, required)
                else:
                    self.assertTrue(name in required or any(name in v for v in R.ROLE_REQUIRED.values()), name)
        self.assertIn("limitations", required)

    def test_reviewer_subfields(self):
        text = self.fields()["reviewer"]
        listed = re.findall(r"`([a-z_]+)`", text)
        props = self.schema["properties"]["reviewer"]["properties"]
        self.assertEqual(sorted(x for x in listed if x in props or x not in ("fresh", "human")), sorted(props))
        self.assertEqual(sorted(props["context"]["enum"]), ["fresh", "human"])

    def test_enums(self):
        d = self.schema["$defs"]
        expect = {"mark": d["skim_mark"]["properties"]["mark"]["enum"],
                  "verdict": d["verdict"]["properties"]["verdict"]["enum"],
                  "status": d["carry_item"]["properties"]["status"]["enum"],
                  "kind": d["finding"]["properties"]["kind"]["enum"],
                  "severity": d["finding"]["properties"]["severity"]["enum"]}
        flat = " ".join(" | ".join(r) for r in self.rows)
        for field, values in expect.items():
            with self.subTest(field=field):
                m = re.search(r"`" + field + r"` \(([^)]*)\)", flat)
                self.assertIsNotNone(m, field)
                listed = re.findall(r"`([a-z/-]+)`", m.group(1))
                self.assertEqual(sorted(listed), sorted(values))
        role = re.findall(r"`([a-z-]+)`", self.fields()["role"])
        self.assertEqual(sorted(role), sorted(self.schema["properties"]["role"]["enum"]))

    def test_basis_table_matches(self):
        rows = table(spec_section("5.3 Review record").split("**Evidence bases**")[1])
        bases = [re.search(r"`([a-z-]+)`", r[0]).group(1) for r in rows if r and r[0].startswith("`")]
        defs = [k[len("evidence_"):].replace("_", "-") for k in self.schema["$defs"] if k.startswith("evidence_")]
        self.assertEqual(sorted(bases), sorted(defs))
        indep = {re.search(r"`([a-z-]+)`", r[0]).group(1): r[3] for r in rows if r and r[0].startswith("`")}
        for b, text in indep.items():
            d = self.schema["$defs"]["evidence_" + b.replace("-", "_")]["description"]
            low = text.lower()
            expected = "it depends" if low.startswith("it depends") else "yes" if low.startswith("yes") else "no"
            self.assertIn(f"Independent: {expected}", d, b)

    def test_identifier_pattern_allows_digits(self):
        pat = self.schema["$defs"]["id"]["pattern"]
        for ok in ("F1", "C12", "A1.2", "S10", "CF3"):
            self.assertRegex(ok, pat)
        self.assertNotRegex("1F", pat)
        self.assertNotIn("slotid", R.json.dumps(self.schema))
        self.assertNotIn("carryforward", R.json.dumps(self.schema))


class ConfigTests(unittest.TestCase):
    def test_defaults_are_in_range_and_not_weak(self):
        cfg = {"config_version": "1.0.0", "models": ["m"]}
        self.assertEqual(R.config_problems(cfg), [])
        self.assertEqual(R.weak_config(cfg), [])

    def test_out_of_range(self):
        for name, (_, low, high, _) in R.CONFIG_RULES.items():
            with self.subTest(name=name):
                bad = high + 1 if isinstance(high, int) else high + 0.1
                probs = R.config_problems({"config_version": "1.0.0", "models": ["m"], name: bad})
                self.assertTrue(any(name in p for p in probs))

    def test_weak_config_loose_direction(self):
        self.assertEqual(R.weak_config({"models": ["m"], "unresolved_max_ratio": 0.49}), ["unresolved_max_ratio"])
        self.assertEqual(R.weak_config({"models": ["m"], "deep_sample": 10}), ["deep_sample"])
        self.assertEqual(R.weak_config({"models": ["m"], "deep_sample": 30, "canaries_per_slot": 3}), [])
        self.assertEqual(R.weak_config({"models": ["m"], "attempt_timeout_minutes": 120}), [])

    def test_models_required(self):
        self.assertTrue(R.config_problems({"config_version": "1.0.0", "models": []}))


class RecordRuleTests(unittest.TestCase):
    def test_examples_pass(self):
        self.assertEqual(R.record_rules(example_record("lens", "S1"), "reviewer"), [])
        self.assertEqual(R.record_rules(example_record("arbiter", "S9"), "arbiter"), [])

    def test_role_required_fields(self):
        rec = example_record("lens", "S1")
        del rec["skim"]
        self.assertEqual([c for c, _ in R.record_rules(rec, "reviewer")], ["schema_invalid"])

    def test_locator_needs_lines_or_section_and_url_copy(self):
        rec = example_record("lens", "S1")
        del rec["evidence"][0]["lines"]
        self.assertIn("schema_invalid", [c for c, _ in R.record_rules(rec)])
        rec = example_record("lens", "S1")
        rec["evidence"][0]["ref"] = "https://example.org/doc"
        self.assertIn("schema_invalid", [c for c, _ in R.record_rules(rec)])

    def test_basis_specific_fields(self):
        rec = example_record("lens", "S1")
        rec["evidence"].append({"id": "E3", "basis": "third-party", "command": "x"})
        self.assertIn("schema_invalid", [c for c, _ in R.record_rules(rec)])

    def test_contiguity(self):
        self.assertTrue(R.contiguous(["U0003", "U0002", "U0004"]))
        self.assertFalse(R.contiguous(["U0002", "U0004"]))
        self.assertFalse(R.contiguous(["U0002", "U0002"]))

    def test_basis_class(self):
        self.assertEqual(R.basis_class({"basis": "locator", "source_kind": "page"}), "independent")
        self.assertEqual(R.basis_class({"basis": "locator", "source_kind": "code"}), "external")
        self.assertEqual(R.basis_class({"basis": "tool-output"}), "external")
        self.assertEqual(R.basis_class({"basis": "internal"}), "internal")


class KeyMatchTests(unittest.TestCase):
    def test_numeric_keys_ignore_language(self):
        for text in ("應為 3 倍", "3x faster", "about 3 times", "(3)"):
            self.assertTrue(R.key_in(text, "3"), text)
        for text in ("13x", "31 倍", "x30"):
            self.assertFalse(R.key_in(text, "3"), text)
        self.assertTrue(R.key_in("lines 118-126 hold it", "118-126"))

    def test_identifier_keys(self):
        self.assertTrue(R.key_in("see `finding_shape` here", "finding_shape"))
        self.assertFalse(R.key_in("see finding_shapes", "finding_shape"))


class LogTests(unittest.TestCase):
    def make(self):
        ev = [R.make_event(None, "round_started", "2026-01-01T00:00:00Z",
                           {"review_id": "R1", "round": 1, "document": "d.md", "source_sha256": "0" * 64,
                            "units_sha256": "0" * 64, "config": {"models": ["m"]}, "config_sha256": "0" * 64,
                            "slots": [{"slot_id": "S1", "model": "m"}], "author": {"identity": "a", "model": "m"},
                            "carry_forward": {}, "removed_findings": []})]
        ev.append(R.make_event(ev[-1], "escalated", "2026-01-01T00:01:00Z", {"items": ["round-limit"], "reason": "x"}))
        return ev, R.make_head("R1", ev)

    def test_good_log_verifies(self):
        ev, head = self.make()
        self.assertEqual(R.verify_log(ev, head), [])
        self.assertEqual(validate(head, "review_head.json").errors, [])

    def test_edits_are_caught(self):
        ev, head = self.make()
        bad = copy.deepcopy(ev)
        bad[0]["data"]["document"] = "other.md"
        self.assertTrue(R.verify_log(bad, head))
        self.assertTrue(R.verify_log(ev[:1], head))
        self.assertTrue(R.verify_log(ev, dict(head, review_id="R2")))
        late = copy.deepcopy(ev)
        late[1]["time"] = "2025-01-01T00:00:00Z"
        self.assertTrue(R.verify_log(late, R.make_head("R1", late)))

    def test_parse_log_refuses_unterminated(self):
        with self.assertRaises(ValueError):
            R.parse_log(b'{"a":1}')
        with self.assertRaises(ValueError):
            R.parse_log(b"")


if __name__ == "__main__":
    unittest.main()
