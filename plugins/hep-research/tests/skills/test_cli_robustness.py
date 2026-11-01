"""Every script under skills/*/scripts/ and adapters/*/assets/ behaves as a command-line tool (T12).

1. `python3 -I SCRIPT --help` exits 0 without a traceback, even when an optional dependency (pyhf, uproot, ROOT,
   torch) is missing: -I drops the script's folder and the working directory from sys.path, so a script must find
   its siblings itself and import optional packages only when it runs.
2. Pointed at a missing input file, a script exits non-zero with a short message and no traceback. A missing
   optional dependency may be reported first; that is also a short message.
The table below names, for every script, the arguments that point it at a missing file, or why it reads none. A new
script without an entry fails the inventory test.
3. hep-computing scripts (HC_CONTRACT, HC_SHELL; CMP-12): a missing input, a refused target and an unwritable output
   each give one JSON object with a "status" key and the exit code SKILL.md invariant 5 documents; the .sh scripts are
   run too. A new hep-computing script needs an entry there or in HC_EXEMPT.
"""
import contextlib
import glob
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MISSING_BASE = "/nonexistent/hep-research-cli-check"
M = MISSING_BASE + "/input.json"
OUT = MISSING_BASE + "/out"


@contextlib.contextmanager
def unique_missing(args):
    """args with MISSING_BASE replaced by a base only this call uses, removed afterwards: a tool may create its --out
    folder, and root may create /nonexistent (the optional ROOT job runs as root), so a folder one call made must not
    make another call's input exist (extract_names.py then scanned an empty --root: exit 3, not 2)."""
    base = f"{MISSING_BASE}-{uuid.uuid4().hex}"
    try:
        yield [a.replace(MISSING_BASE, base) for a in args]
    finally:
        shutil.rmtree(base, ignore_errors=True)

MISSING_FILE_ARGS = {
    "skills/hep-review/scripts/review.py": [["verify-export", M], ["r0", "--bundle", M]],
    "skills/hep-theory/scripts/transport_conventions.py": ["diffusion", "--input", M],
    "skills/hep-theory/scripts/bartels_rotation.py": ["average", "--series", M, "--date-column", "date",
                                                      "--value-column", "v", "--rotation", "2426",
                                                      "--lag-days", "0", "--min-coverage", "0.5"],
    "skills/hep-computing/scripts/extract_names.py": ["--surface", "N1", "--root", "/nonexistent/hep-research-cli-check",
                                                      "--out", OUT],
    "skills/hep-authoring/scripts/extract_names.py": ["--surface", "N14", "--root", "/nonexistent/hep-research-cli-check",
                                                      "--out", OUT],
    "skills/hep-citations/scripts/extract_names.py": ["--surface", "N17", "--root", "/nonexistent/hep-research-cli-check",
                                                      "--out", OUT],
    "skills/hep-detector/scripts/extract_names.py": ["--surface", "N11", "--root", "/nonexistent/hep-research-cli-check",
                                                     "--out", OUT],
    "skills/hep-measurement/scripts/extract_names.py": ["--surface", "N9", "--root", "/nonexistent/hep-research-cli-check",
                                                        "--out", OUT],
    "skills/hep-ml/scripts/extract_names.py": ["--surface", "N12", "--root", "/nonexistent/hep-research-cli-check",
                                               "--out", OUT],
    "skills/hep-statistics/scripts/extract_names.py": ["--surface", "N10", "--root", "/nonexistent/hep-research-cli-check",
                                                       "--out", OUT],
    "skills/hep-theory/scripts/extract_names.py": ["--surface", "N13", "--root", "/nonexistent/hep-research-cli-check",
                                                   "--out", OUT],
    "skills/hep-detector/scripts/charge_confusion_rate.py": ["template", "--input", M],
    "skills/hep-detector/scripts/evaluate_design.py": ["report", "--artifacts", M],
    "skills/hep-detector/scripts/design_estimates.py": ["precision-from-result", "--result", M],
    "skills/hep-detector/scripts/species_response.py": ["assemble", "--manifest", M],
    "skills/hep-detector/scripts/survival_feeddown.py": ["compute", "--layers", M, "--species", M, "--xs", M],
    "skills/hep-detector/scripts/detector_atlas.py": ["audit", M],
    "skills/hep-detector/scripts/build_response.py": ["build", M, "--truth-col", "t", "--reco-col", "r", "--unweighted",
                                                       "--all-selected", "--truth-edges", "0", "1", "--reco-edges", "0",
                                                       "1", "--variable", "x", "--unit", "GeV", "--normalization",
                                                       "conditional_on_selected", "--acceptance", "outside_matrix",
                                                       "--residual", "difference", "--intended-use", "forward_folding",
                                                       "--artifact-id", "a", "--objective", "o", "--out", OUT],
    "skills/hep-detector/scripts/calorimeter_resolution.py": ["--fit", M],
    "skills/hep-detector/scripts/tag_and_probe_efficiency.py": ["--probes", M, "--pass-column", "p"],
    "skills/hep-detector/scripts/frontend_response.py": [["hit-efficiency", "--thresholds", "1", "--noise", "1",
                                                           "--signal-model", "table", "--spectrum", M],
                                                          ["optimal-filter", "--peaking", "25", "--period", "25",
                                                           "--samples", "5", "--first-offset", "-50",
                                                           "--noise-covariance", M],
                                                          ["waveform-toy", "--peaking", "25", "--period", "25",
                                                           "--samples", "5", "--first-offset", "-50", "--amplitude",
                                                           "10", "--noise-covariance", M],
                                                          ["s-curve", "--scan-file", M]],
    "skills/hep-measurement/scripts/isotope_fraction.py": ["fit", "--config", M, "--data", M, "--seed", "1"],
    "skills/hep-measurement/scripts/collection_time.py": ["accumulate", "--config", M, M],
    "skills/hep-measurement/scripts/acceptance_from_generation.py": ["--config", M, "--events", M],
    "skills/hep-measurement/scripts/anisotropy.py": ["harmonic", "--events", M],
    "skills/hep-measurement/scripts/solar_modulation_force_field.py": ["--modulate", "--energy", "1", "--mass", "0.938",
                                                                     "--charge", "1", "--phi", "0.5", "--lis-table", M],
    "skills/hep-detector/scripts/mix_period_responses.py": ["stack", "--period", f"e1={M}", "--out", OUT],
    "skills/hep-detector/scripts/multiple_scattering.py": [M],
    "skills/hep-detector/scripts/pileup_reweight.py": [M],
    "skills/hep-detector/scripts/multisample_pid.py": ["charge", M, "--layers", "a", "--response", M, "--method",
                                                      "truncated-mean", "--truncate-high", "0.2", "--no-path-correction"],
    "skills/hep-detector/scripts/stability_monitor.py": [M, "--time-column", "t", "--value-column", "v", "--sigma", "1",
                                                        "--false-alarm", "0.05", "--seed", "1"],
    "skills/hep-detector/scripts/propagate_scale_distortion.py": ["response", M, "--mode", "scale", "--scale", "0.01"],
    "skills/hep-detector/scripts/toy_spectrometer.py": ["generate", M, "--seed", "1", "--events-out", OUT, "--periods-out", OUT + "p"],
    "skills/hep-measurement/scripts/check_systematic_variations.py": ["--json", M],
    "skills/hep-measurement/scripts/cr_spectrum_powerlaw_fit.py": ["--input", M],
    "skills/hep-measurement/scripts/make_yield_table.py": ["--input", M, "--status", "synthetic"],
    "skills/hep-measurement/scripts/mask_blinded_bins.py": ["--hist", M, "--low", "1", "--high", "2"],
    "skills/hep-measurement/scripts/review_analysis_change.py": [M],
    "skills/hep-measurement/scripts/review_measurement_spec.py": [M],
    "skills/hep-measurement/scripts/spectrum_transform.py": [M, "--to", "rigidity"],
    "skills/hep-measurement/scripts/systematics_table_tex.py": ["--input", M, "--status", "synthetic"],
    "skills/hep-computing/scripts/audit_blinded_outputs.py": ["scan", "--sealed", M, "/tmp"],
    "skills/hep-computing/scripts/audit_histograms.py": [M],
    "skills/hep-computing/scripts/compare_root_histograms.py": ["--reference", M, "--candidate", M, "--hist", "h"],
    "skills/hep-computing/scripts/environment_manifest.py": ["check", "--manifest", M],
    "skills/hep-computing/scripts/inspect_root_file.py": ["--input", M],
    "skills/hep-computing/scripts/lint_task.py": [M],
    "skills/hep-computing/scripts/local_partition.py": ["status", "--manifest", M, "--state", OUT],
    "skills/hep-computing/scripts/run_workflow.py": [M, "--work", OUT],
    "skills/hep-computing/scripts/check_definitions.py": [["validate-freeze", M], ["decide", M], ["verify-chain", M]],
    "skills/hep-computing/scripts/control_layer.py": [["status", "--task-log", M],
                                                      ["contract", "--task-log", M, "--file", M, "--expect-head", "0"],
                                                      ["receipt", "--task-log", M, "--receipt", M, "--work", M,
                                                       "--expect-head", "0"],
                                                      ["resume", "--task-log", M],
                                                      ["reconcile", "--task-log", M, "--receipt", M, "--work", M,
                                                       "--expect-head", "0"]],
    "skills/hep-computing/scripts/executor_capabilities.py": [["declare", "--qualification", M, "--out", OUT],
                                                              ["admit", "--declaration", M, "--qualification", M,
                                                               "--require", "G1"]],
    "skills/hep-computing/scripts/roofit_workspace_summary.py": ["--input", M, "--workspace", "w"],
    "skills/hep-computing/scripts/summarize_histogram_statistics.py": ["--input", M, "--hist", "h"],
    "skills/hep-computing/scripts/validate_agile_notes.py": [M],
    "skills/hep-statistics/scripts/bayes_calibration.py": ["check-quantiles", "--input", M],
    "skills/hep-statistics/scripts/roofit_fit_check.py": ["result", "--file", M, "--name", "r", "--edm-max", "1e-3"],
    "skills/hep-statistics/scripts/bayes_diagnostics.py": ["diagnose", "--input", M],
    "skills/hep-statistics/scripts/covariance_fit.py": ["fit", "--input", M],
    "skills/hep-statistics/scripts/propagation_fit.py": ["fit", "--input", M, "--provider-registry", M],
    "skills/hep-statistics/scripts/eft_scan.py": ["scan", "--input", M],
    "skills/hep-statistics/scripts/global_significance.py": ["run", "--input", M, "--seed", "1"],
    "skills/hep-statistics/scripts/sweighted_fit.py": ["fit", "--input", M],
    "skills/hep-statistics/scripts/combine_asymmetric.py": ["measurements", "--input", M],
    "skills/hep-statistics/scripts/combine_measurements.py": [M],
    "skills/hep-statistics/scripts/split_consistency.py": ["--input", M],
    "skills/hep-statistics/scripts/build_covariance.py": ["build", "--input", M],
    "skills/hep-statistics/scripts/periodicity_scan.py": ["--input", M, "--null", "white", "--surrogates", "10", "--seed", "1"],
    "skills/hep-statistics/scripts/time_structure.py": ["lag", "--input", M, "--max-lag", "2", "--surrogates", "5", "--seed", "1"],
    "skills/hep-statistics/scripts/project_uncertainty.py": [M, "--k", "2"],
    "skills/hep-statistics/scripts/tail_extrapolation.py": ["--input", M],
    "skills/hep-statistics/scripts/result_artifact.py": ["--cli-output", M, "--poi", "mu", "--construction", "asymptotic",
                                                         "--test-statistic", "q", "--label", "synthetic", "--artifact-id",
                                                         "x", "--out", OUT],
    "skills/hep-statistics/scripts/pdf_reweighting.py": [M, "--weights", "nnpdf", "--min-replicas", "2"],
    "skills/hep-statistics/scripts/hessian_profiling.py": [M],
    "skills/hep-statistics/scripts/look_elsewhere.py": ["brute", "--input", M, "--seed", "1"],
    "skills/hep-statistics/scripts/sensitivity_and_gof.py": ["gof", "--input", M, "--seed", "1"],
    "skills/hep-theory/scripts/eft_truncation.py": [M],
    "skills/hep-theory/scripts/event_weights.py": [M],
    "skills/hep-theory/scripts/pdf_uncertainty.py": [M],
    "skills/hep-theory/scripts/structure_functions_lo.py": [
        "--x", "0.1", "--Q2", "10", "--s", "1000", "--M", "0.938", "--lepton", "e-", "--polarization", "0",
        "--bosons", "gamma", "--sf-signs", "pdg", "--alpha", "0.0073", "--alpha-label", "a", "--target", "p",
        "--target-normalization", "per-nucleon", "--target-mass-treatment", "neglected",
        "--heavy-quark-scheme", "ZM-VFNS", "--partons", M],
    "skills/hep-theory/scripts/sum_rules.py": ["--table", M, "--rule", "momentum"],
    "skills/hep-theory/scripts/nuclear_combination.py": ["ratio", "--input", M],
    "skills/hep-theory/scripts/tmd_gaussian.py": ["sidis", "--x", "0.1", "--z", "0.4", "--kperp2", "0.5",
                                                  "--pperp2", "0.1", "--PhT", "0.5", "--partons", M],
    "skills/hep-theory/scripts/drell_yan_lo.py": ["xsec", "--sqrt-s", "38.8", "--rapidity-frame", "cm", "--M", "5",
                                                  "--y", "0", "--alpha", "0.0073", "--alpha-label", "a",
                                                  "--bosons", "gamma", "--partons", M],
    "skills/hep-theory/scripts/physical_data.py": ["nuclide", "4He", "--ame", M],
    "skills/hep-theory/scripts/import_published_table.py": ["--table", M, "--spec", M, "--out", M],
    "skills/hep-theory/scripts/coalescence.py": ["yield", "--spectrum", M, "--mass-number", "2", "--b-a", "0.004"],
    "skills/hep-theory/scripts/secondary_gamma.py": ["pi0", "--spectrum", M, "--e-gamma-gev", "1"],
    "skills/hep-computing/scripts/check_histogram_errors.py": [M],
    "skills/hep-authoring/scripts/render_results.py": ["--quantity", f"Mu={M}:a:b", "--out", OUT],
    "skills/hep-ml/scripts/check_split_integrity.py": [M],
    "skills/hep-ml/scripts/check_surrogate_domain.py": [M],
    "skills/hep-ml/scripts/compare_model_runs.py": [M],
    "skills/hep-ml/scripts/export_bdt.py": [M, "--to", "ubj", "--out", OUT],
    "skills/hep-ml/scripts/estimate_training_memory.py": [M, "--json"],
    "skills/hep-ml/scripts/domain_shift_report.py": ["--reference", M, "--target", M, "--features", "x", "--control-sample", "c"],
    "skills/hep-ml/scripts/inspect_checkpoint.py": [M],
    "skills/hep-ml/scripts/make_grouped_splits.py": [M, "--id-column", "id", "--group-column", "g", "--out", OUT],
    "skills/hep-ml/scripts/train_bdt.py": ["--data", M, "--config", M, "--negative-weights", "drop", "--out-dir", OUT],
    "skills/hep-ml/scripts/write_ml_artifact.py": ["--run-summary", M, "--out", OUT],
    "skills/hep-ml/scripts/train_emulator.py": [["train", "--training-set", M, "--out-dir", OUT],
                                                ["predict", "--model", M, "--points", M]],
    "skills/hep-authoring/scripts/audit_claims.py": [M, "--project-root", "/tmp"],
    "skills/hep-citations/scripts/build_lit_matrix.py": [M],
    "skills/hep-authoring/scripts/spectrum_plot.py": ["--record", M, "--bin-position", "center", "--out", OUT + ".png"],
    "skills/hep-authoring/scripts/check_adaptation.py": [M, "--project-root", "/tmp", "--responses"],
    "skills/hep-authoring/scripts/check_communication.py": [M, "--project-root", "/tmp"],
    "skills/hep-authoring/scripts/check_diagram_sources.py": [M],
    "skills/hep-authoring/scripts/check_manuscript.py": [M],
    "skills/hep-authoring/scripts/check_citations.py": [M],
    "skills/hep-authoring/scripts/review.py": ["start", M],
    "skills/hep-authoring/scripts/check_terminology.py": [M, "--project-root", "/tmp", "--glossary", M],
    "skills/hep-citations/scripts/manage_literature.py": ["import", M, "--project-root", "/tmp", "--out", OUT],
    "skills/hep-authoring/scripts/track_revision_impact.py": [M, M, "--project-root", "/tmp"],
    "adapters/cr-propagation/assets/dragon2_run.py": ["--spec", M, "--out", OUT, "--prepare-only"],
    "adapters/cr-propagation/assets/dragon2_provider.py": ["--request", M, "--response", OUT],
    "adapters/cr-propagation/assets/dragon2_to_prediction.py": ["--txt", M, "--numerator", "NUC_5011", "--denominator",
                                                                "NUC_6012", "--edges", "10,100", "--level", "x",
                                                                "--param", "D0=1", "--out", OUT],
    "adapters/cr-propagation/assets/usine_translate.py": ["translate", "--transport", M, "--name", "r", "--out", OUT,
                                                          "--ekn-range", "1,10", "--data-dir", "/tmp"],
    "adapters/cr-propagation/assets/usine_to_prediction.py": ["--run-dir", M, "--observable", "B/C", "--axis", "ekn",
                                                              "--edges", "1,10"],
    "adapters/cr-propagation/assets/usine_provider.py": ["--request", M, "--response", OUT],
    "adapters/cr-propagation/assets/emulator_provider.py": ["--request", M, "--response", OUT],
    "adapters/crdb/assets/crdb_query.py": ["summarize", M],
    "adapters/unfolding/assets/unfold.py": ["unfold", "--input", M, "--backend", "pyunfold", "--iterations", "3"],
    "adapters/geomagnetic-backtracing/assets/otso_cutoff.py": ["dipole-check", "--replay", M],
    "adapters/detector-simulation/assets/detsim.py": ["--backend", "allpix-squared", "check", "--workspace",
                                                      MISSING_BASE, "--task", M],
    "adapters/geant4/assets/geant4_build.py": ["check", "--record", M],
    "adapters/geant4/assets/geant4_examples.py": ["extract", "--example", "B1", "--out-file", M],
    "adapters/geant4/assets/geant4_run.py": [["run", "--spec", M, "--exe", M, "--build-record", M, "--work", OUT,
                                              "--run-id", "r", "--record", OUT], ["check-spec", "--spec", M],
                                             ["from-geometry", "--geometry", M, "--profile", M, "--out", OUT],
                                             ["reco", "--run-record", M, "--reco-spec", M, "--simreco", M,
                                              "--work-out", OUT, "--reco-id", "r", "--record", OUT],
                                             ["table", "--reco-record", M, "--figure-of-merit",
                                              "momentum-resolution-core", "--observable", "core", "--out", OUT,
                                              "--id", "t"]],
    "adapters/geant4/assets/geant4_verify.py": ["balance", "--run-record", M, "--tolerance-mev", "0.001"],
    "adapters/geant4/assets/summary_from_csv.py": ["--csv", M, "--observables", M, "--block-size", "10", "--blocks",
                                                   "16", "--run-record", M, "--out", OUT],
    "skills/hep-detector/scripts/check_geant4_study.py": ["spec", "--spec", M],
    "skills/hep-detector/scripts/geant4_benchmarks.py": ["run", "--config", M],
    "adapters/hepdata/assets/hepdata_export.py": ["--artifact", M, "--out", OUT],
    "adapters/hepdata/assets/hepdata_record.py": ["--table", M, "--observable", M, "--record", "r", "--table-name", "t",
                                                  "--out", OUT],
    "adapters/literature-lookup/assets/literature_lookup.py": ["arxiv:1007.1727", "--replay", M],
    "adapters/pyhf-combine/assets/backend_comparison.py": ["--model", M],
    "adapters/pyhf-combine/assets/model_card.py": ["--card", M],
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
    "skills/hep-detector/scripts/cherenkov_angle.py": "numbers on the command line",
    "skills/hep-detector/scripts/pid_separation_power.py": "numbers on the command line",
    "skills/hep-detector/scripts/tracker_resolution.py": "numbers on the command line",
    "skills/hep-detector/scripts/xmax_gaisser_hillas.py": "numbers on the command line",
    "skills/hep-measurement/scripts/cosmic_ray_flux.py": "numbers on the command line",
    "skills/hep-measurement/scripts/counting_reference.py": "counts on the command line",
    "skills/hep-measurement/scripts/geomagnetic_cutoff.py": "numbers on the command line",
    "skills/hep-measurement/scripts/orbit_averaged_geomagnetic_cutoff.py": "numbers on the command line",
    "skills/hep-measurement/scripts/particle_ratio_with_uncertainty.py": "numbers on the command line",
    "skills/hep-computing/scripts/create_story_card.py": "text on the command line",
    "skills/hep-computing/scripts/find_python.py": "interpreter paths and package names on the command line",
    "skills/hep-computing/scripts/make_synthetic_nanoaod.py": "writes a file, reads none",
    "skills/hep-statistics/scripts/degeneracy.py": "a built-in synthetic study (scan points and threshold on the command line)",
    "skills/hep-statistics/scripts/discrete_profile.py": "a built-in synthetic study (toys and seed on the command line)",
    "skills/hep-statistics/scripts/li_ma_significance.py": "counts on the command line",
    "skills/hep-statistics/scripts/pcl_efficiency_ratio.py": "numbers on the command line",
    "skills/hep-statistics/scripts/ratio_estimation.py": "a built-in synthetic model (parameters on the command line)",
    "skills/hep-theory/scripts/dis_kinematics.py": "numbers on the command line",
    "skills/hep-theory/scripts/kinematics.py": "numbers and particle names on the command line",
    "skills/hep-theory/scripts/neutrino_oscillation.py": "numbers on the command line",
    "skills/hep-theory/scripts/running_coupling.py": "numbers on the command line",
    "skills/hep-theory/scripts/decay_chain.py": "numbers and nuclide names on the command line",
    "skills/hep-theory/scripts/lepton_energy_losses.py": "numbers on the command line",
    "skills/hep-theory/scripts/sidis_kinematics.py": "numbers on the command line",
    "skills/hep-theory/scripts/dipole_lo.py": "numbers on the command line",
    "skills/hep-theory/scripts/exclusive_kinematics.py": "numbers on the command line",
    "skills/hep-theory/scripts/dm_direct_rate.py": "numbers on the command line",
    "skills/hep-ml/scripts/benchmark_model.py": "a synthetic model, no input",
    "skills/hep-ml/scripts/check_dataset_contract.py": "a synthetic dataset, no input",
    "skills/hep-ml/scripts/check_pytorch_env.py": "inspects the environment",
    "skills/hep-ml/scripts/estimate_compute_budget.py": "numbers on the command line",
    "skills/hep-ml/scripts/find_nan_batches.py": "a synthetic dataset, no input",
    "skills/hep-ml/scripts/profile_dataloader.py": "a synthetic dataset, no input",
    "skills/hep-ml/scripts/serving_capacity.py": "numbers on the command line",
    "adapters/geant4/assets/g4common.py": "shared helpers of the geant4 adapter scripts; only --help",
    "adapters/detector-simulation/assets/detsim_canonical.py": "shared-layer module of detsim.py; only --help",
    "adapters/detector-simulation/assets/detsim_profile.py": "shared-layer module of detsim.py; only --help",
    "adapters/detector-simulation/assets/detsim_schemas.py": "shared-layer module of detsim.py; only --help",
    "adapters/detector-simulation/assets/detsim_plan.py": "shared-layer module of detsim.py; only --help",
    "adapters/detector-simulation/assets/detsim_platform.py": "shared-layer module of detsim.py; only --help",
    "adapters/detector-simulation/assets/detsim_run.py": "shared-layer module of detsim.py; only --help",
    "adapters/detector-simulation/assets/detsim_runner.py": "shared-layer module of detsim.py; only --help",
    "adapters/geant4/assets/element_spec.py": "element_sim spec rules imported by geant4_run.py; only --help",
    "adapters/geant4/assets/simreco_spec.py": "simreco spec rules imported by geant4_run.py; only --help",
    "adapters/cr-propagation/assets/dragon2_translate.py": "source-item rules imported by dragon2_provider.py and the D3 "
                                                           "study; only --help",
}
def argv_sets(entry) -> list[list[str]]:
    """The argv sets of a MISSING_FILE_ARGS entry: one list, or a list of lists (Geant4 program B1.6)."""
    return entry if entry and isinstance(entry[0], list) else [entry]


SCRIPTS = sorted(os.path.relpath(p, ROOT) for p in glob.glob(str(ROOT / "skills/*/scripts/*.py"))
                 + glob.glob(str(ROOT / "adapters/*/assets/*.py")))


def run(script, args, timeout=120):
    with tempfile.TemporaryDirectory() as cwd, unique_missing(args) as args:
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
        for script, entry in sorted(MISSING_FILE_ARGS.items()):
            # an entry is one argv set, or several (a script whose subcommands read different files, Geant4 B1.6)
            for args in argv_sets(entry):
                with self.subTest(script=script, args=args[:1]):
                    res = run(script, args)
                    text = (res.stdout + res.stderr).strip()
                    self.assertNotEqual(res.returncode, 0, text[-400:])
                    self.assertNotIn("Traceback", text)
                    if len(text.splitlines()) > 6:  # a JSON error report may span lines; anything else must be short
                        json.loads(res.stdout)


HC = "skills/hep-computing/scripts/"
# hep-computing script contract (SKILL.md invariant 5, CMP-08/12): (arguments, documented exit code). Every case must
# print one JSON object with a "status" key on stdout and no traceback. {OUT} is an output path under a regular file,
# so it cannot be created on any system (also as root); {HIST} is a valid synthetic histogram.
HC_CONTRACT = {
    "audit_blinded_outputs.py": [(["scan", "--sealed", M, "{TMP}"], 2),
                                 (["seal", "--hist", "{HIST}", "--low", "1", "--high", "2", "--out", "{OUT}"], 2)],
    "audit_histograms.py": [([M], 2)],
    "check_definitions.py": [(["validate-freeze", M], 2), (["decide", M], 2), (["verify-chain", M], 2)],
    "check_histogram_errors.py": [([M], 2)],
    "control_layer.py": [(["status", "--task-log", M], 2),
                         (["contract", "--task-log", M, "--file", M, "--expect-head", "0"], 2),
                         (["init", "--task-log", "{OUT}"], 2),
                         (["resume", "--task-log", M], 2),
                         (["lock", "acquire", "--task-log", M, "--owner", "s1"], 2)],
    "executor_capabilities.py": [(["declare", "--qualification", M, "--out", "{OUT}"], 2),
                                 (["admit", "--declaration", M, "--qualification", M, "--mode", "M1"], 2)],
    "compare_root_histograms.py": [(["--reference", M, "--candidate", M, "--hist", "h"], 2)],
    "create_story_card.py": [(["--actor", "a", "--capability", "c", "--outcome", "o", "--output", "{OUT}", "--json"], 2)],
    "environment_manifest.py": [(["check", "--manifest", M], 2), (["record", "--packages", "pip", "--out", "{OUT}"], 2)],
    "extract_names.py": [(["--surface", "N1", "--root", M, "--out", "{OUT}"], 2),
                         (["--surface", "N9", "--root", "{TMP}", "--out", "{OUT}"], 2),
                         (["--surface", "N1", "--root", "{TMP}", "--out", "{OUT}"], 2)],
    "find_python.py": [(["--require", "surely_not_a_module_xyz", "--python", "/nonexistent/python"], 1)],
    "inspect_root_file.py": [(["--input", M, "--json"], 2)],
    "lint_task.py": [([M, "--json"], 2)],
    "local_partition.py": [(["status", "--manifest", M, "--state", "{TMP}"], 2),
                           (["plan", "--job", "j", "--items", "4", "--chunk-size", "2", "--seed", "1", "--out", "{OUT}"], 2)],
    "make_synthetic_nanoaod.py": [(["--out", "{OUT}", "--events", "5"], None)],  # 2, or 3 without numpy/awkward/uproot
    "roofit_workspace_summary.py": [(["--input", M, "--workspace", "w", "--json"], 2)],
    "run_workflow.py": [([M, "--work", "{TMP}"], 2),
                        ([str(ROOT / "skills/hep-computing/assets/workflow/workflow.json"), "--work", "{OUT}"], 2)],
    "summarize_histogram_statistics.py": [(["--input", M, "--hist", "h", "--json"], 2)],
    "validate_agile_notes.py": [([M, "--json"], 2)],
}
HC_SHELL = {  # bash scripts: (arguments, PATH override or None, documented exit code)
    "new_root_cpp_project.sh": [(["--json", "bad name"], None, 2), (["--json", "--dir", "{FULL}", "demo"], None, 2)],
    "check_root_cpp_env.sh": [(["--json"], "/usr/bin:/bin", 3)],
}
HC_EXEMPT = {"inspect_root_file.C": "ROOT macro, runs inside ROOT and prints text (SKILL.md invariant 5)"}


class HepComputingScriptContractTests(unittest.TestCase):
    """CMP-12: the hep-computing scripts print a JSON status and use the documented exit codes, also on an
    unwritable output (four scripts gave a traceback there on c1d375c)."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        d = Path(self.tmp.name)
        (d / "blocker").write_text("a regular file, so nothing can be created under it\n")
        (d / "hist.json").write_text(json.dumps({"edges": [0, 1, 2, 3], "values": [5, 6, 7]}))
        (d / "full").mkdir()
        (d / "full" / "keep.txt").write_text("x")
        self.subst = {"{OUT}": str(d / "blocker" / "out" / "x.json"), "{HIST}": str(d / "hist.json"), "{TMP}": str(d),
                      "{FULL}": str(d / "full")}

    def args(self, args):
        return [self.subst.get(a, a) for a in args]

    def check(self, label, res, code):
        self.assertNotIn("Traceback", res.stdout + res.stderr, label)
        try:
            doc = json.loads(res.stdout)
        except ValueError:
            self.fail(f"{label}: stdout is not one JSON object: {res.stdout[-300:]!r} {res.stderr[-300:]!r}")
        self.assertIsInstance(doc, dict, label)
        self.assertIn("status", doc, label)
        if code is None:
            self.assertIn(res.returncode, (2, 3), label)
        else:
            self.assertEqual(res.returncode, code, f"{label}: {res.stdout[-300:]} {res.stderr[-300:]}")

    def test_every_script_is_covered_or_exempt(self):
        names = {Path(p).name for p in glob.glob(str(ROOT / HC / "*")) if Path(p).is_file()}
        self.assertEqual(sorted(names - set(HC_CONTRACT) - set(HC_SHELL) - set(HC_EXEMPT)), [])
        self.assertEqual(sorted((set(HC_CONTRACT) | set(HC_SHELL) | set(HC_EXEMPT)) - names), [])

    def test_python_scripts_print_a_json_status_with_the_documented_exit(self):
        for script, cases in sorted(HC_CONTRACT.items()):
            for args, code in cases:
                with self.subTest(script=script, args=args):
                    self.check(f"{script} {args}", run(HC + script, self.args(args), timeout=300), code)

    @unittest.skipUnless(os.path.exists("/bin/bash"), "bash not available")
    def test_shell_scripts_print_a_json_status_with_the_documented_exit(self):
        for script, cases in sorted(HC_SHELL.items()):
            for args, path, code in cases:
                with self.subTest(script=script, args=args):
                    env = dict(os.environ, PATH=path) if path else None
                    with tempfile.TemporaryDirectory() as cwd:
                        res = subprocess.run(["/bin/bash", str(ROOT / HC / script), *self.args(args)], capture_output=True,
                                             text=True, timeout=300, cwd=cwd, env=env)
                    self.check(f"{script} {args}", res, code)


if __name__ == "__main__":
    unittest.main()
