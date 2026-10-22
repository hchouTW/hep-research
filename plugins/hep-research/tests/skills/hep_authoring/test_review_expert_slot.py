"""The optional expert slot of round 1 (contracts 3.6.0; docs/dev/independent-review-spec.md sections 5.1, 5.2, 6.10,
7.6 and A8), the per-review configuration (start --own-config) and the identity scrub of the filter packet, driven
in-process with scripted reviewer, expert, filter and arbiter agents. Synthetic data only.

- --expert-model: the expert slot is allocated in round 1 with a random label and dispatched with the other round-1
  slots; its packet is the whole document without canaries and no lens scope; receipt rejects its record by the rules
  of spec 7.6; its accepted findings go to the filter, to dispose and to the report like any other; a changed expert
  finding is confirmed by the design lens in round 2; no expert slot in round 2; an exhausted expert never escalates.
- --own-config: the review carries its own configuration file (recorded in round_started), the shared file is not
  changed, concurrent reviews may use different settings, and observe and check watch the review's own file.
- The filter packet's free text has the raising slot's id, its identity and the model names removed, with counts in
  the private directory."""
from __future__ import annotations

import json
import re
import tempfile
import unittest
from pathlib import Path

from tests.skills.hep_authoring import review_harness as H
from contracts import review as R

MODELS = ["model-a", "model-b"]
BASE_CFG = {"config_version": "1.0.0", "models": MODELS}
EXPERT_ID = "expert-agent-1"


def all_deep_and_focus(h: H.Harness, sids) -> set:
    out = set()
    for sid in sids:
        scope = h.packet(sid)[0]
        out |= set(scope.get("deep_units", [])) | set(scope.get("focus_units", []))
        out |= {c["unit"] for c in h.canaries(sid)}
    return out


def free_units(h: H.Harness, sids, n: int = 1) -> list[str]:
    """Sentence units no lens or shadow slot judges in depth and no canary touches (so no conflict arises)."""
    used = all_deep_and_focus(h, [s for s in sids if h.slot_info(s)["role"] in ("lens", "shadow")])
    table = json.loads(h.rv.units_path(h.st()["round"]).read_text(encoding="utf-8"))["units"]
    return [u["id"] for u in table if u["kind"] == "sentence" and u["id"] not in used][:n]


def expert_record(h: H.Harness, sid: str, unit: str, mode: str = "good", identity: str = EXPERT_ID) -> dict:
    """An expert record with one error on unit; mode breaks one rule of spec 7.6."""
    d = h.dispatched(sid)
    adir = h.adir(sid)
    value = h.unit_text(unit).strip()[:30]
    rec = {"packet_sha256": d["packet_sha256"], "dispatch_nonce": d["nonce"],
           "instructions_sha256": d["instructions_sha256"], "role": "expert",
           "reviewer": {"identity": identity, "context": "fresh", "model": "model-x", "host": "claude-code",
                        "slot_id": sid},
           "isolation": {"saw_prior_conversation": False, "host_injected": ["memory file"],
                         "instruction_files_seen": "unknown"},
           "paths_read": [{"path": f"packet/{n}", "sha256": H.sha(adir / "packet" / n)}
                          for n in ("document.md", "instructions.md", "scope.json", "units.json")],
           "evidence": [{"id": "E1", "basis": "locator", "ref": str(H.LICENSE), "lines": "2-3", "sha256": H.sha(H.LICENSE),
                         "source_kind": "page"}],
           "claims": [{"id": "C1", "units": [unit], "summary": "A general statement of the page."}],
           "verdicts": [{"claim_id": "C1", "verdict": "unsupported", "rationale": "False in the limit the page covers.",
                         "evidence_ids": ["E1"], "finding_ids": ["F1"], "refutation_attempts": []}],
           "findings": [{"id": "F1", "kind": "other", "severity": "medium", "units": [unit], "value": value,
                         "correction": "a statement restricted to the regime where it holds",
                         "description": f"Slot {sid} ({identity}, running on MODEL-X) finds this false in one regime.",
                         "fix": f"Restrict the statement; reported by {sid}."}],
           "limitations": "Synthetic scripted expert."}
    if mode == "unbacked":
        rec["verdicts"][0].update(verdict="unresolved", finding_ids=[])
    elif mode == "no-evidence":
        rec["verdicts"][0]["evidence_ids"] = []
    elif mode == "skim":
        rec["skim"] = [{"unit": unit, "mark": "ok"}]
    elif mode == "value":
        rec["findings"][0]["value"] = "text that is not in the unit"
    elif mode == "no-finding":
        rec["verdicts"][0]["finding_ids"] = []
        rec["findings"] = []
    elif mode == "copy":
        rec["paths_read"].append({"path": str(h.project / h.doc_rel), "sha256": H.sha(h.project / h.doc_rel)})
    elif mode == "self-citation":
        rec["evidence"].append({"id": "E2", "basis": "internal", "units": [unit]})
        rec["verdicts"][0]["evidence_ids"].append("E2")
    elif mode == "wrong-role":
        rec["role"] = "reviewer"
    elif mode == "nothing-found":
        rec.update(claims=[], verdicts=[], findings=[])
    return rec


def write_expert(h: H.Harness, sid: str, rec: dict):
    (h.adir(sid) / "review_record.json").write_text(json.dumps(rec, indent=1, ensure_ascii=False), encoding="utf-8")


def filter_record(h: H.Harness, sid: str) -> dict:
    d = h.dispatched(sid)
    adir = h.adir(sid)
    ids = [f["id"] for f in json.loads((adir / "packet" / "findings.json").read_text(encoding="utf-8"))["findings"]]
    return {"packet_sha256": d["packet_sha256"], "dispatch_nonce": d["nonce"],
            "instructions_sha256": d["instructions_sha256"], "role": "filter",
            "reviewer": {"identity": "filter-agent", "context": "fresh", "model": "model-f", "host": "claude-code",
                         "slot_id": sid},
            "isolation": {"saw_prior_conversation": False, "host_injected": [], "instruction_files_seen": "unknown"},
            "paths_read": [{"path": "packet/findings.json", "sha256": H.sha(adir / "packet" / "findings.json")}],
            "decisions": [{"finding_id": x, "decision": "keep", "reason": "The page should change."} for x in ids],
            "limitations": "Synthetic scripted filter."}


def start_expert(h: H.Harness, *extra) -> dict:
    return h.run("start", h.doc_rel, "--seed", h.seed, "--own-config", "--expert-model", "model-x", *extra, expect=0)


class ExpertEndToEndTests(unittest.TestCase):
    """--own-config with the expert slot and the filter: round 1 (the expert rejected once, then accepted, with a
    design-lens finding naming its own slot), the filter over both, dispose (the expert finding changed), round 2 with
    the design lens confirming the expert's change and no expert slot, close; check exits 0."""

    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory(prefix="hep-review-expert-")
        h = cls.h = H.Harness(Path(cls._tmp.name), config=BASE_CFG).setup()
        cls.shared_before = (h.project / "reviews" / "review-config.json").read_bytes()
        cls.start = start_expert(h, "--filter-model", "model-f")
        cls.esid = cls.start["expert_slot"]
        cls.dispatch_act = act = h.next()
        H.dispatch_all(h, act)
        cls.packet_dir = h.adir(cls.esid) / "packet"
        cls.unit = free_units(h, act["slots"])[0]
        cls.unit_text1 = h.unit_text(cls.unit)
        cls.expert_value = cls.unit_text1.strip()[:30]
        cls.design1 = h.slot_of("lens", "design")
        for sid in act["slots"]:
            if sid == cls.esid:
                write_expert(h, sid, expert_record(h, sid, cls.unit, "unbacked"))
            else:
                rec = h.good_record(sid)
                if sid == cls.design1:
                    pick = h.design_only_units(sid, exclude=[cls.unit])[0]
                    rec = h.good_record(sid, findings=[(pick, "low", "partially-supported")])
                    f = rec["findings"][-1]
                    f["description"] = f"Seen by {sid} (reviewer-{sid}-1) on Model-A; the s{sid[1:]} label is not mine."
                h.write_record(sid, rec)
            h.run("returned", sid, expect=0)
        act = h.next()
        assert act["action"] == "receive", act
        cls.receipts = {sid: h.run("receive", sid) for sid in act["slots"]}
        act = h.next()
        assert (act["action"], act["slots"]) == ("dispatch", [cls.esid]), act
        h.run("dispatch", cls.esid, expect=0)
        write_expert(h, cls.esid, expert_record(h, cls.esid, cls.unit))
        h.run("returned", cls.esid, expect=0)
        cls.accepted = h.run("receive", cls.esid)
        act = h.next()
        assert (act["action"], act["row"]) == ("filter", "8a"), act
        cls.fsid = h.run("filter", expect=0)["slot"]
        H.dispatch_all(h, h.next())
        cls.filter_packet = json.loads((h.adir(cls.fsid) / "packet" / "findings.json").read_text(encoding="utf-8"))
        cls.filter_ids = json.loads((h.rv.private_attempt(1, cls.fsid, 1) / "filter_ids.json").read_text(encoding="utf-8"))
        (h.adir(cls.fsid) / R.FILTER_SIDECAR).write_text(json.dumps(filter_record(h, cls.fsid)), encoding="utf-8")
        h.run("returned", cls.fsid, expect=0)
        assert h.run("receive", cls.fsid)["status"] == "ok"
        cls.dispose_act = act = h.next()
        assert act["action"] == "dispose", act
        cls.expert_finding = f"1/{cls.esid}/F1"
        for g in act["findings"]:
            if g == cls.expert_finding:
                text = h.unit_text(cls.unit)
                h.write_doc(h.read_doc().replace(text, text[:-1] + ", in the regime where it holds.", 1))
                h.run("dispose", g, "--as", "changed", "--reason", "restricted", "--verified", "locator:LICENSE:2-3",
                      expect=0)
            else:
                h.run("dispose", g, "--as", "declined", "--reason", "a preference", expect=0)
        cls.carry2 = None
        for _ in range(60):
            act = h.next()
            a = act["action"]
            if a == "rereview":
                h.run("rereview", expect=0)
            elif a == "dispatch":
                H.dispatch_all(h, act)
                for sid in act["slots"]:
                    info = h.slot_info(sid)
                    if info["role"] == "lens" and info["lens"] == "design":
                        cls.carry2 = h.packet(sid)[0]["carry_forward"]
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

    # --own-config
    def test_own_config_file_recorded_and_shared_file_untouched(self):
        h = self.h
        self.assertEqual((h.project / "reviews" / "review-config.json").read_bytes(), self.shared_before)
        own = h.rv.dir / "review-config.json"
        cfg = json.loads(own.read_text(encoding="utf-8"))
        self.assertEqual(cfg, dict(BASE_CFG, expert={"model": "model-x"}, filter={"model": "model-f"}))
        rs = [e["data"] for e in self.events if e["event"] == "round_started"]
        self.assertEqual([d["config_file"] for d in rs], [f"reviews/{h.rv.id}/review-config.json"] * 2)
        self.assertEqual({d["config_sha256"] for d in rs}, {H.sha(own)})
        self.assertEqual(rs[0]["config"], cfg)
        self.assertEqual(self.start["config"], f"reviews/{h.rv.id}/review-config.json")
        self.assertIn(f"| configuration file | `reviews/{h.rv.id}/review-config.json` (this review's own) | - |", self.report)

    # the expert slot in round 1
    def test_expert_slot_allocated_with_the_round_1_slots(self):
        slots = self.h.rv.slots()
        self.assertEqual(slots["1"][self.esid], {"role": "expert", "lens": None, "model": "model-x"})
        rs1 = [e["data"] for e in self.events if e["event"] == "round_started"][0]
        self.assertEqual(rs1["expert"], {"slot_id": self.esid, "model": "model-x"})
        self.assertIn({"slot_id": self.esid, "model": "model-x"}, rs1["slots"])
        self.assertIn(self.esid, self.dispatch_act["slots"])
        self.assertEqual(len(self.dispatch_act["slots"]), len(slots["1"]) - 1)  # all but the later filter slot
        self.assertNotIn("expert", {v["role"] for v in slots["2"].values()})
        rs2 = [e["data"] for e in self.events if e["event"] == "round_started"][1]
        self.assertNotIn("expert", rs2)

    def test_expert_packet(self):
        names = sorted(p.name for p in self.packet_dir.iterdir())
        self.assertEqual(names, ["document.md", "instructions.md", "manifest.json", "scope.json", "units.json"])
        scope = json.loads((self.packet_dir / "scope.json").read_text(encoding="utf-8"))
        self.assertEqual(scope, {"slot_id": self.esid, "lens": None, "role": "expert", "max_units_per_claim": 3})
        units = json.loads((self.packet_dir / "units.json").read_text(encoding="utf-8"))["units"]
        self.assertTrue(all(u["in_scope"] is False and u["role"] is None for u in units))
        doc = (self.packet_dir / "document.md").read_text(encoding="utf-8")
        self.assertTrue(doc.endswith(H.DOC))  # the original text: no canary
        d = [e["data"] for e in self.events if e["event"] == "dispatched" and e["data"]["slot_id"] == self.esid]
        self.assertEqual([(x["attempt"], x["canaries"], x["canaries_expected"]) for x in d], [(1, 0, 0), (2, 0, 0)])
        self.assertEqual(json.loads((self.h.rv.private_attempt(1, self.esid, 1) / "canary.json").read_text())["canaries"], [])
        text = (self.packet_dir / "instructions.md").read_text(encoding="utf-8")
        for part in ("R0 isolation self-check", "--role expert", "finding_without_verdict", "basis_missing",
                     "Never read any other copy or version of the document", "whole of document.md",
                     "There are no controls in this slot", "Role: `expert`"):
            self.assertIn(part, text)
        for part in ("skim_missing", "deep_missing", "canary", "carry_forward"):
            self.assertNotIn(part, text)
        others = [s for s in self.h.rv.slots()["1"] if s != self.esid]
        for name in ("instructions.md", "scope.json", "units.json", "manifest.json"):
            t = (self.packet_dir / name).read_text(encoding="utf-8")
            for sid in others:
                self.assertIsNone(re.search(rf"\b{sid}\b", t), (name, sid))
        from review_lib.packet import extract_example
        self.assertEqual(R.record_rules(extract_example(text), "expert", 3), [])

    def test_expert_rejected_then_accepted(self):
        out = self.receipts[self.esid]
        self.assertEqual((out["status"], out["codes"]), ("rejected", ["finding_without_verdict"]))
        self.assertEqual(self.accepted["status"], "ok")
        acc = [e["data"] for e in self.events if e["event"] == "accepted" and e["data"]["slot_id"] == self.esid][0]
        self.assertEqual(acc["metrics"], {"verdicts": {"unsupported": 1}, "findings": 1,
                                          "bases": {"independent": 1, "external": 0, "internal": 0, "tool-output": 0}})
        self.assertEqual(acc["verdicts"][0]["eligible"], True)
        self.assertEqual(acc["findings"], [{"id": "F1", "kind": "other", "severity": "medium", "units": [self.unit]}])

    def test_expert_findings_go_to_filter_and_dispose(self):
        fn = [e["data"] for e in self.events if e["event"] == "filter_needed"][0]
        self.assertIn(self.expert_finding, fn["findings"])
        self.assertIn(self.expert_finding, self.dispose_act["findings"])
        self.assertIn(self.expert_finding, self.dispose_act["filter"])

    def test_filter_packet_scrubbed(self):
        """The expert's and the design lens's own slot ids, identities and model names are gone from the free text;
        the counts are private; value and unit_texts are untouched."""
        ids = self.filter_ids["ids"]
        by_ref = {v: k for k, v in ids.items()}
        texts = json.dumps(self.filter_packet)
        for x in (self.esid, EXPERT_ID, "MODEL-X", "model-x", self.design1, f"reviewer-{self.design1}-1", "Model-A"):
            self.assertIsNone(re.search(rf"(?<![A-Za-z0-9_]){re.escape(x)}(?![A-Za-z0-9_])", texts), x)
        fx = next(f for f in self.filter_packet["findings"] if f["id"] == by_ref[self.expert_finding])
        self.assertEqual(fx["description"], "Slot [redacted] ([redacted], running on [redacted]) finds this false in one "
                                            "regime.")
        self.assertEqual(fx["fix"], "Restrict the statement; reported by [redacted].")
        self.assertEqual((fx["value"], fx["unit_texts"]), (self.expert_value, {self.unit: self.unit_text1}))
        design_ref = next(g for g in ids.values() if g.split("/")[1] == self.design1)
        fd = next(f for f in self.filter_packet["findings"] if f["id"] == by_ref[design_ref])
        self.assertEqual(fd["description"], f"Seen by [redacted] ([redacted]) on [redacted]; the s{self.design1[1:]} "
                                            "label is not mine.")
        sc = self.filter_ids["scrubbed"]
        self.assertEqual(sc["findings"][by_ref[self.expert_finding]], {"slot_id": 2, "identity": 1, "model": 1})
        self.assertEqual(sc["findings"][by_ref[design_ref]], {"slot_id": 1, "identity": 1, "model": 1})
        self.assertEqual(sc["total"], {"slot_id": 3, "identity": 2, "model": 2})
        self.assertIn("Reviewer identity removed from the findings' free text (latest attempt): 3 slot ids, "
                      "2 reviewer identities, 2 model names.", self.report)
        for name in ("findings.json", "scope.json", "instructions.md"):
            self.assertNotIn("scrubbed", (self.h.rv.attempt_dir(1, self.fsid, 1) / "packet" / name).read_text(
                encoding="utf-8"))

    def test_changed_expert_finding_confirmed_by_the_design_lens(self):
        design2 = next(s for s, v in self.h.rv.slots()["2"].items() if v["role"] == "lens" and v["lens"] == "design")
        plan = [e["data"] for e in self.events if e["event"] == "round_started"][1]["carry_forward"]
        mine = [c for c in plan[design2] if c["target"] == self.expert_finding]
        self.assertEqual([c["kind"] for c in mine], ["finding"])
        self.assertIn(mine[0]["ref"], [c["ref"] for c in self.carry2])  # in the design lens's packet
        conf = [e["data"]["finding"] for e in self.events if e["event"] == "change_confirmed"]
        self.assertIn(self.expert_finding, conf)
        self.assertEqual(self.h.st()["findings"][self.expert_finding]["state"], "change-confirmed")

    def test_closed_check_ok_and_report(self):
        self.assertEqual(self.events[-1]["event"], "closed")
        res = R.check(self.h.rv.dir)
        self.assertEqual(res["status"], "ok", res)
        r = self.report
        self.assertIn("| expert | model model-x | - |", r)
        self.assertIn("## Expert slot", r)
        self.assertIn(f"- Round 1, slot {self.esid}, model model-x: 2 attempt(s), accepted (a1: rejected "
                      "finding_without_verdict).", r)
        self.assertIn(f"- Findings: 1 ({self.expert_finding}); they are disposed like any other.", r)
        self.assertIn(f"| 1 | {self.esid} | expert | - | model-x | 2 | accepted |", r)
        self.assertIn("unsupported 1", r.split(f"| 1 | {self.esid} | expert |", 1)[1].split("\n", 1)[0])

    def test_check_catches_an_edited_own_config(self):
        p = self.h.rv.dir / "review-config.json"
        orig = p.read_bytes()
        try:
            p.write_bytes(orig.replace(b"model-x", b"model-y"))
            res = R.check(self.h.rv.dir)
            self.assertEqual(res["status"], "fail")
            self.assertIn(f"reviews/{self.h.rv.id}/review-config.json",
                          [d for c in res["codes"] if c["code"] == "artifacts_changed" for d in c["detail"]])
        finally:
            p.write_bytes(orig)


class ExpertReceiptTests(unittest.TestCase):
    """Each bad expert record alone gets its code; an exhausted expert slot is not escalated."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(prefix="hep-review-expert-r-")
        h = self.h = H.Harness(Path(self._tmp.name), config=dict(BASE_CFG, expert={"model": "model-x"})).setup()
        out = h.start()
        self.sid = out["expert_slot"]
        act = h.next()
        H.dispatch_all(h, act)
        self.slots = act["slots"]
        self.unit = free_units(h, act["slots"])[0]

    def tearDown(self):
        self._tmp.cleanup()

    def ctx(self, rec):
        from review_lib import receipt as REC
        st = self.h.st()
        return REC.build_context(self.h.rv, r=1, sid=self.sid, k=self.h.latest_attempt(self.sid),
                                 slot=self.h.slot_info(self.sid), dispatched=self.h.dispatched(self.sid),
                                 author=st["author"]["identity"], shared=[], instructions_changed=False, parties=[],
                                 item_lenses={}, record=rec)

    def codes(self, mode, **kw):
        rec = expert_record(self.h, self.sid, self.unit, mode, **kw)
        return sorted({c for c, _ in R.receipt_codes(rec, self.ctx(rec))})

    def test_codes(self):
        cases = {"good": [], "nothing-found": [], "unbacked": ["finding_without_verdict"],
                 "no-evidence": ["basis_missing"], "skim": ["schema_invalid"], "value": ["finding_shape"],
                 "no-finding": ["verdict_without_finding"], "copy": ["read_outside_packet"],
                 "self-citation": ["self_citation"], "wrong-role": ["schema_invalid"]}
        for mode, codes in cases.items():
            with self.subTest(mode=mode):
                self.assertEqual(self.codes(mode), codes)
        self.assertEqual(self.codes("good", identity=H.AUTHOR), ["same_identity"])
        self.assertTrue(set(R.EXPERT_CODES) >= {"finding_without_verdict", "basis_missing", "finding_shape"})
        self.assertFalse(set(R.EXPERT_CODES) & {"canary_missed", "deep_missing", "skim_missing", "carry_forward_missing",
                                                "unresolved_dominant"})

    def test_copy_of_the_document_elsewhere_is_rejected(self):
        """The copy guard: a file holding the document's text outside the packet counts as a copy."""
        copy = self.h.project / "notes" / "draft-copy.md"
        copy.parent.mkdir(parents=True, exist_ok=True)
        copy.write_text(H.DOC, encoding="utf-8")
        rec = expert_record(self.h, self.sid, self.unit)
        rec["paths_read"].append({"path": str(copy), "sha256": H.sha(copy)})
        self.assertEqual([c for c, _ in R.receipt_codes(rec, self.ctx(rec))], ["read_outside_packet"])

    def test_isolation_self_check(self):
        rec = expert_record(self.h, self.sid, self.unit)
        rec["isolation"]["saw_prior_conversation"] = True
        self.assertEqual([c for c, _ in R.receipt_codes(rec, self.ctx(rec))], ["prior_conversation"])

    def test_exhausted_expert_is_not_escalated(self):
        h = self.h
        for sid in self.slots:
            if sid == self.sid:
                write_expert(h, sid, expert_record(h, sid, self.unit, "no-evidence"))
            else:
                h.write_record(sid, h.good_record(sid))
            h.run("returned", sid, expect=0)
        for sid in h.next()["slots"]:
            h.run("receive", sid)
        act = h.next()
        self.assertEqual((act["action"], act["slots"]), ("dispatch", [self.sid]))
        h.run("dispatch", self.sid, expect=0)
        write_expert(h, self.sid, expert_record(h, self.sid, self.unit, "value"))
        out = h.run("receive", self.sid)
        self.assertEqual((out["status"], out["codes"]), ("rejected", ["finding_shape"]))
        snap = R.snapshot(h.st())
        self.assertEqual((snap["slots"][self.sid]["state"], snap["slots"][self.sid]["kind"]), ("exhausted", "expert"))
        act = h.next()
        self.assertEqual(act["action"], "close")  # not escalate; only control findings, closed as auto-canary
        h.run("report", expect=0)
        text = (h.rv.dir / "report.md").read_text(encoding="utf-8")
        self.assertIn("Not applied: the expert slot used up its attempts; nothing escalates.", text)

    def test_returned_empty_and_timeout(self):
        h = self.h
        h.run("returned", self.sid, expect=0)
        act = h.next()
        self.assertEqual((act["row"], act["action"], act["slots"]), (5, "withdraw", [self.sid]))
        h.run("withdraw", self.sid, "--reason", "host-failure", expect=0)
        act = h.next()
        self.assertEqual((act["action"], act["slots"]), ("dispatch", [self.sid]))

    def test_check_record_only_role_expert(self):
        import subprocess
        import sys
        p = Path(self._tmp.name) / "rec.json"
        cli = [sys.executable, str(H.PLUGIN / "contracts" / "review.py"), "check", "--record-only", str(p), "--role",
               "expert"]
        p.write_text(json.dumps(expert_record(self.h, self.sid, self.unit)), encoding="utf-8")
        res = subprocess.run(cli, capture_output=True, text=True, timeout=60)
        self.assertEqual(res.returncode, 0, res.stdout)
        p.write_text(json.dumps(expert_record(self.h, self.sid, self.unit, "unbacked")), encoding="utf-8")
        res = subprocess.run(cli, capture_output=True, text=True, timeout=60)
        self.assertEqual(res.returncode, 1)
        self.assertIn("finding_without_verdict", res.stdout)


class ExpertOnlyDispatchTests(unittest.TestCase):
    """How an evaluation runs only the expert slot: start with --own-config --expert-model, dispatch the slot start
    names (expert_slot), and receive it; the other slots stay undispatched and nothing else is needed."""

    def test_dispatch_and_receive_only_the_expert(self):
        with tempfile.TemporaryDirectory() as t:
            h = H.Harness(Path(t), config=BASE_CFG).setup()
            sid = start_expert(h)["expert_slot"]
            act = h.next()
            self.assertEqual(act["action"], "dispatch")
            self.assertIn(sid, act["slots"])
            out = h.run("dispatch", sid, expect=0)
            self.assertTrue(out["message"].startswith("Read and follow the instruction file below exactly.\n"))
            unit = free_units(h, [sid])[0]
            write_expert(h, sid, expert_record(h, sid, unit))
            h.run("returned", sid, expect=0)
            self.assertEqual(h.next()["action"], "receive")
            self.assertEqual(h.run("receive", sid)["status"], "ok")
            self.assertEqual(sorted(g for g in h.st()["findings"]), [f"1/{sid}/F1"])
            self.assertEqual(h.next()["action"], "dispatch")  # the lens and shadow slots were never dispatched


class ConflictWithExpertTests(unittest.TestCase):
    """An expert verdict that contradicts a lens's supported verdict on the same unit forms a conflict item; its lenses
    name the expert, so the arbiter needs external evidence."""

    def test_conflict_item_and_arbiter(self):
        with tempfile.TemporaryDirectory() as t:
            h = H.Harness(Path(t), config=dict(BASE_CFG, expert={"model": "model-x"})).setup()
            esid = h.start()["expert_slot"]
            act = h.next()
            H.dispatch_all(h, act)
            facts = h.slot_of("lens", "facts")
            cu = {c["unit"] for c in h.canaries(facts)}
            unit = next(u for u in h.packet(facts)[0]["deep_units"] if u not in cu)
            for sid in act["slots"]:
                if sid == esid:
                    write_expert(h, sid, expert_record(h, sid, unit))
                else:
                    h.write_record(sid, h.good_record(sid))
                h.run("returned", sid, expect=0)
            for sid in h.next()["slots"]:
                self.assertEqual(h.run("receive", sid)["status"], "ok", sid)
            act = h.next()
            self.assertEqual(act["action"], "arbitrate")
            self.assertTrue(any(esid in (it["first"] or "") + (it["second"] or "") for it in act["items"]))
            h.run("arbitrate", expect=0)
            items = [e["data"] for e in h.rv.events() if e["event"] == "arbitration_needed"]
            mine = [it for it in items if esid in (it["first"] or "") + (it["second"] or "")]
            self.assertTrue(mine)
            self.assertIn("expert", mine[0]["lenses"])
            act = h.next()
            self.assertEqual(act["action"], "dispatch")
            for sid in act["slots"]:
                h.run("dispatch", sid, expect=0)
                items_json = h.packet(sid)[2]
                self.assertTrue(items_json)


class OwnConfigTests(unittest.TestCase):
    """Concurrent reviews with different settings; observe and repair watch the review's own file."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(prefix="hep-review-own-")
        self.h = H.Harness(Path(self._tmp.name), config=BASE_CFG).setup()
        self.shared = self.h.project / "reviews" / "review-config.json"
        for name in ("b", "c", "d"):
            (self.h.project / "docs" / f"{name}.md").write_text(H.DOC.replace("small design note", f"note {name}"),
                                                              encoding="utf-8")

    def tearDown(self):
        self._tmp.cleanup()

    def test_concurrent_reviews_with_different_settings(self):
        h = self.h
        a = h.start()["review_id"]  # uses the shared file
        before = self.shared.read_bytes()
        out = h.run("start", "docs/b.md", "--own-config", "--filter-model", "model-f", "--models", "model-c,model-d",
                    "--lens-model", "design=model-d", expect=0)
        b = out["review_id"]
        self.assertEqual(self.shared.read_bytes(), before)
        own_b = json.loads((h.project / "reviews" / b / "review-config.json").read_text(encoding="utf-8"))
        self.assertEqual(own_b, {"config_version": "1.0.0", "models": ["model-c", "model-d"],
                                 "lens_models": {"design": "model-d"}, "filter": {"model": "model-f"}})
        out = h.run("start", "docs/c.md", "--own-config", "--expert-model", "model-x", expect=0)
        self.assertNotIn("filter", json.loads((h.project / "reviews" / out["review_id"] / "review-config.json").read_text()))
        # changing the shared file is still refused while review a (shared) is open, and only a is named
        out = h.run("start", "docs/d.md", "--filter-model", "model-g")
        self.assertEqual(out["_exit"], 2)
        self.assertIn(f"review(s) {a} also use", out["error"])
        self.assertIn("--own-config", out["error"])
        self.assertEqual(self.shared.read_bytes(), before)
        # each review's next sees its own configuration and no config_changed
        for rid in (a, b):
            self.assertNotEqual(h.run("next", "--review", rid)["action"], "repair")

    def test_shared_file_change_allowed_when_only_own_config_reviews_are_open(self):
        h = self.h
        h.run("start", "docs/b.md", "--own-config", "--expert-model", "model-x", expect=0)
        out = h.run("start", "docs/c.md", "--filter-model", "model-g", expect=0)
        self.assertEqual(json.loads(self.shared.read_text())["filter"], {"model": "model-g"})
        self.assertNotIn("config", out)

    def test_own_config_without_a_shared_file(self):
        h = self.h
        self.shared.unlink()
        out = h.run("start", h.doc_rel, "--own-config", "--models", "model-a,model-b", expect=0)
        self.assertFalse(self.shared.exists())
        own = h.project / "reviews" / out["review_id"] / "review-config.json"
        self.assertEqual(json.loads(own.read_text()), BASE_CFG)

    def test_observe_watches_the_own_file(self):
        h = self.h
        rid = h.run("start", h.doc_rel, "--own-config", "--expert-model", "model-x", expect=0)["review_id"]
        self.shared.write_text(json.dumps(dict(BASE_CFG, filter={"model": "other"})), encoding="utf-8")
        self.assertEqual(h.next()["action"], "dispatch")  # the shared file is not this review's
        own = h.project / "reviews" / rid / "review-config.json"
        orig = own.read_bytes()
        own.write_text(json.dumps(dict(BASE_CFG, expert={"model": "model-y"})), encoding="utf-8")
        act = h.next()
        self.assertEqual((act["action"], act["codes"]), ("repair", ["config_changed"]))
        out = h.run("repair", "config_changed", expect=0)
        self.assertEqual(out["detail"], f"reviews/{rid}/review-config.json")
        own.write_bytes(orig)
        self.assertEqual(h.next()["action"], "dispatch")

    def test_bad_option_values(self):
        h = self.h
        out = h.run("start", h.doc_rel, "--own-config", "--expert-model", " ")
        self.assertEqual(out["_exit"], 2)
        out = h.run("start", h.doc_rel, "--own-config", "--lens-model", "design=not-a-model")
        self.assertEqual(out["_exit"], 2)
        self.assertIn("config_out_of_range", out["error"])
        self.assertEqual(sorted(p.name for p in (h.project / "reviews").iterdir()), ["review-config.json"])


class UnchangedWithoutOptionsTests(unittest.TestCase):
    def test_no_expert_slot_config_file_or_report_lines(self):
        with tempfile.TemporaryDirectory() as t:
            h = H.Harness(Path(t)).setup()
            out = h.start()
            self.assertNotIn("expert_slot", out)
            self.assertNotIn("config", out)
            rs = h.rv.events()[0]["data"]
            self.assertNotIn("expert", rs)
            self.assertNotIn("config_file", rs)
            self.assertNotIn("expert", {v["role"] for v in h.rv.slots()["1"].values()})
            self.assertFalse((h.rv.dir / "review-config.json").exists())
            self.assertEqual(R.fold(h.rv.events())["expert_slots"], {})
            h.run("report", expect=0)
            text = (h.rv.dir / "report.md").read_text(encoding="utf-8")
            for part in ("Expert slot", "| expert |", "configuration file"):
                self.assertNotIn(part, text)


if __name__ == "__main__":
    unittest.main()
