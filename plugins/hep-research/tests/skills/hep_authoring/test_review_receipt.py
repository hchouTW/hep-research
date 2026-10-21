"""Receipt rules of the independent review (spec sections 7.1 and 7.2, acceptance criteria 1 and 9): for every reason
code, a minimal otherwise-valid record breaks exactly one condition, and receive writes rejected with that code and no
other. Synthetic data only."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tests.skills.hep_authoring import review_harness as H
from contracts import review as R


def _lens_base(root: Path) -> H.Harness:
    h = H.Harness(root).setup()
    h.start()
    H.dispatch_all(h, h.next())
    return h


class _Base(unittest.TestCase):
    """One dispatched round, copied for every test."""

    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory(prefix="hep-review-receipt-")
        cls.base = _lens_base(Path(cls._tmp.name) / "base")

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    def setUp(self):
        self._t = tempfile.TemporaryDirectory(prefix="hep-review-case-")
        self.h = self.base.copy(Path(self._t.name))

    def tearDown(self):
        self._t.cleanup()

    def receive(self, sid, rec):
        self.h.write_record(sid, rec)
        out = self.h.run("receive", sid)
        last = [e for e in self.h.rv.events() if e["event"] in ("accepted", "rejected")][-1]
        return out, last


class LensReceiptTests(_Base):
    def setUp(self):
        super().setUp()
        self.sid = self.h.slot_of("lens", "facts")
        self.rec = self.h.good_record(self.sid)
        scope, units, _ = self.h.packet(self.sid)
        self.cu = {c["unit"] for c in self.h.canaries(self.sid)}
        self.deep = [u for u in scope["deep_units"] if u not in self.cu]
        self.skim = [u for u in scope["skim_units"] if u not in self.cu]

    def verdict_of(self, unit):
        cid = next(c["id"] for c in self.rec["claims"] if c["units"] == [unit])
        return next(v for v in self.rec["verdicts"] if v["claim_id"] == cid)

    def assert_only(self, code):
        out, ev = self.receive(self.sid, self.rec)
        self.assertEqual(ev["event"], "rejected", out)
        self.assertEqual(ev["data"]["codes"], [code], ev["data"].get("problems"))

    def test_good_record_is_accepted(self):
        self.assertGreaterEqual(len(self.cu), 1)
        self.assertTrue(self.deep and self.skim)
        out, ev = self.receive(self.sid, self.rec)
        self.assertEqual(ev["event"], "accepted", out)

    def test_schema_invalid(self):
        del self.rec["limitations"]
        self.assert_only("schema_invalid")

    def test_packet_mismatch(self):
        self.rec["packet_sha256"] = "f" * 64
        self.assert_only("packet_mismatch")

    def test_dispatch_mismatch(self):
        self.rec["dispatch_nonce"] = "not-the-nonce"
        self.assert_only("dispatch_mismatch")

    def test_prior_conversation(self):
        self.rec["isolation"]["saw_prior_conversation"] = True
        self.assert_only("prior_conversation")

    def test_same_identity(self):
        self.rec["reviewer"]["identity"] = H.AUTHOR
        self.assert_only("same_identity")

    def test_finding_shape_value_not_an_excerpt(self):
        self.rec["findings"].append({"id": "F99", "kind": "other", "severity": "low", "units": [self.deep[0]],
                                     "value": "text that is not in the unit", "correction": "", "description": "x",
                                     "fix": ""})
        self.assert_only("finding_shape")

    def test_finding_shape_non_contiguous(self):
        a, b = self.deep[0], f"U{R.unit_pos(self.deep[0]) + 2:04d}"
        self.rec["findings"].append({"id": "F99", "kind": "other", "severity": "low", "units": [a, b],
                                     "value": "x", "correction": "", "description": "x", "fix": ""})
        self.assert_only("finding_shape")

    def test_read_outside_packet(self):
        doc = self.h.project / self.h.doc_rel
        self.rec["paths_read"].append({"path": str(doc), "sha256": H.sha(doc)})
        self.assert_only("read_outside_packet")

    def test_read_outside_packet_implementation_file(self):
        impl = H.PLUGIN / "contracts" / "review.py"
        self.rec["paths_read"].append({"path": str(impl), "sha256": H.sha(impl)})
        self.assert_only("read_outside_packet")

    def test_file_hash_mismatch(self):
        self.rec["paths_read"][0]["sha256"] = "0" * 64
        self.assert_only("file_hash_mismatch")

    def test_output_mismatch(self):
        self.rec["evidence"].append({"id": "E9", "basis": "tool-output", "command": "python3 x.py", "plugin_version": "0.21.0",
                                     "output_files": [{"path": "work/out.txt", "sha256": "0" * 64}]})
        self.assert_only("output_mismatch")

    def test_output_mismatch_outside_work(self):
        p = self.h.adir(self.sid) / "out.txt"
        p.write_text("x", encoding="utf-8")
        self.rec["evidence"].append({"id": "E9", "basis": "tool-output", "command": "python3 x.py", "plugin_version": "0.21.0",
                                     "output_files": [{"path": "out.txt", "sha256": H.sha(p)}]})
        self.assert_only("output_mismatch")

    def test_output_in_work_with_matching_hash_is_accepted(self):
        p = self.h.adir(self.sid) / "work" / "out.txt"
        p.write_text("x", encoding="utf-8")
        self.rec["evidence"].append({"id": "E9", "basis": "exhaustive", "script": "work/out.txt", "script_sha256": H.sha(p),
                                     "range": "all", "output_files": [{"path": "work/out.txt", "sha256": H.sha(p)}]})
        out, ev = self.receive(self.sid, self.rec)
        self.assertEqual(ev["event"], "accepted", out)

    def test_instructions_changed(self):
        self.h.obs["instruction_files"] = {"/fixture/CLAUDE.md": "b" * 64}
        self.h.save_obs()
        self.assert_only("instructions_changed")

    def test_claim_shape(self):
        self.rec["claims"].append({"id": "C99", "units": [self.deep[0]], "summary": "no verdict"})
        self.assert_only("claim_shape")

    def test_deep_missing(self):
        u = self.deep[0]
        cid = next(c["id"] for c in self.rec["claims"] if c["units"] == [u])
        self.rec["claims"] = [c for c in self.rec["claims"] if c["id"] != cid]
        self.rec["verdicts"] = [v for v in self.rec["verdicts"] if v["claim_id"] != cid]
        self.assert_only("deep_missing")

    def test_skim_missing(self):
        self.rec["skim"] = [s for s in self.rec["skim"] if s["unit"] != self.skim[0]]
        self.assert_only("skim_missing")

    def test_skim_missing_na_share(self):
        for s in self.rec["skim"]:
            if s["unit"] not in self.cu:
                s["mark"] = "n/a"
        self.assert_only("skim_missing")

    def test_basis_missing(self):
        u = self.deep[0]
        self.rec["evidence"].append({"id": "E2", "basis": "internal", "units": [f"U{R.unit_pos(u) + 10:04d}"]})
        self.verdict_of(u)["evidence_ids"] = ["E2"]
        self.assert_only("basis_missing")

    def test_self_citation(self):
        u = self.deep[0]
        self.verdict_of(u)["refutation_attempts"][0]["target"] = u
        self.assert_only("self_citation")

    def test_refutation_weak(self):
        self.verdict_of(self.deep[0])["refutation_attempts"] = []
        self.assert_only("refutation_weak")

    def test_verdict_without_finding(self):
        self.verdict_of(self.deep[0])["verdict"] = "partially-supported"
        self.assert_only("verdict_without_finding")

    def test_unresolved_dominant(self):
        for u in self.deep:
            self.verdict_of(u)["verdict"] = "unresolved"
        self.assert_only("unresolved_dominant")

    def test_canary_missed(self):
        for n, u in enumerate(sorted(self.cu)):
            v = self.verdict_of(u)
            v.update(verdict="supported", finding_ids=[],
                     refutation_attempts=[{"method": "m", "target": f"LICENSE:{90 + n}", "outcome": "ok"}])
        for s in self.rec["skim"]:
            if s["unit"] in self.cu:
                s.pop("finding_id", None)
                s["mark"] = "ok"
        self.rec["findings"] = [f for f in self.rec["findings"] if not set(f["units"]) & self.cu]
        self.assert_only("canary_missed")

    def test_carry_forward_missing(self):
        self.rec["carry_forward"] = [{"ref": "CF1", "status": "confirmed"}]
        self.assert_only("carry_forward_missing")

    def test_carry_forward_unmarked(self):
        ctx = {"kind": "lens", "lens": "design", "slot_id": "S1", "author": "a", "files": {},
               "dispatched": {"packet_sha256": "0" * 64, "nonce": "n", "instructions_sha256": "0" * 64},
               "limits": {"max_units_per_claim": 3, "na_max_ratio": 0.3, "unresolved_max_ratio": 0.3,
                          "refutation_duplicate_max": 0.2, "refutation_min_attempts_effective": 3},
               "unit_text": {}, "skim_units": [], "deep_units": [], "canaries": [], "carry_refs": ["CF1"]}
        rec = {"packet_sha256": "0" * 64, "dispatch_nonce": "n", "instructions_sha256": "0" * 64, "role": "reviewer",
               "reviewer": {"identity": "r", "context": "fresh", "model": "m", "host": "h", "slot_id": "S1"},
               "isolation": {"saw_prior_conversation": False, "host_injected": [], "instruction_files_seen": []},
               "paths_read": [], "evidence": [], "skim": [], "claims": [], "verdicts": [], "findings": [],
               "limitations": "none"}
        self.assertEqual([c for c, _ in R.receipt_codes(rec, ctx)], ["carry_forward_missing"])

    def test_every_lens_code_has_a_test(self):
        names = {n for n in dir(self) if n.startswith("test_")}
        for code in R.REVIEWER_CODES:
            self.assertTrue(any(n.startswith(f"test_{code}") for n in names), code)


class ShadowReceiptTests(_Base):
    def test_four_identical_refutation_attempts_are_refutation_weak(self):
        sid = self.h.slot_of("shadow", "facts")
        scope = self.h.packet(sid)[0]
        self.assertEqual(len(scope["focus_units"]), 4)
        self.assertEqual(scope["refutation_min_attempts_effective"], 4)  # min(5, 4 deep units), at least 3
        rec = self.h.good_record(sid)
        for v in rec["verdicts"]:
            v["refutation_attempts"] = [{"method": "same check", "target": "LICENSE:1", "outcome": "ok"}]
        self.assertEqual(sum(len(v["refutation_attempts"]) for v in rec["verdicts"]), 4)
        out, ev = self.receive(sid, rec)
        self.assertEqual(ev["data"]["codes"], ["refutation_weak"])

    def test_threshold_minimum_is_three(self):
        self.assertEqual(R.refutation_threshold({}, 1), 3)
        self.assertEqual(R.refutation_threshold({}, 4), 4)
        self.assertEqual(R.refutation_threshold({}, 40), 5)
        self.assertEqual(R.refutation_threshold({"refutation_min_attempts_for_ratio": 10}, 7), 7)


class ArbiterReceiptTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory(prefix="hep-review-arb-")
        cls.base, _ = H.run_e2e(Path(cls._tmp.name) / "base", stop_at="arbiter-dispatched")

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    def setUp(self):
        self._t = tempfile.TemporaryDirectory(prefix="hep-review-case-")
        self.h = self.base.copy(Path(self._t.name))
        self.sid = self.h.slot_of("arbiter")
        self.rec = self.h.good_record(self.sid, identity="arbiter-agent")

    def tearDown(self):
        self._t.cleanup()

    def assert_only(self, code):
        self.h.write_record(self.sid, self.rec)
        out = self.h.run("receive", self.sid)
        ev = [e for e in self.h.rv.events() if e["event"] in ("accepted", "rejected")][-1]
        self.assertEqual(ev["event"], "rejected", out)
        self.assertEqual(ev["data"]["codes"], [code], ev["data"].get("problems"))

    def test_good_arbiter_record_is_accepted_and_resolves(self):
        self.h.write_record(self.sid, self.rec)
        out = self.h.run("receive", self.sid, expect=0)
        self.assertIn("arbitration_resolved", out["events"])

    def test_arbiter_identity(self):
        st = self.h.st()
        it = next(iter(st["items"].values()))
        r, sid, _ = it["finding"].split("/", 2)
        k = max(st["attempts"][(int(r), sid)])
        party = json.loads((self.h.rv.attempt_dir(int(r), sid, k) / "review_record.json").read_text())["reviewer"]["identity"]
        self.rec["reviewer"]["identity"] = party
        self.assert_only("arbiter_identity")

    def test_arbiter_identity_author(self):
        self.rec["reviewer"]["identity"] = H.AUTHOR
        self.assert_only("arbiter_identity")

    def test_resolves_incomplete(self):
        self.rec["resolves"] = []
        self.assert_only("resolves_incomplete")

    def test_resolution_type(self):
        self.rec["resolves"][0]["conclusion"] = "uphold-first"
        self.assert_only("resolution_type")

    def test_resolution_basis(self):
        self.rec["resolves"][0]["evidence_ids"] = []
        self.assert_only("resolution_basis")

    def test_common_code_on_an_arbiter(self):
        self.rec["dispatch_nonce"] = "wrong"
        self.assert_only("dispatch_mismatch")


if __name__ == "__main__":
    unittest.main()


class PluginRelativePathTests(_Base):
    """A path relative to the plugin root resolves (found in the P3 pilot: reviewers cite plugin paths)."""

    def test_plugin_relative_path_is_accepted(self):
        sid = self.h.slot_of("lens", "facts")
        rec = self.h.good_record(sid)
        rec["paths_read"].append({"path": "LICENSE", "sha256": H.sha(H.LICENSE)})
        out, ev = self.receive(sid, rec)
        self.assertEqual(ev["event"], "accepted", out)

    def test_plugin_relative_path_with_wrong_hash_is_rejected(self):
        sid = self.h.slot_of("lens", "facts")
        rec = self.h.good_record(sid)
        rec["paths_read"].append({"path": "LICENSE", "sha256": "0" * 64})
        out, ev = self.receive(sid, rec)
        self.assertEqual(ev["data"]["codes"], ["file_hash_mismatch"])
