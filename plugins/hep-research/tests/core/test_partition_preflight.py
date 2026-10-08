"""AGENTIC-R5 T0.5: command templates and manifests are checked before a campaign or local run starts (X02 chunk-ID
path traversal; N07 template errors caught before submission)."""
from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from core.partition import campaign as cp  # noqa: E402
from core.partition import engine  # noqa: E402

GOOD = "python3 worker.py --start {start} --stop {stop} --seed {seed} --out {out} --tag {id}"


def rehash(m: dict) -> dict:
    body = {k: v for k, v in m.items() if k != "manifest_hash"}
    return dict(body, manifest_hash=engine._hash(body))


class TemplateTests(unittest.TestCase):
    def test_good_template(self):
        self.assertEqual(engine.check_template(GOOD)[-1], "c0000")
        self.assertTrue(engine.check_template("python3 -c 'print({{1: 2}})' {out}"))

    def test_rejected_templates(self):
        for bad in ("", "worker {} {out}", "worker {0} {out}", "worker {x} {out}", "worker {out.parent}",
                    "worker {out[0]}", "worker {out!r}", "worker {seed:04d} {out}", "worker { {out}", "worker } {out}",
                    "worker {start} {stop}", "worker '{out}"):
            with self.subTest(template=bad):
                with self.assertRaises(ValueError):
                    engine.check_template(bad)


class ManifestTests(unittest.TestCase):
    def setUp(self):
        self.m = engine.make_manifest("synthetic-test", 10, 4, 7)

    def test_made_manifest_is_valid(self):
        self.assertIs(engine.validate_manifest(self.m), self.m)

    def broken(self, edit, rehashed=True) -> dict:
        m = copy.deepcopy(self.m)
        edit(m)
        return rehash(m) if rehashed else m

    def test_rejected_manifests(self):
        cases = {
            "traversal id": lambda m: m["chunks"][0].update(id="../escape"),
            "slash id": lambda m: m["chunks"][0].update(id="a/b"),
            "duplicate id": lambda m: m["chunks"][1].update(id=m["chunks"][0]["id"]),
            "gap": lambda m: m["chunks"][1].update(start=5),
            "overlap": lambda m: m["chunks"][1].update(start=3),
            "short": lambda m: m["chunks"].pop(),
            "float seed": lambda m: m["chunks"][0].update(seed=1.5),
            "bool start": lambda m: m["chunks"][0].update(start=False),
            "job id newline": lambda m: m.update(job_id="a\nb"),
        }
        for name, edit in cases.items():
            with self.subTest(name):
                with self.assertRaises(ValueError):
                    engine.validate_manifest(self.broken(edit))

    def test_stale_hash_is_rejected(self):
        with self.assertRaises(ValueError):
            engine.validate_manifest(self.broken(lambda m: m["chunks"][0].update(seed=99), rehashed=False))


class EntryPointTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.d = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_campaign_init_refuses_before_writing(self):
        m = engine.make_manifest("synthetic-test", 4, 2, 1)
        bad = rehash(dict(m, chunks=[dict(m["chunks"][0], id="../x"), m["chunks"][1]]))
        for manifest, cmd, code in ((bad, GOOD, "campaign.bad_manifest"), (m, "worker {x} {out}", "campaign.bad_template")):
            with self.subTest(code=code):
                with self.assertRaises(cp.CampaignError) as ctx:
                    cp.init(self.d / code, manifest, cmd)
                self.assertEqual(ctx.exception.code, code)
                self.assertFalse((self.d / code).exists())

    def test_local_run_refuses(self):
        m = engine.make_manifest("synthetic-test", 4, 2, 1)
        mf = self.d / "m.json"
        mf.write_text(json.dumps(rehash(dict(m, chunks=[dict(m["chunks"][0], id="../x"), m["chunks"][1]]))))
        local = subprocess.run([sys.executable, str(ROOT / "skills/hep-computing/scripts/local_partition.py"), "run",
                                "--manifest", str(mf), "--state", str(self.d / "state"), "--cmd", GOOD],
                               capture_output=True, text=True, timeout=120)
        self.assertEqual(local.returncode, 2, local.stdout)
        self.assertFalse((self.d / "state").exists())


if __name__ == "__main__":
    unittest.main()
