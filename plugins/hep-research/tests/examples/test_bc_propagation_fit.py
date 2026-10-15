"""End-to-end B/C grid fit (examples/bc-propagation-fit, ams02-skill-upgrade WP8): theory:cr-secondary-ratio grid
predictions, SYNTHETIC B/C data with a full covariance, covariance_fit.py tabulated-grid.

One run with the default seed and toys (about 35 s; envelope artifacts kept in a temporary --keep directory): every pre-declared criterion passes, D0/L is recovered and the
degenerate direction is matched to the theory spec, the result matches the committed output (floats to rel 1e-6,
since fit outputs are minimizer results; environment versions are not compared), and the committed artifacts are
consistent with the profile. The byte-for-byte rerun is slow-gated (HEP_SLOW_TESTS=1)."""
import contextlib
import hashlib
import importlib.util
import io
import json
import math
import os
import sys
import tempfile
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[2]
EXAMPLE = PLUGIN / "examples" / "bc-propagation-fit"
SCRIPT = EXAMPLE / "run.py"
COMMITTED = EXAMPLE / "output" / "results.json"
NOT_COMPARED = {"environment"}

try:
    import numpy  # noqa: F401
    import scipy  # noqa: F401
    HAVE_DEPS = True
except ImportError:
    HAVE_DEPS = False


def differences(a, b, path="$", rel=1e-6, abs_tol=1e-9) -> list[str]:
    if isinstance(a, bool) or isinstance(b, bool):
        return [] if a == b else [f"{path}: {a!r} != {b!r}"]
    if isinstance(a, (int, float)) and isinstance(b, (int, float)) and (isinstance(a, float) or isinstance(b, float)):
        return [] if math.isclose(a, b, rel_tol=rel, abs_tol=abs_tol) else [f"{path}: {a} != {b}"]
    if isinstance(a, dict) and isinstance(b, dict):
        if sorted(a) != sorted(b):
            return [f"{path}: keys {sorted(a)} != {sorted(b)}"]
        return [d for k in a if not (path == "$" and k in NOT_COMPARED)
                for d in differences(a[k], b[k], f"{path}.{k}", rel, abs_tol)]
    if isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            return [f"{path}: length {len(a)} != {len(b)}"]
        return [d for i, (x, y) in enumerate(zip(a, b)) for d in differences(x, y, f"{path}[{i}]", rel, abs_tol)]
    return [] if a == b else [f"{path}: {a!r} != {b!r}"]


def load_run_module():
    spec = importlib.util.spec_from_file_location("bc_propagation_fit_run", SCRIPT)
    m = importlib.util.module_from_spec(spec)
    sys.modules["bc_propagation_fit_run"] = m
    spec.loader.exec_module(m)
    return m


@unittest.skipUnless(HAVE_DEPS, "numpy and scipy are required (requirements-core.txt)")
class BCPropagationFitTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = load_run_module()
        cls.tmp = tempfile.TemporaryDirectory()
        cls.out = Path(cls.tmp.name) / "run"
        cls.work = Path(cls.tmp.name) / "work"
        with contextlib.redirect_stdout(io.StringIO()):
            cls.code = cls.m.main(["--out", str(cls.out), "--keep", str(cls.work)])
        cls.r = json.loads((cls.out / "results.json").read_text())

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_passes_predeclared_criteria(self):
        self.assertEqual(self.code, 0, self.r["criteria"])
        self.assertTrue(all(self.r["criteria"].values()))

    def test_recovers_D0_over_L(self):
        truth = math.log(3e28 / 4.0)
        a = self.r["asimov"]
        self.assertLess(abs(a["ln_D0_over_L"] - truth), 0.25 * a["sigma_ln_D0_over_L"])
        fa = self.r["pseudo_data"]["fits"]["models/xs-illustrative-A.json"]
        self.assertLess(abs(fa["ln_D0_over_L"] - truth), 3 * fa["sigma_ln_D0_over_L"])
        self.assertTrue(fa["D0_over_L_constrained"])
        self.assertFalse(any(p["constrained"] for p in fa["parameters"].values()))

    def test_degenerate_direction_matched_to_theory_spec(self):
        self.assertEqual(self.r["pseudo_data"]["theory_spec_degenerate_directions"], ["D0/L"])
        for f in [self.r["asimov"], *self.r["pseudo_data"]["fits"].values()]:
            (d,) = f["degenerate_directions"]
            self.assertEqual(d["matches_theory_spec"], "D0/L")
            self.assertAlmostEqual(abs(d["eigenvector"]["D0"]), abs(d["eigenvector"]["L"]), delta=0.05)
            self.assertGreater(d["eigenvector"]["D0"] * d["eigenvector"]["L"], 0)
        self.assertEqual(self.r["pseudo_data"]["warnings"], [])

    def test_cross_sections_as_model_set(self):
        p = self.r["pseudo_data"]
        self.assertEqual(p["cross_section_uncertainty"]["mode"], "model-set")
        self.assertFalse(p["envelope"]["gaussian"])
        self.assertEqual(p["envelope"]["prescription"]["owner"], "hep-theory")
        self.assertIn("synthetic", p["carried_statuses"])

    def test_negatives_refused(self):
        neg = {n["name"]: n for n in self.r["negative_variants"]}
        self.assertEqual({k: v["exit"] for k, v in neg.items()},
                         {"ungated-no-measurement": 1, "rigidity-bins": 1, "unfolded-level": 1, "unknown-correlation": 3})
        self.assertEqual(neg["unknown-correlation"]["status"], "incomplete")
        self.assertIn("variable", neg["rigidity-bins"]["error"])
        self.assertIn("level", neg["unfolded-level"]["error"])

    def test_data_binning_and_level_match_the_prediction(self):
        meas = json.loads((self.work / "measurement.json").read_text())
        node = json.loads(next((self.work / "grid").glob("node-xsA-*.json")).read_text())
        mo, po = meas["extension"]["observable"], node["extension"]["observable"]
        self.assertEqual(mo["variables"], po["variables"])
        self.assertEqual(mo["level"], "crsr:local-interstellar")
        self.assertEqual(mo["level"], po["level"])
        self.assertEqual(meas["extension"]["data"]["edges"], node["extension"]["values"]["edges"])
        self.assertEqual(node["extension"]["representation"], "grid")

    def test_grid_has_equal_log_spacing(self):
        man = json.loads((self.out / "artifacts" / "grid-manifest.json").read_text())
        for key in ("D0_cm2_s", "L_kpc"):
            steps = [math.log10(b / a) for a, b in zip(man[key], man[key][1:])]
            self.assertTrue(all(abs(s - 0.05) < 1e-9 for s in steps), key)
        self.assertEqual(man["nodes"], 2 * 21 * 21)

    def test_theory_spec_a_is_the_profiles(self):
        mine = json.loads((self.work / "theory-spec-xs-A.json").read_text())
        stored = json.loads((PLUGIN / "profiles/theory/cr-secondary-ratio/derivations/theory-spec.json").read_text())
        mine["artifact_id"] = stored["artifact_id"]
        self.assertEqual(mine, stored)

    def test_reproduces_committed_output(self):
        diffs = differences(self.r, json.loads(COMMITTED.read_text()))
        self.assertEqual(diffs, [], "\n".join(diffs[:20]))
        for name in self.m.COMMITTED:
            fresh = json.loads((self.out / "artifacts" / name).read_text())
            committed = json.loads((EXAMPLE / "output" / "artifacts" / name).read_text())
            self.assertEqual(differences(fresh, committed, rel=1e-9), [], name)

    def test_artifacts_validate_with_the_profile_vocabulary(self):
        import subprocess
        project = Path(self.tmp.name) / "hep-research.project.json"
        project.write_text(json.dumps({"schema_version": "1.0.0", "plugin_version": ">=0.10,<1.0", "experiments": [],
                                       "theory": [{"profile": "theory:cr-secondary-ratio", "version": "0.1.0"}]}))
        paths = [self.work / n for n in ("measurement.json", "theory-spec-xs-A.json", "theory-spec-xs-B.json")]
        paths.append(next((self.work / "grid").glob("node-xsB-*.json")))
        for p in paths:
            proc = subprocess.run([sys.executable, str(PLUGIN / "contracts" / "validate.py"), str(p),
                                   "--profiles-from", str(project)], capture_output=True, text=True, timeout=120)
            with self.subTest(artifact=p.name):
                self.assertEqual(proc.returncode, 0, proc.stdout)

    def test_kept_inputs_rerun_through_the_cli(self):
        import subprocess
        proc = subprocess.run([sys.executable, str(PLUGIN / "skills/hep-statistics/scripts/covariance_fit.py"), "fit",
                               "--input", str(self.work / "fit-input-asimov.json")], capture_output=True, text=True,
                              timeout=300)
        self.assertEqual(proc.returncode, 0, proc.stdout[-500:])
        comb = next(c for c in json.loads(proc.stdout)["fits"][0]["combinations"] if c["name"] == "D0/L")
        self.assertAlmostEqual(comb["ln_value"], self.r["asimov"]["ln_D0_over_L"], delta=1e-9)

    def test_committed_output_holds_no_envelope_artifact(self):
        # the grid nodes, theory-specs and data records are regenerated (--keep), not committed: the committed
        # examples/ artifacts are snapshotted by tests/contracts/test_gate_verdict_snapshot.py
        for p in (EXAMPLE / "output").rglob("*.json"):
            self.assertNotIn("artifact_type", json.loads(p.read_text()), p.name)

    def test_report_is_labelled_synthetic(self):
        text = (self.out / "report.md").read_text()
        self.assertIn("SYNTHETIC", text)
        self.assertIn("ILLUSTRATIVE", text)

    @unittest.skipUnless(os.environ.get("HEP_SLOW_TESTS") == "1", "slow (a second full run): set HEP_SLOW_TESTS=1")
    def test_rerun_is_byte_identical(self):
        other = Path(self.tmp.name) / "run2"
        with contextlib.redirect_stdout(io.StringIO()):
            self.m.main(["--out", str(other)])
        h = [hashlib.sha256(p.read_bytes()).hexdigest() for p in (self.out / "results.json", other / "results.json")]
        self.assertEqual(h[0], h[1])


if __name__ == "__main__":
    unittest.main()
