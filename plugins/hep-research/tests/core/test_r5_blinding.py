"""R5 proposals for core/blinding on top of the g2 scanner: float32 caches, binary content that decodes as
Latin-1, and histogram step outlines (synthetic values only)."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

try:
    import numpy as np
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    HAVE = True
except ImportError:  # pragma: no cover
    HAVE = False

from core.blinding import blinding as bl

EDGES = [100, 105, 110, 115, 120, 125, 130, 135, 140]
WEIGHTED = [1520.37, 1311.71, 1102.93, 987.41, 905.63, 812.27, 745.89, 690.13]
SR = {"variable": "m", "low": 120, "high": 130}
CENTERS = [(a + b) / 2 for a, b in zip(EDGES[:-1], EDGES[1:])]


@unittest.skipUnless(HAVE, "numpy and matplotlib are needed")
class ScanTests(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp())
        self.sealed = bl.seal(EDGES, WEIGHTED, SR)

    def test_float32_cache_is_found(self):
        np.save(self.d / "c.npy", np.asarray(WEIGHTED, dtype=np.float32))
        self.assertEqual(bl.scan_paths([self.d / "c.npy"], self.sealed)["status"], "fail")

    def test_float32_cache_of_masked_values_still_passes(self):
        m = bl.mask_binned(EDGES, WEIGHTED, SR)["values"]
        np.save(self.d / "m.npy", np.asarray([np.nan if v is None else v for v in m], dtype=np.float32))
        self.assertEqual(bl.scan_paths([self.d / "m.npy"], self.sealed)["status"], "pass")

    def test_raw_binary_without_suffix_is_unscanned_not_pass(self):
        np.asarray(WEIGHTED).tofile(self.d / "rawcache")
        self.assertEqual(bl.scan_paths([self.d / "rawcache"], self.sealed)["status"], "incomplete")
        self.assertEqual(bl.scan_paths([self.d / "rawcache"], self.sealed, strict=True)["status"], "fail")

    def test_latin1_text_is_still_read(self):
        (self.d / "log.txt").write_bytes(f"r\xe9sultat {WEIGHTED[4]}\n".encode("latin-1"))
        self.assertEqual(bl.scan_paths([self.d / "log.txt"], self.sealed)["status"], "fail")

    def test_numeric_dumps_on_the_utf16_path_are_unscanned_not_pass(self):
        # float64, float32 and int32 dumps with many zero bytes decode as UTF-16; they must not pass (N03 follow-up)
        sealed = [4731.3712, 4731.0]
        for dtype, vals in (("<f8", [1.0, 2.0, 4731.3712, 3.0, 0.0]), ("<f4", [1.0, 2.0, 4731.3712, 3.0, 0.0]),
                            ("<i4", [1, 2, 4731, 3, 0])):
            p = self.d / f"dump_{dtype[1:]}"
            np.asarray(vals * 20, dtype=dtype).tofile(p)
            with self.subTest(dtype=dtype):
                self.assertEqual(bl.scan_paths([p], sealed)["status"], "incomplete")

    def test_utf16_text_is_still_read(self):
        (self.d / "log16.txt").write_bytes(f"yield {WEIGHTED[4]}\n".encode("utf-16-le"))
        self.assertEqual(bl.scan_paths([self.d / "log16.txt"], self.sealed)["status"], "fail")

    def test_float16_copy_is_found_but_neighbours_are_not(self):
        # the float16 copy of 4731.3712 is 4732; 4745 and 4728 are unrelated values (N17)
        np.save(self.d / "h.npy", np.asarray([4731.3712], dtype=np.float16))
        self.assertEqual(bl.scan_paths([self.d / "h.npy"], [4731.3712])["status"], "fail")
        np.save(self.d / "n.npy", np.asarray([4745.0, 4728.0], dtype=np.float16))
        self.assertEqual(bl.scan_paths([self.d / "n.npy"], [4731.3712])["status"], "pass")


@unittest.skipUnless(HAVE, "numpy and matplotlib are needed")
class StepOutlineTests(unittest.TestCase):
    def found(self, region, weights):
        fig, ax = plt.subplots()
        ax.hist(CENTERS, bins=EDGES, weights=weights, histtype="step")
        out = bl.check_figure(fig, region)
        plt.close(fig)
        return out

    def test_step_outline_is_caught(self):
        self.assertTrue(self.found(SR, WEIGHTED))

    def test_one_bin_window_is_caught(self):
        self.assertTrue(self.found({"variable": "m", "low": 120, "high": 125}, WEIGHTED))

    def test_zeroed_blinded_bins_pass(self):
        w = [0 if 120 <= c < 130 else v for c, v in zip(CENTERS, WEIGHTED)]
        self.assertEqual(self.found(SR, w), [])

    def test_window_outside_the_histogram_passes(self):
        self.assertEqual(self.found({"variable": "m", "low": 200, "high": 210}, WEIGHTED), [])


if __name__ == "__main__":
    unittest.main()
