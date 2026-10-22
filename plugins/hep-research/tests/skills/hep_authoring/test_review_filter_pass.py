"""The optional filtering pass of the independent review (contracts 3.4.0; docs/dev/independent-review-spec.md
sections 5.1, 5.2, 5.5, 6.9, 7.5 and A8), driven in-process with scripted reviewer and filter agents, together with
the per-lens model choice (the design lens fixed to model-c). Synthetic data only.

- filter / --filter-model: after round 1's records are received, next prints filter (row 8a); the filter slot's packet
  holds the pooled findings under random ids and no reviewer identity; receipt rejects a bad filter record; after two
  failed attempts the filter is not applied; the report lists kept findings first and the dropped ones apart."""
from __future__ import annotations

import json
import re
import tempfile
import unittest
from pathlib import Path

from tests.skills.hep_authoring import review_harness as H
from contracts import review as R

MODELS3 = ["model-a", "model-b", "model-c"]
FILTER_CFG = {"config_version": "1.0.0", "models": MODELS3, "lens_models": {"design": "model-c"},
              "filter": {"model": "model-f"}}


def round1(h: H.Harness, extra_findings: int = 3) -> dict:
    """Dispatch round 1, write good records (the design lens adds extra findings on design-only units), receive them.
    Returns {design lens slot: [units of its extra findings]}."""
    act = h.next()
    H.dispatch_all(h, act)
    picks = {}
    for sid in act["slots"]:
        info = h.slot_info(sid)
        extra = []
        if info["role"] == "lens" and info["lens"] == "design":
            pick = h.design_only_units(sid)[:extra_findings]
            picks[sid] = pick
            extra = [(u, "low" if n == 2 else "medium", "partially-supported") for n, u in enumerate(pick)]
        h.write_record(sid, h.good_record(sid, findings=extra))
        h.run("returned", sid, expect=0)
    act = h.next()
    assert act["action"] == "receive", act
    for sid in act["slots"]:
        out = h.run("receive", sid)
        assert out["status"] == "ok", out
    return picks


def filter_packet(h: H.Harness, sid: str) -> dict:
    p = h.adir(sid) / "packet"
    return json.loads((p / "findings.json").read_text(encoding="utf-8"))


def filter_record(h: H.Harness, sid: str, mode: str = "good", identity: str = "filter-agent") -> dict:
    """A filter record for the packet: the first finding kept, the second dropped as its duplicate, the rest dropped;
    mode breaks one rule."""
    d = h.dispatched(sid)
    adir = h.adir(sid)
    ids = [f["id"] for f in filter_packet(h, sid)["findings"]]
    decisions = [{"finding_id": ids[0], "decision": "keep", "reason": "The statement is wrong; the page should change."}]
    if len(ids) > 1:
        decisions.append({"finding_id": ids[1], "decision": "drop", "duplicate_of": ids[0],
                          "reason": "The same problem as the kept finding."})
    for x in ids[2:]:
        decisions.append({"finding_id": x, "decision": "drop", "reason": "A wording preference."})
    if mode == "missing":
        decisions = decisions[:-1]
    elif mode == "repeat":
        decisions.append(dict(decisions[-1], reason="Second thoughts."))
    elif mode == "unknown-decision":
        decisions[0]["decision"] = "maybe"
    elif mode == "unknown-id":
        decisions.append({"finding_id": "Pnot-a-finding", "decision": "drop", "reason": "Not in the packet."})
    elif mode == "dup-of-dropped":
        decisions[1]["duplicate_of"] = ids[2]
    return {"packet_sha256": d["packet_sha256"], "dispatch_nonce": d["nonce"],
            "instructions_sha256": d["instructions_sha256"], "role": "filter",
            "reviewer": {"identity": identity, "context": "fresh", "model": "model-f", "host": "claude-code",
                         "slot_id": sid},
            "isolation": {"saw_prior_conversation": False, "host_injected": ["memory file"],
                          "instruction_files_seen": "unknown"},
            "paths_read": [{"path": f"packet/{n}", "sha256": H.sha(adir / "packet" / n)}
                           for n in ("document.md", "findings.json", "instructions.md")],
            "decisions": decisions, "limitations": "Synthetic scripted filter."}


def write_filter(h: H.Harness, sid: str, rec: dict):
    (h.adir(sid) / R.FILTER_SIDECAR).write_text(json.dumps(rec, indent=1), encoding="utf-8")


def to_filter_dispatch(h: H.Harness) -> str:
    act = h.next()
    assert (act["action"], act["row"]) == ("filter", "8a"), act
    out = h.run("filter", expect=0)
    act = h.next()
    assert act["action"] == "dispatch" and act["slots"] == [out["slot"]], act
    h.run("dispatch", out["slot"], expect=0)
    return out["slot"]


class FilterPassEndToEndTests(unittest.TestCase):
    """Round 1 with the filter (one rejected attempt, then accepted), dispose, a re-review round that keeps the fixed
    design-lens model and runs no second filter, close; check exits 0."""

    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory(prefix="hep-review-filter-")
        h = cls.h = H.Harness(Path(cls._tmp.name), config=FILTER_CFG).setup()
        h.start()
        cls.picks = round1(h)
        cls.design1 = next(iter(cls.picks))
        cls.fsid = to_filter_dispatch(h)
        cls.packet = filter_packet(h, cls.fsid)
        cls.packet_dir = h.adir(cls.fsid) / "packet"
        write_filter(h, cls.fsid, filter_record(h, cls.fsid, "missing"))
        h.run("returned", cls.fsid, expect=0)
        assert h.next()["action"] == "receive"
        cls.rejected = h.run("receive", cls.fsid)
        act = h.next()
        assert act["action"] == "dispatch" and act["slots"] == [cls.fsid], act
        h.run("dispatch", cls.fsid, expect=0)
        cls.ids2 = json.loads((h.rv.private_attempt(1, cls.fsid, 2) / "filter_ids.json").read_text())["ids"]
        write_filter(h, cls.fsid, filter_record(h, cls.fsid))
        h.run("returned", cls.fsid, expect=0)
        assert h.next()["action"] == "receive"
        cls.accepted = h.run("receive", cls.fsid)
        cls.dispose_act = act = h.next()
        assert act["action"] == "dispose", act
        # the kept finding is changed (edit + verified); the rest declined (medium and low: closed)
        kept = [g for g, d in act["filter"].items() if d["decision"] == "keep"]
        cls.kept = kept
        for g in act["findings"]:
            if g in kept:
                unit = h.st()["findings"][g]["units"][0]
                text = h.unit_text(unit)
                h.write_doc(h.read_doc().replace(text, text[:-1] + ", as revised.", 1))
                h.run("dispose", g, "--as", "changed", "--reason", "fixed", "--verified", "locator:LICENSE:2-3", expect=0)
            else:
                h.run("dispose", g, "--as", "declined", "--reason", act["filter"][g]["reason"], expect=0)
        cls.report1 = None
        for _ in range(60):
            act = h.next()
            a = act["action"]
            if a == "rereview":
                h.run("rereview", expect=0)
            elif a == "dispatch":
                H.dispatch_all(h, act)
                for sid in act["slots"]:
                    h.write_record(sid, h.good_record(sid))
                    h.run("returned", sid, expect=0)
            elif a == "receive":
                for sid in act["slots"]:
                    assert h.run("receive", sid)["status"] == "ok"
            elif a == "close":
                h.run("close", expect=0)
            elif a == "stop":
                break
            else:
                raise AssertionError(act)
        cls.events = h.rv.events()
        cls.report = (h.rv.dir / "report.md").read_text(encoding="utf-8")

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    def test_filter_slot_and_event(self):
        fn = [e["data"] for e in self.events if e["event"] == "filter_needed"]
        self.assertEqual(len(fn), 1)  # round 1 only
        self.assertEqual((fn[0]["round"], fn[0]["model"], len(fn[0]["findings"])), (1, "model-f", 3))
        self.assertEqual(self.h.rv.slots()["1"][self.fsid], {"role": "filter", "lens": None, "model": "model-f"})
        # the pool is the design lens's three findings; the control findings closed as auto-canary are not in it
        self.assertTrue(all(g.split("/")[1] == self.design1 for g in fn[0]["findings"]))

    def test_filter_runs_before_arbitration_and_dispose(self):
        kinds = [e["event"] for e in self.events]
        self.assertLess(kinds.index("filter_needed"), kinds.index("disposed", kinds.index("filter_needed")))
        first_user_disposal = next(i for i, e in enumerate(self.events) if e["event"] == "disposed"
                                   and e["data"]["disposition"] != "auto-canary")
        self.assertLess(kinds.index("filter_needed"), first_user_disposal)

    def test_bad_record_rejected_then_good_record_accepted(self):
        self.assertEqual((self.rejected["status"], self.rejected["codes"]), ("rejected", ["decisions_incomplete"]))
        self.assertEqual(self.accepted["status"], "ok")
        self.assertEqual((self.accepted["kept"], self.accepted["dropped"]), (1, 2))
        dec = [e["data"] for e in self.events if e["event"] == "accepted" and e["data"]["slot_id"] == self.fsid][0]
        self.assertEqual(sorted(d["finding"] for d in dec["decisions"]), sorted(self.ids2.values()))
        dup = [d for d in dec["decisions"] if d["duplicate_of"]]
        self.assertEqual(len(dup), 1)
        self.assertEqual(dup[0]["duplicate_of"], self.kept[0])
        self.assertEqual(dec["metrics"], {"kept": 1, "dropped": 2, "duplicates": 1})

    def test_ids_are_new_for_each_attempt(self):
        ids1 = json.loads((self.h.rv.private_attempt(1, self.fsid, 1) / "filter_ids.json").read_text())["ids"]
        self.assertEqual(sorted(ids1.values()), sorted(self.ids2.values()))
        self.assertFalse(set(ids1) & set(self.ids2))

    def test_dispose_action_carries_the_filter_advice(self):
        self.assertEqual(sorted(self.dispose_act["filter"]), sorted(self.dispose_act["findings"]))
        self.assertIn("advice", self.dispose_act["filter_note"])

    def test_packet_has_no_reviewer_identity(self):
        allowed = {"id", "kind", "severity", "units", "unit_texts", "value", "correction", "description", "fix"}
        for f in self.packet["findings"]:
            self.assertEqual(set(f), allowed)
            self.assertRegex(f["id"], r"^P[0-9a-f]{8,}$")
        slots = self.h.rv.slots()["1"]
        others = [s for s in slots if s != self.fsid]
        st = self.h.st()
        identities = [a["data"]["identity"] for (r, s), atts in st["attempts"].items() for a in atts.values()
                      if a["outcome"] == "accepted" and s != self.fsid]
        local_ids = [g.split("/")[2] for g in st["filter"]["findings"]]
        for name in ("findings.json", "scope.json", "units.json", "instructions.md", "manifest.json"):
            text = (self.packet_dir / name).read_text(encoding="utf-8")
            for sid in others:
                self.assertIsNone(re.search(rf"\b{sid}\b", text), (name, sid))
            for x in identities + ["model-a", "model-b", "model-c"]:
                self.assertNotIn(x, text, name)
            if name == "findings.json":
                for x in local_ids:
                    self.assertNotIn(f'"{x}"', text)
                for key in ('"lens"', '"role"', '"slot_id"', '"model"', '"reviewer"', '"identity"'):
                    self.assertNotIn(key, text)
        scope = json.loads((self.packet_dir / "scope.json").read_text(encoding="utf-8"))
        self.assertEqual(scope["finding_ids"], [f["id"] for f in self.packet["findings"]])
        # the document copy carries no canary
        doc = (self.packet_dir / "document.md").read_text(encoding="utf-8")
        self.assertTrue(doc.endswith(H.DOC))

    def test_written_example_passes_and_instructions_name_the_rules(self):
        text = (self.packet_dir / "instructions.md").read_text(encoding="utf-8")
        from review_lib.packet import extract_example
        self.assertEqual(R.filter_record_rules(extract_example(text)), [])
        for part in ("`keep`", "`drop`", "duplicate_of", "decisions_incomplete", "duplicate_target", "--role filter",
                     "R0 isolation self-check"):
            self.assertIn(part, text)

    def test_rereview_keeps_the_fixed_design_model_and_runs_no_second_filter(self):
        self.assertEqual([e["data"]["round"] for e in self.events if e["event"] == "round_started"], [1, 2])
        slots2 = self.h.rv.slots()["2"]
        design = {v["role"]: v["model"] for v in slots2.values() if v["lens"] == "design"}
        self.assertEqual(design["lens"], "model-c")
        self.assertNotEqual(design["shadow"], "model-c")
        self.assertNotIn("filter", {v["role"] for v in slots2.values()})

    def test_closed_and_check_ok(self):
        self.assertEqual(self.events[-1]["event"], "closed")
        res = R.check(self.h.rv.dir)
        self.assertEqual(res["status"], "ok", res)

    def test_report_lists_kept_first_and_drops_apart(self):
        r = self.report
        self.assertIn("| filter | model model-f | - |", r)
        self.assertIn("| lens_models | design=model-c | - |", r)
        self.assertIn("## Filtering pass", r)
        self.assertIn("a1: rejected decisions_incomplete", r)
        self.assertIn("Applied: kept 1, dropped 2", r)
        findings = r.split("## Findings\n", 1)[1].split("## Findings the filter dropped", 1)[0]
        dropped = r.split("## Findings the filter dropped", 1)[1].split("\n## ", 1)[0]
        self.assertIn(self.kept[0], findings)
        self.assertIn("keep: The statement is wrong", findings)
        for g in self.dispose_act["findings"]:
            if g not in self.kept:
                self.assertIn(g, dropped)
                self.assertNotIn(f"| {g} |", findings)
        self.assertIn("The same problem as the kept finding.", dropped)
        self.assertIn("A wording preference.", dropped)
        self.assertIn(f"| {self.kept[0]} |", dropped)  # the duplicate_of column

    def test_check_catches_an_edited_filter_record(self):
        p = self.h.rv.attempt_dir(1, self.fsid, 2) / R.FILTER_SIDECAR
        orig = p.read_bytes()
        try:
            p.write_bytes(orig.replace(b"wording", b"Wording"))
            res = R.check(self.h.rv.dir)
            self.assertEqual(res["status"], "fail")
            self.assertIn(f"round-1/{self.fsid}/attempt-2/{R.FILTER_SIDECAR}",
                          [d for c in res["codes"] if c["code"] == "artifacts_changed" for d in c["detail"]])
        finally:
            p.write_bytes(orig)


class FilterReceiptTests(unittest.TestCase):
    """Each bad filter record alone is rejected with its code; after two rejected attempts the filter is not applied
    and the review goes on to dispose."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(prefix="hep-review-filter-r-")
        self.h = H.Harness(Path(self._tmp.name), config=FILTER_CFG).setup()
        self.h.start()
        round1(self.h)
        self.sid = to_filter_dispatch(self.h)

    def tearDown(self):
        self._tmp.cleanup()

    def receive(self, rec) -> dict:
        write_filter(self.h, self.sid, rec)
        return self.h.run("receive", self.sid)

    def test_codes(self):
        h, sid = self.h, self.sid
        cases = {"missing": ["decisions_incomplete"], "repeat": ["decisions_incomplete"],
                 "unknown-decision": ["schema_invalid"], "unknown-id": ["decisions_incomplete"],
                 "dup-of-dropped": ["duplicate_target"]}
        for mode, codes in cases.items():
            with self.subTest(mode=mode):
                rec = filter_record(h, sid, mode)
                self.assertEqual(sorted({c for c, _ in R.filter_receipt_codes(rec, self.ctx(rec))}), codes)
        rec = filter_record(h, sid, identity=H.AUTHOR)
        self.assertEqual([c for c, _ in R.filter_receipt_codes(rec, self.ctx(rec))], ["same_identity"])
        rec = filter_record(h, sid)
        rec["isolation"]["saw_prior_conversation"] = True
        self.assertEqual([c for c, _ in R.filter_receipt_codes(rec, self.ctx(rec))], ["prior_conversation"])
        rec = filter_record(h, sid)
        rec["dispatch_nonce"] = "wrong"
        self.assertEqual([c for c, _ in R.filter_receipt_codes(rec, self.ctx(rec))], ["dispatch_mismatch"])
        rec = filter_record(h, sid)
        rec["paths_read"].append({"path": str(h.project / h.doc_rel), "sha256": H.sha(h.project / h.doc_rel)})
        self.assertEqual([c for c, _ in R.filter_receipt_codes(rec, self.ctx(rec))], ["read_outside_packet"])
        rec = filter_record(h, sid)
        rec["paths_read"][0]["sha256"] = "0" * 64
        self.assertEqual([c for c, _ in R.filter_receipt_codes(rec, self.ctx(rec))], ["file_hash_mismatch"])
        self.assertEqual(R.filter_receipt_codes(filter_record(h, sid), self.ctx(filter_record(h, sid))), [])

    def ctx(self, rec):
        from review_lib import receipt as REC
        st = self.h.st()
        k = self.h.latest_attempt(self.sid)
        ids = json.loads((self.h.rv.private_attempt(1, self.sid, k) / "filter_ids.json").read_text())["ids"]
        return REC.build_filter_context(self.h.rv, r=1, sid=self.sid, k=k, dispatched=self.h.dispatched(self.sid),
                                        author=st["author"]["identity"], shared=[], instructions_changed=False,
                                        finding_ids=sorted(ids), record=rec)

    def test_driver_rejects_and_the_filter_is_not_applied_after_two_attempts(self):
        h, sid = self.h, self.sid
        out = self.receive(filter_record(h, sid, "repeat"))
        self.assertEqual((out["status"], out["codes"]), ("rejected", ["decisions_incomplete"]))
        act = h.next()
        self.assertEqual((act["action"], act["slots"]), ("dispatch", [sid]))
        h.run("dispatch", sid, expect=0)
        out = self.receive(filter_record(h, sid, "dup-of-dropped"))
        self.assertEqual((out["status"], out["codes"]), ("rejected", ["duplicate_target"]))
        snap = R.snapshot(h.st())
        self.assertEqual((snap["slots"][sid]["state"], snap["slots"][sid]["kind"]), ("exhausted", "filter"))
        act = h.next()
        self.assertEqual(act["action"], "dispose")  # not escalate: an exhausted filter is only not applied
        self.assertNotIn("filter", act)
        h.run("report", expect=0)
        text = (h.rv.dir / "report.md").read_text(encoding="utf-8")
        self.assertIn("Not applied: the filter slot used up its attempts", text)
        self.assertNotIn("## Findings the filter dropped", text)

    def test_returned_empty_and_timeout_use_the_usual_rows(self):
        h, sid = self.h, self.sid
        h.run("returned", sid, expect=0)
        act = h.next()
        self.assertEqual((act["row"], act["action"], act["slots"]), (5, "withdraw", [sid]))
        h.run("withdraw", sid, "--reason", "host-failure", expect=0)
        act = h.next()
        self.assertEqual((act["action"], act["slots"]), ("dispatch", [sid]))
        h.run("dispatch", sid, expect=0)
        h.now(120)
        act = h.next()
        self.assertEqual((act["row"], act["action"]), (6, "withdraw"))
        h.run("withdraw", sid, "--reason", "timeout", expect=0)
        self.assertEqual(h.next()["action"], "dispose")

    def test_check_record_only_role_filter(self):
        import subprocess
        import sys
        p = Path(self._tmp.name) / "rec.json"
        p.write_text(json.dumps(filter_record(self.h, self.sid)), encoding="utf-8")
        cli = [sys.executable, str(H.PLUGIN / "contracts" / "review.py"), "check", "--record-only", str(p), "--role", "filter"]
        res = subprocess.run(cli, capture_output=True, text=True, timeout=60)
        self.assertEqual(res.returncode, 0, res.stdout)
        p.write_text(json.dumps(filter_record(self.h, self.sid, "repeat")), encoding="utf-8")
        res = subprocess.run(cli, capture_output=True, text=True, timeout=60)
        self.assertEqual(res.returncode, 1)
        self.assertIn("decisions_incomplete", res.stdout)


class FilterConfigTests(unittest.TestCase):
    def test_start_option_writes_the_filter(self):
        with tempfile.TemporaryDirectory() as t:
            h = H.Harness(Path(t)).setup()
            (h.project / "reviews" / "review-config.json").unlink()
            h.run("start", h.doc_rel, "--seed", "7", "--models", ",".join(MODELS3), "--lens-model", "design=model-c",
                  "--filter-model", "model-f", expect=0)
            cfg = json.loads((h.project / "reviews" / "review-config.json").read_text(encoding="utf-8"))
            self.assertEqual(cfg, FILTER_CFG)
            self.assertEqual(h.st()["rounds"][1]["config"], cfg)
            other = h.project / "docs" / "other.md"
            other.write_text(H.DOC.replace("small design note", "second note"), encoding="utf-8")
            out = h.run("start", "docs/other.md", "--filter-model", "model-g")
            self.assertEqual(out["_exit"], 2)
            self.assertIn("finish them first", out["error"])
            out = h.run("start", "docs/other.md", "--filter-model", " ")
            self.assertEqual(out["_exit"], 2)

    def test_config_rules(self):
        self.assertEqual(R.config_problems(FILTER_CFG), [])
        self.assertTrue(R.config_problems(dict(FILTER_CFG, filter={})))
        self.assertTrue(R.config_problems(dict(FILTER_CFG, filter={"model": "m", "extra": 1})))
        self.assertEqual(R.config_problems(dict(FILTER_CFG, filter={"model": "not-in-models"})), [])
        self.assertIsNone(R.effective_config({"models": ["m"]})["filter"])
        self.assertEqual(R.weak_config(FILTER_CFG), [])


class UnchangedWithoutOptionsTests(unittest.TestCase):
    def test_no_filter_row_slot_or_event_without_the_option(self):
        with tempfile.TemporaryDirectory() as t:
            h = H.Harness(Path(t)).setup()
            h.start()
            round1(h, extra_findings=2)
            act = h.next()
            self.assertEqual(act["action"], "dispose")
            self.assertNotIn("filter", act)
            self.assertFalse(R.snapshot(h.st())["filter_needed"])
            self.assertNotIn("filter_needed", [e["event"] for e in h.rv.events()])
            self.assertNotIn("filter", {v["role"] for v in h.rv.slots()["1"].values()})
            h.run("report", expect=0)
            text = (h.rv.dir / "report.md").read_text(encoding="utf-8")
            self.assertNotIn("Filtering pass", text)
            self.assertNotIn("lens_models", text)
            self.assertIn("| Finding | Severity | State | Disposition | Verification |\n", text)

    def test_no_filter_when_round_1_has_only_control_findings(self):
        with tempfile.TemporaryDirectory() as t:
            h = H.Harness(Path(t), config=FILTER_CFG).setup()
            h.start()
            round1(h, extra_findings=0)
            st = h.st()
            self.assertTrue(st["findings"])  # the control findings, closed as auto-canary
            self.assertEqual(R.filter_pool(st), [])
            self.assertEqual(h.next()["action"], "close")


if __name__ == "__main__":
    unittest.main()
