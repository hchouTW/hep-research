"""Packets and the instruction-file generator of the independent review (spec 5.2; acceptance criteria 7 and 11): for
each role the example extracted from the instructions.md actually written passes check --record-only, a corrupted
example stops the build, and no packet carries a hash of the document or a unit, canary originals or witnesses,
seeds, the slot table or the dispatch message. Synthetic data only."""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tests.skills.hep_authoring import review_harness as H
from contracts import review as R
from review_lib import packet as PKT
from review_lib import units as U

ALLOWED_UNIT_KEYS = {"id", "section", "kind", "text", "substantive", "in_scope", "role"}


class GeneratorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory(prefix="hep-review-gen-")
        cls.h, _ = H.run_e2e(Path(cls._tmp.name) / "a", stop_at="arbiter-dispatched")

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    def test_written_example_passes_record_only_for_each_role(self):
        roles = {"lens": self.h.slot_of("lens", "facts"), "shadow": self.h.slot_of("shadow", "design"),
                 "arbiter": self.h.slot_of("arbiter")}
        for role, sid in roles.items():
            with self.subTest(role=role):
                text = (self.h.adir(sid) / "packet" / "instructions.md").read_text(encoding="utf-8")
                ex = PKT.extract_example(text)
                rrole = "arbiter" if role == "arbiter" else "reviewer"
                self.assertEqual(R.record_rules(ex, rrole, 3), [])
                p = Path(self._tmp.name) / f"{role}.json"
                p.write_text(json.dumps(ex), encoding="utf-8")
                res = subprocess.run([sys.executable, str(H.PLUGIN / "contracts" / "review.py"), "check", "--record-only",
                                      str(p), "--role", rrole], capture_output=True, text=True, timeout=120)
                self.assertEqual(res.returncode, 0, res.stdout)
                self.assertIn("### Evidence bases", text)
                for basis in ("locator", "third-party", "tool-output", "exhaustive", "person", "internal"):
                    self.assertIn(f"| `{basis}` |", text)
                self.assertNotIn("canar", text.lower())

    def test_instructions_carry_this_slots_thresholds(self):
        sid = self.h.slot_of("shadow", "facts")
        text = (self.h.adir(sid) / "packet" / "instructions.md").read_text(encoding="utf-8")
        scope = self.h.packet(sid)[0]
        self.assertIn(f"total {scope['refutation_min_attempts_effective']} or more", text)
        self.assertIn("deep and focus units", text)

    def test_corrupted_example_stops_the_build(self):
        with tempfile.TemporaryDirectory() as t:
            h = H.Harness(Path(t)).setup()
            h.start()
            act = h.next()
            good = PKT.example_record

            def broken(kind, sid):
                ex = good(kind, sid)
                del ex["limitations"]
                return ex

            with mock.patch.object(PKT, "example_record", broken):
                out = h.run("dispatch", act["slots"][0])
            self.assertEqual((out["_exit"], out["status"]), (2, "error"))
            self.assertIn("output example fails check --record-only", out["error"])
            self.assertNotIn("dispatched", [e["event"] for e in h.rv.events()])
            self.assertFalse((h.rv.dir / "round-1" / act["slots"][0]).exists() and
                             any((h.rv.dir / "round-1" / act["slots"][0]).rglob("instructions.md")))


class PacketHygieneTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory(prefix="hep-review-hyg-")
        cls.h, _ = H.run_e2e(Path(cls._tmp.name) / "a")

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    def packets(self):
        return sorted(self.h.rv.dir.glob("round-*/*/attempt-*/packet"))

    def test_forbidden_content(self):
        rv = self.h.rv
        hashes = set()
        for p in sorted(rv.dir.glob("units/round-*.json")):
            t = json.loads(p.read_text(encoding="utf-8"))
            hashes.add(t["source_sha256"])
            hashes |= {u["text_sha256"] for u in t["units"]}
        for p in sorted(rv.private.glob("round-*/source.md")):
            hashes.add(U.sha256_text(p.read_text(encoding="utf-8")))
        seeds = json.loads((rv.private / "sample_seed").read_text())
        secrets = {seeds["master"], *seeds["rounds"].values()}
        for p in rv.private.glob("round-*/*/attempt-*/sample_seed"):
            secrets |= set(json.loads(p.read_text()).values())
        witnesses, nonces = [], [e["data"]["nonce"] for e in rv.events() if e["event"] == "dispatched"]
        for p in rv.private.glob("round-*/*/attempt-*/canary.json"):
            d = json.loads(p.read_text())
            secrets.add(d["salt"])
            witnesses += [json.dumps(c["witness_right"], sort_keys=True) for c in d["canaries"]]
            witnesses += [json.dumps(c["witness_wrong"], sort_keys=True) for c in d["canaries"]]
        secrets = {x for x in secrets if len(x) >= 16}  # the derived seeds and salts; the fixture's master seed is "7"
        self.assertGreater(len(secrets), 10)
        slots_json = (rv.private / "slots.json").read_text()
        self.assertTrue(self.packets())
        for pdir in self.packets():
            for f in sorted(pdir.iterdir()):
                text = f.read_text(encoding="utf-8")
                with self.subTest(file=str(f.relative_to(rv.dir))):
                    self.assertFalse([h for h in hashes if h in text], "a document or unit hash")
                    self.assertFalse([s for s in secrets if s in text], "a seed or salt")
                    self.assertFalse([n for n in nonces if n in text], "a dispatch nonce")
                    self.assertNotIn("Read and follow the instruction file below exactly.\nREVIEW-DISPATCH nonce=" + nonces[0], text)
                    self.assertFalse([w for w in witnesses if w in text], "a witness")
                    self.assertNotIn(slots_json.strip(), text)
                    self.assertNotIn('"role": "shadow"', text)
                    self.assertNotIn('"role": "lens"', text)
                    self.assertNotIn("canary", text.lower())

    def test_lens_packets_do_not_hold_the_canary_originals(self):
        rv = self.h.rv
        n = 0
        for p in rv.private.glob("round-*/*/attempt-*/canary.json"):
            rel = p.parent.relative_to(rv.private)
            doc = (rv.dir / rel / "packet" / "document.md").read_text(encoding="utf-8")
            units = (rv.dir / rel / "packet" / "units.json").read_text(encoding="utf-8")
            for c in json.loads(p.read_text())["canaries"]:
                n += 1
                self.assertNotIn(c["original"], doc)
                self.assertIn(c["mutated"], doc)
                self.assertNotIn(json.dumps(c["original"], ensure_ascii=False)[1:-1], units)
        self.assertGreater(n, 0)

    def test_units_json_allow_list(self):
        for pdir in self.packets():
            units = json.loads((pdir / "units.json").read_text(encoding="utf-8"))["units"]
            for u in units:
                self.assertEqual(set(u), ALLOWED_UNIT_KEYS)
                self.assertIsInstance(u["in_scope"], bool)

    def test_manifest_hash_is_the_packet_hash(self):
        st = R.fold(self.h.rv.events())
        for (r, sid), atts in st["attempts"].items():
            for k, a in atts.items():
                man = self.h.rv.attempt_dir(r, sid, k) / "packet" / "manifest.json"
                self.assertEqual(H.sha(man), a["dispatched"]["packet_sha256"])
                from contracts.schema import validate
                self.assertEqual(validate(json.loads(man.read_text()), "review_manifest.json").errors, [])


if __name__ == "__main__":
    unittest.main()
