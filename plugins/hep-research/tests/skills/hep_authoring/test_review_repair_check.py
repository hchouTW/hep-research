"""Repair codes (spec 7.3) and overall check codes (spec 7.4) of the independent review (acceptance criterion 2):
each is triggered and gives its documented result (repair action, fail, incomplete, warning or a report listing).
Synthetic data only."""
from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path

from tests.skills.hep_authoring import review_harness as H
from contracts import review as R


class RepairTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory(prefix="hep-review-repair-")
        cls.base = H.Harness(Path(cls._tmp.name) / "base").setup()
        cls.base.start()
        H.dispatch_all(cls.base, cls.base.next())

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    def setUp(self):
        self._t = tempfile.TemporaryDirectory(prefix="hep-review-case-")
        self.h = self.base.copy(Path(self._t.name))

    def tearDown(self):
        self._t.cleanup()

    def repair_codes(self):
        out = self.h.next()
        self.assertEqual((out["action"], out["row"]), ("repair", 3), out)
        return out["codes"]

    def test_clean_state_needs_no_repair(self):
        self.assertEqual(self.h.next()["action"], "await")

    def test_config_changed(self):
        cfg = dict(self.h.config, deep_sample=15)
        (self.h.project / "reviews" / "review-config.json").write_text(json.dumps(cfg), encoding="utf-8")
        self.assertEqual(self.repair_codes(), ["config_changed"])

    def test_config_out_of_range(self):
        cfg = dict(self.h.config, deep_sample=99)
        (self.h.project / "reviews" / "review-config.json").write_text(json.dumps(cfg), encoding="utf-8")
        self.assertIn("config_out_of_range", self.repair_codes())
        out = self.h.run("repair", "config_out_of_range", expect=0)
        self.assertTrue(any("deep_sample" in x for x in out["detail"]))

    def test_canary_in_deliverable(self):
        st = self.h.st()
        c = self.h.canaries(self.h.slot_of("lens", "facts"))[0]
        self.h.write_doc(self.h.read_doc() + "\n" + c["mutated"] + "\n")
        self.assertIn("canary_in_deliverable", self.repair_codes())
        self.assertTrue(st)

    def test_isolation_precondition(self):
        self.h.obs["host"]["precondition"] = "none"
        self.h.save_obs()
        self.assertEqual(self.repair_codes(), ["isolation_precondition"])

    def test_isolation_not_yet_effective(self):
        self.h.obs["host"].update(session_start="2026-01-01T08:00:00Z", settings_mtime="2026-01-01T08:30:00Z")
        self.h.save_obs()
        self.assertEqual(self.repair_codes(), ["isolation_not_yet_effective"])

    def test_no_session_start_is_a_warning_not_a_repair(self):
        self.h.next()
        obs = [e for e in self.h.rv.events() if e["event"] == "observed"][-1]["data"]
        self.assertEqual(obs["repair"], [])
        self.assertTrue(any("cannot confirm" in w for w in obs["warnings"]))

    def test_fork_denied_is_a_warning(self):
        self.h.obs["host"]["precondition"] = "fork-denied"
        self.h.save_obs()
        self.assertEqual(self.h.next()["action"], "await")
        obs = [e for e in self.h.rv.events() if e["event"] == "observed"][-1]["data"]
        self.assertTrue(any("Agent(fork)" in w for w in obs["warnings"]))

    def test_shared_dir_contamination(self):
        shared = self.h.root / "shared"
        shared.mkdir()
        nonce = self.h.dispatched(self.h.slot_of("lens", "facts"))["nonce"]
        old = shared / "old-note.txt"
        old.write_text(f"REVIEW-DISPATCH nonce={nonce}", encoding="utf-8")
        os.utime(old, (946684800, 946684800))  # 2000-01-01, outside every attempt window
        self.h.obs["shared_dirs"] = [str(shared)]
        self.h.save_obs()
        self.assertEqual(self.repair_codes(), ["shared_dir_contamination"])
        out = self.h.run("repair", "shared_dir_contamination", expect=0)
        self.assertEqual(out["detail"], [str(old)])

    def test_shared_dir_file_inside_an_attempt_window_is_listed_only(self):
        shared = self.h.root / "shared"
        shared.mkdir()
        f = shared / "tool-output.txt"
        f.write_text(self.h.dispatched(self.h.slot_of("lens", "facts"))["nonce"], encoding="utf-8")
        t = self.h.t.timestamp() - 30
        os.utime(f, (t, t))
        self.h.obs["shared_dirs"] = [str(shared)]
        self.h.save_obs()
        self.assertEqual(self.h.next()["action"], "await")
        obs = [e for e in self.h.rv.events() if e["event"] == "observed"][-1]["data"]
        self.assertEqual(obs["shared_dirs"]["in_window"], [str(f)])

    def test_change_without_edit(self):
        h = self.h
        for sid in h.rv.slots()["1"]:
            info = h.slot_info(sid)
            design = info["role"] == "lens" and info["lens"] == "design"
            extra = [(h.design_only_units(sid)[0], "medium", "partially-supported")] if design else []
            h.write_record(sid, h.good_record(sid, findings=extra))
        while True:
            act = h.next()
            if act["action"] != "receive":
                break
            for sid in act["slots"]:
                h.run("receive", sid, expect=0)
        self.assertEqual(act["action"], "dispose")
        g = act["findings"][0]
        h.run("dispose", g, "--as", "changed", "--reason", "fixed", "--verified", "person:author,2026-01-01", expect=0)
        self.assertEqual(self.repair_codes(), ["change_without_edit"])
        self.assertIn(g, h.run("repair", "change_without_edit", expect=0)["detail"])


class CheckTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory(prefix="hep-review-check-")
        cls.closed, _ = H.run_e2e(Path(cls._tmp.name) / "closed")
        cls.mid, _ = H.run_e2e(Path(cls._tmp.name) / "mid", stop_at="round1-accepted")

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    def setUp(self):
        self._t = tempfile.TemporaryDirectory(prefix="hep-review-case-")

    def tearDown(self):
        self._t.cleanup()

    def codes(self, h):
        res = R.check(getattr(h, "rv", h).dir)
        return res["status"], {c["code"]: c for c in res["codes"]}

    def test_closed_review_passes_with_warnings(self):
        status, codes = self.codes(self.closed)
        self.assertEqual(status, "ok")
        self.assertEqual(codes["adopted_unverified"]["result"], "warning")
        self.assertEqual(codes["no_control"]["result"], "warning")

    def test_log_broken(self):
        h = self.closed.copy(Path(self._t.name))
        lines = h.rv.log.read_text(encoding="utf-8").splitlines(keepends=True)
        rec = json.loads(lines[2])
        rec["time"] = "2026-01-01T09:00:59Z"
        lines[2] = json.dumps(rec, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n"
        h.rv.log.write_text("".join(lines), encoding="utf-8")
        status, codes = self.codes(h)
        self.assertEqual((status, codes["log_broken"]["result"]), ("fail", "fail"))

    def test_log_broken_head(self):
        h = self.closed.copy(Path(self._t.name))
        head = json.loads(h.rv.head.read_text())
        head["count"] -= 1
        h.rv.head.write_text(json.dumps(head))
        self.assertIn("log_broken", self.codes(h)[1])

    def test_not_closed_and_finding_open(self):
        status, codes = self.codes(self.mid)
        self.assertEqual(status, "incomplete")
        self.assertEqual(codes["not_closed"]["result"], "incomplete")
        self.assertEqual(codes["finding_open"]["result"], "incomplete")

    def test_changed_after_close(self):
        h = self.closed.copy(Path(self._t.name))
        h.write_doc(h.read_doc() + "\nA later edit.\n")
        status, codes = self.codes(h)
        self.assertEqual((status, codes["changed_after_close"]["result"]), ("fail", "fail"))

    def test_artifacts_changed(self):
        h = self.closed.copy(Path(self._t.name))
        p = next(h.rv.dir.glob("round-1/*/attempt-1/packet/scope.json"))
        p.write_text(p.read_text() + " ", encoding="utf-8")
        status, codes = self.codes(h)
        self.assertEqual((status, codes["artifacts_changed"]["result"]), ("fail", "fail"))

    def test_artifacts_changed_sidecar_and_units(self):
        for target in ("units/round-1.json", "round-1/S1/attempt-1/review_record.json"):
            with self.subTest(target=target), tempfile.TemporaryDirectory() as t:
                h = self.closed.copy(Path(t))
                p = h.rv.dir / target
                p.write_text(p.read_text() + "\n", encoding="utf-8")
                self.assertIn(target, json.dumps(self.codes(h)[1]["artifacts_changed"]["detail"]))

    def test_uphold_not_honored(self):
        h = self.closed.copy(Path(self._t.name))
        events = h.rv.events()
        n = next(i for i, e in enumerate(events) if e["event"] == "arbitration_resolved")
        g = next(e["data"]["finding"] for e in events if e["event"] == "arbitration_needed")
        # rebuild the log up to the uphold, then a decline the driver would refuse
        h.rv.log.unlink()
        h.rv.head.unlink()
        for e in events[:n + 1]:
            h.rv.append(e["event"], e["time"], e["data"])
        h.rv.append("disposed", events[n]["time"], {"finding": g, "disposition": "declined", "reason": "no", "verification": None,
                                                    "edited_units": [], "finding_units": [], "round": 1, "by": "author-agent"})
        status, codes = self.codes(h)
        self.assertEqual((status, codes["uphold_not_honored"]["result"]), ("fail", "fail"))
        out = h.run("dispose", g, "--as", "declined", "--reason", "again")  # the driver itself refuses
        self.assertEqual(out["_exit"], 2)

    def test_no_model_diversity_weak_config_shortfall(self):
        cfg = {"config_version": "1.0.0", "models": ["only-model"], "unresolved_max_ratio": 0.49, "canaries_per_slot": 3}
        with tempfile.TemporaryDirectory() as t:
            h = H.Harness(Path(t), config=cfg).setup()
            h.start()
            H.dispatch_all(h, h.next())
            status, codes = self.codes(h)
            self.assertEqual(status, "incomplete")
            for c in ("no_model_diversity", "weak_config", "canary_shortfall", "no_control"):
                self.assertEqual(codes[c]["result"], "warning", c)
            self.assertEqual(codes["weak_config"]["detail"], ["unresolved_max_ratio"])  # 3 canaries is stricter

    def test_superseded_reviews_and_late_records(self):
        with tempfile.TemporaryDirectory() as t:
            h = H.Harness(Path(t)).setup()
            h.start()
            H.dispatch_all(h, h.next())
            sid = h.slot_of("lens", "bypass")
            h.run("withdraw", sid, "--reason", "other", "--explanation", "the host crashed", expect=0)
            h.write_record(sid, h.good_record(sid))
            h.next()
            self.assertIn("late", [e["event"] for e in h.rv.events()])
            old = h.rv.id
            self.assertEqual(h.run("start", h.doc_rel, "--seed", "8")["_exit"], 2)  # an unfinished review exists
            h.run("start", h.doc_rel, "--seed", "8", "--supersede", old, "--reason", "restart", expect=0)
            from review_lib.store import Review
            status, codes = self.codes(Review(h.project, old, h.state / "hep-research" / "reviews"))
            self.assertEqual(codes["late_records"]["result"], "listing")
            new = [x for x in (h.project / "reviews").iterdir() if x.is_dir() and x.name != old][0]
            status, codes = self.codes(Review(h.project, new.name, h.state / "hep-research" / "reviews"))
            self.assertEqual(codes["superseded_reviews"]["detail"], [old])

    def test_every_check_code_has_a_test(self):
        text = Path(__file__).read_text(encoding="utf-8")
        for code in R.CHECK_CODES:
            self.assertIn(code, text)
        for code in R.REPAIR_CODES:
            self.assertIn(f"test_{code}", text)


if __name__ == "__main__":
    unittest.main()


class FollowUpTests(unittest.TestCase):
    """Regressions found in code review: CRLF documents, refused appends, check on a relative path."""

    def test_crlf_document_is_not_seen_as_changed(self):
        with tempfile.TemporaryDirectory() as t:
            h = H.Harness(Path(t)).setup()
            (h.project / h.doc_rel).write_bytes(H.DOC.replace("\n", "\r\n").encode("utf-8"))
            h.start()
            self.assertEqual(h.next()["action"], "dispatch")
            obs = [e for e in h.rv.events() if e["event"] == "observed"][-1]["data"]
            self.assertEqual(obs["document_sha256"], h.st()["rounds"][1]["source_sha256"])

    def test_append_refuses_a_time_earlier_than_the_log(self):
        with tempfile.TemporaryDirectory() as t:
            h = H.Harness(Path(t)).setup()
            h.start()
            n = len(h.rv.events())
            out = h.run("next", minutes=-30)
            self.assertEqual(out["_exit"], 2)
            self.assertIn("earlier than the last event", out["error"])
            self.assertEqual(len(h.rv.events()), n)
            h.now(60)
            self.assertEqual(h.next()["action"], "dispatch")  # the log still verifies

    def test_check_on_a_relative_path(self):
        with tempfile.TemporaryDirectory() as t:
            h = H.Harness(Path(t)).setup()
            h.start()
            cwd = os.getcwd()
            try:
                os.chdir(h.rv.dir)
                self.assertEqual(R.check(Path("."))["status"], "incomplete")
            finally:
                os.chdir(cwd)
