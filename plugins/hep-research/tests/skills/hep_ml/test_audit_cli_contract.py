"""hep-ml audit (PML-WP1.5, ML-C17): every hep-ml script follows the CLI contract: invalid input exits 2 with a
one-line message and no traceback, a missing PyTorch exits 3, and the data-report scripts take --status and echo it as
status_label. Before the fix, invalid input exited 1 (or 0 for --params inf), and a negative batch size crashed with a
traceback."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SC = ROOT / "skills" / "hep-ml" / "scripts"
sys.path.insert(0, str(SC))
VOCAB = json.loads((ROOT / "contracts" / "vocab" / "core.json").read_text())["vocabularies"]["artifact_statuses"]


def run(*args):
    return subprocess.run([sys.executable, *map(str, args)], capture_output=True, text=True, timeout=600)


class CliContractTests(unittest.TestCase):
    def test_invalid_input_is_exit_2_without_traceback(self):
        with tempfile.TemporaryDirectory() as td:
            bad = Path(td) / "bad.json"
            bad.write_text("{bad")
            cases = [
                (SC / "estimate_training_memory.py", "--params", "inf"),
                (SC / "estimate_training_memory.py", "--params", "nan"),
                (SC / "estimate_training_memory.py", "--params", "-5"),
                (SC / "estimate_compute_budget.py", "--params", "inf", "--tokens", "1e9"),
                (SC / "serving_capacity.py", "--qps", "inf", "--batch-size", "8", "--batch-latency-ms", "10",
                 "--latency-budget-ms", "100"),
                (SC / "compare_model_runs.py", bad),
                (SC / "check_dataset_contract.py", "--batch-size", "-1"),
                (SC / "find_nan_batches.py", "--max-batches", "-1"),
                (SC / "profile_dataloader.py", "--batches", "-3"),
                (SC / "benchmark_model.py", "--steps", "-1"),
                (SC / "check_split_integrity.py", bad),
                (SC / "check_surrogate_domain.py", bad),
            ]
            for case in cases:
                with self.subTest(case[0].name, args=case[1:]):
                    r = run(*case)
                    self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
                    self.assertNotIn("Traceback", r.stdout + r.stderr)

    def test_status_label_is_echoed_and_matches_the_vocabulary(self):
        import check_split_integrity
        import check_surrogate_domain
        import compare_model_runs
        import make_grouped_splits
        for mod in (check_split_integrity, check_surrogate_domain, compare_model_runs, make_grouped_splits):
            self.assertEqual(set(mod.STATUSES), set(VOCAB), mod.__name__)
        with tempfile.TemporaryDirectory() as td:
            m = Path(td) / "m.json"
            m.write_text(json.dumps({"train": ["a"], "test": ["b"], "groups": {"a": "r1", "b": "r2"}}))
            r = run(SC / "check_split_integrity.py", m, "--json", "--status", "synthetic")
            self.assertEqual(json.loads(r.stdout)["status_label"], "synthetic")
            r = run(SC / "compare_model_runs.py", "--baseline", "1", "2", "3", "--variant", "2", "3", "4", "--json",
                    "--lower-is-better", "--status", "synthetic")
            self.assertEqual(json.loads(r.stdout)["status_label"], "synthetic", r.stderr)


if __name__ == "__main__":
    unittest.main()
