# cr-propagation r4: campaign report (RC)

Work package RC of the cr-propagation r4 campaign (`workflow-r4.md` §10). For the maintainer, and as the source of the
0.43.0 release notes. Every number below comes from the state of record on the integration branch at 9b121eae:
`status.json` (work-package states, merge commits, dispatches, rework rounds, worker and verifier reports, log),
`decisions.md` (H0 D0-D12, amendment A1.1-A1.19), `escalations.md` (items 1-12), `acceptance.json` and the `CRPROP-*`
sections of `VALIDATION.md`. Where those files give no number, the report says so.

Campaign window: H0 2026-10-26 to RC 2026-10-29 (integration branch `worktree-crprop-integration` from `main`
8fcbb826, release 0.42.0; `main` has not moved since).

WAVE6-RESULT: <pending>

This line is for the final confirmation run after the wave-6 fixes. The wave-6 run itself (on 6f377150) failed
twice; see §2 and §6.

## 1. Summary

**Work packages.** 20 of 24 merged: P0, ENV, A1, A1R, A2, A3, A4, B1, B1X, B2, B3, C1, C2, C2U, C2UF, D1, D3, E1, E2,
F1. Not merged:

- D2 (GALPROP, optional): `unavailable`, its manifest fallback. No GALPROP v57 source was obtainable (no reachable
  host, no tarball; A1.2) and escalation 2 was decided that way at RC (A1.19). D3 compared DRAGON2 and USINE only.
- F2 (optional cross-code redo of F1): `skipped` by orchestrator decision A1.18. F1 reached no converged fit to extend,
  and the campaign was near the 6000-evaluation cap.
- F3 (v1 changes, conditional on F1, D11): `skipped` by its own condition (F1-1 not passed, A1.17); listed for H1.
- RC: this work package.

**Outcome per r3 definition-of-done item** (`cr-propagation-plan.md` line 83):

| # | r3 item | Outcome | Evidence |
|---|---|---|---|
| 1 | At least two propagation codes and the closed form produce `prediction` artifacts through one provider protocol and are interchangeable inside one likelihood | Met, with one limit: closed form (C1), USINE (B1) and DRAGON2 (D1) all serve `cr-provider/1` and pass C1's conformance checks (B1-PRV, D1-PRV; also the emulator, E2-PRV). The same `propagation_fit.py` likelihood ran with the closed form (C2), USINE (C2U, C2UF, F1) and the USINE emulator (C2UF). No fit with the DRAGON2 provider is recorded. GALPROP is absent | C1-1..7, B1-PRV-1/2, D1-PRV-1/2, C2-1, C2U-1 |
| 2 | Multi-dataset global fits of secondary/primary ratios and clocks are in v1 (shared LIS, modulation per period, cross-section nuisances, covariance alternatives) | Not met as v1. The tools exist on integration: multi-dataset fits with component multipliers and covariance alternatives (C2), B/C plus 10Be/9Be with USINE (C2UF), a force-field potential per data period and cross-section nuisances with priors (F1, provider-side modulation, see §8). v1 needs F3, which was skipped | C2, C2UF-1, F1 |
| 3 | Every fit result carries object-form `degenerate_directions` and lists every surviving model family | Met for the fits that test it: object-form entries with evidence and `valid_range` (C2-4, contracts 3.14.0 rules from A2), families listed with toy-calibrated delta chi2 (C2-3, C2UF-1). Not re-checked at RC for F1's records | A2-2..5, C2-3, C2-4, C2UF-1 |
| 4 | At least one published result reproduced from public data with the original code, within the user-confirmed tolerance | Not met. F1 is a partial reproduction of Génolini et al. 2019 with USINE: delta and K10 lie in the paper's 1-sigma windows for BIG, SLIM and the declared variant QUAINT-Vc0, but no fit reaches the convergence verdict (A1.17) | F1-1 (VALIDATION CRPROP-F1) |
| 5 | With consent, the capability map lists secondary-nucleus propagation fits as `v1: true` | Not done: F3 skipped; the paid live routing run was never consented (D3, D11) | A1.18 |

**r4 definition of done** (`workflow-r4.md` line 48): item 1 holds (every non-optional WP merged, F3 skipped through
its fallback); item 2 is the wave-6 and RC check run (placeholder above); items 3 and 4 are this report and
`pr-draft.md`; item 5 did not hold strictly: the maintainer decided A1.1-A1.15 during the run (see §6).

## 2. Work packages

Verifier model as stated in `status.json`; "not stated" where the report names none. Rework rounds count the
wave-run fix branches (§6).

| WP | State | Merge commit | Dispatches | Rework rounds | Verifier (model): verdict |
|---|---|---|---|---|---|
| P0 | merged | 21e18305 (round 3) | 1 | 3 | rounds 0-2 REWORK (not stated); round 3 (Sonnet): PASS |
| ENV | merged | 7d5c6934 (dispatch 1), cbb7907f (dispatch 2) | 2 | 0 | dispatch 1 (not stated): PASS; dispatch 2 (Sonnet): PASS |
| A1 | merged | 5d5fd918 | 1 | 0 | Opus: PASS |
| A1R | merged | 18b43b34; fix a634e747 | 1 | 1 | Opus: PASS; wave-3 fix (Sonnet): PASS |
| A2 | merged | a3c880f8 | 1 | 0 | Sonnet: PASS |
| A3 | merged | f62f70e8 | 2 | 0 | Sonnet: PASS |
| A4 | merged | 0ee4c914 | 1 | 0 | Sonnet: PASS |
| B1 | merged | 3ed1e89e | 1 | 0 | Opus: PASS |
| B1X | merged | 2360c294 | 1 | 0 | Opus: PASS |
| B2 | merged | 81cb2ce0 | 2 | 0 | Opus: PASS |
| B3 | merged | c1b5967d | 1 | 1 | round 0 (not stated): REWORK; round 1 (Opus): PASS |
| C1 | merged | 099d1d22 | 1 | 1 | round 0 (not stated): REWORK; round 1 (Sonnet): PASS |
| C2 | merged | 9f17775c | 1 | 0 | Opus: PASS |
| C2U | merged | 886bb316 | 1 | 0 | Opus: PASS on C2U-1/2 (C2U-3 moved, A1.12) |
| C2UF | merged | dee1179b | 2 | 0 | Opus: PASS |
| D1 | merged | e44377f4 | 2 | 0 | Opus: PASS under A1.11 |
| D2 | unavailable | — | 0 | 0 | — (missing `env-galprop`) |
| D3 | merged | 6a332c90; fix 310bb517 | 1 | 1 | Opus: PASS under A1.13; wave-5 fix (Sonnet): PASS |
| E1 | merged | a4ad05d3; fix 63e7c1b2 | 1 | 1 | Sonnet: PASS; wave-3 fix (Sonnet): PASS |
| E2 | merged | c28d960c; fix bc6f314f | 1 | 1 | Opus: PASS; wave-4 fix (Sonnet): PASS |
| F1 | merged | 3ccaa643 | 2 | 0 | Opus: PASS under A1.17 |
| F2 | skipped | — | 0 | 0 | — (A1.18) |
| F3 | skipped | — | 0 | 0 | — (A1.18, condition false) |
| RC | dispatched | — | — | — | this work package |

All 25 merges have a post-merge static result (static part of `run_all_checks.py`, with `workflow_check.py
acceptance`) in the record. For 20 of them the log said "post-merge static ok" at merge time. For A1R 18b43b34, D1
e44377f4, E2 fix bc6f314f, D3 fix 310bb517 and F1 3ccaa643, the log entry at merge time did not give it; the results
(all exit 0) were taken from the orchestrator's merge logs and added to the record later (log entry "record gap
filled ...", 2026-10-29). ALL-3 (full `run_all_checks.py` and `check_relocation.py`) ran once per wave on the
integration HEAD (A1.5):

| Wave run | WPs covered | Result |
|---|---|---|
| 1, on 566bfd1e | ENV 1, A2, A1, C1, B2 | 1 failure (later full runs passed this test): `tests.tools.test_run_all_checks` timing coverage (49 modules without timing, limit 47), cumulative from new campaign test modules; fixed by adding 6 measured modules to `tools/module_timings.json`. Relocation: only the 2 known geant4 path-with-spaces failures |
| 2, on 2d451e87 | P0 r3, ENV 2, A3, A4, B1 | pass; relocation only the 2 known geant4 failures (identical on `main`) |
| 3, on a4211583 | C2, B3, E1, A1R | 2 failures: A1R (Th13 phrase test), E1 (subprocess calls without timeout); fixed on fix branches, confirmed by wave 4 |
| 4, on 6ecc1ffa | B1X, D1, E2, wave-3 fixes | wave-3 fixes confirmed; 1 failure: E2 (`train_emulator.py` lacked `--status`, CLI contract); fixed, confirmed by wave 5 |
| 5, on 03cfca5d | C2U, D3, E2 fix | E2 fix confirmed; 1 failure: D3 (`d3_study.py:285` subprocess without timeout); fixed, confirmed by wave 6 (its subprocess-timeout test listed only the F1 line) |
| 6, on 6f377150 | D3 fix, C2UF, F1 | FAIL, 2 failures: routing-table budget, hep-statistics `SKILL.md` + `core-stats-guide.md` 25688 > 25600 B (C2UF, 7d997d02); `test_cr_propagation.py:2269` subprocess without timeout (F1). Relocation: the same two. Both being fixed on fix branches (rework round 1); final confirmation run: WAVE6-RESULT above |

## 3. Acceptance results per merged WP

One line per entry; evidence from the verifier reports in `status.json` and the WP's `VALIDATION.md` section. The
common entries hold for every merged WP unless noted: ALL-1 (environment field in the WP's VALIDATION section), ALL-2
(`workflow_check.py acceptance` ok), ALL-4 to ALL-6 (naming, layering and scope, no run output or home path; checked
by the worker and the verifier), ALL-3 (the wave run of §2), ALL-7 (judged by the verifier; C1's verifier recorded it
not-run, F1's was checked by the orchestrator).

**P0.** WF-1 pass (`workflow_check.py dag` ok: 21 WPs, 9 capabilities, acyclic). WF-2 pass (frozen sha256 recorded in
VALIDATION CRPROP-ACCEPTANCE). Round 3 (A1.6): `--no-renames` in `check_diff`, regression test fails 2/3 without the
fix and passes 3/3 with it; hole reproduced and closed in a scratch clone by the verifier.

**ENV.** ENV-1 pass (all 9 capabilities in `capabilities.json` with evidence). ENV-2 pass (DRAGON2 and USINE
computational-runs and environment manifests under `tests/adapters/fixtures/cr_propagation/env/`). ENV-3 pass
(E-crprop registered). USINE V3.5 fb53006d (GPL-2.0) built; `usine -tUSINE` 42/46, the 4 differences text or last
digit only (verifier).

**A1.** A1-1 pass (round trips within 1e-12). A1-2 pass (3.01720e29 cm^2/s). A1-3 pass (table parsed row by row).
A1-4 pass (breaks never `exact`). A1-5 pass (V_A zones `approximate`). A1-6 pass (structure; schema test passes after
A2: 29 tests, 0 skipped).

**A1R.** A1R-1 pass (`dragon2` = D0 beta^etaT (rho/DiffRefRig)^delta, cd588707 `diffusion.cc:150`). A1R-2 pass
(verifier's independent derivation: V_A,disc = V_A,halo sqrt(L/(3h)) at first order, bound (1+lam)/5; DRAGON2
Ptuskin94 = 3/4 of USINE's D_pp). A1R-3 pass (round trips within 1e-12).

**A2.** A2-1 pass (every committed theory-spec same result before and after; 1213 contract tests). A2-2 pass (three
negative fixtures, one code each). A2-3, A2-4, A2-5 pass (object-only list, tabulated-grid equivalence, gating from
`CRPROP_FROM` = 3.14.0).

**A3.** A3-1 pass (161/161 tabulated-grid output hashes equal the baseline; reproduced by the verifier on f747fbe7).
A3-2 pass (`valid_range.L_kpc.max` 6.947, in [6, 8]). A3-3 pass. A3-4 pass.

**A4.** A4-1 pass (every cost number traced to 13 validated run records). A4-2 pass (closed-form and DRAGON2 rows;
USINE row added by B1, GALPROP not measured).

**B1.** B1-1 pass (43 offline tests). B1-2 pass (seven recorded runs rerun live; reader vs USINE tables within
7.8e-6). B1-3 pass (V3.5, fb53006d, Apple clang 21.0.0, ROOT 6.38.04; USINE `tested-in-declared-environment`). B1-4
pass. B1-PRV-1 pass (9/9 conformance checks live). B1-PRV-2 pass.

**B1X.** B1X-1 pass (high-break fixtures exercised). B1X-2 pass (`init.TEST.par` reproduced on 33/33 nodes, deviation
0). B1X-3 pass (USINE's own XS files read in place). B1X-4 pass (field-by-field map confirmed by the verifier). B1X-5
pass (545 USINE files hashed, no match in the repo).

**B2.** B2-1 pass (pure-diffusion limits, symbolic and numerical). B2-2 pass (13 dimension checks). B2-3 pass (58
profile tests). Verifier's own finite-volume solver agrees to 2e-8.

**B3.** B3-1 failed under harmonized-v1 (2D B/C to 2.47% above 45 GV), superseded (A1.10). B3-1a pass (B/C 9e-5,
10Be/9Be 4.1e-4; tolerance 2%). B3-1b reported and attributed (radial escape; product of ratios 1 within 1e-3).
B3-1c pass (0.21% / 0.16% against Fourier-Bessel; tolerance 0.5%). B3-2 pass (max 8.9e-6; tolerance 0.5%). B3-3
written (22 rows).

**C1.** C1-1 to C1-7 pass (registry refusal, single-shot/serve equality, cache hit without a call, crash reported,
out-of-domain, hash equality on 10 objects, tool contract and no path string). Round-0 blocking finding (inherited
conformance cache) fixed in round 1.

**C2.** C2-1 pass (Asimov within 0.1 sigma, boundary case included). C2-2 pass (coverage 0.686 / 0.671 / 0.696 in the
Bonferroni band; verifier's independent 200-toy rerun 0.690 / 0.680 / 0.675). C2-3 pass (BIG, SLIM listed as not
expressible by the closed form; expressible families toy-calibrated). C2-4 pass. C2-5 pass. C2-6 pass.

**C2U.** C2U-1 pass (pulls about 4e-5 sigma; V_c on its bound with `boundary_kkt` and profile). C2U-2 pass (565
records resolved, USINE V3.5 fb53006d). C2U-3 not met (response model 2.81 sigma off), moved to C2UF-1 (A1.12).

**C2UF.** C2UF-1 pass in dispatch 2 (A1.14): GP emulator validated at 0.0038 sigma on 40 held-out USINE runs
(tolerance 0.05); BIG survives (toy p 1.0), SLIM excluded (delta chi2 23.93, p < 0.0151), 200 toys each. Dispatch 1
had not met it (no polynomial response model reached 0.05 sigma within 600 runs).

**D1.** D1-1 failed, superseded (A1.9). D1-1a: convection pass (0.73% / 0.44% against the closed form); decay B/C
pass, 10Be/9Be fail (13.3% closed form, 11.3% USINE; finite gas layer); reacceleration fail (5.7%, within the
first-order conversion bound); losses fail (6.1%, Coulomb on HII vs ionization-only reference); the three misses
accepted as attributed (A1.11, verifier confirmed). D1-1b reported and attributed. D1-L pass (n_HII = 0 divergence,
`eloss.cc:118-120`, refused with tests). D1-2 pass. D1-PRV-1, D1-PRV-2 pass live.

**D3.** D3-1 failed (38-77% at level 1; decomposed into gas column, He target, inelastic cross sections, parent O/C,
injection convention), accepted as attributed (A1.13). D3-2 pass (level-2 residual 0.42% within 2.46%). D3-3 failed
overall (0.59-0.67% for four configurations; reacceleration 17.0%, losses pair on Galprop gas 17.7%, both
attributed), accepted (A1.13).

**E1.** E1-1 pass (64/64 design points, 111 USINE evaluations with records). E1-2 pass (forced test stops at 5
rounds). E1-3 pass (no training data committed).

**E2.** E2-1 pass (largest delta chi2 0.0045). E2-2 pass (0.063 sigma_stat). E2-3 pass (best fits within 0.002
sigma, widths within 1.2%). E2-PRV-1, E2-PRV-2 pass (offline).

**F1.** F1-1 not met (convergence only): BIG delta 0.500, K10 0.286; SLIM 0.516, 0.289; QUAINT-Vc0 0.459, 0.323, all
in the windows; no fit reaches the `fit_diagnostics` verdict; accepted as the partial reproduction F1-1 foresees
(A1.17, verifier recomputed the windows and confirmed the declared variant). F1-2 pass (data `observed`, covariance
`model-supplied`, 67 CRDB rows `secondary`).

**Not run:** D2-1, D2-2, D2-PRV-1, D2-PRV-2 (D2 unavailable); F3-1, F3-2 (F3 skipped). WF-2 to WF-10 belong to RC (§9).

## 4. Criteria changed or accepted

`acceptance.json` was never loosened: `workflow_check.py acceptance` reports `ok`, frozen sha256
`f5b0dbe61aca360e364f0df52a41bc00f27f2cfaf0ad2808e43bc4f3480b813e`, 86 frozen entries unchanged, 17 entries added
(103 in total). Every change below either adds a stricter or equivalent entry or accepts a recorded, attributed miss
of a frozen entry; the frozen entry stays in the file with its failed verdict.

| Change | Decision | Kind |
|---|---|---|
| B1X-1..B1X-5 added with the new WP B1X | A1.7 | added |
| D1-1 superseded for D1's verdict by D1-1a (item effects within 3%) and D1-1b (offsets reported); D1-L, A1R-1..3 and D3-3 added | A1.9 (D3-3 planned there, added at D3 dispatch) | added; frozen D1-1 kept, failed |
| B3-1 superseded for B3's verdict by B3-1a (matched 1D, 2%), B3-1b (2D offset reported), B3-1c (stricter: 0.5% against Fourier-Bessel) | A1.10 | added; frozen B3-1 kept, failed under harmonized-v1 |
| D1-1a misses (decay 10Be/9Be, reacceleration, losses) accepted as attributed | A1.11 | accepted miss |
| C2U-3 (added by the orchestrator on the C2 verifier's advisory) moved to C2UF-1 in the new WP C2UF | A1.12 | moved, same criterion |
| D3-1 and D3-3 misses accepted as attributed | A1.13 | accepted miss |
| F1-1 miss on convergence accepted as the partial reproduction F1-1 foresees; F3 stays disabled | A1.17 | accepted miss |

## 5. Escalations

| # | WP | Type | Handling |
|---|---|---|---|
| 1 | ENV → B1 | capability | USINE source absent. Closed 2026-10-28: maintainer allowed USINE V3.5 from gitlab.com/dmaurin/USINE (A1.1); ENV dispatch 2 built it |
| 2 | ENV → D2 | capability | No GALPROP v57 source. Decided 2026-10-29 (A1.19): D2 `unavailable`; D3 compared DRAGON2 and USINE only |
| 3 | ENV → F1 | capability | CRDB host timed out. Closed (A1.19): F1 used PRL 117 data and CRDB cross-check rows without that host |
| 4 | P0 | blocked | Rename hole in `check_diff` at the rework limit. Closed 2026-10-28: extra round authorized (A1.6), fix merged 21e18305 |
| 5 | D1 | tolerance-miss | D1-1 3% missed (He target, gas layer). Decided by A1.9 (D1-1a/b, D1-L, WP A1R, D1 dispatch 2) |
| 6 | D1 → A1 | rule-conflict | DRAGON2 row of the convention table wrong. Decided by A1.9 (WP A1R corrected it) |
| 7 | A4 → E1 | budget | Which D7 cap binds. Decided by A1.8 (cap counts external codes only; core-hours count all CPU) |
| 8 | B1 → C2U, F1 | capability | No high-break field; ILLUSTRATIVE XS only. Decided by A1.7 (WP B1X) |
| 9 | D1 → D3 | blocked | D1-1 passed 1 of 8 cases; DRAGON2 losses unphysical. Decided by A1.9 |
| 10 | A1R → B1, D1, B1X | rule-conflict (wording) | r3 P1 "about sqrt(L/h)" vs first-order sqrt(L/(3h)); DRAGON2 Ptuskin94/03 enum likely upstream bug. Translators now call `transport_conventions`. Decided (A1.19): known issue (§8) |
| 11 | D1 → D3 | tolerance-miss | D1-1a misses after dispatch 2. Decided by A1.11 (accepted with attribution; verifier still required); attribution wording corrected by the D1 verifier |
| 12 | D3 → D1, B1X, A1 | repo-mismatch | Translator gaps found by D3. Accepted for D3 under A1.13; decided (A1.19): known issue (§8) |

## 6. Process departures

- **Mid-run decisions.** r4 asks for no person between H0 and H1. The maintainer decided A1.1-A1.15 during the run, approved the USINE clone and build after the host permission check held ENV's second dispatch,
  stopped the campaign on 2026-10-27 (resumed 2026-10-28) and paused and unpaused it before RC. A1.15 (itself a mid-run
  decision) delegated H1 (push, PR, merge after the required CI jobs, release 0.43.0) to the orchestrator;
  A1.16-A1.19 are orchestrator decisions under that delegation.
- **Check execution (A1.4, then A1.5).** Workers stopped running the full checks (A1.4: the verifier ran ALL-3);
  A1.5 then moved ALL-3 to one orchestrator run per wave on the integration HEAD, with workers and verifiers running
  the static part plus impacted tests. WF-4 (static after every merge) and WF-10 (full run at RC) were unchanged.
- **Wave-run failures fixed forward.** A1.5 says a wave-run failure reverts the responsible merge. Instead, the
  failures were fixed on fix branches counted as rework round 1, verified and merged. Reasons as recorded:
  - wave 3 (A1R, E1): later merges depended on both WPs (`status.json` log[65]; the A1R note names B1X and D1, the
    E1 note says E2 builds on E1); recorded as an orchestrator departure from A1.5 for H1;
  - wave 4 (E2): "same handling as the wave-3 fixes" (E2 note);
  - wave 5 (D3): the record gives no dependency reason; the handling was consistent with waves 3 and 4;
  - wave 6 (C2UF: hep-statistics routing size budget 25688 > 25600 B; F1: `test_cr_propagation.py:2269` subprocess
    without timeout): the same handling, fix branches as rework round 1, in progress at the time of this report.
- **Limits.** P0 got a third rework round beyond the limit of 2 (A1.6). Concurrency was capped at 3 workers and 2
  full check runs (A1.3) instead of the manifest's 4 workers. `status.json` log[26] (2026-10-28) records a 4th
  worker (ENV dispatch 2) while A3 finished its check run: above A1.3's cap of 3, within r4 §4's limit of 4.
- **Budget.** The external-code evaluation cap was raised from 5000 to 6000 (A1.16); per-WP USINE caps were raised for
  C2UF (A1.14, +400) and F1 (A1.16, +600).
- **Scope widening by the orchestrator.** WP file lists were widened during the run, each recorded in the log: A2
  (version-pin regeneration, `test_grid_fit.py`), A3 and C2/C2U (`core-stats-guide.md`), E2 (one entry in
  `test_adapter_missing_dependency.py`), C2UF (E2 emulator provider, behaviour pinned unchanged), F1 (modulation and
  low break; `adapter.json` under A1.16).
- **WF-9 and F2.** F2's manifest fallback applies when E2 is skipped or blocked; E2 merged, so F2 was skipped by
  decision A1.18, not by its fallback.
- **Independent review.** r3 Q10's formal review with `review.py` was moved from P0 to before H1 (host isolation
  setting outside D3). `status.json` records no run of it.

## 7. Budget (D7, as amended by A1.8 and A1.16)

Caps: 6000 external-code evaluations (DRAGON2, USINE, GALPROP; closed-form evaluations do not count), 200
core-hours, 6 weeks of wall time.

| WP | DRAGON2 runs | USINE runs | Source |
|---|---|---|---|
| A4 | 6 completed + 1 aborted (4257 CPU-s, about 1.2 core-hours) | 0 (USINE cost row timed in B1) | VALIDATION CRPROP-A4 |
| B1 | — | about 130 | A1.8 tally (CRPROP-B1 gives no count) |
| B1X | — | about 53 (about 37 before the rebase rerun) | `status.json` B1X note; CRPROP-B1X |
| B3 | — | 192 (about 0.12 core-hours) | CRPROP-B3 |
| D1 | 30 | 0 (B1's runs reused) | CRPROP-D1 |
| D3 | 2 (plus 13 cross-section table calls, no propagation) | 37 | CRPROP-D3 |
| E1 | — | 114 (about 0.1 core-hours) | CRPROP-E1 |
| E2 | — | 177 (about 0.2 core-hours) | CRPROP-E2 |
| C2U | — | about 1372 | CRPROP-C2U |
| C2UF | — | 862 | CRPROP-C2UF |
| F1 | — | 2347 (1693 in dispatch 1; dispatch 2: 2347 - 1693 = 654, of which VALIDATION itemises 653) | CRPROP-F1 |
| **Total** | **about 39** | **about 5284** | sum of the rows |

External-code evaluations: **about 5320 of 6000**. Not tallied anywhere: ENV's DRAGON2 live rerun, USINE smoke run and
`usine -tUSINE`, and the verifiers' reruns. C2 used about 6600 closed-form evaluations, which do not count (A1.8).

Core-hours: A1.16 records **about 8 core-hours** used when F1's dispatch 2 was decided. F1's dispatch-2 runs (654 by difference, 653
itemised) came after that estimate (its noise probes took 7.8-8.9 s per run); no WP gives a core-hour total for C2U, C2UF, D1, D3 or
F1, so the campaign total is not stated in the record. It is above 8 and, at the per-run times reported (USINE about
1-20 s per run: E1 about 1-3 s, B3 about 2.4 s, D3 2-20 s, F1 probes 7.8-8.9 s; DRAGON2 about 125-221 CPU-s at the A4 grid), far below 200. Wall time: 4 days of 6 weeks.

## 8. Known issues and future work (for the release notes)

1. **Escalation 10.** r3 P1's "about sqrt(L/h)" for the thin-disc/whole-halo V_A conversion is wrong at first order
   (sqrt(L/(3h)) with bound (1+lam)/5, A1R); the plan's wording is not amended. DRAGON2 cd588707 applies the 4/3 D_pp
   factor to the enum value of Ptuskin03, so Ptuskin94 gives 3/4 of USINE's D_pp: likely an upstream bug, not
   reported upstream.
2. **Escalation 12.** `dragon2_run.spec_from_transport` does not translate or record `sources.abundances` (DRAGON2
   BaseModel O/C 1.21 vs 0.9, x1.10 on B/C); harmonized-v1 and both translators leave the injection variable unstated
   (momentum vs E_k/n, up to 3% on B/C at 2-3 GV); `usine_translate._gas` sets a gas term written without cm^-3 to 0
   with only a substitute note. Follow-up: translators refuse or record these; clarify harmonized-v1.
3. **F1 convergence floor.** No F1 fit reaches the `fit_diagnostics` verdict (EDM <= 1e-5): USINE prints 6-digit
   output tables, giving about ±0.0005 to ±0.003 noise in -2 ln L; tighter USINE tolerances change no output digit.
   The criterion was not loosened.
4. **F1 chi2 gap.** -2 ln L about 83-90 against the paper's about 62. Attributed but not testable here: the paper's
   data file is not shipped (PRL 117 values used), USINE V3.4 vs V3.5, C/N/O source normalisation (HEAO-3 vs AMS-02).
5. **Provider-side modulation.** F1's USINE provider applies the force-field potential per data period (USINE
   SolMod0DFF per isotope), against `cr_provider.json`'s "providers never modulate". The departure is recorded in
   every modulated prediction (2328 cached predictions per the F1 verifier); the protocol is not amended.
6. **C2UF advisory.** The toy fits are bounded by the emulator's k = 4 domain, while the emulator was validated over
   the k = 3 box (shell point 0.0187 sigma); the amendments were tuned on the same toy seeds.
7. **`propagation_fit` reason for unconverged fits.** An unconverged fit carries the reason "artifact-invalid",
   which does not name the cause; listed as a follow-up by the F1 verifier.
8. **Polish.** With polish enabled, the fit keeps `t_hat` from before the polish while the verdict describes the
   polished point. Polish is off by default (F1 verifier).
9. **GALPROP not available.** D2 unavailable; `adapter.json` keeps GALPROP `proposed` with no tested version, so the
   `cr-propagation` adapter stays `proposed` (its status rule).
10. **F2 and F3 not done.** No cross-code redo of F1, no v1 change; the paid live routing run was never consented.
11. **DRAGON2 upstream issue draft** (energy-loss divergence at n_HII = 0, D1-L) is kept outside the repository,
    unposted (A1.15, A1.19).
12. **Release.** Plugin 0.43.0 makes contracts 3.14.0 and core 1.2.0 official (A1.15); until the release they are the
    campaign's unreleased bumps.
13. **Accepted DRAGON2/USINE misses.** D1-1a item effects (A1.11): 10Be/9Be with decay 11-13% below 1 GeV/n
    (DRAGON2's finite gas layer vs thin-disc references), reacceleration 5.7% on B/C (within the first-order zone
    conversion bound), losses 6.1% on B/C (DRAGON2 Coulomb loss on HII vs USINE's ionization-only reference). D3-1:
    38-77% at level 1 (decomposed). D3-3: reacceleration 17.0%, losses pair on Galprop gas 17.7% (A1.13). Caveats of
    escalation 11 (D1 verifier): the second-order reacceleration term was not estimated, and the losses attribution
    was not quantified (the neutral column likely contributes as much as Coulomb on HII); the thick-gas diagnostic
    agrees within about 1% only in bins 3-5.
14. **adapter.json and A1.11.** A1.11 asked that `adapter.json` record the DRAGON2 provider as tested with these known
    differences; it does not (the D1 verifier also noted this). Open, for follow-up; not edited in this campaign.
15. **B3 sign error in VALIDATION.** The B3-1b attribution paragraph of VALIDATION CRPROP-B3 gives USINE 2D / USINE 1D
    for 10Be/9Be as "up to -1.3%"; per the B3 verifier it is +1.3%. VALIDATION is append-only, so B3's section is
    not edited.
16. **Other verifier advisories** (recorded, not re-checked at RC):
    - C2U: the P2 statement is found by regex (a negation would pass); `transport_substitutes` exempted from the gate
      (to be stated as conditions for F1); `kkt` docstring; budget checked before the cache.
    - B1X: nested break and injection fields are not in the field loop; the canonical parameter table lacks the new
      names.
    - A1: USINE smooth-break form not re-read from Weinrich 2020a; n_H only as text; source spatial distribution left
      open; He-target and ghost treatment vs `xs-illustrative-A`.
    - C1 (worker's open items; the verifier recorded ALL-7 not-run): the closed-form provider gives bin-averaged
      ratios, not P2 bin integrals; profile README and index not updated.
    - B2: stale function name in the derivation script (line 164); resonant case refused; `R0_GV`/`h_kpc` kept
      beside canonical `V_c_kms`; profile version not bumped.
    - D1: `--spec` path does not refuse BronfFerr losses.
17. **Open texts for the maintainer.** The en/zh differences of r3 and r4 listed in `decisions.md` are not resolved;
    r3 Q10's independent review has not run (§6).

## 9. Workflow criteria (RC's entries)

| Entry | Status at RC | Evidence |
|---|---|---|
| WF-2 | holds | `workflow_check.py acceptance` ok, frozen sha256 f5b0dbe6…, 86 frozen entries, 17 added |
| WF-3 | holds | every merged WP has a verifier PASS in `status.json`; verifiers were separate agents from the workers |
| WF-4 | static clause holds; revert clause missed (fixed forward, §6) | all 25 merges have a post-merge static result (exit 0); 5 of them (A1R, D1, E2 fix, D3 fix, F1) were taken from the orchestrator's merge logs and added to the record later (§2); wave-run failures fixed forward instead of reverted |
| WF-5 | holds | `status.json` and the other orchestrator-only files are checked by `workflow_check.py diff` on every WP branch |
| WF-6 | missed, accepted (A1.6: P0 rework round 3) | P0 hit the rework limit (escalation 4) and got one authorized extra round; D1, at its limits, was escalated (9, 11); no WP used more than 2 dispatches |
| WF-7 | person clause missed | maintainer decisions A1.1-A1.15, the USINE clone approval and the pause and its cancellation were asked during the run (§6); nothing pushed, `main` unchanged, no pull request |
| WF-8 | holds (natural test) | the campaign stopped on 2026-10-27 with WPs dispatched and resumed on 2026-10-28 ("resumption check ok: 6 worktrees, HEADs as recorded"); each was merged once |
| WF-9 | capability clause holds; fallback clause missed, accepted (A1.18: F2 skipped by decision) | no WP was dispatched without its capabilities (B1, B3, C2U waited for `env-usine`; D2 never dispatched); F2's manifest fallback did not apply (§6) |
| WF-10 | pending | wave 6 failed twice (§2), fixes in progress; final confirmation run: WAVE6-RESULT above; `main` has not moved, so no rebase was needed |

## 10. For H1 (delegated to the orchestrator, A1.15)

Merge the integration branch into `main` after the required CI jobs pass, push, release 0.43.0 with contracts 3.14.0
and core 1.2.0, and carry §8 into the release notes. Not delegated and not done: the paid live routing run, any post
to a third-party upstream, and the v1 capability change (F3).
