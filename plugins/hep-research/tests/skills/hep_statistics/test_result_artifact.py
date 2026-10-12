"""Audit T04: a core/stats CLI result and the statistical-result written from it agree on status (SYNTHETIC)."""
import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "skills" / "hep-statistics" / "scripts"))

import result_artifact as ra  # noqa: E402

from contracts.validate import publication_gate, validate_artifact  # noqa: E402
from core.stats import likelihood_limits as ll  # noqa: E402

DOC = {"bins": [{"n": 4, "b": 3.0, "s": 1.0}, {"n": 2, "b": 1.5, "s": 0.8}],
       "nuisances": [{"name": "bkg", "kind": "background_norm", "sigma": 0.1}]}


def run_cli(argv):
    buf = io.StringIO()
    with redirect_stdout(buf):
        code = ll.main(argv)
    return code, json.loads(buf.getvalue())


class ResultArtifactStatus(unittest.TestCase):
    def write(self, tmp, cli, *extra):
        src, out = Path(tmp) / "cli.json", Path(tmp) / "res.json"
        src.write_text(json.dumps(cli))
        with redirect_stdout(io.StringIO()):
            code = ra.main(["--cli-output", str(src), "--poi", "mu", "--construction", "asymptotic", "--test-statistic",
                            "q_mu_tilde", "--label", "synthetic", "--artifact-id", "synthetic-t04", "--out", str(out), *extra])
        return code, (json.loads(out.read_text()) if out.exists() else None)

    def test_ok_and_failed_cli_results_map_to_the_artifact(self):
        with tempfile.TemporaryDirectory() as tmp:
            model = Path(tmp) / "model.json"
            model.write_text(json.dumps(DOC))
            code, cli = run_cli(["shape-limit", "--input", str(model), "--seed", "1"])
            self.assertEqual((code, cli["status"]), (0, "ok"))
            code, art = self.write(tmp, cli, "--model", str(model))
            self.assertEqual(code, 0)
            self.assertEqual(art["extension"]["fit_status"], "converged")
            self.assertNotIn("failed", art["status"])
            self.assertTrue(validate_artifact(art).ok)
            self.assertEqual(len(art["extension"]["likelihood"]["model_sha256"]), 64)
            # coverage was not checked by this run: the gate says unresolved, not passed
            self.assertEqual(publication_gate(art)["status"], "unresolved")

            orig = ll.newton_fit
            ll.newton_fit = lambda f, x0, fixed_first=False, max_iter=60: orig(f, x0, fixed_first, 0)
            try:
                code, cli = run_cli(["shape-limit", "--input", str(model), "--seed", "1"])
            finally:
                ll.newton_fit = orig
            self.assertEqual((code, cli["status"]), (1, "failed"))
            code, art = self.write(tmp, cli, "--model", str(model))
            self.assertEqual(code, 1)
            self.assertEqual(art["extension"]["fit_status"], "failed")
            self.assertIn("failed", art["status"])
            self.assertEqual(art["extension"]["fit_diagnostics"]["status"], "failed")
            self.assertTrue(validate_artifact(art).ok)
            self.assertEqual(publication_gate(art)["status"], "failed")

    def test_zero_toy_exceedances_become_a_typed_bound(self):
        with tempfile.TemporaryDirectory() as tmp:
            code, cli = run_cli(["profile-significance", "--n", "20", "--b", "1", "--toys", "100", "--seed", "1"])
            self.assertEqual(code, 0)
            code, art = self.write(tmp, cli)
            sig = art["extension"]["significance"]
            self.assertNotIn("local_p", sig)
            self.assertEqual((sig["local_p_bound"]["kind"], sig["local_p_bound"]["k"], sig["local_p_bound"]["n"]), ("upper", 0, 100))
            self.assertAlmostEqual(sig["local_p_bound"]["value"], 1 - 0.05 ** 0.01, places=12)
            self.assertTrue(validate_artifact(art).ok)

    def test_rejected_cli_output_writes_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            code, art = self.write(tmp, {"status": "rejected", "error": "x"})
            self.assertEqual((code, art), (2, None))


if __name__ == "__main__":
    unittest.main()
