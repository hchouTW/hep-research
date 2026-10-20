"""hep-ml audit (PML-WP0.1: ML-C01, ML-K03, ML-C13): a calibration fitted and evaluated on the same sample never
reaches a valid ml-artifact.

Before the fix (0.9.0, source brief A5): calibration.py --allow-same-sample recorded sample_check.disjoint false, the
writer dropped sample_check, the validator compared the two sample names as exact strings, and the artifact validated
with no finding (ECE after 6.5e-17). Without --id-col, a copy of the evaluation file with one byte changed passed the
disjointness check. All inputs SYNTHETIC.
"""
import copy
import csv
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
ML = ROOT / "skills" / "hep-ml"
sys.path.insert(0, str(ROOT))
from contracts import validate as v  # noqa: E402

CURRENT = json.loads((ROOT / "contracts" / "fixtures" / "artifacts" / "valid" / "ml_artifact_v25.json").read_text())
SUMMARY = {"task": "classification", "features": ["x"], "labels": ["bkg", "sig"], "grouping_key": "run",
           "training_domain": {"x": [0, 1]}, "preprocessing": [],
           "model_hash": "sha256:" + "ab" * 32,
           "split_check": {"tool": "check_split_integrity.py", "result": "pass"},
           "environment": {"device": "cpu", "precision": "fp32", "seeds": {"torch": 1}},
           "weights": {"source": "w", "negative_weight_treatment": "none-present", "used_in": ["loss"]}}


def codes(rep, level="error"):
    return {f.code for f in rep.findings if f.severity == level}


def run(*args):
    return subprocess.run([sys.executable, *map(str, args)], capture_output=True, text=True, timeout=600)


def write_scores(path, n=2000, seed=1):
    import numpy as np
    rng = np.random.default_rng(seed)
    y = rng.integers(0, 2, n)
    p = np.where(y == 1, rng.beta(5, 3, n), rng.beta(3, 5, n))
    s = 1 / (1 + np.exp(-0.5 * np.log(p / (1 - p))))
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["id", "label", "weight", "score"])
        for i in range(n):
            w.writerow([f"e{i}", int(y[i]), 1.0, float(s[i])])


class CalibrationCliTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        write_scores(self.dir / "val_scores.csv")
        (self.dir / "copy_val.csv").write_bytes((self.dir / "val_scores.csv").read_bytes())

    def tearDown(self):
        self.tmp.cleanup()

    def cal(self, *extra):
        return run(ML / "assets" / "calibration.py", "--fit", self.dir / "val_scores.csv", "--eval",
                   self.dir / "copy_val.csv", "--method", "isotonic", *extra)

    def test_id_col_is_required_unless_declined(self):
        text = (self.dir / "copy_val.csv").read_text()
        (self.dir / "copy_val.csv").write_text(text.replace("e0,", "f0,", 1))  # one byte changed, same events
        r = self.cal()
        self.assertEqual(r.returncode, 2, r.stdout)
        self.assertIn("--id-col", r.stdout)       # F-04: the refusal is a JSON status on stdout
        r = self.cal("--id-col", "id")
        self.assertEqual(r.returncode, 2, r.stdout)  # 1999 shared event ids
        r = self.cal("--no-id-check")
        self.assertEqual(r.returncode, 0, r.stderr)
        check = json.loads(r.stdout)["calibration"]["sample_check"]
        self.assertEqual(check["id_check"], "skipped (--no-id-check)")
        self.assertNotEqual(check["fit_sha256"], check["eval_sha256"])

    def test_a5_same_sample_records_both_hashes_inside_the_calibration_block(self):
        r = self.cal("--id-col", "id", "--allow-same-sample")
        self.assertEqual(r.returncode, 0, r.stderr)
        block = json.loads(r.stdout)["calibration"]
        self.assertFalse(block["sample_check"]["disjoint"])
        self.assertEqual(block["sample_check"]["fit_sha256"], block["sample_check"]["eval_sha256"])
        self.assertEqual(len(block["sample_check"]["fit_sha256"]), 64)

    def test_a5_end_to_end_is_refused(self):
        r = self.cal("--id-col", "id", "--allow-same-sample")
        (self.dir / "cal.json").write_text(r.stdout)
        (self.dir / "summary.json").write_text(json.dumps(SUMMARY))
        w = run(ML / "scripts" / "write_ml_artifact.py", "--run-summary", self.dir / "summary.json",
                "--calibration", self.dir / "cal.json", "--status", "synthetic", "--output-semantics", "probability",
                "--out", self.dir / "ml.json")
        self.assertEqual(w.returncode, 1, w.stdout)
        self.assertIn("ml.calibration_on_fit_sample", w.stdout)


class SampleIdentityPropertyTests(unittest.TestCase):
    """sci-fix ML-CALIBRATION, axis C: the sample checks against independent computations over finite domains."""

    def test_event_id_check_is_exhaustively_right_over_all_subset_pairs(self):
        """Exhaustive: every pair of subsets of six event ids (4096 pairs), the overlap counted here by a sorted
        merge, not a set intersection; the record's id_overlap and disjoint flag must equal it, and the check must
        refuse exactly the overlapping pairs. Negative control: the pre-fix decision without an id check (names and
        file content differ, so 'disjoint') calls all 4096 pairs disjoint; 3367 of them share events."""
        import itertools

        sys.path.insert(0, str(ML / "assets"))
        import calibration

        universe = [f"e{i}" for i in range(6)]
        subsets = [list(c) for r in range(7) for c in itertools.combinations(universe, r)]

        def merge_overlap(a, b):
            a, b, i, j, n = sorted(a), sorted(b), 0, 0, 0
            while i < len(a) and j < len(b):
                if a[i] == b[j]:
                    n, i, j = n + 1, i + 1, j + 1
                elif a[i] < b[j]:
                    i += 1
                else:
                    j += 1
            return n

        wrong_without_ids = disjoint = 0
        for fit, ev in itertools.product(subsets, subsets):
            want = merge_overlap(fit, ev)
            rec = calibration.sample_provenance("fit.csv", "eval.csv", fit, ev, allow_same_sample=True)
            self.assertEqual((rec["id_overlap"], rec["disjoint"]), (want, want == 0), (fit, ev))
            if want:
                with self.assertRaises(ValueError):
                    calibration.sample_provenance("fit.csv", "eval.csv", fit, ev)
            disjoint += want == 0
            wrong_without_ids += want > 0  # different names and bytes: the pre-fix check saw nothing
        self.assertEqual(disjoint, 3 ** 6)  # each id in fit only, eval only, or neither
        self.assertEqual(wrong_without_ids, 4 ** 6 - 3 ** 6)

    def test_validator_names_one_sample_under_every_spelling_of_its_path(self):
        """Independent implementation: pathlib.PurePosixPath (after stripping and turning backslashes into slashes)
        and case folding decide whether two spellings name one file; the validator's ml.calibration_on_fit_sample
        must fire exactly for the pairs that do. Spellings: leading './', doubled separators, backslashes, case,
        surrounding whitespace, of two different files. Negative control: the pre-fix exact-string comparison
        fires for none of the differing spellings."""
        from pathlib import PurePosixPath

        def spellings(path):
            out = set()
            for prefix in ("", "./", "././"):
                for sep in ("/", "//", "\\"):
                    for case in (str, str.upper):
                        for pad in ("", " ", "\t"):
                            out.add(pad + prefix + case(path).replace("/", sep) + pad)
            return sorted(out)

        def same_file(a, b):
            def norm(x):
                return str(PurePosixPath(x.strip().replace("\\", "/"))).casefold()
            return norm(a) == norm(b)

        names = spellings("work/val_scores.csv") + spellings("work/test_scores.csv")
        fired = should = 0
        for fit, ev in itertools_pairs(names):
            doc = copy.deepcopy(CURRENT)
            doc["extension"]["calibration"]["fit_sample"] = fit
            doc["extension"]["calibration"]["validation"]["sample"] = ev
            got = "ml.calibration_on_fit_sample" in codes(v.validate_artifact(doc))
            with self.subTest(fit=fit, eval=ev):
                self.assertEqual(got, same_file(fit, ev))
            fired += got
            should += same_file(fit, ev)
        self.assertEqual(fired, should)
        self.assertGreater(should, 1000)


def itertools_pairs(names):
    """Ordered pairs of distinct spellings (the exact-name case is the older 2.5.0 rule's)."""
    return [(a, b) for a in names for b in names if a != b]


class CalibrationIdentityRuleTests(unittest.TestCase):
    """Probe rows M01-M03 on the current valid fixture (contract 2.8.0, native) and on a 2.7.0 copy (--strict)."""

    def variants(self):
        def spelled(e):  # M01: the same file named two ways
            e["calibration"]["fit_sample"] = "./work/Val_Scores.csv "
            e["calibration"]["validation"]["sample"] = "work/val_scores.csv"

        def hashes(e):  # M02: different names, identical content
            e["calibration"]["sample_check"] = {"fit_sha256": "1" * 64, "eval_sha256": "1" * 64}

        def flag(e):  # M03: the calibration tool said the samples were not disjoint
            e["calibration"]["sample_check"] = {"disjoint": False, "same_sample_allowed": True}
        return {"M01": spelled, "M02": hashes, "M03": flag}

    def test_rows_are_errors_natively_and_under_strict(self):
        for name, mutate in self.variants().items():
            with self.subTest(name):
                doc = copy.deepcopy(CURRENT)
                mutate(doc["extension"])
                self.assertIn("ml.calibration_on_fit_sample", codes(v.validate_artifact(doc)))
                old = copy.deepcopy(doc)
                old["contract_version"] = old["versions"]["contracts"] = "2.7.0"
                self.assertNotIn("ml.calibration_on_fit_sample", codes(v.validate_artifact(old)))
                self.assertIn("ml.calibration_on_fit_sample", codes(v.validate_artifact(old, strict=True)))

    def test_distinct_hashes_and_names_pass(self):
        doc = copy.deepcopy(CURRENT)
        doc["extension"]["calibration"]["sample_check"] = {"disjoint": True, "fit_sha256": "1" * 64,
                                                           "eval_sha256": "2" * 64}
        self.assertNotIn("ml.calibration_on_fit_sample", codes(v.validate_artifact(doc)))


if __name__ == "__main__":
    unittest.main()
