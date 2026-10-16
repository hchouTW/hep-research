"""core/status.py (F-04): run statuses, exit codes 0-3 and their mapping to artifact status labels."""
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from core.status import ARTIFACT_LABELS, EXIT_CODES, RUN_STATUSES, artifact_labels, exit_code  # noqa: E402


class SharedVocabulary(unittest.TestCase):
    def test_run_statuses_map_to_the_four_exit_codes(self):
        self.assertEqual(EXIT_CODES, (0, 1, 2, 3))
        self.assertEqual(set(RUN_STATUSES.values()), set(EXIT_CODES))
        self.assertEqual([exit_code(s) for s in ("ok", "failed", "rejected", "incomplete")], [0, 1, 2, 3])
        with self.assertRaises(KeyError):
            exit_code("satisfied")      # an analysis-check obligation state, not a run status

    def test_labels_match_the_contract_vocabulary(self):
        vocab = json.loads((ROOT / "contracts/vocab/core.json").read_text())["vocabularies"]["artifact_statuses"]
        self.assertEqual(set(ARTIFACT_LABELS), set(vocab))

    def test_artifact_labels(self):
        self.assertEqual(artifact_labels("ok", ["synthetic"]), ["synthetic"])
        self.assertEqual(artifact_labels("failed", ["observed"]), ["observed", "failed"])
        self.assertEqual(artifact_labels("not-converged", ["synthetic", "failed"]), ["synthetic", "failed"])
        self.assertEqual(artifact_labels("incomplete", ["synthetic"]), ["synthetic", "unvalidated"])
        for status in ("rejected", "refused", "missing-dependency", "not-run"):
            self.assertIsNone(artifact_labels(status, ["observed"]))
        with self.assertRaises(ValueError):
            artifact_labels("ok", ["final"])


if __name__ == "__main__":
    unittest.main()
