"""adapters/calo-cluster, D2 stage 3 of T08: the ROOT side of the zdcsim converter, on tiny files written here with uproot.

The files are hand-made: the tree "events" with the three columns zdcsim writes (cell, zbin, edep, one entry per crystal and
1 mm bin) and a truth column the converter must not read. No Geant4 program runs and zdcsim.cc is never read. Needs uproot and
awkward (the plugin's root-uproot extra), not SciPy: the job runs it in the environment that reads the zdcsim file.

Run from the plugin root: python -m unittest tests.adapters.test_calo_zdcsim_root -v
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import numpy

ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / "adapters" / "calo-cluster" / "assets"
sys.path.insert(0, str(ASSETS / "fixture_tools"))
sys.path.insert(0, str(ASSETS))

try:
    import awkward
    import uproot
    HAVE = True
except ImportError:  # pragma: no cover - the job's environment has both
    HAVE = False

import t08_zdcsim_cells as zc  # noqa: E402
from calo_recipe import cell_input  # noqa: E402

N, Z_BINS = 6, 53
EVENTS = [[(13, 0, 1.5), (13, 1, 2.25), (8, 3, 0.125)], [], [(35, 52, 0.75)]]


def write_tree(path, events=EVENTS, columns=("cell", "zbin", "edep"), tree="events", truth=True):
    columns_written = {}
    kinds = {"cell": numpy.int32, "zbin": numpy.int32, "edep": numpy.float32}
    for k, name in enumerate(("cell", "zbin", "edep")):
        if name in columns:
            columns_written[name] = awkward.values_astype(awkward.Array([[e[k] for e in event] for event in events]), kinds[name])
    if truth:
        columns_written["E0"] = numpy.full(len(events), 500.0)
    with uproot.recreate(path) as f:
        f[tree] = columns_written


@unittest.skipUnless(HAVE, "uproot or awkward not installed")
class RootReader(unittest.TestCase):
    def setUp(self):
        self.work = tempfile.TemporaryDirectory()
        self.d = Path(self.work.name)

    def tearDown(self):
        self.work.cleanup()

    def test_reads_the_three_columns_only(self):
        write_tree(self.d / "e.root")
        events, read = zc.read_root_deposits(self.d / "e.root")
        self.assertEqual(read, ["cell", "zbin", "edep"])
        self.assertEqual(len(events), 3)
        cell, zbin, edep = events[0]
        self.assertEqual(cell.tolist(), [13, 13, 8])
        self.assertEqual(zbin.tolist(), [0, 1, 3])
        self.assertEqual(edep.tolist(), [1.5, 2.25, 0.125])
        self.assertEqual(len(events[1][0]), 0)

    def test_sums_through_the_file(self):
        write_tree(self.d / "e.root")
        events, _ = zc.read_root_deposits(self.d / "e.root")
        raw, record = zc.deposits_to_cells(events, N, Z_BINS)
        self.assertEqual(raw[0, 1, 2], 3.75)       # zdcsim 13 = iy 2, ix 1
        self.assertEqual(raw[0, 2, 1], 0.125)      # zdcsim 8 = iy 1, ix 2
        self.assertEqual(raw[2, 5, 5], 0.75)
        self.assertEqual(float(raw.sum()), 4.625)
        self.assertEqual([r["deposit_sum_mev"] for r in record], [3.875, 0.0, 0.75])

    def test_missing_column_or_tree(self):
        write_tree(self.d / "a.root", columns=("cell", "zbin"))
        with self.assertRaises(zc.ConversionError) as cm:
            zc.read_root_deposits(self.d / "a.root")
        self.assertIn("edep", str(cm.exception))
        write_tree(self.d / "b.root", tree="other")
        with self.assertRaises(zc.ConversionError) as cm:
            zc.read_root_deposits(self.d / "b.root")
        self.assertIn("events", str(cm.exception))

    def test_not_a_root_file(self):
        (self.d / "c.root").write_bytes(b"not root")
        with self.assertRaises(zc.ConversionError):
            zc.read_root_deposits(self.d / "c.root")

    def test_convert_end_to_end_with_a_stand_in_source(self):
        write_tree(self.d / "e.root")
        src = self.d / "zdcsim.cc"
        src.write_text("// stand-in\n")
        geo = self.d / "g.yaml"
        geo.write_text("type: prototype\nn_crystals: 6\ncrystal_z_mm: 53\n")
        sample = self.d / "s.yaml"
        sample.write_text("particle: e+\nenergy_mev: 500\n")
        files = zc.convert(root=self.d / "e.root", source=src, geometry=geo, sample=sample, seed=7, events=3, physics="FTFP_BERT_EMZ",
                           threads=1, executable=None, out_dir=self.d / "out", stem="z",
                           expected_source=hashlib.sha256(src.read_bytes()).hexdigest())
        read = cell_input.read_file(files["cells"]["path"], cell_input.read_cells, "cells")
        prov = read.header["provenance"]
        self.assertEqual(read.header["label"], "simulated-unvalidated")
        self.assertEqual(prov["input"]["sha256"], hashlib.sha256((self.d / "e.root").read_bytes()).hexdigest())
        self.assertEqual(prov["producer"]["source_sha256"], hashlib.sha256(src.read_bytes()).hexdigest())
        self.assertEqual([c["sha256"] for c in prov["configuration"]],
                         [hashlib.sha256(geo.read_bytes()).hexdigest(), hashlib.sha256(sample.read_bytes()).hexdigest()])
        self.assertEqual((prov["run"]["seed"], prov["run"]["events"], prov["input"]["entries"]), (7, 3, 3))
        self.assertEqual(read.raw[0, 1, 2], 3.75)
        with self.assertRaises(zc.ConversionError) as cm:     # the run asked for another number of events
            zc.convert(root=self.d / "e.root", source=src, geometry=geo, sample=sample, seed=7, events=4, physics="FTFP_BERT_EMZ",
                       threads=1, executable=None, out_dir=self.d / "out2", stem="z", expected_source=hashlib.sha256(src.read_bytes()).hexdigest())
        self.assertIn("entries", str(cm.exception))

    def test_cli_refuses_another_source(self):
        write_tree(self.d / "e.root")
        src = self.d / "zdcsim.cc"
        src.write_text("// stand-in\n")
        (self.d / "g.yaml").write_text("n_crystals: 6\n")
        (self.d / "s.yaml").write_text("particle: e+\n")
        p = subprocess.run([sys.executable, "-I", "-B", str(ASSETS / "fixture_tools" / "t08_zdcsim_cells.py"), "convert",
                            "--root", str(self.d / "e.root"), "--zdcsim-source", str(src), "--geometry", str(self.d / "g.yaml"),
                            "--sample", str(self.d / "s.yaml"), "--seed", "1", "--events", "3", "--physics", "FTFP_BERT_EMZ",
                            "--threads", "1", "--out-dir", str(self.d / "out"), "--stem", "z"], capture_output=True, text=True, timeout=120)
        self.assertEqual(p.returncode, 2, p.stdout + p.stderr)
        self.assertIn("not the supplied", json.loads(p.stdout)["reason"])
        self.assertFalse((self.d / "out" / "z.cells").exists())


@unittest.skipUnless(HAVE, "uproot or awkward not installed")
class FixRound1Root(unittest.TestCase):
    def setUp(self):
        self.work = tempfile.TemporaryDirectory()
        self.d = Path(self.work.name)
        write_tree(self.d / "e.root")

    def tearDown(self):
        self.work.cleanup()

    def test_a_missing_codec_is_a_missing_dependency_not_a_refusal(self):          # F8
        from unittest import mock
        with mock.patch.object(uproot, "open", side_effect=ModuleNotFoundError("No module named 'cramjam'", name="cramjam")):
            with self.assertRaises(ImportError):
                zc.read_root_deposits(self.d / "e.root")

    def test_a_decoding_failure_is_a_named_refusal(self):                            # F8
        from unittest import mock

        class Tree:
            def keys(self):
                return list(zc.COLUMNS)

            def arrays(self, *args, **kwargs):
                raise ValueError("bad basket")

        class File:
            def __enter__(self):
                return self

            def __exit__(self, *exc):
                return False

            def __getitem__(self, name):
                return Tree()

        with mock.patch.object(uproot, "open", return_value=File()):
            with self.assertRaises(zc.ConversionError) as cm:
                zc.read_root_deposits(self.d / "e.root")
        self.assertIn("cannot be decoded", str(cm.exception))

    def test_check_layout_writes_nothing(self):                                     # F9
        geo = self.d / "g.yaml"
        geo.write_text("n_crystals: 6\n")
        sample = self.d / "s.yaml"
        sample.write_text("particle: e+\n")
        before = sorted(self.d.iterdir())
        result = zc.check_layout(root=self.d / "e.root", geometry=geo, sample=sample, events=3)
        self.assertEqual(sorted(self.d.iterdir()), before)
        self.assertEqual((result["entries"], result["deposit_entries"]), (3, 4))
        self.assertEqual(set(result["dtypes"]), {"cell", "zbin", "edep"})
        with self.assertRaises(zc.ConversionError):
            zc.check_layout(root=self.d / "e.root", geometry=geo, sample=sample, events=2)

    def test_build_record_enters_the_provenance(self):                             # F7
        src = self.d / "zdcsim.cc"
        src.write_text("// stand-in\n")
        geo = self.d / "g.yaml"
        geo.write_text("n_crystals: 6\n")
        sample = self.d / "s.yaml"
        sample.write_text("particle: e+\n")
        rec = self.d / "build.json"
        rec.write_text(json.dumps({"format": zc.BUILD_RECORD_FORMAT, "compiler": "g++ 11.5.0", "geant4_version": "11.4.3",
                                   "route": "geant4-config", "command": "g++ ..."}))
        files = zc.convert(root=self.d / "e.root", source=src, geometry=geo, sample=sample, seed=7, events=3, physics="FTFP_BERT_EMZ",
                           threads=1, executable=None, out_dir=self.d / "out", stem="z",
                           expected_source=hashlib.sha256(src.read_bytes()).hexdigest(), build_record=rec)
        build = cell_input.read_file(files["cells"]["path"], cell_input.read_cells, "cells").header["provenance"]["producer"]["build"]
        self.assertEqual(build["record_sha256"], hashlib.sha256(rec.read_bytes()).hexdigest())
        self.assertEqual((build["compiler"], build["geant4_version"], build["route"]), ("g++ 11.5.0", "11.4.3", "geant4-config"))


if __name__ == "__main__":
    unittest.main()
