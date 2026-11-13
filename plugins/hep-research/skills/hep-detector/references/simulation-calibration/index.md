# Simulator calibration: detector-type specializations

The specialization interface of the simulator calibration workflow (Part B,
`docs/dev/simulator-calibration/simulator-calibration-v7.37.4-clean-en.md`, §11.1, §12, §13) for eight detector
types. Each page gives the eight items a detector type must provide (§11.1) and a node-binding example (§11.4) that
the existing generic layer accepts unchanged. The engine, gates and scripts are hep-statistics' (`calib_*.py`); this
folder only describes detector types. Experiment-specific content (control samples, conditions, thresholds, model
identities) belongs to an experiment instance (§11.2), never here.

## Contents

| Type | Page | Example (`assets/simulation-calibration/`) |
|---|---|---|
| Electromagnetic calorimeter | [ECAL](ecal.md) | `ecal.binding.example.json` |
| Hadronic calorimeter | [HCAL](hcal.md) | `hcal.binding.example.json` |
| Ring-imaging Cherenkov | [RICH](rich.md) | `rich.binding.example.json` |
| Detection of internally reflected Cherenkov light | [DIRC](dirc.md) | `dirc.binding.example.json` |
| Transition-radiation detector | [TRD](trd.md) | `trd.binding.example.json` |
| Silicon or gas tracker | [Tracker](tracker.md) | `tracker.binding.example.json` |
| Time of flight | [TOF](tof.md) | `tof.binding.example.json` |
| Muon detector | [μ detector](muon-detector.md) | `muon.binding.example.json` |

## Rules that hold on every page

- Source of each mapping: Part B §3.1 (derivation basis), §3.2 (mechanisms), §3.5 (degeneracy modes), §11.4 (g4sim
  binding) and the type's §12 row. A physics statement without such a source is marked *Inferred*.
- Item 7 is advisory (approval A21, §19-1): the table lists f, C, ℓ with a verified citation per value, or "no
  literature value". A contract still declares f, C, ℓ (§5.4), and `hep-statistics/scripts/calib_contract.py check` never reads the table.
  Correlation lengths come from physics and are never chosen to make G6 pass (§5.4).
- Item 8 is advisory (A21, §19-4): alternative hypotheses are simulation settings, never parameter shifts (§9.4), each
  with the observable expected to see it. A contract still declares at least one when validation is not `none`
  (§5.2 clause 10 item 2, D32); nothing here is applied automatically.
- Degeneracy modes are diagnostic hints (§3.5); identifiability is decided only by P3 and G5.

## Node-binding examples

Each example holds a contract fragment (`contract_fragment`: simulator, source, stage graph, parameters with their
g4sim field bindings, references, models, `validation_alternatives`) and a plan with the node binding of §11.4
Table 1. The experiment instance completes the contract: observables, event samples, data releases, the five model
identity items of §5.1 and the V_model kernel. Bounds in the examples are placeholders, not detector facts.

`tests/core/test_calibration_specialization.py` completes each fragment with the synthetic fixture of
`tests/core/calibration_fixtures.py` and runs `hep-statistics/scripts/calib_contract.py check`, `hep-statistics/scripts/calib_chain.py p4` and
`hep-statistics/scripts/calib_chain.py candidates` unchanged (the §12 acceptance criterion: a new type must not need a change of the
generic layer). The candidate methods each page lists are the ones that test asserts.

## Item 7: literature search record

Searched 2026-11-13 through the hep-citations route (INSPIRE-HEP literature API, arXiv API), read level
`metadata-only` except where an abstract was opened. Queries: title "model discrepancy" (2 hits; abstract of the
second opened: a generic hybrid-model method, no detector values); `"model discrepancy"` in arXiv abstracts with
`physics.ins-det` (1 hit) and `hep-ex` (4 hits; titles on neutrino cross sections, cosmic rays and an open-data
search, none a detector-simulation kernel); "Gaussian process" with each of electromagnetic calorimeter, hadronic
calorimeter, RICH, DIRC, transition radiation, silicon tracker, time-of-flight, muon chamber and "simulation" in
INSPIRE abstracts (1 hit in total, on electron reconstruction by its title; not opened); Kennedy–O'Hagan, "Bayesian calibration"
with detector, and correlation length with data–simulation and calorimeter (no relevant hit). No published value of
a model-discrepancy kernel amplitude, cross-group correlation or correlation length was found for any of the eight
types, so every item-7 table reads "no literature value". A later search that finds one adds the value with its
identifier, the passage and the read level.

## g4sim binding limits met by the examples

These are limits of g4sim or of its binding (§11.4), not of the generic layer: each example states which §12
parameters it could not bind and why.

- Hashed tables (`charge_sharing`, `drift_table`) carry no stage parameter value, so Lorentz angle, diffusion,
  charge sharing, cluster size and the r–t relation have no Table 2 row (Tracker, TRD, μ detector).
- No gas-avalanche stage kind: gas gain is bound to the `sensor` stage gain (*Inferred* mapping; TRD, μ detector).
- No field for TTS, the effective light speed or the scintillation emission time (TOF, DIRC); no SiPM saturation
  stage (HCAL); no single-photoelectron injection before response stage 3 (ECAL).
- Misalignment through `alignment-overlay/1` has no recorded run yet (D83 (7)); the RICH mirror is bound as a
  detector-spec parameter instead.
- `chain.binding_row` classes every run-card physics field other than the reference list, EM option and
  constructor, extra constructors and fast simulation as the continuous "geometry" row, including `/physics/pai`,
  `/physics/xtr` and the optical process switches, which are discrete. The examples therefore enter the PAI choice
  as a discrete model and bind no θ there.
