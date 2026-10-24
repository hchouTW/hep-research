"""Contract side of the filtering pass and of lens_models (contracts 3.4.0; docs/dev/independent-review-spec.md
sections 5.1, 5.5, 6.9 and 7.5): the filter record schema against the spec's field table, the context-free rules,
the fixtures under contracts/fixtures/review/, decide row 8a, fold, the filter slot's attempt limit, the log
transitions, and an exhaustive check that the filter row never preempts a slot in flight. Synthetic data only."""
from __future__ import annotations

import copy
import itertools
import json
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "skills" / "hep-authoring" / "scripts"))

from contracts import review as R  # noqa: E402
from contracts.schema import load_schema  # noqa: E402
from review_lib.packet import filter_example_record  # noqa: E402
from tests.contracts.test_review_contract import spec_section, table  # noqa: E402
from tests.contracts.test_review_state import DL, SLOT_STATES, T, base_events, ev, first_row, slot, snap  # noqa: E402

FIX = ROOT / "contracts" / "fixtures" / "review"


def filter_events(cfg_filter=True, max_attempts=None, auto_canary=False):
    """base_events with a filter in the configuration (and the second slot's finding optionally a control)."""
    evs = base_events(sev="medium", second_verdict="partially-supported")
    cfg = evs[0]["data"]["config"]
    if cfg_filter:
        cfg["filter"] = {"model": "m-f"}
    if max_attempts:
        cfg["max_attempts_per_slot"] = max_attempts
    if auto_canary:
        evs.append(ev("disposed", finding="1/S2/F1", disposition="auto-canary", reason="r", verification=None,
                      edited_units=[], finding_units=["U0001"], round=1, by="review.py"))
    return evs


def needed(sid="S3"):
    return ev("filter_needed", round=1, slot_id=sid, model="m-f", findings=["1/S2/F1"])


class SchemaAndSpecTests(unittest.TestCase):
    def test_spec_field_table_matches_the_schema(self):
        rows = table(spec_section("5.5 Filter record").split("**Rules**")[0])
        schema = load_schema("review_filter_record.json")
        first = {n for cells in rows for n in re.findall(r"`([a-z_0-9]+)(?:\[\])?`", cells[0])}
        self.assertEqual(first, set(schema["properties"]))
        contents = {n: cells[1] for cells in rows for n in re.findall(r"`([a-z_0-9]+)(?:\[\])?`", cells[0])}
        for sub in ("reviewer", "isolation"):
            for name in schema["properties"][sub]["properties"]:
                self.assertIn(f"`{name}", contents[sub], (sub, name))
        for name in schema["$defs"]["decision"]["properties"]:
            self.assertIn(f"`{name}`", contents["decisions"], name)
        self.assertEqual(schema["$defs"]["decision"]["properties"]["decision"]["enum"], list(R.FILTER_DECISIONS))
        self.assertIn("`keep`, `drop`", contents["decisions"])
        self.assertEqual(set(schema["required"]), set(schema["properties"]) - set())

    def test_example_passes(self):
        self.assertEqual(R.filter_record_rules(filter_example_record("S9")), [])

    def test_receipt_codes_are_in_the_spec(self):
        text = spec_section("7.5 Receipt rules (filter slot)")
        for code in R.FILTER_CODES:
            self.assertIn(f"`{code}`", text, code)

    def test_config_fields_in_the_spec_table(self):
        text = spec_section("5.1 Configuration `review_config` (1.0.0)")
        self.assertIn("`lens_models`", text)
        self.assertIn("`filter`", text)


class RecordRuleTests(unittest.TestCase):
    def setUp(self):
        self.rec = filter_example_record("S9")

    def codes(self, rec):
        return sorted({c for c, _ in R.filter_record_rules(rec)})

    def test_repeated_decision(self):
        self.rec["decisions"].append(copy.deepcopy(self.rec["decisions"][2]))
        self.assertEqual(self.codes(self.rec), ["decisions_incomplete"])

    def test_unknown_decision_and_blank_reason(self):
        self.rec["decisions"][0]["decision"] = "maybe"
        self.assertEqual(self.codes(self.rec), ["schema_invalid"])
        self.rec = filter_example_record("S9")
        self.rec["decisions"][2]["reason"] = "   "
        self.assertEqual(self.codes(self.rec), ["schema_invalid"])

    def test_duplicate_of_rules(self):
        self.rec["decisions"][1]["duplicate_of"] = self.rec["decisions"][2]["finding_id"]  # a dropped finding
        self.assertEqual(self.codes(self.rec), ["duplicate_target"])
        self.rec["decisions"][1]["duplicate_of"] = self.rec["decisions"][1]["finding_id"]  # itself
        self.assertEqual(self.codes(self.rec), ["duplicate_target"])
        self.rec["decisions"][1]["duplicate_of"] = "Pnowhere"  # an unknown id
        self.assertEqual(self.codes(self.rec), ["duplicate_target"])
        self.rec = filter_example_record("S9")
        self.rec["decisions"][0]["duplicate_of"] = self.rec["decisions"][1]["finding_id"]  # on a keep
        self.assertIn("duplicate_target", self.codes(self.rec))

    def test_reviewer_record_is_not_a_filter_record(self):
        self.rec["role"] = "reviewer"
        self.assertEqual(self.codes(self.rec), ["schema_invalid"])
        self.assertEqual(self.codes("text"), ["schema_invalid"])

    def test_receipt_coverage(self):
        rec = filter_example_record("S9")
        ctx = {"slot_id": "S9", "author": "author-agent", "files": {p["path"]: {"sha256": p["sha256"]} for p in rec["paths_read"]},
               "dispatched": {"packet_sha256": rec["packet_sha256"], "nonce": rec["dispatch_nonce"],
                              "instructions_sha256": rec["instructions_sha256"]},
               "instructions_changed": False, "finding_ids": [d["finding_id"] for d in rec["decisions"]]}
        self.assertEqual(R.filter_receipt_codes(rec, ctx), [])
        ctx2 = dict(ctx, finding_ids=ctx["finding_ids"] + ["Pextra"])
        self.assertEqual([c for c, _ in R.filter_receipt_codes(rec, ctx2)], ["decisions_incomplete"])
        ctx3 = dict(ctx, instructions_changed=True)
        self.assertEqual([c for c, _ in R.filter_receipt_codes(rec, ctx3)], ["instructions_changed"])
        bad = copy.deepcopy(rec)
        bad["packet_sha256"] = "f" * 64
        self.assertEqual([c for c, _ in R.filter_receipt_codes(bad, ctx)], ["packet_mismatch"])
        self.assertEqual([c for c, _ in R.filter_receipt_codes(None, ctx)], ["schema_invalid"])


def fixture_rules(name: str, record: dict) -> list:
    """The context-free rules of a review fixture: filter records (filter_record*.json) by filter_record_rules,
    expert records (expert_record*.json, contracts 3.6.0) by record_rules with role expert."""
    if name.startswith("expert_record"):
        return R.record_rules(record, "expert")
    return R.filter_record_rules(record)


class FixtureTests(unittest.TestCase):
    cases = json.loads((FIX / "cases.json").read_text(encoding="utf-8"))

    def test_valid_fixtures_pass(self):
        self.assertTrue(self.cases["valid"])
        for name in self.cases["valid"]:
            with self.subTest(name=name):
                self.assertEqual(fixture_rules(name, json.loads((FIX / "valid" / name).read_text())), [])

    def test_invalid_fixtures_fail_with_their_codes(self):
        self.assertTrue(self.cases["invalid"])
        for name, codes in self.cases["invalid"].items():
            with self.subTest(name=name):
                got = {c for c, _ in fixture_rules(name, json.loads((FIX / "invalid" / name).read_text()))}
                self.assertEqual(got, set(codes))

    def test_every_fixture_is_listed_and_synthetic(self):
        listed = {f"valid/{n}" for n in self.cases["valid"]} | {f"invalid/{n}" for n in self.cases["invalid"]}
        found = {p.relative_to(FIX).as_posix() for p in FIX.rglob("*.json") if p.name != "cases.json"}
        self.assertEqual(found, listed)
        for p in FIX.rglob("*.json"):
            if p.name != "cases.json":
                self.assertIn("SYNTHETIC", json.loads(p.read_text())["limitations"], p.name)


class StateTests(unittest.TestCase):
    def test_row_8a_after_round_1_is_received(self):
        st = R.fold(filter_events())
        self.assertEqual(R.filter_pool(st), ["1/S2/F1"])
        a = R.decide(R.snapshot(st))
        self.assertEqual((a["row"], a["action"]), ("8a", "filter"))

    def test_no_filter_row_without_config_or_findings(self):
        self.assertEqual(R.decide(R.snapshot(R.fold(filter_events(cfg_filter=False))))["action"], "dispose")
        st = R.fold(filter_events(auto_canary=True))
        self.assertEqual(R.filter_pool(st), [])
        self.assertFalse(R.snapshot(st)["filter_needed"])

    def test_filter_slot_goes_through_the_usual_rows(self):
        evs = filter_events() + [needed()]
        s = R.snapshot(R.fold(evs))
        self.assertEqual(s["slots"]["S3"], {"state": "none", "attempt": 0, "deadline": None, "kind": "filter", "resolved": False})
        self.assertFalse(s["filter_needed"])
        self.assertEqual(R.decide(s), {"row": 7, "action": "dispatch", "slots": ["S3"]})
        evs.append(ev("dispatched", round=1, slot_id="S3", attempt=1, deadline=DL))
        self.assertEqual(R.decide(R.snapshot(R.fold(evs)))["action"], "await")

    def test_accepted_filter_records_decisions_and_dispose_follows(self):
        dec = [{"finding": "1/S2/F1", "decision": "drop", "reason": "r", "duplicate_of": None}]
        evs = filter_events() + [needed(), ev("dispatched", round=1, slot_id="S3", attempt=1, deadline=DL),
                                 ev("accepted", round=1, slot_id="S3", attempt=1, decisions=dec)]
        st = R.fold(evs)
        self.assertEqual(st["filter"]["decisions"], dec)
        self.assertEqual(set(st["findings"]), {"1/S2/F1"})  # nothing added, nothing deleted
        self.assertEqual(st["findings"]["1/S2/F1"]["state"], "open")
        self.assertEqual(R.decide(R.snapshot(st))["action"], "dispose")

    def test_exhausted_after_two_attempts_even_when_slots_get_three(self):
        evs = filter_events(max_attempts=3) + [needed()]
        for k in (1, 2):
            evs += [ev("dispatched", round=1, slot_id="S3", attempt=k, deadline=DL),
                    ev("rejected", round=1, slot_id="S3", attempt=k, codes=["x"])]
        s = R.snapshot(R.fold(evs))
        self.assertEqual(s["slots"]["S3"]["state"], "exhausted")
        self.assertEqual(R.decide(s)["action"], "dispose")  # row 9 covers lens and shadow slots only
        self.assertEqual(R.slot_state(R.fold(filter_events(max_attempts=1) + [needed()]), 1, "S3")["state"], "none")

    def test_transitions(self):
        recs = []
        for e in filter_events() + [needed()]:
            recs.append(R.make_event(recs[-1] if recs else None, e["event"], T, e["data"]))
        self.assertEqual(R.transition_problems(recs), [])
        third = recs[:]
        for k in (1, 2, 3):
            third.append(R.make_event(third[-1], "dispatched", T, {"round": 1, "slot_id": "S3", "attempt": k}))
            third.append(R.make_event(third[-1], "rejected", T, {"round": 1, "slot_id": "S3", "attempt": k}))
        self.assertIn("attempt 3 out of order", " ".join(R.transition_problems(third)))
        twice = recs + [R.make_event(recs[-1], "filter_needed", T, dict(recs[-1]["data"], slot_id="S4"))]
        self.assertIn("a second filter_needed", " ".join(R.transition_problems(twice)))

    def test_sidecar_name(self):
        st = R.fold(filter_events() + [needed()])
        self.assertEqual((R.sidecar_name(st, 1, "S3"), R.sidecar_name(st, 1, "S1")), (R.FILTER_SIDECAR, R.SIDECAR))

    def test_exhaustive_filter_row(self):
        """Two review slots and the filter slot in every state, filter_needed true or false: decide is the first row
        whose condition holds, with row 8a between 8 and 9; filter is printed only when no slot is in flight, and an
        exhausted filter slot never escalates."""
        live = ("none", "dispatched", "returned-empty", "overdue", "submitted", "rejected", "withdrawn")
        for a, b, f, need in itertools.product(SLOT_STATES, SLOT_STATES, ("absent",) + live + ("accepted", "exhausted"),
                                               (False, True)):
            slots = {}
            for sid, s in (("S1", a), ("S2", b)):
                slots[sid] = slot("exhausted", resolved=True) if s == "exhausted-resolved" else slot(s)
            if f != "absent":
                slots["S3"] = slot(f, kind="filter")
            s = snap(slots=slots, findings={"1/S1/F1": "open"}, filter_needed=need and f == "absent")
            act = R.decide(s)
            row = first_row(s)
            if s["filter_needed"] and isinstance(row, int) and row >= 9:
                row = "8a"
            self.assertEqual(act["row"], row, (a, b, f, need))
            if act["action"] == "filter":
                self.assertTrue({v["state"] for v in slots.values()} <= {"accepted", "exhausted"})
            if f == "exhausted":
                self.assertNotEqual(act.get("items"), ["slot:1/S3"])


if __name__ == "__main__":
    unittest.main()
