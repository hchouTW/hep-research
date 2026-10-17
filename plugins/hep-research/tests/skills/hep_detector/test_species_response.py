"""D2: species_response.py. Oracles: on D7 two-species synthetic events (protons and helium, the reco species from
the measured charge) the sparse fold of the generated truth spectra through the four blocks built by
build_response.py equals direct counting of the reco species; assemble refuses axes that differ and column sums
above 1; check exits 1 on a planted double count (an effect in a block and in the correction chain); from-rates
turns charge_confusion_rate.py sign rates into blocks; above 60 flattened bins the output recommends parametrized
forward folding. Inputs are SYNTHETIC."""
import csv
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[3]
SCRIPTS = PLUGIN / "skills" / "hep-detector" / "scripts"
SCRIPT = SCRIPTS / "species_response.py"
EDGES = ["2", "4", "8", "16", "32"]
try:
    import numpy  # noqa: F401
    HAVE_NUMPY = True
except ImportError:
    HAVE_NUMPY = False


def run(script, *args):
    p = subprocess.run([sys.executable, "-B", str(script), *map(str, args)], capture_output=True, text=True,
                       timeout=600)
    return p.returncode, (json.loads(p.stdout) if p.stdout.strip().startswith("{") else p.stdout + p.stderr)


@unittest.skipUnless(HAVE_NUMPY, "toy_spectrometer.py needs numpy")
class TwoSpeciesFold(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        d = cls.d = Path(cls.tmp.name)
        cfg = json.loads((PLUGIN / "skills" / "hep-detector" / "assets" / "toy-spectrometer.fictional.json").read_text())
        for sp in cfg["species"]:
            sp["spectrum"] = dict(sp["spectrum"], index=1.5, r_min_gv=2.0, r_max_gv=32.0)
        cfg["charge"]["tail_fraction"] = 0.2  # enough confusion between charges to populate the off-diagonal blocks
        cfg["periods"] = {"count": 4, "duration_s": 1000.0, "rate_hz": 5.0, "live_fraction": 0.9}
        cfg["eras"] = cfg["eras"][:1]
        (d / "toy.json").write_text(json.dumps(cfg), encoding="utf-8")
        code, out = run(SCRIPTS / "toy_spectrometer.py", "generate", d / "toy.json", "--seed", 4, "--events-out",
                        d / "ev.csv", "--periods-out", d / "per.csv")
        assert code == 0, out
        with (d / "ev.csv").open() as fh:
            rows = list(csv.DictReader(line for line in fh if not line.startswith("#")))
        cls.species = {"p": 1, "He4": 2}
        cls.truth, cls.reco = {}, {}
        e = [float(x) for x in EDGES]

        def bin_of(x):
            return next((i for i in range(len(e) - 1) if e[i] <= x < e[i + 1]), None)
        for s in cls.species:
            cls.truth[s] = [0.0] * (len(e) - 1)
            cls.reco[s] = [0.0] * (len(e) - 1)
        blocks = []
        for t, zt in cls.species.items():
            mine = [r for r in rows if r["species"] == t]
            for r in mine:
                b = bin_of(float(r["rigidity_true_gv"]))
                if b is not None:
                    cls.truth[t][b] += 1
            for s, zs in cls.species.items():
                path = d / f"ev_{t}_{s}.csv"
                with path.open("w", newline="") as fh:
                    w = csv.writer(fh)
                    w.writerow(["truth", "reco", "sel"])
                    for r in mine:
                        zr = round(float(r["z_meas"]))
                        sel = int(zr == zs)
                        w.writerow([r["rigidity_true_gv"], r["rigidity_meas_gv"], sel])
                        if sel and bin_of(float(r["rigidity_true_gv"])) is not None:
                            rb = bin_of(float(r["rigidity_meas_gv"]))
                            if rb is not None:
                                cls.reco[s][rb] += 1
                resp = d / f"resp_{t}_{s}.json"
                code, out = run(SCRIPTS / "build_response.py", "build", path, "--truth-col", "truth", "--reco-col", "reco",
                                "--unweighted", "--selected-col", "sel", "--truth-edges", *EDGES, "--reco-edges", *EDGES,
                                "--variable", "rigidity", "--unit", "GV", "--normalization", "conditional_on_generated",
                                "--acceptance", "outside_matrix", "--residual", "inverse", "--intended-use",
                                "forward_folding", "--artifact-id", f"resp-{t}-{s}".lower(), "--objective", "SYNTHETIC",
                                "--created", "2026-10-17", "--out", resp)
                assert code == 0, out
                blocks.append({"true": t, "reco": s, "response": str(resp), "source": "toy_spectrometer.py seed 4",
                               "effects": ["migration"] if t == s else ["species_migration"]})
        cls.manifest = d / "manifest.json"
        cls.manifest.write_text(json.dumps({"manifest_version": "0.1.0", "species": list(cls.species),
                                            "variable": {"name": "rigidity", "unit": "GV"},
                                            "inefficiency_location": "outside", "blocks": blocks}), encoding="utf-8")

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_fold_equals_direct_counting(self):
        truth = self.d / "truth.json"
        truth.write_text(json.dumps({"truth": self.truth}), encoding="utf-8")
        code, out = run(SCRIPT, "fold", "--manifest", self.manifest, "--truth", truth)
        self.assertEqual(code, 0, out)
        for s in self.species:
            for a, b in zip(out["reco"][s], self.reco[s]):
                self.assertAlmostEqual(a, b, places=6)
        self.assertGreater(sum(self.reco["p"]), 0)
        self.assertGreater(sum(self.reco["He4"]), 0)

    def test_assemble_checks_column_sums(self):
        code, out = run(SCRIPT, "assemble", "--manifest", self.manifest)
        self.assertEqual(code, 0, out)
        for s, sums in out["column_sums"].items():
            self.assertTrue(all(c <= 1 + 1e-12 for c in sums), (s, sums))
        self.assertEqual(out["flattened_bins"], {"reco": 8, "truth": 8})

    def test_planted_double_count_is_caught(self):
        chain = self.d / "chain.json"
        chain.write_text(json.dumps({"extension": {"corrections": [{"effect_id": "species_migration"}]}}), encoding="utf-8")
        code, out = run(SCRIPT, "check", "--manifest", self.manifest, "--chain", chain)
        self.assertEqual(code, 1, out)
        self.assertEqual(out["status"], "failed")
        self.assertIn("species_migration", json.dumps(out["double_counted"]))
        chain.write_text(json.dumps({"extension": {"corrections": [{"effect_id": "trigger_efficiency"}]}}), encoding="utf-8")
        code, out = run(SCRIPT, "check", "--manifest", self.manifest, "--chain", chain)
        self.assertEqual(code, 0, out)


class FromRatesAndRefusals(unittest.TestCase):
    def test_from_rates_blocks_and_fold(self):
        with tempfile.TemporaryDirectory() as d:
            rates = Path(d) / "r.json"
            rates.write_text(json.dumps({"sign_rates": {"edges": [1, 10, 100], "variable": "rigidity",
                                                        "rates": [{"true": "negative", "reco": "positive",
                                                                   "rate": [0.01, 0.1]}]}}), encoding="utf-8")
            out_m = Path(d) / "m.json"
            code, out = run(SCRIPT, "from-rates", "--rates", rates, "--out", out_m)
            self.assertEqual(code, 0, out)
            truth = Path(d) / "t.json"
            truth.write_text(json.dumps({"truth": {"negative": [100, 1000], "positive": [0, 0]}}), encoding="utf-8")
            code, out = run(SCRIPT, "fold", "--manifest", out_m, "--truth", truth)
        self.assertEqual(code, 0, out)
        self.assertEqual([round(x, 9) for x in out["reco"]["positive"]], [1.0, 100.0])
        self.assertEqual([round(x, 9) for x in out["reco"]["negative"]], [99.0, 900.0])

    def test_refusals_and_large_model_warning(self):
        with tempfile.TemporaryDirectory() as d:
            def man(blocks, species=("a", "b")):
                p = Path(d) / "m.json"
                p.write_text(json.dumps({"manifest_version": "0.1.0", "species": list(species),
                                         "variable": {"name": "x", "unit": "GeV"}, "inefficiency_location": "outside",
                                         "blocks": blocks}), encoding="utf-8")
                return p
            inline = lambda m, e: {"matrix": m, "truth_edges": e, "reco_edges": e}  # noqa: E731
            over = man([{"true": "a", "reco": "a", "response": inline([[0.8, 0], [0, 0.9]], [0, 1, 2]), "source": "s"},
                        {"true": "a", "reco": "b", "response": inline([[0.3, 0], [0, 0.0]], [0, 1, 2]), "source": "s"}])
            code, out = run(SCRIPT, "assemble", "--manifest", over)
            self.assertEqual(code, 2, out)
            self.assertIn("column", out["error"])
            axes = man([{"true": "a", "reco": "a", "response": inline([[0.8, 0], [0, 0.9]], [0, 1, 2]), "source": "s"},
                        {"true": "b", "reco": "b", "response": inline([[0.8, 0], [0, 0.9]], [0, 1, 3]), "source": "s"}])
            code, out = run(SCRIPT, "assemble", "--manifest", axes)
            self.assertEqual(code, 2, out)
            n = 31
            big = man([{"true": s, "reco": s, "response": inline([[0.5 if i == j else 0 for j in range(n)] for i in range(n)],
                                                                list(range(n + 1))), "source": "s"} for s in ("a", "b")])
            code, out = run(SCRIPT, "assemble", "--manifest", big)
            self.assertEqual(code, 0, out)
            self.assertTrue(any("parametrized forward folding" in w for w in out["warnings"]))


if __name__ == "__main__":
    unittest.main()
