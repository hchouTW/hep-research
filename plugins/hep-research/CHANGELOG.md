# Changelog — hep-research

Release notes for the plugin. Each entry says what changed in behavior; evidence is in [VALIDATION.md](VALIDATION.md).
Software checks establish contract consistency only, not physical validity.

## Unreleased

- **New skill hep-review (protocol hep-review/1, schema 1.0.0; 0.x records labelled experimental).** Recorded, tiered review of physics
  work: review obligations, assurance tiers R0-R3 computed from the records (the R2 floor per obligation), an
  append-only SQLite commit log in the private state directory with head continuity and checkpoints, export/import,
  file submissions read by bytes, and a two-layer report (a byte-reproducible projection plus an attestation) that
  never claims more than its achieved tier. Kernel `contracts/hep_review.py` and schemas
  `contracts/schemas/hep_review_*.json`; skill `skills/hep-review/` (`review.py` CLI). R3 is not reachable on the
  measured host. Skill names now nine (`contracts/skill_names.py`); manuscript review stays with hep-authoring and
  measurement-design review with hep-measurement. Development records: `docs/dev/hep-review/`.
  New pages: `workflow-and-tiers.md` (entry reference), `evidence-and-adjudication.md`, `host-and-trust-boundaries.md`,
  `storage-continuity-and-export.md`, `evaluation-and-claims.md`, and the domain cards `domains/index.md`,
  `domains/statistics.md`, `domains/computing.md`; new script `review.py`.
  Gate G2 passed on three narrow pilots (G2, a held-out follow-up, and a Codex-authored multi-defect suite with
  cross-family grading: 0 content misses in 141 trials; `docs/dev/hep-review/g2*-report.md`), after which the schema
  was frozen at 1.0.0 (validator `1.0.0`; 0.1.0 kept for historical data). The packet now asks reviewers for a
  separately computed SHA-256 or `SHA256: unavailable` (a fabricated digest quarantined a correct review in g2x).

## 0.43.0 (2026-10-29)

Minor release; contracts 3.14.0 (one minor, the `CV-CRPROP` of the cr-propagation campaign, new rules gated by
`contracts/validate.py` `CRPROP_FROM`), `CORE_VERSION` 1.2.0 (new `core/provider/`), adapter `cr-propagation` 0.2.0.
It ships the cr-propagation r4 campaign (20 of 24 work packages; report in
`docs/dev/cr-propagation/campaign-report.md`): propagation predictions from USINE V3.5, DRAGON2 cd588707 and the
closed-form thin-disc model through one subprocess provider protocol `cr-provider/1`, multi-dataset propagation fits
with object-form degeneracies, toy-calibrated family comparison, and a Gaussian-process emulator provider. The
reproduction of Génolini et al. 2019 is partial, so the capability map is unchanged (propagation global fits stay
outside v1).

**Before you upgrade** (details in each entry below):
- A theory-spec that declares contracts 3.14.0 or later is checked natively by the object-form
  `degenerate_directions` and `transport.diffusion.breaks` rules (new errors `theory.degeneracy_evidence_missing`,
  `theory.degeneracy_range_missing`, `theory.degeneracy_evidence_unknown` and the transport errors); older artifacts
  only under `--strict`. Every committed artifact keeps its outcome.
- Profiles and adapters may declare a `provider` field; `tools/provider_registry.py` lists them. External codes are
  found only through `HEP_USINE_BIN`/`HEP_USINE_DATA` and `HEP_DRAGON2_BIN`/`HEP_DRAGON2_DATA`; USINE (GPL-2.0) is
  never vendored.

**Known issues** (campaign report §8): no F1 fit converges at USINE's 6-digit output noise floor (delta and K10 are
inside the paper's 1-sigma windows; -2 ln L about 83-90 against about 62, attributed); the USINE provider applies solar
modulation itself, against `cr_provider.json`'s "providers never modulate" (recorded in every modulated prediction);
accepted, attributed DRAGON2/USINE differences D1-1a, D3-1 and D3-3, not yet recorded in `adapter.json`; C2UF toy fits
bounded by the emulator's k = 4 domain while validation covered k = 3; `propagation_fit.py` reports unconverged fits as
"artifact-invalid"; translator gaps (escalation 12) and the r3 P1 zone-conversion wording with a likely DRAGON2
Ptuskin94/03 enum issue (escalation 10); `train_emulator.py` lets the GP nugget reach its 1e-12 floor, which gives
near-singular models (the provider now factorizes them with a bounded jitter), and the C2UF emulator fixture is refused
off macOS (its self-check does not reproduce under another libm; its tests skip, A1.21) until it is retrained; GALPROP
unavailable; F2, F3 and the live routing run not done.

- crprop ci: the campaign's regression pins compare platform-robustly (PR #308 CI on Linux, decision A1.20): recomputed
  closed-form, USINE-reader and DRAGON2-port values against committed numbers within relative 1e-12, the E2 emulator's
  pinned responses and hold-out numbers within relative 1e-4 (GP linear algebra); E2-1, E2-2 and every acceptance
  tolerance unchanged. `emulator_provider.py`: a kernel matrix that does not factorize as stored (the C2UF model's is
  near-singular and failed on Linux, so `--declaration` refused) is factorized with a jitter of 1e-14, else 1e-13,
  times its mean diagonal; the self-check accepts ln mean and ln sigma each within max(1e-9, 1e-4 x the stored ln
  sigma) and a refusal names the worst deviations and where. The C2UF model stays refused on platforms whose libm
  differs (simulated drift up to 2.5e-2 x sigma: not portable); the E2 model drifts at most 9e-7 x sigma.
  The C2UF fixture is platform-bound (A1.21): its tests skip on that refusal only; the follow-up is retraining
  with a nugget floor in `train_emulator.py`.
- crprop env: capability probe of the cr-propagation campaign and environment E-crprop registered in VALIDATION.md
  (E2 plus DRAGON2 cd588707 verified by a live rerun); DRAGON2 computational-run and environment manifest under
  `tests/adapters/fixtures/cr_propagation/env/`. USINE and GALPROP absent (no source tarball). No behavior change.
- crprop a2: theory-spec contract extension for cosmic-ray propagation (cr-propagation plan r3 §A2, §5.4; contracts
  `CV-CRPROP` = 3.14.0, unreleased, gated by `contracts/validate.py` `CRPROP_FROM`). New optional
  `extension.transport` block (geometry, diffusion with breaks, reacceleration, convection, losses, decay, gas,
  sources, cross sections, species, family, free) in the canonical parameter names (`D0_cm2_s`, `R0_gv`, `L_kpc`,
  `V_A_kms`, ...); its parameter blocks refuse any other key. `degenerate_directions` items are now a string or an
  object (`combination`, `form`, `exponents`, `valid_range`, `broken_by`, `evidence`); new core vocabulary
  `degeneracy_evidence` (`fisher-screen`, `profile-scan`, `posterior`). An object entry with a combination now counts
  for `theory.degeneracy_missing`; from `CRPROP_FROM` (older artifacts only under `--strict`) an object entry needs its
  evidence and the range where it holds: new errors `theory.degeneracy_evidence_missing`,
  `theory.degeneracy_range_missing`, `theory.degeneracy_evidence_unknown`. String entries keep their meaning, and
  every committed theory-spec keeps its outcome. `covariance_fit.py` `tabulated-grid` reads an object entry as its
  `combination` (same fit as the equivalent string). Fixtures: two positive, four negative. The `CONTRACTS_VERSION`
  bump with its regenerated fixtures, templates, profile artifacts and examples is the separate commit on branch
  `worktree-crprop-a2-bump`.
- crprop a1: new `skills/hep-theory/scripts/transport_conventions.py` converts cosmic-ray diffusion parameters among
  the GALPROP, USINE (K0, K10) and DRAGON2 conventions and the canonical names (`D0_cm2_s`, `R0_gv`, `delta`, `eta`),
  marking each result `exact`, `approximate` with a relative-error bound, or `not-convertible`; it also moves V_A
  between thin-disc and whole-halo reacceleration (approximate), converts per-nucleon and total kinetic energy, and
  maps the legacy names `D0` and `L`. Units from the IAU parsec and Julian year (1 kpc^2/Myr = 3.0172e29 cm^2/s). New
  fixture `tests/adapters/fixtures/cr_propagation/specs/harmonized-v1.json` (r3 §5.5 in the §5.4 transport format);
  usage paragraph in `cosmic-ray-phenomenology.md`. Contracts unchanged.
- crprop c1: provider protocol `cr-provider/1` (cosmic-ray propagation plan r3 §C1, §5.2). New contract schema
  `contracts/schemas/cr_provider.json` (provider declaration, request, response, components; not an artifact type;
  `want` only `lis` and `components`; no new vocabulary) and the optional `provider` field of `profile.json`
  (`contracts/schemas/profile.json`) and `adapter.json`, part of the campaign's unreleased contracts minor
  (CV-CRPROP, 3.14.0, whose version line A2 sets). New core module `core/provider/` (`CORE_VERSION` 1.1.0 → 1.2.0,
  steward hep-computing): `protocol`, `hashing` (point hash, equal to `contracts/recipe_semantics.py`
  `canonical_sha256`), `registry` (the caller passes `--provider-registry`; core never searches), `entrypoint` (every
  provider's `--request/--response`, `--serve` JSON Lines and `--allow-outside-validated-range`), `runner` (subprocess
  calls in batches, cache keyed by the point hash under a caller-given folder, refusals with reasons: out-of-domain,
  unregistered-provider, provider-failed on a crash, ...; a request with a `theory_spec_ref` but no transport block is
  not cached; user-supplied providers labelled `user-supplied`) and
  `conformance` (PRV-1/PRV-2 checks, also a command line). New `tools/provider_registry.py --write PATH` builds the
  registry from the `provider` fields (never committed). First provider: `scripts/provider.py` of the
  `cr-secondary-ratio` theory profile, the closed-form thin-disc B/C with one component per production channel
  (values bin-averaged in ln(E/n) as in the profile, not P2 bin integrals). New tool contract
  `contracts/tool_contracts/solar_modulation_force_field.json` for the force-field script. Tests:
  `tests/core/test_provider.py`, the reusable helper `tests/core/provider_conformance.py` for provider work packages
  (its own test `tests/core/test_provider_conformance_mixin.py`),
  `tests/tools/test_provider_registry.py`, the profile's `tests/test_provider.py`, the `provider` check in
  `tests/adapters/test_adapter_declarations.py` and a force-field contract test; `docs/adapter-authoring.md` gains
  the field row and a provider section.
- crprop b2: `theory:cr-secondary-ratio` gains closed forms of the 1D thin-disc model with constant convection
  (`V_c_kms`) and radioactive decay of secondaries (rate 1/(gamma tau_0), half-lives from `core.constants`
  NUBASE2020, 10Be -> 10B gain kept, fully stripped 7Be stable by a recorded assumption):
  `scripts/convection_decay.py` (with a `solve_bvp` benchmark), SymPy derivation `scripts/derive_convection_decay.py`
  recorded in `derivations/convection-decay-record.md` (`analytic-derivation`; pure-diffusion limits and dimension
  checks), ILLUSTRATIVE isotopic set `models/xs-illustrative-decay.json`, tests `tests/test_convection_decay.py`;
  the profile's tests directory is now a package so it is discoverable from the plugin root. Reacceleration stays
  excluded. Profile version unchanged (0.1.0): the minor bump needs `profiles/registry.json` and the example pins.
- crprop p0: `workflow_check.py diff` lists changed paths with `--no-renames` so a rename cannot hide its source path; regression test added in `docs/dev/cr-propagation/`
- crprop env: USINE V3.5 (gitlab.com/dmaurin/USINE, commit fb53006d, GPL-2.0; decision A1.1) built against ROOT 6.38.04
  and smoke-run for environment E-crprop (`usine -tUSINE`: 42 of 46 reference tests pass, the other 4 differ only in
  time zone, labels or last digits); USINE computational-run and environment manifest under
  `tests/adapters/fixtures/cr_propagation/env/`. No behavior change.
- crprop a3: two-level degeneracy diagnostics. New `skills/hep-statistics/scripts/degeneracy.py`: the Fisher screen
  (eigen-decomposition and flat-direction rule moved unchanged from `covariance_fit.py`, which now calls it) and
  profile-likelihood scans along one parameter, a direction (or each Fisher flat direction) or over a plane, with
  object-form degeneracy entries (`combination`, `form`, `exponents`, `evidence`: `fisher-screen` without `valid_range`,
  `profile-scan` with the `valid_range` where the profile stays within the threshold). `covariance_fit.py fit`
  (tabulated-grid) accepts an optional `degeneracy_scan` block and then adds `degeneracies` and `profile_scans` to each
  fit; without it every output is byte-identical to the base (A3-1 baseline hashes). `degeneracy.py synthetic-curved`
  is a built-in SYNTHETIC study (D0_cm2_s proportional to L_kpc^1.2, exact to 6 kpc, broken above by a spectral tilt):
  the profile scan gives `valid_range.L_kpc` = [2, 6.95]. Tests: `tests/skills/hep_statistics/test_degeneracy.py`.
- crprop a4: cost benchmark of the cr-propagation campaign (r3 §A4): wall time and peak RSS (median of three runs)
  of the closed-form provider of `cr-secondary-ratio` and of DRAGON2 under `harmonized-v1`, and the grid convergence
  of DRAGON2's B/C over 2–1000 GV (spatial and energy grids doubled once; reported, no threshold), in the
  `CRPROP-COST` section of VALIDATION.md. Run records, run specs, provider requests and the convergence script under
  `tests/adapters/fixtures/cr_propagation/cost/`. USINE and GALPROP rows not measured (capability absent). No
  behavior change.

- crprop b1: USINE V3.5 in `adapters/cr-propagation` (adapter 0.2.0): `usine_translate.py` writes a USINE run from
  a transport block (Model2DKisoVc for `cylinder-2d`, Model1DKisoVc for `slab-1d`; diffusion with low breaks,
  thin-disc reacceleration, constant convection, losses, decay; the ILLUSTRATIVE cross sections of
  `theory:cr-secondary-ratio` only), records every item USINE expresses only approximately and refuses the rest, runs
  USINE and records the run; `usine_to_prediction.py` turns USINE's local-flux tables into ratios of bin integrals
  (isotopes summed on the data's axis); `usine_provider.py` serves it as the cr-provider/1 provider `usine` (B/C,
  10Be/9Be, Be/B on E_k/n or rigidity). Seven recorded runs replayed offline, live rerun with `HEP_USINE_LIVE_TEST=1`;
  USINE `tested-in-declared-environment`, adapter still `proposed` (GALPROP). USINE is GPL-2.0 and runs as a separate
  program; no USINE file is committed. The USINE row of the CRPROP-COST table is filled. README package size
  statement updated (about 3800 files, 56.6 MB).
- crprop c2: multi-dataset propagation fit through a `cr-provider/1` provider (cosmic-ray propagation plan r3 §C2,
  closed-form provider and SYNTHETIC data only; the USINE case is C2U). New
  `skills/hep-statistics/scripts/propagation_fit.py fit`: datasets as dataset-records (covariance from their
  components, missing: exit 3), the provider's prediction gated and its bin semantics checked first (a bin-averaged
  ratio is never fitted to data declared as P2 bin integrals; refused, exit 1); component multipliers for production
  norms (P15) and parent abundances (P14), profiled exactly; inelastic and slope nuisances refused without provider
  support; modulation refused for a provider without isotopic LIS; declarative families (those outside the provider
  domain listed as not expressible); `fit_diagnostics` verdicts with `boundary_kkt`, at most 5 restarts; Fisher screen
  and profile scans of `degeneracy.py`, a fit-derived theory-spec with object-form `degenerate_directions`; profile
  intervals; covariance alternatives from `build_covariance.py` lengths (P9); toys (`toy_ensemble`), toy-calibrated
  family delta chi2 and a Metropolis posterior (`bayes_diagnostics`, no interval above R-hat 1.01 or below ESS 400) on
  a validated response model of the provider; loop limits (restart cap, 2% toy failures, 2e5 steps per chain) and
  `--max-evaluations`. New example `examples/propagation-fit/` and section of `core-stats-commands.md`. Tests:
  `tests/skills/hep_statistics/test_propagation_fit.py`.
- crprop b3: USINE V3.5 against the closed forms of `theory:cr-secondary-ratio` under harmonized-v1, with the same
  parents, cross sections, tertiary and ghost settings. B3-1 as frozen fails under harmonized-v1 (2D: B/C up to 2.5%
  off, attributed to radial escape at R = 20 kpc) and is superseded for B3's verdict by B3-1a/b/c (decisions A1.10):
  matched 1D geometry within 4e-4 (B3-1a), the 2D offset reported per bin and attributed (B3-1b), USINE 2D against the
  Fourier-Bessel thin-disc solution within 0.21% (B3-1c, tolerance 0.5%). Level-by-level norm reweighting at +-20% matches full reruns within 9e-6 for all 22 channel cases; slope
  changes need energy-basis responses when energies couple. Channel list with `must_rerun` flags; specifications, nominal
  tables, records, run index and offline tests under `tests/adapters/fixtures/cr_propagation/b3/`. No behavior change.
- crprop e1: training design and bounded active addition with USINE (r3 §E1; optional WP). New
  `tests/adapters/fixtures/cr_propagation/e1/active_addition.py`: Sobol design (N0 = 64, k = 6 for 5 free
  parameters, decision Q9), one USINE computational-run per point through `local_partition.py` and the provider
  runner with cache, and the active-addition loop with its limits (5 rounds, E2 termination criteria, error-plateau
  and min-distance early stops, evaluation cap) on a placeholder emulator that E2 replaces. Committed: design file,
  summaries with per-point hashes and run references; training data stay under `$CRPROP_OUT/e1/`. No behavior change.
- crprop a1r: `transport_conventions.py` corrected and extended from the codes' sources (decision A1.9). The
  `dragon2` diffusion convention is now D0 beta^etaT (rho/DiffRefRig)^delta in rigidity with `D0_1e28` in 1e28 cm^2/s
  and etaT, DiffRefRig free (DRAGON2 cd588707 src/diffusion.cc:150, src/crevolutor.cc:121-122); it was D0 (p/p0)^delta
  with eta = 0. The DRAGON2 row of the convention table in `cosmic-ray-phenomenology.md` follows. New reacceleration
  conversion among `thin-disc`, `whole-halo`, `dragon2-ptuskin94`, `dragon2-ptuskin03` and `usine`: the D_pp
  constants read from the code (DRAGON2 cd588707 Ptuskin94 c = 1 without the 4/3, which its enum gives to Ptuskin03;
  USINE V3.5 c = 4/3) convert exactly; the thin-disc/whole-halo change uses the first-order equivalence
  V_A,disc^2 h = V_A,halo^2 L / 3 derived in the module (not sqrt(L/h)), approximate with the bound (1 + lam)/5 on the
  second-order term, lam = h Gamma L / D, now a required input (`--destruction-escape-ratio`). The `reacceleration`
  subcommand takes `--from`/`--to` (the old `--from-zone`/`--to-zone` still work). Tests: an independent
  finite-difference oracle of the zone weights, round trips within 1e-12.
- crprop b1x: high break and USINE's own inputs (decision A1.7; still the unreleased contracts 3.14.0 with
  `CRPROP_FROM`, no new gate). `extension.transport` gains a high break (`{"kind": "high", "R_break_gv",
  "delta_above", "s"}`), `geometry.local_bubble_radius_kpc` and the source beta exponent `eta` of an injection item;
  from `CRPROP_FROM` (older artifacts only under `--strict`) a half-specified break is refused
  (`theory.transport_break_incomplete`) and a break kind other than low or high too
  (`theory.transport_break_kind_unknown`); every committed theory-spec keeps its outcome (one positive and two
  negative fixtures added). `transport_conventions.py` evaluates the high break (USINE V3.5's shipped K formula).
  `usine_translate.py` translates the high break, the local bubble, the source eta, HII and H2 densities,
  electron-capture decay (`ec_treatment` `laboratory-half-life`) and an explicit energy grid (`--ekn-grid`), and can
  use USINE's own cross-section files and data-normalised abundances (`usine:<path>` names, read in place from
  `HEP_USINE_DATA`, never copied; refused with exit 3 when it is unset); a transport block matching USINE's shipped
  `init.TEST.par` reproduces that example's B/C exactly (recorded run `b1x-init-test`, live test). The translator now
  refuses unknown keys and records every default and every field it does not use; records also hash the committed
  form of their inputs (`committed_form_sha256`, added to the seven B1 records without a rerun). The reader counts
  14C in carbon. A whole-halo V_A is converted with `transport_conventions.py reacceleration` (A1R: sqrt(L/(3h)),
  approximate, bound recorded at the run's largest lam); `b1-slab-all-items` rerun and its results updated.
- crprop d1: DRAGON2 physics items and the provider `dragon2` (cr-propagation r3 §D1, §D1b, folded by r4 §6).
  `adapters/cr-propagation` 0.2.0: `dragon2_run.py` gains a translator from a `transport` block (`--from-transport`,
  `spec_from_transport`) that records every item DRAGON2 cannot express (gas, helium, disc thickness, source
  distribution, inelastic cross sections, V_A zone) and refuses breaks; optional Convection and Reacceleration blocks,
  NUBASE2020 half-lives written into a copy of `isotope_list.dat` (DRAGON2 ships 10Be at 1.51 Myr) and a single
  injection slope. `dragon2_to_prediction.py` gains ratios of bin integrals on ekn or rigidity bins (r3 P2, P3). New
  `dragon2_provider.py` (cr-provider/1, declared in `adapter.json`; not decomposable; runs kept under
  `HEP_DRAGON2_RUN_DIR` when set). Six runs from new `harmonized-v1-<item>.json` files recorded under
  `tests/adapters/fixtures/cr_propagation/dragon2/`. The translator converts V_A with hep-theory's
  `transport_conventions.py reacceleration` (A1R; subprocess) and runs energy losses on Galprop gas, refusing them on
  gas without HII (DRAGON2 cd588707's nuclear Coulomb loss diverges at n_HII = 0). D1-1 (absolute, frozen) fails and is
  superseded by D1-1a/D1-1b (decision A1.9): item effects pass for convection and fail for 10Be/9Be with decay,
  reacceleration and losses (13%, 5.7%, 6.1%), with attribution (VALIDATION CRPROP-D1).
- crprop e2: emulator of USINE B/C with its valid domain and provider (r3 §E2, §E2b; optional WP). New
  `skills/hep-ml/scripts/train_emulator.py`: Gaussian-process emulator of a vector simulator output on a box of
  inputs (principal components, Matern-5/2 GP each, error per prediction, `DomainModel` in the model file, run summary
  for the writer with task surrogate). `write_ml_artifact.py` now copies the task's validation block
  (`extrapolation_policy`, `generative_validation`, `sbi_validation`, `anomaly_validation`, `reweighting_validation`,
  `parameters`, `supervision`), so a surrogate artifact can be written. New cr-provider/1 provider `emulator`
  (`adapters/cr-propagation/assets/emulator_provider.py`, declared in `adapter.json`): reads only the ml-artifact and
  model file, refuses points the `DomainModel` calls sparse or outside, gives the emulator error as uncertainty
  components; `HEP_EMULATOR_ML_ARTIFACT` names another model. Committed model, ml-artifact, hold-out sets and summary
  under `tests/adapters/fixtures/cr_propagation/e2/` (with the driver `emulator_campaign.py`): E2-1, E2-2 and E2-3 met
  on synthetic data (177 USINE evaluations). Tests: `tests/skills/hep_ml/test_train_emulator.py`, E2 classes in
  `tests/adapters/test_cr_propagation.py`.

- crprop c2u: `propagation_fit.py` with the USINE provider (r3 §C2, USINE case). A provider that is not decomposable
  is fitted through one `total` component (multipliers refused); a `transport` block is sent with every request;
  `parameters.<name>.step` sets the difference steps of the Jacobian, Fisher matrix and verdict for a noisy provider
  (a coordinate within one step of a bound is set on it and judged by `boundary_kkt`); response model kind
  `polynomial` (total-degree Chebyshev on a Sobol design, 1 to 6 coordinates); the bin-semantics guard recognises P2
  ratios declared `bin-integrated` or `bin-averaged` with the P2 statement and checks binning conventions on both
  sides; `run_record_keys` (parameter_point keys that record a run, not compared); every evaluation's record and,
  with `computational_runs`, its computational-run resolved with the tool versions; toy seeds in the
  statistical-result, per-toy rows kept, multipliers bounded; a failed family calibration is recorded instead of
  aborting the run. Recorded USINE study and tests (C2U-1, C2U-2 met; C2U-3 not met: response model above tolerance,
  VALIDATION CRPROP-C2U).
- crprop d3: two-level cross-code comparison of DRAGON2 cd588707 and USINE V3.5 (cr-propagation r3 §D3; GALPROP
  unavailable, A1.2). New `tests/adapters/fixtures/cr_propagation/d3/` (study script `d3_study.py`, DRAGON2's own
  inelastic cross sections tabulated with its compiled code, 2 DRAGON2 and 20 USINE recorded runs, `d3-results.json`)
  and `D3CrossCode` / `LiveUsineD3` in `tests/adapters/test_cr_propagation.py`. D3-1 (level 1, 5%) fails at 38-77% and
  is decomposed (gas column, helium target, inelastic cross sections, parent ratio O/C, injection convention); D3-3
  (USINE given DRAGON2's fixed settings) passes within 0.7% on BronfFerr gas and fails for reacceleration (17%,
  first-order zone conversion) and losses on Galprop gas (17.7%, gas geometry), both attributed; D3-2 (level 2, each
  code's defaults) passes with every difference registered as a model alternative (residual 0.4%) (VALIDATION
  CRPROP-D3).
- crprop c2uf: propagation_fit.py sends every dataset's observable in one provider request per point
  (`provider_requests` "per-point", one USINE run per point) and adds response-model layouts "joint" and
  "per-center" for the family calibration; the two-dataset USINE study (B/C and 10Be/9Be with decay on) and its
  record under tests/adapters/fixtures/cr_propagation/c2uf/ (polynomial response models refused). Dispatch 2
  (decision A1.14): emulator_provider.py takes a per-model declaration (observables with output slices, axes, bins,
  the domain from the model's box; `--declaration`), the committed E2 model answered exactly as before (pinned
  responses); propagation_fit.py response_model kind "provider" (toys on the provider itself) and toy fits that use
  the stated steps, bound snapping and a Newton finish; a Gaussian-process emulator of USINE B/C and 10Be/9Be
  (decay on) validated on 40 held-out USINE runs at 0.0038 sigma; C2UF-1 met: BIG survives (p 1.0), SLIM excluded
  (delta chi2 23.9, p < 0.015) with 200 toys each (VALIDATION CRPROP-C2UF).

- crprop f1: reproduction of Génolini et al. 2019 (BIG, SLIM, QUAINT) with USINE on AMS-02 B/C. The USINE provider
  takes the low break (`R_break_gv`, `delta_below`), a data period's force-field potential (`phi_2011_2016_gv`,
  USINE's SolMod0DFF per isotope; recorded departure from "providers never modulate") and a production channel's
  norm, low-energy slope and threshold (`xs_norm_12C_H_11B`, ...; USINE's fit-mode transformation on a run-time copy
  of the channel, never committed); a point that moves `delta` keeps each high break's Deltabreak. The translator adds
  `--phi`, `--production-modifiers` and `pure:<isotopes>` in data-normalised abundances; the reader reads modulated
  tables with a phi check. `propagation_fit.py`: parameter priors, periods accepted when the provider's domain has
  `phi_<period>_gv`, optional Newton polish before the verdict. New example `examples/bc-usine-reproduction`. Outcome
  (VALIDATION CRPROP-F1): F1-1 not met on convergence only (delta and K10 in window for BIG, SLIM and the declared
  variant QUAINT-Vc0, V_c on its bound by boundary_kkt; no fit_diagnostics verdict at USINE's 6-digit noise floor),
  F1-2 met. `usine_translate.py --usine-tolerance` sets USINE's EPS_ITERCONV, EPS_INTEGR, EPS_NORMDATA (defaults
  unchanged; tighter values change no output digit). `adapters/cr-propagation/adapter.json` provider domain widened
  (decision A1.16).
- crprop RC: campaign summary in `docs/dev/cr-propagation/campaign-report.md` (20 of 24 work packages merged with a
  verifier PASS; D2 unavailable, F2 and F3 skipped; F1 a partial reproduction, so no v1 change; known issues listed
  there) and the pull-request draft `docs/dev/cr-propagation/pr-draft.md`. Documentation only.

## 0.42.0 (2026-10-26)

Minor release; contracts 3.13.0, `CORE_VERSION` 1.1.0 and geant4 adapter 0.5.0 unchanged. It ships semantic naming
governance (#303-#306): one data model, rule registry, engine, disposition rule, procedure and report for every
naming surface N1-N17, with an extractor for each surface in its owner skill, cross-surface checks (shape histograms
a nuisance derives, label references, BibTeX citations), glossary identifiers, and the plugin's own naming gate.

**Before you upgrade** (details in each entry below):
- Stanza item 6 in every `SKILL.md` now asks agents to name what they add or change for what it holds, per the
  semantic naming charter (`skills/hep-computing/references/semantic-naming.md`), and never to rename an external
  (C4) name.
- `hep-research.project.json` schema 1.3.0 adds an optional `naming` block (`strict`, `glossary`, `waivers`); a
  config that declares 1.3.0 needs this plugin version.
- The eight "(moved)" pointers of the hep-detector front-end page are gone: links to their old anchors now need the
  new pages `front-end-waveform-processing.md` and `front-end-calibration.md`.
- `run_all_checks` runs two new checks, `naming_registry` and the naming gate `naming`.

- Semantic naming governance, phases P1 and P2 of the semantic naming spec v4.2 (phases one release later than the
  spec, since 0.41.0 shipped without it). Every naming surface (N1-N17) shares one data model, rule registry, engine,
  disposition rule, procedure and report; a surface brings an extractor and its rule data.
  - New charter page `skills/hep-computing/references/semantic-naming.md` (precedence, principles, contract levels
    C0-C4, the ten predicates, tokenizer, vocabulary chain, waivers, disposition and severity, the nine-step
    procedure, the naming table and change sets, surface index). hep-computing's **Owns:** line adds semantic naming;
    a Resources row and a `docs/routing-contract.md` ownership row (`semantic naming`) route to it.
  - New `core/naming/` (steward hep-computing): model, tokenizer, vocabulary chain, predicates, engine; default
    vocabulary and forbidden table in `core/naming/data/`. New `core/terminology/` (steward hep-authoring) holds
    `load_glossary`, moved unchanged; `communication_lib/terminology.py` re-exports it and `check_terminology` is
    unchanged.
  - New `contracts/naming_check.py` (`check`, `annotate-template`, `validate`, `validate-change-set`, `surfaces`) with
    the `audit_report` outer shape and exit codes 0/1/3/2; new `contracts/naming_registry.py` (`check`, `sections`);
    registries `contracts/naming/surfaces.json` (17 surfaces) and `contracts/naming/rules.json` (13 rules); schemas
    `naming_inventory.json`, `naming_annotations.json`, `naming_report.json`, `naming_change_set.json`,
    `naming_rule_registry.json`, `naming_surfaces.json`.
  - New script `skills/hep-computing/scripts/extract_names.py` for N1 (Python identifiers), N2 (files and folders),
    N5 (CLI flags, environment variables, configuration keys) and N16 (plugin vocabulary), with owner sections
    (anchors `naming-n1`, `naming-n2`, `naming-n5`, `naming-n16`) in `python-balanced-design-guidelines.md`,
    `analysis-data-pipelines.md`, `environments-and-containers.md` and `engineering-playbook.md`; their kinds tables
    are generated from the registry.
  - The plugin's own gate `tools/check_naming.py` (N1, N5, N16, deterministic rules) runs in `run_all_checks` with
    `contracts/naming_registry.py check`; the 1042 findings that predate it are listed in
    `tools/naming_known_gaps.json`, which only shrinks.
  - Project config schema 1.3.0: an optional `naming` block (`strict`, `glossary`, `waivers` with explicit entity ids);
    `contracts/project.py --preflight` prints it. A 1.3.0 config needs this plugin version.
  - Context-resolution stanza item 6 (all eight `SKILL.md`): name what you add or change for what it holds, in the
    project's terms, per the charter; never rename an external (C4) name. The spec's longer wording put the
    hep-statistics quick load at 25,656 B, over the 25,600 B limit (spec Q2); the shorter sentence measures 25,597 B.

- Semantic naming phases P3 to P5: every surface N1-N17 now has an extractor and an owner section.
  - New shared extractor module `core/naming/extract.py` (file walk, text and path mention indexes, coverage, git
    change marking, read-only artifact reading, the common command line); hep-computing's extractor uses it.
  - `skills/hep-computing/scripts/extract_names.py` adds N3 (objects inside ROOT files, uproot or else PyROOT; Up/Down
    histograms are `shape_histogram`), N4 (TTree branches, RNTuple fields, Parquet columns with pyarrow, RDataFrame
    `Define`/`Redefine`/`Alias` columns; `--external PATH` marks official ntuples) and N6 (Snakemake rules and logs,
    Slurm and HTCondor job names and log patterns, `run_workflow.py` steps, partition chunks).
  - New scripts `extract_names.py` in hep-measurement (N7 samples, datasets, run ranges; N8 selections and regions;
    N9 variations), hep-statistics (N10 from Combine datacards, pyhf workspaces and statistical-result artifacts),
    hep-detector (N11 conditions tags, external, and response outputs), hep-ml (N12 models, features, checkpoints),
    hep-theory (N13 parameters and scheme labels), hep-authoring (N14 labels, label references, macros, figure and
    table files; N15 BibTeX keys with their DOI or arXiv id) and hep-citations (N17 literature record ids, external).
  - Owner sections with generated kinds tables (anchors `naming-n3`, `naming-n4`, `naming-n6` to `naming-n15`,
    `naming-n17`) in `root-usage-patterns.md`, `python-hep-coding-patterns.md`, `batch-scheduling.md`,
    `analysis-design.md`, `systematics.md`, `nuisance-modeling.md`, `calibration-and-alignment.md`,
    `reproducibility.md`, `regularization-and-schemes.md`, `latex-mechanics-and-tooling.md`,
    `citations-and-bibliography.md` and `citation-verification.md`; the charter's surface index links them all.
  - Cross-surface names: an entity may list `targets` (names it refers to; `derived` when built from its own name).
    A shape nuisance derives `<process>_<nuisance>Up`/`Down` on N3 through the datacard's shapes lines, and a process
    its nominal template: `naming.n10.shape-pairing` finds a missing variation with the N3 inventory (unverified
    without it), and `validate-change-set` needs the N3 inventory and a replacement for every derived histogram when
    a nuisance is renamed. A `\ref` to a label no file declares, or an included file that does not exist, fails
    `naming.common.reference`.
  - Correlation inventory (spec Q1, provisional): `check --declaration` also takes a measurement-spec, read from its
    systematics ledger (`correlation_key`, `era_correlation`, optional `nuisance_names`) by
    `core/naming/declarations.py`; members may be bare names.
  - Cross-surface vocabulary (P4): `naming.cross.glossary-identifier` checks every surface against the glossary's
    `identifiers`; the engine fills `meaning.concept_id` from the glossary.
  - Rules: 20 (new `naming.n4.block-member`, `naming.n10.name-format`, `naming.n10.shape-pairing`,
    `naming.n14.label-prefix`, `naming.n15.duplicate-record` (one DOI under two keys, the only N15 rename),
    `naming.n17.identifier-format`, `naming.cross.glossary-identifier`); the common rules cover the new surfaces.
    Uniqueness compares declarations of one kind (a label and a reference to it are not duplicates).
  - Schema `naming_inventory.json`: optional entity `targets`. `tools/optional_modules.json` runs the N3/N4 tests
    in the uproot jobs; without uproot they skip.

- Semantic naming, fixes from the re-review of the spec's third round (R869ec87b88, round 2):
  - `extract_names.py --changed` alone compares against the merge base of `HEAD` and the main branch; an explicit
    revision that already holds commits of this branch (their names would look unchanged) makes the check report
    every name, and an inventory without change marks (or with such a revision) leaves its unchanged names'
    `semantic` review unverified, so the check cannot pass on a hidden change. The table names the revision compared
    against. A `--root` below a project root is refused (narrow with `--scope`).
  - Change sets: the proposed name is judged (not forbidden, in the kind's format, not another entity's name: on N10
    anywhere, on N15 only the duplicate's); a `dedup-only` change set needs a uniqueness `trigger`; a C3 approval
    names the approved `proposed`; an N10 rename needs the N3 inventory from the registry (`references_to` with
    `derived`), even when the inventory lists no targets.
  - Correctness rules (uniqueness, reference, the N15 duplicate, the glossary identifier) are never waivable, and the
    registry checker refuses a waivable one; a waiver without `@line` covers a name declared once only; an
    annotation resolves a near-duplicate only at high confidence; a missing inventory a rule needs is `unsupported`
    (it was `unverified`); unreadable inputs (`skipped_inputs`) make the surface `unsupported`; `naming.inputs`
    records the sha256 of every `core/naming/data` file.
  - `tools/check_naming.py`: the baseline may grow only for a rule new since `--base` (default `origin/main`;
    skipped with a note when absent, as in a shallow clone).

- hep-detector front-end page: the eight "(moved)" section pointers left by the 0.41.0 split are removed, as recorded
  (`remove_in` 0.42.0). The sections are in `front-end-waveform-processing.md` (sampled waveforms, pileup,
  photosensors, LAr TPC, digital pulse processing, pulse-shape discrimination) and `front-end-calibration.md`
  (calibration and simulation of the electronics); the page's introduction links both. Their records are gone from
  `pointers` in `tools/wiring_known_gaps.json`.

## 0.41.0 (2026-10-26)

Minor release; contracts 3.13.0, `CORE_VERSION` 1.1.0 and geant4 adapter 0.5.0 unchanged. It ships the front-end
electronics work for reconstruction, simulation and calibration (#294-#300): five new `frontend_response.py`
subcommands, then a table signal model, a measured noise covariance, batch S-curve fits and the simreco
`noise-digitization` numbers; the front-end reference page split in three; and a simulated thin-silicon spectrum.

**Before you upgrade** (details in each entry below):
- The front-end page's sections on sampled waveforms, pileup, photosensors, LAr TPC, digital pulse processing and
  pulse-shape discrimination are now in `front-end-waveform-processing.md`, and its calibration and simulation
  sections in `front-end-calibration.md`. Links to their old anchors reach a "(moved)" pointer until 0.42.0.
- `frontend_response.py`: an input error whose message contains "JSON" now exits 2 (`invalid-input`); it exited 1
  before. A non-finite result still exits 1.
- sci-fix FRONTEND-INJECTION-GAIN (S3): the calibration chain no longer takes the charge-injection gain for the
  signal gain.

hep-detector front-end electronics for reconstruction, simulation and calibration (VALIDATION FRONTEND-RECO-SIM). No contracts,
`core/` or adapter version change; `frontend_response.py` now imports `core.stats._linalg.solve`.

- `frontend_response.py` gains five subcommands (tool contract `frontend_response.json`: 15 operations):
  `optimal-filter` (weights and variance of a sampled CR-(RC)^n pulse with exponentially correlated electronic noise
  and Campbell pileup noise, against the uncorrelated template and the largest sample; `--constraints phase` and/or
  `baseline` by Lagrange multipliers; the relative bias from phase errors; the gain on a constant baseline offset; the
  linearized errors of a joint amplitude and time fit), `hit-efficiency` (efficiency of a Landau or Gaussian signal
  with a charge fraction, noise and a Gaussian threshold spread, and the noise occupancy per sample and per window,
  channel-averaged in closed form; the operating window for an efficiency and an occupancy target; Landau from
  Nolan's integral for the stable law alpha = 1, beta = 1, scale pi/2), and `waveform-toy` (a seeded synthetic
  sampled readout with AR(1) noise, Poisson pileup, phase jitter and an ADC, reconstructed by four estimators, with
  closure z-scores against the analytic prediction; `status_label` synthetic), `s-curve` (binomial
  maximum-likelihood fit of a threshold scan with inverse-Fisher errors and the deviance, or the expected errors of a
  scan design) and `threshold-trim` (dispersion left by a trim DAC: uniform residual inside the range, the excess
  beyond it, DAC nonlinearity).
- `front-end-electronics-and-signal-processing.md`: continuous versus sampled noise occupancy and the threshold-spread
  average; efficiency with a fluctuating signal and the operating window (worked example); constrained optimal
  filters, the baseline gain, time from samples, the waveform toy; ToT inversion; bandwidth and rise time; digital
  pulse processing for spectroscopy; pulse-shape discrimination; the electronics calibration rewritten as an ordered
  chain (robust pedestals and the noise covariance, binomial S-curve fits and scan
  design, trim residual, templates and weights, calibration closure in simulation); new misconceptions and
  deliverables. The worked
  optimal-filter and phase-error numbers already on the page are now reproduced by the tool and pinned by tests.
- New reference `readout-digitization-and-overlay.md` (linked from `detector-simulation.md` and the front-end page):
  a nine-step digitization recipe, overlay and premixing rules (no noise counted twice, the sum before the
  nonlinearities, sub-threshold content lost by a suppressed overlay, same period, pileup counted once) and the
  closure checks that validate a digitization. Cross-links from `event-reconstruction.md` and
  `tracking-and-vertexing.md`; bibliography adds Jordanov and Knoll (1994) and Nolan (1997).
- Tests: `tests/skills/hep_detector/test_frontend_waveforms.py` (33 tests); `FrontendResponseContractTests` cover
  the five new operations.
- Sources: the constrained optimal filter cites the ATLAS liquid-argon paper arXiv:0709.1094, the overlay rules the
  HSF detector-simulation white paper arXiv:1803.04165 (bibliography entries added).
- **The charge-injection gain is not the signal gain (sci-fix FRONTEND-INJECTION-GAIN, S3).** The front-end page's
  calibration chain treated the gain from charge injection as the gain for sensor signals. An injected pulse has no
  collection time (so no ballistic deficit) and sometimes no sensor capacitance, so the two differ; the page now says
  to cross-check with a source or minimum-ionizing particles and lists the misconception. Sources: arXiv:1306.6756v2
  sec. II-C and arXiv:0912.2642v4 sec. 3.1.2, eq. 5 (the physics-to-calibration pulse ratio `M_phys/M_cali`), both
  read in full text; regression test `InjectionGainGuidance` in `test_frontend_waveforms.py`. Committed apart from
  the `feat:` calibration commit (maintainer decision D-C4).
- Developer document `docs/dev/frontend-electronics/frontend-reco-sim-calibration.md` (English, task format, passes
  `lint_task.py`): the evaluation, the completed work, and stages FE0-FE5 with isolated-worktree execution,
  acceptance criteria and open decisions.
- **Fixed: `frontend_response.py` exit code of an input error that names JSON.** The CLI serialized the result inside
  the input-error handler and took any `ValueError` whose message contained "JSON" for a non-finite result, so such an
  input error exited 1 (`failed`) instead of 2 (`invalid-input`). The result is now serialized after the input checks;
  a non-finite result still exits 1. Tests: `CommandLine.test_input_error_naming_json_exits_2` and
  `test_non_finite_result_exits_1` in `test_frontend_waveforms.py`. The bug is in 0.40.0 too; no input of 0.40.0 is
  known to reach it.

hep-detector front-end FE1: a tabulated signal for `hit-efficiency` (VALIDATION FRONTEND-FE1).

- `hit-efficiency --signal-model table --spectrum FILE`: a measured or simulated charge spectrum from CSV (`charge,density`
  or `charge,count`), for the low-side tail that a Landau model makes too thin. A density is linear between its points
  (trapezoid-integrated CDF), counts are bins with edges at the midpoints; the CDF is normalized over the table and is
  0 below and 1 above it; `--signal-fraction` scales the charge axis. `validity` flags thresholds outside the table and
  a table that ends above 1e-3 of its peak (its missing tail would raise every inefficiency). Every file problem is
  invalid input (exit 2, JSON), never a traceback. Tool contract: `spectrum` input (kind path); `frontend_response.py`
  is now in `MISSING_FILE_ARGS` of `tests/skills/test_cli_robustness.py`.
- Front-end page: one sentence on using the table for the low-side tail. Tests: `HitEfficiencyTable` (6 tests).

hep-detector front-end FE2: a measured noise covariance for `optimal-filter` and `waveform-toy` (VALIDATION
FRONTEND-FE2).

- `--noise-covariance FILE` (`{"covariance": [[...]]}`, one row per sample, units of the per-sample noise sigma
  squared; not with `--rho`) on both subcommands, read by one function: weights and predictions use the matrix plus
  the Campbell pileup term, and `waveform-toy` draws the noise as `L z` (Cholesky). A matrix that is not square of the
  sample count, finite, symmetric and positive definite is refused, never repaired (exit 2). New outputs `noise_model`
  (`ar1` or `measured`) and `noise_covariance_sha256` (SHA-256 of the compact JSON of the matrix as floats). With
  `--rho` the outputs are unchanged; a rho^|i-j| file gives the `--rho` numbers to 1e-12 (its Cholesky factor is the
  AR(1) recursion). Tests: `MeasuredNoiseCovariance` (5 tests).

hep-detector front-end FE3: batch S-curve fits (VALIDATION FRONTEND-FE3).

- `s-curve --scan-file FILE` (CSV `channel,charge,injections,hits`; not with `--charges`, `--injections`, `--hits` or
  `--design-*`): each channel is fitted as in the single fit. A channel whose fit raises goes to `failed_channels`;
  one that did not converge, has fewer than 2 points between 5 % and 95 % or p < 1e-3 goes to `excluded_channels`.
  The summary of the included channels gives the mean threshold, `threshold_sd`, `threshold_mad_sigma` (1.4826 MAD),
  `threshold_dispersion_corrected` = sqrt(max(0, sd^2 - mean sigma_T^2)) (0 with a `validity` note when the spread is
  not above the fit error) and the median noise, plus the count of fitted channels with p < 1e-3. `validity` warns
  when more than 5 % of the channels are excluded or failed; `note` says where the corrected dispersion goes
  (`threshold-trim --spread` before trim, `hit-efficiency --threshold-dispersion` after). File errors exit 2.
- Tests: `SCurveBatch` (6 tests, 60 Monte Carlo batches of 200 channels).

hep-detector front-end FE4: `hit-efficiency` fills simreco's `noise-digitization` (VALIDATION FRONTEND-FE4;
maintainer decision D-FE4: new options only).

- `hit-efficiency --simreco-channels N [--simreco-sides 1|2]` (one threshold, with `--peaking` and `--window`, signal
  fraction 1) also prints `simreco_noise_digitization` with the keys of the reco spec's tail source: `threshold` =
  threshold / reference signal (Landau MPV, Gaussian mean or table peak), `efficiency` = channel efficiency ** sides,
  `noise_hits_per_plane` = (occupancy upper bound x N) ** sides; and `simreco_derivation`. `--threshold-enc K` gives
  the one threshold in noise sigmas (K x `--noise`). Without the new options the output is byte for byte unchanged;
  the Geant4 adapter, simreco and its defaults, and the J15 and J16 records are not touched (adapter 0.5.0).
- Front-end page and Geant4 study protocol: one sentence each. Tool contract: inputs `threshold_enc`,
  `simreco_channels`, `simreco_sides`. Tests: `SimrecoBlock` (6 tests).

hep-detector front-end FE5: the front-end reference page split in three (VALIDATION FRONTEND-FE5; maintainer decision
D-FE5: two new pages).

- Moved without a content change: amplitude and time from sampled waveforms, pileup of pulses, photosensor readout,
  LAr TPC signal processing, digital pulse processing and pulse-shape discrimination to the new
  `skills/hep-detector/references/front-end-waveform-processing.md`; calibration and simulation of the electronics to
  the new `skills/hep-detector/references/front-end-calibration.md`. `front-end-electronics-and-signal-processing.md`
  goes from 40,480 to 24,202 bytes, under the 24,576-byte warning line, and keeps a "(moved)" pointer for each section until
  0.42.0 (recorded under `pointers` in `tools/wiring_known_gaps.json`); it is registered there as a hep-detector hub.
  Links into the moved sections, the `InjectionGainGuidance` test and the internal source of ledger entry
  FRONTEND-INJECTION-GAIN follow the move; the reference inventory is regenerated and the README counts forty-two
  references. After the move: the front-end page's introduction names the two pages, and links whose topic moved
  (Campbell pileup, SiPM saturation, dead time, sampled-waveform estimators) point to the new page.

hep-detector front-end: a simulated thin-silicon spectrum for the table signal model.

- `skills/hep-detector/assets/thin-silicon-300um-mu10gev.geant4-pai.csv` (with a provenance `.json`): journey J14's
  recorded Geant4 PAI run `mpv-pai` (10 GeV mu-, 300 um silicon) binned in 100 e, for `hit-efficiency --signal-model
  table`. Its low-side tail is far wider than Landau's (at 16 000 e and ENC 1000 e the inefficiency is 9.5e-4 against
  1.7e-6); status `unvalidated`, a simulation, not a measurement. Front-end page: one sentence. Tests:
  `HitEfficiencyGeant4Spectrum` (3 tests). Decisions recorded: review R720d9d2e80 slot S4 accepted as missing; FE1
  spectrum: this simulated table, no measured one.

## 0.40.0 (2026-10-25)

Minor release; contracts 3.13.0, `CORE_VERSION` 1.1.0 and geant4 adapter 0.5.0 unchanged. It ships the follow-ups
of the Geant4 program (#289-#292): `f4` refuses a refused study, search role rules 1.1.0 (TOF and calorimeter in the
geometry mapping's names, TOF plane overlap), and the control rule `declared-size/1` with `plan-controls`.

**Before you upgrade** (details in each entry below):
- `evaluate_design.py f4 --study` on a study whose `label --upgrade` was refused exits 3 and writes nothing.
- A new search spec names `rules_version` 1.1.0 and the new TOF and calorimeter parameter names; recorded 1.0.0
  searches still expand.
- A search design whose TOF plane overlaps another subsystem or a tracking plane is now invalid.

**Before you upgrade:** `evaluate_design.py f4 --study` on a study record whose `label --upgrade` was refused now
exits 3 (`upgrade-refused`) and writes no F4 evaluation; until 0.39.0 it wrote one that decided nothing. A script that
expected exit 0 there treats exit 3 like the `--label-spec` path's refusal.

- `check_geant4_study.py label --upgrade` keeps the reasons of a refused upgrade in the record
  (`extension.study.upgrade_refused`); a record labelled without `--upgrade` is unchanged.
- `evaluate_design.py f4` refuses such a record the way it already refused a refusal it ran itself, with the reasons and
  the record's gaps. An unvalidated study that was never labelled with `--upgrade` still gives a below-screening F4
  evaluation (ART-31).
- J15 and J16 regenerated: the refused 100 GV, charge-confusion and shower studies of J15 and the J16 confirmation
  write no F4 evaluation (`results.json` records `f4_written` and the exit), with no verdict change except that the
  rows lose the below-screening F4 entry; the J14, J15 and J16 study records name the new tool hash.

**Before you upgrade:** search role rules 1.1.0 rename the TOF and calorimeter search parameters to the
design-geometry mapping's names: TOF `layer_positions_m` (2 to 4 planes) and `layer_thickness_m` replace `n_layers`,
`scintillator_thickness_cm` and `path_m`; calorimetry-em `depth_x0` (the whole sampling structure), `passive_material`
and `front_position_m` replace `depth_X0`, `absorber_material` and `z_front_m`. A new search spec names
`rules_version` 1.1.0 and these names; a recorded 1.0.0 search still expands (1.0.0 is kept as `roles-1.0.0.json`).

- `evaluate_design.py search` (rules 1.1.0): the TOF flight path `path_m` (the F1 time-of-flight input) is derived from
  the plane positions; a calorimeter's sampling structure (`sampling_layers`, `passive_thickness_mm` in whole
  micrometres, `active_material`, `active_thickness_mm`) is derived from `depth_x0` and the passive material with the
  rule's template (20 layers of 5 mm scintillator), and its extent and budget come from that structure. A TOF or
  calorimeter the search sets therefore carries the geometry mapping's fields and can vary in Geant4 (follow-up of
  stage C2). `load_asset` reads an earlier version from `<stem>-<version>.json`.
- Tests: the search tests run on rules 1.1.0; `test_design_search_g4.py` decodes TOF plane positions and thickness and
  a calorimeter depth into an element_sim spec that passes `check-spec`; a 1.0.0 spec still decodes.

Control rule `declared-size/1` for the multiple-scattering reference (decided 2026-10-25, for new studies; the factors
1.25 and 1.5 are provisional). The default rule (`shift-window/1`: caught and |shift| <= 1.1 DL after the runs) and
every recorded study are unchanged.

- `geant4_benchmarks.py`: a benchmark's `control_rule` (validated; `declared-size/1` only for
  multiple-scattering-reference). Under `declared-size/1` each control's expected shift comes from its
  `injected_relative` through Lynch and Dahl's formula (`ms_expected_shift`); a control counts when caught and its
  expected shift is at most 1.5 x the planned detection limit (from the nominal run alone); the benchmark claims the
  largest detection limit a caught control demonstrated, max(DL, |shift|). New subcommand `plan-controls --config C`
  prints the planned limit and the +- injections for an expected shift of 1.25 x it, to declare before the control
  runs. The gap names an oversized or undeclared control.
- The Geant4 study protocol says to use the rule for new studies and why (the window is narrow against the scatter of
  a measured shift; a density change of DL moves the width only about DL/2). J15 at 100 GV and J16 at 1 TV keep the
  window rule and stay refused.
- Tests: `tests/skills/hep_detector/test_geant4_declared_size.py`.
- `declared-size/1` also covers `stopping-power` and `thin-layer-mpv`: the expected shift comes from Bethe at the
  shifted mid-slab energy and from the Landau-Vavilov Delta_p of the scaled areal density (the density effect kept at
  the spec density's parameters); the injection must be in the control's run record (effective config), as for the
  multiple-scattering reference. The modelled responses agree with J14's recorded Geant4 controls within 2 SE.
  `plan-controls --benchmark NAME`. `range` and `longitudinal-profile` keep the window rule (not modelled).
- `evaluate_design.py search`: TOF planes (rules 1.1.0; each plane centre +- half its thickness) are checked for
  overlap against the other subsystems' extents (a TOF that is their daughter excepted) and against the tracking
  planes; an overlapping design is invalid and not evaluated.

## 0.39.0 (2026-10-25)

Minor release, contracts 3.13.0, `CORE_VERSION` 1.1.0, geant4 adapter 0.5.0. It ships the Geant4 program (spec
`docs/dev/geant4-architecture/geant4-program.md`) stages A1, C1, A2, B1, B2, B3, C2 and C3 with their §A.8 checks
and G5 confirmations (#274-#287): Geant4 correctness fixes, automated candidate generation, the `element_sim`,
`simroot` and `simreco` programs, the F4 interface and qualification path, Geant4 search values with F4
confirmation, and journeys J15 and J16. The stage entries below list the details.

**Before you upgrade** (each stage's own list below has the rest):
- Geant4 study records written from 0.20.0 to 0.38.x with `validated-in-scope` can fail `validate.py --strict`
  (SFA-2026-039, SFA-2026-040): regenerate them, then redo their F4 evaluations with `evaluate_design.py f4 --replace`.
- `check_geant4_study.py summarize` is retired (use `adapters/geant4/assets/summary_from_csv.py`).
- Rebuild layered_sim (`geant4_run.py build-sim`): source hash keys, per-event seeding by default in `scan`, the
  moved `MiniJson.hh`.
- A `tracking-resolution` study is upgraded only through the qualification path; `charge-confusion` cannot be
  upgraded yet (D0-b). The adequacy table 1.2.0 (provisional) floors a qualified F4 resolution at 2 %.
- simreco 0.4.1 changes strip digitization and shower containment: reconstructions with noise-digitization differ.
- An evaluation that names a search run or reuses a Geant4 search seed is an error.

Geant4 program, stage A1 (correctness fixes; spec `docs/dev/geant4-architecture/geant4-program.md`, approved
2026-10-24). Contracts CV-A1 (sci-fix) shares the unreleased contracts 3.13.0 with stage C1: the new rules apply
natively from 3.13.0, and under `--strict` to older records that carry `validated-in-scope`. `CORE_VERSION` 1.1.0.

**Before you upgrade:** Geant4 study records written from 0.20.0 to 0.38.x with `validated-in-scope` can fail
`validate.py --strict` (advisories SFA-2026-039, SFA-2026-040): regenerate them with this version, then redo their F4
design evaluations with `evaluate_design.py f4 --replace`. `check_geant4_study.py summarize` is retired: write run
summaries with `adapters/geant4/assets/summary_from_csv.py` (study spec `observables` and `blocks`); `run` still reads
the legacy `geant4-run-summary/1` for old records. Benchmark configs name a `summary` and an `observable` for the
stopping-power, range, thin-layer and longitudinal-profile benchmarks, and `negative_controls` in both directions.

- Benchmark classes come from the contracts table `GEANT4_BENCHMARKS` (`geant4-grade-table`); `longitudinal-profile`
  is setup-matched (`geant4-setup-matched-class`). The scope check compares the controlled observable kind
  (`geant4-scope-kind`) and every scope dimension of the benchmark (`geant4-scope-missing-dimension`); a counted
  benchmark needs an isolated target whose configuration and `spec-v1` target hash `geant4_benchmarks.py` derives from
  the named run record and `contracts/dependencies.py` re-derives (`geant4-isolation`).
- The convergence gate needs every declared scan value (`geant4-gate-scan-completeness`) and is an equivalence test
  (`geant4-gate-iut`): unresolved or a missed se target is `incomplete` (exit 3), not `failed`.
- Batch-means SEs over K blocks replace the bootstrap (`geant4-batch-means-se`), exact intervals at low counts
  (`geant4-low-count-exact`), the MPV is the mean of three-point block modes (`geant4-mpv-estimator`); negative
  controls are judged on the observable in both directions (`geant4-control-shift`) with DL = tol + |rel| +
  t_0.977 se (`geant4-detection-limit`). New core modules `core/stats/distributions.py`, `batch_means.py`,
  `decisions.py`, `core/simulation/seeds.py`, `summary.py`, `estimates.py`; schemas `simulation_summary.json`,
  `simulation_observables.json`.
- Run records carry `evidence_role`, `point_id`, `logical_run_seed` and `seed_scheme` (seed hash H); a study refuses a
  repeated S; study records list `evidence_overlap`. The protocol states the stopping rule (`geant4-stopping-rule`)
  and the evidence correlation (`geant4-evidence-overlap`).
- `evaluate_design.py f4` passes `--label-run-record`, `--label-reference-record` and `--label-variations` to `label`
  and reports a refused upgrade or missing results as `incomplete` (`design-f4-label-passthrough`).
- J14 (`examples/geant4-thin-silicon`) re-recorded live with trial runs and planned event counts; both studies keep
  `validated-in-scope`; detection limits 0.0700 (MPV, was 0.0827) and 0.0394 (stopping power), caught in both
  directions. Test fixes: the J14 replay cache is forgotten at module teardown (D10); the study-spec benchmark enum and
  grades (D8).

Geant4 program stage C1 (automated candidate generation at F1), contracts 3.13.0 (CV-C1; the number is the stage's
placeholder and is fixed at release in merge order with CV-A1).

**Before you upgrade:**
- New subcommands `evaluate_design.py search` and `expand --search`; `expand` now takes `--scan` or `--search`.
- An evaluation whose `run_ref` names a search run is the error `design.search_point_not_expanded`.

Contracts 3.13.0 (minor; no capability added).

- `search_summary` in `ext_computational_run.json` (declared with hep-computing's agreement), with its field rules in
  `contracts/schemas/design_search_summary.json` and cross-field checks in `contracts/validate.py` (front and finalist
  indices name recorded points, finalists kept inline, a points file listed in `output_hashes`, no verdict, ranking or
  recommendation), applied from `SEARCH_SUMMARY_FROM` (3.13.0) on or in strict mode; `contracts/design.py` exempts a
  search run from the orphan-run rule and refuses an evaluation that names one (`design.search_point_not_expanded`,
  a new code rather than reusing `design.scan_point_not_expanded`). The search spec schema
  `contracts/schemas/design_search_spec.json` (`design-search-spec/1`; not an artifact).
- hep-detector: `evaluate_design.py search` builds the genome of a base candidate's slots and free parameters inside
  the role rules (`assets/design-search/roles.json` 1.0.0: tracking, bending, tof, calorimetry-em, rich; the
  materials table `materials.json` 1.0.0 dumped from Geant4 11.4.3 NIST materials), decodes it into overrides on the
  base candidate (an independent candidate when a subsystem is dropped), skips invalid designs (spacing, envelope,
  overlap, nesting), computes F1 search values in process with the tool contracts' tools (`main(argv)`, the same
  arguments as `run`), runs NSGA-II from Sobol designs and the designer's proposals (`proposer: llm`) with the exact
  hypervolume as the stopping rule (`scripts/design_search_lib/`, standard library, bit-for-bit reproducible), fixes
  up to `finalists.max` finalists from distinct topologies, checks them and a sample of points against `run`
  (relative difference at most 1e-12, else nothing is written), and records one `runs/SEARCH-*.computational-run.json`.
  It writes no candidate, evaluation, verdict or ranking. `expand --search` turns a finalist (only) into a candidate
  that must reproduce the point's effective digest; `run`, `budget` and `report` then treat it like any candidate.
- `multiple_scattering.py`, `pid_separation_power.py`, `cherenkov_angle.py` and `calorimeter_resolution.py`: `main()`
  takes `argv` (no change to `--help`, the tool contracts or the outputs).
- `references/system-design-workflow.md`: section "D2 Automated candidate generation" (when to search, the search spec,
  search values versus evaluations, `expand --search`, the winner's curse, the designer's limits, what the reply
  states); capability `detector-design` item DSD-SEARCH; routing case `dsd-direct-3` (no description change).
- Closure tests (gate G-C1): DTLZ2, plane placement, structure choice on Example A, reproducibility, consistency.

Geant4 program §A.8 checks for stages A1, C1 and A2 (VALIDATION GEANT4-A8-CHECKS): new problems run by agents that
did not write the code, `review.py` reviews of the Geant4 study protocol and the design workflow, and the fixes they
led to.

- layered_sim's own `summary.json` is now completed by `geant4_run.py` with the run fields hep-detector's study check
  reads (run id, role, seed scheme, spec hash, settings, dataset checks), so `check_geant4_study.py run` accepts it.
- `geant4_run.py scan`: S = H(study_id, role, point id) (`--study-id`, default the grid name; `--role`, default
  scan) for every point, also when the base spec declares per-event seeding; the workflow step passes S, role and point
  id to `run`, so the run records are hash-v1.
- `check_geant4_study.py`: the hadronic model table matches exact list names (a variant is unknown); the EM
  constructor comes from the suffix or the list itself (QGSP_BIC_HP family option 4, FTFP_BERT_TRV GS, LBE ignores
  suffixes); the study spec's `convergence_plan.observables` accepts any declared observable; optional `stopping_rule`.
- Rule `G4R-DATASETS` now applies (it tested a field that does not exist).
- The protocol and design workflow state the limits the reviews found; the code gaps are in a follow-up issue.
- Sci-fix ledger: GEANT4-STOPPING-RULE has its external source (gap closed).

Geant4 program stage A2 (shared headers and boundary artifacts): geant4 adapter 0.2.0. No contracts bump (the new
schema keywords are used by no contract schema; tree-v1 was already a CV-A1 hash scheme). Existing spec/1 files and
outputs are unchanged: the 26 recorded J14 specs give bit-identical CSVs with the new build (gate G-A2).

**Before you upgrade:**
- The keys of a run record's `simulation.program.sources_sha256` change once: from bare names (`Spec.cc`) to paths
  under `adapters/geant4/assets/` (`layered_sim/Spec.cc`, `g4sim/MiniJson.hh`), and the map now also covers `g4sim/`.
  `MiniJson.hh` moved from `layered_sim/` to `g4sim/`. Rebuild layered_sim (`geant4_run.py build-sim`).
- `geant4_run.py scan` writes specs with per-event seeding unless the base spec states `run.seeding`
  (`--seeding stream` keeps the stream).
- Benchmark configs may name the run's `column_map`; the benchmarks name semantic columns, so a study script or
  config that relied on a CSV column name in a refusal message sees the semantic name instead.

- `adapters/geant4/assets/g4sim/`: `SimHash.hh` (SHA-256, the seed hash H, Python `float.hex()` formatting,
  SplitMix64 and Box-Muller), `SimSeed.hh` (per-event seeds), `SimSummary.hh` and `SimObservables.hh` (the run summary
  accumulators and their JSON), `SimProbe.hh` (the effective-config probe), `SimMaterials.hh`, `SimPhysics.hh`,
  `SimCsv.hh` (moved from layered_sim unchanged), `MiniJson.hh` (moved); `selftest.cc` with
  `tests/adapters/test_g4sim.py` checks the Geant4-free headers against `core/simulation/` and Python.
- layered_sim spec/1 optional fields, in `validate_spec()`, `spec.schema.json` and `Spec.cc` together:
  `run.seeding` (`stream` or `per-event`), `run.logical_run_seed`, `output.observables`, `output.blocks`,
  `output.debug_observable_dump`. Per-event seeding reseeds event i at the start of `GeneratePrimaries`; with
  observables layered_sim writes `summary.json` (merged across threads through a `G4VAccumulable`; an event weight
  other than 1 exits 2). Every run also writes `column_map.json` (`simulation-columns/1`) and `probe.json`, from which
  `geant4_run.py` builds the effective config (schemas in `adapters/geant4/assets/schemas/`), stored once per
  `config_sha256` under `effective_configs/`.
- `geant4_run.py`: run records carry the summary, column map and effective config (hash and reference, with the
  geometry tree and its tree-v1 hashes), `seeding`, `argv`, `script_sha256` and `versions.plugin_release`; a run whose
  spec-v1 and tree-v1 isolation decisions differ is refused (exit 2); `chunk` lists the chunk's summary and
  `summarize` merges chunk summaries without reading a CSV.
- contracts: `geant4_tree_v1` (configuration and target hash from an effective config's geometry tree: physics only,
  names in `naming_sha256`, canonical daughter order), `geant4_tree_thickness_mm` and `geant4_configuration` (dispatch
  by `hash_scheme`); `contracts/dependencies.py` re-derives a benchmark's configuration by its `hash_scheme`.
  `contracts/schema.py` implements `maxItems`, `maximum`, `exclusiveMaximum`, `oneOf` and `not`; the schema-keyword
  test also scans the adapters' schemas.
- hep-detector: `geant4_benchmarks.py` and `check_geant4_study.py` read only boundary artifacts and name semantic
  columns, resolved through the run's column map or `assets/geant4-columns-legacy.json` for older runs; records from
  adapter 0.2.0 get a tree-v1 configuration (a probe that recorded nothing is a configuration gap);
  `check_geant4_study.py spec --effective-config` takes the thin-layer rule's minimum thickness from the geometry
  tree. `geant4_verify.py` counts placements and takes thicknesses from the tree when there is one.

Geant4 program stage B1 (`element_sim`, event files and geometry derivation): geant4 adapter 0.3.0, no contracts
bump (VALIDATION GEANT4-ELEMENT). layered_sim is unchanged and gives the same probe without a field.

**Before you upgrade:**
- `geant4_run.py`'s `SIM_SOURCES` is a map per program (`layered_sim`, `element_sim`, `simroot`, `g4sim`); a
  layered_sim run record keeps the same `sources_sha256` keys. Records name adapter 0.3.0.
- `geant4_run.py run` decides the program by the spec's `schema`; `build-sim --program element_sim` builds
  element_sim and simroot.
- `contracts/schema.py`: a `$ref` to another file from an adapter's schema (validated by absolute path) names the
  sibling file when one exists, else a file in `contracts/schemas/` as before.

- `adapters/geant4/assets/element_sim/`: the box-element program `element_sim` (spec `element_sim.spec/1`, schema
  `spec.schema.json`): elements given by world-coordinate centres and half-lengths, one level of nesting, repeated
  copies, roles (`passive`, `tracker-plane`, `tof-layer`, `calorimeter`, `calorimeter-active`,
  `calorimeter-passive`); uniform field regions with the stepper and driver built explicitly (`G4DormandPrince745` in
  `G4InterpolationDriver`), thread-local field managers attached with `SetFieldManager(fm, true)`, the maximum step on
  the field element and its daughters, `G4StepLimiterPhysics` with a field; a gun source (with an optional cycle of
  energies and directions; `gps` and `event-file` refused); per-event seeding only. Per event: deposits per element,
  primary path length per element (`plen_<element>_mm`), energy leaving the world (`escape_world_MeV`), the energy
  leaving the calorimeter mother by face (`leak_rear_MeV`, `leak_front_MeV`, `leak_lateral_MeV`), the first entry of
  every charged track into each tracker plane and TOF layer, and at level `hits` every step with a deposit. The same
  three boundary artifacts as layered_sim; the column map may name `root` columns (`ntuple`).
- Per-event ROOT file `events.root` (`element_sim.events/1`; levels `summary`, `crossings`, `hits`, the last limited
  by `max_events_hits`), written through Geant4's bundled g4tools (ROOT is not needed), merged by the MT master,
  never committed; the run record keeps its path, file sha256, `content_sha256` and rows per ntuple. A killed or
  timed-out element_sim run is incomplete (exit 3) and writes no record.
- `adapters/geant4/assets/simroot/`: `simroot info | dump | hash` reads event files with `G4RootAnalysisReader`
  (several files as one logical run, rows sorted by key, processes deduplicated, a duplicate key refused);
  `content_sha256` does not depend on threads or the split into jobs.
- `geant4_run.py check-spec` (schema and cross-field rules of `element_spec.py`) and `from-geometry`
  (`design-geometry/1` from `evaluate_design.py geometry` plus an `element_sim.realization/1` profile, schema
  `realization.schema.json`, mapping 1.0.0, to an `element_sim.spec/1`; byte-identical for the same inputs, with both
  inputs named by sha256 in `provenance`).
- `geant4_verify.py field`: the deterministic field check of charged geantinos against the analytic helix of the new
  `core/simulation/helix.py` (in-plane distance and TOF-layer time); `budget` and `balance` read element_sim runs
  (`balance --inject double-count-leakage` is element_sim's negative control).
- `g4sim/SimProbe.hh` records, for a field manager with a field, the field's class and value, the accuracy
  parameters and the actual driver and stepper classes, and lists the distinct field managers with the volume each
  was attached to; the field block enters the tree-v1 target hash.

Geant4 program stage B2 (`simreco`, tail sources, the F4 interface and the F4 qualification path): geant4 adapter
0.4.0, contracts CV-B2 in the unreleased 3.13.0 (`GEANT4_B2_FROM`), D0 as decided on 2026-10-24 (VALIDATION
GEANT4-F4). `CORE_VERSION` stays 1.1.0 (new `core.stats.decisions.change`, `core.simulation.estimates` estimator
`gaussian-core`, shared helix crossing comparison).

**Before you upgrade:**
- A detector-level study (`tracking-resolution`) is upgraded only through the qualification path: `material-definition`,
  `field-propagation`, `reco-closure` and `multiple-scattering-reference`, each matched by its own key in
  `validation_plan.scope` (`geant4_benchmarks.py scope-keys`); `charge-confusion` cannot be upgraded until a tail
  reference exists (D0-b). Other kinds keep the CV-A1 rule.
- `evaluate_design.py f4` takes the study's uncertainty object (coverage 0.90, statistical (+) replica spread; exact
  for counting) and writes the evaluation's own `geometry_ref`; `design.py check_f4` reads that geometry file and
  compares its denominator.
- `contracts/rules/design_geometry.json` is mapping 1.1.0 (optional fields); geometry files of 1.0.0 candidates keep
  their fields and digest.
- D0-c as decided on 2026-10-24: on a qualification path `label` widens the F4 uncertainty by the qualifying
  reference's tolerance, and the adequacy table (1.2.0, still provisional) gives such an F4 resolution the floor
  `f4_qualified_min_relative_uncertainty` (0.02, Lynch and Dahl's published accuracy) instead of 0.2.
- `design.py check_f4` validates the study record strictly and compares the study result's denominator.
- `label` refuses a qualification whose declared hash keys are not the study's own inputs, and results whose reco
  record is not an evidence record of the study; `simreco_spec.check` refuses a tail source that does nothing;
  `table` refuses a denominator that is not the simulated gun's and an observable on the wrong column.

- `adapters/geant4/assets/simreco/` (C++17, no Geant4, `-ffp-contract=off`; spec `simreco.spec/1`): point errors or a
  strip digitization, a Gauss-Newton fit of chained circle arcs with the multiple-scattering covariance in both
  projections, TOF beta and calorimeter energy, and four switchable tail sources (alignment and
  calibration-non-uniformity as M >= 20 reconstruction replicas, noise-digitization, pattern-recognition); a run
  summary (`simulation-summary/1`) whose `tail_sources_simulated` lists only the stages that ran. CI job `simreco`.
- `geant4_run.py reco` (simroot dump, simreco per replica, a computational-run with `extension.reconstruction`; the
  design geometry's point and time resolution replace the reco spec's) and `table` (a simulated dataset-record;
  `--f4-results` writes `f4-results/1` with the model envelope from `--variation` and the geometry's sha256).
- `check_geant4_study.py label --results --geometry` keeps the results, tail sources and geometry in the re-issued
  record and its manifest (a mismatched geometry exits 2); `evaluate_design.py f4 --label-results --label-geometry`
  passes them on, and a refused upgrade lists label's gaps.
- New benchmarks in the contracts table and `geant4_benchmarks.py`: verification `field-propagation`,
  `material-definition`, `reco-closure`, `tof-beta`, `tof-layer-consistency`; sanity `field-propagation-muon`,
  `sampling-fraction`; reference `multiple-scattering-reference` (a Gaussian fitted to the central 98 % against Lynch
  and Dahl, with density controls) and `ms-tail-reference` (not implemented); regression `regression-comparison`
  (decided by `change`, never affecting a label); evidence role `regression`; scope kind `hash`.
- `contracts/dependencies.py`: a simulated table may rest on a chain of recorded computational-runs whose every root
  is a simulation or study record (from 3.13.0).
- `from-geometry` realizes mapping 1.1.0's tracker material and size, field extent, TOF layers and calorimeter front
  face, depth and sampling (a profile declaring 1.1.0, with `calorimetry-em` radiation lengths for the depth check).
- Independent review fixes: the counted reference keeps the isolation check on the qualification path and its
  controls count only with the injection in their run records; `material-definition` also checks the passive slab
  and refuses a length mismatch or a material Geant4 did not resolve; simreco fits a missing plane with the
  path-weighted field and keeps its material, uses the particle's charge (rigidity 1/|rho|, Highland's z), takes the
  true beta from the primary's own crossings, and rejects malformed CSV rows (exit 2); the counting interval is
  centred on the replica mean.
- `simulation_observables.json`: estimator `gaussian-core` (`core_truncation_sigma`); the study spec schema gains the
  CV-B2 scope keys, `element_sim_spec`, the kinds `tracking-resolution` and `charge-confusion`, and material `z`,
  `a_g_mole`, `radiation_length_mm`.

Geant4 program stage C3 (examples): journey J16, `examples/design-search-j16` (VALIDATION
DESIGN-SEARCH-EXAMPLES). No contract or adapter version change.

- `examples/design-search-j16/`: the search on Examples A and B (F1, seeded NSGA-II), finalists expanded and
  evaluated, Example B's `capability.unavailable` requirements carried, reports and `search --diagnose`; one Example
  A finalist confirmed live at F4 (`live.py`, recorded): the upgrade was refused on the multiple-scattering
  reference's control (beyond 1.1 detection limits), shown as recorded; `space.realization.json` for Example A;
  `tests/examples/test_design_search_j16.py`.
- J15's `live.py` campaign takes the study prefix, the realization profile's name, the reference slab's thickness and
  the materials from class attributes (J16 reuses it; J15 unchanged).
- `evaluate_design.py`: the rows of `search_minus_official` (`search --diagnose`, `report`) carry `f4_qualified` for
  F4 evaluations, so an F4 evaluation of a study whose upgrade was refused is marked (it decides nothing).
- The optional Bayesian-optimisation backend (`adapters/design-bo/`) is not provided: Ax and BoTorch are not installed
  in either environment; the search runs NSGA-II.
- Docs: J16 in `docs/researcher-journeys.md`, `docs/maintenance.md`, the capability map and matrix, the design
  workflow's example; routing case `j16`.

Geant4 program stage C2 (Geant4 search values and F4 confirmation): geant4 adapter 0.5.0, contracts CV-C2 (in the
unreleased 3.13.0), VALIDATION DESIGN-SEARCH-G4.

- `core/stats/decisions.py`: paired mode (`paired_statistic`; `equivalence` and `change` accept `pairing="paired"`
  with per-block estimates of one seed_group); the default stays independent.
- `core/simulation/summary.py`: an observable declared with `values: true` keeps per-block raw values (`values_max`,
  `values_omitted`, merge rule concat); `core/stats/batch_means.py` `empirical_quantile` (Hyndman-Fan type 7), used
  by the quantile estimator when values are kept; `core/simulation/estimates.py` `block_estimates`;
  `core/simulation/seeds.py` `search_group_seed`, `confirmation_study_id`, `seed_uniqueness_problems`. Schemas
  `simulation_summary.json` and `simulation_observables.json` gain the optional fields.
- geant4 adapter 0.5.0: `g4sim/SimSummary.hh` writes values like the Python builder (element_sim, simreco,
  layered_sim); `geant4_run.py run --seed-group`; run records carry `simulation.blocks`.
- Contracts CV-C2: evidence role `search` and `simulation.seed_group`; `contracts/design.py` refuses an evaluation
  that reuses a Geant4 search seed (`design.contract_mismatch`) and a seed repeated outside one seed_group
  (`design.seed_reuse`); `check_geant4_study.py label` refuses a search run as study evidence.
- `evaluate_design.py search`: `budget.geant4 > 0` with a `geant4` block and `--geant4-work` runs S2 (Geant4 search
  values from short element_sim and simreco runs, `design_search_lib/geant4_values.py`, cached; generations in one
  seed_group with gate G-C2a; one survivor per topology; finalists `fixed_from: geant4`); `search --diagnose` writes
  `runs/DIAG-*` with each expanded finalist's F1 and Geant4 search values minus its official or F4 value; the
  report lists the Geant4 rows too.
- J15 `live.py`: a study's id comes from `study_id()` (a confirmation study derives it from the search).
- Docs: the D2 automated candidate generation section of `system-design-workflow.md`, the study protocol, the
  capability map and matrix.

Geant4 program stage B3 (the J15 design project): journey J15, `examples/design-minimal-spectrometer`, geant4
adapter 0.4.1 (VALIDATION GEANT4-J15). No contracts bump.

**Before you upgrade:**
- simreco's strip digitization draws a random strip-grid phase per plane and event, and gives hits the
  sharing-aware resolution sqrt((p - w)^3 / 12 p) (it was p / sqrt 12); `simreco_spec.check` refuses a digitization
  finer than the declared point resolution. Reconstructions with noise-digitization differ from 0.4.0.
- simreco's shower containment is the calorimeter's total deposit over the incident kinetic energy (it was 1 - net
  face leakage / E0, which upstream secondaries pushed above 1).

- `examples/design-minimal-spectrometer/` (J15): design-spec `j15-v1`, candidates `cand-N6`, `cand-N4`, `cand-N8`,
  realization profile (mapping 1.1.0), H1 and H2 decision records prepared by an agent and marked as needing a human
  signature; F1 and F2 evaluations checked against section B.4.2; `live.py` runs the Geant4 campaign (six tracking
  studies, charge confusion at 500 GV, shower containment with a four-point production-cut scan, the verification
  ladder, the multiple-scattering reference at 1, 100 and 500 GV) and writes `recorded/` (run records gzip-compressed,
  1.8 MB); `run.py` replays it offline (labels re-issued through the qualification path, F4 evaluations, report);
  `tests/examples/test_design_minimal_spectrometer.py`. The 1 GV resolution studies of all three candidates qualify
  and two pass `REQ-TRK-001` decisively; the 100 GV studies are refused (a reference control beyond its detection
  limit, recorded and not rerun); charge confusion is not qualifiable before D0-b; shower containment has no reference.
- element_sim: `field.max_track_time_ns` (spec and realization profile) kills tracks older than that in a field
  element (a looper in a vacuum field region never triggers Geant4's looper killer under a step limit).
- simreco: a test-only `tof.test_layer_offset_ps` (the negative control of the TOF bookkeeping benchmarks); a
  counting interval's lower side stops at zero after the replica spread is added.
- `geant4_benchmarks.py`: a reference benchmark whose control is caught but not at its claimed detection limit is a
  gap again (it raised a KeyError for detector benchmarks).
- `geant4_benchmarks.py --help` lists the detector benchmarks' config keys; the Geant4 study protocol says to declare a
  reference control with the injection Geant4 realizes, warns about single scattering's cost with a thick
  calorimeter and says to validate the whole artifacts_dir; the design workflow says `geometry` writes `geometry_ref`
  into the candidate (from the B3.9 independent-agent run).
- J15's `live.py export` writes `~` for the home directory in the recorded files and rewrites the sha256 citations
  of the files it changes (the packaging scan refuses private paths).
- Docs: J15 in `docs/researcher-journeys.md`, `docs/maintenance.md`, the capability map and matrix; routing case `j15`.

## 0.38.0 (2026-10-24)

Minor release, contracts 3.12.0. It ships the maintainer's decisions on the four spec questions left open by the M3
independent reviews of the detector system design loop, and automates CHN-16 (calibration residuals into the
measurement-spec) (#271).

**Before you upgrade:**
- **design-spec (contracts 3.12.0):** a derived requirement must name in `covered_by` the driving requirement whose H4
  disposition covers it, and a hard constraint must list its `subsystems`; a 0.37.0 design-spec without them now gives
  `design.derived_uncovered` or `design.constraint_scope_missing`. Write a new spec version with the fields.
- A candidate that lacks a subsystem in a hard constraint's scope can no longer pass it (`chain.incomplete`).
- **Adequacy table 1.1.0:** charge-confusion compliance counts a rigidity-scale-offset evaluation only when the measured
  offset covers the offset the requirement assumes; an exactly zero assumed offset (tolerance 0) can never be covered,
  so declare a realistic tolerance.
- New subcommand `evaluate_design.py calibration` (CHN-16).

Contracts 3.12.0 (minor; no capability added).

- Detector system design, follow-ups of the M3 reviews (decided by the maintainer): a derived requirement names in
  `covered_by` the driving requirement whose H4 disposition covers it (`design.derived_uncovered` otherwise; its
  inconclusive rows open that driving requirement at H4 and the report proposes the disposition "under" it); a hard
  constraint lists the subsystems it covers (`subsystems`, `design.constraint_scope_missing` otherwise; a candidate
  lacking one cannot pass it: `chain.incomplete` with the subsystem listed; the report shows the scope); adequacy table
  1.1.0 `upstream_value_checks`: a rigidity-scale-offset upstream counts for charge-confusion compliance only when
  |measured - assumed| + z sigma stays within the offset tolerance the requirement assumes (ADQ-02 value check);
  Example A states in its comparison basis note that the magnet is the same in every candidate (the outer planes sit
  outside it), so its mass is shared. Both examples now declare the constraint scope and Example B the covering driving
  requirement of its four derived requirements. CHN-16 automated: `evaluate_design.py calibration` propagates a
  candidate's calibration residual (rigidity scale or curvature offset parameter) through
  `propagate_scale_distortion.py` into yield shifts, up/down variations and covariance blocks (its run records the
  residual's parameter digest for incremental reruns) and writes a new measurement-spec version carrying them as a
  shape systematic for the Asimov fit; a subsystem without a calibration control sample is refused.
  `tests/skills/hep_detector/test_design_followups.py`.

## 0.37.0 (2026-10-24)

Minor release, contracts 3.11.0. It ships the detector system design loop of hep-detector (spec v2, milestones M0-M4,
#265-#269): design-spec, design-candidate and design-evaluation artifacts; verdicts, maturity, staleness, screening,
comparison basis, ranking and Pareto front derived by `contracts/design.py`, never written by hand; evaluations at
F1-F5 run from tool contracts by `skills/hep-detector/scripts/evaluate_design.py`; review gates H1-H4.

**Before you upgrade:**
- **Contracts 3.11.0:** three new artifact types (design-spec, design-candidate, design-evaluation); envelope
  `inputs[].binding: "parameters"` (a 3.10 reader refuses it rather than misreading a parameter-bound input as a stale
  hash); decision record 1.1.0 (design categories, `{"state": "not-applicable"}`, `dispositions[]`); tool contract
  1.1.0 design blocks; new optional fields on computational-run (`argv`, `script_sha256`, `parameter_digest`,
  `scan_summary`) and dataset-record (`design_measurement`).
- The design adequacy table (`contracts/rules/design_adequacy.json`) is an initial default until physics review: every
  pass is reported as provisional.
- The review axis is advisory: only a valid human design-baseline (H4) record sets it, and the actor kind is
  self-declared.
- Routing: no skill description changed; the routing contract and the static case set name the system design
  workflow under hep-detector (static routing passes; no live routing run for this release).

Contracts 3.11.0 (minor; no capability added).

- Detector system design, milestone M4 (design space): `evaluate_design.py scan` (OQ-18: a subcommand of
  evaluate_design.py) runs a figure of merit of one candidate over a parameter grid in a scratch copy and stores every
  point in one summary computational-run (`scan_summary`, new optional field of the computational-run extension) with
  the local elasticities at the candidate's own values; it writes no evaluation, is exempt from the orphan-run rule,
  and an evaluation that names a scan summary as its run is `design.scan_point_not_expanded` (AGG-08: unexpanded points
  support no verdict). `evaluate_design.py expand` turns one point into a candidate derived from the scanned one, to be
  evaluated and compared like any candidate (RSK-04: only points that enter comparison are expanded). Pareto front
  (`comparison_basis.pareto_axes`, new optional field of the design-spec extension; must include expected-precision,
  CHN-00): computed only when the basis holds and every surviving candidate has a non-optimistic evaluation per axis
  with the same fidelity vector and denominator (CHN-06, RPT-07); a candidate is dominated only beyond the combined
  1-sigma uncertainties; refused with every reason otherwise; never a global optimum. Both examples declare the axes and
  show the refusal (no expected-precision evaluations yet). `tests/skills/hep_detector/test_design_m4.py`.
- Detector system design, milestone M3 (engineering and review): the review axis (only a valid human design-baseline
  H4 record sets it: exact artifacts = the derived report and the evaluations it used, the report equal to the one
  recomputed now apart from the frozen MAT-05 exclusions, a disposition for every inconclusive driving requirement;
  the derivation says `baseline: draft` or `baselined`); F5 measurements (`evaluate_design.py f5` from a dataset-record's
  new optional `design_measurement`; decided only after a human `measurement-acceptance` record approves the dataset
  as it is and binds the candidate by the digest of the measured configuration, decision record artifacts may carry
  `binding: parameters` with a `parameter_digest`; a configuration that differs from the candidate is
  domain.mismatch); stale evaluations are no longer compared with their study or dataset (ART-61); budget coupling
  between subsystems (expression `parameters_all`, `design_estimates.py material-sum`, figure of merit
  `material-budget`; CHN-14); calibratability (`design.calibration_incomplete` without a control sample; CHN-16); the
  calorimeter design contract (`calorimeter_resolution` evaluate, optimistic; tool contract 1.1.0) and adequacy rows
  recorded as unavailable (hadronic energy resolution, trigger efficiency, pileup robustness). Example B
  `examples/design-collider-tracker` (synthetic-collider profile; tracking and ECAL only; the rest
  capability.unavailable, listed in the report and in an agent-prepared H3 record that a human must sign). Both
  examples' derived reports went through the hep-authoring independent review (agent review: advisory, not a review
  record by a reviewer other than the author in the sense of O04/O14). Open item OQ-15 is now complete (review axis,
  dispositions and F5 approval). From that review: a budget item cancels in the comparison basis only when both
  candidates carry the same subsystem (identical merged definition) with the same budget row (ART-15; Example A's
  shared magnet cancels and its equal-mass basis holds; Example B's lighter 2.0 T solenoid and coarser ECAL now carry
  their own masses and its basis does not hold), a refused ranking lists every reason (RPT-07), dispositions are
  proposed only for candidates that survive screening (a screened-out candidate and a derived requirement say why they
  have none; H4 asks dispositions for those candidates only), H4 sets the review axis only when no earlier gate flag
  is open (interpretation: H4 follows H1-H3), charge-confusion compliance also needs a rigidity-scale-offset
  evaluation (adequacy row; the missing-for-compliance list names each required upstream with its own compliance
  fidelity, F5 for the offset), decision records are named relative to the decisions folder's parent (no host path
  in a report), the basis names the F1 evaluations it uses (chosen by id) and how their uncertainty is formed, an
  unqualified F4 study or a stale or mismatched evaluation no longer counts toward the compliance threshold, and the
  rendering states the baseline state, that the H4 actor kind is self-declared (advisory, LIM-01), that screening
  comes from the verdicts, and "orphan runs: none". The reviews closed after three rounds with the maintainer's
  decision to close the escalated findings; follow-ups for the spec owner: a quantitative check of the
  rigidity-scale-offset evaluation against the assumed curvature offset, dispositions for derived requirements, the
  subsystem scope of hard constraints, and whether Example A should model a field length per candidate.
- Detector system design, milestone M2 (fidelity and sensitivity): parameter-level invalidation (envelope
  `inputs[].binding: "parameters"`, `contracts/dependencies.py` warns instead of stale, `contracts/design.py` compares
  `parameter_digest`: an evaluation goes stale only when a parameter it read changes; a forged digest is a contract
  mismatch); `evaluate_design.py` writes parameter-bound evaluations, `run --replace` (stale only), `--digest-only`,
  `--input-artifact`, and new subcommands `response` (F3 response assembly and a parametrized `response` artifact for
  forward folding), `geometry` (the Geant4 study geometry from the mapping table `contracts/rules/design_geometry.json`)
  and `f4` (an F4 evaluation from a study record, optionally re-issued by `check_geant4_study.py label --upgrade`).
  `design_estimates.py` gains `infield-acceptance` (F2 seeded helix Monte Carlo through offset apertures),
  `response-assembly` (F3) and `precision-from-result` (F3 expected-precision write-back from an Asimov
  statistical-result); a design contract for `toy_spectrometer.py` resolution (F2). design.py: F4 checks (upgraded
  study record, geometry digest, observable, value from the record, tail sources, model envelope compared end by
  end), the CHN-06 ranking on expected precision (refused unless the basis holds and the chains are non-optimistic
  with one fidelity vector and denominator), the missing-evidence list now names lower-fidelity entries of the same
  figure of merit. `run_workflow.py` records `argv`, `script_sha256`, `versions.plugin_release`, the NumPy version and
  an optional `parameter_digest`, and `--incremental` skips unchanged steps (never with an unknown release digest).
  Adequacy table: the four ADQ-07 rows (survival probability with its data validation, tracking and selection
  efficiency, rigidity scale and offset, low-rigidity bias; OQ-09); the acceptance minimum uncertainty 1% (OQ-05,
  provisional). Open items: OQ-03 (the binding field, the run's parameter_digest, the design-block keys
  `upstream_directions` and `input_artifact`, and the evaluation's `model_envelope` extend the unreleased 3.11.0),
  OQ-08 (the geometry mapping lives in `contracts/rules/`, the spec's alternative location, because it describes no
  command-line tool and every file in `contracts/tool_contracts/` is checked against a tool's `--help`), OQ-09, OQ-11
  (composites declare their own uncertainty). Physics note: two apertures in a uniform field have a charge-symmetric
  acceptance (Liouville and time reversal); a dog-leg needs at least three.
- Detector system design, milestone M1 (analytic MVP, F1 end to end):
  `skills/hep-detector/scripts/evaluate_design.py` (`run`: one design-evaluation from the tool contract that computes
  the figure of merit at the requested fidelity, its inputs recomputed from the candidate, denominator and upstream
  evaluations by `contracts/design.py`, the output, computational-run with `argv`, `script_sha256`,
  `versions.plugin_release` and generated config files, and a `capability.unavailable` evaluation when no evaluator
  exists; `budget`; `plan`; `report`: the design report as a `communication` artifact with a Markdown rendering,
  derived by design.py, `--omit` hides an evaluation from the rendering only) and
  `skills/hep-detector/scripts/design_estimates.py` (`budget-sum`, `straight-line-acceptance` of coaxial apertures,
  `pid-rejection` from a separation power and a working-point efficiency). Design contracts (tool contract 1.1.0) for
  `multiple_scattering` (Gluckstern MDR as an estimate with a 12% relative uncertainty; positional stack file
  generated from the candidate), `cherenkov_angle` and `pid_separation_power` (TOF; separation power, optimistic),
  `design_estimates` and the exact-fit MDR of `tracker_resolution` (optimistic). The tool contract design block gains
  the expressions `budget`, `object`, `zip`, `config`, `span` and species constants by `of`, and an `uncertainty`
  location; `contracts/design.py` checks generated config files against the run's input_manifest (ART-72) and the
  uncertainty against the contract, and checks the comparison basis only among candidates not screened out.
  Reference `skills/hep-detector/references/system-design-workflow.md` (usage levels L0-L2, stages D0-D4, verdict
  codes), linked from `detector-design-principles.md` (registered as a hub). Example A
  `examples/design-space-spectrometer` (AMS-like, public facts from the `experiment:ams-02` ledger: ams02:C93, C94,
  C112, C175): the M0 verdicts reproduced through evaluate_design.py, equal-mass basis checked, ranking not given.
  Routing set DSD (4 cases); capability `detector-design` extended (items DSD-M0, DSD-M1; OQ-17). Open items: OQ-01
  (entry under hep-detector with a hub link), OQ-04 (no candidate ranking in the first release), OQ-17, OQ-20 (public
  profile only).
- Detector system design, milestone M0 (verdict rules first; spec 1.0 of the Detector System Design Architecture v2):
  three artifact types `design-spec`, `design-candidate` and `design-evaluation`
  (`contracts/schemas/ext_design_*.json`) and the core vocabulary `subsystem_roles`; `contracts/design.py` derives
  compliance verdicts (the 18-row single-evaluation table RUL-01..RUL-18, row 18 proven unreachable by exhaustive
  enumeration), bound combination (CMB-*), per-requirement aggregation (AGG-*), maturity axes, staleness from
  `contracts/dependencies.py`, candidate screening, the comparison basis and the gate flags H1-H3, from the artifacts
  and the tool contracts only; the adequacy table `contracts/rules/design_adequacy.json` (initial default, every pass
  reported provisional until physics review). Tool contract 1.1.0 (positional arguments, config-file fields, the
  per-operation `design` block; `contract_version` 1.0.0 or 1.1.0) with design contracts for `tracker_resolution`
  momentum (optimistic only above the crossover rigidity, otherwise an estimate) and `charge_confusion_rate`
  gaussian-core (optimistic, zero curvature offset, upstream resolution a lower bound). Decision record 1.1.0 (six
  design categories, the seen marker `not-applicable` with its input-closure check, `dispositions[]`; `lineage.py
  decision` needs `--exposure` only without the marker). computational-run gains the optional `argv` and
  `script_sha256`. A SYNTHETIC three-candidate spectrometer project (`contracts/fixtures/design/spectrometer`,
  regenerated by `tests/contracts/design_fixtures.py`): the probe fails resolution (`bound.excludes`), the two
  reasonable candidates are inconclusive on resolution and charge confusion (`bound.direction`) with the missing F3,
  F4 and data-validation evidence listed. No skill entry point or `evaluate_design.py` yet (M1).
  Open items resolved with the spec's recommendations: OQ-02 (3.11.0), OQ-03 (one 3.11.0 note, extended by later
  milestones before a release), OQ-05 (passes provisional before freezing), OQ-06 (design-block and uncertainty key
  names in docs/architecture.md section 4), OQ-07 (fields read by gates or verdict rules are required), OQ-11
  (all-estimate chains feed central values; the composite declares its own uncertainty), OQ-12 (an excluded-adverse or
  orphan-run requirement is never pass; a fail stays fail with the code added), OQ-13 (`--decisions DIR`), OQ-15
  (schema, lineage, the not-applicable validator and H1-H3 flags now; review axis, dispositions and F5 approval in
  M3), OQ-16 (`tests/contracts/test_design_*.py`), OQ-19 (abstract factor states). Interpretation: the adequacy
  table's "with" conditions (e.g. data validation for charge confusion) are required upstreams once an evaluation's
  chain reaches the compliance threshold, so an F1 evaluation is still judged by its bound.

## 0.36.0 (2026-10-24)

Minor release, contracts 3.10.0 (unchanged). It completes the hadron-structure plan with its seventh module: PDF,
nPDF and FF fits on the hep-statistics side (S12 reweighting and profiling, S13 global-fit specification and review)
and their theory inputs in hep-theory.

**Before you upgrade:**
- **Routing:** the hep-statistics description names PDF reweighting/profiling and PDF fits and no longer lists
  "asymptotics" or "(saying if no shipped tool covers it)" (unpinned phrases). Static routing passes; the live routing
  run is pending the maintainer's approval.
- `covariance_fit.py` has a new multiplicative mode `t0` (`t0_prediction`, `t0_iterations`); existing modes are
  unchanged.
- Executing a complete global PDF fit is not provided (`global-pdf-fits` is documentation only).

- hep-statistics and hep-theory, hadron structure phase 7 (S12, S13, global fits):
  `skills/hep-statistics/references/pdf-fit-statistics.md` (chi2 and multiplicative uncertainties, tolerances, Hessian
  and replica uncertainties, reweighting, profiling, impact studies, review checklist) and
  `skills/hep-theory/references/global-fits-theory-inputs.md`; new scripts
  `skills/hep-statistics/scripts/pdf_reweighting.py` and `skills/hep-statistics/scripts/hessian_profiling.py`;
  `covariance_fit.py` gains the `t0` multiplicative mode (fixed prior prediction, optional iterations). Capabilities
  `pdf-reweighting-and-profiling` (S12, tool) and `global-pdf-fits` (S13, documentation: no fit is executed). The
  hep-statistics description names PDF reweighting/profiling and PDF fits; "asymptotics" and "(saying if no shipped
  tool covers it)" were trimmed (unpinned). Live routing pending approval. Routing set S12-S13 (4 cases).

## 0.35.0 (2026-10-23)

Minor release, contracts 3.10.0 (unchanged). It adds the sixth module of hep-theory's hadron-structure plan: small-x
physics and saturation (Th19), and exclusive processes, GPDs and diffractive DIS (Th20).

**Before you upgrade:** nothing to migrate. `dipole_lo.py` needs SciPy (core stack); `exclusive_kinematics.py angles`
rejects an off-shell recoil.

- hep-theory, hadron structure phase 6 (Th19 small x, Th20 exclusive processes and GPDs):
  `skills/hep-theory/references/small-x-and-saturation.md` (dipole factorization, GBW model, BK/JIMWLK and running
  coupling as rules, nuclei, status labels) and `references/exclusive-and-gpd.md` (DVCS kinematics, BMK and Trento
  azimuths, GPD properties and sum rules, diffractive DIS); sources read in full text 2026-10-23. New scripts
  `skills/hep-theory/scripts/dipole_lo.py` (SciPy, core stack) and `skills/hep-theory/scripts/exclusive_kinematics.py`;
  `sum_rules.py` GPD rules (`gpd-integral:<F>`, `gpd-ji`). Capabilities `small-x-saturation` (Th19) and
  `exclusive-and-gpd` (Th20); routing cases (4).

## 0.34.0 (2026-10-23)

Minor release, contracts 3.10.0 (unchanged). It adds the fifth module of hep-theory's hadron-structure plan: SIDIS,
fragmentation functions and TMDs (Th18), with a Gaussian-ansatz TMD theory profile.

**Before you upgrade:** nothing to migrate. `profiles/registry.json` lists one more theory profile and is close to its
3072-byte budget.

- hep-theory, hadron structure phase 5 (Th18, SIDIS and TMDs): `skills/hep-theory/references/sidis-and-tmd.md` (Trento
  conventions, SIDIS structure functions, collinear SIDIS at LO, TMD factorization rules, Gaussian ansatz, Sivers sign
  change, Drell-Yan q_T) and `references/fragmentation-functions.md` (sum rule, flavour assumptions, sets, spin and TMD
  FFs); sources read in full text 2026-10-23. New scripts `skills/hep-theory/scripts/sidis_kinematics.py` and
  `skills/hep-theory/scripts/tmd_gaussian.py`; `sum_rules.py ff-momentum`. Capability `sidis-and-tmd` (Th18); routing
  set Th18 (3 cases).
- Theory-domain profile `theory:tmd-gaussian-lo` (Gaussian-ansatz SIDIS F_UU,T and Cahn term, Sivers asymmetry with
  the SIDIS -> Drell-Yan sign change as a cited rule, Drell-Yan q_T shape; benchmark Anselmino et al. Eqs. 38-39 and
  64-67), registered in `profiles/registry.json`.

## 0.33.0 (2026-10-23)

Minor release, contracts 3.10.0 (unchanged). It adds the fourth module of hep-theory's hadron-structure plan:
polarized DIS (Th17), and the first two hadron-structure theory-domain profiles (DIS parton model with the O(alpha_s)
F_L; LO Drell-Yan with the O(alpha_s) angular coefficients and Lam-Tung).

**Before you upgrade:** nothing to migrate. `profiles/registry.json` lists two more theory profiles.

- hep-theory, hadron structure phase 4 (Th17, polarized DIS): `skills/hep-theory/references/polarized-dis.md` (g_1, g_2,
  asymmetries and depolarization factors, Bjorken, Ellis-Jaffe, Burkhardt-Cottingham and ELT sum rules, MS-bar/AB/JET
  schemes of Delta Sigma; sources read in full text 2026-10-23) and polarized rules in `sum_rules.py` (`g1-moment:p|n`,
  `bjorken-lo`, `ellis-jaffe:p|n`). Capability `polarized-dis` (Th17); routing set Th17 (2 cases).
- Theory-domain profiles `theory:dis-parton-model` (LO F_2 and the O(alpha_s) F_L derived in SymPy from the Moch,
  Vermaseren, Vogt coefficient functions; synthetic only) and `theory:drell-yan-lo` (LO cross section; O(alpha_s)
  angular coefficients and the Lam-Tung relation from Peng et al.'s quark-axis representation; benchmark Peng et al.
  Eq. 10), registered in `profiles/registry.json`.

## 0.32.0 (2026-10-23)

Minor release, contracts 3.10.0 (unchanged). It adds the third module of hep-theory's hadron-structure plan: nuclear
targets and nuclear PDFs (Th16).

**Before you upgrade:** nothing to migrate. `nuclear_combination.py combine` requires `"grid_kind": "bound-proton"` in
its parton file and refuses average-nucleon grids; `ratio` refuses a replica set over an external proton set and needs
the set's `prescription` for replica sets.

- hep-theory, hadron structure phase 3 (Th16, nuclear targets): `skills/hep-theory/references/nuclear-parton-effects.md`
  (per-nucleon conventions, isospin combination, isoscalar and deuteron corrections, the conventions of EPPS21,
  nNNPDF3.0, nCTEQ15 and nCTEQ15HQ, member-by-member nuclear ratios, nuclear effects by x region, non-nPDF effects;
  sources read in full text 2026-10-23), an nPDF section in `pdfs-and-lhapdf.md`, and
  `skills/hep-theory/scripts/nuclear_combination.py` (`combine`, `ratio`, `convert`). Capability
  `nuclear-parton-effects` (Th16); routing set Th16 (3 cases).

## 0.31.0 (2026-10-23)

Minor release, contracts 3.10.0 (unchanged). It adds the second module of hep-theory's hadron-structure plan:
Drell-Yan (Th15).

**Before you upgrade:** nothing to migrate. `drell_yan_lo.py xsec` implements photon exchange only and refuses Z
exchange; its `frames` subcommand refuses angular parameters outside the allowed domain (exit 1).

- hep-theory, hadron structure phase 2 (Th15, Drell-Yan): `skills/hep-theory/references/drell-yan.md` (LO cross
  section derived from PDG 2026 cross-section formulae; x_F definitions and rapidity frames; angular coefficients,
  Collins-Soper and helicity frames, frame-invariant combinations, Lam-Tung; NLO and resummation as rules; sources read
  in full text 2026-10-23) and `skills/hep-theory/scripts/drell_yan_lo.py` (`xsec` for photon exchange, Z exchange
  refused; `convert`, `frames`, `lam-tung`, `coefficients`). Capability `drell-yan` (Th15); routing set Th15 (4 cases).

## 0.30.0 (2026-10-23)

Minor release, contracts 3.10.0. It adds the first module of hep-theory's hadron-structure plan: unpolarized inclusive
DIS (Th14), with an entry page for the hadron-structure modules that follow.

**Before you upgrade:**
- **Contracts 3.10.0 (additive):** 13 new core convention keys for hadron-structure predictions, also listed in the new
  core vocabulary `conditional_convention_keys`; the theory-spec completeness warning skips them. A 3.9 reader warns
  on the new keys and its comparison gate treats them as not comparable.
- **Routing:** the hep-theory description names hadron structure (DIS, Drell-Yan, nPDFs, TMDs, small-x, GPDs) and no
  longer lists "units", "couplings", "scales" or "(its HEPData, CSV or FITS table)". Static routing passes; the live
  routing run is pending the maintainer's approval.
- **New out-of-v1 notices:** model calculations of PDFs, TMDs and GPDs (`hadron-models`), quarkonium production
  (`quarkonium-production`), jets in lepton-hadron scattering (`jets-in-dis`).

- hep-theory, hadron structure phase 1 (Th14, unpolarized inclusive DIS): new entry page
  `skills/hep-theory/references/hadron-structure-essentials.md` (registered hub; modules B-H marked planned) and
  `skills/hep-theory/references/dis-structure-functions.md` (NC photon, gamma-Z and Z, CC, neutrino; LO quark-parton
  model; heavy-quark schemes and thresholds, Georgi-Politzer target-mass corrections and higher twist as rules); sources
  read in full text 2026-10-23 (PDG 2026 Structure Functions review, Schienbein et al. 2008). New scripts
  `skills/hep-theory/scripts/structure_functions_lo.py` (LO F_2, xF_3, sigma_r and d2sigma/dx dy, dx dQ^2 from
  user-supplied parton values; every electroweak, sign and target convention an input; exit 2 on unusable input) and
  `skills/hep-theory/scripts/sum_rules.py` (momentum, number, Adler and GLS LO integrals with a convergence estimate and
  the extrapolations outside the table reported separately). Tests on constructed inputs only; they do not establish
  physical validity.
- Contracts vocabulary: 13 new core convention keys (`target_normalization`, `exchanged_bosons`, `electroweak_scheme`,
  `em_coupling`, `structure_function_signs`, `heavy_quark_scheme`, `factorization_scheme`, `target_mass_treatment`,
  `polarization_convention`, `xF_definition`, `rapidity_frame`, `azimuth_convention`, `log_accuracy`); additive, the
  contracts version moves to 3.10.0 at release. **Before you upgrade:** an older reader warns on these keys and its
  comparison gate treats them as not comparable.
- Capability map: `dis-structure-functions` (Th14, tool, in v1); out-of-v1 notices `hadron-models`,
  `quarkonium-production`, `jets-in-dis` with routing cases. Routing: the hep-theory description names hadron
  structure (DIS, Drell-Yan, nPDFs, TMDs, small-x, GPDs); "units", "couplings", "scales" and the "(its HEPData, CSV or
  FITS table)" parenthesis were trimmed (unpinned phrases). Static routing check passes; the live routing run is
  pending the maintainer's approval (paid calls). Routing set Th14 (8 cases).

## 0.29.0 (2026-10-23)

Minor release, contracts 3.9.0 (unchanged). It adds hep-theory's cosmic-ray phenomenology (Th13) with every source read
in full text, and architecture step 1: a wiring lint that keeps each skill's hand-kept lists in step.

**Before you upgrade:**
- **Removed:** `skills/hep-measurement/references/data-pipelines.md`, a pointer since 0.7.0; its content is in
  hep-computing's `analysis-data-pipelines.md`.
- **New static check `wiring`** (`tools/check_wiring.py`): a reference page not reachable from its skill's Resources
  table, entry routing part or a registered hub, a wrong README count or a misfiled CLI script now fails
  `run_all_checks.py --part static`. Adding a topic: `docs/maintenance.md`, "Adding a topic".
- **Routing:** the hep-theory description names cosmic-ray propagation and solar modulation (live routing on the 82
  cases that involve hep-theory: Claude 76/82, no regression against main; Codex 79/82).
- **CI:** the AMS-optionality job runs only the plan's modules in its suites (CI plan 1.1.0).
- **Budgets:** Resources tables may be 1.5-3 KB; the SKILL.md test limit is the budget's 12,288 B.

Sources (Th13): the three cosmic-ray pages' sources, first read through a summarizing fetch, were re-read in full text
(49 arXiv PDFs at the cited versions, the ICRC proceedings, the two Bartels sources) and every attribution, locator and
number was checked; about 30 statements were corrected (wrong locators, overstated or misread findings, author
initials and order) and the pages now carry the read level "full text, 2026-10-23" (VALIDATION TH13-SOURCES, ledger
`documentation_fixes` TH13-SOURCES). The DRAGON2 D_pp prefactor and beta^eta form, previously "not read", are now cited
(App. C.8-C.9); the "factor 2" LIS claim from an unopened 2005 paper was dropped. Journal references and all 16 DOIs on the
sources list were then confirmed at arXiv, INSPIRE-HEP and Crossref. Closed afterwards: the HAWC diffusion
coefficient (Table 1) and the Wilcox L and R tilt-model assumptions (the observatory's page) are now cited, the
antiproton "no newer determination" search is refreshed (2026-10-23), the 2021 AAfrag comparison is cited, and the
opt12/opt22 origin and Weinrich label differences between papers are noted. The Planck 2018 annihilation bound
(Sect. 7.9, Eq. 89c) is cited on the new-physics page, and Usoskin et al. 2005 (read from the authors' copy) again
supports the LIS factor-2 and linear-conversion statements (App. A, Eq. A4); no listed source remains unread.

Routing (T2): the hep-theory description names "cosmic-ray propagation and solar modulation" (1,020 of 1,024
characters; room made by dropping three phrases no routing case pins: "importing", "truncation", "and its global
analyses"). A new English case `th13-mod-2` (solar modulation) and the trigger term "cosmic-ray propagation" on
`th13-codes-1` pin it; 425 routing cases. Live routing (decision D7) on the 82 cases that involve hep-theory: Claude
76/82 (the misses are cases that missed before the change; a control on main shows no regression), Codex 79/82
(`evals/routing/README.md`).

CI: the AMS-optionality job is selected like the units shards. A pull request's plan (`tools/ci_plan.py`, plan 1.1.0)
lists `ams_optional_modules`, the selected test modules that are in that check's suites; the part runs when the list is
not empty, and `tools/check_ams_optional.py --plan` reruns only those modules (its fixed steps, a few seconds, always
run; an unselected suite is reported as skipped). Before, a bounded pull request never ran this check at all, even
when it changed modules in its suites, and a full one ran all of it. Profile changes name `part:ams-optional` in the
impact map, so they run every suite, and so do full plans and changes to `check_ams_optional.py` (now CI tooling). The
gate (`tools/reconcile_check_runs.py --plan`) fails an AMS-optionality run that did not run exactly the planned modules.

Removed: `skills/hep-measurement/references/data-pipelines.md`, a "(moved)" pointer since 0.7.0 (its removal release
0.29.0 was recorded in `tools/wiring_known_gaps.json`). The three hep-computing links to it now point to
`analysis-data-pipelines.md` (where the material moved) or, for the physics rules, to hep-measurement's
`analysis-design.md` and `weights-normalization.md`; the hep-measurement README counts twelve references.

Budget decisions D1-D3 and the last routing gaps of architecture step 1 (B4b):

- hep-authoring: the papers guide's "Reference files" section is now "Reference index" (same bytes), so the entry
  routing part names the reference index (2,377 -> 2,512 B), and the index is a registered hub. The 17 hep-authoring
  pages it routes to are reachable; `tools/wiring_known_gaps.json` lists no gap.
- D1: the Resources table limit (B-02, `tests/skills/test_routing_tables.py`) is 1.5-3 KB, up from 2.5 KB; B-03
  (SKILL.md plus entry reference, 25,600 B) stays the binding budget.
- D2: one SKILL.md size limit: the routing-table test reads `skill_bytes_target` (12,288 B) from
  `tools/measure_entrypoints.py` instead of its own 11,264 B, and honours `tools/budget_exceptions.json` waivers up to
  the 16,384 B hard limit; `docs/maintenance.md` says so.
- D3: B-03 margin restored to about 0.9 KB in the two skills that were at the limit (hep-measurement 11 -> 935 B,
  hep-statistics 19 -> 904 B). hep-measurement's guide condenses its script, asset and example lines (details stay
  in each script's `--help` and the README) and drops two lines that repeated SKILL.md (the blinding invariant) and its
  own handoff table; hep-statistics' core/stats guide keeps short fit-verdict and toy-tail rules and moves their
  detail to "Conventions in detail" in `core-stats-commands.md`.

Theory (Th13): cosmic-ray propagation and astroparticle phenomenology in hep-theory. Guidance on three pages and one
helper script; no propagation code is run and no fit to real data is tested.

- **`skills/hep-theory/references/cosmic-ray-phenomenology.md`**, the second propagation page: GALPROP, DRAGON2 and
  USINE and their diffusion-coefficient conventions (reference rigidity, beta^eta, units) and the reacceleration
  relation D_pp D_xx; transport degeneracies, benchmark families and halo-height determinations; the production
  cross-section sets (Webber family, Silberberg-Tsao, GALPROP opt12/opt22, the DRAGON2 recipe, renormalized OPT sets)
  with the sizes of their differences, the nuisance schemes in use (normalization-slope-shape with Gaussian priors,
  per-element normalization and slope with flat priors, sets as model alternatives), antiproton and secondary e+-
  production alternatives; the nuisance blocks hep-theory supplies to a global fit and how they travel in the
  theory-spec and prediction artifacts (statistics stay in hep-statistics). Sources: about 50, read 2026-10-20
  through a summarizing fetch, so under hep-citations' rule they are unverified (snippet level) until re-read in the
  primary source; the pages say so, and the unverified items are listed.
- **`references/solar-modulation-models.md`**: energy-dependent, empirically modified, charge-sign and drift
  (extended force-field) and numerical models; LIS dependence and recalibration of phi series; heliospheric inputs
  (tilt-angle models, averaging window, lag); polarity definition; aligning a model with monthly or Bartels-rotation
  data.
- **`references/cosmic-ray-new-physics.md`**: dark matter to antiprotons (how L, halo profile, local density,
  transport family and modulation move a signal; the reassessed antiproton excess as an example block) and to
  positrons, pulsars, and the checks before stating an interpretation. Interpreting an excess with a dark-matter
  model and global fits that run a propagation code stay outside v1.
- **`skills/hep-theory/scripts/bartels_rotation.py`**: dates to Bartels rotation numbers and back (27-day rotations from
  1832-02-08, WDC Kp/Ap format description; rotation 2426 = 2011-05-15 checked against the Caltech ACE table), and
  rotation averages of a daily heliospheric input with a declared lag and minimum coverage (exit 3 below it); dates
  must be YYYY-MM-DD (timestamps refused), a byte-order mark is accepted.
- Wiring: hep-theory Resources row and README; pointers from `cosmic-ray-propagation.md`; capability map
  (`cosmic-ray-propagation` gains Th13) and matrix row; five routing cases (set Th13); tests `test_bartels_rotation.py`,
  `test_cosmic_ray_phenomenology_th13.py` and the CLI-robustness inventory entry.

Maintenance (architecture step 1): a wiring lint for adding a topic. No schema, contracts, file moves or description
changes.

- **`tools/check_wiring.py`** (static check `wiring`): every reference page one step from its skill's Resources table
  or entry routing part, or two steps through a registered hub page (R1; a "(moved)" pointer page is exempt until
  its recorded removal release); `NO_INPUT_FILE` reasons are strings and name no script that reads a file argument
  (R2); README counts match their files (R3); with `--since REV`, added pages and scripts are named under
  Unreleased and a new capability id has a matrix row (R4). Report mode: exit 1 only on a gap not listed in
  **`tools/wiring_known_gaps.json`** (hubs, pointer releases, README count patterns and the existing gaps; it only
  shrinks). Tests in `tests/tools/test_check_wiring.py`; checklist "Adding a topic" in `docs/maintenance.md`.
  `tools/reference_inventory.py` does not count the known-gaps file as citing the pages it lists.
- Routing fixes that add no SKILL.md or entry-reference bytes (B4a): hub pages registered (hep-theory
  `cosmic-ray-propagation.md`, so the two Th13 pages it links are reachable; hep-ml `deep-learning-guide.md`;
  hep-computing `agile-development-guide.md`, `task-authoring-guide.md`, `batch-scheduling.md`; hep-detector
  `detector-simulation.md`; hep-authoring `academic-papers-guide.md`, `academic-diagrams-guide.md`), and README counts
  corrected (hep-computing 35 references and 18 helpers, hep-ml 42, hep-statistics 13 references). The 17 hep-authoring
  pages reached only through its reference index stay known gaps until that index is one step away (a Resources or
  entry-reference change, pending the budget decisions).
- CLI dictionary (R2): three scripts that read a file named by an argument move from `NO_INPUT_FILE` to
  `MISSING_FILE_ARGS`, so a missing file is tested: `tag_and_probe_efficiency.py` (`--probes`, `--bins`; it already
  refused with a JSON status), `estimate_training_memory.py` (a plan file; JSON status `rejected` with `--json`) and
  `solar_modulation_force_field.py` (`--lis-table`), which now prints every invalid-input error as a JSON object with
  status `failed` and `error_kind` `invalid-input` on stdout (usage still on stderr, exit 2); its CLI-contract case
  gains a malformed-table check.

## 0.28.0 (2026-10-23)

Minor release, contracts 3.9.0. It completes the cross-artifact check's Shrink by removing the suites that 0.27.0
deprecated.

**Before you upgrade:**
- **Removed:** `model-card` and `run-lineage`, model-only bundles (`--mode model`) and result bindings (`--results`,
  `--project`).
- **Refusals:** a context, bundle, CLI option or report that uses them is refused with the reason. Reproduce such
  reports with 0.27.x.
- **Remaining:** the check runs `counting-chain` (frozen) and `ratio-subset`, and stays experimental and advisory.

- **Cross-artifact check: `model-card` and `run-lineage` removed (value gate Shrink, architecture section 13.4).**
  - **Removed:**
    - `contracts/analysis_checks/model.py` and `runs.py`, and their suites (every version);
    - the model-card pairing contract and the result-binding schema;
    - model-only bundles (`--mode model`), `check --results` and `--project`;
    - the permit's post-execution checks.
  - **Reports:** they are now always pre-execution.
  - **Readers refuse the removed formats** with the reason, and every refusal names 0.27.x as the release that still
    reads them (`docs/dev/cross-artifact-check/refusal-matrix.md`):
    - `bundle.removed` at freeze;
    - `definition.suite_removed` at check;
    - a usage error for `--results` and `--project`;
    - `permit.report_post_execution_removed` for a post-execution report.
  - **Registry:** the 9 rule versions are retired. Their V-case parts are `not-run` with the removal recorded.
  - **Docs:** the skill references no longer teach them. Preservation now asks for the run and merge records.
  - **Kept:** `counting-chain` (frozen), `ratio-subset`, `custody.py`, and the separate pyhf SR/CR model-card adapter.

## 0.27.0 (2026-10-23)

Minor release; contracts unchanged (3.8.0). It deprecates two suites of the experimental cross-artifact analysis check
after the value gate's Shrink decision.
- **Deprecated:** `model-card` and `run-lineage`, together with `--mode model`, `--results` and the result binding.
  They are removed in 0.28.0, so reproduce such reports with 0.26.x or 0.27.x.
- **Kept:** `counting-chain` (frozen) and `ratio-subset`.

- **Cross-artifact check shrunk: `model-card` and `run-lineage` are deprecated (value gate Shrink).**
  - **Measurement:** the value gate, re-measured on 0.26.0, still found no error the checker catches that the
    closure tests and contract checks miss (I = 0 of 28, AI-planted; `docs/dev/cross-artifact-check/
    decision-value-gate.md`).
  - **Decision:** the maintainer chose the architecture's Shrink.
    - `counting-chain` is kept but frozen (no new rules).
    - `ratio-subset` is kept.
    - `model-card` and `run-lineage` (with `--mode model`, `--results` and the result binding) are deprecated now and
      removed in the next minor release.
  - **Notice:** the check CLI prints a deprecation note on stderr when a context selects them; reports are unchanged.
    The registry marks their rules `deprecated`.
  - **Reproducing reports:** reproduce such reports with 0.26.x.
  - **Unchanged:** `custody.py` stays under the assurance-plane exemption. Every rule stays in shadow mode, and the
    check stays experimental.
## 0.26.0 (2026-10-23)

Minor release, contracts 3.8.0: the cross-artifact analysis check's Phase 2 (releases R2 and R3 together) and
selective pull-request CI. The check stays experimental and in shadow mode; reports are advisory.

**Before you upgrade**
- **The stable 1.1.0 suites are now the default.**
- **1.0.0 suites:** they give `check.rule_not_run` for every fixed rule:
  - `r-rep.repetition`, `r-ratio.correlation` and `r-comp.factor_values`;
  - `r-aux.use`;
  - `r-run.binding`, `r-run.blinding` and `r-run.campaign`.

  So a 1.0.0 counting-chain, ratio-subset, model-card or run-lineage check is `incomplete`. **Reproduce 1.0.0 results
  with hep-research 0.25.x.**
- **Converting frozen work:** convert a frozen 1.0.0 context with
  `contracts/migrate.py --convert check-context=context-1.0.0-to-1.1.0`. A context with `required: false` is refused
  and needs manual completion.
- **Bundles frozen with 0.25.x:** they show lock differences (rule registry, effect catalog) and are reproduced from
  their snapshots (`--snapshots`).
- **Spec vocabulary:** `response_corrections` gains `cutoff_transmission`, `survival` and `fragmentation_feeddown`
  (additive). Under the 1.1.0 rules every correction a recipe step applies must be described in the spec (only
  `bin_width` is exempt).
- **AMS-02 example:** the flux-ratio example spec now describes the corrections its recipe applies.
- **Older readers:** a 0.25.x reader refuses check-context 1.1.0, result binding 1.1.0 and registry 1.2.0 as invalid
  input.

- **Cross-artifact check, release R3: stable 1.1.0 suites, the new default.**
  - **Suites:** `counting-chain`, `ratio-subset`, `model-card` and `run-lineage` 1.1.0 carry every R2 and R3 rule fix.
    `check-report` accepts them and refuses the `1.1.0-dev.N` pre-releases.
  - **Conversion:** `migrate.py context-1.0.0-to-1.1.0` now moves a context to 1.1.0.
  - **1.0.0 suites:** they still give `check.rule_not_run` for every fixed rule. Reproduce 1.0.0 results with
    hep-research 0.25.x.
- **Cross-artifact check: full mutation testing (V76), and the report check refuses hand-edited states.**
  - **Operators:** all nine mutation operators (relabel, rename, copy, copy+perturb, drop, loosen, toggle-optional,
    reorder, edit-report) run on the chain, reduced, ratio and model cases. Every invariant holds.
  - **Report check:** edit-report showed that `permit.py` accepted a report whose failing states were edited to
    satisfied with a recomputed summary. The report check now also requires each obligation's state to match its
    reason code under the rule's outcome contract (`permit.report_inconsistent`).
  - **Remaining gap:** an edit that also uses valid reason codes needs the report to be re-judged (the assurance plane,
    design only).
- **Cross-artifact check, release R3: a correction a step applies must be in the spec (G1, DR-8, V86), and the factor
  obligation no longer depends on the mapping key (G14, V87).** The new rule `r-real.undescribed` runs on generator
  `counting-chain-obligations` 1.1.0 and the effect catalog 1.1.0, in the suites `1.1.0-dev.5`.
  - **Rule:** every effect a recipe step applies must be described:
    - background by a non-empty `backgrounds` block (`no_backgrounds_reason` with an applied background contradicts it);
    - exposure, luminosity and livetime by the observable's normalization kind;
    - any other effect by a spec correction of exactly that category;
    - `bin_width` needs nothing.
  - **Scope:** per the maintainer's decision, every catalog effect except `bin_width` is `description_required`.
  - **G14:** the generator builds the factor obligation for a table bound under the composition's parent or any child
    key.
  - **Catalog compatibility:** coverage contracts written for catalog 1.0.0 still read; the version check is now SemVer
    compatibility, not equality.
  - **Vocabulary:** `response_corrections` gains `cutoff_transmission`, `survival` and `fragmentation_feeddown`.
  - **AMS example:** the AMS-02 flux-ratio example spec now describes the livetime, cutoff fraction, survival and (exact
    zero) fragmentation feed-down corrections its recipe applies; its artifacts are regenerated.
  - **Lock pins:** bundles frozen against catalog 1.0.0 show a catalog lock difference and are reproduced from their
    snapshots.
- **CI plan: a changed test helper selects the tests that import it.** A non-test `.py` file under `tests/` (for
  example `analysis_check_cases.py`) now selects every test module that imports it by name. The impact map listed
  the helper but not all of its importers, so three of them would have been skipped. A helper that no test module
  imports by name gives the full run.
- **CI: pull requests run only the checks their changes need.** A new `plan` job (`tools/ci_plan.py`) maps the
  changed files through the impact map in `contracts/rules/registry.json` to test modules and check parts. Each checks
  job runs `run_all_checks.py --plan`, and a job with nothing selected skips installing and still writes its record.
  The `checks-complete` gate recomputes the plan, and `reconcile_check_runs.py --plan` fails a run made under another
  plan, a part whose selection disagrees with the plan, or shards that do not cover exactly the selected modules.
  - **Full-run fallback:** a file outside the plugin, CI tooling, a path no impact group covers, or an unreadable
    diff gives the full run. Pushes to main, the weekly and manual runs stay full.
  - **Example:** a cross-artifact rule fix like #228 runs 12–18 test modules and the static part instead of every
    module and the AMS-optional part.
  - **Limit:** `check_ams_optional.py` now has its own 1200 s limit (it had reached 600 s on CI runners).
  - **Tests:** `tests/tools/test_ci_plan.py`.
- **Cross-artifact check: Phase 2 may start.** The maintainer changed the value gate's decision from Stop to
  Continue (`docs/dev/cross-artifact-check/decision-value-gate.md`). The measurement is unchanged (no incremental
  detection in 28 AI-planted errors) and the gate is not passed, so every rule stays in shadow mode and the check
  stays experimental until Phase 2 releases its fixes. No behavior change.
- **Cross-artifact check, release R2 formats (Phase 2).** check-context 1.1.0 removes `required` from roots and ratio
  roots (DR-2: deferral only through an exception) and is paired with suites at or above 1.1.0 (`bundle.context_version`
  at freeze, input-invalid at check); a 1.0.0 context keeps the 1.0.x suites. Every suite exists as the pre-release
  `1.1.0-dev.1` with the 1.0.0 rules, so outcomes do not change. `contracts/semver.py` reads SemVer pre-releases
  (`parse_full`, `is_prerelease`, `precedence`) while `parse` and ranges stay release-only. The rule registry schema
  1.2.0 keys rules by (rule_id, version) and keeps retired versions listed. `migrate.py` converts a frozen context with
  `context-1.0.0-to-1.1.0` (V90) and refuses a deferred root. V77-V90 are registered. A 0.25.1 reader refuses a 1.1.0
  bundle as invalid input.
- **Cross-artifact check, input checks of check-context 1.1.0.** A 1.1.0 context is input-invalid (refused at freeze)
  for a malformed factor table or tolerance (`calibration.shape`, G16), two different bundle coverage contracts for one
  table (`coverage.duplicate_contract`, G15), a shared parameter inside one model (`context.shared_within_model`,
  G12), and a blank or placeholder root unit (`context.unit_placeholder`, G22). 1.0.0 contexts are not judged by
  these checks. Probes G2, G12, G15, G16 and G22 now pass; V78, V80, V81, V89 and the G16 part of V79 pass.
- **Cross-artifact check, first rule fixes: outcomes no longer depend on input order (G3, G17, V77).**
  `r-ratio.correlation` 1.1.0 reads every complete validation record for a claim, so one contradicting record gives
  `violated` whatever the item IDs (1.0.0 took the first record by ID). `r-rep.repetition` 1.1.0 reads every
  `partition_exclusive` declaration naming both scopes, so one contradicting declaration gives
  `check.exclusion_contradiction` and every such declaration is listed. Rules are dispatched by a per-rule version
  table; the rule registry moves to 1.2.0, with the two 1.0.0 entries marked `retired` beside the new `changed` 1.1.0
  entries. The fixed rules ship in the pre-release suites `1.1.0-dev.2`, and `migrate.py context-1.0.0-to-1.1.0` now
  moves each suite to the newest installed 1.1.0 version. **The stable 1.0.0 suites now give `check.rule_not_run` for
  these two rules** (P3: an old version is never run with new code), so a 1.0.0 counting-chain or ratio-subset check is
  `incomplete`. To reproduce a 1.0.0 result, use hep-research 0.25.x (release R1). Measured on the Phase 0 comparison
  set (403 obligations): on 1.0.0 only the 96 `r-rep.repetition` and 3 `r-ratio.correlation` obligations change, all to
  `rule_not_run`; on dev.2 only G3 changes (both orders are now `violated`).
- **Cross-artifact check: a factor table no longer chooses its own tolerance (G4, DR-6, V79).**
  `r-comp.factor_values` 1.1.0 ignores the table's `tolerance`. The relative tolerance is 1e-9 unless the table
  declares `significant_digits` d (an integer from 1 to 17; shape-checked for 1.1.0 contexts) and every value of the
  relation has at most d significant digits. It is then Σ|power| · ½·10^(1−d), counting the parent's power as 1, which
  bounds the effect of rounding every value to d digits. A declaration that the values contradict is not used. Each
  outcome reports the tolerance it used and its basis. The rule ships in the suites `1.1.0-dev.3`, and the 1.0.0
  suites give `check.rule_not_run` for it. On the Phase 0 comparison set, on dev.3 only the G4 case changes (a
  tolerance of 0.6 no longer hides 3.0 against 1.0 × 2.0); on 1.0.0, the 4 `r-comp.factor_values` obligations also
  become `rule_not_run`.
- **Cross-artifact check: a copied observation file is the same observation (G5, DR-3, V85).** `r-aux.use` 1.1.0
  identifies an auxiliary observation by its source identity plus pointer instead of the item ID. The source identity
  is an artifact envelope's `artifact_id`, or otherwise the item's frozen canonical digest (the bytes for a non-JSON
  file). A copy bound under a second aux_id is therefore `check.aux_repeated`. Values are never compared, so a copy with
  one key added is still a different source (a known limitation). The rule ships in `1.1.0-dev.3` (the model-card suite);
  the 1.0.0 suite gives `check.rule_not_run` for it.
- **Cross-artifact check: blinding by lineage and the project's blinded list; declarations stay flagged (G7, G13, G8,
  A3; DR-7, DR-9, DR-1; V83, V84, V88).**
  - **G13, `r-run.blinding` 1.1.0:** blinding applies when the spec's flag says so or when the project's `blinded`
    list names the spec's `artifact_id`.
  - **G7, `r-run.blinding` 1.1.0:** a blinded result is permitted by the lineage of the run that produced it, never
    by its own status label. Every data leaf must be a dataset record with dataset status `synthetic` or
    `simulated`; otherwise the project's `allowed_outputs` must name the result.
    - No data leaf gives `check.lineage_no_data`.
    - A leaf without a dataset status gives `check.lineage_status_unknown`.
    - A result no run produced, including a campaign result until G6, gives `check.blinding_label_only`.
    - All three are unverified.
  - **G8, `r-run.binding` 1.1.0:** the binding's own `asserted_by.kind: person` no longer removes the declaration
    flag.
  - **A3, check-context 1.1.0:** an outcome that read a coverage contract supplied by the bundle is
    declaration-based (`coverage-contract:<table_id>`).
  - **G6, `r-run.campaign` 1.1.0 and result binding 1.1.0 (V82):** each campaign in the binding lists its `inputs`
    with their sources. It is campaign-recorded only when every input matches its source and at least one is an
    analysis item.
    - A digest mismatch gives `check.closure_mismatch` (violated).
    - Missing inputs or no analysis item is unverified.
    - Campaign results are judged for blinding through these inputs.
    - An installed 0.25.1 refuses a 1.1.0 binding as invalid input.
  - **Suites:** these rules ship in `1.1.0-dev.4`. The 1.0.0 suites give `check.rule_not_run` for the three run rules.

## 0.25.1 (2026-10-22)

Patch release: the cross-artifact check's value gate and the owner's Stop decision; no artifact contract change
(contracts 3.7.0) and no behavior change.

- **The cross-artifact analysis check is experimental.** Its value gate (`docs/dev/cross-artifact-check/
  decision-value-gate.md`; harness in the repository's `evals/cross-artifact-value-gate/`) found that it caught none
  of 28 AI-planted errors that closure tests and contract checks missed. The owner chose to stop: the checker code is
  frozen, no suites are added, and the README, the skill references that teach `freeze` and `check`, and
  `review_measurement_spec.py --check-bundle` now say it is experimental. Behavior is unchanged.

## 0.25.0 (2026-10-22)

Phase 0 of the cross-artifact check architecture (`docs/dev/cross-artifact-check/`, release R1): foundations of the
opt-in analysis check. No rule outcome changes: the same 403 obligations over 22 cases give the same state and
reason as on 0.24.1. Every rule stays in shadow mode.

- **Rules run only at their own version.** The check dispatches rules by (rule_id, version); an obligation whose rule
  version this checker does not implement is unverified (`check.rule_not_run`) instead of being evaluated with other
  code. Suites name a supported obligation generator (freeze refuses another one, `bundle.generator_unsupported`),
  and input checks are enabled per check-context version.
- **Rule registry 1.1.0.** Each rule version records the source digest of its code (`source_sha256`);
  `rule_registry.py check` fails when the code changes without a new version. New V cases V72–V76.
- **The status agrees with the exit code.** A report with a missing dependency or with definitions that differ from
  its semantic lock is never `complete` and exits 3.
- **Snapshots are on by default.** `freeze` stores the pinned definitions in `<root>/.hep-research/snapshots/` and
  lists the bundle in `<root>/.hep-research/bundles.json` (`--no-snapshots` turns this off); `check` uses that store;
  `analysis_check.py snapshots gc` deletes only unreferenced snapshots (dry run unless `--apply`). Bundles frozen
  earlier without snapshots now report `lock_differences` (the registry changed) and are reproduced with the
  release that froze them.
- **Report identity.** The checker identity covers every plugin module loaded at run time; the generator digest
  covers the generator, the model-card subjects and the effect catalog; `assessment.plugin_release` names the
  release.
- **`permit.py check-report` refuses more without a rerun:** `permit.report_dependency_missing`,
  `permit.report_lock_differences`, `permit.report_prerelease_suite`, `permit.report_inventory_mismatch` (a report
  whose obligations or suites are not the bundle's frozen inventory).
- **Renamed code-name identifiers** (DR-15): `docs/dev/v6.3/` is now `docs/dev/cross-artifact-check/` (a forwarding
  README stays at the old path), the `test_v63_*` modules are `test_analysis_check_*` and `tests/core/test_evidence_query`,
  done with `tools/rename_analysis_check_ids.py`.
- **Records:** the architecture (English and Chinese), `decision-architecture.md` (DR-1 to DR-15),
  `decision-value-gate.md` (thresholds proposed, to be confirmed before measuring), `decision-phase0.md`,
  `g21-classification.md`; gap probes G1–G22 (`tests/contracts/test_cross_artifact_check_gap_probes.py`).

## 0.24.1 (2026-10-22)

Patch release: sci-fix evidence and tooling after the improvement plan; no artifact contract change (contracts 3.6.0).
Statistical-results record which core/stats code produced them; every ledger oracle runs weekly with all its backends;
three C3 entries gain an oracle that does not come from a transcribed formula.

- **Statistical-results show which core/stats code produced them.** The seven core/stats CLIs add `trace`
  (`code_paths`, `code_tags`) to their JSON result, and `result_artifact.py`, which wraps that output from another
  process, joins it to the artifact's `provenance` (entries that are not plugin-relative `.py` paths or tags are
  dropped). A future advisory about core/stats code can then decide new statistical-results from the trace. Evidence:
  VALIDATION SCIFIX-TRACE-FORWARD.
- **Every oracle of the sci-fix ledger runs weekly, with all its backends and no skip allowed.** A new
  `ledger-evidence` job in `statistics-validation` (weekly, on demand, on a release tag) runs
  `run_required_backends.py --from-ledger --no-skips` with pyhf, ArviZ and pdg; locally all 56 nodes pass. TH9-MASSES's
  PDG cross-check, which no venv had run, passes on both its parent and its fix (it checks the bundled constants, which
  the fix did not change), so it cannot show the defect: the entry stays D1 with that reason. Evidence: VALIDATION
  SCIFIX-EVIDENCE-CI.
- **Sci-fix evidence: oracles whose expected values do not come from a transcribed formula (no behavior change).**
  DR-WP1-01 gains a Geant4 11.4.3 G4Cerenkov oracle (proton and alpha photon counts frozen with the version stated),
  DR-WP1-02 the Gaussian limit of the Gaisser-Hillas profile at large X_max (arXiv:1811.04660v2 eq. (3.1), p. 5), and
  DR-WP2-06-CALO a toy truth-recovery study over three term sets (PDG RPP 2024 Statistics sec. 40.2); each fails on
  its entry's parent by assertion and passes on the fix. The transcription gap is closed for the three; DR-WP1-01
  moves from D0 to D1. DR-WP2-06-MS keeps the gap: no qualifying source was found, and the grade is left to the
  maintainer. New source scifix:S13 and claims scifix:C31, C32 (VALIDATION SCIFIX-TRANSCRIPTION-ORACLES).

## 0.24.0 (2026-10-22)

- **Independent review: an optional expert slot in round 1, a per-review configuration file, and reviewer identity
  removed from the filter packet (contracts 3.6.0).** All three are off unless asked for; without them every
  allocation, event, packet and report is unchanged bit for bit (the P1 end-to-end review is byte-identical).
  `start --expert-model M` (config `expert`) adds one round-1 slot: an agent of M reads the whole document as a domain
  expert and reports only substantive physics, statistics or method errors (a general statement false in some regime,
  inconsistent reasoning, treatments called equivalent that are not, statements the plugin's own tools contradict),
  never style. In two evaluation runs the substantive errors no reviewer found were such whole-page reasoning errors.
  It is dispatched with the other round-1 slots, has no canaries (the R0 self-check, the read rules and the copy guard
  are its controls), at most two attempts, never escalates, and writes `review_record.json` with the new role
  `expert`: claims, verdicts and findings in the reviewers' shape and evidence bases, no skim, deep list or
  carry-forward; receipt applies the reviewer rules minus coverage, controls and re-review, accepts any evidence basis,
  and adds `finding_without_verdict`. Its findings go to the filter, arbitration, dispose and the report like any
  other; a changed one is rechecked by the design lens in round 2. Being evaluated, not yet recommended. `start
  --own-config` writes the review's configuration to `reviews/<id>/review-config.json` (recorded in `round_started`
  as `config_file`; observe and `check` watch it) instead of the shared file, so concurrent reviews can use different
  settings and no unfinished review blocks another's options. The filter packet's `correction`, `description` and
  `fix` now have the raising slot's id, its reported identity and the model names replaced by `[redacted]`, with the
  counts in the private `filter_ids.json` and the report. Contracts 3.6.0: the config field, the record role and the
  optional `round_started` key (fixtures, templates and example artifacts carry the new version string only).
  Evidence: VALIDATION REVIEW-EXPERT-SLOT.
- **Advisories: OSV timestamps, waivers, regression links; schemas for the ledger and the advisories (sci-fix
  improvement plan C1, C2, C6; F-13, F-17, F-18, F-22).** Advisories carry OSV `published` (first commit, UTC) and
  `modified`. `scifix_advisories.py check` warns, never fails, when an advisory was introduced by another advisory's
  fix commit, until the ledger records the link: CANONICAL-KEY-ZERO-FRACTION is a regression of ML-SPLITS,
  SAMPLE-NAME-DOT-SEGMENTS of ML-CALIBRATION (`regression_of`). Every S1 and S2 entry is named by an advisory or states
  an `advisory_waiver` (seven do: CLS-LOGINTERP, the three triage status fixes, the three scan fixes).
  `docs/evidence/advisories/README.md` records that SFA-2026-012, -013 and -026 to -029 were never published.
  `docs/evidence/schemas/` holds JSON schemas of the ledger and of format /2 advisories, checked in the tests. The
  normalisation rule of C1 (a property or exhaustive test, and the callers listed in the PR) is in
  `docs/maintenance.md`. Evidence: VALIDATION SCIFIX-PLAN-C1-C2-C6.

- **Sci-fix ledger report: transcription rule, structured S3 sources, per-entry sign-off (sci-fix improvement plan
  B2, B5, B7; F-08, F-15, F-16).** `tools/scifix_ledger.py report` lists, read-only: entries below their severity's
  minimum (27), C3 entries whose oracles all compute their expected value from a formula transcribed into the
  repository (DR-WP1-01, DR-WP1-02, DR-WP2-06-CALO, DR-WP2-06-MS; each now says so in `gaps`, grades unchanged until
  the maintainer decides), S1 entries without a sign-off (18: none is signed yet), and S3 entries below their minimum
  (5). Every independence record states `expected_from`; documentation fixes list `sources` (the three whose ledger
  text never itemized them, and the two internal-only warning fixes, state the gap). Evidence: VALIDATION
  SCIFIX-PLAN-B2-B5-B7.
- **Validator: the same efficiency under two namespaces now warns.** A measurement spec listing a bare `efficiency`
  next to `<ns>:efficiency` (or `<ns>:efficiency` next to `<other-ns>:efficiency`) counted the efficiency twice and
  passed with no finding. It now gets the warning `measurement.efficiency_counted_twice_namespaced`; the existing
  `measurement.correction_category_repeated` errors are unchanged, so no artifact changes outcome (no contracts
  change). `correction-chain.md` says what the validator catches and what it cannot (a profile term with another
  name).
- **periodicity_scan.py: the red-noise p-value refits the null on every surrogate (sci-fix PERIODICITY-REFIT, S1,
  advisory SFA-2026-038).** Since 0.14.0 the AR(1) and OU surrogates used phi (or tau) estimated once from the data;
  the lag-1 estimate is biased low on short series, and the global p was anti-conservative (no-signal AR(1) toys,
  n = 50, phi = 0.9: 0.147 rejected at alpha = 0.05 and 0.253 at 0.1; n = 100, phi = 0.9: 0.077 and 0.163). The
  default is now a double parametric bootstrap (`--null-fit refit`, `--inner-surrogates`, default 199) with the
  first-order bias-corrected lag-1 estimate for AR(1); on the same toys every rejection fraction lies within two
  binomial sigma of alpha or below it. `--null-fit once` reproduces the old numbers for the same seed and is labeled
  anti-conservative. The white null is unchanged. Output gains `global.p_single_level`, `global.null_fit` and, with
  the refit, `global.inner_surrogates`; a refit costs N x (M + 1) surrogate series (new cap 4e6). The docstring's
  "conservative" wording and `time-series-inference.md` now state the measured calibration.
- **Fifteen references corrected after review batch 1 and the expert-slot tests (54 issues; VALIDATION
  REVIEW-REFS-4).** Substantive: the track-fit chi^2 uses the measurement covariance (the fitted-residual covariance is
  singular) and the biased residual is positively correlated with the measurement (`core-detector-equations.md`,
  `performance-metrics-and-residual-diagnostics.md`); QGSP_BIC and FTFP_BERT coincide for pions below 12 GeV and
  nucleons from 1.5 to 12 GeV, and the Geant4 convergence gate and scope check are described as what they enforce
  (`geant4-study-protocol.md`, rules G4R-BIC-RANGE and G4R-HP-NEUTRON); era mixing is exact only when every
  era-varying factor is inside the response or the weights (`response-and-forward-folding.md`). Also one-sided p-values,
  the Chernoff condition and the Braun et al. background (`astroparticle-statistics.md`), and 13 earlier expert-slot
  findings in ten references (code1/code4 differences, charge-sign comparisons, harmonic trials, unipolar anode
  signals, induced-charge sign, angle-dependent most probable value, electron-only E/p symmetry, tag-and-probe shapes,
  Bayesian vs profile intervals, Z_A for discovery, non-nested trigger bootstrap). The independent-review reference now
  recommends `--expert-model` with the strongest model alongside the lens slots, and an Opus filter over Sonnet.
  Guidance only.
- **Five more references corrected after the first live review with the 0.23.0 options (42 issues; VALIDATION
  REVIEW-REFS-3).** Ignoring a positive correlation overstates the uncertainty of a difference or ratio, not only
  understates it (`statistical-inference-for-physics.md`); geomagnetic cutoff deliverables use the backtraced maximum
  over the acceptance cone, and the Garwood level is 68.27% (`space-based-direct-detection.md`); measured-value
  notation in the inverse-offset model (`calibration-and-alignment.md`); trigger-weight and luminosity citations
  (`triggers-luminosity-pileup.md`); era checks, `residual.py` scope and Z_A regime (`analysis-design.md`). The
  independent-review reference now recommends `--filter-model` with the live-run numbers. Guidance only.
- **An installed copy of a release keeps its release identity (sci-fix improvement plan A2, F-03).** The plugin
  system writes `.in_use/<pid>` into the root of an installed copy; the code identity counted it as an added file, so
  `plugin_release()` returned `unreleased` on every installed copy (reproduced on 0.21.0, 0.22.0 and 0.23.0), the
  advisory scan treated its artifacts as from an unreleased build, and the protected guard refused every
  qualification with `protected.qualification_other_plugin`. The identity now leaves out `.in_use/` at the plugin
  root only; any other added, missing or changed file still makes the copy another plugin (a nested `core/.in_use/`,
  a module beside runnable assets, a globbed data file). `identity.verify()` also warns
  (`identity.bytecode_unverified`) when `.pyc` files are present, since bytecode is outside the identity; the guard's
  docstring states that limit. Evidence: VALIDATION SCIFIX-PLAN-A2.
- **Advisory check: discriminating keys, stricter ranges, and advisories for code that writes no artifact
  (sci-fix improvement plan A0 and A3; F-01, F-02, F-04, F-05, F-07, F-27).** `scifix_advisories.py check` now
  rejects an advisory whose extension keys cannot show the affected code ran (a key that a listed type's extension
  schema requires, so every artifact carries it, or no key at all): SFA-2026-036 and -037 keyed on `tools`, which
  every `computational-run` has, so a merge job that only ran `hadd` was reported affected. The eleven older
  advisories with such keys are frozen in `NONDISCRIMINATING_ALLOWED` until their migration; none is added. The eight
  advisories whose affected scripts print JSON and write no artifact (SFA-2026-014 to -019, -036, -037) now say so
  (`database_specific.no_artifact`, `outputs`). Ranges: an inverted range (`fixed` at or below its `introduced`), two
  events at one version and a malformed version are problems (a malformed version raised before); a `fixed` release
  must change an affected file against the release before it, and an `introduced` release that already held one
  states `introduced_basis` (added to SFA-2026-002 and -003); an unknown artifact type is a problem. Scan verdicts
  are unchanged in this step.
- **Release manifests of 0.3.0 and 0.4.0, backfilled (sci-fix improvement plan C4, F-20).** `release_manifest.py
  backfill --commit SHA` records a release made before manifests existed, by today's identity rules, marked
  `backfilled` with its full commit and the generator; `check-published` checks it against its tag, or its commit when
  the release was never tagged (0.4.0, `9870a35a`), and treats it as published. The advisories whose range ends
  before 0.5.0 (SFA-2026-008 to -011, -030, -031) now resolve against the 0.3.0 manifest, and `check` confirms that
  0.4.0 changed their files.
- **hep-computing: run the advisory scan when work resumes on an older project (plan C3, F-21).** A rule in the
  skill's reference index (`engineering-playbook.md`): when a project's artifacts predate the newest fixed release of
  an advisory, or an advisory is still open, run `tools/scifix_advisories.py scan` and report its three classes
  (affected, possibly affected, output that is no artifact) with each remedy; read-only, no recomputation.
- **Advisories format /2: match what an artifact can show, and say "possibly affected (no trace)" when it cannot
  (sci-fix ADVISORY-MATCH-V2, S2; plan A1 change 1).** `applies_to.match` replaces `extension_keys`: groups of
  conditions on any envelope path (`exists`, `eq`, `in`, `regex`; `[*]` expands lists), undecided when the artifact
  predates the field (`unknown_before`) or the execution trace, and `match: []` with `match_basis` when no field can
  show the affected code ran. Every group must discriminate; the frozen allowlist is gone. All 31 advisories are
  rewritten: ten list outputs only (the blinding scanner, the five detector scripts, `anisotropy.py`,
  `estimate_training_memory.py`), which no artifact can show; six cannot be decided from any field (SFA-2026-004, 006,
  010: the statistical-result writer wraps a core/stats CLI's output; 023, 025: required ml-artifact keys; 033: required
  claims), so their artifacts in range are now possibly affected (no trace) instead of affected; the others match on
  fields the affected code writes (SFA-2026-020 only from contracts 2.5.0, when its fields appeared; 031 on the
  partition runner's tool name). The number of findings on old artifacts does not drop: what changes is that a
  finding says what it rests on. The scan still reads `/1` for one release. Evidence: VALIDATION SCIFIX-ADVISORY-V2.
- **Envelope execution trace: `provenance.code_paths` and `code_tags` (contracts 3.5.0, minor; sci-fix improvement
  plan A1 change 2, maintainer decision 2026-10-22).** Twelve artifact writers add the plugin `.py` files their process
  had loaded and the tags advisory-named shared functions set (`core/trace.py`, imported as `contracts.trace`; tags cleared per envelope), so a
  later advisory can tell whether the affected code was loaded for an artifact. Loaded is not executed, and code run
  in another process (a core/stats CLI wrapped by `result_artifact.py`, a training asset) is not in the trace. No
  capability: a 3.4 reader ignores both fields; older artifacts carry none. Fixtures, assets, profile artifacts and
  examples carry the new version string, and the examples' writers their `code_paths`. Evidence: VALIDATION
  SCIFIX-PLAN-A1-TRACE.
- **Advisory scan: a missing marker does not show that the affected code ran (sci-fix SCAN-MISSING-MARKER, S2; plan
  A4).** An extension key holding `unknown`, `not-applicable` or `not-provided` counted as present, so a
  measurement-spec whose `blinding` is `not-provided` matched an advisory keyed on `blinding`. Markers are now absent;
  a zero is present. Evidence: VALIDATION SCIFIX-PLAN-A1-TRACE.
- **Advisory scan: code without artifacts is listed apart, and a release must hold an affected file (sci-fix
  SCAN-VERDICT-ORDER, S2; plan A5).** `scan` matched every advisory against every artifact of a listed type with a
  listed key, so a 0.21.0 merge job that only ran `hadd` was reported affected by SFA-2026-036 (S1) and -037, and a
  release in range whose manifest lacks the affected file was reported affected too. The scan now decides in order:
  an advisory whose code writes no artifact is listed in `outputs_not_artifacts` (with its outputs and remedy) and
  matches nothing; then the type, the keys, the range, and whether that release's manifest holds an affected file.
  `release_basis` `verified` is renamed `digest-consistent` (an artifact's own digest matched; nothing was verified);
  `release_basis_legacy` keeps the old value for one release. Old artifacts matched through the eleven frozen
  advisories are still reported as before. Evidence: VALIDATION SCIFIX-SCAN-VERDICT-ORDER.
- **Sci-fix ledger: structured `changelog` and D-scope gaps (plan C5 and F-23).** Each entry's `changelog` is
  `{"kind": "release" | "audit" | "unreleased", "release", "name", "detail"}`, checked against the CHANGELOG
  sections and the advisories' fixed releases; four stale `Unreleased` values are corrected (three shipped in 0.18.0,
  ANISO-WEIGHTED-COV in 0.22.0) and the triage entries point to 0.23.0, and the audit names gain their release
  (0.10.0). Seven entries graded D2 whose later oracle tests were never run on the parent (FC-MONOTONE, POISSON-SF,
  COV-NOREPAIR, POISSON-500, ROBUST-MALFORMED, BLINDING-SCANNER, ROBUST-CAMPAIGN) state it in `gaps`; their grades
  are unchanged until the D-scope rule. Evidence: VALIDATION SCIFIX-PLAN-P0-CHECK.
- **Sci-fix ledger: located sources in the evidence ledger format, and evidence that runs (plan B1 and B4; F-10,
  F-12).** The *Sources read for locators* table is now `docs/evidence/scifix-sources.json` and
  `scifix-claims.json` (11 sources, 27 located claims, checked by `core/evidence/ledger.py`, index
  `scifix-index.md`), and each of the 15 `locator` records names its `source_id` and `locator_id`; the source must
  have been read at `page` or `full-text`. arXiv:2109.07851 (ML-NEGWEIGHTS), cited only in prose, was read
  (v2, 2026-10-22, page level): eq. (2.2) is in Sec. 2, p. 3, not in Sec. 2.2 as the ledger and
  `hep_metrics.cell_resample` said; the citation is corrected and the grade (C3) stands. Each of the 60
  `independence` records states `requires: {"core", "backend"}`, found by hiding each package in turn; every backend
  is locked by a required CI gate. `run_required_backends.py --from-ledger` runs the 52 oracle nodes (24 modules,
  16 not in its `MODULES`) one by one and classifies each failure: a missing core dependency is an environment error,
  a missing backend is unverified, anything else means the evidence does not hold; with `--no-skips` an unverified
  or skipped node fails too. Evidence: VALIDATION SCIFIX-PLAN-B1-B4.
- **Sci-fix ledger: the D axis is data, and D2 covers every oracle (plan B3 and B6; F-11, F-14, F-23; maintainer
  decision 2026-10-22).** Each entry records its commits (parent, fix, follow-ups; full hashes), its per-test parent
  records (outcome on the parent and the fix, failure kind, environment, adaptation, VALIDATION section, what the test
  needs) and its mutants; `evidence_tests` lists the test nodes used. D2 now needs a parent failure of every oracle
  node named by the entry's independence records (at most D1 when only other regression tests have one), D3 also a
  killed revert mutant, and the ledger test recomputes both. The oracle nodes without a record were run on their
  parent and fix commits in detached worktrees: many test functions, arguments or outputs that are new in the fix,
  so they cannot reach the parent's code, and some pass on the parent. 22 grades fall (13 S1 and 9 S2 entries now
  D1 or D0, each with a `gaps` line); none rises. ML-SMALL is split into ML-SMALL-C10, -C24, -C25 and -C26 (K13
  corrected a test and left the ledger; the old id stays in `superseded`), and SFA-2026-025 names the four. No code
  changes; no released number changes. Evidence: VALIDATION SCIFIX-PLAN-B3-B6.

## 0.23.0 (2026-10-22)

Contracts 3.4.0 (minor): independent review gains a per-lens model and an optional filtering pass; 27 more
reference corrections; 24 triaged plugin issues fixed (exit codes, checkers, validator warnings); a required
`bdt-backend` CI gate (advisory SFA-2026-037).

- **Independent review: per-lens model choice and an optional filtering pass after round 1 (contracts 3.4.0).** Two
  optional `review-config.json` fields, both set at `review.py start` and both off unless set; without them every
  allocation, event, packet and report is unchanged bit for bit. `lens_models` (`--lens-model LENS=MODEL`, repeatable;
  the model must be in `models`) fixes the model of that lens's lens slot in every round; its shadow keeps the
  rotation and moves off the fixed model. The P3 tuning run found Haiku design-lens slots missing their canaries in 8
  of 9 attempts, so the reference recommends the strongest model on the design lens. `filter` (`--filter-model M`)
  adds one filtering pass once round 1's records are received (decide row 8a, before escalation, arbitration and
  dispose): one agent judges every accepted round-1 finding, controls excepted, from a packet with random ids and no
  reviewer identity, as `keep` or `drop` with a reason (`filter_record.json`, new sidecar format
  `review_filter_record` 1.0.0, receipt codes `decisions_incomplete` and `duplicate_target`); at most two attempts,
  after which the filter is not applied. Its decisions are advice: `next` shows them with `dispose`, every finding is
  still disposed, and the report lists the kept findings first and the dropped ones apart with their reasons. In the
  tuning run one Opus pass raised precision from 0.53 to 0.88 at about 2% of the review's tokens. Contracts 3.4.0:
  the new schema, the `filter_needed` event and the two config fields (fixtures, templates and example artifacts carry
  the new version string only). Evidence: VALIDATION REVIEW-FILTER-PASS.
- **Five more references corrected after the review tuning run (27 issues; VALIDATION REVIEW-REFS-2).** The
  efficiency factor product needs no independence when the factors are chained, and the acceptance already holds the
  simulated selection efficiency (`correction-chain.md`); the fake-hit recipe multiplies by `nu`, not `nu_0`
  (`front-end-electronics-and-signal-processing.md`); `periodicity_scan.py` exists and its red-noise null omits the
  measurement covariance, and a model-built covariance is not equivalent to a normalization nuisance
  (`time-series-inference.md`); the TOF ceilings name their separation convention and the TR onsets scale with mass
  (`particle-identification.md`); Combine impacts and `autoMCStats` pointers (`nuisance-modeling.md`). Guidance only.
- **anisotropy.py: `--cl` below 0.5 is rejected with its reason, not a TypeError (robust-fix ANISO-CL-RANGE).** An
  upper limit below CL 0.5 is not supported: the expected limit (the Neyman limit at the median isotropic amplitude)
  is empty there and the power constraint undefined. `harmonic --cl` outside [0.5, 1) is rejected (exit 2) with that
  reason, and `amplitude_upper_limit` raises ValueError for it; at CL 0.5 an expected limit found empty by rounding is
  reported as its analytic value 0 (it was a TypeError with a non-uniform exposure map). Results for CL >= 0.5 that
  ran before are unchanged bit for bit. Evidence: VALIDATION ANISO-CL-RANGE.
- **CI: a required `bdt-backend` job runs the xgboost and scikit-learn tests with the `bdt` extra pinned.** The
  `train_bdt.py`, `export_bdt.py` and analysis-to-paper BDT tests skipped in every required job; the new job installs
  xgboost 3.4.1 and scikit-learn 1.9.1 and fails on a test skipped for either (`tools/run_required_backends.py`);
  `tests/tools/test_pyproject.py` checks that every such module is listed. Evidence: VALIDATION BDT-BACKEND-GATE.
- **A missing input file is bad input, exit 2 (sci-fix CLI-MISSING-INPUT-EXIT2, T17).** `calorimeter_resolution.py`,
  `multiple_scattering.py`, `pileup_reweight.py` (hep-detector), `hepdata_export.py`, `hepdata_record.py` and
  `geant4_build.py` reported a missing or unreadable input file as status `failed`, exit 1 (a negative verdict). They now
  exit 2: the detector scripts with the shape of their argument error (`error_kind` `invalid-input`, as their tool
  contracts declare for exit 2), the adapters with status `rejected`. Invalid file content keeps its documented exit 1.
  The plugin-wide CLI contract test now requires exit 2 for a missing input (or 3 only with `missing-dependency`) for
  every tool it runs; it accepted 1.
- **Adapters report a missing optional package as `missing-dependency`, exit 3 (sci-fix ADAPTER-MISSING-DEPENDENCY,
  T19).** The pyhf-combine scripts exited 2 with `refused` or `failed`; `coffea_dijet_processor.py` and
  `root_to_parquet.py` exited 2 with text only; `uproot_awkward_analysis.py` and the two PyROOT templates exited 1 with
  text only; `hepdata_export.py --engine hepdata_lib` exited 1 with `failed` after reading its input (now checked first);
  `hepdata_record.py` on a YAML table without PyYAML, and `unbinned_fit.py` and `reproduce_published_likelihood.py`
  without NumPy or SciPy, ended in a traceback. All print `{"status": "missing-dependency", ...}` and exit 3; a test
  hides each third-party module of each adapter in turn (28 pairs, 14 tools).
- **`backend_comparison.py` and `model_card.py` report input they cannot read or map as `rejected` (sci-fix
  PYHF-REJECTED-STATUS, T18).** They printed `refused` (a negative verdict in `core/status.py`) with exit 2; exit 2 is
  unchanged.
- **`estimate_training_memory.py` states its verdict (sci-fix TRAINING-MEMORY-VERDICT, T33) and its activation inputs
  (T34).** A configuration that does not fit exits 1 (was 0) and `--json` carries `status` `ok` or `failed`; bad input
  with `--json` prints `rejected` (exit 2 as before). The report and the JSON give the micro-batch size and sequence
  length the activation estimate used (`micro_batch`, `seq_len`, and `recompute`).
- **`core/status.exit_code` on an unknown status (robust-fix STATUS-UNKNOWN-EXIT, T16)** names the status on stderr and
  returns 3 (incomplete) instead of raising KeyError, which exited 1 (a verdict) with a traceback. `artifact_labels`
  refuses an unknown status with ValueError. No shipped script was found printing an unknown status (latent).
- **`run_all_checks.py` writes its summary when git is missing or hangs (robust-fix RUN-ALL-CHECKS-GIT, T21)**, with
  `git_commit` `unknown`, instead of ending in a traceback after every check had run.
- **Documentation (T18):** `core/status.py` states that `refused` is a negative verdict (exit 1), names the documented
  exception (the protected-use guard and the permit check refuse a run before it starts with exit 3) and the older tools
  that print `refused` with exit 2, and says new code uses `rejected` for unusable input.
- **Checkers enforce the rules they state (plugin triage batch B).** Development and packaging checks only; no
  scientific number changes.
  - `tools/measure_entrypoints.py` and `tools/validate_skill_bundle.py` measure a folded or literal block SKILL.md
    description (`description: >-`) in full, so a long block description no longer passes the 1,024-character limit
    (T01); the 500-line limit counts lines, not newline characters, so a file without a final newline is counted
    right (T02).
  - `tools/check_layering.py` reads relative imports (resolved against the file's package), constant-string
    `importlib.import_module()` and `__import__()` calls, and code under `fixtures/` outside `tests/`, so "core/ never
    imports contracts/" holds for every import form (T03); a core module's steward in `core/OWNERS.json` must be a
    skill name, not empty or a placeholder (T04).
  - `tools/check_ownership.py` reads a plural (`BDTs`) as a claim of its term (T07).
  - `tools/check_packaging.py` scans every text file, detected by content (no NUL byte in the first 8 KiB), not only
    known suffixes (T27); finds batch-scheduler site keys at any depth below a slurm or htcondor backend or section,
    in any case (T29); and exempts placeholder e-mail addresses only at reserved domains (example.com/.org/.net,
    `*.example`, `*.invalid`, `*.test`, `*.localhost`; RFC 2606, RFC 6761), so `author@<real domain>` is reported
    (T30). The LaTeX venue template in hep-authoring now uses `author@example.org`.
  - `docs/profile-authoring.md` states the registry budget as 3,072 bytes (`REGISTRY_BUDGET`), not 2 KiB (T35).
- **Artifact validation gaps from the plugin triage closed without a contracts major (T09, T11, T12, T14, T15,
  T36).** Contracts-visible: new finding codes, all warnings except T09; no field added, `CONTRACTS_VERSION`
  unchanged. Specs and artifacts that validated before keep their outcome (360 shipped artifacts, fixtures and
  examples revalidated: no outcome change).
  - `contracts/validate.py` on a directory validates `*.JSON` (any suffix case) like `*.json`: an invalid artifact
    named `bad.JSON` now fails the directory check (artifact errors, or `artifacts_dir.not_artifact`); before it was
    only an `artifacts_dir.non_json` warning (T09; an error, as the docstring already stated for every JSON file).
  - measurement-spec: a `conditional_denominator` that is null, a number, a bool or a placeholder token (`n/a`,
    `none`, `tbd`, `-`, `?`, ...) is the warning `measurement.denominator_placeholder` (T11); an empty backgrounds
    list with a placeholder `no_backgrounds_reason` is `measurement.no_backgrounds_reason_placeholder` (T12); a
    blinded spec whose mask names no region and no interval variable is `measurement.blinding_mask_empty` (T14).
    A blank string, a missing mask and a missing reason stay errors.
  - An unknown (not retired) skill name under an extension `handoff` key is the warning `skill.unknown_handoff` in
    every artifact type; where the 2.8.0 ml rules report it as `ml.handoff_unknown` it is reported once (T15).
  - An observable at level `unfolded` whose `phase_space.definition` names no target level (a level term other than
    `unfolded` and `detector`) is the warning `observable.unfolded_target_undeclared` (T36). A structured
    `observable.target_level` field is left for a contracts minor.
- **Partition manifests with shared chunk seeds are refused (T23).** `core.partition.engine.validate_manifest` raises
  `PartitionError("partition.duplicate_seed")` (a `ValueError`) when two chunks share a seed; `local_partition.py`
  and `campaign.init` (`campaign.bad_manifest`) refuse such a manifest before writing anything. Manifests from
  `make_manifest` are unaffected.
- **A failed revocation status has no readable events (T26).** `RevocationStatus.events` is a property that raises
  `RevocationUnverified` when the log did not verify (it was a public `[]`, readable as "nothing revoked"); the
  constructor field is now `_events`.

## 0.22.0 (2026-10-22)

Contracts 3.3.0 (minor): independent review of drafts, P1 (`docs/dev/independent-review-spec.md`); five references
corrected after its real-document evaluation; an S1 sci-fix of the weighted anisotropy statistics (advisory SFA-2026-036).

- **A draft can be reviewed by agents that did not write it, with a record a script checks.**
  `skills/hep-authoring/scripts/review.py` drives one review of a Markdown document: `start`, then `next` until
  `stop`. Four lenses (facts, design, sources, bypass) and one shadow per lens review packets built per attempt; the
  author agent passes a fixed two-line message to each agent through the host's own mechanism (the plugin dispatches
  and requires no subagent). Receipt checks each `review_record.json` (24 reason codes: dispatch and packet hashes,
  isolation self-report, forbidden reads, recomputed file hashes, claim and finding shape, deep and skim coverage,
  evidence bases, refutation attempts, unresolved share, canaries, carry-forward; arbiter identity and conclusions).
  Findings are disposed with declared verification (`--verified` or `--adopted-unverified`); a declined high finding
  and conflicting verdicts go to arbitration; changes are confirmed by a fresh review in the next round; a reverted
  edit is caught before close; unresolved items go to a human (`escalate`, `report`, `resolve`) and the review then
  continues. `report.md` lists the configuration, per-slot quality metrics, canary hits and witnesses, dispositions
  and the limitations that applied.
- **Contract and check.** `contracts/review.py` holds the seven new schemas' Python rules, the state table shared by
  the driver and `check`, and `check` (`log_broken`, `not_closed`, `changed_after_close`, `artifacts_changed`,
  `finding_open`, `uphold_not_honored` and the warnings). The event log is hash-chained with a head and appended under
  a file lock.
- **P1 limits.** Facts and design canaries only: sources and bypass slots run without controls and are reported as
  `no_control`; Markdown only; Claude Code host notes only (shared directories and the session start, read from the
  process `CLAUDE_PID` names, observed on the macOS CLI and undocumented; without `CLAUDE_PID` a warning). Thresholds
  are provisional until the P3 evaluation.
- **Maintainer decisions (2026-10-21, `docs/dev/decision-independent-review.md`).** The plugin dispatches and requires
  no subagent: clarifying sentences in `docs/architecture.md`, `docs/routing-contract.md` and under the invariant at
  `docs/protected-data-architecture.md:526` (its wording unchanged). Review verdicts use the evidence bases of
  `docs/maintenance.md` plus the non-independent `tool-output` and `internal`. A closed agent review is not a
  non-author review record for the v6.3 conditions O04/O14 (the author agent could forge one); it is advisory input a
  human reviewer may cite.
- **Fixes from the P3 stage-1 pilot.** Receipt rejects a record that cites a copy or version of the delivered
  document anywhere on the host (`read_outside_packet`), and `start` warns about copies in the plugin and the project;
  design canaries fire on documents without numbered references (a repeated value made inconsistent, a repeated name
  misspelt); a lens with nothing in scope gets no slot and a shadow only when it can have focus units; one `--seed`
  reused for several reviews no longer repeats their nonces; records may cite plugin-relative paths.
- `tools/check_packaging.py`: the local-hostname rule no longer matches a name followed by `.md` or `.json`, so the
  Claude Code memory and settings file names the review host notes need are not read as hostnames (planted hostnames
  still fail; maintainer decision). The host notes write temporary and Claude configuration folders as placeholders.
- Ownership row "Independent review packets, review records and the review log" (hep-authoring; `independent
  review`, `review packet`); four routing cases (en, zh-Hant).
- Contracts 3.3.0 adds sidecar formats only: no artifact, vocabulary or capability change; fixtures, examples and
  profile artifacts regenerated for the version string.
- **`anisotropy.py harmonic` uses the exact null covariance of the weighted harmonic (sci-fix ANISO-WEIGHTED-COV, S1;
  advisory SFA-2026-036; VALIDATION ANISO-WEIGHTED-COV).** With `--exposure-map` the Rayleigh probability and the Rice
  width took `2/N_eff` per component, but a non-uniform exposure makes the variances of `a` and `b` unequal and
  correlated (`1 + 0.9 cos alpha`: `N Var(a) = 6.39`, `N Var(b) = 2.79`, against 4.59 for both): a dipole along the
  less exposed axis looked more significant than it is and its upper limit was too tight. The covariance now comes
  from the binned map (`harmonic_covariance`, reported as `covariance_ab`), the probability is `exp(-chi^2 / 2)` with
  `chi^2 = v^T V^-1 v` (`chi2_ab`), `sigma_per_component` is `sqrt(trace V / 2)`, and the upper limit, when V is not
  isotropic, excludes an amplitude only if it is excluded for every dipole phase on a 72-point grid aligned with V's
  axes. Without a map, with a uniform map and for the solar, sidereal and anti-sidereal checks the numbers are unchanged
  bit for bit; a map with an empty right-ascension bin is now rejected.
- **`tail_extrapolation.py` warns when only one model passes validation (VALIDATION REVIEW-CODE-WARN).** The envelope
  then has zero width by construction (`low = high`, `gaussian_sigma = 0` under a prescription); the warning names
  the model and says the model uncertainty was not assessed. Numbers unchanged.
- **`assets/inference.py --external-scores` explains scored events missing from the split manifest.** They are still
  scored (real data and other samples are legitimate), but the warning says the check cannot exclude that the model
  was trained on them and that, for simulated events of the training sample, the manifest is incomplete; a refusal
  for scored training events carries the warning too.
- **Negative weights: dropping them from training only is allowed under option 3's condition.**
  `ml-analysis-weights.md` option 4 no longer forbids it outright: the classifier learns the positive-weight density
  instead of the signed one, like |w| training, so the effect must be shown against signed-weight or resampled
  training, and negative weights are never dropped from evaluation. `train_bdt.py` now prints a `warnings` entry
  under `--negative-weights drop` or `abs-train-signed-eval` when negative weights are present. Scores, metrics and
  policy names unchanged.
- **Five references corrected after an adjudicated review (45 issues; VALIDATION REVIEW-REFS).** The first-harmonic
  variance `2/N` and its bias hold for uniform exposure only, and `N_eff` is an approximation with weights
  (`cosmic-ray-measurements.md`); flattening inside a class is a documented training-only choice, as
  `ml-analysis-weights.md` allows, and hyperparameter selection in `train_bdt.py` is not nested
  (`multivariate-analysis-bdt-nn.md`); the Bethe shell term scales as `z^2`, and the fluctuation regimes and Highland
  accuracy follow PDG 2025 (`signal-formation-and-readout.md`); Cowan et al. eq. 98, the Baker-Cousins, Jeffreys and
  Z_Bi statements, and the `cls-limit`/`profile-cls` handover (`inference-recipes.md`); DRAGON2 diagnostics and the
  Moderski attribution (`cosmic-ray-propagation.md`). Guidance only; no tool output changes.

## 0.21.0 (2026-10-21)

Contracts 3.2.0 (minor): simulated dataset-records; a reference benchmark for shower development; CI speedup.

- **Tables derived from simulation runs have their own dataset status.** `dataset-record` `extension.status` accepts
  `simulated`: the envelope inputs are the Geant4 run records or study record the table came from (checked by
  `contracts/dependencies.py`: hash, labels, and `dataset.simulated_source` when an input is neither a run record with
  `extension.simulation` nor a study record). The record is never `observed`, is at level `detector` or
  `particle-fiducial`, and keeps `unvalidated` unless an input study record carries `validated-in-scope`
  (`dataset.simulated_*`). A `communication` using a simulated table gets the warning `communication.simulated_source`
  (label figures and tables "Simulation"). Additive: existing records keep their outcome; a 3.1 reader refuses the new
  status as an unknown term. Closes the J2/J14 known limitation for simulation tables; scope containment of a table
  inside its study's benchmarked scope is not checked.
- **`multiple_scattering.py` says when the Gluckstern term is an approximation.** PDG states
  `sigma_x sqrt(720/(N+4)) / (0.3 B L^2)` for N >= 10 equally spaced points; with fewer measuring layers it overstates
  the intrinsic term (3.5% at N = 3, 5.4% at N = 4, 2.4% at N = 8; the crossover and the intrinsic MDR move by the
  same factor). The output now carries `intrinsic_coefficient` (Gluckstern, the exact least-squares coefficient for N
  equally spaced points `sqrt(720 (N-1)^3 / ((N-2) N (N+1) (N+2)))`, their variance ratio, and which one is used) and
  a warning below N = 10 that points to `tracker_resolution.py momentum` for the actual layer positions. The numbers
  it reports are unchanged (Gluckstern stays the term used); `toy_spectrometer.py` keeps Gluckstern as the definition
  of its synthetic slope.
- **A reference benchmark for electromagnetic shower development (`longitudinal-profile`).** `geant4_benchmarks.py`
  fits dQ/dt = Q_E beta (beta t)^(alpha-1) e^(-beta t) / Gamma(alpha) + Q0 to the per-layer mean deposits of a
  layered_sim sampling stack (weighted least squares, standard library) and compares the shower maximum
  t_max = (alpha - 1)/beta with the same fit to published test-beam data; the reference uncertainty propagates the
  published alpha and beta without their correlation (conservative), `systematic_relative` covers stated
  model-versus-measurement differences, the SE is a seeded event bootstrap with refits. First reference: ALICE FoCal-E
  (JINST 19 (2024) P07006, arXiv:2311.07413, Table 3), replacing the paywalled Bathow et al. 1970 and the LumiCal
  Moliere radius (figures only) as the open-access shower reference. Lateral leakage still has no reference.
- **layered_sim materials can be mixtures.** A `materials[]` entry takes either `z` and `a_g_mole` (one element) or
  `components` (at least two NIST `G4_` materials or earlier user materials with mass fractions summing to 1), with a
  density; checked by `geant4_run.py` and the C++ reader (G4Material::AddMaterial). Needed for alloys (W-Ni-Cu), FR4
  and glues; existing specs are unchanged.
- CI (options 2 and 3 of the CI improvement proposal): `tools/module_timings.json` refreshed from two Python 3.13 CI
  runs (it covered 239 of 382 test modules; the rest got the median, and the two units shards took 444 s and 547 s;
  simulated work per shard now 1677 s each), and the units run in three shards instead of two (1118 s of work each;
  `checks-complete` reconciles `--shards 3`); a test fails when more than a tenth of the modules lack a timing. On pull
  requests the optional jobs run only the modules whose tests their extra unlocks (`run_all_checks.py --extra`,
  `tools/optional_modules.json`, generated by `tools/optional_selection.py` from the full runs: pyhf 15 modules,
  torch-cpu 9, columnar 9, root-uproot 8, ROOT 4, hepdata 1); pushes to main, the weekly and manual runs keep the full
  suites, and the new `optional-selection` job fails there when a module with an unlocked test is not listed. Tests
  that behave differently with an extra without being skipped are still covered only by those full runs.
- `tools/check_routing_static.py` reads the journey list from `docs/researcher-journeys.md` (journey coverage was
  hard-coded to J1-J12, so a missing J13 or J14 case passed); `adapters/geant4/assets/geant4.def` pins the
  `ubuntu:24.04` base image by digest (still declared only, not built).

## 0.20.0 (2026-10-21)

Contracts 3.1.0 (minor): Geant4 phase 2.

- **Study records can be re-issued as `validated-in-scope` (Geant4 phase 2).** `check_geant4_study.py label --upgrade`
  re-issues a study record only when a scope is eligible (a passed reference benchmark whose negative control was
  caught, a passed convergence gate, the declared scope inside the benchmark scope) and no gap remains; otherwise it
  stays `unvalidated` and the refusal is reported. Run records are never upgraded.
- **Contracts 3.1.0.** New optional `computational-run` field `extension.evidence_records` (run records referenced by
  path and sha256 without inheriting their labels) with the capability `core:evidence-records`, resolved by
  `dependencies.py` (hash, exit status 0, no `failed`, output hashes: `evidence.*`). New rule family
  `geant4.upgrade_*` in `validate.py` for computational-runs with Geant4 study material that carry
  `validated-in-scope`; other computational-runs (none carries that label in the plugin) are unaffected, as agreed for
  hep-computing, owner of the computational-run schema. Older contract versions keep their outcome.
- **Shared context-resolution stanza, point 5:** the one exception to keeping labels ("except a Geant4 study record
  that passes the 3.1.0 upgrade rule"); every SKILL.md regenerated. Two entry references trimmed by about 60 bytes to
  stay within the quick-load budget.
- **`build_response.py`:** `--input-record` links the artifacts the events came from as inputs (sha256, status;
  their propagating labels are carried) and `--also-status` adds labels. J14's response links its run record.
- **J14:** both studies re-issued as `validated-in-scope` for their benchmarked scope; the coarse-cut scenario's upgrade
  is refused.

## 0.19.0 (2026-10-21)

Geant4 capability (epic TASK-geant4-00 to 03, phase 1). Contracts unchanged (3.0.1); no skill description, SKILL.md or
entry reference changed.

- **`adapters/geant4` (new, optional, owned by hep-detector; demonstrated-on-synthetic-data).** `geant4_build.py`
  builds Geant4 from a pinned build spec in the user's work folder (commit checked, datasets fetched with their MD5
  checked and content-hashed, `geant4-config --check-datasets` recorded as information only) and `check`s an
  installation against its record; `geant4_examples.py` runs B1, B4a, TestEm3 and TestEm5 unchanged through a wrapper
  macro in serial mode and compares them with the reference outputs by the meaning of each printed number (B1 rms is
  the SD of the run total, TestEm3 RMS is per event, TestEm5 errors are on the mean; rounding of the printed digits
  included), with a Bonferroni threshold and reruns pooled, never substituted; `layered_sim` (this plugin's C++ program,
  built against the user's installation) runs a layered-slab geometry from a JSON spec, one `G4PVPlacement` per slab
  with overlap checks, UI commands applied after the physics list and before `/run/initialize`, per-event CSV with
  deposits, leakage by category, killed-track energy booked and not booked, and the primary's fate; `geant4_run.py`
  records every run as a `computational-run` with a `simulation` block (resolved data paths compared with the build
  record: another copy fails the run), writes scans for `run_workflow.py`, partition chunks for `local_partition.py`,
  reduced replay copies, and an `oracle` that calls hep-detector's `geant4_benchmarks.py`; `geant4_verify.py` checks
  overlaps, material budget (geantino scan), energy balance (EM-only closure) and mirrors of TestEm3 and TestEm5 run 0.
  Licence boundary: nothing of Geant4 is bundled (gate G5 wording approved for the branch; maintainers decide).
- **hep-detector Geant4 study tools.** `references/geant4-study-protocol.md` (verification versus validation, the
  study spec, a sourced settings checklist, the convergence gate, the validation ladder and verified pitfalls,
  variations, labels, adapter usage); `assets/geant4-physics-rules.json` (11 rules, each with a Geant4 11.4.3 source
  path or RPP 2024 section; a rule without a source is refused); `scripts/check_geant4_study.py` (`spec`, `summarize`,
  `run` with the hard convergence gate, `variations` with the model assignment of each variation, `label --write` for
  the study record, always `unvalidated` in phase 1); `scripts/geant4_benchmarks.py` (stopping power, range,
  thin-layer MPV as reference benchmarks with negative controls at the claimed detection limit; thin-layer width,
  multiple scattering and shower shape as sanity checks; reference inputs from the study spec, never the Geant4
  material dump). Two behavioural examples in `skills/hep-detector/examples/`.
- **Journey J14** (`examples/geant4-thin-silicon/`, `tests/examples/test_geant4_thin_silicon.py`): 10 GeV mu- and
  100 MeV protons in 300 um of silicon; offline replay byte-identical to the committed output, live mode with
  `HEP_GEANT4_LIVE_TEST=1`; 11 routing cases (`g4-*`, `j14`), capability `full-detector-simulation`, the Geant4 row of
  the hep-citations version checks extended. Not run: live routing of the new cases (needs approval and budget).

- **Geant4 follow-ups (independent check and maintainer decisions, 2026-10-21).** `layered_sim` splits leakage by
  the world face crossed (`leak_rear_MeV`, `leak_front_MeV` for the albedo, `leak_lateral_MeV`);
  `check_geant4_study.py summarize --observables` adds leakage fractions and `--slab all`; new sanity benchmark
  `shower-containment` (PDG gamma-function profile, a fit to EGS4 showers, never validation); rules `G4R-SHOWER` and
  `G4R-CITATION` (13 rules); Sternheimer inputs required only by the benchmarks that use them; `label` lists a written
  result without a literature record as a gap. Maintainer decisions: gate G5 licence boundary approved for distribution;
  phase 2 (`validated-in-scope` for Geant4-derived artifacts) deferred, its requirements recorded in the study protocol.
- **Highland accuracy statement (E4).** `core-detector-equations.md` and `multiple_scattering.py` no longer state
  "about 11% for 1e-3 < x/X0 < 100" as current: RPP 2024 Eq. (34.16) gives no numerical accuracy; the range stays
  only as an operating guard (its source edition unverified).
- **`check_citations.py`: DOIs with parentheses.** A bare DOI such as 10.1016/S0168-9002(03)01368-8 was cut at the
  first parenthesis and reported not-verified; balanced parentheses are now part of the DOI.

## 0.18.1 (2026-10-21)

Patch release: the sci-fix ledger review and a corrected citation. Contracts unchanged (3.0.1).

- **Sci-fix ledger reviewed (maintainer decisions).** An AI-written oracle counts as an independent kind only with a
  basis: a located source (equation, table or page, read and recorded), a third-party implementation's own algorithm,
  an exhaustive domain, or a person's check; every counted kind is an `independence` record in
  `docs/evidence/sci-fixes.json`, checked by its test. Locators read for the detector, Bayesian and Feldman-Cousins
  oracles (VALIDATION SCIFIX-LEDGER-REVIEW); new third-party, symbolic and exhaustive cross-checks in the tests; pyhf
  oracles in the required stats-backends gate. Every entry meets its minimum (BAYES-T24's AR(1) check located in
  Thompson, arXiv:1011.0175, eq. (7)). DR-WP2-06 is split into calorimeter, PID and multiple-scattering entries.
- **Feldman-Cousins citation.** The monotone adjustment is Sec. IV.A of the paper (was cited as IV.B), also in the
  `construction` string of the Poisson diagnostics output.

## 0.18.0 (2026-10-20)

Contracts 3.0.1 (patch: the validator's sample-name comparison, below). Three scientific corrections found by the new
oracle tests, sci-fix advisories with a read-only impact scan, and required CI gates for the pdg and PyTorch evidence.
The sci-fix evidence ledger (`docs/evidence/sci-fixes.json`) now meets its minimums for every entry; its grades await
maintainer review.

- **Blinding scanner: integers printed with rounding zeros (sci-fix, BLINDING-ROUNDING-ZEROS).** An integer printed
  without a point or exponent may end in rounding zeros: its trailing zeros are now read as rounding, down to 3
  significant digits, so 22000 or 22,000 (like 2.20e4) and 22010 are hits for a sealed 22014; before, every trailing
  zero was read as a printed digit and the scan passed. 2.2e4 (two digits) stays out of scope; a zero before a point
  (22000.0) is still a printed digit. Cost: round numbers in logs within half a step of a sealed value now alarm
  (4730 for 4731.37); on the example outputs with random sealed values, files with a false alarm rose from 6.2% to
  6.7%.

- **Split keys: a zero fraction keeps the digits as written (sci-fix, CANONICAL-KEY-ZERO-FRACTION).**
  `canonical_key` (split tools and the copy in `assets/train_classifier.py`) read a text ID with a zero fraction
  through int(), so "007.0" was 7 against "007" and "+5.0" was 5 against "+5": the same ID written both ways was two
  groups, and a split check could miss the overlap. Only the zero fraction is dropped now ("007.0" is "007", "+5.0"
  is "+5"); the documented rule that a string keeps its digits ("007" is not 7) is unchanged. The text "-0.0" is now
  "-0", no longer the key of the float -0.0 ("0").

- **Validator: sample names with '.' segments (sci-fix, SAMPLE-NAME-DOT-SEGMENTS; contracts
  3.0.1).** `ml.calibration_on_fit_sample` compared sample names after removing only a leading './', so a
  calibration validated on its fit sample written as 'work/./val_scores.csv' passed. The sample name now drops '.'
  segments anywhere and repeated or trailing separators; '..' is kept (resolving it needs the file system).

- **Sci-fix advisories and impact scan (shadow mode).** `docs/evidence/advisories/` records a corrected defect for
  people holding older results (OSV `introduced`/`fixed` ranges, the scientific impact apart, the ledger entries as
  evidence): SFA-2026-001 to -003 for the three fixes above, and SFA-2026-004 to -035 for the older ledger entries
  whose defect shipped in a release (ROBUST-MALFORMED, S4, and CLS-LOGINTERP, in an example script only, have none).
  `tools/scifix_advisories.py check | affected | scan
  PROJECT_DIR` validates them, lists the affected releases from the release manifests, and reports read-only which of
  a project's artifacts they touch (exit 0 whatever it finds). Format provisional.

## 0.17.0 (2026-10-20)

Contracts 3.0.0 (major): the deprecated skill names are retired, as planned for migration option A (restructuring plan
section 9). Artifacts or profiles that still record an old skill name fail validation here; migrate them with 0.16.x
first.

- **Retired skill names.** The schema enum lists only the eight current skills. A name retired here (the four aliases
  of the 0.11.0 rename and the communication skill's name from the 0.16.0 split) in `provenance.producer_skill`,
  `handoff.to_skill`, an extension `handoff` or a profile's `related_skills` is an error, `skill.unknown_name`, with
  or without `--strict-versions`, and the message says to migrate with hep-research 0.16.x. Any other unknown
  `handoff.to_skill` is the same error (it was unchecked). `--strict-versions` now carries only the version policy.
- **Removed:** `contracts/migrate_skill_names.py`, its fixture and test, and the "Formerly" lines in the skill
  READMEs.
- **`tools/check_retired_names.py`** (a static check of `run_all_checks.py`): fails on any maintained file that
  spells a retired name; the names are kept only as SHA-256 hashes (`contracts.skill_names.RETIRED_SHA256`). History
  files, release manifests, `docs/dev/` and evidence ledgers are not scanned. It replaces the retired-folder check of
  `tests/skills/test_reference_links.py`.
- **Profile ranges.** The ten shipped profiles and the registry fixtures accept contracts `<4.0` (was `<3.0`); the
  ams02-research companion declares `>=2.0` and is unaffected. Older 2.x artifacts with current names keep their
  outcome; fixtures, templates, theory-profile artifacts and examples move to 3.0.0.

## 0.16.0 (2026-10-20)

The communication skill is split into **hep-citations** (sources, citations, literature records) and **hep-authoring**
(papers, figures, diagrams, talks), with a literature-record artifact type and a citation check (restructuring plan,
version 6). Contracts 2.13.0. Static routing passes all 404 cases (394 original reassigned, none deleted, 10 added);
live evals (VALIDATION SPLIT-LIVE-EVAL, about $98 over three rounds): the skills are named hep-citations and
hep-authoring because the host lists skills alphabetically and names sorting after hep-computing let it draw
ambiguous detector requests; after round 2 and a targeted fix (hep-statistics owns whether two results agree) every measured regression is
back at main's level; a final full run scores 371 of main's 394 cases (main 369) plus 8 of the 10 new ones.

- **Two skills replace hep-communication.** hep-citations answers what a paper or an experiment published, whether a
  paper exists, the latest result, whether a source supports a claim and citation requests, from the bound profile's
  ledger or a primary source, never from memory, and owns literature records, matrices and `core/evidence`.
  hep-authoring drafts papers, theses, proposals, talks, figures, diagrams and referee reports. Each description names
  the other in its "Not for" part. The other skills hand write-ups to hep-authoring; the ams-02 profile lists both.
- **Skill names (contracts 2.13.0).** `hep-citations` and `hep-authoring` are skill names; `hep-communication` is a
  deprecated alias of hep-authoring (a warning, an error under `--strict-versions` and protected use), and the 0.11.0
  alias `research-communication` now points to hep-authoring. `contracts/migrate_skill_names.py` rewrites both to
  hep-authoring.
- **`literature-record` artifact type.** `manage_literature.py` (now hep-citations's) writes its record inside the
  common envelope (`producer_skill` hep-citations, status `user-supplied`), so a record in `artifacts_dir` passes
  `contracts/validate.py` instead of failing as `artifacts_dir.not_artifact`. The validator checks that sources and
  claims are keyed by their ids and still pass the evidence-ledger rules. `--into` still reads a bare record written
  before.
- **Citations never from memory: `check_citations.py`.** hep-authoring's new invariant says every citation comes from a
  literature record or a profile evidence ledger. The script reads `.tex`, `.bib` and `.md` drafts and matches each
  citation by identifier (DOI, arXiv id, INSPIRE record), then by stored key. A citation found nowhere is
  `not-verified` (exit 3). A citation recorded only at metadata level, or at another arXiv version, is a warning.
- **hep-citations content.** A literature guide is its entry reference: routing, rules, the latest-result
  procedure, reading profile evidence ledgers and handling a ledger that disagrees with a lookup, the reading
  workflow and an index. The lookup adapter is in the quick-question table. There are three worked examples and a
  citation-databases reference split out of `citations-and-bibliography.md` (hep-authoring keeps BibTeX hygiene and
  style). The two papers indexes of hep-authoring point to the literature guide, and crossing links between the halves
  are rewritten.
- **Shared code.** The audit report shape moves to `contracts/audit_report.py`, used by both halves. It cannot go
  into `core/`, because `core/` may import only `core/`. Literature identifier normalization moves to
  `core/evidence/identifiers.py`.
- **Routing.** The 40 cases that expected hep-communication now expect hep-citations (17) or hep-authoring (23). The
  `not`, `chain`, `turns` and `also_accept` values that named it are reassigned too. Ten cases are new:
  neighbouring and negative cases for hep-citations, four boundary cases between the halves, zh-Hans and ja
  literature cases, a writing-to-literature multi-turn case, and journey J13 (hep-citations → hep-theory →
  hep-statistics → hep-authoring). The ownership table gains five topics; the description-topics table gains rows for
  both skills. The capability map splits `claims-and-literature` into `literature-verification` and
  `claims-to-results`.
- **Plan step 0 (independent of the split).**
  - hep-computing's example-authoring tools (`generate_skill_example.py`, `validate_skill_example.py`,
    `check_example_diversity.py`) and the bundle check `validate_skill_bundle.py` are maintenance tools in `tools/`.
  - `example-authoring.md` is `docs/dev/example-authoring.md`. The task section contract lives in `lint_task.py`.
  - The EIC profile tests read the skill names from `contracts/skill_names.py`.
  - `tools/capability_map.py` derives its valid owners from the skill folders, so a stale owner fails.
  - `tools/check_routing_static.py` reports the description phrases that no case or topic pins (a report, not a
    failure).
  - `tools/measure_entrypoints.py` records each skill's quick-question load (SKILL.md plus its entry reference;
    a warning above 25,600 bytes): hep-citations 18,290 and hep-authoring 21,635 bytes, where hep-communication had
    24,451.
- **Link test.** `tests/skills/test_reference_links.py` checks both new skills, including links into the other skill
  and into profiles, and fails on any maintained file that still names the old skill folder.
- **Citation follow-up hops to hep-citations.** Asked mid-draft whether its citations are verified, hep-authoring
  now loads hep-citations instead of answering from its own resource table (`lit-turns-1` second turn: no skill in 7
  earlier runs, 2/3 live after the change; VALIDATION SPLIT-LIVE-EVAL).
- **Old skill names: one more release.** Migration option A of the restructuring plan: 0.16.0 keeps every deprecated
  name (the four 0.11.0 names and hep-communication) as a warning, and the message now names 0.16.0 as the release of
  the split. 0.17.0 (contracts 3.0.0) removes the aliases and `contracts/migrate_skill_names.py`; migrate old
  artifacts with 0.16.x.
- **Removed:** the pointer `docs/agentic-architecture.md` (renamed `docs/protected-data-architecture.md` after
  0.14.1; removal moved from 0.15.0 to here).

## 0.15.0 (2026-10-19)

Behavioral-eval round (`evals/behavior/`, L3 handoff chains): artifact checks on handoffs and on whole
`artifacts_dir` folders, skill handoffs to hep-statistics, and ML and unfolding tool fixes. Full L3 on main against
#150: Sonnet 43 of 48, Haiku 39 of 48, every fault case passes for Sonnet. Contracts stay 2.12.0.

- **`train_bdt.py` refuses validation parts it cannot score.** When no fold's validation part had both classes,
  every hyperparameter point scored NaN; the script still trained and saved fold models, then crashed writing
  `run_summary.json` (exit 1, a traceback and no JSON status). It now stops before training with exit 2,
  `"status": "rejected"` and each fold's validation counts, and says what to change (`validation_fraction`, fewer
  folds, a finer `event_number` key or more events). A fold whose own validation part is empty still trains, and the
  other folds choose the hyperparameters; the scikit-learn backend no longer crashes scoring that empty part. Seen in
  the L3 ML chain, where Haiku retried four configurations on the 16-event sample and gave up.
- **A BDT's ml-artifact names its fold models.** `skills/hep-ml/scripts/write_ml_artifact.py` read only a run
  summary's `checkpoint`, so `train_bdt.py`'s per-fold `models` were missing from `outputs`; they are now listed as
  `checkpoint:fold<k>`, and a `train_bdt.py` run folder with its ml-artifact passes the `artifacts_dir` check.
  hep-ml's workflow step 3 says configs, run folders and raw tool outputs go in a work folder, not `artifacts_dir`.
  In the L3 ML chain every Sonnet failure after #151 was these files left in `artifacts_dir`.
- **hep-ml hands limits and fits to hep-statistics, even when it was loaded first.** Its opening "Never" line now
  says that a limit, fit or significance with the model belongs to hep-statistics, which is loaded before computing
  one. In the L3 ML chain, Haiku with hep-ml loaded first never loaded hep-statistics in 11 of 12 runs across four
  versions, while workflow step 5 already said to load hep-statistics.
- **The L3 chains' remaining failures.**
  - `skills/hep-statistics/scripts/result_artifact.py` copies vectors and matrices of numbers into `results`, so an
    unfolded spectrum keeps its estimate, sigma and covariances. It also creates the `--out` folder: before, a missing
    folder raised a traceback. `references/unfolding.md` gives the command for an unfolded spectrum
    (`--paradigm likelihood-only --construction other --test-statistic none`). In the L3 unfold runs, agents left the
    result out, saying there was no artifact type for it.
  - `contracts/validate.py` on a directory accepts a file that an artifact there refers to by path, such as the
    `split_report.json` of `train_bdt.py`. The file is listed under `sidecars`. Before, such a file was an error.
  - hep-ml's references say to load hep-statistics for a limit, fit or significance with the model. Before, they
    linked straight into hep-statistics' references.
  - `skills/hep-detector/scripts/build_response.py` skips `#` comment lines in a CSV, as the other hep-detector
    scripts do. Before, every L3 unfold run had to strip a `# SYNTHETIC` header first.
- **Handed-over artifacts are validated on the quick path too, and unfolding loads hep-statistics.**
  - hep-statistics' Step 0 validates a handed-over artifact (`contracts/validate.py <file>`) before running a row's
    tool, even for one number. In the L3 fault cases Haiku took the quick path and skipped step 1's validation.
  - hep-detector's response reference says to load hep-statistics before unfolding or fitting, not to work from its
    unfolding reference alone; `skills/hep-statistics/references/unfolding.md` opens with the same instruction. In
    the L3 unfold chain Sonnet followed the direct link and never loaded hep-statistics.
  - The Resources note that repeated Step 0's script paths is removed, to stay within the 25,600-byte quick load.
- **`contracts/validate.py` checks a whole `artifacts_dir`.** Given a directory, it validates every JSON file under it
  and lists each one.
  - A JSON file without `artifact_type`, such as a raw tool output, is an error (`artifacts_dir.not_artifact`). Any
    other file is a warning (`artifacts_dir.non_json`), because an artifact may refer to it. Hidden files are skipped.
  - `--gate` still takes a single artifact.
  - hep-statistics' step 1 names the file it validates (`validate.py <file>`), so a handed-over artifact outside
    `artifacts_dir` is still validated before use.
  - Context-resolution step 5, and the final validate step of hep-detector, hep-measurement, hep-ml and
    hep-statistics, now run it on `<artifacts_dir>`. The two text-only rounds before it did not stop the agent from
    leaving raw tool outputs there.
- **Producing skills now hand their results to the next skill.**
  - hep-theory: after the comparison gate, it loads hep-statistics for the chi2 or fit and never computes it
    inline.
  - hep-detector: after its two validators, it loads hep-statistics for unfolding or a fit.
  - hep-ml: it writes the `ml-artifact` with `scripts/write_ml_artifact.py` into `artifacts_dir`, and loads
    hep-statistics for a limit or fit.
  - hep-statistics: it writes the `statistical-result` with `scripts/result_artifact.py` into `artifacts_dir`, and
    loads hep-communication for a written report.
  - Context-resolution step 5, in every `SKILL.md`, now says that durable results and handoffs in `artifacts_dir`
    pass `contracts/validate.py`, and that no scratch files go there. The step is the same length as before.
  - In the 2026-10-18 L3 runs, the chain cases failed on scratch JSON in `artifacts_dir` and on hand-written
    artifacts, and most runs never loaded the next skill.
- **The L3 checks are now on the path the agent takes.**
  - hep-theory's workflow step 5 runs `contracts/comparison/gate.py` before any chi2, pull or fit against data. On
    exit 1 it declares transformations or stops.
  - hep-statistics' workflow step 1 validates each handed-over artifact (`contracts/validate.py`, and for a
    response also `response_adapter.py --validate`) and stops on a contract error.
  - In the 2026-10-18 behavioral runs, no L3 run did either.
  - The duplicated Contents list of `skills/hep-statistics/references/core-stats-guide.md` is removed, to keep the
    quick-question load within 25,600 bytes.
- **Profile preflight.** `contracts/project.py <project-dir> --preflight` adds a `preflight` list to its output.
  - Each profile the project binds that ships in the plugin is listed with its `index.md` path, sha256 and text.
  - A bound profile outside the plugin (a local profile or a companion's) is listed as `not-in-plugin`; it is read
    as context-resolution step 3 says.
  - An invalid config lists nothing.
  - Without the flag the output is unchanged.

  Context-resolution step 1, in every `SKILL.md`, now makes this the first action in a project. In the 2026-10-18
  behavioral baseline, the bound profile's `index.md` was not read in 40 of Sonnet 5.5's 47 runs with a blocking
  failure and 63 of Haiku 5.5's 68 (`evals/behavior/README.md`).
- **Two new validator warnings**, for SKILL.md invariants that had no check:
  - `stats.construction_missing`: a frequentist limit names no construction (hep-statistics: approximations are
    named);
  - `ml.weights_not_separated`: weights enter the loss without separate `weights.training` and
    `weights.evaluation` blocks (hep-ml).

  Both are warnings, so artifacts that validated before still validate; contracts stay 2.12.0.

- `docs/agentic-architecture.md` is renamed `docs/protected-data-architecture.md` and retitled "Protected-Data
  Architecture: Blinding, Custodianship and Egress": it describes how blinded and private data are protected when
  an agent takes part, not an agent workflow. Section numbers and constraint IDs are unchanged. Every live
  reference is updated, including the stage reference in `skills/hep-computing/examples/agentic-loop-task.md`. The
  old path holds a pointer until 0.15.0. The planning ID AGENTIC-R5 is kept for traceability. Documentation and
  comments only; no behavior changes, contracts stay 2.12.0.

## 0.14.1 (2026-10-17)

Routing fix after the first live run of the cases added in batches A-D (`evals/routing/`, 117/135 on 0.14.0).
Contracts stay 2.12.0.

- Descriptions: hep-detector names geomagnetic cutoff backtracing (OTSO); hep-theory names importing a published
  HEPData, CSV or FITS table for a comparison; hep-computing's "Not for" names both owners. The four cases that went to
  hep-computing in both languages now route to their owners; a 180-case check of the three skills showed no
  regression (repeats against 0.14.0 for every case that changed).

## 0.14.0 (2026-10-17)

The upgrade plan v1.3 (88 items in six batches, PRs #131-#136). Contracts 2.12.0: vocabulary and optional fields only
(levels, two artifact status labels, four effects and a composition, optional measurement-spec fields, the profile kind
`reference`); a 2.11 artifact keeps its outcome. Every analysis-check rule stays in shadow mode. The batch notes below
say "no version bump" for each batch; this release is that bump.

Upgrade plan v1.3, batch 0a (F-01 to F-15): correctness and risk fixes, each with a regression test that fails on
its parent commit (VALIDATION UPGRADE-0A). Contracts stay 2.11.0 with one additive vocabulary change (F-14); no
version bump. Every analysis-check rule stays in shadow mode.

- Statistics.
  - `covariance_fit.py`: a grid fit whose optimizer stopped before converging is `failed` (exit 1), not `ok` (F-01).
    A plugin model runs only with `--allow-plugin`, its path is read relative to the input file, and its errors are
    `failed` JSON, never a traceback (F-09).
  - `result_artifact.py --paradigm frequentist|bayesian|likelihood-only` (default frequentist, unchanged output); a
    Bayesian result is written from `bayes_diagnostics.py diagnose` output with priors, sampler and convergence (F-02).
  - `li_ma_significance.py` prints `status`, `method_kind: asymptotic` and a low-count warning (F-03).
- Script contract (F-04). `core/status.py` (owner hep-computing): run statuses, exit codes 0-3, the mapping to
  artifact status labels and `add_status_argument`. The plugin-wide test `tests/skills/test_cli_contract.py` checks
  exit codes, a JSON status on a refused input and `--status`; the scripts of the other skills that print no JSON
  status on a refused input are listed there for follow-up. `inference.py --on-out-of-domain reject` exits 1 (was 4)
  with status `refused`. The hep-theory and hep-ml scripts print JSON statuses on refused inputs and take
  `--status`, echoed as `status_label`.
- `review_analysis_change.py`: every verdict other than accept exits 1; text outside the Latin script, which the
  English-only patterns cannot judge, is `needs-human-review` (F-05).
- `pid_separation_power.py`, `cherenkov_angle.py`, `geomagnetic_cutoff.py` report `inputs` and `defaults_used`
  and warn when a detector parameter or the dipole moment is defaulted; `geomagnetic_cutoff.py --epoch` (F-06).
- Partition merge rules (F-07): `sum`, `min`, `max`, `first`, `concat` per key (`engine.merge(rules=)`,
  `local_partition.py merge --rule`, `batch_campaign.py merge/report --rule`). Undeclared keys still sum; an
  undeclared key named like a non-additive quantity (seed, median, mean, quantile, min, max, rate, fraction) is
  refused.
- hep-ml hashes (F-08): `train_classifier.py` records `split_manifest_sha256`, `calibration.py` records
  `model_hash`, `inference.py` refuses a calibration made for another model and reports a changed split manifest.
- No `__pycache__` from scripts (F-10): 40 scripts set `sys.dont_write_bytecode` before importing siblings or plugin
  packages; `tests/skills/test_no_bytecode.py` runs every CLI from a copy of the plugin.
- Documentation consistency (F-11): the ninth derivation status in the hep-theory README and reference; the uproot
  claim of the hep-computing README; the communication-evaluation row; the SKILL.md size record; the solar cycle as
  a SILSO lookup; `train_classifier.py` drops `accuracy_weighted`; RooFit's `AsymptoticError` treats weights as known.
- Communication (F-12): the paper skeleton uses `unsrturl` (prints eprints and DOIs) and a `[VALUE NEEDED]`
  headline; the claim-wording patterns cover Simplified Chinese.
- Side effects (F-13): a local partition worker gets a default timeout of 3600 s; `check_diagram_sources.py
  --no-mermaid`; the CERN EOS note says to ask before writing.
- Vocabulary (F-14): core levels `top-of-instrument` and `top-of-atmosphere`; the synthetic cosmic-ray spec uses the
  first.
- Documentation-claim tests (F-15) for the hep-statistics and hep-detector statements about script output. The audit
  found that `validate_covariance.py` and `validate_response.py` did not label their output `[General method]` as the
  core/stats guide says; their CLI output now carries the label (also on a refused input).

Upgrade plan v1.3, batch 0b (B-01 to B-05): budgets and entry points (VALIDATION UPGRADE-0B). Live routing has not
been run for the new descriptions and routing tables (gate G2).

- Budget (B-01): `tools/measure_entrypoints.py` warns above a 12,288-byte SKILL.md target (waivable in
  `tools/budget_exceptions.json`) and fails above 16,384 bytes or 500 lines; descriptions stay at 1,024 characters
  (Agent Skills specification), the registry at 3,072 bytes. Output gains `warnings`; `--root`.
- Routing tables (B-02): every SKILL.md has a 1.7-2.0 KB "request -> file or script" table under `## Resources`;
  SKILL.md files are 7,895-9,322 bytes.
- Lighter entry references (B-03): the hep-measurement guide puts routing first and moves the cosmic-ray invariants
  to `cosmic-ray-measurements.md`; the detector principles summary links instead of repeating the comparison tables
  and checklists; `ml-analysis.md` is a 7 KB core with four subfiles; the papers guide keeps the method (review modes
  and the reference index move to `papers-review-modes-and-reference-index.md`); the core/stats guide's failure
  modes move to the command reference. SKILL.md plus entry reference is at most 25,321 bytes for every skill.
- Descriptions (B-04): six descriptions from the plan's Appendix J (hep-measurement unchanged; hep-communication
  keeps "compatibility", a recorded routing fix); 18 routing cases (259 in all).
- Reference soft budget (B-05): `tools/reference_inventory.py` warns, without failing, on an entry reference's
  routing part above 4 KB and on any reference above 24 KB.
- `validate_covariance.py` and `validate_response.py` label their CLI output `[General method]`, as the core/stats
  guide says (follow-up to the F-15 audit).

Upgrade plan v1.3, batch A (Th9, Th7, D7, D1, M5, Th3, ML2, Com1, Com3, X3, X1, X2): test bed, foundations and scope
(VALIDATION UPGRADE-A). Contracts stay 2.11.0 with one additive optional field (M5, gate G4); no version bump.

- Constants and particle/nuclear data (Th9): `core/constants` (steward hep-theory) with CODATA 2022 (exact SI
  constants marked exact; hbar, hbar c and (hbar c)^2 derived from the exact h, c and e), a PDG 2026 subset of 32
  particles (via `pdg` 2026.0; CC BY 4.0) and AME2020/NUBASE2020 data for 40 nuclides, each value with uncertainty,
  unit, source and edition; full tables through user-supplied AME/NUBASE files. New CLI
  `skills/hep-theory/scripts/physical_data.py` (`get`, `particle`, `nuclide`, `convert`, `qvalue`, `edition`, `list`;
  `particle --backend pdg` with the new optional extra `pdg`, gate G5). `geomagnetic_cutoff.py` takes its masses from
  core with bit-identical output. A scan of the code of skills/, core/ and profiles/ refuses unlisted mass literals;
  the CODATA 2018 pins of two theory profiles are allowlisted with their claim IDs.
- sci-fix (Th9, gate G7): `pid_separation_power.py` (and `cherenkov_angle.py`, which uses its table) take the CODATA
  2022 / PDG 2026 masses instead of rounded ones; the He4 Cherenkov test values move by at most 3e-9 relative (old
  and new values in the commit and the test).
- Kinematics (Th7): `core/kinematics/fourvector.py` and `skills/hep-theory/scripts/kinematics.py`: two-body decays
  (Kallen function), Lorentz boosts, invariant masses, Mandelstam variables, fixed-target thresholds, Dalitz
  boundaries, rapidity and pseudorapidity, width/lifetime/c tau.
- Detector (D7, D1): `toy_spectrometer.py`, a seeded synthetic spectrometer with a fictional configuration (layers,
  field model, charge estimator, velocity detector, species, eras, periods; byte-reproducible from the seed);
  `propagate_scale_distortion.py` (`response`, `events`: scale, inverse-offset, resolution and plugin modes, the
  opposite-sign ratio, `{nominal, up, down}` variations, a correlated covariance block, `--validation-record` on
  request) and "Propagating a calibration residual" in `calibration-and-alignment.md`.
- Measurement (M5): scaling classes of systematics (statistical-like, floor, mixed) in `systematics.md`; optional
  spec field `systematics[].scaling` (gate G4).
- Theory (Th3): charge-sign-dependent modulation in the force-field section of `cosmic-ray-propagation.md` (drift
  limits, polarity eras, one phi per period; the cycle-25 reversal cited from arXiv:2606.15259 with its hedging).
- hep-ml (ML2): `make_grouped_splits.py --stratify-column` and composite `--group-column` keys;
  `check_split_integrity.py` reports per-stratum coverage.
- Communication (Com1, Com3): planned claims (`kind: planned`, `recheck_by`) are flagged after their date
  (`manage_literature.py`, exit 3) and never support a measured result (`audit_claims.py`); the glossary template adds
  collection time, exposure (normalization, with effect IDs), data exposure (blinding), rigidity and momentum in
  English and Traditional Chinese, and `check_terminology.py` warns on mixed use.
- Scope (X3, X1): `docs/capability-map.json` and `.md` (owner, state, in v1; generated by `tools/capability_map.py`);
  `check_routing_static.py` requires a limited-support routing case for every domain outside v1; a generated "Scope
  of v1" section in `docs/routing-contract.md`; routing cases `th-scope-2`, `th-flavour-2` and three more
  limited-support cases.
- One owner per topic (X2): the propagation equation, B/C and the force-field formula live in hep-theory, period
  searches in hep-statistics; the other copies are links. `tools/reference_inventory.py` makes a cross-skill overlap
  an error.
- Routing cases: 282 (23 new).

Upgrade plan v1.3, batch B (C1, M1, D9, D5, D10, D11, M7, D8, M3, D6, S1, S6, ML1, ML3, S11, and the first part of
E-3): tools needed before a detector-configuration change (VALIDATION UPGRADE-B). Contracts stay 2.11.0 with additive
changes behind gate G4 (one effect, one composition, optional spec fields); no version bump.

- Time-sliced inputs and collection time (C1, M1): `skills/hep-computing/assets/time_slice_reduction.py`
  (deduplicate by a stable key, then sum; partials merged through `core/partition`); `collection_time.py`
  (`accumulate`, `--emit-partial`, `merge`): live time above the cutoff per era, time bin and variable bin, from a
  declarative configuration with no defaults. Effect catalog: `cutoff_transmission` and the composition
  `exposure_acceptance_livetime_transmission`, with coverage entries; the analysis check picks the composition a
  factor table completes, so existing reports are unchanged.
- Responses (D9, D5): `build_response.py` writes a validated response artifact from matched truth, reco, weight and
  selection (resolution core and tails, multinomial MC uncertainty, `--fold`); `mix_period_responses.py` mixes era
  responses per truth bin with acceptance x collection time, or stacks them for a joint fit.
- Detector (D10, D11, D8, D6): `multisample_pid.py` (charge from many samples with the leakage matrix; likelihood
  ratio with the efficiency-rejection curve); `stability_monitor.py` with `core/stats/change_point.py` (trends,
  change points and CUSUM with toy-calibrated thresholds, proposed calibration eras never written into a spec);
  `tag_and_probe_efficiency.py --probes` with frequency or sampling weights (Kish n_eff), `--bins`, and no cap on the
  total; "Adding a tracking layer to a running detector".
- Measurement (M7, M3): `spectrum_transform.py` (a bin-averaged flux in another spectral variable with an isotope
  composition and its covariance); optional spec fields `eras[]` and `systematics[].era_correlation` with four era
  review rules in `review_measurement_spec.py` (gate G4).
- Statistics (S1, S6, S11): `split_consistency.py` (split samples with the shared covariance subtracted; asymptotic
  and toy p-values; Sidak correction for several splits); "Multi-era joint fits"; `roofit_fit_check.py` maps a saved
  RooFitResult (status, covQual, EDM) to the result status and requires a declared error treatment for weighted data.
- hep-ml (ML1, ML3): era changes in ML studies; `train_bdt.py`, a cross-trained BDT (xgboost or scikit-learn
  HistGradientBoosting; new optional extra `bdt`, gate G5) with a declared negative-weight policy, Asimov or AUC
  selection on validation folds, no pickle.
- Example `examples/multi-era-fit/` (E-3, first part): the chain above on two synthetic eras with a layer added
  midway; joint-fit coverage 0.689 over 1,000 toys; S1 catches a 5% offset in one era.
- Routing cases: 312 (30 new).

Upgrade plan v1.3, batch C (Th1, D4, D3, D2, M4, E-1, Th8, M8, M10, Th4, Th10, Th12, S2 with the E-3 projection, S7,
S8, ML4, ML3 extensions, S11 extensions, C7, Com6, Com7, D13, D14, E-2, E-4) (VALIDATION UPGRADE-C). Contracts stay
2.11.0 with additive changes behind gate G4 (two effects, two artifact status labels, an optional spec field, a
profile kind); no version bump.

- Nuclear physics in material and species (Th1, D4, D3, D2, M4, M8): nuclear cross-section conventions;
  `survival_feeddown.py` (survival probability and first-order feed-down; effects `survival` and
  `fragmentation_feeddown`); `charge_confusion_rate.py` (template, control, gaussian-core reference);
  `species_response.py` (block responses for species migration; a double count between a block and the correction
  chain fails); spec field `coupled_backgrounds` with rule `coupled.fixed_subtraction`; `isotope_fraction.py`.
- Theory (Th8, Th4, Th10, Th12): `import_published_table.py` (CSV, FITS, HEPData to a dataset record with a
  provenance sidecar; no network); `neutrino_oscillation.py` (PDG PMNS convention, vacuum and constant-density
  matter; neutrino oscillations enter v1); `running_coupling.py` (alpha_s at 1-4 loops with threshold matching) and
  `particle-physics-essentials.md`; `decay_chain.py` (Bateman and matrix exponential) and
  `nuclear-physics-essentials.md`; `core/constants` converts year-unit half-lives with the NUBASE2020 year
  (365.2422 d).
- Measurement (M10): rare-event and neutrino measurements (exposure and live time, ROI without unblinding, salting,
  background budget, quenching, near/far).
- Statistics (S2, S7, S8, S11): `project_uncertainty.py` (label `projection`, refused by the publication gate);
  `--allow-outside-validated-range` on every overridable core/stats cap (label `outside-validated-range`, refused
  without a validation record); `tail_extrapolation.py`; `roofit_fit_check.py toys` and `crosscheck`, and
  `roofit-and-roostats-methods.md` (the RooFit sections of `likelihood-fitting.md` moved there).
- hep-ml (ML4, ML3): `domain_shift_report.py` fills the ml-artifact `domain_shift` block; `train_bdt.py` regression
  and mass-sculpting report; `export_bdt.py`; external TMVA or LightGBM scores through the inference checks.
- Computing (C7): ROOT usage patterns and `check_histogram_errors.py` (PyROOT or uproot); the object / interval /
  efficiency boundary in `docs/routing-contract.md`.
- Communication (Com6, Com7): paper blueprints and `check_manuscript.py --blueprint` (advisory);
  `render_results.py` (macros and tables traced to artifacts, synthetic watermarks a final build refuses), the PDG
  rounding rule, `check_manuscript.py --numbers`, `audit_claims.py --compare`.
- Detector (D14, D13): `detector-design-principles.md` and `tracker_resolution.py`; the sourced detector atlas, a
  new profile kind `reference` at `profiles/reference/detector-atlas/` (60 claims for six experiments) with
  `detector_atlas.py`; hep-detector owns `detector design principles` and `sourced detector atlas` (gate G3).
- Examples: `examples/bc-fragmentation/` (E-1), `examples/pbar-p-curvature-offset/` (E-2),
  `examples/analysis-to-paper/` (E-4); `examples/multi-era-fit/` gains the S2 projection check (new keys only).
- Routing cases: 356 (44 new; `th-scope-2` becomes a direct case).

Upgrade plan v1.3, batch D (S3, S4, S5, S9, S10, M2, M6, M9, Th2, Th5, Th6, Th11, C2, C3, C4, C5, C6, Com2, Com4,
Com5, D12, and the D13 expansion) (VALIDATION UPGRADE-D). Contracts stay 2.11.0; no version bump. Two new optional
adapters wrap third-party code that the plugin never bundles (gate G5).

- Statistics (S3, S4, S5, S9, S10): `build_covariance.py` ([Proposal] covariances from declared correlation models,
  with a length scan; a non-PSD block is reported, never repaired); `covariance_fit.py` joint fits with a per-dataset
  `scale_nuisance` (unchanged without the declaration); `periodicity_scan.py` (weighted generalized Lomb-Scargle with
  white, AR(1) or OU surrogates and a band-maximum global p-value); `time_structure.py` (change points with a
  toy-calibrated penalty, lags with autocorrelation-preserving surrogates); `adapters/unfolding/` (pyunfold, and
  RooUnfold when built, with the plugin's own closure, stress and coverage validation).
- Measurement (M2, M6, M9): `acceptance_from_generation.py`; `cosmic_ray_flux.py` reports a free bin-width unit and
  has an asymptotic interval beyond the Feldman-Cousins grid (`auto`); `orbit_averaged_geomagnetic_cutoff.py` maps
  retrograde inclinations and takes `--edges`; `anisotropy.py` (right-ascension exposure, first harmonic, dipole
  projection, amplitude upper limit, spurious-modulation checks).
- Theory (Th2, Th5, Th6, Th11): `lepton_energy_losses.py`; `dm_direct_rate.py` and `dark-matter-phenomenology.md`
  (dark-matter phenomenology conventions enter v1; interpreting an excess stays outside v1); `coalescence.py` and
  `light-nuclei-coalescence.md`; `secondary_gamma.py` and `astroparticle-essentials.md`.
- Computing (C2-C6): `environment_manifest.py pairs`; the preservation checklist; an uproot reader for
  `summarize_histogram_statistics.py` and the Python floor tiers; columnar and large-scale data with
  `assets/chunked_histogram.py`; analysis workflows with `run_workflow.py` and a Snakefile template.
- Communication (Com2, Com4, Com5): the flux-measurement reporting policy 1.2.0 (refold kit, collection-time
  definition, bin position, variable conversion, era); seven more venues with sources or to-verify, Chinese
  typesetting and a XeLaTeX thesis skeleton, diagram files by extension, read levels in reading notes and
  `build_lit_matrix.py --require-provenance`; `spectrum_plot.py` (dataset-records only, a stated bin position,
  status labels, overlays never combined).
- Detector (D12, D13): `adapters/geomagnetic-backtracing/` runs OTSO (GPL-3.0) as a separate program with a
  user-supplied interpreter, never imported or bundled; the detector atlas adds Belle II, ALICE, DUNE, JUNO, XENONnT
  and the Pierre Auger Observatory (12 experiments, 123 claims).
- Routing cases: 394.

## 0.13.1 (2026-10-17)

G-ENFORCE inputs completed for the full v6.3 suite set, and README updates. Contracts stay 2.11.0, and every
analysis-check rule stays in shadow mode. The companion ams02-research needs no change.

- `permit.py check-report` (advisory, v6.3 G-ENFORCE inputs):
  - It refuses a report whose roots fall below the purpose policy's new optional `min_evidence_level` (`declared` or
    `campaign-recorded`; O15).
  - It treats a per-root evidence level that does not follow from the report's `r-run.campaign` outcomes as a hand
    edit (`permit.report_inconsistent`).
  - It never counts a model-only bundle toward formal use (`permit.report_model_only`; O13).
- The shadow difference review (`analysis_check.difference_review`) covers the model and run cases.
  - A legacy model-card error and the new rule deciding the same question are classified as agreeing:
    `stats.duplicate_auxiliary` with `r-aux.use`, and an unconstrained parameter or POI mismatch with
    `r-model.pairing`.
  - No case leaves a difference unclassified (`docs/dev/v6.3/shadow-review.md`).
- `docs/dev/v6.3/custodian-gate-requirement.md` adds the post-execution conditions, the evidence floor, the
  integrity of evidence levels and the model-only rule for the custodian's gate.

## 0.13.0 (2026-10-16)

v6.3 analysis-check programme completed on synthetic cases. The release adds:
- the model-card suite (M2b model part);
- the stage-1 custody inventory (V30);
- run lineage with result bindings (M2c).

All 80 V parts pass. **Contracts 2.11.0**: new sidecar formats only (the model bundle mode, the pairing contract, the
result binding); no artifact type changes, and a 2.10 artifact keeps its outcome. Every analysis-check rule stays in
shadow mode: reports are diagnostics, enable no gate, and are self-reviewed (C15). The companion ams02-research needs
no change: it requires hep-research >=0.11.0, and its namespace check against this release reports no findings.

- Run lineage `run-lineage/v1` (v6.3 M2c; design `docs/dev/v6.3/m2c-design.md`; decision `m2c-proposal.md`), opt-in
  and in shadow mode.
  - **Two-stage check.** A chain context selects the suite, and its obligations are frozen before execution.
    - Before execution they are unverified (`check.not_executed`).
    - After execution, `analysis_check.py check ... --results BINDING [--project DIR]` assesses them against a result
      binding: a new sidecar, `contracts/schemas/result_binding.json`, written after execution and never inside the
      bundle.
  - **Five rules** (owner hep-computing):
    - `r-run.binding`: the same bundle and lock, and the root's unit, scope and binning. A different lock is semantic
      drift. The attribution is a declaration.
    - `r-run.status`: one named, successful terminal run or a complete merge. Failures propagate; cycles and
      duplicate run IDs are rejected.
    - `r-run.closure` (R-CLOSE): each input maps by explicit reference to a frozen item, an external manifest entry or
      a bound upstream product. A re-serialized JSON input is a derived input.
    - `r-run.campaign`: the adapter's computational-run, the `state.json` collection records, the chunk files and one
      common recorded execution bundle (`digest_of`, `check_campaign`) must agree, or the root stays at the declared
      level.
    - `r-run.blinding`: implements the approved `allowed_outputs` matching rule. Only exact `path:` or `artifact:`
      entries match; unprefixed entries match nothing.
  - **Reports.** A post-execution report states its phase, the binding's digests and the execution evidence level
    per root. It carries digests and labels only, never result values.
  - **`permit.py check-report`** refuses a post-execution report whose cited results are not in the permit's
    `artifacts`, or whose execution bundle is not the permit's.
  - **Refusal matrix.** It gains three result-binding rows: `validate.py` and the measurement-spec review refuse a
    binding, and `dependencies.py` accepts it, the same documented behaviour as for a check context.
  - All 80 V parts of the programme pass. The run-lineage V cases are V20, V32, V33, V38, V53, V54, V55, V56, V61, V62,
    V63 and V70, plus the post-execution part of V60.

- New `contracts/custody.py PROJECT_DIR [--local DIR ...]` (v6.3 D12b, V30). It is a custody inventory of every
  profile a project sees, at companion transition stage 1: an inventory and report only, which loads nothing
  differently and relaxes no refusal.
  - **Plugin profiles:** public, because of where they ship.
  - **Folders supplied at run time** (a companion's `--local`): known-controlled with custody metadata missing,
    `unverified`.
  - **A project's own local profiles:** custody `unknown`, `unverified`.

  A missing `custody_domain` is never read as public, even when a local profile's content looks public. Rejected
  profiles keep their rejection codes.
- Model suite `model-card/v1` (v6.3 M2b model part; design `docs/dev/v6.3/m2b-model-design.md`), opt-in and in shadow
  mode.
  - **New bundle mode `model`**, for model-only diagnostics: `analysis_check.py freeze --mode model`. It takes one or
    more `model-card` items. The context names `models`, `evaluations` (one likelihood each, with explicit
    cross-model `shared_parameters`) and `model_roots`. A new binding type, `observes`, ties a model's `aux_id` to one
    observation, identified as an item plus a JSON pointer.
  - **Four rules**, owner hep-statistics:
    - `r-model.root`: the root intent.
    - `r-model.pairing`: exactly the O03 pairings P1–P3 of the new pairing contract
      `contracts/semantics/model_pairings.json`, which the semantic lock pins. Anything else is `unsupported`.
    - `r-aux.use` (R-AUX): an observation encoded by two constraint terms of one evaluation is violated; an unbound
      constraint leaves the others unverified; two components of one file stay distinct.
    - `r-share.parameters`: incompatible cross-model shared parameters are violated; compatible ones and joint
      evaluations of several cards are unsupported, because the adapter has no combiner.
  - **Other changes:**
    - A chain bundle that selects a model suite is refused (`bundle.suite_mode`).
    - The pyhf-combine adapter's refusal of Poisson and log-normal constraints, and its fixed parameter bounds, are
      now tested.
    - hep-statistics' nuisance-modeling reference names the check.
  - V06, V07, V08, V46, V47 and the model parts of V11, V15, V18, V24, V25 and V64 pass (67 of 80 V parts).

## 0.12.0 (2026-10-16)

v6.3 analysis-check programme (M0–M3, opt-in and advisory), the cosmic-ray propagation adapter and heliospheric
modulation profile (WP13–WP16), and fixes. **Contracts 2.10.0** (capability `measurement:correction-keys-v1` and the
analysis-check sidecar formats; no artifact type changes, a 2.9 artifact keeps its outcome). Every analysis-check rule
is in shadow mode: its reports are diagnostics and enable no gate. `experiment:ams-02` drops the undefined, unused
level `crflux:local-interstellar`. The companion ams02-research needs no change (it requires hep-research >=0.11.0;
its namespace check against this release reports no findings).

- **Contracts 2.10.0.** The v6.3 analysis-check additions are now a contracts minor: the capability
  `measurement:correction-keys-v1` and the sidecar formats of `contracts/analysis_check.py` (analysis bundle /2, check
  context, semantic lock, check report, validation record, effect catalog, operator coverage, rule registry). No
  artifact type changes; a 2.9 artifact keeps its outcome. All analysis-check rules stay advisory and in shadow mode.
- `experiment:ams-02` no longer declares the level `crflux:local-interstellar`. No file defined it and nothing used
  it (`docs/dev/v6.3/crflux-review.md`); `crflux:top-of-instrument` is unchanged. Interstellar spectra keep their own
  terms in the theory profiles (`crsr:local-interstellar`).
- `recipe_semantics.py` refuses an `--upstream` artifact that requires a capability it does not implement
  (`semantics.upstream_unknown_capability`; nothing is read from it). No existing fixture declares such a capability,
  so no existing output changes (v6.3 G-ENFORCE step 1, refusal matrix).
- Advisory report check (v6.3 D10): `permit.py check-report` counts an analysis-check report only among an accepted,
  bound review's evidence, about the permit's bundle, consistent with its own obligations (a hand-edited pass fails),
  from the suites and checker of the custodian's purpose policy, complete and without violation; a pre-execution
  report passes only if the policy accepts it (codes `permit.report_*`; `formal_use_allowed` stays false). The
  existing `permit.py verify` is unchanged. `attestation.py` digests an analysis bundle 2.0.0 with the 1.0.0 rule.
  `analysis_check.py check --exceptions FILE` judges scoped exceptions (accepted only for a waivable rule, the
  finding as reported, a person, a rationale and a future expiry); they never change a state. The requirement for
  the custodian's gate is `docs/dev/v6.3/custodian-gate-requirement.md`.
- Shadow review and refusal matrix (v6.3 D09). `analysis_check.difference_review` classifies every legacy finding and
  every new violation (artifact-local, recipe-local, agrees, new-decides, new-only); on the chain and ratio cases none
  is unclassified. `contracts/rules/refusal_matrix.json` (record `docs/dev/v6.3/refusal-matrix.md`) states what each
  old entry point does with each new format, measured on this tree and on the 0.11.0 release: two readers do not
  refuse (`dependencies.py` accepts a check context; `recipe_semantics.py --upstream` reads capability-gated
  correction keys) and are listed as release blockers.
- Definition snapshots and migration (v6.3 D11b). `analysis_check.py freeze --snapshots DIR` stores every definition the
  semantic lock pins (coverage contracts, catalog effects, compositions, member-set closures, suites, rule registry)
  content-addressed; `check --snapshots DIR` reproduces a subject whose installed definitions changed from that
  snapshot (report `semantics_source: snapshot`, with the installed differences listed), leaves it unverified when a
  pinned digest is missing (never falls back to the latest) and reports a rewritten snapshot as invalid input. The
  lock now pins the suite files too; a changed checker code alone is reported (`checker_changed`) as a new assessment,
  not as a definition difference. New `contracts/migrate.py` converts items of a frozen bundle (lossless converter
  `recipe-1.0.0-to-1.1.0`) into a new folder leaf to root and writes `MIGRATION-COMPLETE.json` only after the new
  bundle verifies and loads; on failure no marker is written and the original files are unchanged.
- Ratio subset (v6.3 D07, suite `ratio-subset/v1`): a check context may select further suites and name ratio roots of
  two chain roots. `r-ratio.operands` requires compatible operands, `r-ratio.cancellation` counts a claimed
  cancellation as exact only for the same factor instance, selection and power with a nonzero factor (different bins
  of one calibration table leave a residual, summarized per bin), and `r-ratio.correlation` needs a validation record
  (new schema `validation_record.json`, bundle role `validation-record`) or a sourced or scoped declaration; bare
  claims stay unverified. The coverage contract now states the efficiency factor power of `correct_efficiency` and
  `divide_effective_exposure`. Model-card checks are not built.
- Analysis check hardening after review (v6.3 M2a): recipes, tables, coverage contracts and spec corrections are
  checked against their schemas at freeze (refused) and at check time (input invalid, never a traceback); duplicate
  spec `effect_id`s are invalid; `freeze` writes the context and lock only after every check passes and refuses an
  output path the context or lock would use; an outcome reached through a declaration is flagged whatever its state
  and the formal-use view demotes declaration-based `not_applicable` too; a root needs its recipe's estimand; factor
  tables need finite, non-empty bins; an uncomparable target scope is unverified, not a conflict; an inventory that
  differs only because definitions drifted is reported as drift (exit 3), not invalid input; malformed CLI inputs
  exit 2.
- `review_measurement_spec.py` takes `--check-bundle BUNDLE --check-root DIR` (opt-in, v6.3 D17): the review then
  carries `analysis_check`, a bounded summary of the cross-artifact check (status, coverage, consistency, missing
  bindings, one row per violated or unverified obligation with its next step), capped at 8 KiB per page. The verdict
  and exit code are unchanged, and without the flags the output is identical. The review reference names the call.
- Old-table reader `contracts/analysis_checks/readers.py` (v6.3 D11a): the chain rules read the 1.0.0 operator-semantics
  table through the coverage contract the semantic lock pins; an unpinned or changed contract, or a table that no
  longer matches the contract, gives no operators (unsupported). The table file is never upgraded.
- Chain rules of the `counting-chain/v1` suite (v6.3 D06, `contracts/analysis_checks/rules.py`), each returning one
  of five states with a registered reason code: R-REAL (a spec correction is realized by exactly one compatible
  application in each instance it applies to; no broadcast without a spec `target_scope` or an `instance_mapping`
  declaration; a conflicting `application_id`, scope, variation or calibration is a description conflict), R-STAGE
  (applied_in against the operator's stage), R-REP (no member applied twice on one computation path, judged from
  `input_of` data flow; variation labels and calibrations grant no exemption, opaque scopes stay unverified, a declared
  exclusion for one selection is a contradiction), R-COMP (a parent factor and its decomposition on one path; per-bin
  factor tables summarized per relation without values) and R-RESP (unfolding needs a bound unfolding response; a
  spec that says unfolding against a chain that does not unfold is violated; forward folding is unsupported).
- `contracts/analysis_check.py check BUNDLE --root DIR [--out REPORT] [--previous REPORT]` (v6.3 D05c) evaluates a v2
  bundle's frozen obligation inventory and prints a report (schema `check_report.json`): input validity, coverage
  (completed over all), consistency, per-obligation state with reason and evidence pointers, declaration-based flags
  and a formal-use view that counts them as unverified, legacy L1 and L2 findings in their own field, lock differences
  and the scope delta against a previous report. An obligation whose rule did not run is unverified. `assessment_id`
  binds subject, suite, rules, rule registry, checker code, readers and settings. Exit codes 0/1/2/3 with precedence
  2 > 1 > 3 > 0; the report is a sidecar that is never written into the bundle or over an existing file, and
  `summary REPORT` pages a bounded agent summary. The suite's rules are registered in `contracts/rules/registry.json`
  with reason codes for all five states.
- New opt-in `contracts/analysis_check.py` with analysis bundle 2.0.0 (`hep-research-analysis-bundle/2`, schema
  `analysis_bundle_v2.json`; v6.3 D05b): per-mode roles (chain: one spec, environment lock, check context and semantic
  lock, at least one recipe), unique item IDs, and for JSON items both the canonical and the bytes digest. New roles
  `response`, `dataset-record`, `context`, `semantic-lock`, `coverage-contract`. `freeze` completes the check context
  (schema `check_context.json`) with the obligation inventory of the suite (`contracts/rules/suites/`), generated
  deterministically by `contracts/analysis_checks/obligations.py` from roots, instances and spec corrections only, and
  records the semantic lock (`semantic_lock.json`, `contracts/analysis_checks/lock.py`: definitions in use with their
  digests and member-set closures). Bundle 1.0.0 and `contracts/analysis_bundle.py` are unchanged; that reader refuses
  a v2 bundle by its schema.
- New capability `measurement:correction-keys-v1` (v6.3 D05a): a measurement-spec that declares it may give each
  correction the R4 keys `target_scope`, `calibration_digest`, `variation_id`, `stage` and an `application_id` (a
  recipe `step_id`); `validate.py` then knows them and rejects a malformed one (`measurement.bad_correction_key`). A
  spec without the capability keeps its `measurement.unknown_key` warnings, and a reader without the capability refuses
  the spec. New pure modules `contracts/analysis_checks/` (`scope.py`: bounded `axis:value` scopes where a missing
  axis is never a wildcard; `instances.py`: read-only recipe instance views that fill only unspecified keys, with a
  source pointer per field; `context.py`: check-context bindings and attributed declarations, never a rule waiver).
- New effect catalog `contracts/vocab/effects.json` and operator coverage contract
  `contracts/semantics/coverage/differential-flux.coverage.json`, checked by `contracts/effect_catalog.py` (schemas
  `effect_catalog.json`, `operator_coverage.json`; v6.3 D04). The catalog classifies effects (an efficiency class with
  listed members) and states conditional compositions (exposure = acceptance × live time only under its listed
  conditions). The coverage contract binds the existing `differential-flux` table by its digest and lists, per
  operator, its stage, the effects and class members it covers and its factor powers; where the table leaves the
  efficiency members of an operator undefined (`unfold_with_efficiency`, `divide_effective_exposure`), every member is
  unverified rather than inferred from the class. `coverage_state` and `resolve_members` (member closure with its
  dependencies and digest) are for the later chain checks. The legacy table, its digest, `IMPLIED_CORRECTIONS` and
  the `<x>_efficiency` rule are unchanged, and no existing entry point reads the new files.
- Profile loading respects load errors everywhere (v6.3 D03a). New `contracts.registry.load_registry` separates usable
  profiles from rejected ones (a profile with an error of its own, such as `profile.incompatible_version`, a namespace
  collision, or a missing or rejected dependency); `validate_registry` and the `registry.py` CLI output are unchanged.
  `load_project` binds only usable profiles and reports `project.profile_rejected` for a bound one that did not load
  cleanly (`project.py` still lists every bound id); `project.resolve_context` returns decision `invalid` for a project
  with errors. Behaviour changes: `review_measurement_spec.py --profiles-from` now exits 2 when the project config has
  errors (it used to review with whatever loaded), and `communication_project.py` reports
  `resolution.project_config_invalid` as an error and binds no profile (it was a warning, with the profiles still
  used for ledgers and vocabulary).
- Namespace ownership at load time: each namespace has exactly one owner across the public registry, the project's
  local profiles and `--local` profiles; a second declaring profile gives `profile.namespace_collision` and neither
  is used (`compose.namespace_collision` stays as a second check).
- New `contracts/resolve.py` with the alias contract: owner, target, versions, rationale and retirement per alias;
  checks for a missing target, cross-owner takeover, ambiguity, cycles and aliases that would need a conversion; an
  in-memory canonical view where old and new keys merge only with equal values and a conflict is rejected with both
  sources (`alias.key_conflict`). No alias is declared yet, so nothing consumes it outside its tests; wiring it into
  the comparison gate's level identification waits for the first declared alias (D03b).
- New rule and obligation registry `contracts/rules/registry.json` (schema `contracts/schemas/rule_registry.json`,
  checker `contracts/rule_registry.py`; v6.3 D12a), run by `tools/run_all_checks.py` as the static check
  `rule_registry`. It registers the existing R4 rules of `contracts/recipe_semantics.py` with `outcome_contract:
  "pending"` (evaluated as unverified), the V01–V71 acceptance cases per slice part (all `not-run`), and an impact map
  from changed paths to test modules or gate parts. A new or changed rule needs reason codes for all five obligation
  states; a V case marked passing or expected-failure must name tests that exist. `impact` returns the full closure for
  a path no group covers, a group marked full, or a check that does not exist yet. No existing verdict or exit code
  changes.
- New `core/evidence/query.py` (v6.3 D02): bounded, pageable rows of a source and claim ledger, one per (claim, cited
  source), each with claim and source IDs, scope, `verification_date`, verification level and strength, location and
  the record position in each file. The ledger is checked with `core/evidence/ledger.py` first and a ledger with
  errors serves no rows (exit 1). Pages hold at most 20 rows and 16 KiB of JSON (product defaults, not measurements),
  report the total match count and an index digest, and give a cursor bound to that digest and the query: a cursor
  used after the ledger changed or with another query is refused (`query.stale_cursor`, `query.cursor_mismatch`,
  exit 2). A row larger than the cap is not cut; the page names the exact command that fetches it. Its CLI runs under
  the protected-mode guard like `ledger.py`. Measurements: `docs/dev/v6.3/m0-budget.md`.
- New optional adapter `adapters/cr-propagation` 0.1.0 (owner hep-computing, required by no skill; adapter status
  `proposed` because GALPROP and USINE are `proposed`). DRAGON2 is `tested-in-declared-environment`: commit cd588707 of
  cosmicrays/DRAGON2-Beta_version built from source on E2 (Homebrew GCC 15.2.0, GSL 2.8, CFITSIO 4.6.4; no system-wide
  installation). `dragon2_run.py` builds a run directory from a JSON run spec (XML, source.param, links to the data
  tables, an optional replacement production-cross-section table), runs DRAGON2 and records a `computational-run`
  (input hashes, program and commit, command, environment manifest, exit status, output hash); exit 3 without the
  binary or data. `dragon2_to_prediction.py` turns one run into one grid-node `prediction` (`representation: "grid"`,
  the node in `parameter_point`, a ratio of summed species averaged uniformly in ln(E/n) over the requested bins, no
  extrapolation) that the comparison gate and `covariance_fit.py` model `tabulated-grid` use unchanged.
- Limit benchmark of DRAGON2 against the 1D thin-disc closed form of `theory:cr-secondary-ratio` (convection,
  reacceleration, energy losses and decay off; the profile's illustrative production cross sections substituted through
  DRAGON2's data table), criteria committed before the comparison: the B/C slope over 100–1000 GeV/n agrees (0.006,
  tolerance 0.05), the absolute B/C agrees within the declared 30% (DRAGON2 9–12% higher, mostly its fixed helium
  target) and a five-node D0 grid of DRAGON2 runs recovers a sixth run's D0 within 2% through `tabulated-grid`; the D0/L
  degeneracy fails at L = 8 kpc (15–18%, tolerance 10%) because of the radial boundary at 20 kpc and the radial gas
  structure. Diagnostic runs with the boundary at 60 kpc and the gas made uniform in R (a local patch of DRAGON2,
  recorded with the runs) reach the closed form: within 2% between L = 2, 4 and 8 kpc and within 5% in absolute B/C
  once DRAGON2's helium production term is divided out. The tests replay fourteen recorded runs offline and assert what
  is established; a live rerun runs with `HEP_DRAGON2_LIVE_TEST=1`. Global propagation fits that run a code stay
  outside v1.
- `dragon2_to_prediction.py` multiplies each DRAGON2 column by its mass number A before forming a ratio: DRAGON2 writes
  its internal density per total kinetic energy (`GetFluxAtSunPosition` computes `weight = A` but does not apply it;
  the spallation source carries A_parent / A_daughter), so a ratio of species with different A was wrong (B/C 12/11
  too high, O/C 12/16 too low). The first version of the limit benchmark reported this as an unexplained 32–34% B/C
  excess (C1 failing); C1 now passes with its declared tolerance (plan amendment of 2026-10-16, a unit correction).
- Fix: `covariance_fit.py` model `tabulated-grid` no longer crashes when the best fit lies inside the first or last
  cell of a grid axis. The Fisher-matrix step was one cell, and where a full cell did not fit on one side it took a
  one-sided second-order difference two cells inward, which could leave the grid (`CovFitError` "outside the grid";
  found by WP13, where a three-node D0 grid of DRAGON2 runs with the truth in the upper cell could not be fitted).
  Steps are now cut at the grid edges: a three-point central difference with unequal steps inside the grid, and on
  an edge a one-sided step no longer than half the room left. Where a full cell fits on both sides the step is as
  before. New test `JacobianStepsStayInsideTheGrid` (four axes with the truth in an edge cell, uniform and
  non-uniform; the error on a parameter the model is linear in matches the 11-node fit within 2%) failed before the
  fix. Rerun of the WP13 three-node grid with the fix: D0 = 3.664e28 for a truth of 3.6e28 (|ln| = 0.018, error
  0.023), the same best fit as the five-node grid.
- New theory profile `theory:heliospheric-modulation` 0.1.0 (WP14): force-field solar modulation by reference to
  `skills/hep-measurement/scripts/solar_modulation_force_field.py`, which the profile runs as a separate process and
  does not reimplement (profiles may import only core and contracts). `scripts/derive.py` checks in SymPy that
  F(T + |Z| phi) solves the zero-streaming equation with a diffusion coefficient proportional to rigidity (the opposite
  sign does not), that T + |Z| phi is constant along the characteristic, the p^2 flux relation, the closed forms of a
  power-law local interstellar spectrum in total kinetic energy, kinetic energy per nucleon and rigidity, and their
  limits (`analytic-derivation`). `scripts/predict.py --benchmark` compares the script with those closed forms on 90
  synthetic points (two species, phi 0 to 1 GV, three energy kinds) to a relative 1e-10 (largest difference 2.4e-15),
  with phi = 0 and a demodulate round trip; `demonstrated-on-synthetic-data`, 25 profile tests. The validity range
  (breakdown below about 300 MeV/n for protons and 250 MeV/n for alpha particles) and the known limits (no rigidity-,
  time- or charge-sign-dependent effects; phi degenerate with the spectrum) cite Gleeson and Axford 1968, Ghelfi et al.
  2016 and Cholis et al. as read on 2026-10-13 for the hep-theory cosmic-ray reference. Convection-diffusion, drift and
  1D-3D numerical models and the neutron-monitor link are documented only, as unverified context; multi-period fits of
  phi point to `skills/hep-statistics/references/time-series-inference.md`. No source-term profiles (dark matter,
  pulsars). Registry: 2,264 of 3,072 bytes.
- `skills/hep-theory/references/cosmic-ray-propagation.md` no longer says the force-field script's rigidity and
  tabulated-spectrum inputs are planned (they shipped earlier), and names the new profile's role without its ID.
- `contracts/registry.py` rejects an unknown flag or a stray argument with exit 2 and a JSON error naming it
  (`{"ok": false, "error": "unknown option '--bogus' ..."}`). Before, an unknown flag such as validate.py's
  `--profiles-from` was ignored and the run reported `ok`, so a companion check with the wrong flag looked clean.
  `--registry`, `--local` (repeatable) and `--strict-versions` work as before; `--help` prints the usage.
- Test robustness: `test_tikz_error_is_a_source_error` (hep-communication diagram check) skips with the preflight's
  reason when a TeX engine is on PATH but the install fails the renderer preflight (for example a missing
  `luatex85.sty`, exit 3), as its no-TeX neighbour does; with a complete install it still asserts exit 1 and one
  source error. A stand-in engine covers the skip. No plugin code changed.
- `contracts/lineage.py decision` now compares each `artifacts[].sha256` with the file it names: relative refs resolve
  against the decision record's folder (or `--artifacts-root DIR`), absolute refs are used as they are. A different
  hash is `lineage.artifact_mismatch`, a missing file `lineage.artifact_missing`, an unreadable one
  `lineage.artifact_unreadable`, all errors (exit 1), as a missing exposure record is. `check_decision()` gains an
  optional `base_dir`; without it the library check is unchanged. No schema change. The hep-ml pre-training freeze
  example passes as shipped; a changed split manifest now fails `lineage.py` itself, and only the hash written in the
  `decision` text is still compared by hand (`ml-analysis.md`, capability matrix updated).
- Registry budget raised from 2,048 to 3,072 bytes (`REGISTRY_BUDGET` in `contracts/registry.py` and
  `registry_bytes` in `tools/measure_entrypoints.py`; decision D3 of the WP13–WP16 order). The registry was at 2,001
  bytes with 8 entries, and one more theory profile costs about 163 bytes plus its scope, so no further profile fit.
  The registry is read only when a profile is needed, so this does not change the always-on description cost. The
  tests now take the budget from `contracts/registry.py`, and a new test checks that the two constants agree.
- Routing: hep-computing's description says to load it first even for a quick build or code fix (`co-companion-ws-1`,
  a CMake fix in a project that binds a companion profile, now loads hep-computing in 3/3 live runs, was 1/3), and
  hep-communication's description says to ask first when a comparison names no observable or experiments (it was
  shortened to stay under 1024 characters; every trigger phrase the routing cases rely on is kept). The routing case
  `rc-t3-neg` ("is this Feynman diagram allowed at tree level?") now has a synthetic `diagram.tex` (a three-photon
  vertex) as its input: without it the model rightly asked for the diagram; with it hep-theory loads in 3/3 runs.
  `wp11-xexp-3` (an underspecified flux comparison) still loads hep-communication before asking, so the harness still
  counts it as a miss, but the model now asks for the observable and experiments straight away in 3/3 runs instead of
  exploring the tree until it ran out of turns (2/3 before). Live check on the 72 cases that involve either skill or
  ask for a question: 69/72, with the other two misses (`eic-underspec-1`, `t19-turns-3`) the same as in the
  2026-10-08 baseline.
- Test robustness: `test_scaling_check_rejects_a_quadratic_scan` (hep-communication manuscript scan) models the
  quadratic rescan as a Python loop over the earlier lines instead of `str.count` over the earlier text. On a CI runner
  the `str.count` byte rate grew with the text, giving a ratio of 7.4 instead of about 16 and a spurious failure (PR
  #108, job `optional (root-uproot)`; passed on rerun); the loop's cost per step is interpreter work, so the ratio
  stays near 16 (14.5–16.6 in five repeats each on an idle and on a loaded laptop). No plugin code changed.

## 0.11.0 (2026-10-15)

AMS-02 skill upgrade (work order WP1–WP12, WP15), four skills renamed, Python 3.13 as the minimum, and CI
improvements. **Contracts 2.9.0** (skill-name aliases). **Breaking for users:** the skills `hep-analysis`,
`detector-response`, `research-communication` and `physics-ml` are now `hep-measurement`, `hep-detector`,
`hep-communication` and `hep-ml` (old names in artifacts and profiles are accepted with a deprecation warning, an error
under `--strict-versions`; `contracts/migrate_skill_names.py` rewrites them), and Python 3.11 and 3.12 are no longer
supported. The companion ams02-research 1.5.0 follows the rename (it requires hep-research >=0.11.0).

- Skill READMEs brought up to date with the tree (no SKILL.md or capability change): hep-computing counts 32
  references and 13 test modules (PyROOT floor test), and `find_python.py` is described with its Python 3.13 floor;
  hep-statistics counts 20 test modules and names the `tabulated-grid` status (demonstrated on synthetic data), its
  exit 3 for a missing covariance or correlation, and `examples/bc-propagation-fit`; hep-theory lists the
  `bc-propagation-fit` example, the 3.13 interpreter floor and its out-of-v1 domains; hep-measurement counts its 12
  references and 21 test modules, lists all its assets and the link to the hep-statistics time-series reference;
  hep-detector states the charge-confusion note's `documented` status; hep-communication points at the behavioral
  evaluation's real folder (`evals/research_communication/`) and its two recorded live runs. The four renamed skills'
  READMEs say in one line which old name is a deprecated alias (contracts 2.9.0).
- `docs/reference-inventory.{json,md}` regenerated (the hep-measurement README now cites `time-series-inference.md`).

- `theory:cr-secondary-antiprotons`: external benchmark for open question B2. `scripts/published_benchmark.py`
  recomputes the pp-induced source term of di Mauro, Donato, Goudelis and Serpico, PRD 90 (2014) 085017
  (arXiv:1408.0288v3), Table VI, from the same paper's closed-form parametrizations (Eqs. (11)-(13), (B1)-(B2);
  Tables III-V, VII; `models/xs-dimauro2014-pp.json`, benchmark use only) and the proton flux of arXiv:1402.0321v2
  Sec. 2.3. Tolerance per entry is the paper's own Table VI error: 12 of 15 entries reproduced (within 2.5% at 5 and
  10 GeV); Eq. (11) at 1000 GeV and Eq. (13) at 500 and 1000 GeV (unstated projectile-energy upper limit), plus the
  spline, Tan & Ng and Duperray et al. columns, documented as not reproduced
  (`benchmarks/published-source-term-dimauro2014.json`). New capability `source-term-external-benchmark`
  (tested-in-declared-environment, E2); 12 new tests (48 in the profile).
- `theory:cr-secondary-antiprotons` evidence: di Mauro et al. 2014 read in full (title corrected), Korsmeier et al.
  2018 and Winkler 2017 opened for tables and ancillary files (no tabulated source term), new source `crpb:S05`
  (arXiv:1402.0321v2) and claims `crpb:C07`-`C11`.
- `theory:cr-secondary-ratio`: open question B1 stays open. Five papers examined on 2026-10-15 tabulate fit
  parameters or cross sections and show B/C in figures only; search record
  `benchmarks/external-benchmark-search.json`, absence claim `crsr:C06`, read levels updated, 4 new tests.
- `docs/capability-matrix.md` Profiles rows and `VALIDATION.md` (CR-BENCHMARKS-B1-B2) updated.

- `find_python.py`: `--min-python` bad usage is decided in `main()` before `find()` runs, so only the format and floor checks exit 2 and any other `ValueError` from `find()` propagates; the CLI error names `--min-python` (not `min_python`); `--min-python` must be dotted non-negative integers (`^[0-9]+(\.[0-9]+)*$`), so `3.13.-5`, `3_14`, `+3.14` and padded values are refused.
- `tools/run_all_checks.py` and `tools/check_ams_optional.py` stop at once with exit 2 and "Python 3.13 or newer is required (running X.Y)" on an older interpreter, instead of running into version-dependent test failures.
- CI: the weekly `latest` job (slow tier) sets `HEP_MODULE_TIMEOUT=1800`: `tests.examples.test_stats_benchmarks` takes about 525-545 s alone there, near the default 600 s limit (toys, seeds and tolerances unchanged); documented in `docs/maintenance.md`.

- `test_scan_time_is_linear_in_lines` measures CPU time (minimum of three, garbage collector off) and bounds the 10k -> 40k line scaling ratio (limit 10; linear about 4, quadratic about 16) with a generous absolute ceiling; it no longer fails on a loaded machine, and a synthetic quadratic scan is shown to fail the same check.
- New `tests/tools/test_python_compat.py`: `core/partition/runner.py`, `find_python.py` and the two suite runners parse as Python 3.9, the `PROBE` string as 3.7 (`ast.parse` feature_version plus PEP 701 f-string, starred-subscript and `datetime.UTC` checks); a real old interpreter compiles them when present.
- The old-floor check now covers `docs/deployment-model.md` and the current statements of `docs/capability-matrix.md`; the matrix's dated E1/E3 environment lines, floor note and E3 ROOT row are excluded by name and must still exist.
- `test_stricter_minimum_is_kept` checks the rejection reason with a fake 3.13 interpreter on any runner (it asserted nothing on 3.14+).
- Long lines wrapped in `find_python.py` and the floor tests; the `test_broken_power_law` tolerance comment describes 3.11 as history.

- Routing: hep-communication's "Not for" clause says "even with published data" and names CRDB queries (hep-theory) and compatibility results (hep-statistics), so requests that name experiments but ask for a result go to the owner; live (2026-10-15): `wp11-crdb-1` 3/3, `wp11-xexp-2` 2/3 (both 0/1 before), all 25 hep-communication cases still pass; `wp11-bound-dm-1` (dark-matter interpretation) also accepts hep-communication. Known misses: `wp11-xexp-3` (underspecified comparison loads hep-communication instead of asking), `rc-t3-neg`, `co-companion-ws-1` (no skill).

- **Four skills renamed** (rename release 0.11.0; contracts 2.9.0). Skill folders, `SKILL.md` `name` fields, test
  folders (`tests/skills/<underscored>`), descriptions' "Not for" lists, handoff tables, READMEs, profiles'
  `related_skills`, the capability matrix, routing cases and docs use the new names:

  | Old name | New name | Test folder |
  | --- | --- | --- |
  | `hep-analysis` | `hep-measurement` | `tests/skills/hep_measurement` |
  | `detector-response` | `hep-detector` | `tests/skills/hep_detector` |
  | `research-communication` | `hep-communication` | `tests/skills/hep_communication` |
  | `physics-ml` | `hep-ml` | `tests/skills/hep_ml` |

  `hep-statistics`, `hep-theory` and `hep-computing` are unchanged. Files named after a skill follow the same rule:
  `references/hep-measurement-guide.md` (was `hep-analysis-guide.md`), `assets/diagrams/hep-measurement-pipeline.md`,
  `tests/skills/hep_detector/test_hep_detector_audit.py`, `tests/skills/hep_ml/test_hep_ml_skill.py`. Release
  manifests, past CHANGELOG entries, dated VALIDATION.md sections and past eval results keep the old names.
- **Contracts 2.9.0: deprecated skill-name aliases.** `contracts/schemas/skill_names.json` (referenced by
  `envelope.json` `provenance.producer_skill` and `profile.json` `related_skills`) and `contracts/skill_names.py`
  accept the seven names plus the four old names as deprecated aliases. An old name in `provenance.producer_skill`,
  `handoff.to_skill` or an extension `handoff` is the warning `skill.deprecated_name`; in a profile's
  `related_skills`, `profile.deprecated_skill_name`. Under the version and name policy (`--strict-versions` of
  `contracts/validate.py`, `contracts/dependencies.py` and, new, `contracts/registry.py`; and protected use) each is
  an error. A 2.8 reader rejects a new name (schema enum) instead of misreading it; no capability is added. The
  aliases are removed one or two releases later.
- **`contracts/migrate_skill_names.py OLD.json [--out NEW.json]`** rewrites `provenance.producer_skill` and
  `handoff.to_skill` to the new names and nothing else (not `contract_version`, not the extension); remaining
  findings are reported, never repaired. Exit 0 migrated or unchanged, 2 unreadable or not an object. Fixture
  `contracts/fixtures/skill_aliases/response_old_skill_names.json`; tests
  `tests/contracts/test_skill_name_aliases.py` (old name warns, fails under `--strict-versions`, validates cleanly
  after migration; registry warning and strict error for `related_skills`).
- Contract fixtures, example outputs (contracts version and producer names) and the gate-verdict snapshot
  regenerated; `docs/maintenance.md` documents the name policy. ams02-research 1.5.0 requires `hep-research
  >=0.11.0` and names the new skills in its profile.

- **Python 3.13 is the minimum** (validation-first migration; Gate 1 evidence in VALIDATION PY313-FLOOR): `requires-python = ">=3.13"`, Ruff `py313`, mypy `3.13`; `skills/hep-computing/scripts/find_python.py` selects only Python 3.13 or newer (default and lowest allowed `--min-python` 3.13: a lower value is bad usage, exit 2; `find()` raises `ValueError`), with 3.11/3.12 rejection, fallback and all-old tests. CI's checks matrix runs on Python 3.13 only (4 jobs instead of 12; the backend jobs already ran on 3.13 and are unchanged), and `checks-complete` reconciles 3.13 only. **Migration:** Python 3.11 and 3.12 are no longer supported or tested; create the environment with Python 3.13 (`python3.13 -m venv ...`, then `pip install -r requirements-core.txt`) and point `HEP_RESEARCH_PYTHON` at it. Scripts run directly are not stopped by `requires-python`; the skills choose the interpreter with `find_python.py`. Python 3.14 is installable but not tested. Dependency pins are unchanged (the 3.11-era upper bounds in `requirements-ci-constraints.txt` stay until a separate dependency change).
- Capability statements for cosmic-ray propagation rewritten to the achieved status (WP10): guidance, the two narrow theory-domain profiles, the `tabulated-grid` fit and `examples/bc-propagation-fit` are demonstrated on synthetic data; only global fits that run a propagation code stay outside v1 (capability matrix, `cosmic-ray-propagation.md`, hep-theory README). The hep-statistics description's out-of-v1 example is now "global propagation fits" (1,016 characters) and the shared context-resolution stanza says "global cosmic-ray propagation fits" in all seven SKILL.md files; the four WP11 propagation-fit routing cases are direct cases now (static routing passes).

- Profile `theory:cr-secondary-antiprotons` 0.1.0: the secondary antiproton source term q(T_pbar) for the channels
  pp, pHe, Hep and HeHe with the antineutron and hyperon factor (2 + Delta_IS + 2 Delta_Lambda), following the
  hep-theory cosmic-ray reference conventions. TOY x-scaling cross sections with ILLUSTRATIVE values (no published
  parametrization reproduced); the closed-form source integral (incomplete beta functions, checked in SymPy) is the
  internal benchmark of the numerical quadrature (agreement 3e-15, criterion 1e-8). `model.family` is
  `cosmic-ray-secondary-source-term`, so `theory.degeneracy_missing` does not apply. 36 profile tests, capabilities at
  `demonstrated-on-synthetic-data`. Published source-term values as a benchmark remain open (B2). Registry 2,001 bytes.
- Example `examples/bc-propagation-fit/`: a 21 x 21 log-spaced (D0, L) grid of `theory:cr-secondary-ratio`
  predictions (882 gated artifacts, two illustrative cross-section sets), SYNTHETIC B/C points with a full covariance,
  and `covariance_fit.py` `tabulated-grid`: D0/L recovered (Asimov within 0.25 sigma, pseudo-data pull -0.41, 100 toys
  with pull mean 0.02 and width 0.95), D0 and L unconstrained, one degenerate direction along (1, 1) matched to the
  theory spec's `D0/L`, cross sections as a model set; ungated, rigidity-binned, unfolded-level and
  unknown-correlation inputs refused. Test `tests/examples/test_bc_propagation_fit.py`.

- `adapters/crdb` 0.1.0 (owner hep-theory, optional, `tested-in-declared-environment` on E2 with CRDB V4.2): one query of the CRDB (LPSC) REST interface, promoted from the ams-02 profile's `scripts/crdb_query.py`. No default experiment filter (`url`/`fetch` without `--exp-dates` or `--all-experiments` exit 2); every summarized row and sub-experiment group carries `secondary: true`; the `.meta.json` sidecar holds the request (parameters, URL, User-Agent), UTC retrieval time, CRDB version, export date and the SHA-256 of the saved file. HEPData or the paper's tables are primary; a CRDB value is a cross-check or a fallback labelled secondary. Offline tests replay four CRDB exports recorded live on 2026-10-15 (`tests/adapters/test_crdb_query.py`, VALIDATION CRDB-ADAPTER).

- ams-02 profile: `scripts/crdb_query.py` and `tests/test_crdb_query.py` removed; the profile lists `adapter:crdb` as optional and its cross-check step passes `--exp-dates AMS` explicitly; capability `papers-manifest-and-crdb-query` renamed `papers-manifest`. `cosmic-ray-databases.md` records that `exp_dates=AMS` also returned an AMS01 row (2026-10-15). Rules and claims C125-C129 unchanged.

# WP3 changelog bullets (for "Unreleased")

- Profile `theory:cr-secondary-ratio` 0.1.0, the first narrow cosmic-ray propagation domain: B/C (from C and O) in a
  weighted-slab (leaky-box) model and a 1D thin-disc diffusion model without convection. SymPy checks of the closed
  forms, of their equivalence through lambda_esc = n_H m_H h v L / D and of the resulting D0/L invariance
  (`scripts/derive.py`); a benchmark of the closed forms against the profile's own numerical solutions (slab ODEs
  averaged over the path-length distribution, a finite-thickness disc solved exactly and by finite volumes, and its
  thin-disc limit; `scripts/predict.py --benchmark`); a theory-spec artifact with `model.family`
  `cosmic-ray-propagation` and `degenerate_directions: ["D0/L"]`; a bin-averaged prediction artifact with a
  cross-section model alternative; and a prediction callable at any parameter point and on (D0, L) grids
  (`predict.evaluate`, `predict.grid`, `predict.bin_averaged`, CLI `--set` / `--grid`) for the grid fit of WP1/WP8.
  Cross sections and transport values are ILLUSTRATIVE; references are cited but were not opened (no network).
  Status `demonstrated-on-synthetic-data`, 37 profile tests, including one showing that a theory-spec without
  `degenerate_directions` fails `contracts/validate.py` with `theory.degeneracy_missing`.
- Capability matrix: a "Profiles" row for `theory:cr-secondary-ratio`.

- `examples/eic-profile-routing/output/` regenerated: the run lists every registered `profile.json` it opens, which now
  includes the new profile.

- CI: a new commit on a pull request cancels that PR's superseded `tests` run (pushes to main, the weekly and manual runs are never cancelled); pip downloads are cached by `setup-python`, keyed on `requirements-ci.lock` (installs and tests still run in full every time). Batch 2 (low-risk part) of the CI improvement proposal.

- hep-statistics: `covariance_fit.py fit` model `tabulated-grid`: fits grid parameters (for example D0 and L) to a
  `dataset-record` from one `prediction` artifact per grid node (`representation: "grid"`, node in `parameter_point`;
  no schema change). Every prediction passes `contracts/comparison/gate.py` first (ungated or not comparable: exit 1);
  multilinear interpolation in the fit coordinates (`scale: "log"` or `"linear"`), no extrapolation (a start outside
  the grid or a minimum beyond its edge is refused); cross-section uncertainty as a rank-one normalization nuisance
  (`multiplicative`, mode `nuisance`) and/or alternative sets through `model_set()` and `envelope()`, the mode recorded
  in `cross_section_uncertainty.mode`; degenerate directions from the Fisher matrix reported with eigenvector and
  condition number and compared with the theory spec's `degenerate_directions` (mismatch: warning); `combinations`
  such as `D0/L` reported with `sigma_ln`. Tests: `tests/skills/hep_statistics/test_grid_fit.py` (synthetic only).
  Status: demonstrated on synthetic data (E2, 2026-10-15).
- `covariance_fit.py`: exit code 3 (`"status": "incomplete"`, `missing`) when a data covariance or an uncertainty
  correlation is missing; a diagonal matrix is never assumed.

- `covariance_fit.py`: a field of the wrong JSON type now gives exit 2 with a JSON error instead of a traceback.

- CI (batch 1 of the CI improvement proposal, test obligations unchanged): `tools/run_all_checks.py` records seconds for every check, prints failed test ids with their traceback tails (profile suites and `check_ams_optional` included) and writes a Markdown job summary with `--summary FILE`; `--part static` and `--part ams-optional` split `--part checks` so the AMS-optionality check (about 75 % of the old "static and profiles" job) runs as its own CI job. Each units run records its plan (full module list with SHA-256, the shard's modules, the timings digest).
- CI: new `tools/reconcile_check_runs.py` and required-in-practice `checks-complete` job: every expected checks run (Python 3.11-3.13 × units 1/2, 2/2, static, ams-optional) present once, of the tested commit, passing, with only the host CLI checks skipped, every planned check reported, and the shards partitioning this tree's module list (planned from the same timings); runs after failures (`always()`), and a missing record fails it. Fault-injection tests in `tests/tools/test_reconcile_check_runs.py`. Its first local run caught shards planned from two different timing files (a module in two shards, others in none) at equal test counts.
- `tools/module_timings.json` refreshed from GitHub Actions run 38680162693 (median of the 6 units-shard samples per module; 53 modules had no record, `test_stats_statistical_toys` was recorded at 70 s and now takes 177 s): the planned 2-shard split of the measured time goes from 1028 s / 845 s to 937 s / 937 s.

- `adapters/literature-lookup` 0.1.0 (optional, owned by hep-communication, standard library only): `literature_lookup.py` looks up an arXiv id (with or without version), DOI, INSPIRE record id or ADS bibcode in INSPIRE-HEP, arXiv and ADS and prints one record per source with source URL, UTC retrieval time, read level and an arXiv version check; HTTP 429 reported as `rate-limited` and never retried; ADS token from `ADS_API_TOKEN`/`ADS_TOKEN`, never printed or recorded, `not-verified` without it; `--replay`/`--record` for recorded responses. Exit 0 found, 1 not found, 2 bad input, 3 incomplete. Status `demonstrated-on-synthetic-data` (INSPIRE-HEP and arXiv `tested-in-declared-environment`, ADS on a constructed response only).
- `tests/adapters/test_literature_lookup.py` with fixtures recorded from INSPIRE-HEP and arXiv on 2026-10-15 (found, not found, HTTP 404, a real arXiv HTTP 429, version mismatch) and constructed INSPIRE 429 and ADS responses; offline (urlopen patched to fail); live smoke only with `HEP_LIVE_LOOKUP_TEST=1`.

- Capability matrix: "Literature and citation verification online" raised from `unverified` to `tested-in-declared-environment` for INSPIRE-HEP and arXiv (E2, live 2026-10-15), ADS `demonstrated-on-synthetic-data`; new Adapters row. VALIDATION LITERATURE-LOOKUP.
- `literature-lookup-recipes.md`: optional lookup-client section; arXiv answered HTTP 429 to a nonexistent id (observed 2026-10-15). hep-communication README and `docs/adapter-authoring.md` (network declaration) updated.

- Routing: 27 new cases (set `WP11`, 13 en / 14 zh-Hant) in `tests/routing/make_cases.py` for cosmic-ray interpretation, propagation fits (hep-statistics, limited support until WP10), time-series inference, cross-experiment comparison, CRDB queries, a custom e/p classifier in a measurement (hep-ml, handoff to hep-measurement), and the dark-matter-interpretation (hep-theory, limited support) and latest-B/C-paper (hep-communication) boundaries; `cases.json` regenerated (241 cases). The live harness in `evals/routing/` reads the same `cases.json`, so it picks them up unchanged.

- `skills/hep-statistics/references/time-series-inference.md` (documented): inference on **binned** time series:
  time-bin covariance as statistical + fully correlated time-independent + time-dependent blocks (valid exponential or
  epoch correlations, positive-definiteness, correlation-time limits, no averaging down, cancellation in ratios,
  rigidity x time Kronecker structure, Peelle); periodicity against an AR(1) red-noise null fitted with the measurement
  covariance and why Rayleigh/Z_m^2 (event-level, white noise) do not apply; trials across periods and energy bins by
  toys of the complete procedure (pattern of `look_elsewhere.py` and `global_significance.py`, which are not periodogram
  tools; the shipped Gross-Vitells bound is one degree of freedom); joint multi-period fits with one modulation
  parameter per period, shared parameters and nuisances for time-independent sources via `covariance_fit.py` plug-in.
  Linked from `SKILL.md` Resources, the core-stats-guide reference index and `astroparticle-statistics.md`.
- `tests/skills/hep_statistics/test_time_series_covariance.py`: the covariance recipe on a synthetic series
  (demonstrated-on-synthetic-data); a nearest-neighbour correlation of 0.7 is refused by `validate_covariance.py` as
  not PSD.

- hep-measurement: `references/cosmic-ray-measurements.md`, an index of cosmic-ray measurement types (absolute flux, flux ratios, isotope ratios, time-dependent flux, rare-event searches) that links existing sections in hep-measurement, hep-detector, hep-statistics and hep-communication, plus new anisotropy measurement design: estimand (first harmonic, equatorial dipole projection, 3D dipole), directional exposure and its non-uniformity (simulated vs data-driven, east-west method), harmonic and full-sky dipole estimators, partial-sky multipole coupling, amplitude bias, solar/sidereal/anti-sidereal checks, and upper limits on the amplitude with the limit construction handed to hep-statistics (Linsley 1975, Sommers 2001, Billoir & Deligny 2008, Ahlers & Mertsch 2017, Compton & Getting 1935, Farley & Storey 1954, Alexandreas et al. 1993, Bonino et al. 2011). Linked from `SKILL.md` Resources and the analysis guide's routing table; capability matrix row `documented`.

- hep-detector: `references/charge-confusion.md`, a synthesis note on charge-sign confusion: the mechanisms (finite curvature resolution toward the maximum detectable rigidity, non-Gaussian scattering and interactions, wrong hit association; alignment weak modes making the two signs' rates differ), how hep-detector measures the rate (simulation validated on data, templates in a confusion-sensitive variable, known-sign control samples) and the handoff to hep-measurement, which subtracts it as a background; linked from the principles-summary reference index and task-routing table and from the tracking reference. Capability-matrix row at `documented` (WP15).

- hep-ml: pre-training freeze procedure in `references/ml-analysis.md` ("Training on data and blinding"): before training, a `decision_record` (category `other`) states labels, features, training domain and the split manifest's file SHA-256, lists the manifest in `artifacts`, and binds `seen` to the analysis's exposure record; checked with `contracts/lineage.py decision`, plus a manual file-hash comparison since `lineage.py` does not open artifacts (WP7).
- hep-ml: synthetic example `assets/pretraining-decision.example.json` with `pretraining-exposure.example.json` and `pretraining-split.example.json`; `tests/skills/hep_ml/test_pretraining_freeze.py` checks it (lineage exit 0, exposure at decision `unexposed`) and shows that an edited exposure history, an understated `seen`, a decision dated before what it counts, a changed split manifest and a hash that disagrees between `artifacts` and the text fail (WP7).

- WP6: hep-communication quick-question routing re-measured live on 0.10.1 (routing 29/31, hep-communication 20/20; communication eval 5 of 11 cases still answered without a skill, a description-level decision); `SKILL.md` unchanged; recorded in VALIDATION (WP6-QUICK-ROUTING) and capability matrix.

## 0.10.1 (2026-10-15)

Follow-ups to the 0.10.0 check (PR #84) and the `run_all_checks.py` timeout fix (PR #83). ams02-research needs no
change (it requires hep-research >=0.4.0 and contracts >=2.0). Contracts stay 2.8.0.

- `tools/run_all_checks.py`: a check script that does not finish within the timeout (`--module-timeout`, default 600 s,
  now applied to the check scripts as well as the test modules) is a failure with the reason "timed out after N s";
  the remaining checks still run. Before, the uncaught timeout aborted the whole run with a traceback (seen in the
  0.10.0 release gate when two runs shared the CPU and `ams_optional` passed 600 s).

Follow-ups to the check of the three audit orders on 0.10.0 (every rerun item verified, no regressions; the open
items below were fixed, sources opened 2026-10-15).

- detector-response: tool contract for `frontend_response.py` (`contracts/tool_contracts/frontend_response.json`, ten
  operations checked against each subcommand's `--help`; exits 1 and 2 print JSON); its top-level usage is one line so
  the checker sees every subcommand. Tests: `FrontendResponseContractTests`.
- detector-response references, from PDG RPP 2025 reviews 34-36, NIST PSTAR, the Geant4 manuals and the arXiv papers
  named in the text: noble-liquid W values and pulse shapes; Gluckstern validity (N >= 10) and the `beta` power of the
  scattering term (PDG eq. 35.70, unchanged); silicon response; Lindhard quenching; transition radiation; stopping-power
  corrections; Polya gain; resistive induction; SiPM and APD noise; LGAD timing (15-20 ps); compensation and
  containment; Geant4 production cuts; prescale handling; luminosity uncertainty; tracker weak modes; Hillas
  parameters; CTAO LST status; neutrino telescopes; new notes on muon detectors, radio detection and wide-field
  gamma-ray arrays (HAWC, LHAASO-KM2A); a `Check:` line per section in the triggers, physics-objects and
  event-reconstruction references. Rows still without an openable source stay deferred in VALIDATION.
- hep-analysis `geomagnetic_cutoff.py`: the default dipole moment 8.05e25 G cm^3 is stated once as the IGRF-14 1955
  dipole (C = 59.6 GV); the 2025 dipole is 7.69e25 G cm^3 (cutoffs about 4.5% lower). Default and outputs unchanged.
  Test: `GeomagneticDipoleDefaultTests`.
- Contracts: committed fixtures for the 2.8.0 ml-artifact rules (53 files, `ml_v28_*`, `statres_v28_*`) and a test
  that every 2.8.0 ML code has one; `gate_verdicts.json` gains rows, no verdict changed. No contract version change.
- physics-ml: regression tests for `anomaly_validation`, `reweighting_validation` and the temperature-at-bound warning.
- research-communication: the Springer Nature AI-use row states what the public policy page says (an "AI Declaration"
  in the manuscript, disclosure in captions for AI visuals; AI not an author); the ADS `citations()`/`references()`
  operators are stated from the ADS help source instead of marked unverified.
- VALIDATION: detector-response deferred list updated (and the work order's "FWHM" 6271594.24 is the falling
  half-maximum depth; FWHM is 2358463.01); physics-ml references size 179,135 B.

## 0.10.0 (2026-10-14)

The detector-response, physics-ml and research-communication audits (PR #81). ams02-research needs no change
(it requires hep-research >=0.4.0 and contracts >=2.0).

Contracts 2.8.0 (minor: new rule families refuse false or incomplete declarations; new fields optional; no new
capability; artifacts before 2.8.0 keep their default outcome and get the new rules under `--strict` and at the gate).
Research-communication adds one value to 2.8.0: `reporting_context.result_type` accepts `flux-measurement`
(`ext_communication_traceability.json`; add-only, RC-C3).

### research-communication (RC-AUDIT-2)

- **A displayed number that disagrees with its passage fails (RC-A2, sci-fix).** `check_communication` and
  `audit_claims` compared a declared display value with its passage as a substring warning, so `1.0` passed inside
  `1.02` and a record of 1.09 against a manuscript of 1.02 exited 0. One number tokenizer
  (`communication_lib/numbers.py`: sign, exponent, grouping, `\pm`/`±`, LaTeX and Unicode forms, CJK adjacency)
  now compares numbers as `Decimal`; absence is the error `occurrence.value_not_in_passage`.
- **Adaptation drafts read numbers at a sentence end and next to Chinese text (RC-A3, sci-fix).** A 9.99 draft
  against a 1.02 record passed `check_adaptation` in English (full stop) and Traditional Chinese.
- **Every display is checked against its source (RC-A5, RC-A15, sci-fix).** Without a rounding rule a display that
  is no rounding of the source is `occurrence.value_mismatch` (it was a warning); a malformed rule, NaN or infinity
  is a record finding (exit 1), not an input error.
- **Rounding rules round half up (RC-A6, sci-fix).** `decimals:2` turns 1.025 into 1.03; `:half-even` keeps the old
  mode. Skill library only; no contracts change. The worked example's audit report shows policy version 1.1.0.
- **`check_manuscript.py` reads LaTeX and BibTeX as TeX does (RC-A1, A4, A7, A9, A18).** Brace-less `\input name`
  is followed; `\Citet`/`\Cite`, multicite groups, nested optional arguments, `%` inside `\url`, entries inside
  `.bib` fields or `@comment`, `\iffalse`, the comment environment, `\verb` and crossref parents are handled; a
  `--bbl` outside the project root is an input error; scans are linear (20,000 lines: 10 s to under 0.2 s);
  `--strict` unused entries are unresolved while coverage is incomplete.
- **Locators and normalisation (RC-A8).** Section titles with nested braces, `\pm`/`±`/math shifts/ties on both
  sides, no headings inside fenced code.
- **Traditional Chinese parity (RC-A10, A13, A17).** Status-promotion, discovery, scope, negation and attribution
  scans, symbol and abbreviation definitions work in Traditional Chinese; status labels match as words; a
  disallowed term inside a declared term is not flagged; an abbreviation used before its definition on the same
  line is.
- **`check_diagram_sources.py` compiles TikZ (RC-A11).** LuaLaTeX (else pdfLaTeX), standalone harness with
  tikz-feynman and the file's setup fences, `--no-tikz`, a skip directive for fragments; a named file without a
  block exits 2. The bundle test compiles TikZ only under `HEP_SLOW_TESTS=1`.
- **Smaller checker fixes (RC-A12, A14, A16, A19).** Revision impact flags empty records and unmapped added claims;
  `--today notadate` and an output aliasing the input are refused; the README says which tool prints what.
- **Text facts (RC-B1-B13).** SKILL.md quotes the read-level vocabulary and names `user-supplied`; one rule for
  values read off plots; deduplication on DOI, arXiv id, INSPIRE record id; correction labels follow the venue;
  PRL Comment length from the APS page; dated AMS-02 specifics removed from references (one sourced absence claim,
  `ams02:C185`, added to the public profile ledger instead); diagram logic (result from the fit, vertex checks,
  pileup stage); compile records and the LuaTeX warning; smaller wording fixes.
- **Usability (RC-D1-D7).** A quick-questions block in SKILL.md and a trigger-first description (978 characters): the
  quick literature questions and citations come first, with the instruction to load the skill even for a quick
  question; every trigger phrase the routing cases use is kept (SKILL.md 8126 B). One home per rule (significance and limit wording, venue facts, posters and talks, captions,
  colour and raster); the papers guide cut to routing, rules and pointers; executable checks instead of
  "mentally desaturate"; a "Done when" line in every reference; reference link test.
- **New content (RC-C1-C11).** `physics-plots.md` (status labels on figures, ratio panels, `pdf.fonttype = 42`,
  colour and raster, cosmic-ray flux and neutrino figures), examples `hep/09`-`hep/11`, limit and null wording,
  the `flux-measurement` reporting policy, `collaboration-results-lifecycle.md`, AI-use disclosure raised
  unprompted with a dated venue table, HEPData records, `literature-lookup-recipes.md` (INSPIRE, ADS, arXiv),
  NSTC/ERC/JSPS and bilingual proposal rules, retraction and SCOAP3 licence checks, combination papers, poster and
  talk formats.
- **Records (RC-E1, E3).** The capability matrix records the live run of 2026-10-13 and where the evaluation files
  live; reference counts updated.

### physics-ml audit (ML-…)

Scientific corrections first (`sci-fix` commits; each with a regression test that failed on 84202aa).

- **Split tools check what they claim (ML-C02, C03, C04, C05, C14, C16, C28).** `check_split_integrity.py` refuses
  (exit 2) a timestamp that is not a finite number or an ISO-8601 date (NaN, `2024-1-10`), a `temporal_order` naming a
  split the file does not have or fewer than two, booleans, lists or objects as keys, and a misspelled reserved key;
  an empty split is `incomplete` under `--strict`; `timestamps_checked` is true only when the comparison ran. One key
  function for both split tools: 1, 1.0, "1" are one group. `make_grouped_splits.py --mode temporal` no longer sorts
  dates as text; `--label-column` reports class counts and refuses a split without a class. `train_classifier.py`
  matches case-folded manifests and reports a split without a class as exit 2.
- **A calibration evaluated on its fit sample never validates (ML-C01, K03, C13).** `calibration.py` records both
  sha256 values inside the calibration block and needs `--id-col` (or `--no-id-check`, recorded); from 2.8.0
  `disjoint: false`, equal hashes or names equal after normalization are `ml.calibration_on_fit_sample`.
- **Domain-shift outcome (ML-K05).** `domain_shift.outcome` (no-shift, corrected, bounded-by-nuisance, uncorrected) and
  `nuisance`; a missing status or outcome, an uncorrected shift without a nuisance and a control sample equal to the
  training sample are unresolved. J9 carries its measured pt_miss scale as the fit nuisance `theta_pt_miss_scale`:
  mu 1.30738 +0.280857/-0.260727 -> 1.33104 +0.293293/-0.277051, toy coverage 0.693 -> 0.660 (criterion 0.635-0.73).
- **One training-domain method (ML-C08, C09, C19, C18).** `check_surrogate_domain.py`'s method is the importable
  `DomainModel` (grouped held-out calibration, categorical features, Clopper-Pearson interval on the false-positive
  rate); `train_classifier.py` stores it fitted on train only and `inference.py` applies it (a broken linear
  constraint is flagged, the per-feature range is a diagnostic, non-finite rows get no score, `--calibration`).
- **Negative weights are never dropped; the metric layer flags or refuses (ML-R06, C11, C12, C15, C20, C21, C22).**
  `--negative-weights {signed, abs, resample}` (cell resampling, Andersen & Maier, arXiv:2109.07851, eq. 2.2);
  signed-weight values outside [0, 1] are flagged, fractional labels refused, `asimov_significance` refuses bad
  sigma_b and keeps its precision at s/b < 1e-6, `undo_prior_shift` refuses r <= 0, temperature-scaling warnings,
  `disco_penalty(check_weights=True)` by default.
- **Physics references (ML-R01-R05, R12, R13, R17, R21, R25; WP2.2/2.3).** Regression prior dependence and the in-situ
  scale and resolution systematic; when an ML uncertainty is a measurement systematic; Platt, isotonic, prior
  correction, conformal; blinding when training on data; validating inputs before training; negative weights by
  library; OmniFold unmatched events and prior dependence; ANODE; flows and flow matching; two-sample tests with power;
  SBI sharpness and overconfidence; GNN tracking; label noise from truth matching; four contradictions resolved.
  Sources opened on 2026-10-14 or marked `unverified`.
- **Small corrections (ML-C10, C24, C25, C26, K13).** `compare_model_runs.py` decides with a Student-t interval below
  10 seeds (false-improvement rate about 5%, was 26%/15%/11% at 3/5/10 seeds); the sculpting baseline is a quantile of
  20 resamplings; a constant training feature is exit 2; `model_hash` covers the weights only; the J9 test compares
  the committed artifacts within a relative 1e-7 (the calibration fit differs by 2-6e-9 between Linux and macOS BLAS;
  digests over float bytes are skipped). Check runs now keep the traceback tail of each failing test.

Contract and tooling:

- **ml-artifact semantics v2 (ML_SEMANTICS_V2_FROM = 2.8.0; ML-K02, K04, K07-K12, K14, K16).** Structured
  downstream validation (vocabulary `ml_downstream_metrics`; ML-only or bare-pass lists are errors; `passed` must
  agree with a numeric value and criterion); `output_semantics` required for classification, inference and
  regression (unresolved); misspelled keys are errors (`_key_checks` takes a `kind`); task blocks
  (`regression_validation`, `generative_validation`, `sbi_validation`, `extrapolation_policy`,
  `reweighting_validation`, `anomaly_validation`; new task `reweighting`; `parameters` and `supervision`); training
  domain coverage, `model_hash` format, label/feature/preprocessing/threshold/unit checks; `observed` and
  `validated-in-scope` need support; structured weights with `training` and `evaluation`; calibration outcomes.
  The Appendix B mutation probe (`tests/contracts/test_ml_mutation_probe.py`) goes from 50 of 53 rows silent on
  84202aa to 1 (M47, by design).
- **ML provenance at the publication gate (ML-K01, K06).** Optional `extension.observable_source` in the
  statistical-result schema (hep-statistics); the gate resolves, hashes and strictly validates every ml-artifact
  input (`gate.ml_input_*`); `dependencies.py` propagates unresolved findings (`dependency.source_unresolved`);
  `write_ml_artifact.py` records tool outputs in `extension.source_files`, not `inputs`. `dependencies.py` on J9: exit
  1 -> 0.
- **Writer does not trust self-reports (ML-C06, K11, C07).** The split verdict is recomputed from the report body; the
  test split is the manifest's `roles.test`; a pass without a report is not-run; no status label is exit 2.
- **CLI contract (ML-C17).** Invalid input exit 2 without traceback, missing PyTorch exit 3, `--status` echoed as
  `status_label` on the data-report scripts.
- **Routing, handoffs, size (ML-R19, K15, R20, R35).** 17 routing cases (en and zh-Hant) for task types without one; a
  Task routes index in `ml-analysis.md`; handoff tests for hep-theory, hep-analysis, detector-response, hep-computing
  and research-communication; references 257 KB -> 179 KB (nothing moved to hep-computing: it already had the
  authoring rules). Live routing: pending.

- **Batch commands refused in protected mode (HC-10, HC-16; review of deferred task P6.2).** In a project whose
  config carries `agent_policy`, `core/partition/campaign.py` refuses a real `submit`, `resubmit` or `cancel` and
  `confirm`, `abandon`, `reset` and `clear-orphans` in any form with `protected.batch_needs_trusted_submitter`, before
  any scheduler call. Before, a protected project with valid inputs could submit in-process as in S0 (jobs failed on
  the workers, where the copied runner refuses, but the submission itself ran). `abandon`, `reset`, `cancel` and
  `clear-orphans` also check the protected inputs now. Dry runs, `plan`, `freeze`, `status`, `watch`, `reconcile`,
  `merge` and `report` are unchanged; outside protected mode nothing changes. The switch is protected mode (DP-2), not
  the campaign config; `docs/agentic-architecture.md` §10.2 now says the same for the trusted submitter. Tests:
  `tests/core/test_partition_protected_batch.py`; the bypass suite lists these entry points and declares
  `REFUSED_IN_CONTROL` for consumers such as the deployment's live C07 check.
- **Protected-input source checks: sticky directories documented as refused for the running account.**
  `core/protected/trusted_input.py` refused a protected input below a world-writable sticky directory
  (`/tmp`, the macOS shared folder) for the running account, because its `os.access` check ignores the sticky bit, while
  its docstring promised the sticky exception. The behavior stays (an ACL can grant a deletion the mode bits do
  not show); the docstring now says so. Found by the deployment's live C07 run (release volume under
  the shared folder), which moved its mount point instead. Documentation only.
- **Decision recorded: no capability IDs for permits and analysis-level bundles (task P3.4).** `core:formal-use-permit`
  and `core:analysis-bundle` are not added to `KNOWN_CAPABILITIES`: permits and bundles are sidecars read as protected
  inputs and verified by `contracts/permit.py` and `contracts/analysis_bundle.py`, and no artifact declares a dependency
  on them. Stated in `docs/agentic-architecture.md` §9.3 and at `KNOWN_CAPABILITIES`. Documentation only; contracts
  2.7.0 unchanged.
- **Architecture and deployment documents brought to 0.9.0.** `docs/agentic-architecture.md`: status line names the
  release; §12 labels name the release that introduced each component instead of "Unreleased"; §3 and §9.3 list every
  sidecar (revocation log and head, exposure and decision records, qualification record, analysis-level bundle, permit,
  scan submission and verdict) and the protected-use package; §4 defines protected mode, protected input, revocation log
  and head, qualification record, exposure and decision records, analysis-level bundle and permit; §6.3 adds the
  release-manifest inputs `--revocation-log`/`--revocation-head` and `--exposure-record`, and the project-config example
  is schema 1.2.0 with `nonce_ledger`; §6.5 names the scan-service interface; §8 adds the roles of the transforms,
  release preparation, protected-use guard, lineage and revocation tools, bundles and permits, and the scan interface,
  and the protected-mode refusal of a copied batch runner; §9.1 names analysis-level bundles and the permit's review
  rule. `docs/deployment-model.md`: the release-manifest interface lists `exposure_record` and a verified revocation
  status. Documentation only.

### detector-response (audit DR-WP1 to DR-WP4)

- **Cherenkov photon yield carries z^2 (sci-fix, DR-WP1-01).** `cherenkov_angle.py` and four references: helium at
  40 GeV/c, n = 1.05 gives 68.08 expected photons (was 17.02, 4x low); species take `mass:charge`, `--rigidity` sets
  p = zR.
- **Gaisser-Hillas profile stable at any X_max (sci-fix, DR-WP1-02).** log1p form without cancellation, doubling
  bracket without the fixed 1e6 cap: X_max = 1e20 gives FWHM 1.824036e11 in 0.03 s (hung before).
- **Script physics (sci-fix, DR-WP2-06).** Calorimeter fit weights by a constant relative error without per-point
  errors (constant term unbiased in toys), refuses percentages and reports a negative squared term as a failure; PID
  refuses electrons in the heavy-particle Bethe formula and uses water I = 79.7 eV; multiple scattering derives
  beta(R) from mass and charge and solves crossover and MDR with it; tag-and-probe names its central interval;
  pileup checks bin order and reports input totals; front-end `--channels`/`--cells` integers and a `leakage-scale`
  subcommand.
- **References corrected (sci-fix, DR-WP1-05, DR-WP1-06, DR-WP3).** Pileup reweighting on the Poisson mean mu;
  background-subtracted tag-and-probe yields need a simultaneous pass/fail fit (hep-statistics); calorimetric space
  instruments are not spectrometers; the Störmer cutoff is east-west asymmetric; the appendix edit list applied
  where a source was opened (deferred rows listed in VALIDATION.md); one home each for the equations, the chain and
  the fourteen questions; residual sign convention in the glossary (signed track coordinate).
- **Every script prints a status label and JSON errors (DR-WP2-05).** `--status` (input file's status by default for
  the three file-input scripts), JSON on stdout at exit 2, exit 1 for failed computations.
- **Response hardening, contracts 2.8.0 (DR-WP2-01 to -04).** `validate.py` rules R1-R10 (`_response_hardening`,
  overlay `ext_response_v2_8.json`): declared intended use and flow handling, misspelled keys, placement, exposure
  contains acceptance and live time, flow vectors, correction space, finite-MC statistics for unfolding, variation
  shapes, and the numbers of an inline matrix. Of 30 crafted broken responses `validate.py` now refuses 28 (5 before);
  the two others pass with warnings by design. `response_adapter.py` reads `file.json#key` and flow vectors from the
  ref, refuses refs outside the artifact folder and exits 2 on unreadable refs. SKILL.md step 5 names both checks.
- **Shipped examples carry resolvable responses (DR-WP1-04).** `ams-flux-ratio` writes one response per species and
  period with `matrices/response_<species>_<period>.json` and declares exposure once with its correction space;
  `collider-angular` points at `matrices/response.json`. All five pass `response_adapter.py --validate`.
- **Tool contracts (DR-WP2-07)** for tag-and-probe, PID separation, calorimeter resolution and pileup reweighting;
  `tool_contract.py` reads options of a required mutually exclusive group.
- **Coverage (DR-WP4).** Finite-MC response covariance, fakes, time-dependent responses, a worked 2x2 example and the
  two-tool table; response systematics; resolution models and data-driven resolution; luminosity calibration (vdM);
  calibration pitfalls; ML-reconstruction and fast-simulation validation; JES chain; spectral breaks and the proton
  knee; instrument-response checklists. AMS-02 profile: Layer-0 status by claim ID, solar cycle 25 phase.
- **Hep-analysis docstring (DR-Q1).** `geomagnetic_cutoff.py` states the east-west asymmetry; its dipole default is
  unchanged (follow-up for hep-analysis).

## 0.9.0 (2026-10-14)

Contracts 2.7.0 (unchanged). Release B of the agentic-completion plan (PR #74): formal-use permits and analysis-level
bundles, blinding transforms and release preparation, tool contracts, the scan-service interface, `--strict-versions`.

- **`--strict-versions` (validate.py, dependencies.py).** The stricter version policy alone (a newer minor contract
  version is an error, for the artifact and every source), which `--protected` meant before 0.8.0. It does not switch
  protected mode on, so it needs no protected inputs and is never refused for their absence. `--protected` keeps its
  0.8.0 meaning (protected mode); the library parameter is `strict_versions=`. Tests in
  `tests/contracts/test_strict_versions.py`.
- **Formal-use permits, analysis-level bundles and the recipe-use review (tasks P5.1-P5.3; C15, C08).** New
  `contracts/analysis_bundle.py` (`analysis_bundle.json`): one digest over the measurement spec, recipes, semantics
  tables, calibrations, tool contracts, environment lock, reviews and the plugin release; `verify` reports each change;
  an attestation may take it as its subject. New `contracts/permit.py` (`permit.json`): a custodian-issued permit, read
  only as a protected input, binding the bundle and the digests of the inputs, one purpose, an actor, a nonce counted
  in the custodian's nonce ledger (`agent_policy.protected_inputs.nonce_ledger`), a validity window and the
  attestation whose review must accept the recipe for the required roles and cover the use (`permit.*` codes;
  revocation kind `permit`). Formal use in protected mode now runs with a valid permit (`hepdata_export.py --permit`,
  `build_tables(..., permit=)`) and stays refused without one; the core guard takes the check as `formal_check`.
- **Input-blinding transforms, release preparation and residual checks (task P4; C02).** New
  `core/blinding/transforms.py` for the modes `binned-mask`, `event-removal`, `common-offset` (continuous quantities
  only) and `common-scale` (no per-event weights): released data, sealed values and the `protected`/`retained` lists,
  with keys as inputs only and input uncertainties masked or withheld. New `core/blinding/residual.py`
  (`residual_checks`: codes such as `offset.boundary`, `scale.quantization`, `removal.totals_elsewhere`) and the
  counterexample suite `tests/core/test_blinding_residual.py`; `core/blinding/README.md` states what each mode does not
  protect. New `contracts/release_prepare.py`: the release directory, the sealed file outside it and a draft manifest
  that passes `release_manifest.py` with every custodian option.
- **Tool contracts and scopes (task P5.4).** Contracts for `release_prepare.py`, `mask_blinded_bins.py` and
  `audit_blinded_outputs.py` (per-subcommand operations: `tool_contract.py` now compares each subcommand's own usage
  line); scopes `contracts/tool_scopes/{fixed-execution,validation}.json` checked in CI.
- **Rules settled in the release-B review.** A formal-use permit must cover every input file, directories expanded
  (links refused), and a use with no input file is refused; an S3-execution permit binds the frozen execution bundle
  that runs; every recipe in the analysis bundle must be the attested one; a relative attestation path is read from
  the project. Release preparation builds and checks everything before writing, creates files exclusively (the sealed
  file owner-only, 0600), compares resolved paths, and refuses an existing sealed file, a `release_id` with path
  characters and a manifest over the sealed file. The scan budget is charged by the service's recount of the received
  bytes (never less than the submission states) and stays exhausted once refused. Residual checks recognize identifier
  fields by name tokens (camelCase included), scaled counts up to 10^5 at float precision, and integer residues at
  large values. Bad bundle refs and duplicate JSON keys are refusals.
- **Scan-service interface (task P6.1).** New `contracts/scan_verdict.py` (`scan_submission.json`,
  `scan_verdict.json`): a closed agent-visible verdict (status and budget state only) and a per-analysis budget
  counted in candidate values tested, charged for every submission.

## 0.8.0 (2026-10-14)

Contracts 2.7.0 (minor: the capability IDs `core:revocation-log`, `core:exposure-record`, `core:decision-lineage` and
the warning `exposure.capability_not_declared`; a 2.6 artifact keeps its outcome; the data release manifest sidecar
keeps `manifest_version` 1.0.0;
new sidecars: revocation log and head, exposure and decision records, qualification record). Project config schema
1.2.0 (`agent_policy.protected_inputs`). A project with `agent_policy` now runs in protected mode (see below).

- **Custodian checks in the release-manifest checker (AGENTIC-R5 T1.2, deployment work package B).** The checks a
  custodian deployment ran on its own side move into `contracts/release_manifest.py`, so every custodian uses one
  tested implementation. Always on, from the manifest alone: a transform parameter name that looks like key material
  (`KEY_LIKE`: key, secret, offset, scale, seed, password, token) is `release.keys_present`, a wildcard in a destination
  is `release.destination_wildcard`. New options (keyword-only in `check()`, flags on the command line; each adds
  checks and none is needed for a pass): `--code-digest` (`release.transform_code_mismatch`), `--destination-sets`
  (`release.destination_set_unknown`: the destinations must equal one held set exactly), `--analysis` (release history:
  `release.related_incomplete`, `release.related_unknown`, warning `release.related_revoked`; ledger entries may carry
  `analysis` and `source_sha256`), `--sealed` (every artifact scanned for a sealed value with `core.blinding`, JSON
  objects without their structure keys: `release.sealed_value_present`; an artifact that cannot be scanned is
  `release.scan_incomplete`, fail closed). Findings name the artifact only, never a sealed value or a count. Passing
  still releases nothing. Tests in `tests/contracts/test_release_manifest.py` (`CustodianOptionTests`).
- **Protected-use mode at the formal-use entry points (task P1; C07 plugin part, HC-09, K08, DP-2, DP-4).** A project
  whose config declares `agent_policy`, or an entry point given `--protected`, now runs in protected mode; omitting a
  flag cannot switch it off, and outside protected mode nothing changes. In protected mode every formal-use entry
  point of the R5.4 code change map (validate, dependencies, comparison gate and check, combination plan, model set,
  `combine_measurements.py`, HEPData export and record, `batch_campaign.py` and campaign submit/resubmit/confirm/merge,
  the runner, `engine.run`/`merge`, `local_partition.py`, `bayes_diagnostics.py`, template fits, change review,
  `mask_blinded_bins.py` and the `core.blinding` entry points, `project.load_project`, `environment_manifest.py`, the
  evidence ledger, `check_manuscript.py`) first reads the authoritative copy of the policy named by
  `agent_policy.authoritative_copy` and, from it, `protected_inputs` (project schema 1.2.0): the revocation log and
  head (verified as in P2) and the new qualification record (`qualification_record.json`: valid now, bound to the
  authoritative policy's digest and to the running plugin's code identity, not revoked). Each must be a protected input
  the session's account neither owns, nor can write, nor can replace. A failure, a revoked input file or an input that
  needs an unknown capability is a refusal: command lines exit 3 with `{"status": "refused", "refusals": [{code, path,
  message}]}`, report-returning functions add `protected.*` error findings, other functions raise
  `ProtectedUseRefused`. Formal use (HEPData export for publication) is refused in protected mode until formal-use
  permits exist (release B). The guard is the new standard-library package `core/protected/` (`guard`,
  `trusted_input`, `revocation_log`, `identity`, moved from `contracts/` so that `core/` functions call it; the
  `contracts.identity` and `contracts.revocation` import paths are unchanged), with `contracts/protected_use.py` as the
  public interface (`status` command). `comparison/gate.py`: the comparison logic is `_gate`; the public `gate` and
  `check` check protected use first (refusal `protected-use`). The copied batch runner cannot check the inputs and
  refuses in protected mode (exit 3; protected batch execution runs through the trusted submitter). Instruction-text
  rules P01-P03 report wording that calls these checks an authorization or a bypass; skill references (hep-computing
  engineering playbook, hep-analysis analysis design, hep-statistics combinations) describe protected mode and exposure
  records. Bypass suite `tests/contracts/test_protected_entry_points.py`; fixture `tests/protected_fixture.py`.
  Rules settled in review: a directory the session's account owns is replaceable even when read-only; an input is
  revoked by its byte digest, its canonical JSON digest or its project-relative path, and an input that cannot be read
  is refused (`protected.input_unreadable`); a qualification is revoked by id or digest; a link into a protected
  project is followed when the mode is decided; a project config that cannot be read, or a malformed one that names
  `agent_policy`, switches protected mode on (`protected.config_unreadable`); `authoritative_copy.sha256` is the canonical
  JSON SHA-256 of the policy without `authoritative_copy`, as the deployment's launcher computes it; malformed protected inputs are refusals,
  never crashes (`protected.input_malformed`); in protected mode an exposure record is read only as a protected input.
- **Exposure and decision lineage (task P3; C12, T1.9, T4.3).** New sidecars `exposure_record.json` (per analysis and
  source snapshot: entries `{seq, release_id, via: session|relay, seen: [closed kinds], time, actor}`, each version
  naming the canonical SHA-256 of the previous one) and `decision_record.json` (decision, category, actor human or
  agent, `seen: {through_seq, entries_sha256}`, artifacts, `recipe_sha256`), checked by the new `contracts/lineage.py`
  (`lineage.*` codes; command line `lineage.py exposure|decision`). `derive_exposure()` is the one mapping to the
  envelope `data_exposure`: `exposed` once an entry names `signal-region`, `unblinded-result` or `sealed-value`,
  `unknown` (never `unexposed`) for a missing or invalid record; appends cannot clear exposure. Producers use it:
  `review_analysis_change.py --exposure-record FILE` and `batch_campaign.py freeze --exposure-record FILE`.
  `release_manifest.py --analysis ... --exposure-record FILE` (`check(..., exposure_record=...)`) refuses a release the
  record knows but `related_releases` omits (`release.related_incomplete`) or the ledger does not know
  (`release.exposure_release_unknown`). The reverse index follows exposure records (release -> record) and decision
  records (recipe -> decision -> artifacts). Capability IDs `core:revocation-log`, `core:exposure-record` and
  `core:decision-lineage` join `KNOWN_CAPABILITIES` (contracts 2.7.0; a 2.6 reader refuses an artifact that requires
  one); the validator warns `exposure.capability_not_declared` when a structured `data_exposure` names
  a record without `core:exposure-record`. Tests in `tests/contracts/test_lineage.py`.
- **Hash-chained revocation log and reverse index (task P2; C07, F07).** New `contracts/revocation.py` with the sidecar
  schemas `revocation_event.json` and `revocation_head.json`: a genesis record and events `{seq, prev_sha256, subject:
  {kind: artifact|release|recipe|source|attestation, ref and/or sha256}, reason, time, actor}`, each binding the
  canonical SHA-256 of the record before it, and a head `{count, last_sha256, as_of, source}` written by the custodian.
  `verify()`/`load()` refuse an empty or unterminated file, a gap, an edited or reordered record, a truncated log, a head
  for another log, from another source, stale or dated in the future (`revocation.*` codes); a refused log answers no
  lookup instead of "nothing revoked". `build_index()`/`affected()` follow envelope inputs, `data_exposure.record_ref`,
  release manifests, attestations, bundles and recipes to every dependent, transitively, without writing anything.
  New `core/protected/trusted_input.py`: in protected mode a protected input must be a regular file with one link that the
  running account neither owns, nor can write, nor can replace along its path (`source.*` codes).
  `dependencies.py --revocations` now reads the chained log (`--revocation-head`, `--revocation-source`,
  `--max-status-age`, `--now`); the legacy JSON Lines format is a warning (`dependency.revocations_legacy`) and is
  refused with `--protected`; an empty legacy file is an error. `release_manifest.py` and `attestation.py` take a
  verified log (`--revocation-log`, `--revocation-head`, or a `RevocationStatus` in `check()`/`evaluate()`) as their
  status source, filtered by subject kind (`release.status_unverified`, `attestation.status_unverified`). Tests in
  `tests/contracts/test_revocation.py`.
- **Architecture and deployment documents.** New `docs/agentic-architecture.md` (objectives, constraints HC-01 to
  HC-18, planes, blinding modes, release manifest, host enforcement points, guard, stages, component roles, the
  scientific-integrity layer, batch architecture, and where each component lives) and `docs/deployment-model.md` (the
  plugin in this repository; the host adapter and custodian in a separate deployment repository; the interfaces a
  deployment relies on; the release-to-deployment procedure; a host-neutral qualification catalog). Documentation
  only; nothing is qualified by them.

## 0.7.1 (2026-10-13)

Contracts 2.6.0 (unchanged). The recipe sidecar gains `recipe_version` 1.1.0 (optional correction keys); 1.0.0 recipes
keep their outcome. Release notes in brief: the R4 correction key for bounded recipes (PR #67) and the skill texts
aligned with R4 §9 scientific-validation guidance (PR #68).

- **R4 correction key for bounded recipes (AGENTIC-R5 backlog, R4 F04/T04).** `recipe.json` accepts
  `recipe_version` 1.1.0 with optional `effect_keys` on the input and on steps: per effect, the key
  `(target_scope, calibration_digest, variation_id, stage)`. `recipe_semantics.py` also reads these fields from upstream
  `extension.corrections[]` entries. A second application of an effect on the same target scope and variation is
  `semantics.repeated_correction` whatever its calibration or stage; on another scope or variation it is not blocked
  (warning `semantics.repeat_distinct_instance`, for review); a repeat where either side lacks a complete key is
  `semantics.repeat_undetermined` (supply the keys). Unkeyed recipes keep the effect-name rule; keys on a 1.0.0
  recipe, a key for an effect the step or input does not apply, and an input key that differs from the upstream record
  are errors. The operator-semantics table (`differential_flux.json`, approved 1.0.0) is unchanged. Tests in
  `tests/contracts/test_recipe_semantics.py`.
- **Scientific-validation wording aligned with R4 §9 (AGENTIC-R5 backlog).** Statements that were stronger than the
  method allows are qualified: optimizing on the measured events is biased unless a validated pre-designed procedure
  (cross-fitting, k-fold) removes the bias, keeping performance evaluation, method selection and formal inference
  apart (hep-analysis `analysis-design.md`); a core tool's own tests count as closure only for the model they test
  (hep-statistics `SKILL.md`); detector closure is labelled same-model and needs a model-mismatch test or a control
  sample beside it; "independent implementation" states what is shared, and agreement is evidence, not proof. Added:
  injection tests and pulls judged on toy ensembles, with a toy oracle for low counts and boundaries
  (`likelihood-fitting.md`); a closure taxonomy and N-version caveat (`numerical-and-computational-methods.md`);
  chunk-merge preconditions and the event-order caveat (hep-computing `SKILL.md`, `analysis-data-pipelines.md`); the
  guarded period-agreement null test (`correction-chain.md`); holdout tiers and generator-family variation
  (physics-ml `evaluation-strategy.md`); quarantine for what a loop learns and variant sets with registered blind
  spots in bug fixes (`loop-engineering.md`, `engineering-playbook.md`).

## 0.7.0 (2026-10-13)

Contracts 2.6.0 (minor: theory-spec, prediction, measurement-spec and statistical-result hardening rules; optional
fields only; every 2.5.0 artifact keeps its default outcome and gets the new rules with `validate.py --strict`, at the
same level, and at the publication gate; no new capability).

Release notes in brief: four skill audits (hep-analysis, hep-computing, hep-statistics, hep-theory; PR #64) and their
follow-ups (PR #65). Test-only release fix: the gate test that inlines the sbottom benchmark artifact ignores its plugin
version string, which every release rewrites.

### hep-theory

- **theory-spec and prediction semantics (contracts 2.6.0).** `ext_theory_spec.json` gains optional `limit`,
  `neglected`, `computational_run_ref`, `degenerate_directions`, `model.family`, `checks_run[].tolerance` and
  `references_read[].date_read`; `ext_prediction.json` gains `derivation_status`; `uncertainty_component` gains
  `prescription`, `method` and per-bin `bounds`. New core vocabularies `envelope_prescriptions`, `truncation_methods`
  (including `not-estimated`) and `check_results`. New checks (native from 2.6.0): an `observed` prediction, or a
  `validated-in-scope` one without a linked theory-spec input carrying that status, a perturbative argument without
  an order, an asymptotic argument without a limit, a formal proof or analytic derivation with no check run, a check
  result outside the vocabulary, an empty validity domain, a scale envelope without a prescription or with values
  that are not one [min, max] pair (or bounds that do not match the bins), and a `cosmic-ray-propagation` model
  without degenerate directions are errors; a prediction with neither `theory_spec_ref` nor `derivation_status` is
  unresolved; a missing core convention key and a truncation without a method are warnings.
- **Scripts refuse what used to give a wrong number.** `pdf_uncertainty.py` accepts `symmhessian+as`, `hessian+as`
  and `replicas+as` (the last two members are alpha_s down and up, reported as a separate `alphas` object; PDF4LHC21
  Eqs. 6.7-6.8), checks `num_members`, offers `--combine-alphas quadrature` (labelled a prescription) and
  `--symmetrize`, and refuses non-finite members. `eft_truncation.py` refuses `a*b` given with `b*a`, keys that are
  not one pair, blank conventions, an empty operator list, `lambda_tev` <= 0 (was a `ZeroDivisionError`) and
  non-finite numbers, requires `cross_term_convention` for off-diagonal terms, runs the promised rescaling check and
  reports the flag fraction's source. `event_weights.py` refuses negative, out-of-range, repeated and non-integer
  selected indices (an `IndexError` and Python wrap-around before), non-positive cross sections, negative luminosity
  and non-finite weights, and reports the selected sum of weights, sum of squares, effective sample size and relative
  statistical uncertainty. `dis_kinematics.py` refuses points outside the exact lepton-mass bounds y_max and
  Q^2_min(y), reports them, and accepts a target at rest.
- **References.** New `amplitudes-and-widths.md` (phase space and widths from the PDG Kinematics review, narrow-width
  conditions, Breit-Wigner and complex-mass scheme), `selection-rules.md` (procedure, conserved quantities,
  Landau-Yang, Furry, helicity suppression, G-parity) and `regularization-and-schemes.md` (CDR/HV/FDH/DRED, gamma_5,
  beta and gamma_m normalizations, pole vs MS-bar, IRC safety). `cosmic-ray-propagation.md` gains kinematics (pointing
  to `core/kinematics/relativistic.py`), the force-field formula with its source and limits (code stays in
  hep-analysis), and antiproton source-term conventions. Each statement cites an opened source with its location and
  read date, or says `unverified`.
- **New theory profile `theory:higgs-bb-width`.** Gamma(H -> b bbar) with the MS-bar running b mass through
  alpha_s^4, the running of mass and coupling derived and checked mu-independent order by order in exact arithmetic,
  and the scale envelope, truncation estimate and parametric alpha_s and m_b variations kept apart.
- Routing cases for selection rules and a scheme conversion (en, zh-Hant). The committed theory examples
  (`qed-prediction`, `theory-comparison`, `recasting`) are written at contracts 2.6.0 with the added fields; their
  numbers are unchanged.

### hep-computing (remediation CMP-01…CMP-28)

- **CMP-01 partition state lock.** `core/partition/engine.py` `run()`, `reset()` and `merge()` hold an exclusive,
  non-blocking lock on `<state>/.lock` (`dir_lock`, shared with `campaign_lock`, so campaign calls still nest); a second
  process gets `PartitionError("partition.locked")`, and `local_partition.py` prints it as a JSON `error` with
  `code`, exit 2. `status` stays lock-free. Tests: `tests/core/test_partition_robustness.py`.
- **CMP-02 atomic chunk writes.** `_write_atomic` serializes first, flushes and fsyncs, and removes its `.tmp-*` file on
  any failure. A worker result that is not JSON-serializable is a failed attempt with signature
  `unserializable-result` (counted; the run continues) instead of a `TypeError` out of `run()`; `merge` ignores dotfiles
  in `chunks/`. A chunk that uses its last attempt is marked `attempts-exhausted` by that same call, not `failed` (Q5).
- **CMP-03 manifest checked by every subcommand.** `local_partition.py status`, `merge` and `reset` validate the
  manifest first (a list or a dict without `chunks` exits 2 with a JSON `error`, no traceback); `reset` writes nothing
  before validation and refuses a state folder of another manifest (`engine.reset(..., manifest=)`) or an unknown chunk.
- **CMP-04 seal only what public data do not reveal (Q3 option a).** `core/blinding` `seal()` drops exact zero and every
  number equal (relative 1e-9, sign ignored) to one the unblinded bins give alone: a sum over any run of unblinded
  bins, the sideband total, or their square roots. A blinded empty bin no longer makes `job finished: 0 errors` or a
  public sideband CSV a leak; a nonzero blinded value is still found. When nothing is left, `audit_blinded_outputs.py
  seal` writes `nothing_sealable: true` and `scan` accepts the empty list. `NOT_SEALED` names both exclusions.
  `tests/core/test_stats_edge_cases.py` updated: 0 is no longer sealed. Tests: `tests/core/test_blinding_regressions.py`.
- **CMP-05 unreadable numpy caches are unscanned.** An object `.npy`, a pickled or non-zip `.npz` and a corrupt zip
  `.npz` (`BadZipFile`) are listed as unscanned: the scan ends `incomplete`, exit 3, instead of exit 2 or a traceback
  with exit 1 (reserved for a found leak).
- **CMP-ANA-P2-7 (core part of hep-analysis audit P2-7) masking fails closed.** `mask_ratio` refuses numerator,
  denominator and mask of different lengths (`zip` truncated them: a 2-entry reference against 4 bins gave a 2-entry
  ratio); `mask_binned`, `mask_ratio` and `seal` refuse strings, booleans and non-finite numbers; `mask_binned(...,
  errors=)` masks an error array with the values' mask; `flow=True` (in `blinded_mask`, `mask_binned`, `seal`) adds
  underflow and overflow bins, blinded when the region reaches past the first or last edge. The script
  `mask_blinded_bins.py` is unchanged here (hep-analysis branch).
- **CMP-06 `compare_root_histograms.py` is a comparison.** Tolerances `--abs-tol`, `--rel-tol` (default 1e-9) and
  optional `--sigma-tol` (difference over combined bin errors); edges checked on every axis; TH2/TH3 compared per
  (x, y, z) bin in ROOT numbering; worst bin by absolute difference, relative difference and pull reported separately;
  one JSON object with `status`; uproot backend when PyROOT is absent (`--backend`). Exit 0 within tolerance, 1 outside
  or shape/edge mismatch (no traceback), 2 bad input, 3 no backend. Tests: `tests/skills/hep_computing/test_compare_histograms.py`
  (uproot, E2); `test_root_integration.py` now parses the JSON (PyROOT).
- **CMP-07 `environment_manifest.py` drift, inputs, project, output.** Records `system` (OS family, architecture,
  libc: compared; kernel release: a note only) instead of comparing `platform.platform()`; also compares `executable`
  and `machine`. `record --inputs FILE...` writes `input_manifest` (`path`, `sha256`, `size`; validates as a
  `computational-run`), `check` reports changed or missing inputs and, with `--project`, a changed commit or a dirty
  checkout. `--out` creates parent folders; an unwritable output is a JSON error, exit 2; `record` prints a JSON
  `status` (`recorded`). `references/environments-and-containers.md` updated.
- **CMP-08 script contract (Q4).** Every Python and shell script of the skill prints JSON with a `status` key (the
  ROOT viewers `inspect_root_file.py`, `summarize_histogram_statistics.py`, `roofit_workspace_summary.py`, plus
  `lint_task.py`, `check_root_cpp_env.sh` and the maintenance validators on `--json`; human text stays the default),
  exits 0/1/2/3 (3: missing optional dependency or incomplete; PyROOT missing was exit 1), and refuses an unwritable
  output without a traceback (`create_story_card.py`, `generate_skill_example.py`, `make_synthetic_nanoaod.py`
  now create folders). `local_partition.py` adds a uniform `status` (planned, complete, incomplete, error);
  `audit_histograms.py` adds `status` and exits 2 on an unreadable file. `inspect_root_file.C` is exempt by name.
  `SKILL.md` invariant 5 and the playbook state the contract; the per-script table is in the skill `README.md`.
- **CMP-09 `new_root_cpp_project.sh` target, overwrite, name.** `--dir DIR` (default `./NAME`); NAME must match
  `^[A-Za-z_][A-Za-z0-9_]*$` before it enters `project(...)` (`bad name`, `../x`, an absolute path exit 2); an
  existing non-empty target is refused (exit 2) unless `--force`; the generated program writes `output.root` and
  `pt.pdf` into an output folder argument (default `output/`); the CMake file links imported `ROOT::` targets and
  takes the standard from `ROOT_CXX_STANDARD`; the build hint is quoted; `--json`. The generated project configures
  and builds against Homebrew ROOT 6.38.04 (test skipped without cmake and ROOT).
- **CMP-10 `check_root_cpp_env.sh` private temporary folder.** `mktemp -d "${TMPDIR:-/tmp}/root_cpp_check.XXXXXX"`
  replaces `$TMPDIR/root_cpp_check.$$` (and no longer reassigns `TMPDIR`); the trap removes it; the test program takes
  `-std` from `root-config --cflags` only. Two parallel runs do not collide and leave nothing behind.
- **CMP-11 `lint_task.py` cited paths stay inside the repository.** Each cited path is resolved (`..` and symbolic
  links followed) and must stay under `--repo` (or the skill root for the fallback); one that escapes is an error
  "path leaves the repository" (an `src/` + 14×`../` + `etc/asl.conf` path was accepted as existing). A path starting
  with `../` is a warning instead of a silent skip; in-repo paths with `..` still pass.
- **CMP-12 robustness test asserts the contract.** `tests/skills/test_cli_robustness.py` gains
  `HepComputingScriptContractTests`: every hep-computing script (both `.sh` included; `inspect_root_file.C` exempt by
  name) must print one JSON object with `status` and the documented exit code for a missing input, a refused target
  and an output path that cannot be created (22 cases fail on c1d375c, including the four output-path tracebacks).
- **CMP-13 `root-balanced-design-guidelines.md` corrections.** R1: writing to a `TFile` does not need `TObject`
  (`WriteObject`/`Get<T>` for any class with a dictionary; non-`TObject` branches); `TObject` is for `TList`/`TObjArray`
  containers, `TObject*` APIs and directory registration. R2: `ClassImp` is not needed in ROOT 6; `ClassDefOverride`
  only adds `override`; `#pragma read` rules instead of a hand-written `Streamer()`. R3: one baseline, C++17, `-std`
  from `root-config --cflags`. R4: the double delete is order-dependent (`~TH1` deregisters); the hazard is a smart
  pointer outliving its file; callers own non-registering `Get` results (`TGraph`, `TF1`, `TCanvas`, `TVectorD`);
  `TH1::AddDirectory(kFALSE)`; `RResultPtr` ownership; the demo now compiles (checked against ROOT 6.38.04). R5:
  `gRandom` in `Define` under IMT, `DefineSlot`, eager `Snapshot` unless `fLazy`, `Range` unsupported with IMT,
  non-deterministic order and sums. R6: "CINT" dropped. R7: one rule each for naming, non-owning members (pointer),
  `std::filesystem` and exceptions, stated once at the top.
- **CMP-14 `cmake-and-build.md` imported targets, one C++ baseline (Q2).** The minimal project links
  `ROOT::RIO ROOT::Tree ROOT::Hist ROOT::Gpad ROOT::ROOTDataFrame` and sets the standard from `ROOT_CXX_STANDARD`
  (no `ROOT_INCLUDE_DIRS`/`ROOT_LIBRARIES`, no second `-std`); configures, builds and runs against Homebrew ROOT
  6.38.04 with CMake 4.3.2. `cpp-balanced-design-guidelines.md` now states the same C++17 baseline and marks its
  C++20 examples "C++20 only".
- **CMP-15 `bash-balanced-design-guidelines.md`.** B1: sourcing `thisroot.sh`, an LCG `setup.sh` or `module load`
  under `set -u` fails; wrap in `set +u` … `set -u`. B2: `"${arr[@]}"` on an empty array fails under `set -u`
  before Bash 4.4 (macOS `/bin/bash` 3.2; checked on 3.2.57), with the `${arr[@]+"${arr[@]}"}` guard. B3: no
  `/var/lock` (root-owned, node-local) and no `flock` on NFS/EOS/AFS/Lustre; lock in local scratch. B4: the EXIT
  trap does not stop children; forward SIGTERM to the child and `wait` (preemption), exit 143; checked on Bash 3.2.
  B5: the bad-comment example no longer uses `((i++))`.
- **CMP-16 `python-hep-coding-patterns.md`.** P1: `with ROOT.TFile.Open(...) as f:` / `with uproot.recreate(...)`
  instead of "close output files explicitly", consistent with the Python guidelines. P2: `ROOT.SetOwnership` and the
  pitfall of a histogram drawn in a helper vanishing from the canvas. Checked with PyROOT 6.38.04.
- **CMP-17 new reference `crash-and-memory-debugging.md`.** Decision rules (reproduce, shrink to one thread and few
  events, first frame in own code, symbols, stop rule), ROOT's stack trace and `gDebug`, gdb/lldb on `root.exe`,
  valgrind with `$(root-config --etcdir)/valgrind-root.supp`, ASan/UBSan through CMake and their limits with ROOT,
  ACLiC `+g` and the stale-library pitfall, a crash-cause table, and leak triage (RSS against events with
  `gSystem->GetProcInfo`, `gObjectTable`, the directory that holds histograms, jitted RDataFrame strings). Linked
  from `root-debugging.md` and a new "References of the hep-computing skill" section in the playbook.
- **CMP-18 new reference `performance-profiling.md`.** Target in the acceptance criteria and a stop rule; wall time
  and peak RSS first; `perf record -g`, `cProfile`, `py-spy`; RDataFrame one loop (`GetNRuns`, checked 1 then 2),
  `RunGraphs`, IMT and jitting caveats, lazy `Snapshot`; `TTreePerfStats`, cluster and basket sizes (default
  auto-flush 30 MB), branch selection, compression; uproot `expressions`/`filter_name` and `step_size`; batch sizing.
- **CMP-19 new reference `symbolic-and-numerical-computation.md`.** SymPy assumptions, the limits of `simplify`, a
  numeric identity check at random points, `lambdify`, exact rationals; `quad` error estimates, endpoint
  singularities, `points`, a narrow peak missed silently (and still with `points`) until the range is split,
  infinite and oscillatory ranges; `solve_ivp` method choice (RK45 729,668 against Radau 726 evaluations on a stiff
  system), `rtol`/`atol`, the rtol/10 check, events, status; `brentq`, `minimize` status. Every number from a run
  with SymPy 1.14.0 and SciPy 1.18.1; points to `find_python.py` and the validation ladder.
- **CMP-20 current stack.** `root-balanced-design-guidelines.md` gains "RNTuple and current RDataFrame features":
  RNTuple versus TTree (format 1.0 final since 6.34, types in `ROOT::` since 6.36; read by RDataFrame and by uproot
  5.7.6), `Vary`/`VariationsFor`, `DefinePerSample`, `FromSpec`, `DefineSlot`/`rdfslot_`, distributed RDataFrame with
  `executor=` (6.36; the `Experimental` path removed in 6.38), `AsNumpy`/`FromNumpy`; all run with ROOT 6.38.04 and
  cited to the 6.34/6.36 release notes. `python-hep-coding-patterns.md` gains link-level guidance for hist and
  boost-histogram, vector, correctionlib, coffea, dask-awkward and numba. `performance-profiling.md` notes the 6.38
  `Snapshot` compression default (505).
- **CMP-22 Slurm `MaxArraySize` preflight.** `slurm_backend.py` reads `MaxArraySize` from `scontrol show config`
  before `sbatch` and refuses (`slurm.array.too_large`, attempts not-submitted, no `sbatch` call) an array whose
  largest index is not below it; an unreadable value leaves the decision to `sbatch`. New fake `scontrol` in
  `tests/adapters/batch_shims/`; tool facts table row added. Tests: `tests/adapters/test_batch_cmp_regressions.py`.
  (Also: the CMP-07 git test no longer uses an e-mail-shaped placeholder, which the packaging check flags.)
- **CMP-23 Slurm `DerivedExitCode`.** `SACCT_FIELDS` gains `DerivedExitCode`; a job row `COMPLETED 0:0` with a
  nonzero derived code (a failed `srun` step) is `failed` with the derived exit code and `failure_reason`
  `derived-exit`. `core/partition/states.signature` appends `reason=<failure_reason>` when a backend sets one (older
  records keep their signature), and `campaign._apply` carries the field. 8-field sacct recordings still parse. The
  fake `sacct` emits the field; `examples/batch-partition/output/results.json` regenerated (the new `scontrol` call
  count from CMP-22, nothing else changed).
- **CMP-24 HTCondor event 002.** `parse_event_log` maps event 002 (error in executable) to `failed` with
  `failure_reason` `executable-error` (signature `...|reason=executable-error`) instead of leaving the job queued and
  asking `condor_q`; a later hold event still wins. The fake `condor_submit` gains an `executable-error` fault.
- **CMP-21 bookkeeping.** `SKILL.md` Owns names `core/blinding` and `core/partition`; skill README counts (thirty-two
  references, twelve test modules) and links to the new references; three static routing cases (`co-cmp-crash-1`,
  `co-cmp-perf-1`, `co-cmp-ode-1`, all hep-computing, triggers from the existing description) in
  `tests/routing/make_cases.py`, `cases.json` regenerated; capability-matrix rows for blinding, local partition,
  ROOT tools, task authoring and the environment manifest updated; VALIDATION section CMP-REMEDIATION.
- **CMP-25 design guidelines consolidated (Q1).** `root-balanced-design-guidelines.md` keeps the ROOT-specific rules
  (TObject or plain C++, dictionaries and I/O, directory ownership, ROOT globals, errors at the ROOT boundary,
  dictionary limits of templates, naming/comments/file headers for every language, build layout, RDataFrame and
  RNTuple patterns, checklist) and the shared conventions; the generic class/struct/inheritance/state/testing
  sections and the toy examples are gone. `cpp-`, `python-` and `bash-balanced-design-guidelines.md` are checklists
  around HEP failure modes with grep-able anti-pattern tables; the CMP-13..15 rules are kept. Four files: 4,573 →
  1,028 lines; file names and linked anchors unchanged. `docs/reference-consolidation.md` records P1 as executed.
- **CMP-26 off-domain material moved (Q1, Q6).** `product-framing.md` moved to `docs/dev/engineering/` (`git mv`);
  the playbook's New Endpoint, UI Feature, Database Migration and Incident Response sections, the Sprint planning
  and Feature flags sections of `design-and-estimation.md` and the Accessibility section of `risk-and-quality.md`
  moved to `docs/dev/engineering/web-and-delivery-practices.md`, with a one-line pointer at each old place and the
  skill's links re-pointed. `prompt-engineering-and-token-optimization.md` stays (the bundle validator and the task
  guide require it). The skill now has thirty-one references.
- **CMP-27 deferred (Q1).** The six task- and example-authoring scripts stay in `skills/hep-computing/scripts/`:
  task and example authoring remain in the skill's scope.
- **CMP-28 physics-code worked example.** `examples/physics-code-task.md`: prove that the RDataFrame cutflow asset
  reproduces a `TTreeReader` event loop bin for bin (zero-tolerance `compare_root_histograms.py`, bin errors
  compared separately, single- and multithreaded, deliberate mutations must fail); passes `lint_task.py --repo` and
  the example tests; listed in `examples/README.md`.

### hep-analysis

- **Flux bin-width unit.** `cosmic_ray_flux.py` requires `--bin-width-unit {GV,GeV,GeV/n,TeV,TV}` and echoes
  `bin_width_unit`; the guide's check-first row passed a 1.2-1.8 TV bin as 0.6, which makes a flux per GV 1000x too
  large (now: 600 GV). Detector-response commands and the tool contract follow.
- **Bounded flux intervals.** `cosmic_ray_flux.py` now reports an interval on the signal mean s >= 0 from core/stats:
  Garwood for any count (the 500 ceiling is gone), Feldman-Cousins for a known background, Cousins-Highland by
  default for an uncertain one (labelled approximate), `--method profile-fc --toys --seed` for publication use. No
  bound is negative; `flux_upper_limit` when the lower end is 0. The old subtraction is `--method naive`
  (approximate, clipped at 0). Above the FC grid limit it exits 3 and names the alternative. New
  `--exposure-rel-uncertainty` gives `flux_syst_exposure`.
- **One CLI contract.** All twelve scripts take `--status` (core statuses; tables also `published`) and report it;
  exit codes 0 ok, 1 finding or failed computation, 2 invalid input or usage (NaN, inf, malformed files), 3
  incomplete; one-line errors, no tracebacks. `make_yield_table.py` requires `--status`;
  `check_systematic_variations.py` defaults to JSON.
- **One spec format.** `assets/analysis-contract.yaml` and `systematics-config.example.yaml` are removed; new
  `assets/measurement_spec.template.json` (validates with `--strict`) and its field guide. `systematics.csv` uses the
  spec's systematics ledger columns; `systematics_table_tex.py` renders them.
- **measurement-spec semantics (contracts 2.6.0).** `MEASUREMENT_SEMANTICS_FROM = "2.6.0"`: estimand sentence,
  complete observable (phase space, frame, unit and binning), conditional denominators, backgrounds with estimator,
  control region or constraint and closure, each correction once from the controlled categories (factorized
  efficiencies allowed), no zero for unknown, systematics with `applied_via` and unique names, missing markers listed
  in `unresolved_inputs`, blinded specs with a mask and without `observed` status, ratio blocks, ordered periods,
  misspelled keys. New optional schema fields: `estimand`, `no_backgrounds_reason`, background `control_region`,
  `constraint`, `closure`, correction `exact_zero`, blinding `mask` and `unblinding_record_ref`. The 30-mutation probe
  went from 30 silent passes to 2 (both by design). `validate.py` accepts flags before the artifact path. Example
  specs gain an estimand and drop the double-listed luminosity and exposure corrections.
- **Review procedure.** New `references/review-and-artifacts.md` (verdict scale `blocked` / `needs-work` /
  `acceptable-with-open-inputs`, output order, checklist, measurement brief, worked review of a synthetic defective
  spec) and `assets/measurement-review-template.md`; the AMS module links it.
- **Correlations.** One rule in SKILL.md, README, references, routing contract (new ownership row `correlation
  evidence`) and the hep-statistics handoff line: hep-analysis supplies the evidence and a proposed scheme,
  hep-statistics encodes it and checks positive semidefiniteness.
- **Guide re-scoped** (219 to 106 lines): code-level material (API selection, pipelines, code-file requirement, the
  RDataFrame normalization code) moved to `skills/hep-computing/references/analysis-data-pipelines.md`;
  `data-pipelines.md` is a pointer; link checker test for `skills/hep-analysis/**/*.md`.
- **Physics corrections** with primary sources: solar cycle 24 phases (SILSO), cutoff selection rule and exposure
  formula, sigma(Xmax) for p and Fe (Kampert & Unger 2012), ratio cancellation, trials (Gross & Vitells 2010), Garwood
  N = 0 footnote, Barlow's rule, Peelle's Pertinent Puzzle.
- **SKILL.md** 8157 to 7771 B; one home per invariant (blinding rules only in `analysis-design.md`); workflow step 5
  names the `validate.py` command.
- **Scripts.** Orbit cutoff: tilted-dipole ground-track mode with time fractions and an exposure-versus-cutoff table.
  Geomagnetic cutoff: AME2020 nuclear masses, `--radius-re` (old `--altitude-re` deprecated). Force field:
  `--energy-kind`, `--phi-unit`, `--phi-uncertainty`, `--lis-table`, conversions via core/kinematics, NaN exit 2.
  Power-law fit: continuous sharp or smooth broken power law with a free break, chi2/ndf, p-value, covariance,
  asymmetric errors, Lafferty-Wyatt centres, pivot normalization; `--break-energy` now fixes the break of the
  continuous model. Systematic variations: statistical normalization and shape tests with bin uncertainties, flow
  bins for JSON. Blinded-bin masking fails closed on length or type mismatches and masks errors and flow bins.
  Change review: outcome and signal-region wording, strict booleans, new `needs-human-review` decision. Ratio:
  exact `poisson-ratio` and `binomial-fraction` methods. Tables: escaping, `--totals`, safe LaTeX labels.
- **Method content.** New `references/correction-chain.md` (factorized efficiencies with denominators, data/MC
  ratios, time-dependent measurements, nuclei and isotopes, neutrino and fixed-target specifics); estimand and fiducial
  definitions and steeply falling spectra in `measurements-and-unfolding.md`; systematics budget; antiparticle
  backgrounds; trigger efficiency from data, unbiased optimization and look-elsewhere at the design stage in
  `analysis-design.md`. Each has a synthetic worked example checked by `tests/skills/hep_analysis/test_method_references.py`.
- **Spec review script.** New `scripts/review_measurement_spec.py` drafts a verdict-first review from the validator
  findings; the collider and cosmic-ray examples run it and write `review.md`.
- **Tests and records.** Behavioural invariant tests replace the guide-wording test; 14 new routing cases (en and
  zh-Hant) for the hep-analysis boundaries, live run pending; `test_ams02_helpers.py` renamed
  `test_cosmic_ray_helpers.py`; a worked cosmic-ray spec with backgrounds and an active mask
  (`assets/worked-spec.cosmic-ray.synthetic.json`); the flagship example documents the `--profiles-from`
  validation command; capability-matrix title no longer carries a version.
- **Backgrounds and blinding in both journey examples (P4-2, P3-12).** `examples/collider-angular` subtracts a
  synthetic tau-pair-like background estimated from an x_vis sideband (transfer factor from the simulated shape, 10%
  fully correlated), closes it in a validation band and by Asimov, and blinds the forward signal-region bin
  cos theta >= 0.9 (outside the fiducial range). `examples/ams-flux-ratio` subtracts a synthetic Z=1 charge tail from
  the helium window with a charge-sideband estimate and validation band, and blinds the helium signal-region count at
  60-100 GV (helium flux, He/p ratio and period average null there; dataset records stop at 60 GV). In both, a
  custodian step runs `mask_blinded_bins.py` (the unmasked histogram lives only in a temporary directory), the
  unfolding fills the blinded bin with the simulated expectation at zero variance, figures pass
  `core.blinding.check_figure`, and the specs declare backgrounds, the transfer-factor systematic and the mask. The
  example tests check the estimate, the closure, the absent bins, and rerun with a synthetic sentinel in the blinded
  bins: outputs byte-identical, `audit_blinded_outputs.py` passes, a planted sentinel fails. The synthetic-collider
  profile generator gains an optional background sample with a visible-energy fraction (`generate_background`,
  `signal_xvis`, `xvis_fraction`, `--background`); `generate()` is unchanged. The published-comparison record copied
  from Path B is regenerated (its covariance gains the transfer-factor block).

### hep-statistics

- **Statistical-result hardening (contracts 2.6.0).** New errors: `stats.coverage_cl_mismatch`,
  `stats.coverage_interval_inconsistent` (a recorded interval outside the 99.73% Clopper-Pearson interval of its toy
  counts), `stats.p_zero_without_bound`, `stats.p_out_of_range` on probability-like `results` keys (p0, p_value, CLs,
  CLb, ...), `stats.z_p_inconsistent` (one-sided, |Δz| > 0.01), `stats.global_z_above_local`,
  `stats.construction_statistic_mismatch` (for example Feldman-Cousins with q0, CLs values from a Neyman
  construction), `stats.model_sha256_malformed`. New unresolved: `stats.coverage_toys_too_few` (fewer than 200 toys),
  `stats.expected_bands_missing` (an observed limit without median and both bands), `stats.global_z_without_p`,
  `stats.seed_missing`, `stats.gof_toys_missing`; Bayesian `stats.propriety_unsupported` (propriety needs
  {argument, ref}), `stats.poi_prior_missing`, `stats.ess_too_low` (100 per chain), `stats.chains_missing`; `stan`,
  `pymc`, `numpyro` count as gradient samplers and `uniform(0, inf)` as improper. Optional fields `extension.seeds`,
  `coverage.seed`, `goodness_of_fit.p_value_bound`, `significance.convention` (`ext_statistical_result_v2_6.json`).
- **Publication gate.** A `synthetic` or `asimov` statistical-result now fails (`gate.not_observed_data`); toy
  undercoverage is judged on the 68.27% Clopper-Pearson upper end computed from the counts; a blank backend or model
  reference is missing provenance. Gate verdict changes on committed artifacts: the J9 example
  (`examples/ml-classifier-to-inference`, `synthetic`) passed and now fails; 11 synthetic or asimov examples and
  fixtures go from unresolved to failed for the same reason; default and strict validator outcomes are unchanged
  for all of them (`tests/contracts/test_gate_verdict_snapshot.py`).
- `migrate_statistical_result.py` brings a 2.2-2.5 artifact to 2.6.0 (version only) and refuses one that breaks a
  2.6.0 error rule; it never repairs a number or invents a seed.
- **Comparison gate.** `variable-change` needs `edges` (the image of every current edge, strictly monotonic,
  recorded as `edge_map`) and a Jacobian that is a number or `{expression, ref}` (a bare word leaves the comparison
  unresolved); `from == to` is refused (use `rebin`). `unit-conversion` needs a finite factor > 0, recorded as
  `recorded_factor`. `plan_combination` refuses duplicate dataset ids (`combine.duplicate_id`); `envelope` refuses
  rows of unequal length.
- **`validate_covariance.py`** judges PSD, rank and conditioning on the correlation matrix D^-1/2 C D^-1/2: an
  indefinite correlation structure fails whatever the units per bin, and disparate but uncorrelated variances are no
  longer rank-deficient or ill-conditioned; metrics report scaled and unscaled eigenvalues.
- **`likelihood_limits.py contour`**: probes where a bin mean is <= 0 are out of the domain (q = +inf, counted as
  `out_of_domain_probes`), not failed fits; the 3-bin audit input now exits 0.
- **`result_artifact.py`** refuses a CLI output without `status` unless `--assume-status` is given (recorded as
  `results.cli_status_assumed`), refuses a coverage value or toy count under `--coverage-check not-checked`, and
  refuses a JSON list input.
- **Skill entry point and guide.** `SKILL.md` has a Step 0 for one-number questions and a task-to-tool table
  (default tool, fallback, or "no shipped tool"); the closure invariant applies to new models; the context stanza
  sits below Resources; the description says "producing missing physics inputs". `core-stats-guide.md` is split into
  a decision guide (conventions, a per-subcommand caps table checked against the code, choosing a tool, skill
  scripts with NumPy/SciPy markers) and `core-stats-commands.md` (per-module reference, gate rules). D'Agostini
  routes to `unfold-scan` (not `regularized-scan`, which refuses it). Ten reference corrections with ledgered
  sources (Bartlett's effect, `SumW2Error` scope, code4p sign convention, pyhf zero-nominal and staterror defaults,
  iminuit EDM, familywise global p-values, ROOT 6.40 off the Combine stack, ...). New
  `assets/combine.example.json`.
- **New capabilities.** `covariance_fit.py`: broken and smoothly broken power laws, plug-in models, `break-scan`
  (toy-calibrated break interval and no-break test); `statistical_toys.py ratio-cov-analytic` (full ratio
  covariance at counts >= 1e4); `unfolding_diagnostics.py dagostini-unfold` (data unfolding with data and response
  covariance); `shape-limit` without toys at ordinary sizes (100 bins, 1e4 events per bin); `shape-significance`
  (multi-bin q0).
- **Defects fixed on valid inputs.** Exact Phi quantiles for expected bands (`cls-limit --n 2 --b 3.7`: -2 sigma
  2.996, was 3.56; `profile-cls` too); MC ranges for `profile-cls` and `profile-limit`; `shape-limit` at n = 0,
  b = 0 (boundary, no longer failed) and a toy-CLs runtime estimate with a 600 s budget; `unbinned_fit.py` at wide
  or offset ranges (natural-scale Hessian steps, exponential relative to lo, boundary policy for n_sig);
  `eft_scan.py` excludes nu <= 0 in empty bins and refuses CL outside (0, 1); `global_significance.py` input checks,
  auxiliary redraw at the fitted scale, shared upcrossing definition; `pcl_efficiency_ratio.py` exact classical limit
  (n, b up to 1e5 in < 1 s); `covariance_fit.py` checks `relative_cov`; `look_elsewhere.py` memory budget;
  `sensitivity_and_gof.py` reports an infeasible model; `model_card.py` leaves validation regions out of the fit and
  uses constraint widths. Every statistics CLI refuses malformed input with exit 2 and JSON (no tracebacks) and
  prints `--help` without NumPy.
- **References.** `unfolding.md` (SVD, TUnfold, iterative and fully Bayesian unfolding, OmniFold, purity and
  stability, undercoverage of regularized intervals, publishing), new `combinations.md` (BLUE, negative weights,
  Peelle's puzzle, likelihood-level combination), `inference-recipes.md` (Wald and sigma_A, Rolke-Lopez-Conrad,
  Cousins-Highland, PCL, the conditional on/off test, Baker-Cousins, reference priors), `nuisance-modeling.md`
  (`autoMCStats`, spurious signal, discrete profiling, non-additive breakdowns), `astroparticle-statistics.md`
  (unbinned point-source likelihood, TS and Chernoff, Rayleigh/Z_m^2/H-test, Bayesian blocks). Every new source is in
  `docs/evidence/statistics/sources.json` with its verification level (S15-S41), with claims C12-C17 and eight new
  capability entries.
- **Routing checks are language independent** (all skills): `tools/check_routing_static.py` requires trigger terms
  for English cases only; a non-English case may be a natural prompt (`"natural": true`) that reuses no four
  consecutive description words; the description-topics table in `docs/routing-contract.md` (hep-statistics row
  now) must stay named in the owner's description. New cases: six natural zh-Hant hep-statistics prompts, ratio
  with covariance, broken-power-law fit to published points, bump hunt with a fitted background, an English
  combination prompt, and the fit half of J5 (`j05-turn-fit`, Q9).
- `examples/ml-classifier-to-inference/run.py` records the coverage toy seed and no longer crashes on an unresolved
  finding (`Finding.severity`, not `.level`); J9 and `published-comparison` outputs regenerated (version strings,
  the seed, the schema list read).

### Integration (PR #64)

- **Same-event systematic variations.** `check_systematic_variations.py` no longer combines per-sample variances
  (ROOT bin errors, JSON `*_sumw2`) as if the variation were independent of the nominal: that hid a 3% JES shift made
  from the same events (`none`, "neither variation changes this histogram"). The statistical test now uses
  `up_diff_sumw2`/`down_diff_sumw2` (new), `--stat-unc`, or per-sample variances only with `--independent` (new);
  otherwise no test is made, the output says why, and the effect comes from the tolerance. The "neither variation
  changes" warning is given only when no bin changed. When bins differ but neither variation is flagged, the
  warning says "not significant at alpha" only if a statistical test was made; on the tolerance-only path (including
  same-event variations without difference variances) it says the integral and normalized shape stay within the
  tolerance, and the per-variation note no longer claims that no bin differs.
- **`check_root_cpp_env.sh` under `set -e`.** A nonzero exit of `root --version` (informational) ended the check
  without output (CMP-08 moved it into an assignment); it is now tolerated, and a failing `root-config` reports
  `failed` in the JSON. Found by the optional ROOT CI job (Linux container), whose check-run record is now uploaded.
- Test fixes found by CI: the pyhf skip restored on `SrCrModelCard`; the broken-power-law covariance comparison uses a
  relative tolerance (finite-difference precision, Python 3.11).

### hep-statistics follow-ups

- **One broken-power-law parametrization (STH Q8).** New helper `core/stats/broken_power_law.py` (steward
  hep-statistics, no CLI): `[ln A, gamma1, gamma2, ln x_b]`, `ln F = ln A - gamma1 (u - h) - gamma2 h`,
  `u = ln(x/x_b)`, `h = max(u, 0)` (sharp) or `s ln((1 + e^(u/s))/2)` (smooth), so `A = F(x_b)` in both forms.
  hep-analysis `cr_spectrum_powerlaw_fit.py` and hep-statistics `covariance_fit.py` both evaluate it and give
  identical model values. Behavior change in `cr_spectrum_powerlaw_fit.py --model smooth-broken`: its smooth form
  lacked the 1/2, so the reported `normalization_at_break` was `F(x_b) 2^((g2-g1) s)`, not the flux at the break; it
  is now `F(x_b)` (indices, break and chi2 unchanged). Documented once in the core/stats guide (conventions) and
  linked from the hep-analysis guide; the guide's stale "diagonal errors only" description of
  `cr_spectrum_powerlaw_fit.py` is replaced.
- **hep-statistics SKILL.md headroom.** 8178 -> 7653 B (budget 8192): the Resources list of ten reference links moved
  into a reference index in the core/stats guide (Contents), with the ML-assisted link kept in SKILL.md; the
  "N hypotheses, no scan data" row (Bonferroni or Sidak, by hand, labeled) moved to the guide's Choosing a tool table.
  No rule removed; the description and the generated context-resolution stanza are unchanged. The guide stays under
  its 17000 B test (16944 B) by dropping a sentence that repeated its "run, do not hand-compute" convention.

## 0.6.17 (2026-10-13)

Contracts 2.5.0 (minor: ML semantics; every 2.4.0 artifact keeps its outcome and gets the new rules with
`validate.py --strict`; no new capability).

- **ml-artifact semantics (contracts 2.5.0).** `ext_ml_artifact.json` gains optional `splits.overlap_check`,
  `splits.manifest`, `splits.test_groups_disjoint`, an object form of `weights` (source, negative-weight treatment,
  class balancing, where the weights are used), `domain_shift`, `environment` and `output_semantics`. New checks
  (native from 2.5.0): blank grouping key, empty model hash, labels or features, training-domain keys outside the
  features or with lo >= hi, a failed split-overlap check, calibration missing for probability or density-ratio
  outputs or for inference, calibration evaluated on its fit sample, or incomplete are errors; an overlap check not
  run, a missing or failed domain-shift check on a model with downstream use are unresolved; no overlap check,
  dropped negative weights and missing seeds are warnings. New `scripts/write_ml_artifact.py` builds and validates
  the artifact from a training run summary, calibration, domain-shift and split-check results.
- **physics-ml: the invariants are enforced in code.** New `scripts/make_grouped_splits.py` (by run, period, seed or
  parameter point; random-groups, temporal or k-fold; null groups refused unless a policy is given; its manifest
  passes `check_split_integrity.py`). `assets/train_classifier.py` trains from a data file with `--split-manifest`,
  runs the split check first and refuses a leaky split, uses signed event weights in the loss and the metrics
  (training and evaluation weights recorded separately), selects on validation and reports a test split used once,
  stores features, units, standardization and the training domain in the checkpoint, and writes a run summary and
  validation and test scores. `assets/inference.py` checks feature names, applies the stored preprocessing and flags
  (or with `--on-out-of-domain reject` refuses) inputs outside the training domain. New `assets/calibration.py`:
  temperature, Platt and weighted isotonic calibration, weighted reliability curves, ECE with its finite-sample floor,
  fit and evaluation samples required to be disjoint. New `assets/set_classifier.py`: Deep Sets/PFN and a ParT-lite
  with masks, ragged collation, phi wrapping and permutation, padding and empty-set tests.
- **physics-ml: domain check rewritten.** `check_surrogate_domain.py` whitens the inputs and uses Mahalanobis and
  k-nearest-neighbour distances with thresholds calibrated as quantiles on held-out training points, and reports the
  false-positive rate. The per-feature box is a diagnostic only (`--box-strict` restores it as a criterion). The old
  check called a 20-dimensional extrapolation (Mahalanobis 9.3) inside and could call an in-distribution point
  outside; `--factor` is removed. Constant features no longer overflow, a dimension mismatch is an input error (exit
  2) and numerical failure exits 3.
- **physics-ml: fixes.** `check_split_integrity.py`: a null group is reported (it used to pass) and ids and groups
  are compared after stripping and case folding (`--case-sensitive` to opt out). `compare_model_runs.py`: the
  command-line `--lower-is-better` wins over the runs file. `metrics.py` refuses shape mismatches that broadcast;
  `transformer_classifier.py` gives finite outputs for fully masked rows; `last.pt` records the current best value;
  `vision_transfer.py` keeps a frozen backbone's BatchNorm in eval mode; `torch.load` uses `weights_only=True`; every
  PyTorch asset answers `--help` without torch (exit 3 when run without it). `train_classifier.py`: `--use-amp` is
  replaced by `--precision fp32|bf16|fp16`, `--num-classes` defaults to 2, `config.yaml` is read with `--config`.
  `inference.py` takes `--input CSV` and reads the model shape from the checkpoint.
- **physics-ml: references updated.** Grouped splits replace row-level `random_split` in the examples; bf16 and fp16
  in one mixed-precision file with the fp16 range warning for inputs in MeV, keV or ADC counts; FSDP2 and distributed
  checkpointing; ONNX export with `dynamo=True` and `dynamic_shapes`, `torch.export` and AOTInductor, TorchScript no
  longer recommended; checkpoints save RNG, GradScaler and sampler state with an atomic write; deterministic
  algorithms and worker seeding; `torch.compile` with dynamic shapes for variable multiplicity; each code section
  states the torch version it was run with. The PyTorch guide routes to the physics references and no longer tells
  BDT questions to skip them. Generic serving, monitoring, fine-tuning and large-model material is labelled as such
  and LLM-only passages are cut; `assets/scaling-plan.example.json` (a 7B plan) is removed and
  `dataset-splits.example.json` uses runs.
- **Routing.** The ownership table gains ML rows (BDTs and classical MVA, ML-assisted inference training, fast
  simulation training, calibration of model outputs to physics-ml; inference coverage to hep-statistics; detector
  calibration and fast-simulation validation to detector-response). detector-response hands learned fast simulation
  and ML response models to physics-ml; hep-analysis hands classifier or BDT training to physics-ml. Eight routing
  cases (en, zh-Hant) for BDTs, negative weights, working points and an ECAL regression.
- **Worked example (journey J9).** `examples/ml-classifier-to-inference/`: see VALIDATION.md. The synthetic-collider
  profile lists physics-ml.

- **physics-ml: HEP content and task routing (external review patch).** `ml-analysis.md` becomes the physics entry
  point (23 to about 290 lines, original content kept): grouping and k-fold, training versus evaluation weights, class
  balancing and prior correction, four treatments of negative weights and the optimization pathology, analysis
  metrics (background rejection at fixed signal efficiency, Asimov significance with background uncertainty), mass
  sculpting and decorrelation (DisCo, adversarial, planing, DDT, MoDe), parameterized and systematic-aware training,
  simulation-to-data (scale factors, DCTR, domain-adversarial), weak supervision (CWoLa, CATHODE, CURTAINs), the
  OmniFold training side, and deployment in experiment frameworks and triggers. New references
  `particle-and-jet-architectures.md` (Deep Sets/EFN/PFN, ParticleNet, ParT, LorentzNet/PELICAN, variable
  multiplicity, a masked Deep Sets example with permutation and empty-set checks), `fast-simulation-validation.md`
  (conditioning range as training domain, physics constraints, five metric classes, statistical meaning of generated
  samples), `space-and-astroparticle-ml.md` (methods only; experiment facts stay in the profile) and
  `sbi-training.md` (NRE/NPE/NLE training, diagnostics handed to hep-statistics). `multivariate-analysis-bdt-nn.md`:
  XGBoost has raised a fatal error on negative weights since 1.3.0 (it said "can silently mishandle");
  `generative-models.md` points to the fast-simulation file and flags BCE and FID as unsuitable for physics data.
- **physics-ml: weighted metrics and losses.** New `assets/hep_metrics.py` (NumPy, also a CLI with strict JSON):
  signed-weight ROC/AUC, weighted efficiency with MC statistical uncertainty, 1/eps_B at fixed eps_S (a lower bound
  when eps_B <= 0), Asimov significance with sigma_b, N_eff, weighted squared distance correlation, mass-sculpting JSD
  with a statistical baseline, prior correction. New `assets/hep_losses.py` (PyTorch): signed-weight BCE with three
  normalizations, per-batch weight report, DisCo penalty (float32, finite gradient on constant-score batches),
  NaN-safe masked softmax and mean. 33 tests against analytic or construction-known values (Gaussian AUC,
  Mann-Whitney with ties, integer weights equal duplicated events, Asimov limits, dCor cases, sculpting detection);
  the PyTorch tests ran with torch 2.14.1 on CPU.
- **physics-ml: description and routing.** The description is written by task and includes BDTs in analyses, adds
  the load-first clause and a detector-response Not-for; an invariant records training and evaluation weights
  separately; Resources becomes a task-to-reference table; Handoffs gain a hep-analysis row and widen the
  detector-response row to scale factors and tag-and-probe.
- **Profiles connected to physics-ml.** AMS-02 lists physics-ml in `related_skills` and its working-rules routing
  table gains a classifier/regressor row; the EIC profile lists physics-ml and its placement inventory gains an ML row.
- **Partition engine: retries bounded across runs (hep-computing audit F01).** `core/partition/engine.py` counted
  `max_attempts` per `run()` call, so rerunning bought new attempts (3, 6, 9, 12 over four calls). Attempts are now
  counted since the chunk's last `reset()` over all calls (`attempts_since_reset`, as in the batch campaign); a chunk
  with none left reports `attempts-exhausted`, and only `reset()` with a reason restores the budget. The "two identical
  failures stop" rule compares failure signatures instead of raw messages: `local_partition.py` gives each command
  failure a stable signature (exit code, timeout, missing or invalid output), and other exceptions are compared with
  paths, long hex strings and numbers masked. `max_attempts` must be an integer of at least 1. A state written before
  this change counts all its recorded attempts (fail closed).
- **Partition engine: merge reads canonical chunk files only (F02).** `merge()` took chunk files in filename order and
  kept the first claiming a chunk, so a stray `b_c0000.json` with another result replaced `c0000.json` and the merge
  still reported `complete`. Each chunk is now read from `chunks/<id>.json` only; a stray file with the same result is
  reported (`merge.duplicate_chunk`), one with a different result makes the merge incomplete
  (`merge.conflicting_duplicate`), and a stray never stands in for a missing chunk. New hard problems
  `merge.id_mismatch` and `merge.seed_mismatch`; non-object or incomplete chunk files are reported as
  `merge.unreadable` instead of crashing. Regressions: `tests/core/test_partition_p0_regressions.py` (15 tests, 14
  fail on the previous code).
- **`local_partition.py`: missing-output message names the path.** The new `missing-output` failure printed
  `{out}` literally (missing f-string prefix).
- **`run_all_checks.py` runs test modules in parallel by default.** `--jobs` defaults to the CPU count, at most 8
  (was 1); `--jobs 1` runs them serially. Each module already ran in its own process; the full suite passes with
  `--jobs 8` (5 min 54 s wall time on an 8-core host).
- **CI runs faster without testing less.** `tools/run_all_checks.py` starts test modules slowest first (durations
  in the new `tools/module_timings.json`), gains `--part units|checks` and `--shard K/N` (shards balanced by those
  durations; every module in exactly one shard) and `--write-timings`. The `checks` job of `tests.yml` runs as three
  parallel jobs per Python version (two unit shards, one for the profile suites and static checks), and the optional
  jobs use the parallel runner instead of a serial `unittest discover`. `tools/check_ams_optional.py` runs its suites
  one test module per process with `--jobs` (the same modules as `unittest discover`; 218 s to 66 s locally with 8).

## 0.6.16 (2026-10-13)

- **detector-response: front-end electronics and signal processing.** New reference
  `front-end-electronics-and-signal-processing.md` models readout electronics as part of the response: signal
  induction (Shockley-Ramo, ballistic deficit), shaping, noise (series, parallel, 1/f, leakage-current scaling,
  correlated noise in sums, common mode), thresholds (S-curves, Rice noise-hit rate), optimal filtering and sampling,
  ADC/TDC quantization and nonlinearity, time pickoff (jitter, walk, CFD modes), pileup (Campbell, bipolar baseline
  transients), dead time and live fraction, SiPM and PMT readout, LAr TPC signal processing, radiation effects,
  calibration and simulation of the electronics, with an explicit out-of-scope list (circuit, ASIC, FPGA design).
  New script `frontend_response.py` (ENC with closed-form CR-(RC)^n integrals and the shaping optimum, noise-hit rate,
  timing, quantization, pileup, SiPM, ballistic deficit, dead time, cluster noise), each result with a validity list;
  23 tests against values checked by numerical integration and Monte Carlo. The bibliography gains an electronics
  section of nine Crossref-checked citations (Shockley, Ramo, Radeka, Spieler, Cleland-Stern, Rice, Vinogradov,
  MicroBooNE signal processing, Moll).
- **detector-response: electronics statements corrected.** Shaping trades series against parallel noise (an optimum,
  not "slower is quieter"); sub-Nyquist sampling with a known pulse shape is unbiased; optimal filter instead of
  "template fit is best"; common-mode estimates exclude signal channels; dead-time formulas are exact for Poisson
  arrivals and the paralyzable form is given; photostatistics timing `tau_d/N_pe` rather than `tau/sqrt(N_pe)`; clock
  jitter split into global and local parts; the reference time dominates in low-multiplicity, not busy, events;
  `LSB/sqrt(12)` needs dithering noise; dark counts add variance, not only an offset. `triggers-luminosity-pileup.md`
  gains a dead-time and live-time section (the existing cross-reference had no target), and the effective luminosity
  is summed per block with its live fraction.

## 0.6.15 (2026-10-13)

Contracts 2.4.0 (minor: response semantics; every 2.3.0 artifact keeps its outcome and gets the new rules with
`validate.py --strict`; no new capability).

- **Response validation by intended use, and a correct counts closure (detector-response review WP1).**
  `core/stats/validate_response.py` folds a `counts` closure through `M_ij / generated_j` (it multiplied the raw
  counts, 100x off in the review case) and reports it `not_assessable` without `generated_per_truth_bin`. A new
  `metadata.intended_use` (`forward_folding`, `unfolding`, `parametric_fit`) sets the identifiability verdict:
  `underdetermined`, `rank_deficient` and `empty.truth_bin` stay errors for `unfolding` and when the use is undeclared
  (with a new `metadata.intended_use_missing` warning), and are warnings for the other uses. Closure now runs unless
  shape, entry, normalization or orientation errors block it; `conditional_on_selected` with acceptance inside the
  matrix and negative closure truth are errors. Rewritten tests: `test_empty_truth_bin`,
  `test_degenerate_truth_bins_are_not_identifiable` and `test_fewer_reco_than_truth_bins` declare `unfolding` and also
  check the undeclared case.
- **Response artifact semantics and adapter (Contracts 2.4.0).** For 2.4.0 artifacts (older ones with `--strict`),
  `includes` / `applied_separately` use the `response_corrections` vocabulary (every `<x>_efficiency` counts as an
  efficiency, so `trigger_efficiency` no longer bypasses `response.double_counted`); a matrix needs `matrix` or
  `matrix_ref` (`response.matrix_missing`); `conditional_on_selected` with inefficiency or acceptance inside and
  `joint_counts` with inefficiency inside are `response.normalization_inconsistent`; one variable in two units is
  `response.unit_mismatch`; unknown terms are `response.unknown_correction`. Optional `matrix`,
  `generated_per_truth_bin`, `intended_use` and `variable_conversion` fields. New `contracts/response_adapter.py`
  converts a response artifact into validator input (explicit errors for unmappable values such as `unnormalized`) and
  folds through it; the collider-angular and ams-flux-ratio examples use it instead of a second hand-written
  declaration. The folding reference writes `nu = D_reco R D_truth x + b` with each correction's space and order.
- **PID scripts guard their validity ranges (WP2).** `pid_separation_power.py` passes the species charge to
  Bethe-Bloch (d/He4 at 2 GeV/c: 121.6 sigma, was 17.9), takes `--rigidity`, refuses beta*gamma < 0.1 instead of
  returning a negative dE/dx, reports every `below_threshold_interval` (crossing dE/dx bands) with
  `ceiling_is_lower_bound`, and labels `separation_convention` / `reference_species` (`--convention single|quadrature`).
  `cherenkov_angle.py` reports `expected_photons`, `p_no_photon` and `photon_regime` and gives no Gaussian separation
  with fewer than 5 expected photons; `--track-resolution` adds a term that does not shrink with N (default 0 keeps
  the values); field `detected_photons` renamed `expected_photons`.
- **Script outputs are valid and labelled (WP3).** Every detector-response CLI emits strict JSON or a JSON error
  (no NaN, Infinity or traceback). `tag_and_probe_efficiency.py` keeps the 0.95 default but renames its fields
  (`interval_level`, `lower_bound`/`upper_bound`, `distance_to_lower_bound`/`distance_to_upper_bound`) and returns
  nulls with a reason for zero probes (rewritten test: `test_efficiency_bin_zero_total_is_null_not_error`).
  `pileup_reweight.py` reports `n_eff` and `max_weight` with warnings and fails on non-finite weights; the calorimeter
  fit takes per-point uncertainties, reports the covariance, an ndof warning and `extrapolated`; multiple scattering
  warns outside the Highland range; Gaisser-Hillas adds the standard shower age and evaluates in log space.
- **Reference corrections (WP4).** Sixteen review items in the detector-response references: the tracking resolution
  minimum is not at the crossover, `1/(B L^2)` scaling with the Gluckstern terms, the energy-scale flux shift is
  `(gamma - 1) * delta`, muon excess of heavy nuclei by sublinear superposition, per-period simulation instead of
  time-averaged conditions, truth-matching efficiency is not exact, charge confusion is a tail property at every
  rigidity, and others; N_sigma (both conventions), purity, fake and duplicate rates and width estimators are defined
  once in the performance-metrics reference; new approximate formulas carry their PDG source.
- **detector-response SKILL.md (WP5).** A stop rule when the inputs cannot determine the answer, the intended use in
  every response declaration, handoffs for a hep-theory prediction to fold and for tag-and-probe fits and pileup
  systematics to hep-statistics, and a task-routing table in the principles summary (SKILL.md 7266 B).

- **Skill READMEs and trimmed entry points.** Every skill folder has a `README.md` (purpose, folder map, scripts,
  references, handoffs, tests) linked from the plugin README and from each `SKILL.md`. The detector-response,
  hep-statistics and hep-computing `SKILL.md` files, which sat at the 8 KiB budget, keep their rules and point to new
  index sections in the principles summary, the core/stats guide and the engineering playbook for the reference and
  script lists; a live routing rerun of the 80 cases involving them scored 75 of 80 with no change attributable to the
  trim (VALIDATION SKILL-TRIM).
- **Live behavioral evaluation recorded.** `evals/research_communication/run_live_eval.py` runs the eleven cases through
  a headless `claude -p` with the routing harness's isolation; one run on claude-sonnet-5-5 at 0.6.14 (`f7709da`,
  $0.71) scored 6 pass, 4 fail (all routing: quick cases answered without a plugin skill) and 1 critical-fail (a
  referee reply asserting an edit behind a bracketed caveat); no fabricated evidence, invented number or status
  promotion. The scorer was calibrated to 1.1 on that run (grounded fixture content, file:line references, years,
  negated phrases, phrase alternatives); the semantic judgments are the executor's, not an independent review.

## 0.6.14 (2026-10-13)

- **Lint-clean contracts.** No behavior change from 0.6.13: the communication contract modules satisfy ruff (B007)
  and mypy as the CI lint job runs them (an unused loop index; four `isinstance` narrowings written so mypy sees
  them), and the research-communication scripts drop three unused loop variables and chain one exception. The 0.6.13
  tag failed the lint job on GitHub after its push; this release carries the fix.

## 0.6.13 (2026-10-12)

Contracts 2.3.0 (minor: the capability `communication:traceability-v1` and its extension schema; every 2.2.0 artifact keeps its outcome). `contracts/migrate_statistical_result.py` now writes the current contracts version (2.3.0) instead of a literal 2.2.0; the 2.2.0 rules it applies are unchanged.

- **Research-communication review minors closed.** A ```latex fence counts as a diagram only when it holds a
  `tikzpicture`, so `check_diagram_sources.py --require-render` can pass on a bundle of code examples; a changed
  document digest is unresolved (not a warning) when any of its occurrences is marked inspected; a revision edge whose
  value matches the recorded display never erases a value change found on another edge; revision and adaptation
  reports are ordered independently of the hash seed (the worked example no longer pins `PYTHONHASHSEED`); the legacy
  `sources_read[].id` is any non-empty string again (the traceability format keeps the namespaced id); a claim whose
  edges are all context-only is held to the envelope statuses and reported as unmapped; `check_manuscript.py` tries
  `name.tex` then `name` for an include and, in `--main` mode, `--style` scans only the included files; a literature
  re-import with a different DOI or arXiv id for the same local id is an identifier conflict (the record keeps its
  value) and an alias merge keeps the incoming arXiv version in the history; `score_replay.py` exits 3 when no output
  matched a case.
- **Communication traceability (research-communication reliability plan, T1).** Legacy `communication` claims are
  typed: `text` and `result_ref` are non-empty strings and `status` a core status or an array of them (a numeric text,
  a null reference or an object status used to pass). A new reader capability `communication:traceability-v1` selects
  `contracts/schemas/ext_communication_traceability.json`: claims with stable ids, evidence edges (`artifact` targets
  matched to `inputs[].ref`, `source` targets to a declared or bound evidence ledger; locator, role, `usage`),
  document occurrences, read events and support assessments. `contracts/communication.py` applies the pure rules: a
  claim inherits the sticky caveats of every `used-in-claim` edge whatever its role (a `contradicts` edge is no
  escape), carries `observed` only with an observed or source edge, never `observed` with `synthetic`/`asimov`, and an
  assessment is bound to a digest of the claim text and scope and to the input digests (a wording change or a changed
  hash makes it stale and unresolved; `currency: current` on a stale assessment is an error). The envelope rules are
  unchanged: the envelope keeps the sticky caveats only, so a mixed observed/synthetic document is representable. The
  marker `traceability_version` without the capability, an unknown version, or the capability without the marker are
  errors; a 2.2.0 reader without the capability refuses the record. `contracts/communication_project.py` resolves a
  record inside a project root through `contracts/dependencies.py` (which gains an additive `vocab` parameter so
  sources using a bound profile's terms validate), loads declared and bound-profile ledgers, resolves source ids and
  document digests, and normalizes outcomes (`resolve_outcome`: input-error 2, fail 1, incomplete 3, pass 0;
  unresolved findings or a failed upstream never read as complete). A legacy record is reported as limited
  traceability. Contracts move to 2.3.0 with this release (additive: a new capability and schema; no field removed or tightened for 2.2.0 artifacts).
- **Manuscript checks scoped to the selected document (T2).** `check_manuscript.py --main MAIN.tex` scans only the
  files the main document reaches through literal `\input`, `\include`, `\subfile` and `\import`, resolved against
  `--build-root` (default: the main file's folder) and bounded by `--project-root`; a label in an unincluded sibling no
  longer satisfies a reference, and two documents in one folder may share labels. Only the bibliography the document
  declares counts; a built `.bbl` counts only with `--bbl`, otherwise the citations it alone could resolve are
  unresolved (exit 3). Macro-generated names, conditional includes, `\includeonly`, missing includes or `.bib`
  files, out-of-root paths and include cycles are reported as incomplete coverage (exit 3), never guessed. Verbatim
  and listing bodies are ignored. Directory mode is unchanged and labeled a repository-wide source scan, except that an
  empty directory is now a no-input error (exit 2) instead of "No issues found". `--format json` prints one report
  object (report_version 1.0.0: status, exit code, coverage, checks run and not run, findings with codes).
- **Diagram verification coverage reported honestly (T3).** `check_diagram_sources.py` gives every block one outcome:
  `rendered` (nonempty renderer output), `lint-only` (Mermaid structural lint without `mmdc`; SVG XML
  well-formedness), `skipped` (DOT without `dot`, PlantUML without `plantuml`, TikZ/LaTeX, which it never compiles),
  `source-error` or `environment-error` (not started, timed out, startup failure, exit without output). Each renderer
  gets one preflight; one that fails it, or times out on a block, is not launched again. Counts reconcile with the
  total; "Checked N block(s)" no longer counts linted or skipped blocks as verified, and rendering is reported apart
  from visual inspection, which the checker never performs. Exit codes: 1 source error; 3 environment error, or with
  `--require-render` any block that was not rendered; 0 otherwise (a timeout used to exit 1 as if the source were
  wrong). `--format json` prints the per-block outcomes, renderer availability and versions.

- **Handoffs and instruction semantics aligned (T4).** `code-review-report.md` and the papers guide now route by the
  question asked, not by the library: implementation, I/O and performance to `hep-computing`, measurement design and
  corrections to `hep-analysis`, statistical treatment to `hep-statistics` (also in ROOT or uproot code), ML rigor to
  `physics-ml`, theory validity to `hep-theory`, detector response to `detector-response`; the old text sent
  statistical treatment of ROOT/uproot code to `hep-analysis` and reruns to `hep-analysis`/`physics-ml`. The 3σ/5σ
  significance table in `scientific-style.md` is scoped to a search's significance statement under the source's own
  field convention; the everyday sense of "evidence" carries no threshold. `citation-verification.md` defines reuse
  of previously verified records (dates, versions, read levels and locators kept; a recheck is a new read event
  beside the old one, never a relabeling). `submission-and-peer-review.md` ties response wording to the revision
  ledger: "we have changed" only for a completed, checked change; pending reruns stay explicit. Six routing cases
  cover these handoffs (`tests/routing/cases.json`, 157 cases) and `test_handoff_text.py` pins the sentences.
- **Results linked to claims; reporting completeness (T5).** Two new research-communication scripts.
  `check_communication.py RECORD --project-root ROOT --checks schema|traceability|manuscript` validates the record,
  resolves its inputs, ledgers, sources and documents, and with `manuscript` opens each declared document and
  compares every declared occurrence with the current text at its locator (Markdown headings; LaTeX sections,
  environments and labels), so a correct manifest cannot mask a wrong manuscript sentence; coverage counts
  (declared, located, checked, mismatched, unresolved) are reported and whole-manuscript coverage is never claimed.
  `audit_claims.py` checks recorded assessments (an unsupported verdict is a confirmed inconsistency), source read
  coverage (a passage cited beyond what the read event covers is unresolved: an abstract value is citable with the
  abstract locator, an unread table is not), advisory wording (status promotion, discovery wording without a global
  significance, generalization beyond the recorded scope; quoted, negated and attributed sentences are skipped),
  display values against exact source values under the occurrence's declared rounding (no invented tolerance; an
  undeclared rounding is a review candidate, an unrecorded unit conversion unresolved), and reporting completeness
  against `assets/reporting-policies.json` (measurement, search, limit, theory prediction, ML result; conditional on
  supplied method metadata, never a chosen default: an expected limit does not imply Asimov, a Bayesian interval
  needs no frequentist construction). It emits a claim matrix, draft-ready facts and handoffs to the producing skill.
  Both print one JSON report (report_version 1.0.0; markdown is a view), refuse an output path that aliases an input,
  and use the exit precedence input-error 2, fail 1, incomplete 3, pass 0. Every CLI consumes the full resolved
  context (schema, resolution and dependency findings), so a missing or replaced evidence file never passes a claim
  audit; an artifact locator that does not resolve is unresolved; read coverage matches whole locators (`Table 1`
  does not cover `Table 12`); a claim waiting on declared inputs, a manuscript check without occurrences, and an
  occurrence whose LaTeX region includes other files are unresolved, not pass or fail. Reference: `evidence-linked-writing.md`.
- **Revision impact and stale assessments (T6).** `track_revision_impact.py BEFORE AFTER --project-root ROOT` compares
  a baseline and a revised record through their pinned identities (input digests, evidence fingerprints, claim
  digests) and classifies each changed claim: analysis rerun (value at the evidence locator changed), source change
  (identity changed, value not shown to differ: reconcile, not reopen), reference move (same identity, new path),
  reassessment (wording or scope changed, sources unchanged), content edit (occurrence text or rounding only), status
  change, added, removed. Every recorded occurrence of a changed claim is listed as stale or edited (abstract, body,
  caption alike); the assessment is reopened where the evidence or wording changed and kept otherwise; a stale
  assessment is reported as needing re-inspection, never as false. A verified revision item that depends on a changed
  claim is reopened; one without completion evidence is an error; an edited item is not evidence that edits happened.
  The baseline is never modified and an old reference is never re-resolved against today's file: when the historical
  content is gone, the impact is reported at identity level with the baseline's own recorded display value, and the
  content comparison is marked incomplete. Each impact lists every change it carries (`changes`), so a rename plus
  stronger wording still reopens the assessment; the revised record's own findings are part of the report; baseline
  references are read only inside the project root and only with their pinned digest. Coverage is the recorded
  occurrences; the report asks for a targeted read of paraphrases instead of claiming whole-manuscript coverage.
- **Literature and citation lifecycle, offline (T7).** `manage_literature.py import INPUT.json --project-root ROOT
  --out OUTPUT.json [--into EXISTING.json]` imports evidence-ledger sources and claims, an explicit search log
  (database, interface, exact query, filters, date, coverage limits, export count, discovery route; template in
  `assets/paper/search-log-template.json`) and status notices into a new literature record with provenance (input
  path and digest, date). Records merge only on identical stable identifiers (DOI, arXiv id without version, INSPIRE
  record) and only across the same formal status; similar titles are proposed merges, never performed; a report and
  a study of one work stay related as same-work. An arXiv version change keeps the history and flags citing claims to
  reassess. A correction or retraction flags dependent claims (reassess inside the notice's scope, check outside) and
  deletes no citation; a journal-version notice records a supersession with its provenance. An old verification date
  is a recheck flag, never an error; an inaccessible full text is an access limitation. Citation keys are preserved and
  collisions reported. The input is never edited; no lookup is performed, and the record says online verification was
  not performed. Quoted instructions inside a source's notes are data.
- **Audience adaptation and evidence-backed reviewer responses (T8).** `check_adaptation.py RECORD --project-root
  ROOT --manifest M --draft D` checks a derived draft (paragraph, abstract, talk outline, poster, public summary;
  skeletons in `assets/paper/audience-adaptation-templates.md`) against its companion manifest
  (`assets/paper/adaptation-manifest-template.json`: brief with audience, format, budget, central claim, record digest
  and indispensable limitations; one statement per quantitative statement or conclusion with its claim ids; omissions;
  unresolved inputs; semantic review): a statement missing from the draft or without a claim id, a number that matches
  no recorded value, a dropped status label, a dropped indispensable limitation, or a universal wording whose claim
  scope is narrower is an error; a stale record digest or a missing semantic review is unresolved (keyword overlap is
  not a semantic check). `--responses` builds the reviewer action table (comment, claims, revision items and states,
  locators, completion evidence) and generates response wording from the recorded state: past tense only for a
  verified change with evidence, pending work explicit, a reasoned decline valid with its reason; a draft that asserts
  uncompleted work is an error.
- **Project terminology and notation consistency (T9).** `check_terminology.py RECORD --project-root ROOT --glossary
  G` scans the record's documents against a project glossary (`assets/paper/glossary-template.json`: concept,
  preferred term per language with English and Traditional Chinese, contextual aliases, definition, abbreviations,
  scope, disallowed substitutions with the context words that make them a likely confusion; notation definitions by
  section scope). Findings are contextual and carry both locations and the rule: a disallowed term next to its context
  word (warning; acceptance versus efficiency, resolution versus precision, confidence versus credible, in either
  language), an abbreviation redefined with another expansion (error) or used before its definition (warning), a
  symbol defined twice in one section with different wording (error), a definition in a scope the glossary does not
  declare (warning). Aliases, bilingual equivalents and declared scoped reuse are never flagged; quoted and
  "so-called" mentions are skipped; nothing is replaced or translated, and meaning stays the reader's review.
- **T17 toy construction diagnosed.** The published-likelihood benchmark (ATLAS-SUSY-2018-31 SRB) adds a post-hoc
  diagnosis, labelled as such: the exact counting CLs limit of the one-bin SRB (n = 3, b = 3.23) is 5.284, inside the
  toy limit's MC range; pyhf's toys match exact Poisson sums on the bare one-bin model; the asymptotic formulae give
  4.68 there, 12% below the exact limit. The toys are correct; the published 4.9 follows the asymptotic construction,
  which understates the limit at three events. The preregistered toy-vs-paper verdict stays a fail.
- **sci-fix: CLs crossings interpolate log CLs.** Linear interpolation of CLs between the 1.0-wide toy grid points put
  every toy crossing 0.06-0.12 too high (observed 5.34 -> 5.28, -1 sigma 4.03 -> 3.94); no verdict changed.

## 0.6.12 (2026-10-12)

- **Discrete profiling coverage established (T27).** A preregistered follow-up with 1,500 toys per envelope row
  (seed 20261013, criteria unchanged) passes bias and coverage for all four truths and both injected signals
  (coverage 0.665-0.694, lower bounds 0.634-0.663 against 0.633; 11 of 12,000 toys failed and count as not covering).
  `discrete_profile.py` runs rows in parallel (`--workers`, `--procedures`); seeds per row are unchanged, so the
  committed 300-toy study reproduces.
- **CI: Combine release gate fixed.** The conda-forge package is `cms-combine`, not `combine` (the first
  statistics-validation run could not solve); the job no longer pip-installs the lock over conda's NumPy. On GitHub it
  now passes: Combine 11.1.0 with ROOT 6.36.14, the datacard template within 2% of pyhf, 0 skipped.
- **CI: campaigns job.** The 300-toy discrete-profiling rerun runs its rows in parallel and compares per row with a
  cross-platform tolerance (coverage 2 points, mean mu-hat 0.01, bias 0.05, failures 2, identical verdicts); timeout
  180 min. First all-green statistics-validation run on GitHub: published, combine and campaigns pass.

## 0.6.11 (2026-10-12)

Hep-statistics audit (audit commit b5c3a55, findings F01–F04, checks T01–T30; evidence in VALIDATION.md,
STATS-AUDIT). Batch A (P0, T01–T08):

- **sci-fix: Poisson domain in the likelihoods (F01, T01).** `likelihood_limits.py` read a negative Poisson mean in an
  empty bin as an empty bin (a shape template interpolated below zero gave expected = -1 with a finite NLL). A
  negative or non-finite mean, or a zero mean with events, is now outside every likelihood (NLL = +inf); a zero mean
  with no events stays valid. `_lnl` and the profiled background `_b_hat` keep `s + b >= 0` (relevant for the
  two-POI fit, where a signal may be negative). No committed example number changed.
- **sci-fix: toy tails are bounds at zero exceedances (F02, T02, T03).** New `core/stats/tail_estimation.py`
  (Clopper-Pearson intervals and one-sided bounds, incomplete beta in pure Python, log-space Poisson tails). Every
  toy p-value of `likelihood_limits.py` and `statistical_toys.py` carries `toy_tail` {k, n, estimate,
  interval (68.27%), upper_bound or lower_bound (95%), convention}. **Behavior change:** `p_value_toys`,
  `toy_p_value_at_asymptotic_limit`, `toy_p_value` and their binomial errors are `null` where they used to report
  p = 0 or an error of 0 (k = 0; the error also at k = n). `statistical_toys.py ratio` counts toys it cannot evaluate
  (`toys_not_evaluated`) instead of reading them as non-exceedances.
- **sci-fix: fit verdicts (F03, T04, T05).** New `core/stats/fit_diagnostics.py`: the damped Newton search is
  unchanged, but every fit now returns `converged` or `failed` with reasons (finite NLL, positive-definite Hessian,
  EDM <= 1e-5; `max_iterations`, `line_search_stalled`, `hessian_not_positive_definite`, `invalid_domain`, ...). A
  best fit at `mu = 0` is checked by the KKT condition. A conditional NLL below the global one by more than 1e-4
  triggers a global refit and, if it remains, a failure (it was clipped to `q = 0` before). `shape-limit`,
  `shape-gof` and `contour` report `fit_diagnostics` and `status`; the CLI exits 1 (`failed`, a fit on the data) or
  3 (`incomplete`, only toy fits failed, or an open contour) instead of always 0. Failed toys are counted and make the
  result incomplete; toy p-values carry the range [k/N, (k+F)/N], while the toy CLs curves still include the q values of
  failed toys, which is why such a result is never ok. A better global minimum found by a refit restarts the limit or
  contour from it.
- **Contracts 2.2.0 (minor): statistical-result semantics (F04, T06–T08).** New optional fields: typed p-value bounds
  (`significance.local_p_bound`, `global_p_bound`), `global_n_toys`, `coverage.check` (`toys`, `exact-construction`,
  `analytic`, `not-checked`) with `n_toys`, `coverage`, `interval`, `cl`, `ensemble`, `failure_policy`, `failures`;
  `fit_diagnostics`; `likelihood.backend`, `model_ref`, `model_sha256`. New rules: a p-value or bound outside [0, 1],
  a confidence level outside (0, 1), a global p-value below the local one, expected bands that are not ordered
  `[low, high]` pairs, or `fit_diagnostics` failed under `fit_status: converged` are errors; untyped coverage, a
  global p-value without `trials_method` and toy coverage without its toy count are unresolved. The rules apply to
  artifacts of contract 2.2.0; older artifacts keep their outcome and get them with `validate.py --strict`. New
  capability `stats:result-semantics`, so a 2.1 reader refuses a 2.2 result that relies on them. New publication
  gate (`validate.py --gate publication`, `contracts.validate.publication_gate`): passed, unresolved or failed, with
  reasons (strict validity, fit status and diagnostics, typed coverage, global calibration of a scan, Bayesian R-hat
  and ESS, model and backend provenance, status labels). New converter `contracts/migrate_statistical_result.py`
  (refuses an artifact that breaks a 2.2.0 rule, names the rule; never invents coverage or a trials method).
- **hep-statistics: `scripts/result_artifact.py`.** Writes a `statistical-result` from a `core/stats` CLI output,
  keeping its status (a failed fit becomes `fit_status: failed` with the `failed` label) and writing a zero-exceedance
  toy p-value as a typed bound.
- **Examples.** The six example statistical-results state `coverage.check` (five `not-checked`: their toy studies are
  closure and pull checks, not interval coverage; `theory-comparison` `toys`; `published-comparison` `analytic`).
  Outputs regenerated for contracts 2.2.0 (only the version strings and `check` changed).

Batch B (P1, T09-T17, T22-T23):

- **Exact counting and asymptotic oracles (T09, T10).** Tests against SciPy roots, an independent Feldman-Cousins
  ordering and the closed forms of Cowan et al. (arXiv:1007.1727v3). New asymptotic calibration gate in
  `likelihood_limits.py` (`asymptotic_calibration`: the asymptotic p inside the toys' 99% exact interval, else
  inapplicable).
- **Toy CLs (T11).** `shape-limit --cls-toys` keeps the CLs+b and CLb exceedance counts per grid point, an exact-interval
  range for the limit (`observed_limit_mc_range`) and reports a limit decided by a floored denominator as unresolved.
- **Toy ensembles and coverage accounting (T12, T13).** New `core/stats/toy_ensemble.py`: explicit ensemble (no
  default), seeds from (seed, toy index), disjoint partitions, one outcome per toy, coverage C/N, (C+F)/N and C/(N-F)
  under a predeclared failure policy, a pass/fail/insufficient-precision coverage gate; no automatic retries.
- **Coverage grid (T14).** `examples/stats-benchmarks/coverage-grid/`: exact coverage of the classical, CLs and FC belts
  and 20,000-toy coverage of the asymptotic profile limit; a negative control (sigma_b ignored) is rejected.
- **SR/CR model card and backend equivalence (T15, T16).** `contracts/schemas/statistical_model.json` (nested as
  `likelihood.model_card`), `adapters/pyhf-combine/assets/model_card.py` and `backend_comparison.py`.
- **Published likelihood (T17).** `examples/stats-benchmarks/published-likelihood-sbottom/`: ATLAS-SUSY-2018-31 SRB from
  the HEPData pallet (checksum pinned) against preregistered paper values, with full CLs scans and bands.
- **Unfolding (T22, T23).** `unfolding_diagnostics.py outer-coverage`; `response-stat` accounts for every toy.

Batch C (P1, T18-T21, T24-T25): `skills/hep-statistics/scripts/covariance_fit.py`, `sweighted_fit.py`,
`bayes_calibration.py`; sci-fix of `bayes_diagnostics.py` (ties, constant chains, ESS and MCSE as Vehtari et al.);
`template_fit.py` refuses signed-weight templates; Bayesian contract rules (NUTS metadata, divergences, E-BFMI,
improper priors).

Batch D (P2, T26-T30, all EXPERIMENTAL): `eft_scan.py`, `discrete_profile.py`, `global_significance.py`,
`pcl_efficiency_ratio.py`, `ratio_estimation.py`. The discrete-profiling study (`examples/stats-benchmarks/discrete-profile/`) meets its
bias criterion; its coverage is not established at 300 toys per point (insufficient precision).

CI, documentation and evidence:

- **CI.** New required job `stats-backends` (`tests.yml`): the statistics tests with pyhf 0.7.6 and ArviZ 0.23.4, where
  a skip for a required backend fails (`tools/run_required_backends.py`). New workflow `statistics-validation.yml`
  (weekly, on demand, on release tags): full-budget campaigns, the published-likelihood reproduction (not-run fails)
  and a Combine 11.1.0 release gate. These workflows were written and their YAML checked here; they have not run on
  GitHub yet.
- **Wording.** CLs is described as a modified frequentist exclusion prescription (not "not a frequentist interval");
  a profile-versus-marginalized difference is no longer called a method systematic to add; frequentist constraint
  terms are `"constraint"` in `shape-limit` (`"prior"` kept as an alias; results carry `constraints` and the legacy
  `priors`); the Combine execution scope in `nuisance-modeling.md` matches VALIDATION; equation numbers of Cowan et al.
  are cited for arXiv v3 (one wrong number corrected).
- **Evidence.** `docs/evidence/statistics/` holds a source and claim ledger (checked by `core/evidence/ledger.py`) and
  a capability ledger with statuses supported, experimental or unvalidated, each with its tests and CI gate.

## 0.6.10 (2026-10-12)

- **batch-schedulers: `limits.max_gpu_hours`.** The Slurm poll reads `AllocTRES`; each attempt records
  `alloc_gpus` (`gres/gpu=N`, 0 for a CPU job, unknown while pending). GPU-hours are GPUs times elapsed time (or the
  walltime limit until the end is observed), allocated GPUs once polled and `resources.gpus` before that; usage
  reports `gpu_hours`. Work without GPUs counts 0 and is never refused by this limit. HTCondor counts requested
  GPUs.
- **batch-schedulers: `limits.alloc_cpu_factor`.** A site-declared allocated-per-requested CPU factor (>= 1) sizes
  `max_core_hours` before any allocation is observed: new jobs and attempts without `alloc_cpus` (queued Slurm
  tasks) count requested CPUs times the larger of this and the observed factor. Closes the first-submission
  under-count left open by the previous entry; usage reports `alloc_cpu_factor` (used) and
  `alloc_cpu_factor_observed`.
- **batch-schedulers: `max_core_hours` counts allocated CPUs.** The Slurm poll reads `AllocCPUS`; each attempt
  records `alloc_cpus`, core-hours use it when present (requested CPUs otherwise, as for HTCondor), and new
  submissions are projected at the largest allocated/requested factor seen in the campaign (`alloc_cpu_factor` in the
  usage). Fixes the 2× under-count on hyper-threaded GPU nodes found in GPU-CAMPAIGN-RUN once a pilot has been
  polled; the first submission and GPU-hours are covered by the two entries above.
- **batch-schedulers: first GPU campaign (documentation and evidence).** Two synthetic GPU chunks on NSTCCore V100
  through the adapter with `resources.gpus`, merged equal to a CPU recompute (GPU-CAMPAIGN-RUN). `batch-scheduling.md`
  now states that `max_core_hours` counts requested CPUs only (under-counting where a site allocates more, 2× on
  hyper-threaded GPU nodes) and that GPU-hours are not tracked (both lifted by the entries above), how
  `resources.gpus` renders and when to use `slurm.gres` instead, and to give GPU chunk results an additive device
  counter so the merge proves where chunks ran. NSTCCore site note, known limitations, capability matrix and
  `adapter.json` environment updated. No code change.

## 0.6.9 (2026-10-11)

- **docs/maintenance.md: real-hardware checks.** The three gated test modules (`HEP_TORCH_GPU_TEST`,
  `HEP_SLURM_TEST`, `HEP_HTCONDOR_TEST`), when to run them before a release, and how to report a GPU run on a pull
  request as a `gpu-tests` commit status (same-repository PRs by maintainers only; site tooling kept outside the
  plugin). First used on PR #41.
- **physics-ml: `check_pytorch_env.py` checks the build against each GPU.** It prints the build's compiled
  architectures and, per visible GPU, whether its compute capability is supported (NVIDIA's binary compatibility
  rules: same major and newer minor for cubins, exact for arch-specific cubins, any newer capability for PTX), and
  exits 3 when one is not. It also exits 3, printing torch's own reason, when `nvidia-smi` sees GPUs but the build
  cannot use them at all (observed: the CUDA 13.0 build on V100 nodes whose driver supports CUDA 12.9 at most, where
  it previously printed "CUDA available: False" and exited 0). Without CUDA it prints the compiled list via
  `torch._C._cuda_getArchFlags()`. Unit tests cover the measured builds; verified on a V100 with both builds and with
  the GPUs hidden.
- **physics-ml guidance:** `ml-analysis.md` treats device and precision as a source of category migration for
  scores that are cut on (evaluate where validated, or measure the migration as a systematic); `reproducibility.md`
  lists the GPU details to record and says to link a `computational-run` artifact from the `ml-artifact`'s `inputs`,
  since the `ml-artifact` has no environment fields.

## 0.6.8 (2026-10-11)

- **physics-ml: first GPU runs.** The assets ran on V100 and RTX PRO 6000 Blackwell GPUs through Slurm (torch 2.14.1,
  CUDA 12.6 and 13.0 builds): CUDA training with and without AMP agrees with CPU, inference, the transformer with fp16
  autocast and 2-GPU NCCL DDP pass; no GPU-only bug found. New opt-in GPU tests `tests/skills/physics_ml/test_gpu_real.py`
  (`HEP_TORCH_GPU_TEST=1`). `test_ddp_skeleton_two_gloo_processes` now hides the GPUs from its child processes: on a
  host with one visible GPU it failed ("invalid device ordinal"), and with two it silently tested NCCL instead of gloo.
  `deep-learning-guide.md` gains "GPU Builds, Clusters and DDP" (compiled architectures per build and how to read them
  without a GPU, emulated bf16, GPUs per DDP rank, AMP not always faster). Evidence in VALIDATION.md (TORCH-GPU-RUN).
- **VALIDATION known limitations:** the batch-adapter row is corrected (it still said fake schedulers only after the
  real Slurm and HTCondor campaigns).
- **hep-computing: checking what a Slurm cluster can give you.** `batch-scheduling.md` gains a read-only procedure
  for the picture the user chooses a partition from: capacity per partition without double-counting shared nodes,
  pending reasons, GPUs that are usable only with free cores beside them, access and QoS limits, what
  `--test-only` does and does not tell, fair-share standing, and one tiny confirming job. Sizing notes that sampled
  `MaxRSS` under-reports short pilots. Learned from a full resource check on NSTCCore (Slurm 24.05.1, 2026-10-10).
- **hep-computing: NSTCCore site note.** The QoS row is corrected (the partition QoS imposes its limits; the job's
  own QoS stays `normal`, it is not replaced); new rows for the RTX PRO 6000 Blackwell node (`b6000-al9_devel`,
  checked with a CUDA kernel) and for partition access and QoS limits. Snapshot values (queue counts, idle
  resources, one user's fair-share figures) are removed from the note: they change by the hour; the note keeps
  configuration and behaviour.

## 0.6.7 (2026-10-10)

- **hep-computing: NSTCCore Slurm site note.** New reference
  `skills/hep-computing/references/batch-site-nstccore-slurm.md`: what Slurm 24.05.1 did on the NSTCCore (TWGrid)
  cluster on 2026-10-10, each fact with its site-guide or SchedMD 24.05.1 page or the observation (partition tiers
  that starve the default partition, memory requests that add billed CPUs, over-memory jobs that swap instead of
  failing, `--export=NONE` rebuilding the login environment, `DerivedExitCode`, sampled `MaxRSS`, Fair Tree priority),
  and how to configure the adapter there. `batch-scheduling.md` links it, and its Slurm tool-facts rows confirmed by
  the first real Slurm campaign (synthetic, 10 chunks, merged equal to a local recompute) now say "observed".
  Follow-up rows: `--export=NIL` starts bare (no `HOME`, no `module`), `srun --container` is silently ignored (no
  `oci.conf`), PyROOT needs `PYTHONPATH=$ROOTSYS/lib` with the `libxxhash` workaround.
- **batch-schedulers: Slurm demonstrated on synthetic data.** `RealSlurmTests` is now a real gated test
  (`HEP_SLURM_TEST=1` plus `HEP_SLURM_CONFIG` naming a reviewed configuration: two synthetic chunks submitted,
  polled, merged and reported) instead of a placeholder skip; it passed on Slurm 24.05.1. `adapter.json` lists Slurm
  `demonstrated-on-synthetic-data` with `tested_versions ["24.05.1"]`, which raises the adapter to
  `demonstrated-on-synthetic-data`. Evidence in VALIDATION.md (NSTCCORE-SLURM-RUN).
- **CI: each pull-request commit runs the workflows once.** `tests` ran on both `push` and `pull_request`, so every
  commit of a PR branch ran the whole suite twice; it now runs on pushes to `main`, on pull requests, weekly and on
  demand. `guard` (path allowlist, secret scan) is unchanged: it still runs on every push and every pull request,
  including pull requests from forks. No plugin change.

## 0.6.6 (2026-10-10)

- **README: package size statement updated** to about 1,070 files and 8.6 MB (the release manifests add about
  0.2 MB each; `check_packaging` flags a statement more than 10 % off).
- **hep-computing: EOS rows of the CERN HTCondor site note observed (work order T06, E2f).** One espresso job
  read a synthetic file from EOS with `xrdcp` and returned outputs through `output_destination`: credentials and the
  EOS mount are present in the job, checksums match, and `output`/`error` are sent to the destination as well (only
  the user log stays on AFS). Documentation only.

## 0.6.5 (2026-10-10)

- **hep-computing: CERN EOS storage note (work order T06).** New reference
  `skills/hep-computing/references/storage-cern-eos.md`: what EOS is, how to address an instance, copying with
  checksums, the mounted file system versus `root://`, versions, recycle bin, quota, ACLs, tokens, and remote
  reading from ROOT and uproot. Every row cites the EOS project site or the EOS 5 documentation (read 2026-10-10) or an
  observation on lxplus with synthetic files. Observations the documentation does not state: overwriting a file
  through the mount keeps no version (an `xrdcp -f` overwrite does); a normal user cannot purge the recycle bin;
  `eos whoami` through the `eosuser` redirector shows nobody; an interrupted upload leaves nothing under the target
  name. Linked from `SKILL.md` (Resources trimmed to stay within the 8,192 B budget), from the HTCondor site note's
  EOS row, and from a new "Remote files (XRootD)" section in `python-hep-coding-patterns.md`. Reference inventory
  regenerated. No code change.

- **CI: the `lint` job passes again.** ruff 0.16 (UP017) asks for the Python 3.11 UTC alias in
  `core/partition/runner.py`; the runner keeps `datetime.timezone.utc` because it runs under the batch workers'
  Python 3.9 (work order T03), now with `# noqa: UP017` and a comment. No runtime change.

- **Tests: the batch-partition example's committed output is compared up to float rounding.** `sum_cos` is a numpy
  reduction whose last digits differ between hosts and numpy builds (lxplus with numpy 1.23.5 against the committed
  file: `…253` vs `…256`), which failed the byte comparison; counts, states, digests and labels stay exact, floats are
  compared at a relative 1e-9, and the helper has its own test. No runtime change.

## 0.6.4 (2026-10-10)

- **batch-schedulers: three follow-ups from the first real HTCondor runs (work order T03).** `watch` stops as soon
  as nothing is queued or running (`nothing-active` when planned chunks were never submitted; before, a pilot watch
  polled to `max_polls` and held the campaign lock); the HTCondor backend reads the event log once more when the
  queue no longer lists a job before falling back to `condor_history` (on AFS the log trailed the queue by seconds
  and the history record came minutes later); a changed configuration with the same files freezes as its own
  request file under the same digest and `submit --bundle` chooses by the configuration hash (before,
  `bundle.request_differs` left no way forward but a new campaign directory). `core.partition.bundle.config_hash`
  is the one formula both sides use. Shim: a `lagged` event-log mode. Tests: watch, HTCondor backend, bundle.

## 0.6.3 (2026-10-10)

- **batch-schedulers: first real HTCondor runs (CERN local pool from lxplus, HTCondor 24.12.16, work order T03).**
  The HTCondor backend takes `htcondor.site_attributes` (a map of ClassAd attribute to string, integer or boolean,
  written as `+Name = value`: CERN's `JobFlavour`, `MaxRuntime`, `WantOS`), accepts `resources.time_limit` (which
  sizes `limits.max_core_hours` and must agree with a `MaxRuntime` attribute), and `htcondor.schedd` (a host name, or
  `caller` for the shell's `_condor_SCHEDD_HOST`): the schedd is recorded with each submission and passed as `-name`
  to every later `condor_q`, `condor_history` and `condor_rm`, so a campaign stays on its schedd when the site's
  mapping changes. Two `condor_submit` failure texts observed on the pool (credential step, rejected transaction)
  settle the attempts as `not-submitted` instead of leaving the submission unconfirmed; `condor_history` is called
  with `-match N`; the cluster-level events `035`/`036` (proc −1, HTCondor 24.12) no longer make the event log
  unparsable. `core/partition/runner.py` no longer uses `datetime.UTC` (3.11+): on workers with Python 3.9 every job
  died before the worker started. `RealHTCondorTests` runs a two-chunk synthetic campaign with `HEP_HTCONDOR_TEST=1`
  and `HEP_HTCONDOR_CONFIG`; it passed on lxplus, and two synthetic 5-chunk campaigns (shared-filesystem and transfer
  modes) merged equal to a local single run. `adapter.json`: HTCondor `demonstrated-on-synthetic-data`,
  `tested_versions ["24.12.16"]`. New reference `hep-computing/references/batch-site-cern-htcondor.md` (CERN batch
  documentation facts with dates, what 24.12.16 did, and how to configure the adapter there); tool-facts rows of
  `batch-scheduling.md` updated to "observed". Evidence: VALIDATION.md, CERN-HTCONDOR-RUN.

## 0.6.2 (2026-10-09)

- **research-communication: identifiers missing from a ledger.** An arXiv number, DOI or INSPIRE record that a ledger
  row lacks is looked up at a primary source the session may reach (INSPIRE-HEP, arXiv, doi.org) and reported as
  looked up there with source and date, not as a ledger claim, and never supplied from memory (`SKILL.md` invariant;
  AMS `source-policy.md` rule with matching against title, journal reference and date). Before, the skill correctly
  refused to quote from memory but did not try an allowed source. Live check in a sandboxed configuration: the B/C
  paper (PRL 117, 231102) was looked up at INSPIRE (record found, no arXiv e-print attached) and arXiv, and reported so.

## 0.6.1 (2026-10-09)

- **Validation hint for profile vocabulary.** `contracts/validate.py` (through `contracts/schema.py`): an unknown
  vocabulary term with a profile prefix (for example `crflux:top-of-instrument`) now says that the prefix comes from a
  profile's vocabulary and that the artifact must be validated with `--profiles-from <project config>`. Before, the
  plugin's own AMS example artifacts failed without a hint. New test: all shipped AMS example artifacts validate with
  the profile bound.
- **Guidance from a synthetic-twin study** (B/C ratio, run in a sandboxed configuration):
  hep-statistics `inference-recipes.md` gives a measured case where `-2 log lambda <= 1` covered 0.57-0.79 instead of
  0.683 at low counts and a toy-calibrated Neyman construction restored it, and asks for yield-scaled backgrounds
  inside the likelihood; hep-analysis `systematics.md` adds how to test whether a variation's shift is significant
  (Barlow's subset approximation for data plus a paired bootstrap for the simulation); the AMS ratio blueprint
  (`charged-cosmic-rays.md`) states that cross-species fragmentation backgrounds scale with the other yield and are
  solved jointly; hep-computing `host-notes.md` warns against hard-coding the plugin cache path in project scripts.
  Reference inventory regenerated.

## 0.6.0 (2026-10-09)

- **Tool contracts (AGENTIC-R5 T4.7, F14, F16).** New sidecar schema `contracts/schemas/tool_contract.json`
  (`contract_version` 1.0.0) and `contracts/tool_contract.py`: per operation, every command-line option mapped to one
  input, inputs and outputs with quantity kind and unit (caller-bound unit symbols such as `{X}` must come from an
  input), failure states by exit code (one meaning per code), required capabilities (only ones this reader implements),
  purposes (exploration, fixed execution, validation; never formal analysis), operators from an operator-semantics table,
  and side effects (no network). The checker runs `--help` and compares the usage line with the declared options in both
  directions, required ones included; `--scope` checks that every operation of an enabled scope has a passing contract
  that declares the scope's purpose. First contract: `contracts/tool_contracts/cosmic_ray_flux.json`; tests also run the
  tool and check the declared outputs and failure exits. `cosmic_ray_flux.py` now refuses a confidence level outside
  (0, 1), and an exposure times bin width or a flux that under- or overflows (exit 2); before, it accepted the levels
  and crashed or printed `Infinity` on the others. A contract authorizes nothing. Tests in
  `tests/contracts/test_tool_contract.py`.
- **Operator semantics for bounded recipes (AGENTIC-R5 T4.6, F04, P05).** New sidecar schemas
  `contracts/schemas/operator_semantics.json` and `recipe.json`, the table `contracts/semantics/tables/differential_flux.json`
  (counts to differential flux: background subtraction, unfolding with or without efficiency in the response,
  efficiency correction, plain or effective exposure, bin width) and the recipe
  `contracts/semantics/recipes/flux_from_counts.json`, bound to the table by canonical SHA-256. `contracts/recipe_semantics.py`
  checks that quantity kinds (and so units) chain from input to estimand, that each step's required effects are already
  applied and its forbidden ones not, that no effect is applied twice, counting effects recorded by upstream artifacts
  (`--upstream`: `included_corrections`, `corrections[].effect_id`; a name outside the table fails closed), that the
  result carries the effects the estimand requires, and that every other effect of the table is applied or listed in
  `not_applied` with a reason (the shipped recipe declares that it does not unfold), and that a step's named tool has a
  passing contract listing its operator. Effects the recipe claims as already applied upstream must be recorded by an
  `--upstream` artifact (without one they are reported as unverified), and an upstream artifact with no such record
  fails. A changed table no longer matches the recipe. A general Recipe IR is not part of this. Tests in
  `tests/contracts/test_recipe_semantics.py`.
- **Attestations with separate axes (AGENTIC-R5 T4.5, F11).** New sidecar schema `contracts/schemas/attestation.json`
  (`attestation_version` 1.0.0) and `contracts/attestation.py`. The subject is a frozen bundle digest and a scope
  (observable, data, recipe digest, calibrations, assumptions, purposes). Three axes are reported separately and never
  combined: capability (`supported`/`unsupported` by this reader), review (each review binds the bundle digest, the
  scope digest and its evidence files' SHA-256, re-hashed under `--evidence-root` without following links; states
  `absent`, `unbound`, `rejected`, `bindings-unchecked` without `--bundle` and `--recipe`, `evidence-unverified`,
  `roles-unchecked`, `roles-incomplete`, `out-of-scope` for a `--use` beyond the reviewed scope, `accepted-as-recorded`:
  the reviewer's identity and the protected record are not verified here) and lifecycle (revocation and expiry from a fresh status source; states
  `unknown`, `draft`, `withdrawn`, `superseded`, `not-yet-effective`, `expired`, `revoked`, `active`). `--bundle` and
  `--recipe` must match the subject; a mismatched or malformed attestation gets no axis states at all, and a status
  age above one day is refused. The exit code says only whether the attestation was evaluated; whether a use may
  proceed is the trusted gate's decision (T4.1). Tests in `tests/contracts/test_attestation.py`.
- **Data release manifest schema and checker (AGENTIC-R5 T1.2, plan basis §7.3).** New sidecar schema
  `contracts/schemas/release_manifest.json` (`manifest_version` 1.0.0, within the schema engine's keyword set) and
  `contracts/release_manifest.py`, meant to run on the custodian side from protected copies. A pass needs every input
  (fail closed): the release directory holds exactly the listed regular files with their sizes and SHA-256 (links and
  unlisted files refused); the approval record names `approval_ref`, binds the manifest digest (without
  `approval_ref`), its purposes, destinations digest and validity period, and is valid now (authority `data-release`,
  held by the approver in the required approver list); the release ledger shows no reuse of `release_id` for other
  content; revocation status comes from `status_source`, is fresher than `max_status_age_s` and does not list the
  release; every effective destination (service, tenant, region, model family, exact model when named, tools, network,
  recipients, logging) is allowed, and an absent tool, network or recipient list is a failure, as is a directory the
  check cannot list or a malformed approver list, ledger entry or revocation entry. Formal analysis is not a release
  purpose. The checker verifies bindings, not the trust anchor (Q-06); passing releases nothing (T1.8). Tests in
  `tests/contracts/test_release_manifest.py`.
- **Execution-bundle freezing (AGENTIC-R5 T4.2 freezing tool, F06, X05, X14).** New `core/partition/bundle.py` and
  `batch_campaign.py freeze` / `verify-bundle`: a write-once `bundles/<digest>.json` lists, with full SHA-256, size
  and mode, the campaign files, the worker tree, the interpreter (resolved through links and re-checked), an
  environment lock and the container image, which must be pinned by digest (a sourceless `.pyc` counts as code); the
  digest also binds the campaign uid, manifest hash and the data exposure recorded at freezing. The command follows a
  closed grammar: an absolute interpreter, an absolute bundled worker script, then only flags, `--name=value`, single
  placeholders, numbers, plain ASCII words and absolute paths to bundled worker files without braces, each re-resolved
  by `verify` (a repointed link is a change); the template is checked again at freezing, a worker's `#!` line must be
  one absolute interpreter without arguments (read as the kernel reads it) and is hashed; launchers (`env`, `nice`,
  `nohup`, ...; judged by the resolved name) and `#!` scripts are refused as interpreters; the worker root may not
  contain the campaign. A bundle frozen for another campaign (directory, uid, manifest) is refused. The file carries
  an approval request (bundle digest, config hash, limits, scope) and approves nothing. `submit`/`resubmit --bundle`
  re-hash it and refuse a changed campaign (`bundle.changed`); the submission records the digest and the artifact
  lists it. Verification of approved bytes at execution stays with the trusted submitter (T3.5). Tests in
  `tests/core/test_partition_bundle.py`, `tests/adapters/test_batch_bundle.py`.
- **Marketplace lists hep-research only.** Both catalogs (`.claude-plugin/marketplace.json`,
  `.agents/plugins/marketplace.json`) no longer list `ams02-research`; the READMEs say so and how an installed copy is
  handled. hep-research never depended on it; companion profile support is unchanged.
- **Campaign limits, attempt identity and confirmed cancellation (AGENTIC-R5 T3.4, X08, X09).** New
  `core/partition/limits.py`: an optional `limits` configuration section (`max_submissions`, `max_total_jobs`,
  `max_concurrent_jobs`, `max_core_hours`, `max_resets_per_chunk`; values are the site's, none are defaulted) stops a
  submission or reset that would exceed it before anything is written (`limits.exceeded`); unknown and abandoned
  attempts count as used, and as running (an unknown one until a poll sees it end) until `clear_orphan_risk` (CLI
  `clear-orphans`) records that every job the scheduler lists under the submission's tag has ended; without a walltime
  core-hours are unbounded, so `max_core_hours` refuses. `states.decide` caps resets (`resets-exhausted`), so a reset
  no longer bypasses the limits. Attempts record `global_attempt_id` (`<campaign_uid>:<attempt_id>`). `cancel` records
  each command's exit per job (`requested`, `request-failed`, `request-unconfirmed`), also targets jobs found under
  the tag of unconfirmed or abandoned submissions, and an attempt is `termination_observed` only when a later poll
  sees a final state. Unknown, abandoned and orphan jobs leave append-only `resource_risk` records, carried into the
  campaign artifact with the usage. `batch_config.validate` checks the section. Tests in
  `tests/core/test_partition_limits.py`. Limit values and a real pilot remain open (Q-07, T3.3).
- **Structured data exposure in change review (AGENTIC-R5 T4.4, K06).** `review_analysis_change.py` reports a
  `data_exposure` (`state`, `basis`, as in the 2.1.0 envelope) per change and accepts a structured record. A missing
  `looked_at` (basis `none`), an empty list, a string, or an entry it does not recognize as control-region, sideband,
  simulation, calibration or validation data in a closed grammar (one kind of data per entry; simulation entries never
  name data) is `unknown`, never unexposed; such a change gets the new decision `exposure-unknown` instead of
  `accept`. A malformed structured record is an input error (exit 2). Legacy text can only raise a structured state.
  Tests in `tests/skills/hep_analysis/test_review_analysis_change.py`.
- **Independent of companion plugins.** hep-research installs, updates and runs without `ams02-research`; a companion
  owns its compatibility check (its preflight) and declares no host dependency on hep-research.
  - `tools/check_host_manifests.py` parses `dependencies` (bare name, `name@marketplace`, object) in both plugin
    manifests and both repository catalogs and fails on an edge between hep-research and another listed plugin, in
    either direction; unrelated dependencies are left alone. No such edge exists today; the test
    (`tests/tools/test_companion_independence.py`) is protective.
  - Context stanza: a companion's profile, including a `local_profile_paths` entry known to be the companion's folder,
    is used only through its `<plugin>:profile` skill after that skill's preflight; nothing scans for companions; a
    failed preflight makes that profile unavailable and other work goes on. `docs/profile-authoring.md` replaces the
    advice to declare `"dependencies": [{"name": "hep-research", "version": "^0.3"}]` with the preflight, and states
    that package compatibility and profile validation are separate.
  - `contracts/registry.py` and `contracts/project.py`: `--local` or `--registry` without a value is a usage error
    (exit 2, JSON `error`) instead of a traceback with exit 1, which a caller would read as a validation failure, or a
    silently ignored flag; the same local folder given twice (for example in `local_profile_paths` and through
    `--local`, or twice in the config) is one profile instead of a `registry.duplicate_id` error. Folders with the same
    profile ID still fail. `tests/contracts/test_companion_validation_cli.py` covers the CLI cases a companion checker
    relies on.
  - The marketplace catalogs pin `ams02-research` 1.2.1 (commit `32d538a`, was 1.0.1 at `1c3f590`): the companion
    release without a host dependency on hep-research; its own check accepts hep-research `>=0.4.0,<0.6.0`. An
    installed 1.1.0 or earlier still holds hep-research at 0.4.x until the companion is updated first (README).

## 0.5.0 (2026-10-08)

- **Agent-run checks are advisory, blinding tools fail closed (AGENTIC-R5 WP0′).** Built from the R5.4 agentic planning
  basis; no host configuration is qualified by these changes, and the interim rules still hold: public or synthetic
  data only, and no real sealed values in an agent session.
  - The verified R5 patch is applied: a newer contract major version is rejected (`contract.unsupported_major`);
    `dependencies.py --revocations` marks revoked artifacts without changing their bytes; `contracts/verify_run.py`
    recomputes a run's input and output hashes; float32 caches, Latin-1-decodable binary and `hist(histtype='step')`
    are caught; a bad runner template writes meta and exits 2. Follow-ups: numeric dumps that decode as UTF-16 are
    unscanned instead of passing, and float copies match exactly (no float16 false positives).
  - `dependencies.py` reports `dependency_consistency_ok`; `formal_use_allowed` is always `false` (formal use is decided
    only by a trusted gate). The analysis contract's `unblinding_authorization` is now `unblinding_record_ref`, never
    filled by the agent.
  - `audit_blinded_outputs.py scan` prints a fixed status only (no sealed value, token, file, line or count); details go
    to `--report`. The tolerance comes from the sealed file; `seal` prints no count and seals more derived quantities
    (difference of sums, square roots, fractions, (N-B)/sqrt(B)). Signs, the Unicode minus and percentages are matched;
    unreadable arrays and symlinked directories are incomplete; invalid bin edges stop `seal` and `mask_blinded_bins`;
    `check_figure` reads every figure text, contour fills and sealed y values, and `check_figure_report` lists what it
    cannot check.
  - Campaigns and local runs refuse invalid command templates and manifests before writing (only `{start}` `{stop}`
    `{seed}` `{out}` `{id}`; safe chunk IDs, so `../` cannot escape the campaign).
  - Instruction texts: unblinding is done by a person outside the agent session; real data arrive as released blinded
    derivatives; sealing and scanning with real values belong to the data custodian; batch submission is unsandboxed
    execution, limited to synthetic test environments; private local and companion profiles are read only when the
    project's `agent_policy` allows them on a qualified host (none is yet); "tested" hosts are not qualified for private
    data. `tools/check_instruction_text.py` (run by `run_all_checks.py`) guards these texts.
  - Code release identity: `tools/release_manifest.py` writes the manifest of a release bundle (git-listed files,
    full SHA-256, size and mode, sorted, no symlinks) and its digest, verifies a tree against it, and, in CI
    (`release-manifests` job), checks that every recorded `release-manifests/<version>.json` matches its published tag
    and that recorded manifests are only ever added.
  - **Contracts 2.1.0 (minor).** New optional envelope fields: `versions.plugin_release` (`{release, digest}` from
    `contracts/identity.py`: the full digest when the installed tree matches its own recorded release manifest,
    otherwise `unreleased`/`unknown`), `required_capabilities` (a reader rejects one it does not implement) and a
    structured `data_exposure` (`state`, `basis`). `inputs[].version` must be a version. The validator now warns on a
    newer minor contract (an error with `--protected`), checks `versions.contracts` against `contract_version`, and
    warns on unknown top-level keys; `dependencies.py` validates every source as a contract artifact. The batch
    computational-run records the runner hash and resource-request hash in full (older 16-digit hashes still match),
    plus the full manifest hash. Example outputs are regenerated for 2.1.0.
  - **Project config schema 1.1.0.** `agent_policy` (policy version, allowed model-context classes, protected paths
    without `..`, data release manifests checked by SHA-256, unblinding outside the agent session, authoritative copy);
    `contracts/project.py` checks `schema_version` (a newer minor or another major is refused), closes the `blinding`
    block from 1.1.0, adds `blinding.regions`, and requires the block when `agent_policy` is present.
    `contracts.project.load_blinding` reads it validated; `core.blinding.load_project_blinding` refuses a policy without
    a blinding block instead of reporting nothing blinded.
  - **Batch execution hardening (WP3′).** Every scheduler call has a timeout (`scheduler_timeout_s`, default 120 s) and
    an allow-listed environment (`env_passthrough` adds names; credential-like names are refused); Slurm jobs use
    `--export=NONE`, HTCondor jobs `getenv = false`. Only a client that could not start records `not-submitted`; a
    timeout, exit 0 without a job ID or a failure after the call keeps the submission unconfirmed. Each submission has a
    tag (`hepr-<campaign uid>-<submission>`, the job name / `batch_name` and `HepResearchTag`); new `reconcile` lists
    the scheduler's jobs under it, and `confirm` refuses job IDs not in that list. `abandon` records `abandoned`.
    `cancel` records each command's exit and reports requests, not terminations. Configuration strings are single-line
    with strict names; `worker_python` and `transfer_input_files` are absolute. Collection never follows symbolic links
    and caps output size; `merge` refuses chunk files `collect` did not record and warns about collected orphan outputs.
    `submit --plan-digest` binds a submission to its reviewed dry run. The runner (`worker_timeout_s`), the local
    executor and `local_partition.py run` (`--timeout`, `--env-passthrough`) apply the same timeout and environment
    rules.

- **Choosing a SymPy interpreter (SYMPY).** `skills/hep-computing/scripts/find_python.py` finds a Python >= 3.11 that
  imports the packages a task needs (default SymPy). It tries, in order, `--python`, `HEP_RESEARCH_PYTHON`, the
  calling interpreter and `python3` on PATH, and scans nothing else. It reports the chosen path with its Python and
  package versions, or a `failed` status with every candidate's reason. hep-theory runs it before SymPy work and
  records the interpreter and versions in a `computational-run`.
- **Missing SymPy explained.** The theory-profile `derive.py` scripts and `examples/qed-prediction/run.py` print a JSON
  `failed` status naming the missing package and exit 2, instead of a traceback; `--help` works without them.
  Theory-profile tests skip, rather than error, when SymPy, NumPy or SciPy is missing.

## 0.4.0 (2026-10-08)

- **Live routing harness and new routing cases (T19).** `evals/routing/run_routing_eval.py` (repository level, outside
  the plugin) runs the routing cases through headless `claude -p` (Codex commands are built and parsed, not yet run),
  one pass per case, in a fresh folder with read-only tools, a pinned model, per-case and total budgets and a check
  that no other plugin loaded; it records the skills loaded and profile files read, scores strict and lenient routing,
  and compares with a committed baseline per CLI, CLI version and model. Scored summaries are committed; raw transcripts
  are not. The case set grows from 118 to 150: Simplified Chinese, Japanese and German cases, adversarial cases (a tool
  is named but the deliverable belongs to another skill), quick questions and two-turn handoffs, all covered by the
  static check.
- **Saturated-model goodness of fit (T22).** `likelihood_limits.py shape-gof` tests a shape-limit model (with its
  nuisances, constraint terms and `mc_stat`) against the saturated model, with μ fitted or fixed, and calibrates the
  statistic with toys from the fitted model; the χ² reference is reported and labeled approximate. Toy p-values are
  uniform under the null at low counts, where the χ² reference is not.
- **Asymmetric uncertainties (T22).** `skills/hep-statistics/scripts/combine_asymmetric.py` combines measurements with
  asymmetric errors by Barlow's linear-variance or linear-σ likelihoods, and adds several asymmetric uncertainty
  sources on one result by matching cumulants (quadratic or piecewise model, with the central value moved so the mean
  is kept). Closure against the exact pooled likelihood of lifetime measurements and against a Monte Carlo sum.
- **Two-POI contours (T22).** `likelihood_limits.py contour` fits two signal strengths (bins with `s1` and `s2`, the
  shape-limit nuisances and `mc_stat`) and traces the profile-likelihood contours at the chi-square 2-dof levels along
  rays from the best fit, with the Hessian covariance. Toys at the true point confirm the Wilks coverage.
- **Toy CLs for shape-limit (T22).** `likelihood_limits.py shape-limit --cls-toys N` computes CLs from seeded toys on
  a grid of signal strengths (common random numbers across the grid; nuisances profiled on the data at each μ for
  CLs+b and at μ = 0 for CLb, auxiliary measurements redrawn) and gives the observed and the expected median and
  1/2-sigma limits from the same toys. It reproduces the exact Poisson CLs limit for one bin.
- **MC statistics in limits (T22).** A bin of `likelihood_limits.py multibin-limit` or `shape-limit` may give
  `mc_stat`, the MC-statistics uncertainty of its background. It enters as a Barlow-Beeston-lite factor (as
  HistFactory `staterror`): a Gaussian-constrained multiplier per bin, profiled in closed form, redrawn in toys. In a
  coverage study with 20% MC uncertainty per bin it brings the coverage back to nominal, where ignoring it under-covers.
- **Smooth nuisance interpolation (T22).** `shape-limit` shape nuisances accept `"interpolation": "code4p"` (polynomial
  inside |θ| < 1, linear outside, no kink at 0), and normalization nuisances accept asymmetric `hi`/`lo` factors with
  code4 (default), code1 or code0 interpolation, as in HistFactory and pyhf. The default shape interpolation stays the
  piecewise-linear code0, so existing inputs give the same results. Checked against pyhf 0.7.6.
- **Expected-limit bands (T22).** `likelihood_limits.py multibin-limit` and `shape-limit` now give the asymptotic CLs
  limit and the median and 1/2-sigma expected limits under background only, for CLs and for CLs+b, from the Asimov data
  set (Cowan, Cranmer, Gross and Vitells 2011), with σ taken at each band's own signal strength and the q̃ form of the
  CLs+b bands below the median. Checked against the closed form for one bin and against background-only toys.
- **Barlow-Beeston fits with empty MC bins (T22).** A bin where a template has no MC count no longer makes the
  Barlow-Beeston likelihood infinite: the template's true content there stays a nuisance, observed as zero, and takes a
  share of the data when the Barlow and Beeston (1993) special case applies (unweighted and weighted fits; an empty bin
  of a weighted template uses the template's mean weight scale). Only the naive fit can now be infeasible; the result's
  status follows the Barlow-Beeston fit and a failed naive comparison is reported in `naive_fit_failed`. The toy
  studies score each fit on its own successful toys instead of dropping a toy when either fit fails.
- **Environments and reproducibility (T23).** `skills/hep-computing/scripts/environment_manifest.py` records the
  environment of a run as the `environment` object and `tools` list of a `computational-run` artifact (Python,
  platform, whether it comes from an LCG view, a container, conda or a venv, package versions, a fixed list of
  variables such as `LCG_VERSION` and `BINARY_TAG`, never other variables, and the git commit and dirty state), and
  `check` lists every drift against a saved manifest. A new `adapters/environments` (status `documented`) holds an LCG
  view setup template and an Apptainer definition built on `requirements-ci.lock`; the new reference
  `environments-and-containers.md` says which route pins what and what to record.
- **Recasting toolchain templates (T20).** A new `adapters/recasting` (status `documented`: none of the tools is
  installed where it was written) holds starting templates for a MadGraph5_aMC@NLO process and launch card, a Rivet
  analysis with its metadata, a Delphes efficiency-module override, a SModelS parameters file and a MadAnalysis 5 recast
  script. `skills/hep-theory/references/recasting-toolchain.md` says which route fits which search, what every recast
  records, and the cutflow and limit checks a template must pass before its status is raised. The packaging scan now
  reads every shipped text format, including these.
- **Columnar analysis starting points (T24).** `adapters/root-uproot/assets/coffea_dijet_processor.py` is a coffea
  processor template (jet selection, signed generator weights, leading-pair mass and its weighted histogram) and
  `root_to_parquet.py` converts a TTree to Parquet in bounded steps, keeping jagged branches, with a manifest of
  checksums and entry counts that must add up. Both are tested on the synthetic NanoAOD-like file from
  `make_synthetic_nanoaod.py`: the processor reproduces the generator's independently computed answers for any chunk
  size, and every entry is written once. A `columnar` extra and an optional CI job cover them.
- **HEPData export (T21).** `adapters/hepdata/assets/hepdata_export.py` writes a dataset-record or a binned prediction
  as a HEPData submission: `submission.yaml`, the table (bins, values, qualifiers from the observable, each uncertainty
  component as a labelled symmetric or asymmetric error) and, when the artifact has one, its covariance table. The
  status label is kept in the submission comment, each description and a `phrases` keyword. A plain standard-library
  writer is the default; `--engine hepdata_lib` uses hepdata_lib. hepdata-validator 0.3.6 accepts both, and
  `hepdata_record.py` reads the export back with the same values and covariance. A new `hepdata` extra and an optional
  CI job run the validator.
- **Systematics table for papers (T26).** `skills/hep-analysis/scripts/systematics_table_tex.py` renders the
  systematics registry (the `assets/systematics.csv` format, plus any impact columns) as a booktabs LaTeX table. It
  refuses a table without a status (`--status` or a per-row `status` column), names synthetic, asimov, preliminary or
  unvalidated content in the caption, records every status in a comment, and escapes LaTeX; tested by compiling the
  output with pdflatex.
- **Missing skill handoffs (T25).** The Handoffs tables gain hep-statistics → physics-ml (simulation-based
  inference, neural likelihoods), physics-ml → detector-response (fast-simulation validation) and → research-
  communication, research-communication → hep-analysis, detector-response and hep-computing, and detector-response and
  hep-computing → research-communication. To stay within the 8,192-byte budget, a few words of existing handoff rows and
  one routing example in `detector-response` and `hep-statistics` were shortened; routing (static), ownership and
  entry-point checks pass.
- **Documentation brought up to date (T27).** The capability matrix header names 0.3.0; `VALIDATION.md` no longer
  points at the removed `DECISIONS.md` as a current file; `docs/maintenance.md` no longer lists the traceability check
  removed in 0.3.0; the entry-point sizes in `docs/architecture.md` and `docs/architecture-review.md` are remeasured
  (5,602–8,185 bytes, descriptions 765–990 characters, about 2,205 always-on tokens); routing results name the case
  set they used (48, 62, or the current 118 cases); the README says `ams02-research` is listed, access-restricted, in
  both marketplace manifests. The AMS example artifacts now record profile `experiment:ams-02` 2.0.0, as shipped in
  0.3.0 (they still said 1.0.0).
- **Feldman-Cousins upper ends now follow the published construction (sci-fix).** `poisson_diagnostics.py
  fc-interval` forces the upper end to be non-increasing in the background, as Feldman and Cousins (1998, Sec. IV.B)
  did for their tables. It now reproduces every `n0 = 0..10`, `b = 0..5` entry of their Tables IV (90%) and VI (95%)
  within 0.01; before, it returned the plain construction, for example 1.08 instead of 1.26 at `n0 = 0`, `b = 2`, 90%,
  and the unit test's reference value was the plain one. `--plain-construction` (`monotone=False`) keeps the old
  interval; the output records `construction`, `upper_plain` and the searched background range. The
  `--sigma-b` (marginalized) interval is unchanged and labelled plain.
- **Exact Poisson p-values no longer underflow (sci-fix).** `likelihood_limits.py profile-significance` and
  `statistical_toys.py boundary` computed `P(N >= n | b)` as `1 - P(N <= n - 1 | b)`, which returned 0 below about
  1e-16 (n = 60, b = 5 gave 0 instead of 7.65e-43). The tail is now summed directly (`poisson_sf`,
  `log_poisson_sf` in `poisson_diagnostics.py`), and both outputs add `log_p_value_exact_poisson` and
  `significance_exact_poisson_z`, computed from the log p-value so they stay finite beyond the smallest double.
  The Garwood lower end uses the same tail.
- **Covariance matrices are no longer repaired silently (sci-fix).** A new private `core/stats/_linalg.py` holds the
  one Cholesky factorization used by `statistical_toys.py`, `unfolding_diagnostics.py` and `likelihood_limits.py`.
  It works on the matrix scaled to a unit diagonal, so its verdict does not depend on units, and it never adds jitter
  quietly. Before, `ratio-measured`, `ratio-cov` and the constant-ratio fit added an absolute jitter of 1e-10 up to
  1.0 until the factorization succeeded: a covariance with correlation 2 gave chi2 = 9e13 and no error, and
  `response-measured` added 1e-14 to every variance. Now a matrix with a pivot below -1e-10 (relative) raises an
  error that names it; a fit refuses a singular matrix; and sampling accepts a semi-definite matrix and reports the
  shift in `regularization` (`response_covariance_check` for `response-measured`, which only checks). The unit test
  of a correlated ratio covariance used an indefinite matrix (smallest correlation eigenvalue -0.05) and now uses a
  valid one.
- **Poisson limits and intervals are no longer clipped at 500 (sci-fix).** `upper-limit` and `interval` searched for
  their root in [0, 500] and returned 500 when it lay beyond (`central_interval(490)` gave an upper end of 500.0
  instead of 513.15, `upper_limit(495, 0)` 500 instead of 533.19). The search range now follows the count, and a root
  that cannot be bracketed below the mean limit is reported `failed` (exit 1), never as the range end. One mean
  limit, 1e5, now holds in `poisson_diagnostics.py`, `likelihood_limits.py` and `statistical_toys.py` (it was 500,
  500 and 1e5), from a new private `core/stats/_poisson.py` whose distribution, tail and quantile are summed in log
  space and stay accurate to that limit (checked against SciPy and decimal arithmetic). `fc-interval` keeps a
  separate, stated limit of 500 on the total mean, since it scans a fine grid.
- **Malformed input gives findings, not tracebacks (sci-fix).** The comparison gate sorted structured cuts with
  `null` (open) bounds by comparing `None` with numbers, and read an explicit `"phase_space": null` or
  `"normalization": null` as an object; both raised on schema-valid input. `validate_artifact` raised "unhashable
  type" when `artifact_type` was a list or an object. The evidence ledger raised on a non-object record, a string
  `year`, a string `data_taking_period`, list-valued ids and a dated source without an `id`. Now the gate CLI goes
  through a new `check()` that refuses an artifact whose fields have the wrong JSON type, or a plan that is not an
  object (`"status": "refused"`, exit 2, findings with a field path and a code), and a malformed plan entry is a
  mismatch of kind `malformed` that is never applied. The ledger reports `source.bad_field_type` and
  `claim.bad_field_type` at `<id>.<field>` and checks the rest of the record. A seeded mutation fuzz (30,000
  mutations of the valid artifact fixtures, gate plans and the shipped ledgers) raises nothing. The ledger's
  `claim.no_limitations` warning is removed: it could fire only when `scope.text` was missing, which is already an
  error. The shipped ledgers give the same findings as before.
- **Blinding scanner: fewer false alarms, no silent passes (sci-fix).** A sealed low count such as 0 or 3 matched
  every "0" or "3" in a log, including `run_3`, `v3.0.1`, `3rd` and dates (8 hits on one unrelated line); a sealed
  value with fewer than 3 significant digits now matches only a standalone number, and such hits are marked
  `weak`. Logs were read as UTF-8 with replacement characters, so a UTF-16 log containing a sealed value passed;
  text is now decoded from its byte-order mark, a UTF-16 byte pattern, UTF-8 or Latin-1, and a file that cannot be
  decoded is `incomplete`. `check_figure` also inspects `fill_between` and other filled areas, `hist2d` and
  `pcolormesh` meshes and `imshow` images, and, given the sealed numbers (`check_figure(fig, region, sealed)`), text
  artists, titles and figure texts; a "blinded" label inside the region is not a leak. What it still cannot see
  (tick labels, legends, colorbars, values carried only by colors, transformed values) is stated in the module.
- **Dependencies, lint and type checks (T18).** A `pyproject.toml` declares the Python dependencies as extras (`core`,
  `pyhf`, `root-uproot`, `torch`, `diagrams`, `test`, `lint`; the plugin itself is not an installable package) and
  configures ruff and mypy for `core/` and `contracts/`, which both pass. `requirements-ci.lock` pins the `core` and
  `test` extras at the newest versions that still install on Python 3.11 (`requirements-ci-constraints.txt` says
  why), checked to install on 3.11, 3.12 and 3.13. `.pre-commit-config.yaml` runs the path allowlist and ruff on
  commit and the fast test tier on push; the repository's git hooks call it when `pre-commit` is installed.
  `docs/maintenance.md` records the plan to trim `detector-response` and `hep-statistics` (8,185 and 8,138 of 8,192
  bytes) by at least 10%.
- **Continuous integration for the tests (T13).** A new workflow `tests.yml` runs the unit tests, profile suites and
  static checks on Python 3.11, 3.12 and 3.13 with the pinned set, and ruff and mypy, on every push and pull request.
  Optional jobs repeat the unit tests with pyhf, uproot and awkward, PyTorch (CPU) or ROOT (container) installed and
  do not block a merge yet; a weekly run uses the latest releases and the slow tier. Actions are pinned to commit SHAs.
- **Faster covariance and response validation (T17).** The validators' eigenvalue step used pure-Python Jacobi
  rotations, cubic in the matrix size (1.6 s at n = 120 here, 6.9 s in the review's container). They now use
  `numpy.linalg.eigh` when NumPy is installed (0.011 s at n = 120) and keep the rotations otherwise, so the checks stay
  standard-library only; `HEP_STATS_PURE_PYTHON=1` forces the rotations, and the report records `eigen_solver`. The
  two solvers agree to 1e-12 relative; a slow-tier benchmark (`tests/core/test_benchmarks.py`) holds the time budgets.
- **One owner for each numerical helper (T16).** Two Jacobi eigensolvers, the Gauss-Jordan solve, the Cholesky solve,
  bisection, the golden-section minimizers and the matrix products now live once in `core/stats/_linalg.py`; the
  number, seed and toy-count checks in a new `core/stats/_validate.py` (each takes the caller's error class); the
  chunked Poisson sampler joins the others in `_poisson.py`. The modules keep thin aliases, numbers are unchanged
  (the examples reproduce bit for bit), and the helpers now say when they did not do their job: the eigensolver
  reports non-convergence (a warning in the covariance and response validators, an error in TSVD unfolding), a
  bisection whose interval does not bracket the limit is refused instead of returning the interval's end, and a
  singular matrix in a profile fit raises `LikelihoodError` (it raised the unfolding module's `ToyError`, which the
  `likelihood_limits.py` command line did not catch).
- **Batch campaigns survive interruptions and concurrent commands (sci-fix, T15).** `campaign.submit` called the
  scheduler before saving its attempts, so a kill in between left jobs running that the campaign did not know about,
  and a second submit could send them again; submission IDs came from a count with no lock. Now every command that
  changes a campaign holds a lock on `<campaign_dir>/.lock` (a second one is refused with `campaign.locked`), and
  `submit` saves its attempts as `submitting` before the scheduler call and confirms them after. An interrupted
  submission blocks further submits until a person runs `batch_campaign.py confirm` with the job IDs the scheduler
  lists or `abandon` with a reason; a refused submission is recorded as `not-submitted`. The default merge no longer
  concatenates string results (it reports `merge.combine_failed`; pass a combine function), and `engine.merge`
  refuses non-finite chunk results and a non-finite merged value (`merge.non_finite`).
- **The test suite is bounded and tiered (T14).** Every subprocess call in the tests and tools has a timeout
  (`tests/tools/test_subprocess_timeouts.py` keeps it so). `check_diagram_sources.py` fails a block whose
  renderer does not finish within `HEP_RENDER_TIMEOUT` (default 60 s) and stops calling Mermaid's `mmdc` after one
  timeout, so a host where Chromium cannot start no longer hangs the suite. `run_all_checks.py` runs each test
  module in its own process with a time limit (`--module-timeout`, default 600 s; `--jobs` for parallel modules) and
  records every module's duration and the modules over 60 s. The full theory-comparison example test (70 to 350 s)
  moved to the slow tier (`HEP_SLOW_TESTS=1`).
- **Every script behaves as a command-line tool (T12).** `tests/skills/test_cli_robustness.py` runs all 64 scripts
  under `skills/*/scripts/` and `adapters/*/assets/` with `python3 -I`: `--help` must exit 0 without a traceback, and
  a missing input file must give a short error (or a JSON error report) with a non-zero exit. A table names each
  script's input arguments or why it reads none, so a new script must be added. Fixed: tracebacks on a missing file
  in 15 scripts (`eft_truncation.py`, `event_weights.py`, `pdf_uncertainty.py`, `check_example_diversity.py`,
  `check_diagram_sources.py`, the four ROOT-file helpers, `check_systematic_variations.py`, `inspect_checkpoint.py`,
  `unbinned_fit.py`, `uproot_awkward_analysis.py`, `reproduce_published_likelihood.py`, `hepdata_record.py`); sibling
  imports that failed under `-I` in `cosmic_ray_flux.py` and `orbit_averaged_geomagnetic_cutoff.py`; and module-level
  imports of pyhf (`reproduce_published_likelihood.py`) and uproot/awkward/PyYAML (`uproot_awkward_analysis.py`)
  that broke `--help`; they now name the package to install when the script runs.
- **Tests for public functions no test reached (T11).** Direct tests for `scan_file`, `load_project_blinding`,
  `clip_demo`, `campaign.chunk_status`, `load_ledger`, `render_tables`, the contract helpers (`check_conventions`,
  `check_finite`, `check_binned`, `check_observable`, `load_schema`, `side_from_artifact`, `find_cycles`,
  `check_profile_dir`, `declared_namespaces`, `namespace_of`) and round trips of every kinematic conversion. New CLI
  tests for `check_surrogate_domain.py`, which printed a traceback for a non-list `features` field and now reports
  it as a JSON error with exit 2. `counting_reference.py` has its own test file (its flat-prior bound at b = 0 checked
  against PDG Table 40.3, its tail against `core/stats`); the `audit_histograms.py` tests moved to hep-computing;
  `examples/published-comparison/make_record.py` is checked to reproduce its committed record.
- **Edge cases in every public `core/stats` entry point (T10).** `tests/core/test_stats_edge_cases.py` feeds NaN,
  +inf and -inf to each numeric argument of 20 scalar entry points and to numeric leaves of 9 document entry points,
  plus empty lists and empty documents; each must raise its module's named error (the two validators must fail
  instead), from a baseline that is checked to be valid. It also covers p-values far below 1e-10, the mean limit and
  zero or low counts in blinded bins. Defects it found, now fixed: `chi2_sf` returned 1.0 for a NaN or infinite
  chi2 or ndf (an infinite chi2 now gives 0, the rest raise); a bin count of inf or NaN in `multibin-limit` and
  `shape-limit` raised `OverflowError` or a bare `ValueError`; `z_from_log_p(nan)` returned NaN.
- **Schema mutation fuzzing and a keyword meta-test (T09).** `tests/contracts/test_robustness.py` mutates every node
  of every valid artifact fixture, a full gate plan and a ledger record four ways (null, type swap, list wrap,
  deletion) in the fast tier, and runs 10,000 seeded random multi-mutations through the validator, the gate and the
  ledger in the slow tier; none raises. `tests/contracts/test_schema_keywords.py` checks that every keyword in
  `contracts/schemas/` is one `contracts/schema.py` implements (`SUPPORTED_KEYWORDS`) or reads as an annotation, so a
  schema cannot promise a check (for example `oneOf` or `maxItems`) that never runs, and that every `$ref` resolves.
- **Property-based tests (T08).** `tests/core/test_properties.py` (with `hypothesis`, a test-only dependency in the
  new `requirements-test.txt`; skipped without it) checks that upper limits are non-decreasing in n and
  non-increasing in b, that intervals are nested in the confidence level, that covariance tools give the same
  verdict at 1e-12 and 1e12 scale, that a GLS fit does not depend on input order, that a partitioned merge does not
  depend on chunking or finish order, and that validators never raise on arbitrary JSON. That last property found
  that `validate_covariance` and `validate_response` raised on a document that was not an object, a non-list
  `labels` or `closure`, and non-numeric `tolerances`; they now report `document.malformed`,
  `tolerances.malformed` and the existing shape codes.
- **Published-table tests (T07).** `tests/core/test_published_tables.py` checks Feldman-Cousins Tables IV and VI,
  PDG 2024 Tables 40.3 (one-sided Poisson limits, the Garwood ends) and 40.4 (unified intervals), each transcribed by
  script with its source, and Li & Ma eq. 17 against an independent transcription (the paper prints no table).

## 0.3.0 (2026-10-07): first public release

The plugin is published under the Apache License 2.0 (`LICENSE` at the repository root and inside the plugin folder,
`license` in both host manifests). This release restructures what the plugin ships; the seven skills, `core/`,
`contracts/` and the adapters are otherwise unchanged in behavior.

- **Access-controlled AMS-02 content moved to a companion plugin.** `experiment:ams-02` (now 2.0.0) keeps the public
  evidence ledger (60 sources, 184 claims), the domain modules, the analysis-spec audit and the paper-manifest and
  CRDB helpers. The user-supplied Offline software modules, the EOS production catalogue, the ntuple-producer kit, the
  generated catalogs and their index, the environment checker and their tests are no longer in this plugin or its
  repository. They are provided to authorized members by the separate, access-restricted plugin `ams02-research`
  (profile `experiment:ams-02-private` 1.0.0, which depends on `experiment:ams-02`), listed in the same marketplace
  `hep-research-dev` for Claude Code and Codex. The public profile's `index.md`, `README.md`, working rules and
  `profile.json` describe only what they hold and name the companion plugin for the rest.
- **Companion-plugin mechanism.** The shared context-resolution stanza (item 3) says how a bound profile that is in
  neither the registry nor `local_profile_paths` is found: load the installed `<plugin>:profile` skill that names it
  and use the folder it gives as a local profile; with no such plugin installed, say the profile is unavailable and
  never answer its topics from memory. The stanza was rewritten to stay within the 8 KiB SKILL.md budget.
  `contracts/project.py` gains `--local DIR` to validate such a profile with the project; `docs/profile-authoring.md`
  gains a "Companion plugin" section; `tools/check_host_manifests.py` also requires the two marketplace files to list
  the same plugins.
- **Contracts 2.0.0.** The optional old-ledger identifier field is removed from `evidence_source.json` and
  `evidence_claim.json`; the ams02 ledger no longer carries it. Shipped profiles declare `contracts >=2.0,<3.0`; example outputs record the new
  versions.
- **Pre-release development records removed.** Migration guides and maps, the traceability, ledger-preservation and
  principles-coverage checks with their fixtures, the legacy analysis-spec converter and four task examples whose
  subject was the earlier development repository are gone; the remaining references, examples and tests cite this
  plugin's own files. `docs/reference-inventory.*` is regenerated. Nothing in the plugin refers to work orders or run
  logs outside it.
- **Packaging guard extended.** `tools/check_packaging.py` also rejects restricted-site facts (EOS, AFS and AMS CVMFS
  paths, lxplus node names, home folders, local hostnames, AMS Offline identifiers) and traces of the earlier
  development repository. The repository adds `.githooks/` (path allowlist on commit and push), the `guard`
  workflow (allowlist over the whole history plus a gitleaks scan) and `.gitleaks.toml` with the known false
  positives (DOIs, checksum tables, article keys).
- **Documentation.** `CHANGELOG.md` and `VALIDATION.md` restart at this release; `README.md` (plugin and repository)
  carry the install commands, the companion-plugin section, the license and the post-split package size;
  `docs/capability-matrix.md` describes the public profile only.

Earlier versions (0.1.0 to 0.2.6, 2026-10-02 to 2026-10-07) were development releases distributed from a private
repository; their notes are not part of the public record.
