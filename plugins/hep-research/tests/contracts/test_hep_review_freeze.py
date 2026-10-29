"""hep-review schema freeze: protocol hep-review/1, schema 1.0.0 after G2 (spec v9 section 5.3, T04 done-when).

0.x data stays readable under its own validator version and is labelled experimental in layer 1 and in the report."""
from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from contracts import hep_review as H  # noqa: E402
import hep_review_fixtures as F  # noqa: E402


def as_experimental(case: F.Case) -> F.Case:
    """The same context written by the 0.x line: every object carries hep-review/0 and 0.1.0."""
    old = copy.deepcopy(case)
    for e in old.entries:
        e["validator_version"] = "0.1.0"
        for o in e["objects"]:
            o["protocol"], o["schema_version"] = "hep-review/0", "0.1.0"
    return old


def reviewed_case() -> F.Case:
    c = F.Case()
    c.plan([F.obligation("O1")])
    c.assignment("rev-1")
    c.review("O1", "supported", actor="rev-1")
    return c


def layer1(case: F.Case) -> dict:
    return H.project(H.validate(case.bundle(), H.LATEST_VALIDATOR), H.LATEST_VALIDATOR)


class Constants(unittest.TestCase):
    def test_frozen_versions_and_the_0x_line_kept(self):
        self.assertEqual(H.PROTOCOL, "hep-review/1")
        self.assertEqual(H.SCHEMA_VERSION, "1.0.0")
        self.assertEqual(H.LATEST_VALIDATOR, "1.0.0")
        self.assertIn("0.1.0", H.VALIDATOR_RULES)
        self.assertIn("hep-review/0", H.EXPERIMENTAL_PROTOCOLS)

    def test_schemas_admit_both_lines_and_name_the_frozen_one(self):
        d = json.loads((ROOT / "contracts" / "schemas" / "hep_review_definitions.json").read_text())
        props = d["$defs"]["header"]["properties"] if "$defs" in d else d["definitions"]["header"]["properties"]
        self.assertEqual(sorted(props["protocol"]["enum"]), ["hep-review/0", "hep-review/1"])
        self.assertIn("hep-review/1", d["title"])


class Objects(unittest.TestCase):
    def test_0x_objects_are_admitted_and_an_unknown_protocol_is_refused(self):
        historical = F.header("intent", "intent-x") | {"protocol": "hep-review/0", "schema_version": "0.1.0"}
        self.assertFalse([e for e in H.check_object(historical) if e["code"] == "object.protocol"])
        bad = dict(historical, protocol="hep-review/2")
        self.assertTrue([e for e in H.check_object(bad) if e["code"] == "object.protocol"])

    def test_schema_version_must_belong_to_its_protocol(self):
        mixed = F.header("intent", "intent-x") | {"protocol": "hep-review/1", "schema_version": "0.1.0"}
        self.assertTrue([e for e in H.check_object(mixed) if e["code"] == "object.schema_version"])
        mixed = F.header("intent", "intent-x") | {"protocol": "hep-review/0", "schema_version": "1.0.0"}
        self.assertTrue([e for e in H.check_object(mixed) if e["code"] == "object.schema_version"])


class Labelling(unittest.TestCase):
    def test_layer1_labels_0x_data_experimental(self):
        self.assertIs(layer1(reviewed_case())["experimental"], False)
        old = as_experimental(reviewed_case())
        self.assertIs(layer1(old)["experimental"], True)
        self.assertEqual(layer1(old)["protocol"], "hep-review/1")  # the projection is written by the current line

    def test_0x_bundle_projects_under_its_own_validator_version(self):
        old = as_experimental(reviewed_case())
        p = H.project(H.validate(old.bundle(), "0.1.0"), "0.1.0")
        self.assertIs(p["experimental"], True)
        self.assertEqual(p["validator_version"], "0.1.0")

    def test_report_says_experimental_for_0x_data(self):
        old = as_experimental(reviewed_case())
        b = old.bundle()
        l1 = H.encode(H.project(H.validate(b, H.LATEST_VALIDATOR), H.LATEST_VALIDATOR))
        att = {"head_continuity": "verified"}
        text = H.render_report(l1, att, bundle=b, validator_version=H.LATEST_VALIDATOR)
        self.assertIn("experimental", text.lower())
        frozen_line = reviewed_case().bundle()
        l1 = H.encode(H.project(H.validate(frozen_line, H.LATEST_VALIDATOR), H.LATEST_VALIDATOR))
        self.assertNotIn("experimental", H.render_report(l1, att, bundle=frozen_line,
                                                         validator_version=H.LATEST_VALIDATOR).lower())


if __name__ == "__main__":
    unittest.main()
