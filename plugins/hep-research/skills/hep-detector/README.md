# hep-detector

Detector performance and response for collider, fixed-target, neutrino, rare-event and astroparticle instruments, delivered as validated `response` artifacts, folded predictions, performance reports and conditions provenance.

## Core capabilities

- Owns: signal formation, reconstruction, detector calibration, alignment, efficiency and resolution, truth matching, detector simulation, data/MC comparison, parametrized response for recasting, response matrices, forward folding of predictions, double-counting checks, detector design principles, sourced detector atlas.
- Signal formation and readout: front-end electronics (noise, thresholds, timing, quantization, pileup, SiPM, dead time), optimal-filter weights of a sampled pulse, hit efficiency against noise occupancy, S-curve fits and threshold trim.
- Reconstruction: tracking, vertexing, calorimetry, particle identification (TOF, dE/dx, RICH; many-sample charge and log-likelihood ratio), timing, Cherenkov, transition radiation, time of flight, muon systems.
- Efficiency and resolution: tag-and-probe from counts or weighted probes, truth matching, core and tails reported separately.
- Response matrices: built from matched events, era responses mixed or stacked, species-migration blocks, forward folding, double-count check against the correction chain.
- Calibration, alignment and conditions: stability over time (trends, change points, CUSUM), proposed calibration era boundaries, propagation of a calibration residual into yields and ratios.
- Charge-sign confusion rates; survival and fragmentation feed-down of nuclei in detector material.
- Detector simulation: Geant4 study protocol, study checker, independent-reference benchmarks for Geant4 runs; choosing Allpix Squared or Garfield++ for charge transport in sensors and gases (both task cards run on one macOS host; see the guide's limitations).
- Detector design: system design workflow, design evaluations from tool contracts, automated candidate generation (Sobol, NSGA-II, hypervolume), design-level budget sums, tracker resolution for a stated layout.
- Sourced detector atlas for large experiments (validate, render, query, audit); `unknown` when a fact is absent.
- Astroparticle instruments: cosmic-ray spectrum and composition, air showers (Gaisser-Hillas profile), ground arrays, imaging atmospheric Cherenkov telescopes, neutrino telescopes, space-based direct detection, multimessenger analysis; geomagnetic cutoff backtracing through the optional OTSO adapter.

## Triggering conditions

Use when:

- the deliverable is about how a detector responds: signal formation and readout, design principles and trade-offs, reconstruction, calibration and alignment, efficiency and resolution, detector simulation (Geant4), data/MC agreement, conditions and their provenance;
- a response matrix, folding a prediction through the response, or a parametrized response for recasting is needed;
- the question concerns geomagnetic cutoff backtracing (OTSO);
- the question concerns a named experiment's detector or resolution (load it first even for a quick question: it reads the profile or sourced atlas and asks which configuration is meant instead of quoting from memory).

Not for:

| Need | Hand to |
|---|---|
| Unfolding, fits on the response; tag-and-probe pass/fail fit, pileup systematics; limits | hep-statistics |
| Measurement design using these numbers | hep-measurement |
| Theory; the truth-level prediction to fold comes from hep-theory as a `prediction` | hep-theory |
| Simulation production, conditions code, generic code | hep-computing |
| ML-based reconstruction or calibration; training a learned fast simulation or ML response model | hep-ml |
| Writing up results | hep-authoring |

## Workspace directory architecture

```text
hep-detector/
├── SKILL.md                  entry point loaded by the host
├── README.md                 this folder guide
├── references/               topic references, entry: detector-principles-summary.md
├── scripts/                  command-line helpers
│   └── design_search_lib/    Sobol, NSGA-II, hypervolume behind evaluate_design.py search
├── assets/                   example inputs, Geant4 schema and rule table
│   └── design-search/        realization rules per role, NIST materials, Sobol direction numbers
└── examples/                 behavioural examples for Geant4 studies
```

| Path | Content |
|---|---|
| `SKILL.md` | entry point: invariants, workflow, context resolution, resources, handoffs; its front matter carries the routing description and it stays under 8 KiB |
| `references/` | forty-four references: a principles summary that indexes the rest, the detector system design workflow, one file per subsystem or topic, astroparticle instruments, case studies, comparison tables, glossary, bibliography |
| `scripts/` | twenty-four helpers and the package `design_search_lib/` (Sobol, NSGA-II, hypervolume) behind `evaluate_design.py search`: design evaluations from tool contracts, automated candidate generation and the derived design report, design-level budget sums, straight-line acceptance and PID rejection, the sourced detector atlas (validate, render, query, audit), a tracker resolution for a stated layout (exact fit and Gluckstern, scattering, MDR, impact parameter, requirement scan), a response artifact from matched events, era responses mixed or stacked, calorimeter resolution, Cherenkov angle, front-end electronics (noise, thresholds, timing, quantization, pileup, SiPM, dead time), multiple scattering, PID separation power, pileup reweighting, tag-and-probe efficiency, the Gaisser-Hillas longitudinal profile, a seeded toy spectrometer (synthetic events and periods), propagation of a calibration residual into yields and ratios, many-sample PID, stability over time, survival and fragmentation feed-down in material, charge-sign confusion rates, species-migration responses, a Geant4 study checker, independent-reference benchmarks for Geant4 runs and the naming extractor for calibrations and conditions tags |
| `assets/` | a simulated thin-silicon charge spectrum for `hit-efficiency --signal-model table` (Geant4 PAI, from journey J14's run `mpv-pai`, unvalidated); synthetic example inputs: a calorimeter response, a detector stack, pileup profiles, a fictional toy-spectrometer configuration, multisample PID events and a response curve, a stability series; the Geant4 study-spec schema with a synthetic example and the sourced Geant4 physics-rule table; `design-search/`: the realization rules per role, the Geant4 NIST materials table and the Sobol direction numbers of `evaluate_design.py search` |
| `examples/` | two illustrative behavioural examples for Geant4 studies: eliciting a study spec, and auditing a result claimed as validated |

References: start with `references/detector-principles-summary.md`, then the topic file the task needs:

- front-end electronics and signal processing, readout digitization and overlay, tracking, calorimetry, PID, timing, muon systems, noble-liquid and rare-event detectors, physics objects, triggers and pileup, reconstruction, photon-likelihood reconstruction, truth matching, performance metrics, response and forward folding, data/MC validation, simulation, calibration and alignment;
- charge-sign confusion: a synthesis note (mechanisms, how the rate is measured, handoff to hep-measurement); status `documented`;
- astroparticle instruments: cosmic-ray spectrum and composition, air showers, ground arrays, imaging atmospheric Cherenkov telescopes, neutrino telescopes, space-based direct detection, multimessenger analysis.

## Input and output specifications

Inputs:

- Request: a question about how the detector responds, a performance study, a response to build or fold, a design to evaluate, a Geant4 study to specify or audit.
- Profiles and context: the profiles the user names, else those bound in `hep-research.project.json` (checked with `contracts/project.py --preflight`); then only the needed subsystem modules. Without a profile for a named experiment: the sourced detector atlas (`detector_atlas.py query`, claim ids; `unknown` if absent), and the skill asks which configuration is meant.
- Files and artifacts read: matched events (CSV), tag-and-probe counts or a CSV of probes with frequency or sampling weights, stability series, per-species responses and sign rates, calibration residual events, Geant4 study specs and the run files `adapters/geant4` writes, design candidates and tool contracts in `contracts/tool_contracts/`, `prediction` artifacts from hep-theory.

Outputs:

- Artifacts written to the project's `artifacts_dir`: `response` (truth/reco axes, orientation, normalization, what sits inside the matrix, intended use), folded `prediction`, performance reports, conditions provenance, design evaluations and the derived design report, the Geant4 `unvalidated` study record.
- A `response` must pass both checks before another skill consumes it:

```text
python3 "<plugin root>/contracts/validate.py" <artifacts_dir>
python3 "<plugin root>/contracts/response_adapter.py" <artifact> --validate
```

- Naming inventories: a working file under `<project>/naming/`, refused inside `artifacts_dir`.

Script CLI contract:

```text
--help              read first
--status LABEL      echoed as the status label
output              JSON at every exit code
exit 0              ok
exit 1              failed
exit 2              invalid input
exit 3              toy_spectrometer.py without NumPy; check_geant4_study.py incomplete (missed statistical target);
                    extract_names.py written but zero inputs scanned
```

Script notes:

- `build_response.py`, `mix_period_responses.py`: exit 1 when the artifact fails its validation; nothing is written.
- `propagate_scale_distortion.py`: exit 1 when a user plugin fails.
- `multisample_pid.py`: combines many samples (a charge from many dE/dx layers with the leakage matrix between neighbouring charges, or a log-likelihood ratio from per-layer PDFs with its efficiency - mis-identification curve).
- `tag_and_probe_efficiency.py`: counts, or a CSV of probes with frequency or sampling weights (Kish effective sample size; negative weights go to hep-statistics) and bins, with no cap on the total.
- `charge_confusion_rate.py`: charge-sign confusion rate per bin (Barlow-Beeston template fit with a profile-likelihood interval, or a control sample with Clopper-Pearson; a Gaussian-core lower bound labelled not an estimate); writes sign rates for `species_response.py`.
- `species_response.py`: ties per-species responses into a block manifest (assemble with column-sum checks, sparse fold, a double-count check against the correction chain, blocks from sign rates).
- `survival_feeddown.py`: survival probability of nuclei through the material above the measuring layers and the first-order fragmentation feed-down, with cross-section scale derivatives and recipe steps with correction keys (no built-in cross sections).
- `stability_monitor.py`: tests a quantity over time (trends, change points and CUSUM with thresholds calibrated by toys to a declared false-alarm rate, periods out of tolerance, proposed calibration era boundaries that are never written into a spec; statistics in `core/stats/change_point.py`).
- `check_geant4_study.py`: spec completeness and the sourced rule table `assets/geant4-physics-rules.json`, run records against the spec, the convergence gate, model variations, and the `unvalidated` study record.
- `geant4_benchmarks.py`: compares layered-slab Geant4 outputs with independent references (Bethe, PDG Delta_p, PSTAR range; sanity: Landau width, Highland, shower maximum) with negative controls at the claimed detection limit. Both Geant4 tools read the files `adapters/geant4` writes and never import it (`references/geant4-study-protocol.md`).
- `evaluate_design.py`: design evaluations from the tool contracts; derives the design report through `contracts/design.py` (`run`, `budget`, `plan`, `report`, and `search` with `expand --search` for automated candidate generation at F1; see the system design workflow reference).
- `design_estimates.py`: budget sums, straight-line acceptance of coaxial apertures, rejection from a separation power.
- `frontend_response.py`: front-end relations; optimal-filter weights of a sampled pulse with correlated and pileup noise (phase and baseline constraints, joint amplitude-time errors); hit efficiency of a Landau, Gaussian or tabulated signal against the noise occupancy (the operating window; for one threshold, also in noise units, the `noise-digitization` numbers of the Geant4 adapter's simreco); a seeded synthetic sampled readout reconstructed by those estimators with closure against the analytic prediction (`waveform-toy`, `status_label` synthetic); the binomial S-curve fit and scan design (`s-curve`) and the threshold dispersion after trim (`threshold-trim`).
- Other helpers: `calorimeter_resolution.py`, `cherenkov_angle.py`, `detector_atlas.py`, `multiple_scattering.py`, `pid_separation_power.py`, `pileup_reweight.py`, `toy_spectrometer.py`, `tracker_resolution.py`, `xmax_gaisser_hillas.py`, `extract_names.py`.
- Ten scripts have tool contracts in `contracts/tool_contracts/` (`frontend_response.json` with one operation per subcommand; six with design blocks).
- Particle masses come from the caller or the primary-source table, never from a built-in constant presented as a measurement.

## Setup requirements

- Python 3.13 or newer.
- Standard library first.
- NumPy: `toy_spectrometer.py` (exit 3 without it).
- Geant4 through `adapters/geant4`: produces the run files the Geant4 checkers read; `evaluate_design.py search` with `budget.geant4 > 0` also needs it (with `--geant4-work DIR` and `HEP_GEANT4_CONFIG`).
- OTSO through `<plugin root>/adapters/geomagnetic-backtracing/assets/otso_cutoff.py`: optional, installed separately (GPL-3.0, never bundled).
- Environment variables:
  - `HEP_GEANT4_CONFIG`: required by `evaluate_design.py search` when `budget.geant4 > 0`; a JSON file naming `element_sim`, `simreco` and `build_record`.
  - `SOURCE_DATE_EPOCH`: when set, the created date of `evaluate_design.py` envelopes (reproducible reruns); else today.

## Operational constraints

- Never invents detector facts; detector specifics come from an experiment profile, the user, the sourced detector atlas, or are `unknown`.
- Inference on top of a response belongs to hep-statistics; the skill does not unfold or fit.
- Every response declares matrix orientation, normalization convention, where inefficiency and acceptance live, underflow/overflow handling, included corrections and intended use (`forward_folding`, `unfolding`, `parametric_fit`); a correction inside the matrix is never applied again outside it.
- Truth and reco variables are named with units; a stated conversion when they differ.
- Stops when the inputs cannot determine the answer (a mean and a width do not determine a migration matrix or its tails); offers a parametrized response only labelled as an assumption.
- Efficiencies are conditional probabilities with a named denominator; non-Gaussian tails are measured, not assumed.
- Calibration toward the expected signal outcome is flagged; conditions are time-dependent until shown otherwise.
- A passing validator shows self-consistency under declared metadata, not physical validity; a successful script run is a software check, not scientific validity.
- Profiles are read only through the context-resolution steps; no experiment facts are embedded; durable results are JSON artifacts in `artifacts_dir`, never inside the plugin.
- [SKILL.md](SKILL.md) is the authoritative statement of what the skill owns, never does, and its invariants.

## Validation

- `tests/skills/hep_detector/`: 36 test modules (the scripts, their validity-range guards, the front-end electronics script (relations in `test_frontend_response.py`; sampled waveforms, the Landau distribution, hit efficiency, the waveform toy, S-curves and trim in `test_frontend_waveforms.py`), reference values, the audit regression suite, a link check of every reference, design evaluation and search, Geant4 checks).
- `tests/contracts/test_response_contract.py`: the response contract.
- Examples under the plugin's `examples/`: `detector-resolution` and `recasting`.
- What is and is not validated: `docs/capability-matrix.md`; the evidence: `VALIDATION.md`.

## Example requests

<!-- example -->
- "AMS-02 RICH velocity resolution vs charge" (this skill with the `experiment:ams-02` subsystem module only).
- "Parametrized muon efficiency for recasting a published search" (this skill, then hep-statistics).
- "Simulate a silicon detector with Geant4 for me" (ask for the study spec first; `examples/01-geant4-elicitation.md`).
<!-- /example -->
