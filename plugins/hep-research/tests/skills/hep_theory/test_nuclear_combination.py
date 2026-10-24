"""nuclear_combination.py (Th16): isospin combination, conversions and member-by-member nuclear ratios.

Tolerances fixed before comparing: relative 1e-12 for identities; the member-by-member and divided-band uncertainties
must differ by more than 20% on the correlated toy below (they differ by a factor of about 5 by construction).
"""
import json
import math
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "skills/hep-theory/scripts/nuclear_combination.py"
TOY = {"d": 0.31, "u": 0.62, "s": 0.07, "c": 0.03, "b": 0.01, "dbar": 0.11, "ubar": 0.09, "sbar": 0.06,
       "cbar": 0.025, "bbar": 0.008, "g": 1.4}


def run(*args, files=None):
    with tempfile.TemporaryDirectory() as tmp:
        extra = []
        for flag, doc in (files or {}).items():
            p = Path(tmp) / f"{flag.strip('-')}.json"
            p.write_text(json.dumps(doc))
            extra += [flag, str(p)]
        r = subprocess.run([sys.executable, str(SCRIPT), *args, *extra], capture_output=True, text=True, timeout=60)
    return r.returncode, json.loads(r.stdout)


def close(a, b, tol=1e-12):
    return abs(a - b) <= tol * max(1.0, abs(a), abs(b))


PARTONS = {"representation": "xf", "grid_kind": "bound-proton", "values": TOY}


class Combine(unittest.TestCase):
    def test_free_proton_limit(self):
        _, out = run("combine", "--Z", "1", "--A", "1", "--normalization", "per-nucleon", files={"--partons": PARTONS})
        for f, v in TOY.items():
            self.assertTrue(close(out["outputs"]["values"][f], v), f)

    def test_isoscalar_invariant_under_isospin_swap(self):
        swapped = dict(TOY, u=TOY["d"], d=TOY["u"], ubar=TOY["dbar"], dbar=TOY["ubar"])
        _, a = run("combine", "--Z", "20", "--A", "40", "--normalization", "per-nucleon", files={"--partons": PARTONS})
        _, b = run("combine", "--Z", "20", "--A", "40", "--normalization", "per-nucleon",
                   files={"--partons": {"representation": "xf", "grid_kind": "bound-proton", "values": swapped}})
        for f in TOY:
            self.assertTrue(close(a["outputs"]["values"][f], b["outputs"]["values"][f]), f)
        self.assertTrue(close(a["outputs"]["values"]["u"], a["outputs"]["values"]["d"]))

    def test_per_nucleus_is_A_times_per_nucleon_and_lead_value(self):
        _, n = run("combine", "--Z", "82", "--A", "208", "--normalization", "per-nucleon", files={"--partons": PARTONS})
        _, a = run("combine", "--Z", "82", "--A", "208", "--normalization", "per-nucleus", files={"--partons": PARTONS})
        for f in TOY:
            self.assertTrue(close(a["outputs"]["values"][f], 208 * n["outputs"]["values"][f]), f)
        self.assertTrue(close(n["outputs"]["values"]["u"], (82 * TOY["u"] + 126 * TOY["d"]) / 208))

    def test_convert(self):
        _, o = run("convert", "--quantity", "cross-section", "--value", "2.5", "--A", "12", "--from", "per-nucleon")
        self.assertTrue(close(o["outputs"]["per_nucleus"], 30.0))
        _, o = run("convert", "--quantity", "x", "--value", "1.5", "--M-nucleon", "0.9315", "--M-nucleus", "11.178",
                   "--from", "per-nucleon")
        self.assertTrue(close(o["outputs"]["x_per_nucleus"], 1.5 * 0.9315 / 11.178))

    def test_rejections(self):
        for z, a in (("7", "6"), ("0", "0.5"), ("2.5", "6")):
            code, out = run("combine", "--Z", z, "--A", a, "--normalization", "per-nucleon", files={"--partons": PARTONS})
            self.assertEqual((code, out["status"]), (2, "rejected"))
        code, _ = run("combine", "--Z", "1", "--A", "2", "--normalization", "per-nucleon",
                      files={"--partons": {"representation": "xf", "grid_kind": "bound-proton", "values": {"u": 1}}})
        self.assertEqual(code, 2)
        # review I1: an average-nucleon grid is already combined; combining again is refused; no grid_kind is rejected
        code, out = run("combine", "--Z", "82", "--A", "208", "--normalization", "per-nucleon",
                        files={"--partons": dict(PARTONS, grid_kind="average-nucleon")})
        self.assertEqual((code, out["status"]), (1, "refused"))
        code, _ = run("combine", "--Z", "82", "--A", "208", "--normalization", "per-nucleon",
                      files={"--partons": {"representation": "xf", "values": TOY}})
        self.assertEqual(code, 2)
        # review minors: convert guards
        for args in (["--quantity", "x", "--value", "5", "--M-nucleon", "0.93", "--M-nucleus", "11.2", "--from", "per-nucleus"],
                     ["--quantity", "x", "--value", "0.5", "--M-nucleon", "0.93", "--M-nucleus", "0.5", "--from", "per-nucleon"],
                     ["--quantity", "cross-section", "--value", "-1", "--A", "12", "--from", "per-nucleon"]):
            code, _ = run("convert", *args)
            self.assertEqual(code, 2, args)


def members(central, shifts):
    return [central] + [central + s for s in shifts]


class Ratio(unittest.TestCase):
    def doc(self, **over):
        # symmhessian toy: numerator and denominator move together along eigenvector 1 (strong correlation)
        num = {"set": "toyA", "baseline": "toyP", "error_type": "symmhessian", "conf_level_percent": 68,
               "members": members(2.0, [0.20, 0.02])}
        den = {"set": "toyA", "kind": "nuclear", "error_type": "symmhessian", "conf_level_percent": 68,
               "members": members(1.0, [0.10, 0.00])}
        d = {"numerator": num, "denominator": den}
        for k, v in over.items():
            side, key = k.split("__")
            d[side][key] = v
        return d

    def test_member_by_member_and_not_divided_bands(self):
        code, out = run("ratio", files={"--input": self.doc()})
        self.assertEqual(code, 0, out)
        r = out["outputs"]["ratio_members"]
        self.assertTrue(close(r[0], 2.0))
        self.assertTrue(close(r[1], 2.2 / 1.1))
        self.assertTrue(close(r[2], 2.02 / 1.0))
        delta = out["outputs"]["combination"]["delta_up"]
        self.assertTrue(close(delta, math.sqrt((2.2 / 1.1 - 2) ** 2 + 0.02 ** 2), 1e-10))
        divided = 2.0 * math.sqrt((math.hypot(0.2, 0.02) / 2.0) ** 2 + (0.1 / 1.0) ** 2)  # correlation lost
        self.assertGreater(abs(divided - delta) / delta, 0.2)

    def test_refusals(self):
        cases = [self.doc(denominator__set="toyB"),                                     # different nuclear sets
                 self.doc(denominator__error_type="replicas"),                          # mixed error types
                 self.doc(denominator__conf_level_percent=90),                          # different CL
                 self.doc(denominator__kind="proton", denominator__set="otherP"),       # baseline mismatch
                 self.doc(denominator__kind="proton", denominator__set="toyP")]         # unpaired members
        for d in cases:
            code, out = run("ratio", files={"--input": d})
            self.assertEqual((code, out["status"]), (1, "refused"), d)
        d = self.doc(denominator__kind="proton", denominator__set="toyP")
        d["paired_members"] = True
        code, _ = run("ratio", files={"--input": d})
        self.assertEqual(code, 0)

    def test_replica_sets(self):
        reps = [1.0 + 0.05 * math.sinh(0.3 * k - 3) for k in range(21)]  # skewed toy, central member first
        num = {"set": "toyR", "baseline": "toyRp", "error_type": "replicas", "conf_level_percent": 68,
               "prescription": "median-68", "members": [2 * v for v in reps]}
        den = {"set": "toyR", "kind": "nuclear", "error_type": "replicas", "conf_level_percent": 68,
               "prescription": "median-68", "members": reps}
        code, out = run("ratio", files={"--input": {"numerator": num, "denominator": den}})
        self.assertEqual(code, 0, out)
        h = out["outputs"]["headline"]
        self.assertEqual(h["rule"], "median-68")
        self.assertTrue(close(h["central"], 2.0))
        # review I2: a replica set over an external proton set cannot be paired member by member
        bad = {"numerator": num, "denominator": dict(den, kind="proton", set="toyRp"), "paired_members": True}
        code, out = run("ratio", files={"--input": bad})
        self.assertEqual((code, out["status"]), (1, "refused"))
        # review I3: a replica set must name its prescription
        code, _ = run("ratio", files={"--input": {"numerator": {k: v for k, v in num.items() if k != "prescription"},
                                                  "denominator": den}})
        self.assertEqual(code, 2)

    def test_rejections(self):
        code, _ = run("ratio", files={"--input": self.doc(denominator__members=[1.0, -1.1, 0.9])})
        self.assertEqual(code, 2)  # non-positive denominator member
        d = self.doc(denominator__members=[1.0, 1.1])
        code, out = run("ratio", files={"--input": d})
        self.assertEqual((code, out["status"]), (2, "rejected"))


if __name__ == "__main__":
    unittest.main()
