"""Every script under skills/*/scripts/ and adapters/*/assets/ behaves as a command-line tool (T12).

1. `python3 -I SCRIPT --help` exits 0 without a traceback, even when an optional dependency (pyhf, uproot, ROOT,
   torch) is missing: -I drops the script's folder and the working directory from sys.path, so a script must find
   its siblings itself and import optional packages only when it runs.
2. Pointed at a missing input file, a script exits non-zero with a short message and no traceback. A missing
   optional dependency may be reported first; that is also a short message.
The table below names, for every script, the arguments that point it at a missing file, or why it reads none. A new
script without an entry fails the inventory test.
"""
import glob
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
M = "/nonexistent/hep-research-cli-check/input.json"
OUT = "/nonexistent/hep-research-cli-check/out"

MISSING_FILE_ARGS = {
    "skills/detector-response/scripts/calorimeter_resolution.py": ["--fit", M],
    "skills/detector-response/scripts/multiple_scattering.py": [M],
    "skills/detector-response/scripts/pileup_reweight.py": [M],
    "skills/hep-analysis/scripts/check_systematic_variations.py": ["--json", M],
    "skills/hep-analysis/scripts/cr_spectrum_powerlaw_fit.py": ["--input", M],
    "skills/hep-analysis/scripts/make_yield_table.py": ["--input", M],
    "skills/hep-analysis/scripts/mask_blinded_bins.py": ["--hist", M, "--low", "1", "--high", "2"],
    "skills/hep-analysis/scripts/review_analysis_change.py": [M],
    "skills/hep-analysis/scripts/systematics_table_tex.py": ["--input", M, "--status", "synthetic"],
    "skills/hep-computing/scripts/audit_blinded_outputs.py": ["scan", "--sealed", M, "/tmp"],
    "skills/hep-computing/scripts/audit_histograms.py": [M],
    "skills/hep-computing/scripts/check_example_diversity.py": [M],
    "skills/hep-computing/scripts/compare_root_histograms.py": ["--reference", M, "--candidate", M, "--hist", "h"],
    "skills/hep-computing/scripts/environment_manifest.py": ["check", "--manifest", M],
    "skills/hep-computing/scripts/inspect_root_file.py": ["--input", M],
    "skills/hep-computing/scripts/lint_task.py": [M],
    "skills/hep-computing/scripts/local_partition.py": ["status", "--manifest", M, "--state", OUT],
    "skills/hep-computing/scripts/roofit_workspace_summary.py": ["--input", M, "--workspace", "w"],
    "skills/hep-computing/scripts/summarize_histogram_statistics.py": ["--input", M, "--hist", "h"],
    "skills/hep-computing/scripts/validate_agile_notes.py": [M],
    "skills/hep-computing/scripts/validate_skill_example.py": [M],
    "skills/hep-statistics/scripts/bayes_diagnostics.py": ["diagnose", "--input", M],
    "skills/hep-statistics/scripts/combine_measurements.py": [M],
    "skills/hep-statistics/scripts/look_elsewhere.py": ["brute", "--input", M, "--seed", "1"],
    "skills/hep-statistics/scripts/sensitivity_and_gof.py": ["gof", "--input", M, "--seed", "1"],
    "skills/hep-theory/scripts/eft_truncation.py": [M],
    "skills/hep-theory/scripts/event_weights.py": [M],
    "skills/hep-theory/scripts/pdf_uncertainty.py": [M],
    "skills/physics-ml/scripts/check_split_integrity.py": [M],
    "skills/physics-ml/scripts/check_surrogate_domain.py": [M],
    "skills/physics-ml/scripts/compare_model_runs.py": [M],
    "skills/physics-ml/scripts/inspect_checkpoint.py": [M],
    "skills/research-communication/scripts/build_lit_matrix.py": [M],
    "skills/research-communication/scripts/check_diagram_sources.py": [M],
    "skills/research-communication/scripts/check_manuscript.py": [M],
    "adapters/hepdata/assets/hepdata_export.py": ["--artifact", M, "--out", OUT],
    "adapters/hepdata/assets/hepdata_record.py": ["--table", M, "--observable", M, "--record", "r", "--table-name", "t",
                                                  "--out", OUT],
    "adapters/pyhf-combine/assets/pyhf_nuisance_diagnostics.py": [M],
    "adapters/pyhf-combine/assets/reproduce_published_likelihood.py": ["--bkgonly", M, "--patchset", M, "--published", M,
                                                                       "--out", OUT],
    "adapters/root-uproot/assets/pyroot_rdf_cutflow_analysis.py": ["--input", M, "--output", OUT],
    "adapters/root-uproot/assets/pyroot_roofit_signal_background.py": ["--input", M, "--hist", "h", "--output", OUT,
                                                                      "--min", "0", "--max", "1"],
    "adapters/root-uproot/assets/uproot_awkward_analysis.py": ["--config", M],
    "adapters/root-uproot/assets/coffea_dijet_processor.py": [M],
    "adapters/root-uproot/assets/root_to_parquet.py": ["--input", M, "--out", OUT],
    "adapters/unbinned-fit/assets/unbinned_fit.py": ["fit", "--data", M, "--config", M],
}
NO_INPUT_FILE = {  # script: why the missing-file check does not apply
    "skills/detector-response/scripts/cherenkov_angle.py": "numbers on the command line",
    "skills/detector-response/scripts/pid_separation_power.py": "numbers on the command line",
    "skills/detector-response/scripts/tag_and_probe_efficiency.py": "counts on the command line",
    "skills/detector-response/scripts/xmax_gaisser_hillas.py": "numbers on the command line",
    "skills/hep-analysis/scripts/cosmic_ray_flux.py": "numbers on the command line",
    "skills/hep-analysis/scripts/counting_reference.py": "counts on the command line",
    "skills/hep-analysis/scripts/geomagnetic_cutoff.py": "numbers on the command line",
    "skills/hep-analysis/scripts/orbit_averaged_geomagnetic_cutoff.py": "numbers on the command line",
    "skills/hep-analysis/scripts/particle_ratio_with_uncertainty.py": "numbers on the command line",
    "skills/hep-analysis/scripts/solar_modulation_force_field.py": "numbers on the command line",
    "skills/hep-computing/scripts/create_story_card.py": "text on the command line",
    "skills/hep-computing/scripts/generate_skill_example.py": "text on the command line",
    "skills/hep-computing/scripts/make_synthetic_nanoaod.py": "writes a file, reads none",
    "skills/hep-computing/scripts/validate_skill_bundle.py": "reads the plugin's own files",
    "skills/hep-statistics/scripts/li_ma_significance.py": "counts on the command line",
    "skills/hep-theory/scripts/dis_kinematics.py": "numbers on the command line",
    "skills/physics-ml/scripts/benchmark_model.py": "a synthetic model, no input",
    "skills/physics-ml/scripts/check_dataset_contract.py": "a synthetic dataset, no input",
    "skills/physics-ml/scripts/check_pytorch_env.py": "inspects the environment",
    "skills/physics-ml/scripts/estimate_compute_budget.py": "numbers on the command line",
    "skills/physics-ml/scripts/estimate_training_memory.py": "numbers on the command line",
    "skills/physics-ml/scripts/find_nan_batches.py": "a synthetic dataset, no input",
    "skills/physics-ml/scripts/profile_dataloader.py": "a synthetic dataset, no input",
    "skills/physics-ml/scripts/serving_capacity.py": "numbers on the command line",
}
SCRIPTS = sorted(os.path.relpath(p, ROOT) for p in glob.glob(str(ROOT / "skills/*/scripts/*.py"))
                 + glob.glob(str(ROOT / "adapters/*/assets/*.py")))


def run(script, args, timeout=120):
    with tempfile.TemporaryDirectory() as cwd:
        return subprocess.run([sys.executable, "-I", str(ROOT / script), *args], capture_output=True, text=True,
                              timeout=timeout, cwd=cwd)


class CliRobustnessTests(unittest.TestCase):
    def test_inventory_is_complete(self):
        listed = set(MISSING_FILE_ARGS) | set(NO_INPUT_FILE)
        self.assertEqual(sorted(set(SCRIPTS) - listed), [], "add each new script to MISSING_FILE_ARGS or NO_INPUT_FILE")
        self.assertEqual(sorted(listed - set(SCRIPTS)), [], "remove entries for scripts that no longer exist")
        self.assertFalse(set(MISSING_FILE_ARGS) & set(NO_INPUT_FILE))

    def test_help_under_isolated_mode(self):
        for script in SCRIPTS:
            with self.subTest(script=script):
                res = run(script, ["--help"])
                self.assertNotIn("Traceback", res.stderr)
                self.assertEqual(res.returncode, 0, res.stderr[-400:])
                self.assertTrue(res.stdout.strip())

    def test_missing_input_file_is_a_short_error(self):
        for script, args in sorted(MISSING_FILE_ARGS.items()):
            with self.subTest(script=script):
                res = run(script, args)
                text = (res.stdout + res.stderr).strip()
                self.assertNotEqual(res.returncode, 0, text[-400:])
                self.assertNotIn("Traceback", text)
                if len(text.splitlines()) > 6:  # a JSON error report may span lines; anything else must be short
                    json.loads(res.stdout)


if __name__ == "__main__":
    unittest.main()
