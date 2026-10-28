# PR draft: cr-propagation campaign into main (release 0.43.0)

Draft for the H1 pull request that merges `worktree-crprop-integration` into `main` (decision A1.15). The title and
body below are meant to be pasted as they stand. The orchestrator fills the check results after the wave-6 run and the
CI run.

## Title

hep-research 0.43.0: cosmic-ray propagation fits with USINE, DRAGON2 and the closed form (cr-propagation r4)

## Body

### Summary

This PR merges the cr-propagation r4 campaign (2026-10-26 to 2026-10-29): 20 of 24 work packages merged, each with a
verifier PASS. The plugin can now run propagation predictions of secondary-to-primary ratios and radioactive clocks
from USINE V3.5, DRAGON2 cd588707 and the closed-form thin-disc model through one subprocess provider protocol, fit
them to several datasets in one likelihood, report object-form degeneracies with their valid ranges, and compare
model families with toy-calibrated delta chi2. The reproduction of Génolini et al. 2019 with USINE is partial (see
Known issues), so the capability map is unchanged (no `v1: true`).

Versions: plugin 0.43.0; contracts 3.14.0 (one minor, new rules gated by `CRPROP_FROM`; every committed artifact keeps
its outcome); core 1.2.0 (new `core/provider/`).

Full report: `plugins/hep-research/docs/dev/cr-propagation/campaign-report.md`
(work-package table, per-entry acceptance results, criteria changed or accepted, escalations, budget).

### User-visible changes (grouped from the CHANGELOG `crprop` entries)

**Contracts and core**
- `extension.transport` block for theory-specs in canonical parameter names, with low and high diffusion breaks,
  local bubble and source eta (crprop a2, b1x); object-form `degenerate_directions` with evidence and valid range,
  and new error codes from `CRPROP_FROM` (a2, b1x).
- Provider protocol `cr-provider/1`: schema `contracts/schemas/cr_provider.json`, `core/provider/` (registry passed by
  the caller, point-hash cache, refusals with reasons, conformance checks), `tools/provider_registry.py`, the
  `provider` field of profiles and adapters, force-field tool contract (c1).

**hep-theory**
- `transport_conventions.py`: diffusion conventions of GALPROP, USINE and DRAGON2 (corrected from the codes'
  sources), reacceleration conversions with stated exactness and error bounds (a1, a1r).
- `theory:cr-secondary-ratio`: closed forms with convection and radioactive decay, SymPy derivation record, and the
  closed-form provider (b2, c1).

**hep-statistics**
- `degeneracy.py`: Fisher screen and profile-likelihood scans with object-form degeneracy entries; optional
  `degeneracy_scan` in `covariance_fit.py` (a3).
- `propagation_fit.py`: multi-dataset fits through any `cr-provider/1` provider, bin-semantics guard, component
  multipliers, covariance alternatives, `boundary_kkt` verdicts, toys and toy-calibrated family comparison, response
  models (polynomial, provider), per-point provider requests, parameter priors, data periods with a force-field
  potential, optional polish; examples `examples/propagation-fit/` and `examples/bc-usine-reproduction` (c2, c2u, c2uf,
  f1).

**hep-ml**
- `train_emulator.py`: Gaussian-process emulator with a domain model; `write_ml_artifact.py` copies the validation
  block; emulator provider `emulator` (e2, c2uf).

**adapters/cr-propagation (0.2.0)**
- USINE V3.5: translator (own cross-section files read in place, never copied; GPL-2.0 kept outside the repo), reader
  to ratios of bin integrals, provider `usine` (b1, b1x, f1).
- DRAGON2: translator from a transport block, bin-integral reader, provider `dragon2`; energy losses refused on gas
  without HII (d1).
- Studies with recorded runs: USINE vs closed forms (b3), DRAGON2 vs USINE at two levels (d3), training design and
  active addition (e1), cost table in VALIDATION CRPROP-COST (a4). Environment E-crprop registered (env).

**Development**
- `workflow_check.py diff` sees renames (p0); campaign documents under `docs/dev/cr-propagation/`.

### Check results

- Waves 1-5 (full `run_all_checks.py` and `check_relocation.py` once per wave): each failure was fixed on a fix
  branch, and the fixes of waves 1-4 were confirmed by later full runs. The wave-5 D3 fix was confirmed by wave 6's
  subprocess-timeout test, which listed only the F1 line. `check_relocation.py` otherwise shows only the 2 known
  geant4 path-with-spaces failures, identical on `main`.
- Wave 6 (6f377150) was one run with two failures: the hep-statistics routing size budget, 25688 > 25600 B (C2UF), and a subprocess
  call without a timeout in `test_cr_propagation.py:2269` (F1). Both were fixed on fix branches (rework round 1, Sonnet PASS, merged).
- Final confirmation run after the wave-6 fixes: final confirmation run on the release commit 790ef3e7 (after the wave-6 fixes and the 0.43.0 bump): full `run_all_checks.py --no-cli --jobs 4` passes in E2 (31 pass, 0 fail, 2 skipped CLI host checks; 6000 tests in 480 modules, 0 failures, 168 skipped) and with the CI lock (31 pass, 0 fail, 2 skipped; 6000 tests, 0 failures, 263 skipped); `check_relocation.py` shows only the 2 known geant4 path-with-spaces failures, identical on `main`.
- Required CI jobs: <pending>

### Known issues

- F1 reproduces Génolini et al. 2019 only partially: delta and K10 lie in the paper's 1-sigma windows for BIG, SLIM
  and QUAINT-Vc0, but no fit converges at USINE's 6-digit output noise floor, and -2 ln L is about 83-90 against the
  paper's about 62 (attributed: data file, USINE V3.4 vs V3.5, C/N/O normalisation). The convergence criterion was not
  loosened.
- The USINE provider applies solar modulation itself, against `cr_provider.json`'s "providers never modulate"; the
  departure is recorded in every modulated prediction.
- Accepted, attributed DRAGON2/USINE differences: D1-1a item effects (10Be/9Be with decay 11-13%, gas layer;
  reacceleration 5.7%; losses 6.1%), D3-1 (38-77% at level 1), D3-3 (reacceleration 17.0%, losses on Galprop gas
  17.7%). The second-order reacceleration term was not estimated and the losses attribution was not quantified.
- `adapter.json` does not yet record the DRAGON2 provider as tested with these known differences, as A1.11 asked
  (follow-up).
- VALIDATION CRPROP-B3 gives the USINE 2D/1D 10Be/9Be offset as "-1.3%"; per the B3 verifier it is +1.3%. The
  history is append-only, so the section is not edited.
- C2UF's toy fits are bounded by the emulator's k = 4 domain while validation covered k = 3.
- `propagation_fit.py` reports unconverged fits with reason "artifact-invalid"; with polish enabled it keeps `t_hat`
  while the verdict describes the polished point (polish is off by default).
- Translator gaps (escalation 12): abundances and the injection variable not recorded by the DRAGON2 translator, a
  unitless USINE gas term set to 0. The r3 P1 wording of the V_A zone conversion and a likely DRAGON2 Ptuskin94/03
  enum bug (escalation 10) are left for follow-up.
- GALPROP is not available (D2 unavailable); the adapter stays `proposed`.
- Not done: F2 (cross-code redo of F1), F3 (v1 change) and the paid live routing run, which was never consented.
- The DRAGON2 upstream issue draft is kept outside the repository and was not posted.

- Other verifier advisories (C2U, B1X, A1, C1, B2, D1) are listed in the campaign report, §8.

### Unfinished items

- r3 Q10 independent review with `review.py` not run.
- English/Chinese differences of the plan texts listed in `decisions.md`, unresolved.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
