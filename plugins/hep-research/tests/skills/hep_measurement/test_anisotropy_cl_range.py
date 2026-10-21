"""anisotropy.py, robust-fix ANISO-CL-RANGE (S4): an upper limit below CL 0.5 is not supported (the expected limit,
the Neyman limit at the median isotropic amplitude, is empty there, so the power constraint is undefined). The CLI
rejects --cl outside [0.5, 1) with that reason (status rejected, exit 2) and amplitude_upper_limit raises ValueError,
where both ended in a TypeError (max(None, ...) or None > float). At CL 0.5 itself the expected limit is 0
analytically (P(r <= median | s = 0) = 1/2); a rounding-level empty result there gave the same TypeError and is now
reported as 0.

Evidence is behavioral (C1): status, exit code, the exception type and the stated reason; the CL 0.5 case checks the
analytic value 0 of the expected limit and that the limit is then the Neyman limit. Results for CL >= 0.5 are
unchanged bit for bit (VALIDATION ANISO-CL-RANGE: full CLI JSON compared before and after). SYNTHETIC inputs only."""
import json
import math
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "skills" / "hep-measurement" / "scripts" / "anisotropy.py"
sys.path.insert(0, str(SCRIPT.parent))
REASON = "[0.5, 1)"


def import_mod():
    import anisotropy
    return anisotropy


def binned_map(nb=24, amp=0.9, axis_deg=30.0):
    """Bin centers of 1 + amp cos(alpha - axis): a non-uniform map, so the null covariance of (a, b) is anisotropic."""
    edges = [360.0 * i / nb for i in range(nb + 1)]
    rel = [1.0 + amp * math.cos(math.radians(360.0 * (i + 0.5) / nb - axis_deg)) for i in range(nb)]
    return edges, rel


def run_harmonic(n, cl, with_map):
    with tempfile.TemporaryDirectory() as d:
        ev = Path(d) / "events.csv"
        ev.write_text("ra_deg\n" + "".join(f"{(360.0 * k / n + 0.1) % 360.0!r}\n" for k in range(n)),
                      encoding="utf-8")
        args = [sys.executable, "-B", str(SCRIPT), "harmonic", "--events", str(ev), "--cl", str(cl)]
        if with_map:
            edges, rel = binned_map()
            emap = Path(d) / "map.json"
            emap.write_text(json.dumps({"ra_edges_deg": edges, "relative_exposure": rel}), encoding="utf-8")
            args += ["--exposure-map", str(emap)]
        p = subprocess.run(args, capture_output=True, text=True, timeout=600)
    return p.returncode, (json.loads(p.stdout) if p.stdout.strip().startswith("{") else None), p.stderr


class CliRange(unittest.TestCase):
    def test_cl_below_one_half_is_rejected_with_the_reason(self):
        """--cl 0.3 and 0.4999, without a map (Rice limit) and with a non-uniform map (anisotropic limit): status
        rejected, exit 2, and the error states the supported range, not a TypeError."""
        for with_map in (False, True):
            for cl in (0.3, 0.4999):
                with self.subTest(with_map=with_map, cl=cl):
                    code, out, err = run_harmonic(500, cl, with_map)
                    self.assertEqual(code, 2, err)
                    self.assertEqual(out["status"], "rejected")
                    self.assertIn(REASON, out["error"])
                    self.assertIn("below CL 0.5", out["error"])
                    self.assertNotIn("NoneType", out["error"])
                    self.assertIn(REASON, err)

    def test_cl_one_half_with_an_anisotropic_map_gives_a_limit(self):
        """--cl 0.5 with the non-uniform map (n = 2000 and 500): the expected limit is 0 (analytic: the median of the
        null amplitude has P = 1/2 at s = 0), so the upper limit is the Neyman limit; the run is ok."""
        for n in (2000, 500):
            with self.subTest(n=n):
                code, out, err = run_harmonic(n, 0.5, True)
                self.assertEqual(code, 0, err)
                self.assertEqual(out["status"], "ok")
                ul = out["upper_limit"]
                self.assertEqual(ul["confidence_level"], 0.5)
                self.assertGreaterEqual(ul["expected_limit"], 0.0)
                self.assertLess(ul["expected_limit"], 1e-6 * ul["median_isotropic_amplitude"])
                self.assertEqual(ul["upper_limit"], max(ul["neyman_limit"], ul["expected_limit"]))


class LibraryRange(unittest.TestCase):
    def test_amplitude_upper_limit_raises_value_error_below_one_half(self):
        """amplitude_upper_limit with cl 0.3 raises ValueError naming the range, for the Rice (n given) and the
        anisotropic (covariance given) construction, with and without an observed amplitude."""
        an = import_mod()
        cov = [[2.0e-3, 3.0e-4], [3.0e-4, 1.0e-3]]
        for label, kwargs in (("rice", {"n": 1000.0}), ("anisotropic", {"n": None, "covariance": cov})):
            for r_obs in (0.05, None):
                with self.subTest(construction=label, r_obs=r_obs):
                    with self.assertRaises(ValueError) as ctx:
                        an.amplitude_upper_limit(r_obs, cl=0.3, **kwargs)
                    self.assertIn(REASON, str(ctx.exception))

    def test_amplitude_upper_limit_rejects_cl_outside_the_range(self):
        """The boundaries: 1.0 and NaN raise ValueError; 0.5 returns a limit."""
        an = import_mod()
        for cl in (1.0, float("nan"), 0.0):
            with self.subTest(cl=cl):
                with self.assertRaises(ValueError):
                    an.amplitude_upper_limit(0.05, 1000.0, cl)
        out = an.amplitude_upper_limit(0.05, 1000.0, 0.5)
        self.assertGreaterEqual(out["upper_limit"], out["expected_limit"])


if __name__ == "__main__":
    unittest.main()
