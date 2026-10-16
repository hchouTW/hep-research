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
            # labelled synthetic: the gate fails it (contracts 2.6.0, gate.not_observed_data); relabelled as observed,
            # coverage was still not checked by this run, so the gate says unresolved, not passed
            self.assertEqual(publication_gate(art)["status"], "failed")
            self.assertEqual(publication_gate({**art, "status": ["observed"]})["status"], "unresolved")

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

    def test_missing_status_needs_an_explicit_assumption(self):
        """STH-T1.7: an output without a status (li_ma_significance.py's before F-03) is not a converged fit."""
        li_ma = {"method": "Li-Ma", "significance": 2.1, "n_on": 30, "n_off": 100, "alpha": 0.1}
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(self.write(tmp, li_ma), (2, None))
            code, art = self.write(tmp, li_ma, "--assume-status", "ok")
            self.assertEqual(code, 0)
            self.assertEqual(art["extension"]["results"]["cli_status_assumed"], "ok")
            self.assertEqual(art["extension"]["fit_status"], "converged")
            code, art = self.write(tmp, li_ma, "--assume-status", "failed")
            self.assertEqual((code, art["extension"]["fit_status"]), (1, "failed"))

    def test_contradictory_coverage_and_non_object_input(self):
        with tempfile.TemporaryDirectory() as tmp:
            ok = {"status": "ok", "cl": 0.95}
            for extra in (["--coverage-value", "0.95"], ["--coverage-n-toys", "100"]):
                with self.subTest(extra=extra):
                    self.assertEqual(self.write(tmp, ok, "--coverage-check", "not-checked", *extra), (2, None))
            self.assertEqual(self.write(tmp, [1, 2, 3]), (2, None))
            code, art = self.write(tmp, ok, "--coverage-check", "toys", "--coverage-n-toys", "500", "--coverage-value", "0.95")
            self.assertEqual(code, 0)


class ResultArtifactParadigm(unittest.TestCase):
    """F-02: an artifact written from an MCMC result has paradigm 'bayesian' with its priors, sampler and convergence
    (before the fix every artifact was written as frequentist). SYNTHETIC chains."""

    def mcmc(self, tmp, chains, *extra):
        import numpy as np
        import bayes_diagnostics as bd
        rng = np.random.default_rng(7)
        draws = rng.normal(1.0, 0.2, size=(4, 1000)) if chains is None else chains
        diag = bd.diagnose({"mu": draws}, (0.05, 0.5, 0.95), 1.01, 100)
        src, smp, out = Path(tmp) / "diag.json", Path(tmp) / "sampler.json", Path(tmp) / "res.json"
        src.write_text(json.dumps(diag))
        smp.write_text(json.dumps({"name": "random-walk Metropolis (synthetic)", "chains": 4, "draws": 1000}))
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = ra.main(["--cli-output", str(src), "--paradigm", "bayesian", "--poi", "mu", "--prior",
                            "mu=uniform(0, 10)", "--sampler", str(smp), "--label", "synthetic",
                            "--artifact-id", "synthetic-f02", "--out", str(out), *extra])
        return code, json.loads(buf.getvalue()), (json.loads(out.read_text()) if out.exists() else None)

    def test_mcmc_result_is_bayesian(self):
        with tempfile.TemporaryDirectory() as tmp:
            code, msg, art = self.mcmc(tmp, None)
            self.assertEqual(code, 0, msg)
            ext = art["extension"]
            self.assertEqual(ext["paradigm"], "bayesian")
            self.assertEqual(ext["priors"], [{"parameter": "mu", "form": "uniform(0, 10)"}])
            self.assertEqual(ext["sampler"]["chains"], 4)
            self.assertLess(ext["convergence"]["rhat"]["mu"], 1.01)
            self.assertEqual(ext["fit_status"], "converged")
            for k in ("construction", "test_statistic", "coverage"):
                self.assertNotIn(k, ext)
            self.assertAlmostEqual(ext["results"]["mu_q0.5"], 1.0, delta=0.05)
            rep = validate_artifact(art)
            self.assertTrue(rep.ok, rep.as_dict())
            self.assertEqual([f for f in rep.as_dict()["findings"] if f["level"] != "info"], [])

    def test_unconverged_chains_are_failed(self):
        import numpy as np
        rng = np.random.default_rng(3)
        stuck = rng.normal(0.0, 0.1, size=(4, 400)) + np.arange(4)[:, None]    # four chains in four places
        with tempfile.TemporaryDirectory() as tmp:
            code, _, art = self.mcmc(tmp, stuck)
            self.assertEqual(code, 1)
            self.assertEqual(art["extension"]["fit_status"], "failed")
            self.assertIn("failed", art["status"])

    def test_bayesian_needs_priors_and_refuses_frequentist_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "diag.json"
            src.write_text(json.dumps({"status": "converged", "parameters": {}}))
            for extra in ([], ["--prior", "mu=uniform(0, 1)", "--construction", "cls"]):
                with self.subTest(extra=extra), redirect_stdout(io.StringIO()):
                    code = ra.main(["--cli-output", str(src), "--paradigm", "bayesian", "--poi", "mu", "--label",
                                    "synthetic", "--artifact-id", "x", "--out", str(Path(tmp) / "o.json"), *extra])
                self.assertEqual(code, 2)
                self.assertFalse((Path(tmp) / "o.json").exists())

    def test_frequentist_is_the_default_and_still_needs_its_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "cli.json"
            src.write_text(json.dumps({"status": "ok", "upper_limit": 3.2}))
            with redirect_stdout(io.StringIO()):
                code = ra.main(["--cli-output", str(src), "--poi", "mu", "--label", "synthetic", "--artifact-id", "x",
                                "--out", str(Path(tmp) / "o.json")])
            self.assertEqual(code, 2)


if __name__ == "__main__":
    unittest.main()
