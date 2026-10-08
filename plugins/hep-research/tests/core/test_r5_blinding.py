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
