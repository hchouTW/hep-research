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


class PortabilityTests(unittest.TestCase):
    """T03 H3: the runner is copied to batch workers whose python3 is older than the plugin's (EL9 ships 3.9), so
    it may use nothing newer than Python 3.9 (datetime.UTC, for one, arrived in 3.11)."""

    SOURCE = (ROOT / "core" / "partition" / "runner.py").read_text(encoding="utf-8")

    def test_runner_avoids_python_3_11_only_names(self):
        self.assertFalse("datetime.UTC" in self.SOURCE, "runner.py uses datetime.UTC (Python 3.11+); use datetime.timezone.utc")

    @unittest.skipUnless(Path("/usr/bin/python3").exists(), "no system python3")
    def test_runner_writes_its_records_under_the_system_python3(self):
        v = subprocess.run(["/usr/bin/python3", "-c", "import sys; print(sys.version_info[:2] < (3, 11))"], capture_output=True, text=True, timeout=60)
        if v.stdout.strip() != "True":
            self.skipTest("/usr/bin/python3 is 3.11 or newer; nothing older to test with")
        d = Path(tempfile.mkdtemp())
        man = make_manifest("t", 2, 1, 1)
        spec = {"manifest": man, "cmd": "/usr/bin/python3 -c \"import json,sys; json.dump({{'n': 1}}, open(sys.argv[1], 'w'))\" {out}"}
        (d / "spec.json").write_text(json.dumps(spec))
        p = subprocess.run(["/usr/bin/python3", str(ROOT / "core/partition/runner.py"), "--spec", str(d / "spec.json"),
                            "--out-dir", str(d / "o"), "--chunk", "c0000", "--attempt", "c0000-a01"],
                           capture_output=True, text=True, timeout=60)
        self.assertEqual(p.returncode, 0, p.stderr[-500:])
        self.assertEqual(json.loads((d / "o" / "c0000-a01.json").read_text())["result"], {"n": 1})


if __name__ == "__main__":
    unittest.main()
