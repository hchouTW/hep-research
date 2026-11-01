"""Checks that the event-display templates still run (Python parts only).

The web build and the browser test need Node and Chromium; they run only when
HEP_EVENT_DISPLAY_FULL=1 (then run_demo.sh is executed end to end).
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

ASSETS = Path(__file__).resolve().parents[3] / "skills" / "hep-computing" / "assets" / "event-display"

try:  # the templates need these; the plugin itself does not
    import awkward  # noqa: F401
    import uproot  # noqa: F401
    HAVE_DEPS = True
except ImportError:
    HAVE_DEPS = False


def run(args, cwd):
    proc = subprocess.run([sys.executable, *args], cwd=cwd, capture_output=True, text=True, timeout=300)
    return proc.returncode, proc.stdout, proc.stderr


class SelfTest(unittest.TestCase):
    def test_exporter_self_test(self):
        if not HAVE_DEPS:
            self.skipTest("uproot/awkward not installed")
        code, out, err = run([str(ASSETS / "export_histogram.py"), "--self-test"], ASSETS)
        self.assertEqual(code, 0, out + err)


@unittest.skipUnless(HAVE_DEPS, "uproot/awkward not installed")
class PythonPipeline(unittest.TestCase):
    """run_demo.sh steps 1-3 and 5, with a stub page instead of the npm build."""

    def setUp(self):
        import tempfile
        self.w = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.w)
        dist = self.w / "web" / "dist"
        dist.mkdir(parents=True)
        (dist / "index.html").write_text("<!doctype html><title>stub</title>", encoding="utf-8")

    def step(self, *args):
        code, out, err = run(["-I", str(ASSETS / args[0]), *args[1:]], self.w)
        self.assertEqual(code, 0, f"{args}: {out}{err}")
        return out

    def test_export_bundle_check(self):
        self.step("make_demo_data.py", "--out", "demo")
        self.step("export_events.py", "demo/demo.root", "--mapping", str(ASSETS / "mapping.example.json"),
                  "--out", "work/events", "--status", "synthetic")
        record = json.loads((self.w / "work/events/export-record.json").read_text())
        self.assertTrue(record["events"])
        for ev in record["events"]:
            event_scene = json.loads((self.w / "work/events" / ev["file"]).read_text())
            self.assertEqual(set(event_scene) - {"run number", "event number", "subrun"}, {"Hits"})
            for items in event_scene["Hits"].values():
                self.assertTrue(all(i["type"] in ("Point", "Line") for i in items))
        self.step("export_histogram.py", "--root", "demo/demo.root", "--object", "h_pt",
                  "--integration", "jsroot", "--out", "work/results")
        self.step("export_histogram.py", "--json", "demo/results/hits_per_run.json",
                  "--integration", "echarts", "--out", "work/results")
        for f in sorted((self.w / "demo/results/hit_r").glob("*.json")):
            self.step("export_histogram.py", "--json", str(f), "--integration", "plotly",
                      "--out", f"work/results/hit_r/{f.stem}")
        shutil.copy(ASSETS / "bundle-spec.example.json", self.w / "bundle-spec.json")
        self.step("build_bundle.py", "bundle-spec.json")
        self.step("check_bundle.py", "bundle", "--spec", "bundle-spec.json")
        # a source result the project changed after export must be caught against the spec's source
        changed = self.w / "demo/results/hits_per_run.json"
        original = changed.read_text()
        table = json.loads(original)
        table["series"][0]["values"][0] += 1
        changed.write_text(json.dumps(table))
        code, out, err = run(["-I", str(ASSETS / "check_bundle.py"), "bundle", "--spec", "bundle-spec.json"], self.w)
        self.assertNotEqual(code, 0, out + err)
        changed.write_text(original)
        # a changed object must be caught
        bundle = json.loads((self.w / "bundle/bundle.json").read_text())
        scene_path = self.w / "bundle" / bundle["events"][0]["scene"]
        scene_path.write_text(scene_path.read_text().replace('"Point"', '"Point" ', 1))
        code, out, err = run(["-I", str(ASSETS / "check_bundle.py"), "bundle"], self.w)
        self.assertNotEqual(code, 0, out + err)


@unittest.skipUnless(os.environ.get("HEP_EVENT_DISPLAY_FULL") == "1", "set HEP_EVENT_DISPLAY_FULL=1 (needs Node, npm, Chromium)")
class FullDemo(unittest.TestCase):
    def test_run_demo(self):
        import tempfile
        work_root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, work_root)
        d = work_root / "display"
        shutil.copytree(ASSETS, d)
        proc = subprocess.run(["bash", "run_demo.sh", str(work_root / "w"), sys.executable], cwd=d,
                              capture_output=True, text=True, timeout=1200)
        self.assertEqual(proc.returncode, 0, proc.stdout[-4000:] + proc.stderr[-4000:])


if __name__ == "__main__":
    unittest.main()
