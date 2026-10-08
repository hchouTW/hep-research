"""T4.2: execution-bundle freezing. A bundle lists every file that defines what runs, by full SHA-256; any change
after freezing (code, defaults, environment, image, recorded exposure) is detected, and a submission bound to a bundle
is refused when the campaign changed. Freezing approves nothing. Synthetic campaigns only."""
import json
import os
import shlex
import sys
import tempfile
import unittest
from pathlib import Path

from core.partition import bundle as bd
from core.partition import campaign as cp
from core.partition import engine
from tests.core.partition_helpers import WORKER, ScriptedExecutor

PINNED = "registry.example/analysis@sha256:" + "a" * 64


class BundleTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.worker = root / "worker"
        (self.worker / "lib").mkdir(parents=True)
        (self.worker / "work.py").write_text(WORKER)
        (self.worker / "lib" / "defaults.json").write_text('{"threshold": 1.0}')
        (self.worker / "__pycache__").mkdir()
        (self.worker / "__pycache__" / "x.pyc").write_bytes(b"cache")
        self.lock = root / "env.lock"
        self.lock.write_text("numpy==2.5.3\n")
        q = shlex.quote
        self.cmd = (f"{q(sys.executable)} {q(str(self.worker / 'work.py'))} --start {{start}} --stop {{stop}} "
                    "--seed {seed} --out {out} --id {id}")
        self.manifest = engine.make_manifest("synthetic-bundle", 8, 4, 3)
        self.cdir = cp.init(root / "camp", self.manifest, self.cmd)

    def tearDown(self):
        self.tmp.cleanup()

    def freeze(self, **kw):
        return bd.freeze(self.cdir, self.worker, self.lock, **kw)

    def test_bundle_lists_every_role_with_full_hashes(self):
        doc = self.freeze(scope="synthetic test", config={"limits": {"max_total_jobs": 4}}, config_hash="c" * 64)
        roles = {(f["role"], f["path"]) for f in doc["files"]}
        self.assertTrue({("campaign", "manifest.json"), ("campaign", "spec.json"), ("campaign", "runner.py"),
                         ("worker", "work.py"), ("worker", "lib/defaults.json"), ("environment", "env.lock")} <= roles)
        self.assertIn(("interpreter", Path(os.path.realpath(sys.executable)).name), roles)
        interp = next(f for f in doc["files"] if f["role"] == "interpreter")
        self.assertEqual(interp["named_as"], sys.executable)
        self.assertFalse(any("__pycache__" in p for _, p in roles))
        self.assertTrue(all(len(f["sha256"]) == 64 for f in doc["files"]))
        self.assertEqual(doc["data_exposure"], {"state": "unknown", "basis": "none"})
        self.assertEqual(doc["approval_request"]["bundle_digest"], doc["bundle_digest"])
        self.assertEqual(doc["approval_request"]["limits"], {"max_total_jobs": 4})
        self.assertIn("not an approval", doc["approval_request"]["note"])
        self.assertTrue(Path(doc["path"]).exists())
        self.assertEqual(bd.verify(bd.load(self.cdir, doc["bundle_digest"]))["status"], "identical")
        again = self.freeze(scope="synthetic test", config={"limits": {"max_total_jobs": 4}}, config_hash="c" * 64)
        self.assertTrue(again["reused"])
        with self.assertRaises(bd.BundleError) as err:  # same content, another request: refused, not overwritten
            self.freeze(scope="another scope")
        self.assertEqual(err.exception.code, "bundle.request_differs")

    def test_changes_after_freezing_are_detected(self):
        doc = self.freeze()
        for change in (lambda: (self.worker / "lib" / "defaults.json").write_text('{"threshold": 2.0}'),
                       lambda: (self.worker / "extra.py").write_text("x = 1\n"),
                       lambda: self.lock.write_text("numpy==2.6.0\n"),
                       lambda: os.chmod(self.worker / "work.py", 0o755)):
            with self.subTest(change=change):
                change()
                rep = bd.verify(doc)
                self.assertEqual(rep["status"], "different", rep)
        forged = dict(doc, data_exposure={"state": "unexposed", "basis": "structured-record"})
        self.assertEqual(bd.verify(forged)["differences"][0]["change"], "document")  # the digest binds the record

    def test_digest_depends_on_exposure_and_image(self):
        a = bd.build(self.cdir, self.worker, self.lock)
        b = bd.build(self.cdir, self.worker, self.lock, {"state": "exposed", "basis": "legacy-text"})
        self.assertNotEqual(a["bundle_digest"], b["bundle_digest"])
        for bad in ({"state": "unexposed", "basis": "legacy-text"}, {"state": "maybe", "basis": "none"}, "unknown"):
            with self.assertRaises(bd.BundleError):
                bd.build(self.cdir, self.worker, self.lock, bad)

    def test_unpinned_image_and_outside_paths_are_refused(self):
        root = Path(self.tmp.name)
        tagged = cp.init(root / "tagged", self.manifest, self.cmd, container_image="registry.example/analysis:latest")
        with self.assertRaises(bd.BundleError) as err:
            bd.build(tagged, self.worker)
        self.assertEqual(err.exception.code, "bundle.image_unpinned")
        pinned = cp.init(root / "pinned", self.manifest, self.cmd, container_image=PINNED)
        self.assertEqual(bd.build(pinned, self.worker)["container_image"], PINNED)
        with self.assertRaises(bd.BundleError) as err:  # no worker root: the worker script is outside the bundle
            bd.build(self.cdir)
        self.assertEqual(err.exception.code, "bundle.path_outside")
        os.symlink(self.worker / "work.py", self.worker / "link.py")
        with self.assertRaises(bd.BundleError) as err:
            bd.build(self.cdir, self.worker)
        self.assertEqual(err.exception.code, "bundle.not_regular")

    def test_submit_bound_to_a_bundle_refuses_a_changed_campaign(self):
        doc = self.freeze()
        ex = ScriptedExecutor({})
        rep = cp.submit(self.cdir, ex, {}, pilot=True, approved=True, bundle_digest=doc["bundle_digest"])
        state = json.loads((self.cdir / "state.json").read_text())
        self.assertEqual(state["submissions"][-1]["bundle_digest"], doc["bundle_digest"])
        self.assertEqual(len(rep["chunks"]), 1)
        (self.worker / "work.py").write_text(WORKER + "\n# edited after approval\n")
        before = (self.cdir / "state.json").read_text()
        with self.assertRaises(cp.CampaignError) as err:
            cp.submit(self.cdir, ex, {}, approved=True, bundle_digest=doc["bundle_digest"])
        self.assertEqual(err.exception.code, "bundle.changed")
        self.assertEqual((self.cdir / "state.json").read_text(), before)
        with self.assertRaises(cp.CampaignError) as err:
            cp.submit(self.cdir, ex, {}, approved=True, bundle_digest="0" * 64)
        self.assertEqual(err.exception.code, "bundle.unreadable")


if __name__ == "__main__":
    unittest.main()
