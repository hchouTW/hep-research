"""Com5: spectrum_plot.py draws spectra only from dataset-records. Oracles: every plotted point traces to its record
(artifact id, file sha256, bin index) and reproduces the record value times x^gamma at the stated bin position
(Lafferty-Wyatt for a declared power law, or the bin centre); synthetic and user-supplied statuses appear in the
legend and the caption, which says the overlay is not a combination; a variable conversion goes through M7's
spectrum_transform.py and keeps its transformation record; a non-dataset-record input is refused. All inputs are
SYNTHETIC."""
import hashlib
import json
import math
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[3]
SCRIPT = PLUGIN / "skills" / "hep-writing" / "scripts" / "spectrum_plot.py"
FIXTURE = PLUGIN / "contracts" / "fixtures" / "artifacts" / "valid" / "dataset_record.json"
EDGES = [1.0, 2.0, 4.0, 8.0, 16.0]
GAMMA = 2.7


def record(path: Path, rid: str, status: list[str], scale: float = 1.0):
    doc = json.loads(FIXTURE.read_text(encoding="utf-8"))
    doc["artifact_id"] = rid
    doc["status"] = status
    ext = doc["extension"]
    ext["dataset_id"] = f"synthetic:{rid}"
    ext["status"] = status[0]
    ext.pop("experiment_profile", None)
    doc["bindings"]["experiments"] = []
    ext["observable"].update({"quantity": "flux", "process": "SYNTHETIC proton flux", "unit": "m^-2 s^-1 sr^-1 GV^-1",
                              "variables": [{"name": "rigidity", "unit": "GV", "edges": EDGES}], "frame": "lab",
                              "level": "top-of-instrument", "conventions": {}, "phase_space": {"definition": "SYNTHETIC",
                                                                                                "fiducial": False}})
    # bin averages of 1e4 R^-GAMMA (exact integrals)
    vals = [scale * 1e4 * (lo ** (1 - GAMMA) - hi ** (1 - GAMMA)) / ((GAMMA - 1) * (hi - lo))
            for lo, hi in zip(EDGES, EDGES[1:])]
    ext["data"] = {"edges": EDGES, "values": vals, "unit": "m^-2 s^-1 sr^-1 GV^-1",
                   "uncertainties": [{"name": "stat", "kind": "statistical", "values": [0.05 * v for v in vals],
                                      "correlation": "uncorrelated"}]}
    path.write_text(json.dumps(doc, indent=1), encoding="utf-8")
    return vals


def run(*args, env=None):
    p = subprocess.run([sys.executable, "-B", str(SCRIPT), *map(str, args)], capture_output=True, text=True,
                       timeout=600, env=env)
    return p.returncode, (json.loads(p.stdout) if p.stdout.strip().startswith("{") else None), p.stderr


class SpectrumPlot(unittest.TestCase):
    def setUp(self):
        try:
            import matplotlib  # noqa: F401
        except ImportError:
            self.skipTest("matplotlib is not installed")
        self.tmp = tempfile.TemporaryDirectory()
        self.d = Path(self.tmp.name)
        self.a = self.d / "a.json"
        self.b = self.d / "b.json"
        self.va = record(self.a, "synthetic-flux-a", ["synthetic"])
        self.vb = record(self.b, "user-flux-b", ["user-supplied"], scale=1.1)

    def tearDown(self):
        self.tmp.cleanup()

    def test_points_trace_to_records_with_lafferty_wyatt_and_e_gamma(self):
        out_png = self.d / "spec.png"
        code, out, err = run("--record", self.a, "--record", self.b, "--weight-power", GAMMA, "--bin-position",
                             "lafferty-wyatt", "--lw-index", GAMMA, "--out", out_png)
        self.assertEqual(code, 0, (out, err))
        self.assertTrue(out_png.is_file())
        side = json.loads(Path(out["sidecar"]).read_text(encoding="utf-8"))
        sha = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in (self.a, self.b)}
        self.assertEqual(len(side["points"]), 8)
        for pt in side["points"]:
            vals = self.va if pt["artifact_id"] == "synthetic-flux-a" else self.vb
            self.assertEqual(pt["record_sha256"], sha["a.json" if pt["artifact_id"] == "synthetic-flux-a" else "b.json"])
            lo, hi = EDGES[pt["bin"]], EDGES[pt["bin"] + 1]
            # Lafferty-Wyatt: the power law equals its bin average at x_lw
            x_lw = ((lo ** (1 - GAMMA) - hi ** (1 - GAMMA)) / ((GAMMA - 1) * (hi - lo))) ** (-1 / GAMMA)
            self.assertAlmostEqual(pt["x"], x_lw, delta=1e-12 * x_lw)
            self.assertAlmostEqual(pt["y"], vals[pt["bin"]] * x_lw ** GAMMA, delta=1e-9 * pt["y"])
        # for the unscaled synthetic power law, x^gamma * flux at the LW point is exactly the normalization
        a_pts = [p for p in side["points"] if p["artifact_id"] == "synthetic-flux-a"]
        for p in a_pts:
            self.assertAlmostEqual(p["y"], 1e4, delta=1e-6)

    def test_statuses_in_legend_and_caption_and_no_combination(self):
        code, out, _ = run("--record", self.a, "--record", self.b, "--bin-position", "center",
                           "--out", self.d / "spec.pdf")
        self.assertEqual(code, 0)
        self.assertIn("synthetic", out["caption"])
        self.assertIn("user-supplied", out["caption"])
        self.assertIn("not combined", out["caption"])
        side = json.loads(Path(out["sidecar"]).read_text(encoding="utf-8"))
        labels = [s["legend"] for s in side["series"]]
        self.assertTrue(any("synthetic" in x for x in labels) and any("user-supplied" in x for x in labels), labels)
        self.assertEqual(side["bin_position"]["rule"], "center")
        for p in side["points"]:
            lo, hi = EDGES[p["bin"]], EDGES[p["bin"] + 1]
            self.assertAlmostEqual(p["x"], 0.5 * (lo + hi), delta=1e-12)

    def test_conversion_goes_through_spectrum_transform(self):
        comp = self.d / "comp.json"
        comp.write_text(json.dumps({"kind": "fixed", "isotopes": [{"A": 1, "fraction": 1.0}]}), encoding="utf-8")
        code, out, err = run("--record", self.a, "--bin-position", "log-center", "--to", "kinetic_energy_per_nucleon",
                             "--Z", "1", "--composition", comp, "--out", self.d / "conv.png")
        self.assertEqual(code, 0, (out, err))
        side = json.loads(Path(out["sidecar"]).read_text(encoding="utf-8"))
        self.assertEqual(side["series"][0]["variable"], "kinetic_energy_per_nucleon")
        self.assertIn("transformation_record", side["series"][0])
        t_edges = side["series"][0]["edges"]
        self.assertLess(t_edges[0], EDGES[0])  # kinetic energy per nucleon of a 1 GV proton < 1 GeV

    def test_bin_position_is_required_and_bad_input_refused(self):
        code, out, _ = run("--record", self.a, "--out", self.d / "x.png")
        self.assertEqual(code, 2)
        bad = self.d / "notrec.json"
        bad.write_text(json.dumps({"artifact_type": "statistical-result"}), encoding="utf-8")
        code, out, _ = run("--record", bad, "--bin-position", "center", "--out", self.d / "y.png")
        self.assertEqual(code, 2)
        self.assertEqual(out["status"], "rejected")
        code, out, _ = run("--record", self.a, "--bin-position", "lafferty-wyatt", "--out", self.d / "z.png")
        self.assertEqual(code, 2)
        self.assertIn("lw-index", out["error"])


class MissingMatplotlib(unittest.TestCase):
    def test_exit_3_without_matplotlib(self):
        with tempfile.TemporaryDirectory() as d:
            Path(d, "matplotlib.py").write_text("raise ImportError('hidden for this test')\n", encoding="utf-8")
            rec = Path(d) / "r.json"
            record(rec, "r", ["synthetic"])
            env = dict(os.environ, PYTHONPATH=d, PYTHONDONTWRITEBYTECODE="1")
            code, out, _ = run("--record", rec, "--bin-position", "center", "--out", Path(d) / "f.png", env=env)
        self.assertEqual(code, 3)
        self.assertEqual(out["status"], "missing-dependency")


if __name__ == "__main__":
    unittest.main()
