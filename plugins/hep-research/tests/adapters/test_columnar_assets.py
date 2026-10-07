"""adapters/root-uproot columnar assets (T24) on the synthetic NanoAOD-like file from make_synthetic_nanoaod.py:
the coffea processor reproduces the generator's independently computed answers, for any chunk size, and the
ROOT-to-Parquet converter writes every entry once, jagged branches included, with a manifest that checks it."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / "adapters" / "root-uproot" / "assets"
MAKER = ROOT / "skills" / "hep-computing" / "scripts" / "make_synthetic_nanoaod.py"
sys.path.insert(0, str(ASSETS))
try:
    import awkward as ak
    import uproot
    HAVE_UPROOT = True
except ImportError:
    HAVE_UPROOT = False
try:
    import pyarrow  # noqa: F401
    HAVE_ARROW = True
except ImportError:
    HAVE_ARROW = False
try:
    import coffea  # noqa: F401
    HAVE_COFFEA = True
except ImportError:
    HAVE_COFFEA = False


def make_sample(directory: Path, events=400, seed=1) -> tuple[Path, dict]:
    path = directory / "synthetic.root"
    res = subprocess.run([sys.executable, str(MAKER), "--out", str(path), "--events", str(events), "--seed", str(seed)],
                         capture_output=True, text=True, timeout=600)
    if res.returncode:
        raise RuntimeError(res.stderr[-800:])
    return path, json.loads(res.stdout)


@unittest.skipUnless(HAVE_UPROOT and HAVE_COFFEA, "coffea, uproot or awkward not installed: the coffea template is unverified")
class CoffeaProcessorTests(unittest.TestCase):
    def test_reproduces_the_generator_answers_for_any_chunking(self):
        import coffea_dijet_processor as cdp
        with tempfile.TemporaryDirectory() as td:
            sample, expected = make_sample(Path(td))
            results = [cdp.run([str(sample)], chunksize=size)["synthetic"] for size in (37, 400)]
        for got in results:
            self.assertEqual(got["n_selected_events"], expected["n_selected_events"])
            self.assertAlmostEqual(got["sumw_selected"], expected["sumw_selected"], places=9)
            self.assertAlmostEqual(got["sumw2_selected"], expected["sumw2_selected"], places=9)
            self.assertAlmostEqual(got["mjj_weighted_mean_GeV"], expected["mjj_weighted_mean_GeV"], delta=1e-9)
            self.assertAlmostEqual(got["mjj_max_GeV"], expected["mjj_max_GeV"], delta=1e-9)
            self.assertAlmostEqual(sum(got["mjj_hist_sumw"]), expected["sumw_selected"], places=9)
        self.assertEqual(results[0]["mjj_hist_sumw"], results[1]["mjj_hist_sumw"])


@unittest.skipUnless(HAVE_UPROOT and HAVE_ARROW, "uproot, awkward or pyarrow not installed: the Parquet converter is unverified")
class RootToParquetTests(unittest.TestCase):
    def test_every_entry_once_with_jagged_branches(self):
        import root_to_parquet as rtp
        with tempfile.TemporaryDirectory() as td:
            sample, _ = make_sample(Path(td))
            out = Path(td) / "parquet"
            manifest = rtp.convert(sample, out, step_size=150)
            self.assertTrue(manifest["complete"])
            self.assertEqual([p["entries"] for p in manifest["parts"]], [150, 150, 100])
            self.assertNotIn("nJet_pt", manifest["branches"])
            back = ak.concatenate([ak.from_parquet(out / p["file"]) for p in manifest["parts"]])
            with uproot.open(sample) as f:
                ref = f["Events"].arrays(manifest["branches"], library="ak")
            for b in manifest["branches"]:
                self.assertTrue(ak.all(back[b] == ref[b]), b)
            self.assertEqual(str(ak.type(back["Jet_pt"])).split(" * ", 1)[1], "var * float32")
            on_disk = json.loads((out / "manifest.json").read_text())
            self.assertEqual(on_disk["input_sha256"], rtp.sha256(sample))
            self.assertEqual(on_disk["entries_written"], 400)

    def test_branch_selection_and_refusal(self):
        import root_to_parquet as rtp
        with tempfile.TemporaryDirectory() as td:
            sample, _ = make_sample(Path(td), events=50)
            m = rtp.convert(sample, Path(td) / "a", branches=["Jet_pt", "genWeight"])
            self.assertEqual(m["branches"], ["Jet_pt", "genWeight"])
            with self.assertRaisesRegex(ValueError, "not in Events"):
                rtp.convert(sample, Path(td) / "b", branches=["Muon_pt"])


if __name__ == "__main__":
    unittest.main()
