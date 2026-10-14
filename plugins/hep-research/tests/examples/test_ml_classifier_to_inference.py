"""Journey J9 (physics-ml -> hep-statistics): SYNTHETIC classifier to signal-strength fit. One run with the default
seed and toys, with PyTorch made unimportable (the default trainer is NumPy); it must pass every pre-declared
criterion, reproduce the committed results.json byte for byte, and write an ml-artifact and a statistical-result
that validate, with the ml-artifact's grouping key, split check, calibration and domain-shift check recorded and the
statistical-result linked to it by id and sha256."""
import contextlib
import hashlib
import importlib.util
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[2]
SCRIPT = PLUGIN / "examples" / "ml-classifier-to-inference" / "run.py"
_MISSING = object()
sys.path.insert(0, str(PLUGIN))

try:
    import numpy  # noqa: F401
    import scipy  # noqa: F401
    import matplotlib  # noqa: F401
    HAVE_DEPS = True
except ImportError:
    HAVE_DEPS = False


def load():
    spec = importlib.util.spec_from_file_location("ml_classifier_to_inference_run", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["ml_classifier_to_inference_run"] = mod
    spec.loader.exec_module(mod)
    return mod


@unittest.skipUnless(HAVE_DEPS, "numpy, scipy and matplotlib are required")
class J9MlToInferenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.out = Path(cls.tmp.name)
        # The default chain must not need PyTorch: block its import for this run only. Only the "torch" entry is
        # patched: restoring a copy of the whole of sys.modules would also drop the modules imported meanwhile
        # (scipy submodules, for example) and break later tests.
        saved = sys.modules.get("torch", _MISSING)
        sys.modules["torch"] = None
        try:
            cls.m = load()
            with contextlib.redirect_stdout(io.StringIO()):
                cls.code = cls.m.main(["--out", str(cls.out)])
        finally:
            if saved is _MISSING:
                del sys.modules["torch"]
            else:
                sys.modules["torch"] = saved
        cls.r = json.loads((cls.out / "results.json").read_text())
        art = cls.out / "artifacts"
        cls.ml = json.loads((art / "ml_artifact.json").read_text())
        cls.stat = json.loads((art / "statistical_result.json").read_text())

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_all_criteria_pass(self):
        self.assertEqual(self.code, 0, self.r["pass"])
        self.assertTrue(all(self.r["pass"].values()))
        self.assertEqual(self.r["trainer"], "numpy")

    def test_reproduces_committed_output(self):
        committed = (SCRIPT.parent / "output" / "results.json").read_bytes()
        self.assertEqual((self.out / "results.json").read_bytes(), committed)

    def test_committed_artifacts_match_within_tolerance(self):
        """ML-K13: the committed ml_artifact.json and statistical_result.json, not only the rounded results.json, are
        reproduced: every number within a relative tolerance of 1e-9 (last-bit BLAS differences), every other value
        equal; digests and input hashes are skipped because they move with the artifact bytes, and the framework version
        because it records the installed NumPy, not a result."""
        skip = {"sha256", "plugin_release", "digest", "framework"}

        bad: list = []

        def close(a, b, path):
            if isinstance(a, dict) and isinstance(b, dict):
                if set(a) != set(b):
                    bad.append((path, sorted(set(a) ^ set(b))))
                for k in set(a) & set(b):
                    if k not in skip:
                        close(a[k], b[k], f"{path}.{k}")
            elif isinstance(a, list) and isinstance(b, list):
                if len(a) != len(b):
                    bad.append((path, len(a), len(b)))
                for i, (x, y) in enumerate(zip(a, b)):
                    close(x, y, f"{path}[{i}]")
            elif isinstance(a, float) or isinstance(b, float):
                if not abs(a - b) <= 1e-9 * max(abs(a), abs(b), 1e-300):
                    bad.append((path, a, b))
            elif a != b:
                bad.append((path, a, b))

        committed = SCRIPT.parent / "output" / "artifacts"
        close(json.loads((committed / "ml_artifact.json").read_text()), self.ml, "ml_artifact")
        close(json.loads((committed / "statistical_result.json").read_text()), self.stat, "statistical_result")
        self.assertEqual(bad, [], f"{len(bad)} differences (committed, rerun): {bad[:15]}")

    def test_artifacts_validate(self):
        from contracts.validate import validate_artifact
        from contracts.vocab import Vocabulary
        vocab = Vocabulary.with_profiles([self.m.PROFILE])
        for doc in (self.ml, self.stat):
            rep = validate_artifact(doc, vocab)
            self.assertTrue(rep.ok, [f.message for f in rep.errors])
            self.assertEqual([f.code for f in rep.findings if f.level == "unresolved"], [], doc["artifact_type"])
            self.assertIn("synthetic", doc["status"])

    def test_ml_artifact_content(self):
        ext = self.ml["extension"]
        self.assertTrue(ext["splits"]["grouping_key"].startswith("run"))
        self.assertEqual(ext["splits"]["overlap_check"]["result"], "pass")
        self.assertIs(ext["splits"]["test_groups_disjoint"], True)
        self.assertEqual(set(ext["training_domain"]), set(ext["features"]))
        self.assertEqual(ext["output_semantics"], "score")  # the calibration is a no-op within the ECE floor (PML Q5)
        self.assertEqual(ext["calibration"]["outcome"], "no-op-within-floor")
        cal = ext["calibration"]
        self.assertEqual(cal["method"], "temperature")
        self.assertNotEqual(cal["fit_sample"], cal["validation"]["sample"])
        self.assertEqual(ext["domain_shift"]["status"], "checked")
        self.assertIn(self.m.SHIFT_FEATURE, ext["domain_shift"]["result"]["variables_above_noise_floor"])
        self.assertEqual(ext["weights"]["negative_weight_treatment"], "signed")
        self.assertIn("templates", ext["weights"]["used_in"])
        metrics = " ".join(d["metric"] + " " + d["quantity_affected"] for d in ext["downstream_validation"]).lower()
        self.assertIn("signal strength", metrics)
        self.assertNotIn("auc", metrics)
        self.assertTrue({"closure", "coverage", "pull"} <= {d["metric"] for d in ext["downstream_validation"]})

    def test_rowlevel_split_is_caught(self):
        row = self.r["splits"]["rowlevel"]
        self.assertEqual((row["exit"], row["status"]), (1, "failed"))
        self.assertIn("leakage", row["failure_kind"])

    def test_statistical_result_links_the_ml_artifact(self):
        link = [i for i in self.stat["inputs"] if i.get("artifact_type") == "ml-artifact"]
        self.assertEqual(len(link), 1)
        self.assertEqual(link[0]["artifact_id"], self.ml["artifact_id"])
        digest = hashlib.sha256((self.out / link[0]["ref"]).read_bytes()).hexdigest()
        self.assertEqual(link[0]["sha256"], digest)
        self.assertEqual(self.stat["extension"]["coverage"]["check"], "toys")

    def test_asimov_closure_and_toys(self):
        self.assertLess(abs(self.r["asimov"]["mu_hat"] - self.m.MU_TRUE), 1e-3)
        self.assertEqual(self.r["toys"]["failed"], 0)

    def test_labels_and_profile(self):
        self.assertIn("SYNTHETIC", self.r["label"])
        self.assertIn("SYNTHETIC", (self.out / "report.md").read_text().splitlines()[0])
        self.assertEqual(self.r["profiles_loaded"], ["experiment:synthetic-collider"])
        for doc in (self.ml, self.stat):
            self.assertEqual([b["profile"] for b in doc["bindings"]["experiments"]], ["experiment:synthetic-collider"])


if __name__ == "__main__":
    unittest.main()
