"""S2: project_uncertainty.py projects an uncertainty budget to k times the exposure. Oracles: the statistical part
falls as 1/sqrt(k); each systematic follows its M5 scaling class (statistical-like, floor, mixed; the worked example
of systematics.md: 1.41% -> 1.12% at four times the control sample); the Asimov significance equals the closed form
and grows with k; the reach is monotonic in k; a projection from D7 toys agrees within 10% with toys regenerated at
k times the exposure. Every output is labeled `projection`, which cannot pass the publication gate. Inputs are
SYNTHETIC."""
import csv
import json
import math
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[3]
SCRIPT = PLUGIN / "skills" / "hep-statistics" / "scripts" / "project_uncertainty.py"
TOY = PLUGIN / "skills" / "hep-detector" / "scripts" / "toy_spectrometer.py"
TOY_CONFIG = PLUGIN / "skills" / "hep-detector" / "assets" / "toy-spectrometer.fictional.json"
sys.path.insert(0, str(PLUGIN))

BASE = {"quantity": "SYNTHETIC cross section", "stat": 0.04,
        "systematics": [
            {"name": "efficiency", "scaling": "statistical-like", "sigma": 0.02, "control_grows_with_exposure": True},
            {"name": "theory", "scaling": "floor", "sigma": 0.03, "control_grows_with_exposure": False},
            {"name": "calibration", "scaling": "mixed", "a": 0.01, "b": 0.01, "control_grows_with_exposure": True}]}


def run(doc, *args, env=None):
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "in.json"
        p.write_text(json.dumps(doc), encoding="utf-8")
        cp = subprocess.run([sys.executable, "-B", str(SCRIPT), str(p), *map(str, args)], capture_output=True,
                            text=True, timeout=600, env=env)
    out = json.loads(cp.stdout) if cp.stdout.strip().startswith("{") else None
    return cp.returncode, out, cp.stderr


def row(out, k):
    return next(r for r in out["projections"] if abs(r["k"] - k) < 1e-12)


class ScalingClasses(unittest.TestCase):
    def test_stat_and_classes(self):
        code, out, err = run(BASE, "--k", "1,4,9")
        self.assertEqual(code, 0, err)
        r1, r4 = row(out, 1), row(out, 4)
        self.assertAlmostEqual(r4["stat"], 0.04 / 2, delta=1e-15)
        s1 = {s["name"]: s["sigma"] for s in r1["systematics"]}
        s4 = {s["name"]: s["sigma"] for s in r4["systematics"]}
        self.assertAlmostEqual(s4["efficiency"], 0.01, delta=1e-15)
        self.assertEqual(s4["theory"], 0.03)
        self.assertAlmostEqual(s1["calibration"], math.sqrt(2) * 0.01, delta=1e-15)  # 1.41% at k = 1
        self.assertAlmostEqual(s4["calibration"], math.sqrt(1.0 + 0.25) * 0.01, delta=1e-15)  # 1.12% at k = 4
        tot4 = math.sqrt(0.02 ** 2 + 0.01 ** 2 + 0.03 ** 2 + 1.25e-4)
        self.assertAlmostEqual(r4["total"], tot4, delta=1e-15)
        self.assertGreater(r1["total"], r4["total"])
        self.assertGreater(row(out, 4)["total"], row(out, 9)["total"])

    def test_a_control_sample_that_does_not_grow_keeps_its_size(self):
        doc = json.loads(json.dumps(BASE))
        doc["systematics"][0]["control_grows_with_exposure"] = False
        code, out, _ = run(doc, "--k", "4")
        self.assertEqual(code, 0)
        s4 = {s["name"]: s["sigma"] for s in row(out, 4)["systematics"]}
        self.assertEqual(s4["efficiency"], 0.02)

    def test_label_and_assumptions(self):
        code, out, _ = run(BASE, "--k", "2")
        self.assertEqual(out["label"], "projection")
        self.assertEqual(out["status"], "ok")
        self.assertEqual(out["status_label"], "unvalidated")
        self.assertIn("status", out["defaults_used"])
        self.assertIn("quadrature", out["assumptions"]["combination"])
        self.assertIn("publication gate", out["note"])


class Significance(unittest.TestCase):
    DOC = dict(BASE, counting={"s": 20.0, "b": 100.0})

    @staticmethod
    def z_a(s, b):
        return math.sqrt(2 * ((s + b) * math.log(1 + s / b) - s))

    def test_asimov_closed_form_and_growth(self):
        code, out, err = run(self.DOC, "--k", "1,2,4")
        self.assertEqual(code, 0, err)
        for k in (1, 2, 4):
            self.assertAlmostEqual(row(out, k)["asimov_z"], self.z_a(20 * k, 100 * k), delta=1e-12)
        zs = [row(out, k)["asimov_z"] for k in (1, 2, 4)]
        self.assertEqual(zs, sorted(zs))

    def test_reference_values_of_inference_recipes(self):
        sys.path.insert(0, str(SCRIPT.parent))
        import project_uncertainty as pu
        self.assertAlmostEqual(pu.asimov_z(5.0, 20.0), 1.0757, delta=5e-5)
        self.assertAlmostEqual(pu.asimov_z(5.0, 20.0, 2.0), 0.9755, delta=5e-5)

    def test_background_uncertainty_lowers_z_and_scales_by_class(self):
        doc = dict(BASE, counting={"s": 20.0, "b": 100.0, "sigma_b_rel": 0.1, "sigma_b_scaling": "floor"})
        code, out, _ = run(doc, "--k", "1")
        self.assertLess(row(out, 1)["asimov_z"], self.z_a(20, 100))


class Reach(unittest.TestCase):
    def test_reach_is_monotonic_and_bracketed(self):
        reaches = []
        for target in (0.045, 0.04, 0.036):
            doc = dict(BASE, reach={"target": "total", "value": target, "k_max": 1e4})
            code, out, err = run(doc, "--k", "1")
            self.assertEqual(code, 0, err)
            k = out["reach"]["k"]
            reaches.append(k)
            self.assertLessEqual(out["reach"]["total_at_k"], target * (1 + 1e-9))
        self.assertEqual(reaches, sorted(reaches))
        doc = dict(BASE, reach={"target": "total", "value": 0.02, "k_max": 1e4})  # below the floor: never reached
        code, out, _ = run(doc, "--k", "1")
        self.assertEqual(code, 0)
        self.assertIsNone(out["reach"]["k"])
        self.assertIn("floor", out["reach"]["note"])

    def test_significance_reach(self):
        doc = dict(BASE, counting={"s": 5.0, "b": 100.0}, reach={"target": "z", "value": 5.0, "k_max": 1e4})
        code, out, _ = run(doc, "--k", "1")
        k = out["reach"]["k"]
        self.assertAlmostEqual(Significance.z_a(5 * k, 100 * k), 5.0, delta=1e-3)


class RejectedInput(unittest.TestCase):
    def test_bad_inputs_exit_2(self):
        bad = [dict(BASE, stat=-1.0),
               dict(BASE, systematics=[{"name": "x", "sigma": 0.01, "control_grows_with_exposure": True}]),
               dict(BASE, systematics=[{"name": "x", "scaling": "mixed", "a": 0.01, "control_grows_with_exposure": True}]),
               dict(BASE, systematics=[{"name": "x", "scaling": "floor", "sigma": 0.01}]),
               dict(BASE, systematics=[{"name": "x", "scaling": "linear", "sigma": 0.01, "control_grows_with_exposure": True}])]
        for doc in bad:
            with self.subTest(doc=doc["systematics"][0] if doc.get("stat", 1) > 0 else "stat"):
                code, out, _ = run(doc, "--k", "2")
                self.assertEqual(code, 2)
                self.assertEqual(out["status"], "rejected")
        for k in ("0", "-1", "nan"):
            with self.subTest(k=k):
                code, out, _ = run(BASE, "--k", k)
                self.assertEqual(code, 2)

    def test_help_without_numpy(self):
        with tempfile.TemporaryDirectory() as d:
            Path(d, "numpy.py").write_text("raise ImportError('hidden')\n", encoding="utf-8")
            env = dict(os.environ, PYTHONPATH=d)
            cp = subprocess.run([sys.executable, "-B", str(SCRIPT), "--help"], capture_output=True, text=True,
                                timeout=600, env=env)
        self.assertEqual(cp.returncode, 0)
        self.assertIn("control_grows_with_exposure", cp.stdout)


class ProjectionLabelAndGate(unittest.TestCase):
    def test_projection_is_a_core_label_and_fails_the_gate(self):
        from contracts.validate import publication_gate
        vocab = json.loads((PLUGIN / "contracts" / "vocab" / "core.json").read_text())["vocabularies"]
        self.assertIn("projection", vocab["artifact_statuses"])
        doc = json.loads((PLUGIN / "contracts" / "fixtures" / "artifacts" / "valid" / "statres_frequentist.json").read_text())
        doc["status"] = ["projection"]
        g = publication_gate(doc)
        self.assertEqual(g["status"], "failed")
        self.assertIn("gate.projection", [r["code"] for r in g["reasons"]])


class AgainstToys(unittest.TestCase):
    """D7 oracle: the relative statistical uncertainty of the event count in a rigidity bin, projected from one
    exposure to k = 4, agrees within 10% with the value measured on toys generated at four times the exposure."""

    def count(self, cfg, seed, d):
        cfgp, ev, per = Path(d) / f"c{seed}.json", Path(d) / f"e{seed}.csv", Path(d) / f"p{seed}.csv"
        cfgp.write_text(json.dumps(cfg), encoding="utf-8")
        cp = subprocess.run([sys.executable, "-B", str(TOY), "generate", str(cfgp), "--seed", str(seed),
                             "--events-out", str(ev), "--periods-out", str(per)], capture_output=True, text=True,
                            timeout=600)
        self.assertEqual(cp.returncode, 0, cp.stdout + cp.stderr)
        with ev.open(encoding="utf-8") as fh:
            rows = csv.DictReader(line for line in fh if not line.startswith("#"))
            return sum(1 for r in rows if 2.0 <= float(r["rigidity_meas_gv"]) < 4.0)

    def test_projection_matches_toys_at_four_times_the_exposure(self):
        try:
            import numpy  # noqa: F401
        except ImportError:
            self.skipTest("numpy is needed by toy_spectrometer.py")
        base = json.loads(TOY_CONFIG.read_text(encoding="utf-8"))
        base.pop("eras", None)
        base["species"] = [dict(base["species"][0], fraction=1.0)]
        with tempfile.TemporaryDirectory() as d:
            n1 = self.count(dict(base, periods=dict(base["periods"], count=4)), 11, d)
            n4 = [self.count(dict(base, periods=dict(base["periods"], count=16)), s, d) for s in (21, 22, 23)]
        doc = {"quantity": "SYNTHETIC count in 2-4 GV", "stat": 1.0 / math.sqrt(n1), "systematics": []}
        code, out, err = run(doc, "--k", "4")
        self.assertEqual(code, 0, err)
        projected = row(out, 4)["stat"]
        measured = 1.0 / math.sqrt(sum(n4) / len(n4))
        self.assertLess(abs(projected / measured - 1.0), 0.10)


if __name__ == "__main__":
    unittest.main()
