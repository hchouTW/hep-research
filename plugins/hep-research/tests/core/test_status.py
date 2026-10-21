"""core/status.py (F-04): run statuses, exit codes 0-3 and their mapping to artifact status labels."""
import contextlib
import io
import json
import subprocess
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

    def test_unknown_status_is_incomplete_with_a_message_not_a_traceback(self):  # T16
        for status in ("satisfied", "Passed", "", None, ["ok"]):  # an obligation state, a typo, empty, wrong types
            with self.subTest(status=status):
                err = io.StringIO()
                with contextlib.redirect_stderr(err):
                    self.assertEqual(exit_code(status), 3)
                self.assertIn(f"unknown run status {status!r}", err.getvalue())
        with self.assertRaises(ValueError):
            artifact_labels("satisfied", ["observed"])  # no artifact is labelled from an unknown outcome

    def test_a_script_with_an_unknown_status_exits_3_without_a_traceback(self):
        script = f"import sys; sys.path.insert(0, {str(ROOT)!r}); from core.status import exit_code; " \
                 "sys.exit(exit_code('statisfied'))"
        p = subprocess.run([sys.executable, "-I", "-c", script], capture_output=True, text=True, timeout=60)
        self.assertEqual(p.returncode, 3)
        self.assertNotIn("Traceback", p.stderr)
        self.assertIn("unknown run status 'statisfied'", p.stderr)

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
