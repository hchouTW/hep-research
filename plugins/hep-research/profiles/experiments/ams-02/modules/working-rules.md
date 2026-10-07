# AMS-02 Working Rules

## When to read this file

Read first whenever this profile is active: it holds the AMS-specific invariants, labels, source rule and module routing. The general workflow it describes is owned by the core skills; this file adds the AMS constraints.

This profile guides realistic AMS-02 detector and charged-cosmic-ray analysis work while separating **documented facts** (public AMS sources), **general methods** (textbook/PDG/statistics literature), **proposals** (choices you recommend for this analysis), and **unknowns** (internal AMS detail). Scope: public-domain reasoning only. AMS Collaboration internal data, notes, calibration constants, production software, conditions databases, pass names, trigger bits, good-run rules and cuts are **not available here**; never invent them, unless the user supplies them, labelled user-supplied. Access-controlled AMS-02 software and data knowledge (Offline library usage, EOS productions, ntuple kits) is not in this profile; authorized members get it from the companion profile `experiment:ams-02-private` (plugin `ams02-research`), whose statements are labelled `[Official]`, `[Analysis choice]`, `[Inferred from code]`, `[Observed]` or `[User-supplied]` and are never an AMS rule. Without it, say so; never answer those topics from memory. This profile does not replace collaboration review, blinding, or peer review. For generic ROOT/statistics/detector questions with no AMS tie, do not load this profile; the core skills answer them.

## Routing: read the minimum references

| Request type | Mode(s) | Read (in this order) |
|---|---|---|
| "How does subsystem X / observable Y work?" | 1 Concept | [detector-and-observables](subsystems/detector-and-observables.md) |
| RICH/TOF/TRD/ECAL/Tracker role in a specific species | 1 | [detector-and-observables](subsystems/detector-and-observables.md) + the species file |
| Design/review a proton, He, nuclei flux or B/C-type ratio | 2, 3 | [charged-cosmic-rays](species/charged-cosmic-rays.md), [reconstruction-and-data-quality](methods/reconstruction-and-data-quality.md), [efficiency-acceptance-backgrounds](methods/efficiency-acceptance-backgrounds.md), [calibration-mc-systematics](methods/calibration-mc-systematics.md) |
| Positron/electron flux or fraction, e/p separation | 2, 3 | [antimatter-and-leptons](species/antimatter-and-leptons.md), [efficiency-acceptance-backgrounds](methods/efficiency-acceptance-backgrounds.md), [inference-and-unfolding](methods/inference-and-unfolding.md) |
| Antiproton, antideuteron, antihelium, rare-event search | 2, 3, 6 | [antimatter-and-leptons](species/antimatter-and-leptons.md), [inference-and-unfolding](methods/inference-and-unfolding.md), [efficiency-acceptance-backgrounds](methods/efficiency-acceptance-backgrounds.md) (+ [source-policy](sources/source-policy.md) if status is asked) |
| Isotopes, deuteron/proton, Li/Be/B, mass from R and β | 1, 2 | [nuclei-and-isotopes](species/nuclei-and-isotopes.md), [detector-and-observables](subsystems/detector-and-observables.md) |
| Unfolding, response matrix, forward folding | 3, 6 | [inference-and-unfolding](methods/inference-and-unfolding.md), [efficiency-acceptance-backgrounds](methods/efficiency-acceptance-backgrounds.md) |
| Template fit / likelihood / limit / significance | 6 | [inference-and-unfolding](methods/inference-and-unfolding.md) + species file |
| Cuts, run selection, time stability, MC-data mismatch | 2, 3 | [reconstruction-and-data-quality](methods/reconstruction-and-data-quality.md), [calibration-mc-systematics](methods/calibration-mc-systematics.md) |
| Systematics list, covariance, calibration drift | 3 | [calibration-mc-systematics](methods/calibration-mc-systematics.md), [inference-and-unfolding](methods/inference-and-unfolding.md) |
| "What did AMS measure / latest result / is this paper real?" | 4, 5 | [source-policy](sources/source-policy.md), the evidence index, + species file |
| Unit conversion or quick mass-resolution estimate | 1 | [charged-cosmic-rays](species/charged-cosmic-rays.md) (Variable conversion) or [detector-and-observables](subsystems/detector-and-observables.md) (mass propagation) only; run `<plugin root>/core/kinematics/relativistic.py` for the arithmetic |
| Covariance/response/PSD problems | 3, 6 | [inference-and-unfolding](methods/inference-and-unfolding.md); run `<plugin root>/core/stats/validate_covariance.py` / `validate_response.py` on supplied matrices |
| Write a measurement brief, specification, ledger or response card; formal verdict-first review of a design | 2, 3 | [analysis-artifacts](methods/analysis-artifacts.md), then the species and topic references it points to; run `<plugin root>/profiles/experiments/ams-02/scripts/audit_analysis_spec.py` |
| Exact Poisson limit or interval numbers, zero-count bound, FC/CLs limit, seeded coverage, boundary and profile-likelihood significance and limits, finite-template effect, regularization scan, closure and pulls, response statistics, ratio-cancellation check | 6 | [statistical-diagnostics](methods/statistical-diagnostics.md) (after [inference-and-unfolding](methods/inference-and-unfolding.md) for the decision) |
| Time-resolved flux or ratio, solar cycle, periodicity, time stability of a flux result | 2, 3, 6 | [time-dependent-analysis](periods/time-dependent-analysis.md), [charged-cosmic-rays](species/charged-cosmic-rays.md), [calibration-mc-systematics](methods/calibration-mc-systematics.md) |
| Positron fraction vs flux for a model constraint | 4, 6 | [antimatter-and-leptons](species/antimatter-and-leptons.md), [inference-and-unfolding](methods/inference-and-unfolding.md) |
| Compare AMS with other experiments, find which paper holds a published measurement, retrieve compiled cosmic-ray data (CRDB at LPSC, the ASI SSDC database) | 4, 6 | [cosmic-ray-databases](sources/cosmic-ray-databases.md) + [source-policy](sources/source-policy.md); the AMS values still come from the AMS papers' claims |
| See the intended behavior on representative requests | - | [worked-examples](methods/worked-examples.md) |

Multi-mode requests load the union. "Species file" means [antimatter-and-leptons](species/antimatter-and-leptons.md) for e±/antiprotons/antinuclei, [nuclei-and-isotopes](species/nuclei-and-isotopes.md) for elements/isotopes, [charged-cosmic-rays](species/charged-cosmic-rays.md) for p/He fluxes and ratios; add a second only if the question crosses species. A simple factual question gets a short answer and loads only the one concept reference, plus the evidence index whenever an AMS number, date, or status is quoted (that is the only exception to "one reference"); do not impose the full design outline on it: answer in a few sentences, without response-chain, failure-mode or validation sections unless asked. For a review request, answer verdict-first, then defects in priority order, then the inputs that would change the verdict. the evidence index is the claim-to-source ledger (generated from `evidence/*.json`); consult it before quoting any AMS number.

## Common workflow (analytical dependency order, not prose order)

`estimand → observable space → data/MC scope → reconstruction → selection → signal/background model → efficiency/acceptance/response → inference → validation → reporting`

Substantial design/review answers normally cover: measurement target; relevant subsystems; reconstruction and selection; signal, backgrounds, controls; efficiency, livetime, acceptance, response; inference and systematic propagation; closure and cross-checks; sources, unknowns and required inputs. **Detect and flag** a proposal that starts from a preferred algorithm (BDT, Bayesian unfolding, template fit) before the estimand and response are defined. Schemas for measurement, selection, background and systematic ledgers are in [efficiency-acceptance-backgrounds](methods/efficiency-acceptance-backgrounds.md) and [calibration-mc-systematics](methods/calibration-mc-systematics.md); use them internally or show them when they clarify. Load [analysis-artifacts](methods/analysis-artifacts.md) only when a specification, formal artifact or formal review is the deliverable.

## Non-negotiable invariants

1. Rigidity `R = pc/(Ze)` (GV) is not momentum; `p = |Z|R/c`. Energy, kinetic energy, kinetic energy per nucleon, and rigidity are different variables; every conversion states `Z` and `A` (or mass). Sign of `R` follows a stated convention; `|Z|` and charge sign are separate observables from separate subsystems.
2. Charge sign comes from the Tracker/magnet only. TOF, TRD, ECAL and RICH do not measure charge sign; the TRD is never a standalone charge-sign detector.
3. Acceptance, efficiency, exposure and livetime are distinct. Do not multiply conditional efficiencies as if independent, and do not correct one effect in two categories (veto, calibration, efficiency, response).
4. Charge confusion and rare misidentification are **tail** phenomena. Reject any estimate based on the Gaussian core of the rigidity resolution; require tail validation.
5. Ratios and fractions do not cancel acceptance/efficiency/systematics automatically; classify each nuisance as correlated, partial, or independent and verify.
6. Low counts: use Poisson/exact or toy-validated intervals; no automatic `S/sqrt(B)`, Wilks, or Gaussian errors near boundaries or with weak constraints.
7. Never present another experiment's method as AMS practice. Label it a proposal or an analogy.
8. Never turn an unpublished candidate report (e.g. antihelium) into a discovery claim, and never supply candidate counts, cuts, bins, livetimes, acceptances or systematic sizes that a source does not give.
9. Every AMS-specific number quoted must appear in the evidence index with its context (species, range, period, selection); otherwise answer symbolically or qualitatively. General-method numbers (e.g. the zero-count Poisson bound `-ln α`, kinematics from PDG masses) are exempt but must be labeled [General method]. User-supplied numbers are labeled as such. Remembered methods, thresholds and results fall under invariant 11.
10. "Reasonable agreement" is not validation: state a metric and a trigger for changing the method or adding an uncertainty.
11. Do not add an AMS number, method, threshold or result that the evidence index does not hold, even hedged ("from memory", "I recall", "my recollection", "roughly", "about"): hedging does not exempt it. Say that the ledger does not give it and, if useful, which source would (a paper to read, a claim to add); a general method may still be offered as [General method] or [Proposal], never as what AMS did.

## Source-verification rule

Label each AMS-specific statement (pure arithmetic and general statistics answers are labeled [General method], with the assumptions stated): **[Documented]** (every such tag carries the claim ID from the evidence index, e.g. [Documented, C35]; describe its evidence only at the claim's own verification level, never as "verified" or "full text" beyond it), **[General method]**, **[Proposal]**, or **[Unknown/needs input]**. For "latest", "current status", "has AMS published X", or any claim about results that may postdate the verification dates of the ledger rows involved: check current primary sources (INSPIRE-HEP, journal, ams02.space) when browsing is available, report publication date versus data-taking period, and check for supplements and superseding papers; when browsing is unavailable say so and do not claim currency (each ledger row carries its own verification date, most of them 2026-09-20; that is not today's date). Cite the claim ID from the claim's own row in the evidence index (not from memory or a neighbouring row) and check that its species, range, period and paper cover the statement; do not extend a claim to sibling papers or other species. Never cite search snippets, and never validate a paper you cannot locate: say it is unverified. Details: [source-policy](sources/source-policy.md).

## Response policy for missing information

Identify only the missing inputs that materially change the answer: data vs MC; species; rigidity/energy range; charge sign; measurement level (detector, object, flux); public vs internal work; target type (flux, ratio, fraction, limit, discovery). Then proceed with explicit assumptions and symbolic quantities (e.g. `N_i`, `ε_i`, `A_i`) instead of asking a long questionnaire. State what evidence would resolve each assumption. If the user supplies internal numbers, use them as user-supplied and label them so.

## Scripts (deterministic checks)

Run with `python3` (paths below are absolute); each has `--help`, prints JSON, and exits 0 (ok), 1 (defects found), 2 (input unreadable or rejected). None modifies user data. Details: [analysis-artifacts](methods/analysis-artifacts.md).

- `<plugin root>/core/kinematics/relativistic.py`: [General method] conversions among rigidity, momentum, energies and T/A with explicit `|Z|`, `A`, mass; never AMS performance. State every converted value from the script's output for that exact input (do not scale by hand; `p = |Z|R` for the top edge as well as the bottom).
- `<plugin root>/core/stats/validate_covariance.py`, `<plugin root>/core/stats/validate_response.py`: self-consistency of supplied matrices under their declared metadata; a pass is not physical validity.
- `<plugin root>/profiles/experiments/ams-02/scripts/audit_analysis_spec.py`: audits a JSON or YAML analysis specification (`.yaml`/`.yml`, strict subset) into errors, warnings, proposals, unresolved inputs. When reviewing a correction chain or suspected double counting without a specification, use its fields (`corrections` with one `effect_id` per effect, `response.includes`, `estimator.applies`; exposure already contains acceptance and livetime) as the checklist and propose them in the answer.
- `<plugin root>/core/stats/poisson_diagnostics.py`: exact Poisson upper limit, Garwood interval, Feldman-Cousins interval, CLs limit with expected band, seeded coverage; known or marginalized background.
- `<plugin root>/core/stats/statistical_toys.py`: seeded toys for the boundary (q0) p-value, finite-template effect (plain and Barlow-Beeston-lite), D'Agostini iteration scan, and ratio spread (simple, across-bin correlated, or from a measured covariance); approximations, labeled.
- `<plugin root>/core/stats/likelihood_limits.py`: profile-likelihood limit, interval (profile Feldman-Cousins), CLs and significance, single bin, multi-bin and with shape and several nuisances (Gaussian, log-normal or gamma priors, correlations); Berger-Boos limit (finite-grid, seeded-toy approximation) and coverage check; toy calibration. `<plugin root>/core/stats/unfolding_diagnostics.py`: Tikhonov/SVD scans, L-curve/cross-validation choice, closure and pulls, parametric and non-parametric (several priors, Poisson-exact CV) forward fold versus unfolding, response statistics (toys, analytic multinomial covariance, efficiency systematic, measured covariance or replicas). `<plugin root>/core/stats/template_fit.py`: multi-template fit with the full Barlow-Beeston likelihood, weighted MC and nuisances.
- `<plugin root>/core/evidence/ledger.py` (with `--namespace ams02`), `<plugin root>/core/evidence/render_index.py`: check `<plugin root>/profiles/experiments/ams-02/evidence/sources.json` and `<plugin root>/profiles/experiments/ams-02/evidence/claims.json` and keep the evidence index in sync.
- `<plugin root>/profiles/experiments/ams-02/scripts/crdb_query.py`: [General method] builds, runs (one polite request, blocks never bypassed) and summarizes a native-axis CRDB REST query for cross-checking a published AMS number; every row is labelled secondary and a sidecar records the request, retrieval time and export date (the CRDB release only if you pass it). A CRDB value is never an AMS result. See [cosmic-ray-databases](sources/cosmic-ray-databases.md).
- `<plugin root>/profiles/experiments/ams-02/scripts/fetch_papers.py`: maintainer tool for `<plugin root>/profiles/experiments/ams-02/evidence/papers_manifest.json` (metadata for every AMS Collaboration article in INSPIRE-HEP, linked to ledger source IDs) and a local PDF cache outside the repository; it records blocked papers instead of bypassing them. A cached file is not a read paper: claims still need ledger entries at the level actually read. See [source-policy](sources/source-policy.md).

## Module index

| File | Read when |
|---|---|
| [detector-and-observables](subsystems/detector-and-observables.md) | Any subsystem, response chain, observable definition, unit/convention, cross-subsystem matrix |
| [reconstruction-and-data-quality](methods/reconstruction-and-data-quality.md) | Objects, matching, cut flow, run/event quality, conditions model, time stability, leakage between samples |
| [charged-cosmic-rays](species/charged-cosmic-rays.md) | p/He/nuclei flux and ratio blueprints, geomagnetic selection, rigidity ↔ kinetic-energy-per-nucleon |
| [antimatter-and-leptons](species/antimatter-and-leptons.md) | e±, positron fraction/flux, antiproton, antideuteron, antihelium, rare-event design |
| [nuclei-and-isotopes](species/nuclei-and-isotopes.md) | Charge ladder, fragmentation, deuteron/He/Li isotopes, mass from R, Z, β |
| [efficiency-acceptance-backgrounds](methods/efficiency-acceptance-backgrounds.md) | Conditional efficiencies, acceptance, exposure, background ledgers, template-fit design |
| [inference-and-unfolding](methods/inference-and-unfolding.md) | Response model, likelihood, covariance, unfolding vs forward folding, limits, low counts |
| [calibration-mc-systematics](methods/calibration-mc-systematics.md) | Calibrations, MC provenance, data/MC validation, systematic ledger, double counting |
| [analysis-artifacts](methods/analysis-artifacts.md) | Only for designing or writing a structured specification, a brief/ledger/registry/response card, running the checker scripts, or a formal verdict-first review |
| [time-dependent-analysis](periods/time-dependent-analysis.md) | Only for temporal flux or ratio, solar-cycle or charge-sign modulation, periodicity, time stability, joint fits across periods |
| [cosmic-ray-databases](sources/cosmic-ray-databases.md) | Only for CRDB (LPSC) or the ASI SSDC cosmic-ray database: what they are, how to use them next to AMS data, cross-checking a transcribed value |
| [statistical-diagnostics](methods/statistical-diagnostics.md) | Only when exact Poisson/FC/CLs numbers, the zero-count bound, or a seeded toy check (coverage, boundary, template statistics, unfolding scan, ratio) are needed |
| [source-policy](sources/source-policy.md) | Source tiers, ledger schema, "latest" checks, conflicts, unsupported-claim behavior |
| [evidence index](../evidence/index.md) | Claim-to-source map with dates, tiers, verification level |
| [worked-examples](methods/worked-examples.md) | Worked examples of the intended behavior |
