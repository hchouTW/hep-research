"""F-15: every statement about a script's output behavior in the capability-matrix rows and entry references of
hep-statistics and hep-detector has one assertion test.

CLAIMS ties each statement to the test that asserts it: the quoted text must still be in the document, and the test
must exist (it runs in its own module). A statement whose test is missing, or a test whose statement was edited away,
fails here. Statements that had no test get one below (GeneralMethodLabel). The other skills' statements are listed as
a follow-up in the batch 0a pull request.

Before F-03 the Li & Ma claim ("carries `status` and `method_kind: asymptotic`") had no true test: the script printed
neither, so the registry's test fails on the parent of F-03.
"""
import importlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

MATRIX = "docs/capability-matrix.md"
GUIDE = "skills/hep-statistics/references/core-stats-guide.md"
T = "tests.skills.test_documented_output_claims"

# (document, quoted statement, test id)
CLAIMS = [
    # hep-statistics entry reference (core/stats guide)
    (GUIDE, "output is JSON labeled `[General method]`", f"{T}.GeneralMethodLabel.test_computing_modules_label_their_output"),
    (GUIDE, "output is JSON labeled `[General method]`", f"{T}.GeneralMethodLabel.test_validators_label_their_output"),
    (GUIDE, "Every toy-based subcommand requires `--seed` and echoes it",
     "tests.core.test_stats_likelihood_limits.CliTests.test_subcommands_ok_and_seed_echoed"),
    (GUIDE, "Every toy-based subcommand requires `--seed` and echoes it",
     "tests.core.test_stats_statistical_toys.CliTests.test_each_subcommand_ok_and_echoes_seed"),
    (GUIDE, "Every toy-based subcommand requires `--seed` and echoes it",
     "tests.core.test_stats_poisson.CliTests.test_coverage_requires_a_seed"),
    (GUIDE, "Exit codes** (per module, from each module's docstring)",
     "tests.skills.hep_statistics.test_core_stats_guide.CoreStatsGuide.test_exit_codes_match_module_docstrings"),
    (GUIDE, "A limit that cannot be bracketed below the Poisson mean cap is reported `failed`, never clipped",
     "tests.core.test_stats_poisson.MeanLimitTests.test_unbracketed_limit_fails_instead_of_returning_the_range_end"),
    (GUIDE, "`incomplete` (exit 3) when only toy fits failed",
     "tests.core.test_stats_p0_regressions.ReviewFindings.test_only_toy_failures_give_incomplete_and_exit_3"),
    (GUIDE, "fit `failed` (infeasible model or no convergence)",
     "tests.core.test_stats_template_fit.FitStatusAuditT03.test_failed_fit_cli_fails_with_nonzero_exit"),
    (GUIDE, "at k = 0 a one-sided 95% upper bound `1 - 0.05^(1/N)`",
     "tests.core.test_stats_p0_regressions.T02T03ToyTails.test_zero_exceedances_give_a_bound_not_a_zero"),
    (GUIDE, "it refuses `dagostini`",
     "tests.skills.hep_statistics.test_core_stats_guide.RoutedCommandsRun.test_regularized_scan_refuses_dagostini"),
    (GUIDE, "marked ones refuse to run without NumPy (and SciPy) with exit 2 and a JSON message",
     "tests.skills.hep_statistics.test_core_stats_guide.DependencyMarkers.test_markers_match_imports"),
    (GUIDE, "every script prints `--help` without them",
     "tests.skills.hep_statistics.test_cli_input_fuzz.CliInputFuzz.test_help_without_numpy"),
    # hep-statistics capability-matrix rows
    (MATRIX, "the output carries `status` and `method_kind: asymptotic`",
     "tests.skills.hep_statistics.test_li_ma_significance.PValues.test_status_and_asymptotic_label_at_low_counts"),
    (MATRIX, "R-hat, bulk/tail ESS and quantile MCSE on seeded synthetic chains",
     "tests.skills.hep_statistics.test_bayes_diagnostics.Diagnostics.test_quantile_mcse_reported"),
    (MATRIX, "infeasible or unconverged fits reported failed",
     "tests.core.test_stats_template_fit.FitStatusAuditT03.test_failed_fit_status_propagates_to_artifacts"),
    (MATRIX, "CLI exit 1/3, artifact fit_status",
     "tests.skills.hep_statistics.test_result_artifact.ResultArtifactStatus.test_ok_and_failed_cli_results_map_to_the_artifact"),
    (MATRIX, "k = 0 is a bound, not p = 0",
     "tests.core.test_stats_p0_regressions.T02T03ToyTails.test_zero_exceedances_give_a_bound_not_a_zero"),
    (MATRIX, "plugin (only with `--allow-plugin`, path relative to the input, errors as `failed`: F-09)",
     "tests.skills.hep_statistics.test_covariance_fit.PluginModelF09.test_plugin_needs_the_flag"),
    (MATRIX, "missing data covariance -> exit 3, `incomplete`",
     "tests.skills.hep_statistics.test_grid_fit.GridRefusals.test_missing_covariance_is_incomplete_exit_3"),
    (MATRIX, "give exit 2 with JSON, no traceback",
     "tests.skills.hep_statistics.test_cli_input_fuzz.CliInputFuzz.test_malformed_json_inputs_are_refused"),
    (MATRIX, "`--help` without NumPy/SciPy for every script",
     "tests.skills.hep_statistics.test_cli_input_fuzz.CliInputFuzz.test_help_without_numpy"),
    # hep-detector capability-matrix rows (its entry reference, the principles summary, states no script output)
    (MATRIX, "twenty-three scripts with status labels and JSON errors",
     "tests.skills.hep_detector.test_hep_detector_audit.StatusLabelTests.test_every_script_echoes_status"),
    (MATRIX, "twenty-three scripts with status labels and JSON errors",
     "tests.skills.hep_detector.test_hep_detector_audit.UniformErrorTests.test_invalid_input_is_exit_2_with_a_json_error"),
    (MATRIX, "twenty-three scripts with status labels and JSON errors", f"{T}.DetectorScriptCount.test_script_count"),
]


def _flat(text: str) -> str:
    return " ".join(text.split())


def _resolve(test_id: str):
    module, cls, meth = test_id.rsplit(".", 2)
    return getattr(getattr(importlib.import_module(module), cls), meth)


class Registry(unittest.TestCase):
    def test_every_claim_is_in_its_document(self):
        for doc, quote, test_id in CLAIMS:
            with self.subTest(doc=doc, quote=quote):
                self.assertIn(_flat(quote), _flat((ROOT / doc).read_text(encoding="utf-8")))

    def test_every_claim_has_an_existing_test(self):
        for doc, quote, test_id in CLAIMS:
            with self.subTest(test=test_id):
                self.assertTrue(callable(_resolve(test_id)), test_id)


LABELLED = {"poisson_diagnostics.py": ["upper-limit", "--n", "3", "--b", "1"],
            "likelihood_limits.py": ["profile-limit", "--n", "3", "--b", "1.0", "--sigma-b", "0.1", "--toys", "200",
                                     "--seed", "1"],
            "statistical_toys.py": None, "unfolding_diagnostics.py": None, "template_fit.py": None}


def _run(script, args):
    with tempfile.TemporaryDirectory() as cwd:
        res = subprocess.run([sys.executable, "-I", str(ROOT / "core" / "stats" / script), *args], capture_output=True,
                             text=True, timeout=300, cwd=cwd)
    return res.returncode, json.loads(res.stdout)


class GeneralMethodLabel(unittest.TestCase):
    def test_computing_modules_label_their_output(self):
        for script, args in LABELLED.items():
            with self.subTest(script=script):
                text = (ROOT / "core" / "stats" / script).read_text(encoding="utf-8")
                self.assertIn("[General method]", text)
                if args:
                    code, out = _run(script, args)
                    self.assertEqual(code, 0, out)
                    self.assertEqual(out["label"], "[General method]")

    def test_validators_label_their_output(self):
        """The validators label their CLI output like the other modules (until batch 0b they did not, and the guide
        named them as the exception); a refused input carries the label too."""
        with tempfile.TemporaryDirectory() as td:
            cov = Path(td) / "cov.json"
            cov.write_text(json.dumps({"matrix": [[1.0, 0.0], [0.0, 1.0]]}))
            for script in ("validate_covariance.py", "validate_response.py"):
                with self.subTest(script=script):
                    res = subprocess.run([sys.executable, "-I", str(ROOT / "core" / "stats" / script), str(cov)],
                                         capture_output=True, text=True, timeout=300)
                    out = json.loads(res.stdout)
                    self.assertIn("status", out)
                    self.assertEqual(out["label"], "[General method]")
                    bad = subprocess.run([sys.executable, "-I", str(ROOT / "core" / "stats" / script),
                                          str(Path(td) / "missing.json")], capture_output=True, text=True, timeout=300)
                    self.assertEqual(json.loads(bad.stdout)["label"], "[General method]")


class DetectorScriptCount(unittest.TestCase):
    def test_script_count(self):
        self.assertEqual(len(list((ROOT / "skills" / "hep-detector" / "scripts").glob("*.py"))), 24)


if __name__ == "__main__":
    unittest.main()
