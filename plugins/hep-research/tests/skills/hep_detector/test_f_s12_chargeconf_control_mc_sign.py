"""CHK-AT-08-04 (S1): charge_confusion_rate.py control mode must compare the data and MC rates of one species.

The scale factor r_data / r_mc is a ratio of two binomial rates, k wrong-sign of n tracks of one true sign
(pdg_2025_statistics sec. 40.4.2.4, p. 31: n successes out of N trials with one probability). The two rates must
belong to the same species, because c+ and c- differ: an MC sample of the other true sign, or of both pooled, gives a
silently wrong scale factor. The data sample was already required to have one true sign; the MC sample was not.

Oracle (basis exhaustive): every combination of the data's true sign (positive, negative) and the set of true signs
in the MC sample ({positive}, {negative}, {positive, negative}, none) is run; expected: accepted (exit 0) exactly when
the MC set is the data's sign alone, otherwise rejected (exit 2, status rejected). Regression: for the accepted case
the scale factor equals the ratio of the two binomial rates counted here from the rows written. Property: swapping
the sign labels everywhere gives the same counts and scale factors. Negative control: the pre-fix pooled MC rate,
counted here, differs from the same-species MC rate by more than a factor 5 on these inputs, so a pooled scale factor
is wrong. SYNTHETIC samples (seeded). Tolerances: counts and accept/refuse are exact; scale factors agree to 1e-12
relative (both are ratios of the same integers in double precision).
"""
import csv
import json
import random
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[3]
SCRIPT = PLUGIN / "skills" / "hep-detector" / "scripts" / "charge_confusion_rate.py"
SIGNS = ("positive", "negative")
EDGES = ["1", "50", "100"]
RATES = {"positive": 0.03, "negative": 0.002}   # SYNTHETIC per-species wrong-sign probabilities (MC)


def other(sign):
    return SIGNS[1 - SIGNS.index(sign)]


def rows_for(rng, sign, n, rate):
    return [(rng.uniform(1, 100), sign, other(sign) if rng.random() < rate else sign) for _ in range(n)]


def write(path, rows):
    with path.open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["rig", "truth", "reco"])
        w.writerows(rows)


def run(data_csv, mc_csv):
    p = subprocess.run([sys.executable, "-B", str(SCRIPT), "control", "--data", str(data_csv), "--mc", str(mc_csv), "--edges",
                        *EDGES, "--bin-column", "rig", "--true-sign-column", "truth", "--reco-sign-column", "reco"],
                       capture_output=True, text=True, timeout=600)
    return p.returncode, (json.loads(p.stdout) if p.stdout.strip().startswith("{") else p.stdout)


def counts(rows, sign=None):
    """(n, k) per bin of EDGES, over the rows of true sign `sign` (all rows when None)."""
    e = [float(v) for v in EDGES]
    n, k = [0] * (len(e) - 1), [0] * (len(e) - 1)
    for x, t, r in rows:
        if sign is not None and t != sign:
            continue
        for b in range(len(e) - 1):
            if e[b] <= x < e[b + 1]:
                n[b] += 1
                k[b] += r != t
    return n, k


class ControlMcSign(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        rng = random.Random(11)
        cls.tmp = tempfile.TemporaryDirectory()
        d = Path(cls.tmp.name)
        cls.data_rows = {s: rows_for(rng, s, 4000, 0.004) for s in SIGNS}
        cls.mc_rows = {s: rows_for(rng, s, 6000, RATES[s]) for s in SIGNS}
        cls.files = {}
        for s in SIGNS:
            write(d / f"data_{s}.csv", cls.data_rows[s])
            write(d / f"mc_{s}.csv", cls.mc_rows[s])
            cls.files[("data", s)] = d / f"data_{s}.csv"
            cls.files[("mc", frozenset([s]))] = d / f"mc_{s}.csv"
        cls.mixed = cls.mc_rows["positive"] + cls.mc_rows["negative"]
        rng.shuffle(cls.mixed)
        write(d / "mc_mixed.csv", cls.mixed)
        write(d / "mc_none.csv", [])
        cls.files[("mc", frozenset(SIGNS))] = d / "mc_mixed.csv"
        cls.files[("mc", frozenset())] = d / "mc_none.csv"

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_exhaustive_sign_combinations(self):
        for data_sign in SIGNS:
            for mc_set in (frozenset(["positive"]), frozenset(["negative"]), frozenset(SIGNS), frozenset()):
                code, out = run(self.files[("data", data_sign)], self.files[("mc", mc_set)])
                accept = mc_set == frozenset([data_sign])
                with self.subTest(data=data_sign, mc=sorted(mc_set)):
                    self.assertEqual(code, 0 if accept else 2, out)
                    self.assertEqual(out["status"], "ok" if accept else "rejected", out)

    def test_same_species_scale_factor_is_the_rate_ratio(self):
        for s in SIGNS:
            code, out = run(self.files[("data", s)], self.files[("mc", frozenset([s]))])
            self.assertEqual(code, 0, out)
            nd, kd = counts(self.data_rows[s])
            nm, km = counts(self.mc_rows[s])
            for b, row in enumerate(out["bins"]):
                with self.subTest(sign=s, bin=b + 1):
                    self.assertEqual((row["n"], row["k"], row["mc"]["n"], row["mc"]["k"]), (nd[b], kd[b], nm[b], km[b]))
                    expected = (kd[b] / nd[b]) / (km[b] / nm[b])
                    self.assertLessEqual(abs(row["scale_factor"]["value"] - expected), 1e-12 * expected)

    def test_property_sign_swap(self):
        with tempfile.TemporaryDirectory() as scratch:
            d = Path(scratch)
            swap = {"positive": "negative", "negative": "positive"}
            write(d / "data.csv", [(x, swap[t], swap[r]) for x, t, r in self.data_rows["negative"]])
            write(d / "mc.csv", [(x, swap[t], swap[r]) for x, t, r in self.mc_rows["negative"]])
            code_s, out_s = run(d / "data.csv", d / "mc.csv")
        code, out = run(self.files[("data", "negative")], self.files[("mc", frozenset(["negative"]))])
        self.assertEqual((code, code_s), (0, 0), (out, out_s))
        self.assertEqual(out_s["sign_rates"]["rates"][0]["true"], "positive")
        for a, b in zip(out["bins"], out_s["bins"]):
            self.assertEqual((a["n"], a["k"], a["mc"], a["scale_factor"]), (b["n"], b["k"], b["mc"], b["scale_factor"]))

    def test_negative_control_pooled_mc_rate_is_wrong(self):
        """The pre-fix behaviour pooled the MC species: its rate is far from the data species' MC rate here."""
        n_pool, k_pool = counts(self.mixed)
        n_neg, k_neg = counts(self.mixed, "negative")
        for b in range(len(n_pool)):
            with self.subTest(bin=b + 1):
                self.assertGreater((k_pool[b] / n_pool[b]) / (k_neg[b] / n_neg[b]), 5.0)


if __name__ == "__main__":
    unittest.main()
