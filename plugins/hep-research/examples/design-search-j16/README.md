# J16: automated candidate generation on Examples A and B

**SYNTHETIC.** J16 runs the search of `evaluate_design.py` (the D2 candidate generator of
`skills/hep-detector/references/system-design-workflow.md`) on two existing design examples. It demonstrates the
process, not new detector designs: the finalists are candidates to evaluate, every verdict comes from
`contracts/design.py`, search values are not evaluations, and no optimum is claimed.

- **Example A** (`examples/design-space-spectrometer`, an AMS-like space spectrometer): base `cand-S`. The search
  varies the number of tracker planes (4 to 9), their positions over 0 to 3 m and the field (0.1 to 0.5 T), with
  an optional TOF slot. Objectives: `REQ-TRK-001` (momentum-resolution core of 1 TV protons) and `CON-MASS-001`.
  Constraint: `REQ-CC-001`. Three seed proposals with their physics reasons: the longest lever arm with five
  planes, planes clustered at the ends and the centre, and the base layout.
- **Example B** (`examples/design-collider-tracker`, a collider tracker and ECAL): base `cand-B`. The search varies
  the plane count (8 to 13) and positions over 0.1 to 1.1 m, the field (1 to 2 T) and the ECAL stochastic term.
  Objectives: `REQ-TRK-001`, `REQ-ECAL-001` and `CON-MASS-001`. The role rule caps the field at 2 T, so Example B's
  3.8 T `cand-A` lies outside the search space. Its only seed proposal is the base layout: the workflow asks the
  designer for two to six seed topologies (the search-spec schema does not enforce it), and Example B shows the
  search without them.

Each search is seeded NSGA-II on F1 search values (1200 evaluations), started from Sobol designs and the seed
proposals (three for Example A, only the base layout for Example B). The finalists, at most three of distinct
topologies, are fixed before any official evaluation. They are expanded (`expand --search`) and evaluated with
`run` and `budget`. Example B's four requirements without an evaluator are recorded as `capability.unavailable` for
the finalists. Then `report` and `search --diagnose` run.

## What the searches give

| | Example A | Example B |
|---|---|---|
| Search size | 1109 distinct designs, 12 topologies | 1121 distinct designs, 6 topologies |
| Search front (non-binding) | 88 designs | 141 designs |
| Finalists | 7, 9 (with TOF) and 9 planes | 10, 8 and 13 planes |
| Consistency with `run` | identical (relative difference 0) | identical |

The values below are F1 search values (optimistic bounds), not performance claims:

| Finalist | Resolution (F1) | Other | Mass (F1) | Verdicts (`design.py`) |
|---|---|---|---|---|
| A `cand-F937`, 7 planes, 0.10 T | 0.260 | charge confusion 6e-5 | 1411 kg | `CON-MASS-001` pass; `REQ-TRK-001` inconclusive (`fidelity.insufficient`, see below); `REQ-CC-001` inconclusive (`bound.direction`) |
| A `cand-F961`, 9 planes, TOF | 0.062 | charge confusion < 1e-50 | 5089 kg | `CON-MASS-001` inconclusive (`margin.within_uncertainty`); resolution and charge confusion `bound.direction` |
| A `cand-F1047`, 9 planes | 0.046 | charge confusion < 1e-50 | 6925 kg | `CON-MASS-001` fail (`estimate.decides`, limit 3000 kg); resolution and charge confusion `bound.direction` |
| B `cand-F959`, 10 planes | 0.024 | ECAL 0.0070 | 34867 kg | `REQ-TRK-001` and `REQ-ECAL-001` inconclusive (`bound.direction`); `CON-MASS-001` inconclusive (`margin.within_uncertainty`: 39 % over the 25000 kg limit, within the F1 mass uncertainty) |
| B `cand-F1037`, 8 planes | 0.062 | ECAL 0.0070 | 21011 kg | `REQ-TRK-001` fail (`bound.excludes`, target 0.03); `REQ-ECAL-001` inconclusive (`bound.direction`); `CON-MASS-001` inconclusive (`margin.within_uncertainty`) |
| B `cand-F1061`, 13 planes | 0.040 | ECAL 0.0070 | 24506 kg | `REQ-TRK-001` fail (`bound.excludes`); `REQ-ECAL-001` inconclusive (`bound.direction`); `CON-MASS-001` inconclusive (`margin.within_uncertainty`) |

In Example B, `REQ-TRK-001` is an objective, not a constraint, so the search front keeps lighter designs that miss
the resolution target. `design.py` excludes them; the search does not. The four `capability.unavailable` requirements
(hadronic resolution, trigger efficiency, pileup robustness, shower containment) stay inconclusive for every
finalist and are listed in the report. The search does not depend on which detector it designs.

Both reports refuse to rank. The equal-mass comparison basis does not hold (the finalists' masses differ beyond the
5 % tolerance), and no candidate has an expected-precision evaluation. The gates H1, H2 and H3 are flagged as missing:
only a human record clears them.

## The F4 confirmation of an Example A finalist

`live.py` ran one F4 study of the first finalist, `cand-F937`, for 1 TV protons, with J15's campaign code
(`examples/design-minimal-spectrometer/live.py`, class `Campaign3`). The study ran a 1600-event trial, then 5040 events (A1.9) for the
nominal, the cut scan and two physics-list variations, reconstructed with every tail source off, and with all four
on except for the cut scan. It ran the
benchmarks of the four conditions of the qualification path (material definition, field propagation,
reconstruction closure and the multiple-scattering reference; the reference passed its agreement test but missed its
control criterion, below), the reference being a 0.937 mm silicon slab, the planes' x/X0 of 0.01; the aluminium support upstream of the first plane (passive x/X0 0.03) is outside that reference's scope, which is
silicon only. The geometry came
from this example's realization profile (`space.realization.json`; the recorded study records its sha256). The study's own runs (trial, nominal, cut scan,
variations) are seeded from `confirmation_study_id(SEARCH-J16A, digest, figure of merit, denominator)`; the shared
verification and reference runs use the fixed ids `j16a-F937-verification` and `j16a-msref-1000gv`. This search ran at F1 only, so it has no
Geant4 seed to reuse; the rule against search seeds (CV-C2) matters when the search has Geant4 search values, while CV-C2's
seed_group clause (`design.seed_reuse`) already applies to these runs. `run.py` re-labels the
study from `recorded/` (200 kB): it reruns `label --upgrade` and then `f4 --study` on the recorded run records and
benchmark results (on the refused record `f4` still writes an F4 evaluation, which `design.py` treats as unqualified,
`fidelity.insufficient`, and `search --diagnose` lists with fidelity F4 and `f4_qualified: false`); the benchmarks themselves are not recomputed offline, because the control crossings files are not recorded.

The upgrade was **refused**. At 1 TV the reference agrees with Lynch–Dahl to +0.4 %, and both ±13 % density
controls are caught. But the −13 % control shifted the width by −8.0 %, beyond 1.1 times its detection limit of
6.4 % (each control is judged against its own limit; the gap message quotes the larger, 6.6 %): the campaign uses a
fixed control size, not one sized from the detection limit. The protocol records the miss and never reruns it; that rule is procedural: `live.py` deletes and rewrites
`recorded/` when run again, and `confirmation_study_id` has no attempt input, so rerunning the same finalist under
the same search reproduces the same seeds. A qualifying attempt needs a new search (a new id) or a changed design, with its control size declared
before its runs. The F4 evaluation (core 0.313, against 0.260 at F1) is therefore unqualified: `REQ-TRK-001` for
`cand-F937` is inconclusive with `fidelity.insufficient`. A qualified confirmation needs a new study whose control
size is declared before its runs, a step a human checks. J15 met the same limit at 100 GV.

## Not provided, and limits

- The Bayesian-optimisation backend (`adapters/design-bo/`, Ax/BoTorch) is not provided: neither environment has
  Ax or BoTorch, and an untested backend is not shipped. The search runs NSGA-II only.
- A TOF or calorimeter that the search adds has F1 parameters only (the role rules): `evaluate_design.py geometry`
  does not refuse it, but its layers are not placed in the Geant4 geometry (a TOF keeps only its time resolution as a
  geometry field, a calorimeter nothing).

## Files and usage

| File | Content |
|---|---|
| `run.py` | Offline replay: both searches, expansion, evaluations, the recorded confirmation, reports, criteria; writes `output/results.json` |
| `live.py` | The live Example A confirmation; rewrites `recorded/` without a guard, so run it only for a new study (`--work DIR`; needs Geant4 11.4.3 with `element_sim`, `simroot` and `simreco`, `HEP_GEANT4_CONFIG`) |
| `space.realization.json` | The realization profile for Example A (SYNTHETIC: uniform field, no magnet material) |
| `recorded/` | The confirmation's run records (gzip), specs, study inputs and geometry file; home paths written as `~` |
| `output/results.json` | The derived results; `output/A/` and `output/B/` are regenerated on each replay and not committed |

From the plugin root: `python3 examples/design-search-j16/run.py [--out DIR]`. The test is
`tests/examples/test_design_search_j16.py`. Evidence: VALIDATION DESIGN-SEARCH-EXAMPLES.
