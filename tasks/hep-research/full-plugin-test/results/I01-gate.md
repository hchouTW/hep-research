# I01 gate (E2, 3aa942c)

Check-run: `tasks/hep-research/check-runs/check-run-2026-10-03T134843Z.json`: 12 pass, **1 fail**, 1 skip.
`claude plugin validate --strict .`: pass (exit 0).

| Check | Result |
|---|---|
| unittest | **fail**: 1235 run, 1159 pass, 5 fail, 1 error, 70 skip |
| profile suites (ams-02 258, synthetic-collider 9, qed-benchmark 16) | pass |
| ams_ledger_preservation | skip: legacy ledger not fetched (`fetch_legacy.sh` not run; out of scope for r2) |
| the other 10 checks | pass |

## Unit failures and their causes

| Test | Result | Cause (diagnosed, not fixed) |
|---|---|---|
| `test_batch_slurm…test_golden_array_script_and_dry_run` | fail | macOS temp dirs are `/var/folders/…`, a symlink to `/private/var/folders/…`; the rendered script holds the resolved path, so the `<CAMPAIGN>` placeholder substitution leaves a `/private` prefix. Platform-specific path normalization |
| `test_batch_htcondor…test_file_transfer_mode_remaps_outputs_and_matches_golden` | fail | same `/private` symlink cause |
| `test_batch_privacy…test_planted_account_fails_the_packaging_check` | fail | the test copies the plugin tree including the untracked `.venv-hep`; the scanner flags e-mail addresses in NumPy license files. **Confirmed**: passes (OK) with the venv outside the plugin tree |
| `test_root_cpp_assets.RootCppAssetTests` (setUpClass) | error | `make_root_fixtures.py` runs `python3` from PATH (miniconda 3.13); `import ROOT` finds Homebrew ROOT 6.38.04, whose PyROOT is built for Python 3.14.4, and fails at `dlopen` instead of raising a clean ImportError, so the test does not skip |
| `test_theory_comparison.PathDTests.test_passes_predeclared_criteria` | fail | criterion `response_matches_path_b` uses exact `np.array_equal` between two computations of the response matrix; false here (arm64, numpy 2.5.3). Other 11 criteria pass |
| `test_theory_comparison.PathDTests.test_reproduces_committed_output` | fail | follows from the line above: output hash differs from the committed one |

None of these touches the installable content (skills, profiles, manifest); `validate --strict` passes.
