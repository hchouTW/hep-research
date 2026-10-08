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

    def test_command_grammar_is_closed(self):
        root = Path(self.tmp.name)
        q = shlex.quote
        py, work = q(sys.executable), q(str(self.worker / "work.py"))
        tail = " --start {start} --stop {stop} --seed {seed} --id {id}"
        link = root / "alias.py"
        os.symlink(self.worker / "work.py", link)
        bad = [f"python3 {work} --out {{out}}", f"{py} work.py --out {{out}}", f"/usr/bin/env python3 {work} --out {{out}}",
               f"{py} -m evilmod --out {{out}}", f"{py} -c 'import evil' {work} --out {{out}}",
               f"{py} {work} --calib=/etc/hosts --out {{out}}", f"{py} {work} --calib ../outside.json --out {{out}}",
               f"{py} {work} --calib ~/x.json --out {{out}}", f"{py} {work} --calib lib/defaults.json --out {{out}}",
               f"{py} {work} calib=/etc/hosts --out {{out}}", f"{py} {work} -c/etc/hosts --out {{out}}",
               f"{py} {work} '$HOME/x' --out {{out}}", f"{py} {work} --calib={{out}}/../../etc/hosts --out {{out}}",
               f"{py} {work} {{id}}.py --out {{out}}", f"{py} {work} /etc/{{id}} --out {{out}}",
               f"{py} {work} 'C:\\x\\calib' --out {{out}}", f"{py} {work} \u2215etc\u2215hosts --out {{out}}",
               f"{py} {work} calib.json --out {{out}}", f"{py} {q(str(link))} --out {{out}}"]
        for i, cmd in enumerate(bad):
            cdir = cp.init(root / f"c{i}", self.manifest, cmd + tail)
            with self.subTest(cmd=cmd):
                with self.assertRaises(bd.BundleError):
                    bd.build(cdir, self.worker)
        ok = (f"{py} {work} --calib={q(str(self.worker / 'lib' / 'defaults.json'))} --scale 1.5 --shift -2 --mode fast "
              "-v --out={out}" + tail)
        doc = bd.build(cp.init(root / "ok", self.manifest, ok), self.worker)
        self.assertEqual([n["path"] for n in doc["named"]], ["work.py", "lib/defaults.json"])

    def test_repointing_a_named_directory_link_is_a_change(self):
        root = Path(self.tmp.name)
        os.symlink(self.worker, root / "current")
        other = root / "other"
        other.mkdir()
        (other / "work.py").write_text(WORKER + "# other code\n")
        cmd = (f"{shlex.quote(sys.executable)} {shlex.quote(str(root / 'current' / 'work.py'))} --start {{start}} "
               "--stop {stop} --seed {seed} --out {out} --id {id}")
        cdir = cp.init(root / "linked", self.manifest, cmd)
        doc = bd.freeze(cdir, self.worker)
        self.assertEqual(bd.verify(doc)["status"], "identical")
        os.unlink(root / "current")
        os.symlink(other, root / "current")
        self.assertIn("resolves elsewhere", [d["change"] for d in bd.verify(doc)["differences"]])

    def test_format_fields_in_paths_and_edited_specs(self):
        root = Path(self.tmp.name)
        cdir = cp.init(root / "edited", self.manifest, self.cmd)
        spec = json.loads((cdir / "spec.json").read_text())
        decoy = self.worker / "{id:.>2.0}" / "etc"
        decoy.mkdir(parents=True)
        (decoy / "hosts").write_text("decoy")
        for cmd in (self.cmd + f" --calib={self.worker}/{{id:.>2.0}}/etc/hosts",  # renders to <W>/../etc/hosts
                    self.cmd + " --x={out!r}", self.cmd.replace("--id {id}", "--id {id.real}")):
            spec["cmd"] = cmd
            (cdir / "spec.json").write_text(json.dumps(spec))  # edited after init: freeze checks the template again
            with self.subTest(cmd=cmd[-40:]):
                with self.assertRaises(bd.BundleError):
                    bd.build(cdir, self.worker)

    def test_shebang_interpreters_are_hashed_and_launchers_refused(self):
        root = Path(self.tmp.name)
        tail = " --start {start} --stop {stop} --seed {seed} --out {out} --id {id}"
        py = os.path.realpath(sys.executable)
        exe = self.worker / "run.py"
        os.chmod(self.worker, 0o755)
        bin_dir = root / "bin"
        bin_dir.mkdir()
        os.symlink("/usr/bin/env", bin_dir / "myenv")
        bad = {"#!/usr/bin/env python3": "bundle.bad_shebang", f"#!{bin_dir / 'myenv'}": "bundle.launcher",
               "#!/bin/sh /tmp/evil.sh": "bundle.bad_shebang", f"#!{py} -mpkg": "bundle.bad_shebang",
               f"#!{py}\r": "bundle.bad_shebang", f"#!{py}\x0cb": "bundle.bad_shebang", "#!python3": "bundle.relative_path"}
        for i, (line, code) in enumerate(bad.items()):
            exe.write_text(f"{line}\n{WORKER}")
            os.chmod(exe, 0o755)
            with self.subTest(line=line):
                with self.assertRaises(bd.BundleError) as err:
                    bd.build(cp.init(root / f"s{i}", self.manifest, shlex.quote(str(exe)) + tail), self.worker)
                self.assertEqual(err.exception.code, code)
        exe.write_text(f"#!{py}\n{WORKER}")
        doc = bd.build(cp.init(root / "abs", self.manifest, shlex.quote(str(exe)) + tail), self.worker)
        self.assertEqual([f["named_as"] for f in doc["files"] if f["role"] == "shebang"], [py])
        # a launcher as the first word is refused, also through a link; the worker's '#!' is read in the interpreter form too
        for first in ("/usr/bin/env", str(bin_dir / "myenv"), "/usr/bin/nice"):
            with self.subTest(first=first):
                with self.assertRaises(bd.BundleError) as err:
                    bd.build(cp.init(root / f"l{first.replace('/', '_')}", self.manifest, f"{first} {shlex.quote(str(exe))}" + tail), self.worker)
                self.assertEqual(err.exception.code, "bundle.launcher")
        exe.write_text(f"#!/bin/sh /tmp/evil.sh\n{WORKER}")
        with self.assertRaises(bd.BundleError):
            bd.build(cp.init(root / "pyform", self.manifest, f"{shlex.quote(sys.executable)} {shlex.quote(str(exe))}" + tail), self.worker)
        wrapper = root / "wrapper.sh"
        wrapper.write_text(f"#!/bin/sh\nexec {sys.executable} \"$@\"\n")
        os.chmod(wrapper, 0o755)
        with self.assertRaises(bd.BundleError) as err:  # an interpreter that is a '#!' script: no chains
            bd.build(cp.init(root / "wrap", self.manifest, f"{shlex.quote(str(wrapper))} {shlex.quote(str(self.worker / 'work.py'))}" + tail),
                     self.worker)
        self.assertEqual(err.exception.code, "bundle.bad_shebang")

    def test_worker_root_may_not_contain_the_campaign(self):
        with self.assertRaises(bd.BundleError) as err:
            bd.build(self.cdir, Path(self.tmp.name))
        self.assertEqual(err.exception.code, "bundle.bad_worker_root")

    def test_sourceless_pyc_is_bundled(self):
        doc = self.freeze()
        (self.worker / "helper.pyc").write_bytes(b"\x00compiled")
        self.assertEqual(bd.verify(doc)["differences"], [{"role": "worker", "path": "helper.pyc", "change": "added"}])

    def test_a_bundle_of_another_campaign_is_refused(self):
        doc = self.freeze()
        other = cp.init(Path(self.tmp.name) / "other", self.manifest, self.cmd.replace("--id {id}", "--id {id} --evil 1"))
        (other / "bundles").mkdir()
        (other / "bundles" / f"{doc['bundle_digest']}.json").write_text(Path(doc["path"]).read_text())
        with self.assertRaises(cp.CampaignError) as err:
            cp.submit(other, ScriptedExecutor({}), {}, bundle_digest=doc["bundle_digest"])
        self.assertEqual(err.exception.code, "bundle.other_campaign")

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
