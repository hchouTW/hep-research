# hep-detector front-end electronics: reconstruction, simulation and calibration — evaluation, completed work and next stages

| Field | Value |
|---|---|
| Document type | Evaluation results and implementation specification, for the executing agent, reviewers and maintainers |
| Format | hep-computing task format (`skills/hep-computing/assets/task-template.md`); check with `skills/hep-computing/scripts/lint_task.py` |
| Baseline | hep-research `main` at `bc7b1c18` (plugin 0.38.0) |
| Completed work | Local branch `worktree-frontend-reco-sim`, four commits, not pushed (Background, "Completed work"); FE0 done on branch `worktree-frontend-fe0` from main `d5c8ff24` (0.40.0) |
| Date | 2026-10-25 |
| Language | English (translated from the Traditional Chinese original); file names, commands, fields and identifiers unchanged |
| Execution environment | Every stage runs in its own isolated git worktree (Technical Approach §0); never modify the main checkout or another worktree |
| Review | Addresses every finding of independent review R720d9d2e80 (`skills/hep-authoring/scripts/review.py`, round 1) |

All paths are relative to the plugin root `plugins/hep-research/` unless they start with `.claude/`.

#### How to use this document (executing agent)

1. Read **Background** to learn what is already done. Do not redo it.
2. Find your stage in the **stage map** under Objective and check that its prerequisite is met and its decision gate (if
   any) is open. If not, stop and report.
3. Create your worktree as in **Technical Approach §0**.
4. Do the steps of your stage card (Technical Approach §FE0–§FE5).
5. Meet the Acceptance Criteria with your stage's prefix **and** the "All stages" criteria; run **Validation**.
6. Take formulas, units and sign conventions only from **Repository Context → Conventions and formulas**, never from
   memory.

**Stop and report to the maintainer, without guessing, when:** you reach a [U] item; your stage's decision is not yet
taken; a check fails in a way that FE0-1 does not list as known; or the instructions here conflict with what you find in
the repository.

#### Glossary

| Term | Meaning |
|---|---|
| **[C]** Confirmed | Directly supported by the repo, the user or a source that was read |
| **[I]** Inferred | A conclusion drawn from [C] items |
| **[U]** Unresolved | Unknown; listed in Open Questions; never fill in a value yourself |
| FE0–FE5 | The stages of this document (FE = front-end) |
| Fidelity F1–F4 | The fidelity levels of the hep-detector design workflow; unrelated to FE stages. This document always writes "fidelity F4" |
| R1–R5, S1–S6, C1–C5 | Gap codes of this evaluation (R = reconstruction, S = simulation, C = calibration); see "Evaluation findings" |
| Maintenance class S1–S3 | Evidence classes for `sci-fix:` in `docs/maintenance.md` (S3 = wrong guidance). Not the same as gap codes S1–S3; this document always writes "maintenance class S3" |
| Maintenance levels C1–C4, D1–D3 | Evidence levels in `docs/maintenance.md` (D = mutation evidence) |
| E2 | The maintainer's full environment (with SymPy and mpmath), where full checks run; versions as recorded by the maintainer [U] |
| J15, J16 | Researcher journeys recorded in `examples/design-minimal-spectrometer/` and `examples/design-search-j16/` |
| Front-end reference page | `skills/hep-detector/references/front-end-electronics-and-signal-processing.md` |

## Background

#### Status at a glance

| Area | Before (main `bc7b1c18`) | Now (branch `worktree-frontend-reco-sim`) | Still to do |
|---|---|---|---|
| Analytic relations (ENC, Rice, Campbell, CFD, SiPM, dead time…) | Correct; ten subcommands [C] | Unchanged | — |
| Reconstruction: amplitude and time from sampled waveforms | Text only; no tool reproduced the page's numbers [C] | `optimal-filter` (constraints, time errors) [C] | Measured covariance input (FE2) |
| Reconstruction: threshold efficiency and noise occupancy | Fixed charge, Φ((Q−T)/σ) [C] | `hit-efficiency` (Landau/Gauss, operating window) [C] | Measured charge-spectrum input (FE1) |
| Simulation: digitization and overlay | Five bullet points [C] | New reference `readout-digitization-and-overlay.md` [C] | — |
| Simulation: waveform-level sim→reco | None [C] | `waveform-toy` (AR(1) noise) [C] | Noise from a measured covariance (FE2) |
| Calibration: electronics calibration chain | Seven one-line items [C] | Ordered chain, `s-curve`, `threshold-trim` [C] | Multi-channel batch S-curve (FE3) |
| simreco `noise-digitization` | Parameters decoupled from the electronics [C] | Unchanged [C] | Coupling (FE4, maintainer decision) |
| Full checks | — | See "Completed work" [C] | Full rerun in E2 (FE0) |

#### Evaluation findings

**Correctness.** The original front-end reference page is correct in its analytic relations. Its numbers that no tool
reproduced before were recomputed independently with NumPy/SciPy and agree [C]:

| Case | Recomputed | Printed on the page |
|---|---|---|
| CR-RC, t_p 25 ns, 5 samples every 25 ns from 15 ns before the peak, ρ 0.6: sigma of template / largest sample / optimal filter | 1.117 / 1.066 / 1.037 | 1.12 / 1.07 / 1.04 |
| CR-RC⁴, t_p 45 ns, white noise, 5 samples from one before to three after the peak: phase bias | −0.041 % / −0.333 % (±2 ns); −0.787 % / −1.538 % (±5 ns) | as printed |
| Same pulse, ρ 0.6, two samples before and two after the peak: phase bias | +0.93 % / −1.79 % (∓2 ns); −5.81 % (+5 ns) | as printed |

**Coverage.** The main problem was coverage [C]. Only one item, C4, changes existing guidance; it is maintenance class
S3 (wrong guidance); by decision D-C4 it is its own `sci-fix:` commit (FE0).

| Code | Gap | Handling (done unless marked) |
|---|---|---|
| R1 | Optimal filter: no weights, no pileup-dependent R, no constraints | `optimal-filter` |
| R2 | No time error from sampled waveforms | Fisher errors of a joint amplitude–time fit |
| R3 | Threshold efficiency assumes a fixed charge | `hit-efficiency`: Landau/Gauss, charge fraction, threshold spread, operating window; measured spectrum → **FE1** |
| R4 | Noise occupancy only by the Rice formula | Continuous versus sampled comparison; closed-form average over the threshold spread |
| R5 | ToT inversion, bandwidth, digital pulse processing, PSD not covered | New sections of the reference page |
| S1 | Digitization has no executable order | Nine-step recipe |
| S2 | Noise-generation method not specified | Cholesky / spectral-synthesis rules; the tool has only AR(1) → **FE2** |
| S3 | No overlay/premixing rules | Five rules (citing the HSF white paper) |
| S4 | No digitization closure | Pedestal, S-curve, amplitude, charge sharing, calibration closure |
| S5 | No waveform-level sim→reco tool | `waveform-toy` |
| S6 | simreco `noise-digitization` decoupled from the electronics | **FE4**: `hit-efficiency --simreco-channels` prints its numbers (D-FE4: new options only) |
| C1 | Calibration has no order | Chain: pedestal → noise covariance → gain → thresholds and trim → timing → templates/weights → physics scale |
| C2 | S-curve has no fit method or errors | `s-curve`: binomial ML, Fisher errors, deviance, design mode; multi-channel → **FE3** |
| C3 | Dispersion after trim not quantified | `threshold-trim` |
| C4 | Injection gain treated as signal gain (maintenance class S3) | Rewritten with two section-located sources (References); own `sci-fix:` commit, ledger FRONTEND-INJECTION-GAIN (D-C4) |
| C5 | No calibration closure in simulation | Added in two places of the reference pages |

#### Completed work (branch `worktree-frontend-reco-sim`, base `bc7b1c18`)

| Patch | Commit (as on the branch) | Content |
|---|---|---|
| 0001 | `3fa93a77` feat(detector): front-end electronics for reconstruction and simulation | `optimal-filter`, `hit-efficiency`, `waveform-toy`; six topics on the reference page; new `readout-digitization-and-overlay.md`; cross-links; tool contract 13 operations; `test_frontend_waveforms.py` 26 tests |
| 0002 | `a32df2aa` feat(detector): electronics calibration chain, S-curve fit and threshold trim | `s-curve`, `threshold-trim`; calibration chain rewritten (including C4); calibration closure; tool contract 15 operations; 31 tests in total |
| 0003 | `117b44df` docs(detector): front-end task document, ATLAS LAr and HSF sources | This document; ATLAS LAr and HSF white-paper citations and bibliography entries |
| 0004 | `9510f51b` docs(detector): apply independent review R720d9d2e80 to the front-end task document | Review corrections; second source for C4; review record in VALIDATION |

Hashes differ after `git am`; identify commits by their messages.

**Validation results [C]** (details in `FRONTEND-RECO-SIM` of `VALIDATION.md`):

| Item | Result |
|---|---|
| Landau | Agrees with SciPy 1.18.1 to 3.5e-13; with an independent implementation of the oscillatory integral to 2e-6 |
| `hit-efficiency` | Agrees with `scipy.integrate.quad` (0.98796331) and a 4e6-event MC (0.987947 ± 0.000055) |
| `optimal-filter` | Lagrange conditions and constraints hold to 1e-10; joint-fit errors agree with a least-squares MC (0.431 ns) |
| `waveform-toy` | Closure \|z\| < 4 (with the σ error from the fourth moment; the Gaussian formula overstates z for exponential pileup) |
| `s-curve` | Agrees with SciPy Nelder-Mead to < 1e-3 e; 2000-scan MC σ_T 17.9 e, σ_σ 17.5 e (design mode 18.3, 17.3); pull widths 0.98, 1.02 |
| `threshold-trim` | Agrees with a 2e6-channel MC: 441.6 vs 441.8 e; 18.24 % vs 18.28 % beyond range |
| Mutation | 8 mutants: 6 killed, 1 equivalent, 1 got its own test afterwards |
| Static checks `tools/run_all_checks.py --part static --no-cli` (rerun after calibration and after this document) | 27 of 29 pass, 2 skip (host CLI); ruff clean; tool contract pass; `tools/check_wiring.py --since bc7b1c18` pass |
| Full check `tools/run_all_checks.py --part all --no-cli --jobs 2` (before calibration; the run recorded in VALIDATION) | 31 checks: 27 pass, 2 skip (host CLI), 2 fail (`unittest`, `ams_optional`) |
| Unit tests in that full check | 5549 run: 5237 pass, 294 skipped, 18 failures or errors, none caused by this work: 16 `ModuleNotFoundError` (SymPy or mpmath missing; PyPI unreachable there); `tests.skills.hep_authoring.test_paper_skeleton` and `tests.tools.test_ci_plan.RunnerRecord` fail the same way on a clean main; `ams_optional` fails on the same missing SymPy |
| Independent review R720d9d2e80 | All findings disposed (35 changed, 1 declined). Facts-lens slot S4 was rejected twice and escalated for a human; the maintainer accepted it as missing on 2026-10-26 (the shadow facts slot S3 was accepted), which closes the escalation (VALIDATION FRONTEND-RECO-SIM) |

## Objective

**Stage map**

| Stage | What it delivers | Prerequisite | Decision gate | Can run in parallel with |
|---|---|---|---|---|
| FE0 | Pre-merge acceptance of the completed work in E2 | — | D-C4 (how C4 is classified); D-FE0 (merge path) for the merge itself | — |
| FE1 | Table (measured) charge spectrum in `hit-efficiency` | FE0 merged | — | FE2, FE3 |
| FE2 | Measured noise covariance in `waveform-toy` and `optimal-filter` | FE0 merged | — | FE1, FE3 |
| FE3 | Multi-channel batch `s-curve` | FE0 merged | — | FE1, FE2 |
| FE4 | simreco `noise-digitization` driven by `hit-efficiency` | FE0 merged | D-FE4 | — |
| FE5 | Shrink the front-end reference page | FE0 merged | D-FE5 | — |

"FE0 merged" can be relaxed only with maintainer approval (§0 item 2).

**Definition of done.**

- FE0: the full checks pass in E2 except the known failures of FE0-1; C4 is handled as the maintainer decided (D-C4);
  the branch is ready to merge.
- Every stage: code, tool contract, tests, reference pages, CHANGELOG and VALIDATION agree with one another; the static
  checks all pass; before merging, one full check runs in E2 and fails only as FE0-1 allows.

## Scope

### In Scope

| Stage | Scope |
|---|---|
| FE0 | Rerun the full checks in E2; fix every failure this work causes; complete the environment field in VALIDATION; handle C4's commit classification per D-C4 |
| FE1 | `hit-efficiency` accepts a measured or simulated charge spectrum (table) as signal model, fixing the too-thin low-side Landau tail |
| FE2 | `waveform-toy` and `optimal-filter` accept a measured per-sample noise covariance (including non-exponential correlation); `waveform-toy` generates noise by Cholesky; both compute weights and predictions from the same matrix |
| FE3 | `s-curve` batch fit of many channels from CSV; per-channel results and a threshold-dispersion summary that states which dispersion goes to which downstream tool |
| FE4 | (after D-FE4) simreco `noise-digitization` parameters derivable from `hit-efficiency` |
| FE5 | shrink the front-end reference page: two new pages, hub registration (D-FE5) |

### Out of Scope

- ASIC/FPGA design, ADC architecture selection, firmware coding (excluded by the reference page's Scope).
- Production digitization code of any experiment (hep-computing); ML waveform reconstruction or learned fast
  digitization (hep-ml).
- Changes to `SKILL.md`, the skill description or the Resources table (they would trigger a live-routing rerun).
- Version numbers and releases (release manifest); pushing `main` or opening a pull request (needs maintainer approval).
- Changing the version of `core/` or `contracts/` (FE0–FE3 only add tool-contract operations or options).

## Repository Context

All paths below exist on `bc7b1c18` or on `worktree-frontend-reco-sim` [C].

#### Files

**Code and contract**

| Path | Role |
|---|---|
| `skills/hep-detector/scripts/frontend_response.py` | All 15 front-end subcommands; standard library plus `core.stats._linalg.solve` and `core.stats.statistical_toys.chi2_sf` |
| `contracts/tool_contracts/frontend_response.json` | One operation per subcommand; options, inputs, outputs and `--help` must agree |
| `core/stats/_linalg.py` | `solve`; `cholesky` (by default refuses a non-positive-definite matrix and does not repair it) |

**Tests**

| Path | Role |
|---|---|
| `tests/contracts/test_tool_contract.py` | `FRONTEND_OPS`: one succeeding and one invalid-input argument set per operation; `FrontendResponseContractTests` |
| `tests/skills/test_cli_robustness.py` | `NO_INPUT_FILE` lists `frontend_response.py` ("numbers on the command line"); it moves to `MISSING_FILE_ARGS` once any file input exists |
| `tests/skills/hep_detector/test_frontend_response.py` | Tests of the original ten subcommands |
| `tests/skills/hep_detector/test_frontend_waveforms.py` | Tests of the five new subcommands (31), each number with an independent oracle |

**Reference pages**

| Path | Role |
|---|---|
| `skills/hep-detector/references/front-end-electronics-and-signal-processing.md` | Front-end reference page (39,597 bytes) |
| `skills/hep-detector/references/readout-digitization-and-overlay.md` | Digitization recipe, overlay rules, closure validation |
| `skills/hep-detector/references/detector-simulation.md` | Its Digitization section links to the page above |
| `skills/hep-detector/references/detector-principles-bibliography.md` | Bibliography; each entry records how it was checked |

**simreco and examples (FE4 only)**

| Path | Role |
|---|---|
| `adapters/geant4/assets/simreco/simreco.cc` | `Strips` struct fields `pitch_y`, `pitch_z`, `sharing`, `threshold`, `efficiency`, `noise_per_plane` (read from configuration key `noise_hits_per_plane`); `StripSigma` |
| `examples/design-minimal-spectrometer/` (J15), `examples/design-search-j16/` (J16) | Both records use `noise-digitization` |

**Tools and maintenance documents**

| Path | Role |
|---|---|
| `tools/run_all_checks.py` | Overall checks |
| `tools/reference_inventory.py` | Reference inventory; regenerate after any reference page changes |
| `tools/measure_entrypoints.py` | SKILL.md and entry-page budget |
| `tools/check_wiring.py` | Wiring check of reference pages |
| `docs/maintenance.md` | Checks; `sci-fix` rules; evidence classes and levels; wiring steps of "Adding a topic" |
| `docs/dev/geant4-architecture/geant4-program.md` | §P.10: the maintainer's isolated-worktree rules (followed here; differences in §0) |
| `CHANGELOG.md`, `VALIDATION.md`, `docs/capability-matrix.md`, `skills/hep-detector/README.md` | Keep in step at every stage |

#### Rules

**Violations make a check fail:**

1. CLI behaviour: success exits 0 and prints JSON; a `ValueError` becomes exit 2 through `parser.error` with
   `error_kind: invalid-input`; a non-finite result exits 1. Every subcommand has `--status` (default `unvalidated`),
   echoed unchanged; synthetic results also carry `status_label: synthetic` [C].
2. Any new or changed subcommand option: change the tool contract and `FRONTEND_OPS` together;
   `python3 contracts/tool_contract.py` must pass [C].
3. Once a subcommand reads a file: move `frontend_response.py` from `NO_INPUT_FILE` to `MISSING_FILE_ARGS` in
   `tests/skills/test_cli_robustness.py` (`docs/maintenance.md`, "Adding a topic", step 3) [C].
4. `skills/*/scripts` may import only `core` and `contracts` (`tools/check_layering.py`) [C].
5. In skill reference pages and code, experiment names (ATLAS, CMS, …) appear only between `<!-- example: ... -->` and
   `<!-- /example -->`; cite an experiment's method in the "source citation" style of `calibration-and-alignment.md`
   (`tools/check_layering.py`) [C].
6. After changing any reference page, rerun `python3 tools/reference_inventory.py`, or the `reference_inventory` check
   fails [C].
7. A new reference page must be one step from the Resources table or from the routing part of the entry reference page,
   or two steps from a hub registered in `tools/wiring_known_gaps.json` (`tools/check_wiring.py`, R1) [C].
8. hep-detector `quick_load_bytes` (SKILL.md plus the entry reference page) ≤ 25,600 bytes
   (`tools/measure_entrypoints.py`; currently 24,669) [C].

**Warnings only, but respect them:**

- `reference_inventory` warns when the routing part of `skills/hep-detector/references/detector-principles-summary.md`
  exceeds 4096 bytes (exit code unchanged). It is 4081 bytes, so new reference pages are **not** added to that index [C].
- `reference_inventory` warns when a reference page exceeds 24 KB; the front-end reference page already does [C].

**Commit conventions:**

| Prefix | When |
|---|---|
| `sci-fix:` | Changes existing numbers, verdicts or method guidance; needs a regression test and the evidence of maintenance classes S1–S3 (`docs/maintenance.md`) [C] |
| `move:` | Pure move, no content change [C] |
| `feat:` | New functionality (repo-history convention; not defined in `docs/maintenance.md`) [C] |

Every commit ends with the trailer the session prescribes [I].

#### Conventions and formulas

Implemented in the tool. Extensions must not change their meaning.

**Pulse and sampling**

- Pulse: peak-normalized CR-(RC)^n, `g(t) = (t/τ)^n e^(−t/τ) / (n^n e^(−n))`, `t_p = nτ`.
- Sample i is at `t_p + first_offset + i·period`; negative `first_offset` means before the peak.
- Waveform-tool units: amplitudes and noise in units of the per-sample electronic noise σ; the pulse has unit peak.
- Phase-error sign: `dt > 0` means the pulse started dt earlier than assumed, so samples lie later on the pulse
  (`g(t_i + dt)`).

**Noise and filters**

- Noise covariance: `R_ij = ρ^|i−j| + ν⟨a²⟩ ∫ g(t) g(t + t_i − t_j) dt` (Campbell; ν in Hz, time in ns, factor 1e-9 in
  the code).
- Constrained optimal filter: `w = R⁻¹C (CᵀR⁻¹C)⁻¹ e₁`, `C = [g, c₁, …]`; phase constraint `c = g′`, baseline constraint
  `c = (1,…,1)`; variance `((CᵀR⁻¹C)⁻¹)₁₁`.
- Baseline gain: a constant offset b on every sample biases the amplitude by `b·Σw`.

**Signal, efficiency and occupancy**

- Landau: Kölbig's φ(λ), MPV at `λ = −0.22278298`; equals the stable law S1(α=1, β=1, scale π/2, loc 0), i.e.
  `λ = (π/2) z + ln(π/2)` with z distributed as `scipy.stats.landau`; charge `Q = f·[MPV + ξ(λ − λ_mp)]`.
- Efficiency: `1 − E[F_Q(T + s u)]`, `u ~ N(0,1)`, `s² = σ_n² + σ_thr²`.
- Noise occupancy, averaged over the threshold spread (closed form): per sample `Q(T/s)`; Rice count per window
  `ν₀ (σ_n/s) exp(−T²/2s²) · W`; the upper bound is the sum of the two.

**Calibration**

- S-curve: `hits ~ Bin(N, Φ((Q − T)/σ))`; binomial ML; Fisher errors; deviance approximately χ²(n−2).
- Trim: range half-width `h = (2^b − 1)D/2`, edge `h + D/2`; residual rms `D/√12` inside the range, residual `|x| − h`
  beyond it (closed form).

**Flow of the threshold dispersion** (the two inputs are different quantities):

| Input | Takes | Source |
|---|---|---|
| `threshold-trim --spread` | **Pre-trim** dispersion | Scan before trim |
| `hit-efficiency --threshold-dispersion` | **Operating (post-trim)** dispersion | `residual_dispersion` of `threshold-trim`, or a rescan after trim |

They coincide only for a readout without trim.

## Technical Approach

#### §0 Isolated worktree (every stage)

Follows `docs/dev/geant4-architecture/geant4-program.md` §P.10 [C]; the only exception is stated in item 2.

1. **One stage, one worktree, one branch.** Location `.claude/worktrees/frontend-<stage>` (lower case, e.g.
   `.claude/worktrees/frontend-fe1`); branch `worktree-frontend-<stage>`.
2. **Base.**
   - FE0: the completed work. The remote has only `main` (`git ls-remote origin` [C]), so create the worktree from
     `origin/main` in E2 and apply patches `0001`–`0004` in order with `git am`. The patches ship with this document.
     On `d5c8ff24` (0.40.0) they need `git am --3way`: the generated reference inventory conflicts (regenerate it) and
     the CHANGELOG entry lands in the released 0.39.0 section (move it to Unreleased) [C].
   - FE1–FE5: the latest `origin/main` **after FE0 is merged** (as §P.10.2: "the latest main that contains every
     prerequisite stage"). Do not start them earlier. If the maintainer approves an early start, base on FE0's branch,
     rebase onto the new `main` before merging, rerun all checks, and state this exception to §P.10.2 in the stage's
     VALIDATION entry.
3. **Create.**
   - Claude Code: `EnterWorktree` with name `frontend-<stage>`; a subagent doing the implementation gets
     `isolation: "worktree"` in the Agent tool.
   - Other environments, FE0:
     ```bash
     git fetch origin
     git worktree add .claude/worktrees/frontend-fe0 -b worktree-frontend-fe0 origin/main
     git -C .claude/worktrees/frontend-fe0 am /path/to/000[1-4]-*.patch
     ```
   - Other environments, FE1–FE5 (after FE0 is merged; replace `fe1` with the stage):
     ```bash
     git fetch origin
     git worktree add .claude/worktrees/frontend-fe1 -b worktree-frontend-fe1 origin/main
     ```
4. **Check before starting** (record the results in the environment field of the stage's VALIDATION entry):
   - `git rev-parse --show-toplevel` is this worktree;
   - `git branch --show-current` is the stage branch;
   - `git status` is clean;
   - FE1–FE5 only: `git merge-base --is-ancestor <FE0 merge commit> HEAD` succeeds.
5. **Work inside the worktree** (§P.10.3):
   - Edit, test and run MC only here; never `cd` into the main checkout or another worktree.
   - Never use a bare `git stash` (shared by all worktrees); make a WIP commit instead.
   - Put scratch output in an uncommitted directory such as `work/`.
   - Commit only to the stage branch; push it to the remote branch of the same name, or, without push permission, keep
     it local and report. Never push `main` or open a pull request without maintainer approval.
6. **Finish.** After merging (or when abandoning), `git worktree remove .claude/worktrees/frontend-<stage>` and delete the
   local branch; do no cleanup in the main checkout.
7. **Parallel stages.** FE1, FE2 and FE3 all touch `frontend_response.py`, the same contract, the same test file and
   `test_cli_robustness.py`. They may run in parallel; whichever merges later rebases and reruns all checks. One stage is
   never implemented by two agents at once [I].

#### §FE0 Pre-merge acceptance

- **Prerequisite:** none. **Gate:** D-C4 for step 4.
- **Steps:**
  1. Create and check the worktree in E2 (Python, NumPy, SciPy, SymPy, mpmath) per §0.
  2. Run `python3 tools/run_all_checks.py --out work/checks`, including the host CLIs; without them add `--no-cli` and
     say so in the record.
  3. For every failure, rerun the same test id on a clean `origin/main`. It is known only if its test id is listed in
     FE0-1 **and** the exception type and message match. Any other failure is caused by this work: fix it and add a
     regression test.
  4. Handle C4 as decided in D-C4: either keep it in the `feat:` commit and note it in the CHANGELOG, or split the C4
     rewrite into its own `sci-fix:` commit with maintenance-class S3 evidence (the two section-located sources in
     References).
  5. Add the E2 results and environment field (Python, NumPy, SciPy, SymPy, mpmath versions; commit) to
     `FRONTEND-RECO-SIM` in `VALIDATION.md`.
- **Done when:** FE0-1, FE0-2, FE0-3 and the All-stages criteria hold.

#### §FE1 Table signal model for `hit-efficiency`

- **Prerequisite:** FE0 merged. **Gate:** none (the [U] about a public measured spectrum only affects test data).
- **Steps:**
  1. Add `--signal-model table` and `--spectrum FILE`. The file is CSV with header `charge,density` or `charge,count`;
     charges strictly increasing.
  2. Build a monotone CDF:
     - `density`: trapezoidal integration, then normalize;
     - `count`: entries are bin centres, edges at the midpoints between neighbours;
     - interpolate linearly between points: the density for `density` (so the CDF between points is the exact
       integral, quadratic), the CDF within a bin for `count` (uniform bins) [C, FE1];
     - outside the table range use 0 below and 1 above, and flag in `validity` every threshold beyond the range.
  3. `--signal-fraction` scales the table's charge axis; `--threshold-dispersion` and the occupancy calculation are
     unchanged.
  4. Every file error is invalid-input (exit 2, JSON), never a traceback:
     - missing or unreadable file (`OSError`);
     - empty file, or header only;
     - wrong column names or wrong number of columns;
     - non-numbers, NaN or inf;
     - charges not strictly increasing;
     - negative density or count;
     - zero total.

     Convert `OSError`, `csv.Error` and `UnicodeDecodeError` to `ValueError` inside the reading function. Non-finite
     numbers in an input file are invalid-input (exit 2); the rule "a non-finite result exits 1" is about results only.
  5. Move `frontend_response.py` to `MISSING_FILE_ARGS` (Rule 3) and give `hit-efficiency --spectrum` an argument set with
     a non-existent path.
  6. Add one sentence to the paragraph "Efficiency with a fluctuating signal" of the front-end reference page: for the
     low-side tail below 1 %, use the `table` model with a measured spectrum. Then regenerate the reference inventory
     (Rule 6).
- **Done when:** FE1-1 to FE1-4 and the All-stages criteria hold.

#### §FE2 Measured noise covariance (`waveform-toy` and `optimal-filter`)

- **Prerequisite:** FE0 merged. **Gate:** none.
- **Steps:**
  1. Add `--noise-covariance FILE` to both subcommands, through one shared reading function. File format: JSON
     `{"covariance": [[...]]}`, dimension equal to `--samples`, units of per-sample noise σ². Mutually exclusive with
     `--rho`.
  2. Decompose with `core.stats._linalg.cholesky`. Invalid-input, with the matrix never repaired: not positive definite,
     not symmetric, wrong dimension, non-finite entries. `waveform-toy` generates each event's noise as `L·z`.
  3. Compute weights and predictions from the same matrix plus the Campbell pileup term.
  4. Add outputs `noise_model` (`ar1` with `--rho`, `measured` with `--noise-covariance`) and `noise_covariance_sha256`,
     the SHA-256 of the UTF-8 bytes of `json.dumps(matrix, separators=(",", ":"))`, where `matrix` is the parsed matrix
     as a list of lists of float.
  5. File errors and `MISSING_FILE_ARGS`: as §FE1 steps 4 and 5.
- **Done when:** FE2-1 to FE2-4 and the All-stages criteria hold.

#### §FE3 Multi-channel batch for `s-curve`

- **Prerequisite:** FE0 merged. **Gate:** none.
- **Steps:**
  1. Add `--scan-file FILE`: CSV columns `channel,charge,injections,hits`. Mutually exclusive with `--charges`, `--hits`
     and `--design-*`. File errors and `MISSING_FILE_ARGS`: as §FE1 steps 4 and 5.
  2. Fit each channel with the existing `scurve_fit`. A channel whose fit raises (does not cross 50 %, singular matrix)
     goes to `failed_channels` with its reason; the batch continues.
  3. Inclusion rule. A channel enters the summary only if it converged, has at least 2 points in the transition
     (5 %–95 %) and has p ≥ 1e-3. Other fitted channels go to `excluded_channels` with their reason. Output `n_included`,
     `n_excluded`, `n_failed`. If excluded plus failed exceed 5 % of channels, warn in `validity` that the dispersion
     may be biased (excluded channels tend to have the most extreme thresholds).
  4. Summary fields (included channels only):

     | Field | Definition |
     |---|---|
     | mean threshold | Mean of fitted thresholds |
     | `threshold_sd` | Sample standard deviation of thresholds |
     | `threshold_mad_sigma` | `1.4826 × MAD` |
     | `threshold_dispersion_corrected` | `sqrt(max(0, threshold_sd² − mean(σ_T²)))`; if the radicand is ≤ 0, report 0 and write "dispersion not above the fit error" in `validity` |
     | median noise | Median of fitted noise |
     | count of p < 1e-3 | Number of channels with p < 1e-3 (*at FE3 [C]:* over all fitted channels, `fitted_channels_with_p_below_1e-3`; over the included ones it would always be 0) |

     The summary is always finite and never causes exit 1.
  5. Downstream flow, stated in the output `note`: `threshold_dispersion_corrected` is the value to pass on — to
     `threshold-trim --spread` if the scan was taken before trim, to `hit-efficiency --threshold-dispersion` if after
     trim (see "Flow of the threshold dispersion").
- **Done when:** FE3-1 to FE3-5 and the All-stages criteria hold.

#### §FE4 simreco coupling

- **Prerequisite:** FE0 merged. **Gate:** D-FE4 — do not start before the maintainer decides.
- **Goal:** `noise-digitization`'s `efficiency` and `noise_hits_per_plane` can be filled from `hit-efficiency` results; a
  threshold option in ENC units is added alongside the current charge-fraction threshold.
- **Classification depends on the defaults [I]:**

  | Case | Prefix | Consequence |
  |---|---|---|
  | Only new options; defaults unchanged | `feat:` | Existing outputs and the J15/J16 records unchanged; add a test that the default output is bit-for-bit unchanged |
  | Defaults or existing numbers change | `sci-fix:` | Follow the evidence levels of `docs/maintenance.md` and the gates of the Geant4 specification; re-record J15 (`examples/design-minimal-spectrometer/`) and J16 (`examples/design-search-j16/`), both of which go through the qualification path of fidelity F4 |

- *At FE4 [C]:* D-FE4 chose the first case. The coupling is on the hep-detector side: `hit-efficiency
  --simreco-channels N` prints the `noise-digitization` keys (`threshold` as the fraction of the reference signal,
  `efficiency`, `noise_hits_per_plane`), and `--threshold-enc` is the threshold in ENC units. The adapter is not
  changed: every adapter change needs an adapter version bump (`docs/maintenance.md`, "Adapter changes"), and version
  numbers are out of scope here.

#### §FE5 Shrinking the front-end reference page

- **Prerequisite:** FE0 merged. **Gate:** D-FE5 — do not start before the maintainer decides.
- **Facts [C]:** the page is 39,597 bytes; the warning line is 24,576 bytes (24 KB). Moving only `## Photosensor readout`
  and `## LAr TPC signal processing` removes 2,779 bytes (leaving about 36.8 KB) and does not reach the line. Getting
  below it needs about 15 KB moved, for example the sampled-waveform estimator section and the calibration section.
- **Steps:**
  1. Move the chosen sections, as decided in D-FE5, to a new reference page.
  2. Wire the new page (Rule 7). Because this work does not change SKILL.md or the summary index, register the front-end
     reference page as a hub in `tools/wiring_known_gaps.json` (it is one step from the Resources table) and link the new
     page from it; `tools/check_wiring.py --since <base>` must pass.
  3. Use a `move:` commit with no content change. Leave at the old location a pointer headed "… (moved)" for one minor
     version and record in `pointers` the version that removes it (`docs/maintenance.md`, "Adding a topic").
  4. Regenerate the reference inventory; update the reference count in the README.
- *At FE5 [C]:* the front-end page went from 40,480 bytes (after FE1 and FE4) to 23,863 bytes in the `move:` commit
  and to about 24.2 KB with the sentence that names the two new pages, under the line. The "(moved)" pointers are
  sections of a live page, not pointer pages, so `check_wiring.py` does not expire them: their `pointers` entries
  (keyed `page#anchor`, `remove_in` 0.42.0) say to remove them by hand. They were shipped in 0.41.0 and removed
  after it (2026-10-26), for 0.42.0. Links whose topic moved (Campbell pileup, SiPM
  saturation, dead time, the sampled-waveform estimators) now point to the new pages.

## Deliverables

| Stage | Deliverables |
|---|---|
| FE0 | E2 full-check record (summary of `work/checks/check-run-*.json` in `FRONTEND-RECO-SIM` of `VALIDATION.md`); any fix commits; C4 handled per D-C4 |
| FE1 | `table` signal model in `frontend_response.py`; contract, `FRONTEND_OPS`, `MISSING_FILE_ARGS` updated; tests; one sentence in the reference page; CHANGELOG and VALIDATION entries |
| FE2 | `--noise-covariance` in `waveform-toy` and `optimal-filter`; contract; tests; CHANGELOG; VALIDATION |
| FE3 | `--scan-file` batch mode; contract; tests; CHANGELOG; VALIDATION |
| FE4 | `hit-efficiency --simreco-channels`, `--simreco-sides`, `--threshold-enc`; contract; tests; reference sentences; CHANGELOG; VALIDATION |
| FE5 | As decided in D-FE5: new reference page, wiring (hub registration), moved pointer, regenerated reference inventory, README reference count |
| Every stage | One branch; one or more commits with the trailer; `main` not pushed |

## Acceptance Criteria

#### FE0

- **FE0-1** In E2, every item of `tools/run_all_checks.py` except the host CLIs passes, or fails only as listed below,
  with the same test id, exception type and message as on a clean `origin/main`:
  - `tests.skills.hep_authoring.test_paper_skeleton.PaperSkeleton.test_compiled_bibliography_shows_an_eprint`;
  - `tests.tools.test_ci_plan.RunnerRecord.test_check_ams_optional_runs_only_the_planned_modules`.

  `ModuleNotFoundError: No module named 'sympy'` or `'mpmath'` must not appear in E2; if it does, E2 is incomplete —
  fix the environment first. `ams_optional` counts as known only if it fails for that same missing-module cause.
- **FE0-2** `FRONTEND-RECO-SIM` in `VALIDATION.md` has an E2 environment field (Python, NumPy, SciPy, SymPy, mpmath
  versions; commit).
- **FE0-3** C4 is handled as decided in D-C4 and this is written in the CHANGELOG.

#### FE1

- **FE1-1** A density table sampled from the `landau` model (MPV 23000 e, ξ 1500 e, σ 1000 e) with charge step ≤ 150 e
  (0.1 ξ): at thresholds 16000–24000 e every 1000 e (Landau inefficiency 1.8e-6 to 0.36), the relative difference
  between the `table` and `landau` inefficiencies is < 1e-3. *Amended at FE1 (2026-10-25) [C]:* as written the
  criterion cannot hold. The table is normalized over its range, and the Landau tail beyond Q falls only as about
  ξ/(Q − MPV): a table to 200 000 e misses 0.88 %, which raises every inefficiency by that fraction. Interpolation adds
  about 4.5 % (linear CDF) or 2.3 % (linear density) at 16000 e with a 150 e step, falling as the step squared. The test
  therefore compares with the `landau` model truncated at the table's upper end (60 000 e) and uses a 25 e step (still
  ≤ 150 e); `validity` flags a table that ends above 1e-3 of its peak.
- **FE1-2** Negative control: the same table with its charge axis shifted by +300 e (0.2 ξ) must fail the FE1-1 check; at
  these thresholds the relative difference is at least 9 % (computed with `hit-efficiency` at MPV 23300 e [C]).
- **FE1-3** A Gaussian signal (mean 20000 e, σ 1000 e) as a density table with step ≤ 50 e (0.05 σ): at thresholds
  17000–23000 e the efficiency agrees with the closed-form Φ to < 1e-4.
- **FE1-4** Each bad-file kind of §FE1 step 4 gives exit 2 and `error_kind: invalid-input`, with no traceback on stderr;
  `frontend_response.py` is in `MISSING_FILE_ARGS` of `tests/skills/test_cli_robustness.py`.

#### FE2

- **FE2-1** With a ρ^|i−j| matrix (ρ 0.6, 7 samples), `predicted_sigma` from `--noise-covariance` equals that from
  `--rho 0.6` to 1e-12, and `waveform-toy` closure is |z| < 4.
- **FE2-2** With a positive-definite, non-exponential matrix (ρ^|i−j| plus a constant common-mode term 0.3), the sample
  covariance of 20 000 events matches the input element by element within 4 standard errors, and closure |z| < 4.
- **FE2-3** A matrix that is not positive definite, not symmetric, of the wrong dimension, or with non-finite entries gives
  invalid-input; the matrix is not repaired.
- **FE2-4** `noise_model` is `ar1` with `--rho` and `measured` with `--noise-covariance`; `noise_covariance_sha256` equals
  the value recomputed as in §FE2 step 4 and changes when any element changes.

#### FE3

- **FE3-1** Per-channel results from calling `scurve_fit` channel by channel are identical to the batch output.
- **FE3-2** 200 synthetic channels (thresholds N(3700, 150²) e, σ 300 e, 8 charge points every 200 e, 100 injections):
  `threshold_dispersion_corrected` is within 3 MC standard errors of 150 e (MC standard error from at least 50 batches).
- **FE3-3** Synthetic batches with true dispersion 0 e and 5 e: exit 0; `threshold_dispersion_corrected` finite and ≥ 0;
  a batch whose radicand is ≤ 0 has "dispersion not above the fit error" in `validity`.
- **FE3-4** A batch with one channel that never crosses 50 % and one with p < 1e-3 completes; the first is in
  `failed_channels`, the second in `excluded_channels`; neither enters the summary.
- **FE3-5** For Gaussian synthetic thresholds the expectation of `threshold_mad_sigma` is within 3 MC standard errors of
  the true σ (*at FE3 [C]:* the σ of the fitted thresholds, sqrt(σ² + mean σ_T²); the MAD is not corrected for the
  fit error); the summary's median noise and count of p < 1e-3 equal the values recomputed from the per-channel results.

#### All stages

- `python3 contracts/tool_contract.py` passes.
- `ruff check` reports no errors on the changed Python files.
- `python3 tools/reference_inventory.py --check` passes.
- `tools/check_wiring.py --since <base>` passes.
- hep-detector `quick_load_bytes` from `tools/measure_entrypoints.py` ≤ 25,600.

## Validation

Run in `plugins/hep-research` of the stage's worktree. Commands 1–6 run at every stage; command 7 is the full check in E2,
for FE0 and before every stage merges, judged by FE0-1.

1. Unit tests of the front-end tools and CLI contracts.
2. Tool contract.
3. Reference inventory.
4. Wiring.
5. Lint.
6. Static checks.
7. Full check (E2).

```bash
python3 -m unittest tests.skills.hep_detector.test_frontend_waveforms \
  tests.skills.hep_detector.test_frontend_response tests.contracts.test_tool_contract \
  tests.skills.test_cli_contract tests.skills.test_cli_robustness tests.skills.test_reference_links
python3 contracts/tool_contract.py contracts/tool_contracts/frontend_response.json
python3 tools/reference_inventory.py --check
python3 tools/check_wiring.py --since origin/main
ruff check skills/hep-detector/scripts/frontend_response.py tests/skills/hep_detector/test_frontend_waveforms.py
python3 tools/run_all_checks.py --part static --no-cli --out work/checks
python3 tools/run_all_checks.py --out work/checks
```

Test requirements:

- Every new number has at least one independent oracle (analytic, closed form, independent implementation or MC), listed
  at the top of the test file as `test_frontend_waveforms.py` does.
- Every acceptance criterion has at least one test; criteria with a tolerance also have a negative control (like FE1-2).
- Revert mutants: reverting each change must make at least one new test fail (level D of `docs/maintenance.md`).
- Known failures unrelated to this work are judged only by FE0-1.

## Open Questions

- **[C] D-FE0**: decided 2026-10-25 by the maintainer: push `worktree-frontend-fe0`, one pull request with the
  commits kept, merged by the maintainer; no version bump in FE0.
- **[C] D-C4**: decided 2026-10-25 by the maintainer: split. C4 is its own `sci-fix:` commit (ledger
  FRONTEND-INJECTION-GAIN, both sources read in the full text, regression test `InjectionGainGuidance`).
- **[C] D-FE4**: decided 2026-10-25 by the maintainer: do FE4, new options only (`feat:`); defaults and the J15/J16
  records unchanged.
- **[C] D-FE5**: decided 2026-10-25 by the maintainer: do FE5 with two new pages,
  `front-end-waveform-processing.md` (sampled-waveform amplitude and time, pileup, photosensor and LAr TPC readout,
  digital pulse processing, pulse-shape discrimination) and `front-end-calibration.md` (calibration and simulation of
  the electronics); the front-end page is registered as a hub.
- **[C] FE1 spectrum**: decided 2026-10-26 by the maintainer: no measured spectrum (a search on 2026-10-26 found no
  open dataset ready to place in `assets/`); instead a simulated one,
  `skills/hep-detector/assets/thin-silicon-300um-mu10gev.geant4-pai.csv`, binned from J14's recorded Geant4 PAI run
  `mpv-pai` (10 GeV mu-, 300 um silicon; the rerun reproduced the recorded event file's hash). Its low-side tail is far
  wider than Landau's (`HitEfficiencyGeant4Spectrum`); it stays `unvalidated`, and users give their own measured
  spectrum with `--spectrum`.
- **[C] E2 versions**: recorded at FE0 (VALIDATION FRONTEND-RECO-SIM): Python 3.13.2, NumPy 2.5.3, SciPy 1.18.1,
  SymPy 1.14.0, mpmath 1.3.0.

## References

**Repository documents**

- Task format: `skills/hep-computing/assets/task-template.md`, `skills/hep-computing/references/task-authoring-guide.md`,
  `skills/hep-computing/references/task-quality-checklist.md`, `skills/hep-computing/references/acceptance-criteria.md`.
- Maintenance rules: `docs/maintenance.md`. Worktree rules: `docs/dev/geant4-architecture/geant4-program.md` §P.10.
- Content: `skills/hep-detector/references/front-end-electronics-and-signal-processing.md`,
  `skills/hep-detector/references/readout-digitization-and-overlay.md`,
  `skills/hep-detector/references/detector-simulation.md`, `skills/hep-detector/references/calibration-and-alignment.md`.
- Evidence: `FRONTEND-RECO-SIM` in `VALIDATION.md`; Unreleased in `CHANGELOG.md`; report of independent review
  R720d9d2e80.

**External sources (2026-10-25)**

| Source | Used for |
|---|---|
| W. E. Cleland, E. G. Stern, Nucl. Instrum. Methods A338 (1994) 467 | Optimal filtering and pileup noise |
| M. Aharrouche et al., arXiv:0709.1094, sec. 2.4 | ATLAS LAr: OF coefficients from g, g′ and the pedestal-run autocorrelation by Lagrange multipliers |
| N. Nikiforou for ATLAS, arXiv:1306.6756v2, sec. II-C | M_phys/M_cali in the cell-energy formula (C4, first source) |
| G. Aad et al., arXiv:0912.2642v4, sec. 3.1.2, eq. 5 | `1/(M_phys/M_cali)` as the ratio of responses to a calibration pulse and an ionization pulse of the same input current (C4, second source; read in the full text 2026-10-25) |
| J. Apostolakis et al., arXiv:1803.04165, sec. 5 | HSF simulation white paper: overlay needs non-zero-suppressed samples; signal addition is nonlinear |
| J. P. Nolan, Stochastic Models 13 (1997) 759, DOI 10.1080/15326349708807450 | Integral representation of stable distributions (Landau) |
| V. T. Jordanov, G. F. Knoll, Nucl. Instrum. Methods A345 (1994) 337 | Digital trapezoidal shaping |
