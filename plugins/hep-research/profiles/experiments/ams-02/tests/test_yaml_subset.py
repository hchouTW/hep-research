"""Tests for scripts/yaml_subset.py and the YAML input path of scripts/audit_analysis_spec.py.

Covers the supported subset (mappings, sequences in both indent styles, scalars and
their typing, quoting, comments, flow collections, block scalars), every documented
rejection with its line number, equality of the YAML and JSON fixtures, and that
the audit gives the same report for a specification written as YAML or JSON.
Run from the skill directory with `python3 -m unittest discover -s tests -v`."""
import contextlib
import copy
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]  # the ams-02 profile folder
sys.path.insert(0, str(ROOT.parents[2]))  # plugin root: core/, contracts/
FIX = ROOT / "tests" / "fixtures"
sys.path.insert(0, str(ROOT / "scripts"))
import audit_analysis_spec as aas  # noqa: E402
from contracts.legacy import yaml_subset as ys  # noqa: E402


def L(text):
    return ys.loads(text)


class ScalarTests(unittest.TestCase):
    def test_typing(self):
        doc = L("a: 1\nb: -2\nc: 1.5\nd: 1e-3\ne: true\nf: false\ng: null\nh: ~\ni:\nj: text\nk: 2011-05-19\n"
                "l: yes\nm: 0x10\nn: .inf\no: 1.\n")
        self.assertEqual(doc, {"a": 1, "b": -2, "c": 1.5, "d": 0.001, "e": True, "f": False, "g": None, "h": None,
                               "i": None, "j": "text", "k": "2011-05-19", "l": "yes", "m": "0x10", "n": ".inf", "o": 1.0})
        self.assertIsInstance(doc["a"], int)
        self.assertIsInstance(doc["d"], float)

    def test_quoting_and_escapes(self):
        doc = L("a: \"x: y # not a comment\"\nb: 'it''s'\nc: \"tab\\there \\u00e9 \\\"q\\\"\"\nd: \"1\"\ne: 'true'\n")
        self.assertEqual(doc["a"], "x: y # not a comment")
        self.assertEqual(doc["b"], "it's")
        self.assertEqual(doc["c"], "tab\there \u00e9 \"q\"")
        self.assertEqual((doc["d"], doc["e"]), ("1", "true"))

    def test_comments(self):
        doc = L("# head\na: 1  # trailing\n# between\nb: two words # c\nc: a#b\n")
        self.assertEqual(doc, {"a": 1, "b": "two words", "c": "a#b"})

    def test_keys_are_strings_and_may_be_quoted(self):
        self.assertEqual(L('1: a\n"b c": 2\n'), {"1": "a", "b c": 2})


class StructureTests(unittest.TestCase):
    def test_nested_mapping_and_both_sequence_styles(self):
        text = "m:\n  a: 1\n  s:\n  - x\n  - y\n  t:\n    - z\nu:\n- 1\n- 2\n"
        self.assertEqual(L(text), {"m": {"a": 1, "s": ["x", "y"], "t": ["z"]}, "u": [1, 2]})

    def test_list_of_mappings_and_nested_lists(self):
        text = "items:\n  - name: a\n    v: 1\n    sub:\n      - p: 1\n        q: 2\n  - name: b\n  - - 1\n    - 2\n  -\n    k: v\n"
        self.assertEqual(L(text), {"items": [{"name": "a", "v": 1, "sub": [{"p": 1, "q": 2}]}, {"name": "b"},
                                             [1, 2], {"k": "v"}]})

    def test_top_level_sequence_and_scalar_and_empty(self):
        self.assertEqual(L("- 1\n- a: 2\n"), [1, {"a": 2}])
        self.assertEqual(L("42\n"), 42)
        self.assertIsNone(L(""))
        self.assertIsNone(L("# only a comment\n"))

    def test_leading_document_marker_and_crlf_and_bom(self):
        self.assertEqual(L("---\na: 1\n"), {"a": 1})
        self.assertEqual(L("a: 1\r\nb: 2\r\n"), {"a": 1, "b": 2})
        self.assertEqual(L("\ufeffa: 1\n"), {"a": 1})

    def test_empty_value_before_dedent_is_null(self):
        self.assertEqual(L("a:\nb: 1\n"), {"a": None, "b": 1})
        self.assertEqual(L("x:\n  a:\n  b: 1\n"), {"x": {"a": None, "b": 1}})

    def test_flow_collections(self):
        doc = L("a: [1, 2.5, \"x, y\", [3, 4], {k: v}]\nb: {p: 1, q: [a, b], r: {s: null}}\nc: []\nd: {}\ne: [1, 2,]\n")
        self.assertEqual(doc, {"a": [1, 2.5, "x, y", [3, 4], {"k": "v"}], "b": {"p": 1, "q": ["a", "b"], "r": {"s": None}},
                               "c": [], "d": {}, "e": [1, 2]})

    def test_block_scalars(self):
        doc = L("lit: |\n  line one\n  line two\n\n  after blank\nfold: >\n  a\n  b\n\n  c\nstrip: |-\n  x\n  y\nfs: >-\n  p\n  q\nnext: 1\n")
        self.assertEqual(doc["lit"], "line one\nline two\n\nafter blank\n")
        self.assertEqual(doc["fold"], "a b\nc\n")
        self.assertEqual(doc["strip"], "x\ny")
        self.assertEqual(doc["fs"], "p q")
        self.assertEqual(doc["next"], 1)

    def test_block_scalar_keeps_hash_and_colon_literally(self):
        self.assertEqual(L("a: |\n  # not a comment\n  k: v\n")["a"], "# not a comment\nk: v\n")

    def test_block_scalar_in_list(self):
        self.assertEqual(L("- |\n  a\n  b\n- 2\n"), ["a\nb\n", 2])


class RejectionTests(unittest.TestCase):
    def bad(self, text, fragment, line=None):
        with self.assertRaises(ys.YamlSubsetError) as cm:
            L(text)
        msg = str(cm.exception)
        self.assertIn(fragment, msg)
        if line is not None:
            self.assertTrue(msg.startswith(f"line {line}:"), msg)

    def test_unsupported_features(self):
        self.bad("a: &x 1\n", "anchor", 1)
        self.bad("a: *x\n", "alias", 1)
        self.bad("a: !!str 1\n", "tag", 1)
        self.bad("%YAML 1.2\n---\na: 1\n", "directive")
        self.bad("a: 1\n---\nb: 2\n", "multiple documents", 2)
        self.bad("? a\n: b\n", "unsupported", 1)
        self.bad("<<: {a: 1}\n", "merge keys", 1)

    def test_indentation_and_structure_errors(self):
        self.bad("a:\n\tb: 1\n", "tab in indentation", 2)
        self.bad("a: 1\n  b: 2\n", "unexpected indentation", 2)
        self.bad("a: 1\nb: 2\n  c: 3\n", "unexpected indentation", 3)
        self.bad("a: 1\n- 2\n", "unexpected content", 2)
        self.bad("- 1\nb: 2\n", "unexpected content", 2)
        self.bad("a: 1\njust text\n", "expected 'key: value'", 2)

    def test_duplicate_keys(self):
        self.bad("a: 1\na: 2\n", "duplicate key 'a'", 2)
        self.bad("a: {b: 1, b: 2}\n", "duplicate key 'b'", 1)

    def test_plain_scalar_with_colon_space(self):
        self.bad("a: b: c\n", "quote it", 1)
        self.bad("- a: b: c\n", "quote it", 1)

    def test_multiline_quoted_and_flow(self):
        self.bad('a: "open\n', "unterminated quoted", 1)
        self.bad("a: [1,\n  2]\n", "unterminated flow", 1)
        self.bad("a: {k: v\n", "unterminated flow", 1)
        self.bad('a: "x" y\n', "unexpected text after quoted", 1)
        self.bad("a: [1] x\n", "unexpected text after flow", 1)

    def test_bad_escapes_and_block_headers(self):
        self.bad('a: "\\q"\n', "unsupported escape", 1)
        self.bad('a: "\\u12"\n', "bad \\u escape", 1)
        self.bad("a: |+\n  x\n", "unsupported block scalar header", 1)
        self.bad("a: |2\n  x\n", "unsupported block scalar header", 1)
        self.bad("a: |\n    x\n  y\n", "indented less", 3)


class FixtureTests(unittest.TestCase):
    def test_yaml_fixture_equals_json_fixture(self):
        self.assertEqual(L((FIX / "spec_valid.yaml").read_text(encoding="utf-8")),
                         json.loads((FIX / "spec_valid.json").read_text(encoding="utf-8")))

    def test_cli_prints_json_and_reports_errors(self):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            self.assertEqual(ys.main([str(FIX / "spec_valid.yaml")]), 0)
        self.assertEqual(json.loads(buf.getvalue()), json.loads((FIX / "spec_valid.json").read_text(encoding="utf-8")))
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "bad.yaml"
            p.write_text("a: &x 1\n", encoding="utf-8")
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                self.assertEqual(ys.main([str(p)]), 2)
            self.assertEqual(json.loads(buf.getvalue())["verdict"], "unreadable")
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(ys.main([str(Path(d) / "missing.yaml")]), 2)
                with self.assertRaises(SystemExit) as cm, contextlib.redirect_stderr(io.StringIO()):
                    ys.main([])
                self.assertEqual(cm.exception.code, 2)


class AuditYamlTests(unittest.TestCase):
    def run_audit(self, path, *extra):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = aas.main([str(path), *extra])
        return code, json.loads(buf.getvalue()) if not extra else buf.getvalue()

    def test_same_report_for_yaml_and_json(self):
        cj, rj = self.run_audit(FIX / "spec_valid.json")
        cy, ry = self.run_audit(FIX / "spec_valid.yaml")
        self.assertEqual((cy, ry), (cj, rj))
        self.assertEqual(self.run_audit(FIX / "spec_valid.yaml", "--markdown")[1],
                         self.run_audit(FIX / "spec_valid.json", "--markdown")[1])

    def test_yml_suffix_and_defect_found_in_yaml(self):
        doc = json.loads((FIX / "spec_valid.json").read_text(encoding="utf-8"))
        broken = copy.deepcopy(doc)
        broken["measurement"]["unit"] = "TeV"
        with tempfile.TemporaryDirectory() as d:
            # one-line JSON is a YAML flow mapping, so it exercises the flow parser with a real specification
            p = Path(d) / "broken.yml"
            p.write_text("---\n" + json.dumps(broken), encoding="utf-8")
            code, report = self.run_audit(p)
        _, base = self.run_audit(FIX / "spec_valid.json")
        self.assertNotEqual(report["findings"], base["findings"])

    def test_yaml_outside_subset_is_exit_2(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "s.yaml"
            p.write_text("measurement: &m\n  title: x\n", encoding="utf-8")
            code, report = self.run_audit(p)
            self.assertEqual((code, report["verdict"]), (2, "unreadable"))
            self.assertIn("line 1", report["error"])
            p.write_text("- a\n- b\n", encoding="utf-8")
            code, report = self.run_audit(p)
            self.assertEqual((code, report["verdict"]), (2, "unreadable"))

    def test_json_suffix_still_json_only(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "s.json"
            p.write_text("measurement:\n  title: x\n", encoding="utf-8")
            code, report = self.run_audit(p)
            self.assertEqual((code, report["verdict"]), (2, "unreadable"))


if __name__ == "__main__":
    unittest.main()
