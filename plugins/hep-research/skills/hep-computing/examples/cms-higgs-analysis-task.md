# Design a CMS Higgs Boson Significance-Measurement Workflow

> Snapshot note (2026-10-01): the environment statements below (`pyhf`, `ROOT`/PyROOT and Combine not usable) describe the machine checked on 2026-09-12. Since then `hep-analysis` has run PyROOT under a Homebrew Python, and pyhf and Combine from scratch environments, so re-check them before relying on them.

## Background

The user request was: "Create a task for a CMS experiment Higgs boson
analysis." `hep-analysis/references/13-sources.md` and
`hep-analysis/references/09-statistical-tools.md` both point to CMS's
official Combine tool (`HiggsAnalysis-CombinedLimit`) as the standard
workspace/limit-setting tool, and `hep-analysis/assets/` ships two generic,
channel-agnostic statistical-model templates
(`combine_datacard_template.txt`, `pyhf-counting.json`). But
`agentic-ai-skills` is a collection of *agent skill guidance packages*, not a
CMS analysis codebase: there is no CMS dataset, Monte Carlo sample,
trigger/reconstruction code, or Higgs-channel-specific selection anywhere in
it. `hep-analysis/VALIDATION.md` documents that this was a deliberate
choice - a prior validation pass explicitly grepped the skill's references,
scripts, and assets for real experiment names "to confirm the
technology-organized, experiment-agnostic framing holds and that no
synthetic value is presented as a real detector's measurement." This task is
written against that reality, the same way the shipped
[performance-task.md](performance-task.md) RICH-reconstruction example is.

The one place this repository already carries an accurate, real CMS-Higgs
fact is bibliographic, not analytical: `academic-papers/references/
literature-review.md` uses the actual 2012 CMS Higgs discovery paper
(INSPIRE key `Chatrchyan:2012xdj`, "125.3 +/- 0.4 +/- 0.5 GeV", alongside
ATLAS's `Aad:2012tfa`) as an example row for its literature-matrix
formatting tool - a correctly-labeled citation example, not analysis code or
data, and in a different skill (`academic-papers`) from the one this task
targets.

## Objective

Produce a written statistical-analysis design - not a runnable physics
result - for measuring the signal strength / significance of a stated CMS
Higgs boson channel, by adapting this repository's generic Combine-datacard
and pyhf-JSON templates into a fully filled, channel-specific statistical
model, following `hep-analysis`'s likelihood/inference conventions, and
explicitly separating what this repository's guidance can specify today from
the real CMS-specific inputs (actual data, Monte Carlo, calibration,
systematics) that only a genuine CMS analysis environment can supply.

## Scope

### In Scope

- Select one concrete, publicly documented CMS Higgs channel to ground the
  design in (e.g. H→γγ or H→ZZ→4ℓ), or default to H→γγ per Technical
  Approach step 1 if none is supplied.
- Fill `assets/combine_datacard_template.txt` completely for that channel -
  channel name, observation, process names/ids/rates, luminosity nuisance,
  at least one rate and one shape nuisance - with illustrative numbers
  explicitly labeled as illustrative, not claimed to be real CMS numbers.
- Independently fill `assets/pyhf-counting.json`'s channel/sample/modifier
  structure for the same channel, so the Combine-format and pyhf-format
  artifacts describe the same statistical model.
- Write the statistical-treatment section (POI, nuisance parameters, test
  statistic choice, one-/two-sided convention) per
  `references/08-inference.md` and `references/09-statistical-tools.md`.
- Document, as an explicit checklist, exactly which additional CMS-specific
  inputs a real execution of this datacard/model would require and that are
  not present in this repository.
- If the execution environment can be confirmed to have `pyhf` installed,
  run the filled JSON through it as a structural sanity check (workspace
  loads, fit converges on the illustrative numbers) - not a physics result.

### Out of Scope

- Producing an actual CMS physics result (a real significance or exclusion
  limit) - impossible without real CMS data, Monte Carlo, and calibration,
  none of which exists in this repository.
- Selecting or replicating the CMS-approved production software stack
  (CMSSW) or official calibration - out of scope; this task only produces
  the statistical-model design layer `hep-analysis`'s guidance covers.
- Building or installing the `combine` binary itself - its absence is
  recorded as an Open Question, not resolved by this task.

## Repository Context

Verified by direct inspection of `agentic-ai-skills` on 2026-09-12:

- `hep-analysis/references/13-sources.md` and
  `hep-analysis/references/09-statistical-tools.md` both link to CMS's
  official Combine documentation
  (`https://cms-analysis.github.io/HiggsAnalysis-CombinedLimit/latest/`) as
  the reference tool for workspace/limit-setting workflows - confirmed by
  direct read.
- `hep-analysis/assets/combine_datacard_template.txt` is a generic,
  channel-agnostic Combine counting-datacard template with unfilled
  `{...}`-style placeholders (`imax`/`jmax`/`kmax`, `bin`/`process`/`rate`
  lines, a `lumi_{year} lnN` row) - confirmed by direct read.
- `hep-analysis/assets/pyhf-counting.json` is a generic two-sample
  (signal/background) pyhf workspace with a placeholder channel named
  `"synthetic_region"` - confirmed by direct read; not specific to any CMS
  channel.
- `hep-analysis/references/07-likelihood-fitting.md`, `08-inference.md`, and
  `09-statistical-tools.md` cover binned-likelihood construction,
  profile-likelihood test statistics, and CLs conventions generically
  (collider-agnostic), not tied to CMS or any specific channel - confirmed
  by direct read.
- A repository-wide case-insensitive search for "CMS" and "Higgs" (across
  `.md`, `.py`, `.txt`, `.json`, `.cpp`, `.yaml` files) returns only: the two
  Combine-documentation links above, one prompt-example mention in
  `academic-papers/SKILL.md` ("a PRL letter on the Higgs mass measurement",
  an illustrative prompt, not content), the `Chatrchyan:2012xdj` citation
  example noted in Background, and `hep-analysis/VALIDATION.md`'s own note
  that it grepped for "CMS" among other experiment names during a prior
  validation pass. No CMS-specific dataset, channel selection, or prior
  Higgs-analysis task exists anywhere in this repository.
- This repository ships no Python dependency manifest (no `requirements.txt`
  or `pyproject.toml` was found anywhere in the tree), so `pyhf` is not a
  managed dependency here; whether it is installed depends entirely on the
  execution environment, not the repository.
- In the environment this task document was authored in specifically:
  `python3 -c "import pyhf"` fails with `ModuleNotFoundError`, `python3 -c
  "import ROOT"` fails with a `cppyy` ABI-mismatch import error even though a
  `root` binary (ROOT 6.38.04) is present on `PATH`, and no `combine` binary
  is on `PATH`. This is a fact about that one execution environment at that
  moment, not a guaranteed fact about whatever environment this task is
  eventually run in - re-verify before relying on it.

## Technical Approach

1. Confirm which CMS Higgs channel to ground the design in (see Open
   Questions); if none is supplied, default to H→γγ as the most
   datacard-friendly counting-experiment example and state that default
   explicitly in the deliverable.
2. Re-read `references/07-likelihood-fitting.md`, `08-inference.md`, and
   `09-statistical-tools.md` to fix the statistical treatment (POI = signal
   strength μ, nuisance parameters, CLs vs. discovery q0, one-/two-sided
   convention) before touching either template.
3. Fill `assets/combine_datacard_template.txt` completely for the chosen
   channel, replacing every `{...}` placeholder with an explicitly
   illustrative value.
4. Independently fill `assets/pyhf-counting.json`'s structure to describe
   the same channel, process names, and rates as step 3's datacard.
5. Verify the current execution environment's actual ability to run either
   artifact (is `pyhf` installed? is a working `ROOT`/`PyROOT`/`combine`
   toolchain available?) before attempting execution; if unavailable,
   document the gap rather than silently skipping validation.
6. If `pyhf` is available, run it against the filled JSON as a structural
   sanity check only - confirms the workspace is well-formed and the fit
   converges on the illustrative numbers, not that the physics is correct.
7. Write the "what a real CMS analysis would still need" checklist called
   out in Scope.

## Deliverables

- A filled, placeholder-free `combine_datacard_template.txt` derivative for
  the chosen channel.
- A filled, placeholder-free pyhf JSON derivative of `pyhf-counting.json`
  for the same channel.
- A written statistical-treatment section citing the specific reference
  sections used.
- A checklist of CMS-specific inputs required for a real execution,
  explicitly marked as not present in this repository.
- If `pyhf` was runnable in the execution environment: the structural
  sanity-check output; if not: an explicit statement that this step could
  not be performed, and why.

## Acceptance Criteria

- The filled datacard and pyhf JSON contain zero remaining `{...}`-style
  placeholders.
- Both filled artifacts describe the same channel, the same process names,
  and consistent rates.
- The statistical-treatment write-up cites specific sections of
  `references/07-likelihood-fitting.md`, `08-inference.md`, and
  `09-statistical-tools.md` rather than restating generic material
  unsourced.
- The "what a real analysis would still need" checklist explicitly
  separates what this repository's guidance already specifies from what
  only a genuine CMS analysis environment can supply - it does not claim
  the deliverable is a real physics result.
- If `pyhf` could not be run in the available environment, that fact and
  the reason are stated in the deliverable rather than the structural-check
  step being silently omitted.
- Every illustrative number used is explicitly labeled as illustrative, not
  attributed to any real CMS measurement.

## Validation

- Re-run any structural sanity check (pyhf workspace load / fit) and
  confirm the same result, if `pyhf` is available.
- Manual review confirms no placeholder text remains in either filled
  template.
- Manual review confirms every numeric value in the deliverable is labeled
  illustrative vs. sourced, with no unlabeled claim of a real CMS result.

## Open Questions

- Which CMS Higgs channel should this design target (H→γγ, H→ZZ→4ℓ, H→WW,
  ttH, VBF-tagged, or another)? **TBD** - no channel was named in the
  request, and this repository has no existing Higgs-channel code to infer
  one from.
- Is the requester's execution environment expected to have `pyhf`
  installed, or is the structural sanity-check step out of scope entirely?
  **Requires Confirmation** - not installed in the environment this task was
  authored in, and this repository manages no Python dependencies of its
  own to fall back on.
- Is a working `combine` binary or a `ROOT`/`PyROOT` environment expected to
  be available for any later, follow-on execution of the Combine-format
  datacard, or does this task's scope stop at the statistical-model design
  layer? **TBD.**
- Should illustrative signal/background rates be chosen to loosely resemble
  a published CMS result (with an explicit citation) for realism, or kept
  as arbitrary round numbers to avoid any appearance of reproducing a real
  measurement? **Open Question.**

## References

- `hep-analysis/references/07-likelihood-fitting.md`, `08-inference.md`,
  `09-statistical-tools.md` - statistical-treatment source material.
- `hep-analysis/references/13-sources.md` - the Combine
  official-documentation citation.
- `hep-analysis/assets/combine_datacard_template.txt` and
  `assets/pyhf-counting.json` - the two generic templates this task fills
  in.
- `hep-analysis/VALIDATION.md` - the prior validation pass explaining why
  this skill carries no real-experiment-attributed values, which motivates
  this task's illustrative-labeling requirement.
- `academic-papers/references/literature-review.md` - the one existing,
  correctly-labeled real CMS-Higgs bibliographic fact in this repository
  (`Chatrchyan:2012xdj`), noted in Background for completeness; not
  otherwise used by this task.
- No prior CMS-analysis or Higgs-analysis task, dataset, or implementation
  file exists in this repository to reference.
