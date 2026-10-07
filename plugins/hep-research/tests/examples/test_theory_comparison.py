"""Path D (journey J5) regression tests: QED prediction vs SYNTHETIC reconstructed data, normalization fit.

One run with the default seed and toys; it must rerun byte for byte on the same machine, match the committed output
(floats to rel 1e-9 / abs 1e-12, since another platform's floating point differs in the last digits; fit outputs to
the fitter's precision, FIT_TOLERANCE), pass every pre-declared criterion, reject each mismatched variant, and keep the
synthetic status along the contract trace."""
import contextlib
import hashlib
import importlib.util
import io
import json
import math
import re
import sys
import tempfile
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[2]
SCRIPT = PLUGIN / "examples" / "theory-comparison" / "run.py"
COMMITTED = PLUGIN / "examples" / "theory-comparison" / "output" / "results.json"
# Values a minimizer or root finder produces agree across platforms only to the fitter's precision. The q without the
# luminosity constraint is a difference of two minimized NLLs that is 0 in exact arithmetic (5.8e-11 on E1, 0.0 on E2,
# 2.5e-9 on E3, FULLTEST-E3); the interval ends come from brentq on such a q, and the pull divides by them (E3: rel
# 1.0e-9). The tolerances sit well above that noise and well below the pass criterion (q < 1e-6).
FIT_TOLERANCE = [(re.compile(r"\$\.q_without_luminosity_constraint_at_mu_1\.15$"), {"rel_tol": 0.0, "abs_tol": 1e-7}),
                 (re.compile(r"\.interval_68\[\d\]$|\.pull_vs_injected$"), {"rel_tol": 1e-7, "abs_tol": 0.0})]


def differences(a, b, path="$") -> list[str]:
    """Mismatches between two results: floats to rel 1e-9 / abs 1e-12 except FIT_TOLERANCE paths, everything else exact."""
    if isinstance(a, float) or isinstance(b, float):
        tol = next((t for pattern, t in FIT_TOLERANCE if pattern.search(path)), {"rel_tol": 1e-9, "abs_tol": 1e-12})
        return [] if math.isclose(a, b, **tol) else [f"{path}: {a} != {b} ({tol})"]
    if isinstance(a, dict) and isinstance(b, dict):
        if sorted(a) != sorted(b):
            return [f"{path}: keys {sorted(a)} != {sorted(b)}"]
        return [d for k in a for d in differences(a[k], b[k], f"{path}.{k}")]
    if isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            return [f"{path}: length {len(a)} != {len(b)}"]
        return [d for i, (x, y) in enumerate(zip(a, b)) for d in differences(x, y, f"{path}[{i}]")]
    return [] if a == b else [f"{path}: {a!r} != {b!r}"]


def _floats(doc, path="$", steps=()):
    """(path as differences() prints it, key/index steps) for every float in doc."""
    if isinstance(doc, float):
        yield path, steps
    elif isinstance(doc, dict):
        for k, v in doc.items():
            yield from _floats(v, f"{path}.{k}", steps + (k,))
    elif isinstance(doc, list):
        for i, v in enumerate(doc):
            yield from _floats(v, f"{path}[{i}]", steps + (i,))


def _get(doc, steps):
    for s in steps:
        doc = doc[s]
    return doc


def _set(doc, steps, value):
    _get(doc, steps[:-1])[steps[-1]] = value


try:
    import numpy  # noqa: F401
    import scipy  # noqa: F401
    import matplotlib  # noqa: F401
    HAVE_DEPS = True
except ImportError:
    HAVE_DEPS = False


@unittest.skipUnless(HAVE_DEPS, "numpy, scipy and matplotlib are required (D5 environment)")
class PathDTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location("theory_comparison_run", SCRIPT)
        cls.m = importlib.util.module_from_spec(spec)
        sys.modules["theory_comparison_run"] = cls.m
        spec.loader.exec_module(cls.m)
        cls.tmp = tempfile.TemporaryDirectory()
        cls.out = Path(cls.tmp.name) / "d"
        with contextlib.redirect_stdout(io.StringIO()):
            cls.code = cls.m.main(["--out", str(cls.out)])
        cls.r = json.loads((cls.out / "results.json").read_text())

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_passes_predeclared_criteria(self):
        self.assertEqual(self.code, 0, self.r["pass"])

    def test_rerun_is_byte_identical(self):
        other = Path(self.tmp.name) / "d2"
        with contextlib.redirect_stdout(io.StringIO()):
            self.m.main(["--out", str(other)])
        h = [hashlib.sha256(p.read_bytes()).hexdigest() for p in (self.out / "results.json", other / "results.json")]
        self.assertEqual(h[0], h[1])

    def test_reproduces_committed_output(self):
        diffs = differences(self.r, json.loads(COMMITTED.read_text()))
        self.assertEqual(diffs, [], "\n".join(diffs[:20]))

    def test_comparison_still_fails_for_a_real_change(self):
        """The fit-precision tolerances absorb platform noise only: q moved by 1e-3, an interval
        end moved by rel 1e-5, or any other float moved by rel 1e-6 is reported; q moved by 1e-9 is not."""
        committed = json.loads(COMMITTED.read_text())
        key = "q_without_luminosity_constraint_at_mu_1.15"
        for delta, expect_fail in ((1e-3, True), (1e-9, False)):
            changed = json.loads(json.dumps(committed))
            changed[key] = committed[key] + delta
            with self.subTest(delta=delta):
                self.assertEqual(bool(differences(changed, committed)), expect_fail)
        floats = list(_floats(committed))
        interval = next(f for f in floats if re.search(r"\.interval_68\[0\]$", f[0]))
        plain = next(f for f in floats if not any(pattern.search(f[0]) for pattern, _ in FIT_TOLERANCE) and abs(_get(committed, f[1])) > 1e-3)
        for (path, steps), rel in ((interval, 1e-5), (plain, 1e-6)):
            changed = json.loads(json.dumps(committed))
            _set(changed, steps, _get(committed, steps) * (1 + rel))
            with self.subTest(path=path):
                self.assertTrue(any(d.startswith(path + ":") for d in differences(changed, committed)))

    def test_both_profiles_and_nothing_else(self):
        self.assertEqual(sorted(self.r["profiles_loaded"]), ["experiment:synthetic-collider", "theory:qed-benchmark"])

    def test_injection_closure(self):
        for k, a in self.r["asimov"].items():
            self.assertAlmostEqual(a["mu_hat"], float(k), places=8)
        self.assertIn("0.8", self.r["toy_results"])

    def test_every_variant_rejected_with_its_field(self):
        self.assertGreaterEqual(len(self.r["negative_variants"]), 9)
        for n in self.r["negative_variants"]:
            with self.subTest(n["name"]):
                self.assertTrue(n["rejected"])
                self.assertTrue(n["expected_field_reported"], n["mismatches"])
                self.assertTrue(all(x["resolve"] for x in n["mismatches"]))

    def test_contract_trace_keeps_synthetic_status(self):
        trace = {t["artifact"]: t for t in self.r["contract_trace"]}
        self.assertTrue(all("synthetic" in t["status"] for t in trace.values()))
        fit = trace["synthetic-path-d-mu-fit"]
        self.assertIn("artifacts/comparison_spec.json", fit["inputs"])
        self.assertIn("artifacts/folded_expectation.json", fit["inputs"])
        self.assertIn("../qed-prediction/output/artifacts/prediction.json", trace["synthetic-path-d-folded-expectation"]["inputs"])

    def test_no_new_physics_claim(self):
        text = (self.out / "report.md").read_text().lower()
        self.assertIn("no statement about new physics", text)
        self.assertNotIn("evidence for new physics", text)

    def test_gate_failure_stops_the_fit(self):
        bad = dict(self.m.plan(["migration", "efficiency"]))
        bad["mappings"] = []
        orig = self.m.plan
        try:
            self.m.plan = lambda inc: bad
            with tempfile.TemporaryDirectory() as tmp, contextlib.redirect_stdout(io.StringIO()):
                code = self.m.main(["--out", tmp, "--toys", "2"])
                self.assertEqual(code, 1)
                self.assertTrue((Path(tmp) / "gate_failure.json").exists())
                self.assertFalse((Path(tmp) / "results.json").exists())
        finally:
            self.m.plan = orig


@unittest.skipUnless(HAVE_DEPS, "numpy, scipy and matplotlib are required (D5 environment)")
class LowCountTests(unittest.TestCase):
    """AC17: low and zero counts in the Path D likelihood (no Gaussian approximation, empty bins allowed)."""

    def test_zero_and_low_count_bins(self):
        spec = importlib.util.spec_from_file_location("theory_comparison_run_low", SCRIPT)
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        a = [0.4, 0.3, 0.2, 0.1, 0.5, 0.5]
        fit = m.Model([0, 1, 0, 0, 2, 0], a, 0.02, 5.8e-4).fit()
        self.assertAlmostEqual(fit["mu_hat"], 3 / 2.0, places=12)
        lo, hi = fit["interval_68"]
        self.assertGreater(lo, 0.0)
        self.assertGreater(hi - fit["mu_hat"], fit["mu_hat"] - lo)  # Poisson asymmetry is kept


if __name__ == "__main__":
    unittest.main()
