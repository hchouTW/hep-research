"""hep-review CLI (scripts/review.py): JSON with a status key and the exit-code contract (0 ok, 1 negative verdict,
2 bad input), the R0 path through the CLI and export verification."""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "skills" / "hep-review" / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from contracts import hep_review as H  # noqa: E402
from hep_review_support import continuity as C  # noqa: E402
from hep_review_support import export as X  # noqa: E402
from hep_review_support import store as S  # noqa: E402
import store_fixtures as F  # noqa: E402

CLI = ROOT / "skills" / "hep-review" / "scripts" / "review.py"


def cli(*args):
    r = subprocess.run([sys.executable, str(CLI), *args], capture_output=True, text=True, timeout=120)
    return r.returncode, json.loads(r.stdout)


class Cli(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.d = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_r0_through_the_cli(self):
        b = self.d / "r0.json"
        b.write_bytes(H.encode({"intent": F.intent(), "plan": F.plan(1, [F.obligation("O1")]),
                                "answers": [{"obligation_id": "O1", "outcome": "supported", "reasoning": "ok"}]}))
        code, out = cli("r0", "--bundle", str(b))
        self.assertEqual((code, out["status"], out["tier"]), (0, "ok", "R0"))
        self.assertNotIn("no still-valid defect", out["text"])

    def test_verify_export_exit_codes(self):
        s = S.Store(self.d / "store", location=F.TEMP_LOCATION)
        try:
            st = C.start_session(s, "ctx-1", "s")
            for i, o in enumerate(([F.intent()], [F.manifest(s)], [F.plan(1, [F.obligation("O1")])]), 1):
                C.append(s, st, o, f"op-{i}")
            line = C.checkpoint_line(s, "ctx-1")
            X.export(s, "ctx-1", self.d / "e.json")
        finally:
            s.close()
        code, out = cli("verify-export", str(self.d / "e.json"), "--checkpoint", line)
        self.assertEqual((code, out["status"], out["checkpoint"]), (0, "ok", "matches"))
        doc = json.loads((self.d / "e.json").read_bytes())
        doc["commits"][1]["objects"][0]["materials"][0]["view_version"] = "edited"
        (self.d / "bad.json").write_bytes(H.encode(doc))
        code, out = cli("verify-export", str(self.d / "bad.json"))
        self.assertEqual((code, out["status"]), (1, "refused"))
        code, out = cli("verify-export", str(self.d / "missing.json"))
        self.assertEqual((code, out["status"]), (2, "rejected"))

    def test_checkpoint_command_prints_the_handover_line(self):
        s = S.Store(self.d / "store", location=F.TEMP_LOCATION)
        try:
            st = C.start_session(s, "ctx-1", "s")
            C.append(s, st, [F.intent()], "op-1")
            expected = C.checkpoint_line(s, "ctx-1")
        finally:
            s.close()
        loc = S.check_location(self.d)
        if not loc["supported"]:
            self.skipTest(f"temp folder location not supported here: {loc['reason']}")
        code, out = cli("--store", str(self.d / "store"), "checkpoint", "--context", "ctx-1")
        self.assertEqual((code, out["checkpoint"]), (0, expected))


if __name__ == "__main__":
    unittest.main()
