"""examples/reconstruction-calorimetry (T08, adapters/calo-cluster): generate a few synthetic t08-grid/1 events, reconstruct them with
reco.calo.cell-cluster/1 and check the product.

The offline replay of the committed recording must reproduce the committed output/ byte for byte and pass every check of run.py. The
checks are also driven on a recording made here from hand-made events (a closed-form stand-in with the generator's interface, not
t08-grid/1), honest and with one defect each: the energy kind relabelled as incident energy, a recipe command that names a truth file,
other cells than the product names, a planted sharing fraction, a product of another configuration, a wrong unclustered count, a
missing recording. With HEP_T08_GENERATOR naming the frozen generator, the live run is repeated into a temporary folder and its
recorded files must equal the recording byte for byte. The T08 job points HEP_T08_EXAMPLE_RECORDED and HEP_T08_EXAMPLE_OUTPUT at its
own first live run, since the committed recording is copied from that job; elsewhere they default to the committed folders. No
calorimetry quality claim: the example's counts are not an efficiency or a resolution (K09 at Freeze B).
"""
import contextlib
import importlib.util
import io
import json
import math
import os
import re
import shutil
import tempfile
import unittest
from pathlib import Path

import numpy

PLUGIN = Path(__file__).resolve().parents[2]
EXAMPLE = PLUGIN / "examples" / "reconstruction-calorimetry"
RECORDED = Path(os.environ.get("HEP_T08_EXAMPLE_RECORDED", EXAMPLE / "recorded"))
EXPECTED_OUTPUT = Path(os.environ.get("HEP_T08_EXAMPLE_OUTPUT", EXAMPLE / "output"))
HOST_PATH = re.compile(r"/ceph|/var/tmp|/tmp/|/dicos|/home/|hpa-wn")
GENERATOR = os.environ.get("HEP_T08_GENERATOR", "")
N = 40


def load():
    spec = importlib.util.spec_from_file_location("reconstruction_calorimetry_run", EXAMPLE / "run.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def quiet(function, *arguments):
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        return function(*arguments)


def g_axis(i, c):
    return 0.5 * (math.erf((i + 1 - c) / math.sqrt(2.0)) - math.erf((i - c) / math.sqrt(2.0)))


class HandMadeGenerator:
    """The frozen generator's interface, written here: two closed-form two-shower images, no random draw. Not t08-grid/1."""
    N_CELLS, GENERATOR, CLIP_MEV = N, "hand-made", 400.0
    SHOWERS = [[(2000.0, 18.4, 20.2), (2000.0, 23.1, 20.6)], [(1500.0, 12.2, 12.7), (1500.0, 12.4, 18.9)]]

    @staticmethod
    def cell_profile(x, y):
        return numpy.array([[g_axis(ix, x) * g_axis(iy, y) for iy in range(N)] for ix in range(N)])

    def event(self, fixture, block, stratum, index):
        showers = self.SHOWERS[index]
        deposit = numpy.stack([e * self.cell_profile(x, y) for e, x, y in showers])
        return {"data": {"raw": deposit.sum(axis=0), "pedestal": 0.0, "gain": 1.0, "live": numpy.ones((N, N), bool),
                         "saturated": numpy.zeros((N, N), bool)},
                "truth": {"energy_mev": showers[0][0], "energy_bin": 2, "separation": "far", "showers": numpy.array([[x, y] for _, x, y in showers]),
                          "d": math.dist(showers[0][1:], showers[1][1:]), "azimuth": 0.0, "t": None, "f_dead": None, "deposit": deposit}}


class OfflineReplay(unittest.TestCase):
    """The committed recording (made by the T08 job with the frozen generator)."""

    @classmethod
    def setUpClass(cls):
        cls.example = load()
        cls.folder = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.folder.cleanup)
        cls.out = Path(cls.folder.name) / "output"
        cls.code = quiet(cls.example.main, ["--out", str(cls.out), "--recorded", str(RECORDED)])

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
        self.assertEqual((summary["generator"], summary["generator_sha256"]), ("t08-grid/1", self.example.FROZEN_GENERATOR_SHA256))
        self.assertEqual((summary["block"], summary["variant"], summary["stratum"]), (1, "main", 7))  # the tuning block only
        self.assertEqual(summary["recorded_sha256"], {name: self.example.sha256_bytes((RECORDED / name).read_bytes()) for name in self.example.RECORDED_FILES})

    def test_the_recording_and_the_output_hold_no_host_path(self):
        leaks = [f"{folder.name}/{path.name}" for folder in (RECORDED, EXPECTED_OUTPUT) for path in sorted(folder.iterdir())
                 if HOST_PATH.search(path.read_bytes().decode("utf-8", errors="replace"))]
        self.assertEqual(leaks, [])
        self.assertTrue(HOST_PATH.search("<work>/x /ceph/work/y"))  # the pattern finds what it is for


class HandMadeRecording(unittest.TestCase):
    """run.py's live path and every check, on hand-made events, honest and with one defect each."""

    @classmethod
    def setUpClass(cls):
        cls.example = load()
        cls.folder = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.folder.cleanup)
        cls.recorded = Path(cls.folder.name) / "recorded"
        cls.live_code = quiet(cls.example.live, HandMadeGenerator(), None, Path(cls.folder.name) / "work", cls.recorded)

    def copy_of_recording(self, name: str) -> Path:
        copy = Path(self.folder.name) / name
        shutil.copytree(self.recorded, copy)
        return copy

    def replay_of(self, recorded: Path) -> int:
        return quiet(self.example.main, ["--out", str(recorded.parent / (recorded.name + "-out")), "--recorded", str(recorded)])

    def edit_product(self, copy: Path, edit) -> None:
        lines = (copy / "events.product").read_text(encoding="utf-8").splitlines()
        docs = [json.loads(line) for line in lines]
        edit(docs)
        (copy / "events.product").write_text("\n".join(json.dumps(d, sort_keys=True, separators=(",", ":")) for d in docs) + "\n", encoding="utf-8")

    def test_the_honest_recording_passes_every_check(self):
        self.assertEqual(self.live_code, 0)
        self.assertEqual(sorted(p.name for p in self.recorded.iterdir()), sorted(self.example.RECORDED_FILES))
        out = Path(self.folder.name) / "honest-out"
        self.assertEqual(quiet(self.example.main, ["--out", str(out), "--recorded", str(self.recorded)]), 0)
        summary = json.loads((out / "summary.json").read_text(encoding="utf-8"))
        self.assertEqual([c["check"] for c in summary["checks"] if not c["passed"]], [])
        self.assertEqual(summary["generator"], "hand-made")
        self.assertEqual([e["objects"] for e in summary["events"]], [2, 2])
        leaks = [p.name for p in list(self.recorded.iterdir()) + list(out.iterdir()) if HOST_PATH.search(p.read_bytes().decode("utf-8", errors="replace"))]
        self.assertEqual(leaks, [])

    def test_incident_energy_fails(self):
        copy = self.copy_of_recording("incident")
        self.edit_product(copy, lambda docs: docs[0].update(energy_kind="incident-energy"))
        self.assertEqual(self.replay_of(copy), 1)

    def test_a_recipe_command_that_named_a_truth_file_fails(self):
        copy = self.copy_of_recording("truth-to-recipe")
        runs = json.loads((copy / "runs.json").read_text(encoding="utf-8"))
        run = next(r for r in runs["runs"] if r["operation"] == "reconstruct")
        run["command"] = run["command"] + ["--truth", "<work>/events.truth.npz"]
        (copy / "runs.json").write_text(json.dumps(runs, indent=1, sort_keys=True) + "\n", encoding="utf-8")
        self.assertEqual(self.replay_of(copy), 1)

    def test_other_cells_than_the_product_names_fail(self):
        copy = self.copy_of_recording("other-cells")
        content = bytearray((copy / "events.cells").read_bytes())
        content[-6408] ^= 0x01                  # the lowest byte of the last raw value (two events: 6,400 flag bytes follow)
        (copy / "events.cells").write_bytes(bytes(content))
        self.assertEqual(self.replay_of(copy), 1)

    def test_a_planted_sharing_fraction_fails(self):
        copy = self.copy_of_recording("fraction")

        def plant(docs):
            two = next(o for d in docs[1:-1] for o in d["objects"] if o["kind"] == "two-peak")
            two["members"][0][1] = min(1.0, two["members"][0][1] + 1e-3)
        self.edit_product(copy, plant)
        self.assertEqual(self.replay_of(copy), 1)

    def test_a_product_of_another_configuration_fails(self):
        copy = self.copy_of_recording("other-configuration")
        self.edit_product(copy, lambda docs: docs[0]["configuration"].update(sha256="0" * 64))
        self.assertEqual(self.replay_of(copy), 1)

    def test_a_wrong_unclustered_count_fails(self):
        copy = self.copy_of_recording("unclustered")
        self.edit_product(copy, lambda docs: docs[1].update(unclustered_cells=docs[1]["unclustered_cells"] - 1))
        self.assertEqual(self.replay_of(copy), 1)

    def test_a_missing_recording_is_refused(self):
        empty = Path(self.folder.name) / "empty"
        empty.mkdir()
        self.assertEqual(self.replay_of(empty), 1)


@unittest.skipUnless(GENERATOR and Path(GENERATOR).is_file(), "HEP_T08_GENERATOR names no frozen t08-grid/1 generator: the live part runs in the T08 job")
class LiveRun(unittest.TestCase):
    def test_the_live_run_writes_the_recording_again(self):
        run = load()
        with tempfile.TemporaryDirectory() as name:
            folder = Path(name)
            code = quiet(run.main, ["--live", "--generator", GENERATOR, "--work", str(folder / "work"), "--recorded", str(folder / "recorded"),
                                    "--out", str(folder / "output")])
            self.assertEqual(code, 0)
            for file_name in run.RECORDED_FILES:
                with self.subTest(file=file_name):
                    self.assertEqual((folder / "recorded" / file_name).read_bytes(), (RECORDED / file_name).read_bytes())
            for path in EXPECTED_OUTPUT.iterdir():
                with self.subTest(file=path.name):
                    self.assertEqual((folder / "output" / path.name).read_bytes(), path.read_bytes())


if __name__ == "__main__":
    unittest.main()
