"""theory:cr-secondary-antiprotons predictions: channels, fractions, antineutron/hyperon switches, bin averages,
cross-section sets as alternatives, refusal of bad input. Inputs are ILLUSTRATIVE."""
import copy
import json
import sys
import unittest
from importlib.util import find_spec
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import predict  # noqa: E402

CFG = json.loads((ROOT / "benchmarks" / "source-term-benchmark.json").read_text(encoding="utf-8"))


@unittest.skipUnless(find_spec("scipy") and find_spec("numpy"), "numpy and scipy are required (requirements-core.txt)")
class PredictionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.st = predict.source_term(CFG)

    def test_four_channels_and_fractions_sum_to_one(self):
        self.assertEqual(set(self.st["prompt_by_channel"]), {"pp", "pHe", "Hep", "HeHe"})
        for k in range(len(CFG["energies_gev"])):
            self.assertAlmostEqual(sum(f[k] for f in self.st["channel_fractions"].values()), 1.0, delta=1e-12)

    def test_numerical_and_closed_form_paths_agree(self):
        closed = predict.source_term(CFG, method="closed-form")
        for a, b in zip(self.st["total"], closed["total"]):
            self.assertAlmostEqual(a / b, 1.0, delta=1e-8)

    def test_factor_switches(self):
        xs = predict.load_cross_sections(CFG)
        both = predict.factor_parts(CFG, xs)
        d_is, d_lam = both["Delta_IS"], both["Delta_Lambda"]
        self.assertAlmostEqual(d_lam, 0.81 * 0.3, delta=1e-15)
        self.assertAlmostEqual(both["factor"], 2 + d_is + 2 * d_lam, delta=1e-15)
        no_n = predict.factor_parts(dict(CFG, antineutrons="excluded"), xs)
        self.assertAlmostEqual(no_n["factor"], 1 + d_lam, delta=1e-15)
        prompt_only = predict.factor_parts(dict(CFG, antineutrons="excluded", hyperons="excluded"), xs)
        self.assertEqual(prompt_only["factor"], 1.0)
        no_h = predict.factor_parts(dict(CFG, hyperons="excluded"), xs)
        self.assertAlmostEqual(no_h["factor"], 2 + d_is, delta=1e-15)

    def test_total_scales_with_the_factor(self):
        prompt_only = predict.source_term(dict(CFG, antineutrons="excluded", hyperons="excluded"))
        for a, b in zip(self.st["total"], prompt_only["total"]):
            self.assertAlmostEqual(a / b, self.st["factor"]["factor"], delta=1e-12)

    def test_target_density_and_helium_ratio_enter_linearly(self):
        dense = predict.source_term(dict(CFG, ism={"n_H_cm3": 2.0, "He_to_H": 0.1}))
        for a, b in zip(dense["total"], self.st["total"]):
            self.assertAlmostEqual(a / b, 2.0, delta=1e-12)
        no_he = predict.source_term(dict(CFG, ism={"n_H_cm3": 1.0, "He_to_H": 0.0}))
        self.assertEqual(no_he["prompt_by_channel"]["pHe"][0], 0.0)
        self.assertEqual(no_he["prompt_by_channel"]["HeHe"][0], 0.0)

    def test_alternative_set_differs(self):
        alt = predict.source_term(CFG, xs_set=CFG["alternative_cross_section_sets"][0])
        self.assertTrue(all(abs(a / b - 1) > 1e-3 for a, b in zip(alt["total"], self.st["total"])))

    def test_bin_average_between_edge_values_and_threshold_split(self):
        edges = CFG["energy_bin_edges_gev"]
        avg = predict.bin_averaged(CFG, edges)
        ends = predict.source_term(CFG, edges)["total"]
        for i, v in enumerate(avg):
            lo, hi = sorted((ends[i], ends[i + 1]))
            if edges[i + 1] <= predict.threshold(predict.load_cross_sections(CFG)) or edges[i] >= 6.0:
                self.assertTrue(lo <= v <= hi, (i, lo, v, hi))
        # a bin across the threshold: the split average equals a fine direct average
        import numpy as np
        t = np.linspace(5.0, 10.0, 20001)
        q = predict.source_term(CFG, list(t), method="closed-form")["total"]
        direct = float(np.trapezoid(q, t) / 5.0) if hasattr(np, "trapezoid") else float(np.trapz(q, t) / 5.0)
        self.assertAlmostEqual(predict.bin_averaged(CFG, [5.0, 10.0])[0] / direct, 1.0, delta=1e-6)

    def test_bad_inputs_refused(self):
        bad = copy.deepcopy(CFG)
        bad["antineutrons"] = "maybe"
        with self.assertRaises(predict.InputError):
            predict.source_term(bad, [10.0])
        with self.assertRaises(predict.InputError):
            predict.source_term(CFG, [0.0])
        with self.assertRaises(predict.InputError):
            predict.bin_averaged(CFG, [5.0, 2.0])
        bad = copy.deepcopy(CFG)
        bad["primaries"]["p"] = {"form": "log-parabola", "K": 1.0, "T0_gev": 1.0}
        with self.assertRaises(predict.InputError):
            predict.source_term(bad, [10.0])

    def test_cli_runs_and_reports_illustrative(self):
        import subprocess
        proc = subprocess.run([sys.executable, str(ROOT / "scripts" / "predict.py"), "--method", "closed-form"],
                              capture_output=True, text=True, timeout=120)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        out = json.loads(proc.stdout)
        self.assertTrue(out["illustrative"])
        self.assertEqual(out["unit"], "cm^-3 s^-1 GeV^-1")


if __name__ == "__main__":
    unittest.main()
