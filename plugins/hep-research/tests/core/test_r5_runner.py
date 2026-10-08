"""R5 proposal for core/partition/runner.py: a command template that cannot be filled leaves a runner record."""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from core.partition.engine import make_manifest

ROOT = Path(__file__).resolve().parents[2]


class TemplateTests(unittest.TestCase):
    def test_runner_records_a_bad_template_as_failed(self):
        d = Path(tempfile.mkdtemp())
        man = make_manifest("t", 2, 1, 1)
        spec = {"manifest": man, "cmd": "python3 -c \"import json,sys; json.dump({'n': 1}, open(sys.argv[1], 'w'))\" {out}"}
        (d / "spec.json").write_text(json.dumps(spec))
        p = subprocess.run([sys.executable, str(ROOT / "core/partition/runner.py"), "--spec", str(d / "spec.json"),
                            "--out-dir", str(d / "o"), "--chunk", "c0000", "--attempt", "c0000-a01"],
                           capture_output=True, text=True, timeout=60)
        self.assertEqual(p.returncode, 2)
        meta = json.loads((d / "o" / "c0000-a01.meta.json").read_text())
        self.assertEqual(meta["exit_code"], 2)
        self.assertIn("{{", meta["runner_error"])


if __name__ == "__main__":
    unittest.main()
