"""examples/reconstruction-tracking (T07, adapters/acts-tracking): generate, find and refit a few synthetic telescope events through the wrapper.

The offline replay of the recorded run must reproduce the committed output/ byte for byte and pass every check of run.py. Each check is
driven with one defect on a copy of the recording: a refit product relabelled as finding, a finder command that names a truth file, a hit-set
file not the one the refit names, a missing recording. With HEP_ACTS_TRACKING_BUILD naming the built programs, the live run is repeated into a
temporary folder and its recorded files must equal the recording byte for byte: the programs are deterministic, so a difference is a change of
behaviour. The T07 build job points HEP_ACTS_TRACKING_EXAMPLE_RECORDED and HEP_ACTS_TRACKING_EXAMPLE_OUTPUT at its own first live run, since the
committed recording is copied from that job; elsewhere they default to the committed folders. Standard library only, NumPy for the live part.
No tracking quality claim: the example's counts are not an efficiency (K09 at Freeze B).
"""
import contextlib
import importlib.util
import io
import json
import os
import re
import shutil
import tempfile
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[2]
EXAMPLE = PLUGIN / "examples" / "reconstruction-tracking"
RECORDED = Path(os.environ.get("HEP_ACTS_TRACKING_EXAMPLE_RECORDED", EXAMPLE / "recorded"))
EXPECTED_OUTPUT = Path(os.environ.get("HEP_ACTS_TRACKING_EXAMPLE_OUTPUT", EXAMPLE / "output"))
HOST_PATH = re.compile(r"/ceph|/var/tmp|/tmp/|/dicos|/home/|hpa-wn")
BUILD_DIR = os.environ.get("HEP_ACTS_TRACKING_BUILD", "")
BUILT = bool(BUILD_DIR) and all((Path(BUILD_DIR) / name).is_file() for name in ("acts_tracking_driver", "acts_tracking_finder", "t07_fixture_generator"))


def load():
    spec = importlib.util.spec_from_file_location("reconstruction_tracking_run", EXAMPLE / "run.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def quiet(function, *arguments):
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        return function(*arguments)


class OfflineReplay(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.example = load()
        cls.folder = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.folder.cleanup)
        cls.out = Path(cls.folder.name) / "output"
        cls.code = quiet(cls.example.main, ["--out", str(cls.out), "--recorded", str(RECORDED)])

    def copy_of_recording(self, name: str) -> Path:
        copy = Path(self.folder.name) / name
        shutil.copytree(RECORDED, copy)
        return copy

    def replay_of(self, recorded: Path) -> int:
        return quiet(self.example.main, ["--out", str(recorded.parent / (recorded.name + "-out")), "--recorded", str(recorded)])

    def test_the_replay_reproduces_the_committed_output(self):
        self.assertEqual(self.code, 0)
        self.assertEqual(sorted(path.name for path in self.out.iterdir()), sorted(path.name for path in EXPECTED_OUTPUT.iterdir()))
        for path in EXPECTED_OUTPUT.iterdir():
            with self.subTest(file=path.name):
                self.assertEqual((self.out / path.name).read_bytes(), path.read_bytes())

    def test_every_check_passes_and_nothing_is_claimed(self):
        summary = json.loads((self.out / "summary.json").read_text(encoding="utf-8"))
        self.assertTrue(summary["checks"])
        self.assertEqual([item["check"] for item in summary["checks"] if not item["passed"]], [])
        self.assertEqual(summary["data"], "synthetic")
        self.assertTrue(summary["quality_claim"].startswith("none"))
        self.assertEqual((summary["block"], summary["fixture"]), (1, "t07-telescope-clean/1"))  # the tuning block only
        self.assertTrue(summary["finding"]["product"]["reported_as_finding"])
        self.assertEqual((summary["refit"]["product"]["evidence_class"], summary["refit"]["product"]["reported_as_finding"]), ("truth-assisted", False))
        self.assertEqual(summary["recorded_sha256"], {name: self.example.sha256_bytes((RECORDED / name).read_bytes()) for name in self.example.RECORDED_FILES})

    def test_a_refit_relabelled_as_finding_fails(self):
        copy = self.copy_of_recording("relabelled")
        text = (copy / "refit.product").read_text(encoding="utf-8")
        relabelled = text.replace("\nstage refit-known-hit-set\n", "\nstage find-ckf\n", 1).replace("\nevidence_class truth-assisted\n", "\nevidence_class data-side\n", 1)
        self.assertNotEqual(relabelled, text)
        (copy / "refit.product").write_text(relabelled, encoding="utf-8")
        self.assertEqual(self.replay_of(copy), 1)

    def test_a_finder_that_named_a_truth_file_fails(self):
        copy = self.copy_of_recording("truth-to-finder")
        runs = json.loads((copy / "runs.json").read_text(encoding="utf-8"))
        find = next(run for run in runs["runs"] if run["operation"] == "find")
        find["command"] = find["command"] + ["--seed-file", "<work>/events.t07truth"]
        (copy / "runs.json").write_text(json.dumps(runs, indent=1, sort_keys=True) + "\n", encoding="utf-8")
        self.assertEqual(self.replay_of(copy), 1)

    def test_other_hit_sets_than_the_refit_names_fail(self):
        copy = self.copy_of_recording("other-hit-sets")
        with open(copy / "refit.hitsets", "a", encoding="utf-8") as stream:
            stream.write("hit_set extra 0 0.5 0\n")
        self.assertEqual(self.replay_of(copy), 1)

    def test_the_recording_and_the_output_hold_no_host_path(self):
        """Review minor 11 (D1 stage 11 fix round 1): no folder or host name of the machine that made the recording reaches a committed file. The same
        pattern the coordinator greps before committing a recording: grep -rIlE '/ceph|/var/tmp|/tmp/|/dicos|/home/|hpa-wn' recorded output."""
        leaks = [f"{folder.name}/{path.name}" for folder in (RECORDED, EXPECTED_OUTPUT) for path in sorted(folder.iterdir())
                 if HOST_PATH.search(path.read_text(encoding="utf-8", errors="replace"))]
        self.assertEqual(leaks, [])
        self.assertTrue(HOST_PATH.search("<work>/x /ceph/work/y"))  # the pattern finds what it is for

    def test_a_missing_recording_is_refused(self):
        empty = Path(self.folder.name) / "empty"
        empty.mkdir()
        self.assertEqual(self.replay_of(empty), 1)


@unittest.skipUnless(BUILT, "HEP_ACTS_TRACKING_BUILD names no built driver, finder and generator: the live part needs the T07 build job, which runs it")
class LiveRun(unittest.TestCase):
    def test_the_live_run_writes_the_recording_again(self):
        run = load()
        with tempfile.TemporaryDirectory() as name:
            folder = Path(name)
            code = quiet(run.main, ["--live", "--build-dir", BUILD_DIR, "--work", str(folder / "work"), "--recorded", str(folder / "recorded"), "--out", str(folder / "output")])
            self.assertEqual(code, 0)
            for file_name in run.RECORDED_FILES:
                with self.subTest(file=file_name):
                    self.assertEqual((folder / "recorded" / file_name).read_bytes(), (RECORDED / file_name).read_bytes())
            for path in EXPECTED_OUTPUT.iterdir():
                with self.subTest(file=path.name):
                    self.assertEqual((folder / "output" / path.name).read_bytes(), path.read_bytes())


if __name__ == "__main__":
    unittest.main()
