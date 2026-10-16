"""v6.3 D17: hep-measurement's review calls the cross-artifact check (V71). The call is opt-in: without its flags the
review is unchanged; with them the review carries a bounded summary (violated and unverified obligations, missing
bindings, next steps) and keeps its own verdict and exit code. The summary pages under its byte cap and carries IDs
and codes only."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests" / "contracts"))
import v63_cases as cases  # noqa: E402

REVIEW = ROOT / "skills" / "hep-measurement" / "scripts" / "review_measurement_spec.py"


def run(*args):
    p = subprocess.run([sys.executable, str(REVIEW), *map(str, args)], capture_output=True, text=True, cwd=ROOT, timeout=300)
    return p.returncode, p.stdout, p.stderr


@unittest.skipUnless(cases.HAVE_AMS, "the AMS example is not in this copy")
class V71ReviewCallsTheCheck(unittest.TestCase):
    @unittest.expectedFailure  # V71 (D17)
    def test_summary_within_budget_names_missing_bindings(self):
        from contracts.analysis_check import SUMMARY_BYTES
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "c"
            bundle = cases.chain_case(root)
            spec = root / "artifacts" / "measurement_spec.json"
            plain_code, plain_out, _ = run(spec)
            code, out, err = run(spec, "--check-bundle", bundle, "--check-root", root)
        self.assertEqual(code, plain_code, err)
        doc, plain = json.loads(out), json.loads(plain_out)
        self.assertEqual({k: v for k, v in doc.items() if k != "analysis_check"}, plain)
        summary = doc["analysis_check"]
        self.assertLessEqual(len(json.dumps(summary, indent=1).encode()), SUMMARY_BYTES)
        self.assertIn("check.response_use_unbound", summary["missing_bindings"])
        self.assertIn("check.coverage_undefined", summary["missing_bindings"])
        self.assertTrue(all(set(r) == {"obligation_id", "state", "reason", "next"} for r in summary["rows"]))
        self.assertEqual(summary["status"], "incomplete")

    def test_summary_pages(self):
        from contracts import analysis_check as ac
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "c"
            view, diags = ac.load_subject(cases.chain_case(root), root)
            report = ac.evaluate(view, diags)
        rows, cursor = [], 0
        while cursor is not None:
            page = ac.summary_page(report, cursor, 1500)
            self.assertLessEqual(len(json.dumps(page, indent=1).encode()), 1500 + 600)
            rows += page["rows"]
            cursor = page["next_cursor"]
        self.assertEqual(len(rows), page["total_rows"])
        self.assertEqual(len({r["obligation_id"] for r in rows}), len(rows))

    def test_unreadable_bundle_is_visible_and_the_review_still_runs(self):
        with tempfile.TemporaryDirectory() as td:
            spec = Path(td) / "spec.json"
            spec.write_text((ROOT / "contracts" / "fixtures" / "artifacts" / "valid" / "measurement_ratio.json").read_text())
            plain_code, _, _ = run(spec)
            code, out, _ = run(spec, "--check-bundle", Path(td) / "absent.json", "--check-root", td)
        if code == 2 and not out:
            self.skipTest("the review does not take --check-bundle yet")
        self.assertEqual(code, plain_code)
        self.assertEqual(json.loads(out)["analysis_check"]["status"], "usage")


if __name__ == "__main__":
    unittest.main()
