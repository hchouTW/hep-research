<!-- example: experiment-specific illustration -->
# Compose an AMS-02 Antiproton/Proton Ratio Worked-Pipeline Script

> Snapshot note (2026-10-01): the repository facts below were verified on 2026-09-12. The AMS-02 case study is now `hep-analysis/references/38-ams02-case-study.md` (it was numbered 40; paths here are updated), and `hep-analysis/examples/` was removed on 2026-09-25, so the last Open Question about a matching example no longer has a home in this repository.

## Background

The user request was: "Create a task for an antiproton analysis in the AMS
experiment." `hep-analysis/references/38-ams02-case-study.md`'s "Rare-species
measurement pattern" section documents the antiproton/proton ratio as
AMS-02's canonical measurement structure: a ratio of two independent yields
that share (approximately) the same acceptance, so a large part of the
acceptance/exposure systematic an absolute flux measurement cannot avoid is
cancelled; the background for the rarer species is the far more abundant one
mis-identified, so the residual contamination must be modeled and subtracted
rather than assumed negligible.

Unlike the CMS/Higgs situation (see
[cms-higgs-analysis-task.md](cms-higgs-analysis-task.md)), this repository
already ships real, working building blocks for this exact pattern:
`hep-analysis/scripts/geomagnetic_cutoff.py`,
`orbit_averaged_geomagnetic_cutoff.py`, `solar_modulation_force_field.py`,
`particle_ratio_with_uncertainty.py`, and `cosmic_ray_flux.py` are all
standard-library-only, independently runnable, and individually unit-tested
in `tests/test_ams02.py` against synthetic data. What does not exist -
confirmed by inspecting every file in `hep-analysis/scripts/` and every test
class in `tests/test_ams02.py` - is any script or test that composes more
than one of them together into a single worked antiproton/proton-ratio
pipeline. This task closes that specific, narrow gap using only what already
exists, and - unlike the RICH-reconstruction or CMS-Higgs examples in this
same directory - is fully completable inside `agentic-ai-skills` itself,
because it needs no real flight data, only the synthetic-input convention
this skill's own tests already use.

## Objective

Add one new standard-library-only Python script,
`hep-analysis/scripts/ams02_antiproton_ratio_pipeline.py`, that composes the
five existing building-block scripts' public functions into a single worked
example - given synthetic per-event/per-bin inputs, it (1) evaluates whether
a stated rigidity clears the orbit-averaged geomagnetic cutoff for a stated
ISS-like orbital inclination, (2) applies the solar-modulation force-field
correction between a stated modulation potential and the local interstellar
spectrum, (3) computes the antiproton/proton yield ratio with propagated
uncertainty for a stated correlation, and (4) reports the corresponding
differential flux with its exact Poisson interval - printing one
consolidated JSON result - together with corresponding unit tests added to
`tests/test_ams02.py`.

## Scope

### In Scope

- A new script, `hep-analysis/scripts/ams02_antiproton_ratio_pipeline.py`,
  that imports and calls (never reimplements) the existing functions:
  `stormer_cutoff_gv` / `orbit_cutoff_profile`, `modulate` / `demodulate` /
  `power_law_lis`, `ratio_and_fraction`, and `flux_from_counts` /
  `poisson_interval`.
- A CLI built with `argparse`, following the existing five scripts'
  conventions (`--flag` options, `json.dumps(..., indent=2)` output, a
  module docstring with Purpose / What it does / Usage notes / `Run:`
  sections).
- A new test class in `tests/test_ams02.py` covering: an event below the
  orbit's minimum cutoff is excluded before the ratio/flux stages run; the
  pipeline's ratio and flux numbers match calling the underlying functions
  directly with the same inputs; and the CLI's JSON output round-trips
  through `json.loads`.
- Updating `references/38-ams02-case-study.md`'s "Rare-species measurement
  pattern" section with a cross-reference to the new script, if confirmed
  during Technical Approach step 1 that no such cross-reference already
  exists.

### Out of Scope

- Fetching, downloading, or referencing real AMS-02 flight data - this task
  uses only synthetic inputs, exactly like every existing script and test in
  this repository's `hep-analysis` skill.
- Modifying any of the five existing building-block scripts' public function
  signatures - the new script must compose them as-is; if a signature
  genuinely needs to change to support composition, that is a separate,
  escalated decision, not made silently here.
- Any change to the RICH/TRD/TOF/ECAL subsystem descriptions elsewhere in
  the case-study reference - this task is about the statistical/pipeline
  layer only.

## Repository Context

Verified by direct inspection of `agentic-ai-skills` on 2026-09-12:

- `hep-analysis/references/38-ams02-case-study.md`'s "Rare-species
  measurement pattern" section documents the exact three-step pattern this
  pipeline implements (ratio of two yields sharing acceptance; background is
  the abundant species mis-identified; null results reported as upper
  limits) - confirmed by direct read.
- `hep-analysis/scripts/geomagnetic_cutoff.py` (`stormer_cutoff_gv`),
  `orbit_averaged_geomagnetic_cutoff.py` (`orbit_cutoff_profile`),
  `solar_modulation_force_field.py` (`modulate`, `demodulate`,
  `power_law_lis`), `particle_ratio_with_uncertainty.py`
  (`ratio_and_fraction`), and `cosmic_ray_flux.py` (`flux_from_counts`,
  `poisson_interval`) all exist, are standard-library only, and are
  individually unit-tested in `tests/test_ams02.py` - confirmed by direct
  read of each script and of `tests/test_ams02.py`'s import block and its
  four per-script test classes (`OrbitAveragedCutoffTests`,
  `SolarModulationForceFieldTests`, `ParticleRatioTests`,
  `CosmicRayFluxTests`).
- No script or test anywhere in this repository composes more than one of
  these five scripts together - confirmed by inspecting every file in
  `hep-analysis/scripts/` and every test class in `tests/test_ams02.py`;
  each is exercised strictly in isolation today.
- `tests/test_ams02.py`'s own module docstring states it "Uses synthetic
  data and standard library only; no experiment files are needed" -
  confirmed by direct read; this is the existing convention the new script
  and its tests must follow, not a constraint invented for this task.
- `hep-analysis/VALIDATION.md` documents a prior pass that grepped this
  skill's references, scripts, and assets for real experiment names
  specifically to confirm no synthetic value is presented as a real
  detector's measurement - the same discipline applies to any illustrative
  numbers this new script's docstring or usage examples use.

## Technical Approach

1. Re-read the five existing scripts' public functions and their exact call
   signatures and return-dict keys (e.g. `orbit_cutoff_profile`'s
   `min_cutoff_gv` / `max_cutoff_gv` / `time_weighted_mean_cutoff_gv`) to
   compose them without guessing at an interface; while doing so, confirm
   whether `references/38-ams02-case-study.md` already cross-references any
   planned composed pipeline (Scope's conditional documentation update).
2. Design the pipeline script's single consolidated output schema - one JSON
   object with clearly-named nested sections per stage (`cutoff`,
   `modulation`, `ratio`, `flux`) - rather than four independent print
   statements.
3. Implement `hep-analysis/scripts/ams02_antiproton_ratio_pipeline.py`,
   importing each function directly (mirroring `tests/test_ams02.py`'s own
   `sys.path.insert(0, str(ROOT / 'scripts'))` import pattern) rather than
   shelling out to the other scripts' CLIs.
4. Add an `AntiprotonRatioPipelineTests` class to `tests/test_ams02.py`
   covering: a below-cutoff event is flagged and excluded before the
   ratio/flux stages run; the pipeline's ratio/flux numbers match calling
   the underlying functions directly with the same inputs (no silent
   re-derivation); and the CLI's JSON output round-trips through
   `json.loads`.
5. Write the module docstring with the same Purpose / What it does / Usage
   notes / `Run:` sections the other five scripts use, cross-referencing
   `references/38-ams02-case-study.md`'s "Rare-species measurement pattern"
   section explicitly.
6. Run `python3 -m unittest discover -s tests -v` from `hep-analysis/` and
   confirm all existing tests plus the new ones pass.

## Deliverables

- `hep-analysis/scripts/ams02_antiproton_ratio_pipeline.py`, a new
  standard-library-only script.
- A new `AntiprotonRatioPipelineTests` class in `tests/test_ams02.py`.
- An updated module docstring cross-referencing
  `references/38-ams02-case-study.md`.
- A short note (in the script's docstring, or a new
  `hep-analysis/VALIDATION.md` entry) stating this is the first script in
  this repository to compose more than one of the five existing AMS-02
  building blocks.

## Acceptance Criteria

- `python3 hep-analysis/scripts/ams02_antiproton_ratio_pipeline.py
  <documented example args>` runs without error and prints one JSON object
  containing `cutoff`, `modulation`, `ratio`, and `flux` sections.
- An event below the orbit-averaged cutoff is excluded from the ratio/flux
  stages, not silently included.
- The pipeline's ratio and flux numbers are identical (within floating-point
  tolerance) to calling `ratio_and_fraction` and `flux_from_counts` directly
  with the same inputs - the new script must not reimplement their math.
- `python3 -m unittest discover -s tests -v`, run from `hep-analysis/`,
  passes, including both the pre-existing tests and the new pipeline test
  class, with no regression to the existing four test classes.
- The new script's docstring follows the existing five scripts'
  Purpose / What it does / Usage notes / `Run:` structure and explicitly
  links to `references/38-ams02-case-study.md`.
- No real AMS-02 flight data, calibration constant, or unpublished number is
  introduced - only synthetic or explicitly-cited-published inputs, per this
  repository's existing sourcing discipline.

## Validation

- Re-run `python3 -m unittest discover -s tests -v` from `hep-analysis/` and
  confirm the full suite (existing plus new) passes.
- Manually re-run the documented example CLI invocation and confirm the
  JSON output is well-formed and internally consistent (the ratio's implied
  fraction matches `fraction = n1/(n1+n2)` independently recomputed by hand
  for the example numbers).
- Confirm, via `git diff` or equivalent, that no existing script's public
  function signature was modified.

## Open Questions

- Should the pipeline script also support the `--demodulate`
  (measured-flux-to-LIS) direction of `solar_modulation_force_field.py`, or
  only `--modulate` (LIS-to-measured), or both? **TBD** - not specified in
  the request.
- Should the new script live at
  `hep-analysis/scripts/ams02_antiproton_ratio_pipeline.py` as proposed, or
  under a new `hep-analysis/scripts/pipelines/` subdirectory if more
  composed, multi-script examples are expected later? **Open Question** - no
  such subdirectory convention exists in this repository today.
- Is a corresponding worked example (in the former `hep-analysis/examples/`, which no longer exists: archetype examples were removed on 2026-09-25) (one of the
  numbered worked examples, e.g. an Execution-Trajectory or Gated-Pipeline
  archetype demonstrating this exact composition) also wanted alongside the
  script, or is the script-plus-tests deliverable sufficient on its own?
  **Requires Confirmation** - that would be a separate task-authoring
  request per `references/example-authoring.md`, not assumed here.
- What illustrative rigidity, potential, yield, and exposure values should
  the documented example use? **TBD** - none were supplied in the request;
  the implementer should pick physically plausible, clearly-labeled-
  illustrative values (e.g. matching the existing scripts' own `Run:`
  docstring examples) rather than inventing values that could be mistaken
  for a real AMS-02 measurement.

## References

- `hep-analysis/references/38-ams02-case-study.md` - the "Rare-species
  measurement pattern" section this pipeline implements.
- `hep-analysis/scripts/geomagnetic_cutoff.py`,
  `orbit_averaged_geomagnetic_cutoff.py`, `solar_modulation_force_field.py`,
  `particle_ratio_with_uncertainty.py`, `cosmic_ray_flux.py` - the five
  existing building blocks being composed.
- `hep-analysis/tests/test_ams02.py` - the existing per-script test suite
  this task extends rather than duplicates.
- `hep-analysis/VALIDATION.md` - the prior validation discipline on
  avoiding real-value/synthetic-value confusion, which this task's
  Acceptance Criteria extend to the new script.
<!-- /example -->
