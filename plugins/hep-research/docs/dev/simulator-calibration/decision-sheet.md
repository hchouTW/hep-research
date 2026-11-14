# Decision sheet for the author: `simulator-calibration-v7.37.4-clean-en.md`

Sources: the triage tags in the spec (Appendix D entries D1–D87 and the §19 bullets), `triage.md` (classes, readings, options), the computation reports `compute-*.md`, `research-D28.md`, `g4sim-binding-check.md`, `g4sim-S7-check.md` and `g4sim-S8-S9-check.md`, and `apply-computations-verify.md`, `accept-s7-verify.md`, `d28-verify.md` and `d28-s89-verify.md`. **Rebuilt from the markers of the spec after the verification of the acceptance and S7 passes and the computation of §19-g9** (Appendix E items 455–484 of the spec): the class-1 items except D68, and the merged D13 and D64, are marked "accepted 2026-11-09"; §19-g4c is counted as an author decision (its tag records the reclassification in the S7 pass); §19-g9 now has a computed rule; D83 and D84 are listed. **Updated after the D28 revision of 2026-11-09** (Appendix E items 485–516, `research-D28.md`): D28 is marked revised, D85 (open points of that revision) is listed, and the D28 event interval leaves (b′), because the author adopted it with the revision. **Updated after the verification of the D28 revision** (Appendix E items 517–543, `d28-verify.md`): no item changes class or status; three new choices of that pass inside D28 are tagged "(new choice of the D28 verification, …; to be confirmed by the author)" and listed as (b″). **Updated after the g4sim S8 and S9 check** (Appendix E items 544–592, `g4sim-S8-S9-check.md`, hep-research v0.65.0): two new entries, D86 (model identity of alignment overlays and condition snapshots) and D87 (statistical roles of conditions and alignment), not triaged, whose proposals are written in place in §5.1 and §11.4 with the tag "(proposed, to be confirmed by the author; D86)" or "(…; D87)"; six new plugin-source rules tagged "(settled by plugin source, en/g4sim-S8-S9-check.md; to be confirmed by the author)", listed under (b′); a second route for the PDE split of §19-g4c; D83 extended by items (7)–(19). **Updated after the verification of the D28 fixes and S8/S9** (Appendix E items 593–618, `d28-s89-verify.md`): no item changes class or status; two new plugin-source rules (the same digitization path within an ensemble, and every digitization job built from and checked against the hashed documents) are tagged "(settled by plugin source, en/g4sim-S8-S9-check.md; to be confirmed by the author)" and listed under (b′); the job check and the (b″) joint-replica check are corrected; the D86 list of places that say "five" gains §5.2. **Updated after the author's decision of 2026-11-09 on the fixed-map mode** (Appendix E items 619–636, "Author decision of 2026-11-09 (fixed-map mode)"): the M1 note under (b′) is decided ("the fixed-map mode need not keep the linear construction"); the decided rule of §6.7 begins "**Decided by the author (2026-11-09).**"; the M1 rule under (b′) keeps only its k/n centre, still tagged, so the number of (b′) rules does not change; the M1 row of "Still open after computation" is removed. The second part of the same decision (research on the second PDE-split route of §19-g4c) is being done separately; §19-g4c stays an open author decision. No item of the 118 changes class or status. **Updated after the author's acceptance of 2026-11-09 of (b′), (b″), D86 and D87** (Appendix E items 637–691, "Author's acceptance of 2026-11-09 (plugin-source rules, D28 choices, D86, D87)"; given in Chinese, translation "I agree to adopt them"): the 24 plugin-source rules of (b′) and the 3 choices of (b″) are marked "accepted 2026-11-09", and their tags in the spec now read "(accepted by the author, 2026-11-09; source en/…)"; D86 and D87 are accepted and move from "Other" to the accepted items (new subsection (d′) of phase 3); the open part of D31 (the response-layer requirement, a (b′) rule) is thereby closed, and its row leaves "Still open after computation", while D31 stays a plugin fact; D37 stays open (D87 uses its criterion without deciding it). **Updated after the author's decision of 2026-11-10 on the PDE split** (this update was made by the preparation of the task package `simcal-task`, not by the author; the author's copy as supplied is `decision-sheet.before-2026-11-10.md`) (Appendix E items 692–726, "Author decision of 2026-11-10 (PDE split)"; given in Chinese, translation "Adopt in principle: route 2, route 3 when the PDE depends on wavelength, and a mandatory comparison with a nominal-PDE mapping run. Before writing, check the Geant4 `DielectricMetal` branch, revise the text on the four points, and then send it to independent verification."): §19-g4c is decided and begins "**Decided by the author (2026-11-10).**"; the rules are in §6.7 "PDE split"; the (a) count drops from 7 to 6; no other item changes class or status. Item names: "D n" is the Appendix D entry, and "§19-…" is the `triage.md` row name of a §19 bullet. Every count below is checked by script against the spec's tags.

## Header

**Status: 48 of the 118 items are accepted (44 class-1 items, D28 as revised on 2026-11-09 among them, the merged D13 and D64, and D86 and D87, not triaged), 1 is decided by the author (§19-g4c, 2026-11-10), and 69 are not.** The 69 are 6 author decisions (a), 10 items with rules settled by computation (b), 25 "accept?" readings (c), D68 (class 1, excluded from the instruction), and 27 others (8 plugin facts, 13 deferred items, 1 compute item still running, and D81–D85, not triaged). In addition, the 24 plugin-source rules (b′: 16 of the binding and S7 checks and 8 of the S8/S9 check; 23 in phase 3, 1 in phase 4) and the 3 choices of the D28 verification in phase 3 (b″) were accepted by the author on 2026-11-09; they belong to items counted above, and none awaits confirmation. One rule outside the 118 items is decided: U in the fixed-map mode (§6.7, the M1 note; decided by the author on 2026-11-09). The PDE split of §6.7 (§19-g4c) is decided by the author on 2026-11-10.

**Before phases 0–1 you need to look at 5 items: (a) 0 + (b) 0 + (c) 5.** Nothing else blocks phases 0–1: their class-1 items were accepted on 2026-11-09.

- (a) Author decisions: none block phase 0 or 1. Six block phase 2. §19-g4c, which blocked phase 3, was decided on 2026-11-10.
- (b) Rules settled by computation and awaiting confirmation: none are coded in phase 0 or 1.
- (c) "Accept?" readings: D5 and D11 (phase 0), D37, D41 and D42 (phase 1).
- (d) covered 18 class-1 proposals for phases 0–1, plus the merges D13 and D64. **All are accepted (2026-11-09)** by the blanket instruction below. Phase 1 also has one plugin fact to note: §19-g2. g4sim has no design-point generator, so `calib_design.py` generates the Sobol points (D80).

**Blanket instruction for (d), given by the author on 2026-11-09 and applied:** "Accept all class-1 proposals as `triage.md` writes them, and the merges D13 → D63 and D64 → D22, except D68: I will decide its denominator together with §19-14.1f and D3."

- D7 and D26 are already in the body (D7 was settled by computation, and D26 lists corrections made). Accepting them confirmed what is there (marker only).
- D76 takes the "move to phase 2" option (applied in §8.7).
- D68 stays open, to be decided with §19-14.1f (b) and D3 (c).

**Counts by the earliest §17 phase blocked**

| Phase | (a) decide | (b) confirm computed rule | (c) accept? | (d) accepted 2026-11-09 (class 1; d′: D86, D87) | (d) still open | Other (plugin fact, defer, compute, not triaged) | Items |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 0 | 0 | 0 | 2 | 14 (+2 merged) | 0 | 0 | 18 |
| 1 | 0 | 0 | 3 | 4 | 0 | 1 | 8 |
| 2 | 6 | 7 | 19 | 19 | 1 (D68) | 2 | 54 |
| 3 | 0 (§19-g4c decided 2026-11-10) | 1 | 0 | 4 (+2 d′) | 0 | 12 | 20 |
| 4 | 0 | 0 | 0 | 0 | 0 | 5 | 5 |
| 5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| none | 0 | 2 | 1 | 3 | 0 | 7 | 13 |
| **Total** | **6** (+1 decided) | **10** | **25** | **44 (+2 merged, +2 d′)** | **1** | **27** | **118** |

The 118 items are the 87 entries of Appendix D and the 31 triage rows of §19. The 24 (b′) rules and 3 (b″) choices, all accepted 2026-11-09, are not items and are not counted in the table (formerly shown as "+ 23 / + 1 plugin-source rules, b′" and "+ 3 D28-verification choices, b″" in the (b) column of phases 3 and 4).

**Placement rule.** An item sits at the phase given by its triage tag, with one exception. A (b) rule sits at the phase whose deliverable codes it, because the rule now has to be implemented. The tags of §19-2, §19-3 and §19-13 ("blocks no phase") predate their rules, so these three sit at phase 2, with the tag noted.

**Tie-ins to decide together:**

- D50 with §19-14.1a.
- D3 with §19-14.1f and D68.
- D47 with D52, because the G3 box uses the §7.5 total interval.
- D45 with the §7.4 rules of D57.
- §19-g9 with §19-3: the new §6.7 condition uses the quantity and bound of §5.4 condition 2.
- D84 with §19-g9 and the G6 rows of §8.7.
- D85 with D84 and §19-g9: the phase-3 calibration of the new P5 bounds goes with the Geant4 confirmation of §19-g9.
- D37 with D86 and D87 (both accepted 2026-11-09): which snapshot and overlay values hold φ (D87 (b)) follows the "non-negligible uncertainty" criterion of D37, still open, and decides what D86 masks.
- §19-g4c with the M1 decision of 2026-11-09: both concern what g4sim's digitization job (S8), which takes efficiency vectors as data, is used for; the decision adopted the job for U in the fixed-map mode. Resolved on 2026-11-10: the PDE split uses the same job (route 2₁ of §6.7 "PDE split").

---

## Phase 0: abstract model and contracts

### (a) Author decisions
None.

### (b) Rules settled by computation
None.

### (c) Accept? (reading supplied by the reviewer)
- **D5** (§2.1, §9.2). Reading: the sub-shape left after a bin is excluded from a free-ω count shape is a new free-ω shape. The contract declares its own N_decl with a recorded basis, and N_decl ≥ 10 is required. A missing declaration means rejection. Why conservative: an undeclared total can never pass, and the cross-validation equality check against the known total still applies.
- **D11** (§10.1). Reading: add k, k₀ and the unused-observable list with reasons to the `calibration-result` schema. Why conservative: §5.2 and §9.5 already require these values, so the reading only adds fields and changes no decision.

### (d) Accept (accepted by the author on 2026-11-09, except D68)

| Item | One-line proposal | Status |
| --- | --- | --- |
| D15 | Add "effective ≤ own grade" to the I6 text. It holds by construction, and the reference implementation already tests it. | accepted 2026-11-09 |
| D20 | K′ = 1 for an unconditioned absolute-count shape: the excluded bin goes on the unused list, and the rest enters as a Poisson count. | accepted 2026-11-09 |
| D22 (+D64) | k = 0 with the data-side check triggered gives `final` ("failure takes precedence"). The C.1 wording of D64 follows. | accepted 2026-11-09 |
| D23 | C.1 adds the failed ratio test before holdout opening, as the edition has it. | accepted 2026-11-09 |
| D24 | In §15.3.11, "k = 0" means k₀ = 0, as the edition has it. | accepted 2026-11-09 |
| D27 | Clause 9 item 9 and the §14 row: add the qualifier "sample entirely in validation data", and declare the relation as N_d or N_d,c in samples with calibration observables. | accepted 2026-11-09 |
| D32 | "At least one alternative hypothesis" applies only when the mode is not `none`. | accepted 2026-11-09 |
| D38 | K′ < 2 in alr/ilr and conditioned shapes: K′ = 1 leaves the whole shape unused. | accepted 2026-11-09 |
| D60 | Failure records and the 3f comparison use all raw units of the calibration releases on both sides. | accepted 2026-11-09 |
| D63 (+D13) | Define the "outcome already determined" lookup as C.2 then C.3, over all combinations, and add exhaustive tests to the reference implementation. | accepted 2026-11-09 |
| D66 | The contract declares c_j of the data-side check with n_j, and a schema field is added. | accepted 2026-11-09 |
| D69 | Before T_cv exists, every record of another κ counts as earlier, and the input is evaluated again at the T_cv read (now also in Appendix C.1). | accepted 2026-11-09 |
| D74 | Holdout eligibility uses the proposed wording of "never read". | accepted 2026-11-09 |
| D78 | Use the identifiers `not-applicable` and `no-testable-direction`, as proposed. | accepted 2026-11-09 |

---

## Phase 1: evaluation and design stage

### (a) Author decisions
None.

### (b) Rules settled by computation
None.

### (c) Accept?
- **D37** (§2.2, §5.2). Reading: ψ has a "non-negligible uncertainty", and must be listed as φ, when its effect on θ̂ propagated via A exceeds 0.1σ_tot^design. This is the same bound as §5.4. The phase-0 checker checks only the declarations. Why conservative: it reuses an existing bound, and a ψ above it is forced into φ, which is the stricter treatment.
- **D41** (§3.3, §6.7, §7.1, G4). Reading: N_eff,k is computed over the events that enter observable k (its bin for counts). Until you define the "determining region", the checker rejects any P5/G4 decision on a tail-type functional. Why conservative: an undefined case is refused, not guessed. The toy detector has no tail functional, so nothing is lost before phase 3/4.
- **D42** (§6.7, P5 row and note 3). Reading: take the "add" option, adding "V_MC,kk ≤ f·V^unc_data,kk for each Gaussian-block observable" to the P5 row and note 3. Why conservative: P5 gains a condition. The "delete" alternative would drop one.

### (d) Accept (accepted by the author on 2026-11-09, except D68)

| Item | One-line proposal | Status |
| --- | --- | --- |
| D53 | The Bonferroni z of P0 and P6 is two-sided, z_{1−α/(2M)}. | accepted 2026-11-09 |
| D76 | Move the §8.7 rows for τ_num, the rounding condition and n_min/B to phase 2, which is consistent with §17. | accepted 2026-11-09 |
| D77 | N_obs in P2: n_c is the dimension of the calibration data vector (K per count shape, K − 1 per Gaussian shape, 1 per scalar), excluding unused observables. | accepted 2026-11-09 |
| D80 | `calib_design.py` owns the Sobol points and the P6 held-back set, and `calib_emulator.py` owns the surrogate training set. | accepted 2026-11-09 |

### Other
- §19-g2 (plugin fact). g4sim delivers no calibration design-point generator, so this workflow generates design points (§6.4, D80).

---

## Phase 2: engine and validation

### (a) Author decisions (class 6)

**D39: cross-group correlation kernel when ℓ differs (§5.4)**
- Option (a): a convolution (Paciorek–Schervish) cross-kernel, with ρ restricted to squared-exponential or Matérn.
  - Positive definite whenever C is.
  - A closed form exists for these families.
  - Other ρ families are excluded.
- Option (b): a linear model of coregionalization.
  - Positive definite by construction.
  - Reparametrizes f, C and ℓ, so the §5.4 contract declarations change.
- Option (c): require C_{c_i c_j} = 0 when ℓ differs.
  - The simplest option, and safe on the toy detector.
  - Drops correlated discrepancy between groups with different ℓ.
- **Recommendation: (a).** Use (c) as the interim if phase 2 starts before the form is written.

**D47: "68% region of θ̂" in G3 (§8.2 G3, §7.5)**
- Option (a): the box of the per-parameter total intervals of §7.5, including the shift terms and Σ_boot/w.
  - Consistent with the reported intervals.
  - Depends on D52.
- Option (b): the bounding box of the joint region q ≤ χ²_{d,0.68}.
  - Larger for d ≥ 2, so G3, a mandatory gate, fails (`failed`) more often.
- Option (c): the joint region itself, tested point-wise against the three limits.
  - Costlier, and lies between (a) and (b).
- **Recommendation: (a).** Choose (b) only if the sampling limits must cover joint excursions.

**D50: a failed ratio test gives `failed` for G7/G8/P5 but `incomplete` for the interval, V and P7 ensembles (§7.3, §14.1)**
- Option (a): keep the difference and state it in §7.3.
  - G7, G8 and P5 test the procedure on MC, so non-convergence is legitimately a gate failure (remedy: plan).
  - Ensembles on the actual data stay numerical (`incomplete`).
- Option (b): align everything to `incomplete`.
  - A procedure that never converges is then never rejected by G7/G8/P5.
- Option (c): align everything to gate failure.
  - Numerical trouble on the actual data becomes a grade.
  - Contradicts "a numerical failure is not evidence that the data do not fit the model".
- **Recommendation: (a).** Decide it together with §19-14.1a.

**D52: which ±1σ shift response enters the intervals, d_l and G_s (§7.5, §9.2, §10.4, §5.5)**
- Option (a): the symmetric difference ½[Δ(+) − Δ(−)] everywhere.
  - One linear column.
  - Can understate the interval widening by up to about 15% under the asymmetry G9 allows.
- Option (b): max(|Δ+|, |Δ−|) for the interval widening, and the symmetric difference for d_l and G_s.
  - The widening is conservative, and the linear maps stay well defined.
  - The §5.5 normalization s_i then differs from the §7.5 total error. §5.5 now says so (Appendix E item 261).
- Option (c): asymmetric intervals for each sign.
  - Most code.
  - Asymmetric columns do not propagate through §10.4.
- **Recommendation: (b).** For toy-calibrated intervals, accept the proposal: the half-width replaces σ_q, with no Σ_boot/w term.

**D55: G8 boundary injection distance and pseudo-data resampling (§8.4)**
- Size, option (a): follow the data's sampling model (Poisson around the exposure for unconditioned counts, fixed N_tot,s for conditioned samples).
- Size, option (b): always fixed at the data size.
  - For free-ω count shapes, the closure test then does not reproduce the fit's sampling model.
- Distance, option (i): 0.5σ_tot^design from the boundary.
- Distance, option (ii): on the boundary.
- Distance, option (iii): the point where the boundary is first active in ≥ 50% of toys. This needs a search.
- **Recommendation: (a) with (i), resampling with replacement.**

**§19-14.1a: do reproducible numerical exceptions (`LinAlgError`, NaN, out-of-domain refusal) count as non-convergence? (§7.3, §14.1)**
- Option (i): keep the provisional rule, under which any exception makes the ensemble or fit `incomplete`.
  - Conservative.
  - A single reproducible exception blocks a G8 or Σ_boot ensemble permanently.
- Option (ii): count the exception as `not-converged`.
  - It enters X and the ratio test.
  - Class 1 fits then fail G1/G9.
- Option (iii): (ii) for Class 2 ensemble members, `incomplete` for Class 1 single fits.
- **Recommendation: (iii).** It matches the plugin's own convention for fit verdicts ("counted, never dropped"). Decide it together with D50.

### (b) Rules settled by computation, tagged "to be confirmed by the author"
- **D4** (§9.2). Rule: ρ_i^obs of a derived quantity is the half-width of a guaranteed enclosure over the rounding box (outward-rounded interval arithmetic intersected with the mean-value form). Evidence: exact for linear relations. There were 0 false triggers in 12 × 10⁶ correct releases (3 significant digits and fixed decimals, decimal crossings included), and every value shifted by ≥ 2× the larger bound was caught. The first-order bound was exceeded at rates up to 2.5 × 10⁻³. **Confirm.**
- **D30** (§2.1, §6.6, §6.7, §8.7 note 4, Appendix A). Rule:
  - variance-matched n_eff and k_eff;
  - randomized rounding of n_eff in toys;
  - the approximation's scope is k_exp ≥ 30 and Δ_sk ≤ 0.1, computed from a design-stage MC sample that is now in the §6.6 non-overlap check and the §6.7 budget (items 270–271);
  - outside that scope the approximation is "unvalidated".

  Evidence: 175 of 175 configurations pass the §8.7 acceptance on fresh seeds. The Kish variants fail when Σw²/Σw differs between pass and fail. **Confirm.**
- **D57** (§7.4, §7.5, §8.7 note 6, §15.1 bimodal variant, §15.2). Rule:
  - max(2d, 16) Sobol starts;
  - admission σ_tot ≤ σ_prior;
  - separation by the barrier along the segment, τ_bar = max(0.1, 4σ_noise);
  - θ̂ is the lowest basin, with ties within τ_tie = max(0.01, 4σ_noise) broken lexicographically;
  - every toy runs the same multi-start;
  - the union interval is toy-calibrated when `multimodal`.

  Evidence: the classification is stable under 10 reseedings (1.000 at d = 3, σ_noise = 0). The triage's design value was rejected because it merges exactly degenerate basins. The σ_noise terms, the ln det comparison and the per-basin iteration are reasoned rules, not computed (§7.4 lead, item 257). **Confirm.**
- **§19-2 (with D29)** (§5.5 condition 2, §8.2 note 10, §8.7 note 5; tag "blocks no phase", but G9/P8 code it in phase 2). Rule: Δ_i ≤ t_lin = 0.06 replaces "30% symmetry" and "2 ± 0.3". c = 0.1 is kept, and the recomputation at θ̂ uses 1.5c. Evidence: the relative tests rejected harmless or conservative nonlinearity with probability 1, and passed an expansive cubic response with 95% coverage 0.922. **Confirm.**
- **§19-3** (§5.4 condition 2, §15.3.9; tag "blocks no phase", coded with G6 in phase 2). Rule: tr(V_G⁻¹V_⊥) ≤ 0.05, in addition to the 99% truncation. Evidence: truncation never lowers G6 power. The 99% rule alone raises the G6 size to up to 0.75 at α = 0.01, and condition 2 holds it at ≤ 1.1α for every ndf ≥ 3. **Confirm.**
- **§19-13** (§8.2 P5 note 3 item 4, §14, §15.3.1, §17; tag "blocks no phase", now a phase-2 deliverable per §17, item 274). Rule: |b_J,i| ≤ 0.15σ_tot,i^design (Gaussian blocks). Evidence: without the rule, 68% coverage dropped by up to 0.031. With it, the extra undercoverage is ≤ 0.008. **Confirm.**
- **§19-14.1f** (§9.3, §14.1, §9.5 table and §7.3 exceptions of items 250–251). Rule:
  - the summed G5 proportion is decided at the end of every attempt, including one that ends in a failing ratio test;
  - a proportion > 20% there gives `incomplete`, remedy plan, with no redo;
  - within an attempt, renewal stops at F_G5 > 0.25(Σ_a n_req + X_max).

  Evidence: an exhaustive enumeration for n_req ≤ 200 gives OVERALL PASS, and the rerun is byte-identical. Without the end-of-attempt decision, no stop point based on F_G5 is certain. **Confirm together with D3 (c) and D68 (d).**

### (c) Accept?
- **D1** (§9.2, §9.3). Reading: when the fold split makes rank condition (c) fail, the remedy level is the plan. Why conservative: §9.3 states that cause explicitly, and neither reading produces T_cv or a grade.
- **D2** (§9.4, §9.5). Reading: one power lower bound < 0.8 plus another bound that cannot be computed gives "insufficient power" (the cap `calibrated-unvalidated`). Why conservative: the "outcome already determined" principle applies, because no value of the missing bound could make P7/V pass.
- **D3** (§9.5 table). Reading: `incomplete` either way, reporting the remedies of every matching row. Since this pass, the computed rule needs this case resolved toward the plan remedy with no redo (items 250–252). Why conservative: there is no grade effect, and the plan remedy is the stricter one.
- **D8** (§5.2 merging). Reading: the contract is rejected (exit 2) with the observable named. Why conservative: rejection rather than silent removal, matching "a contract that still does not comply is rejected".
- **D9** (§6.6, §6.7, §7.3). Reading: add G2 toys to the bootstrap budget (n_G2), to the non-overlap enumeration and to the §7.3 list, as for G6. Why conservative: more budget and more checks.
- **D10** (§5.2 clause 6). Reading: the lock-time N_d,c decision is provisional, and the binding redo at θ̂ with the actual V_G is a contract error before opening. Why conservative: plan content cannot produce a pass without basis.
- **D19** (§8.4). Reading: the G8 interval toys "per the previous item" means item 2 (the interval toys). Why conservative: it is the only reading consistent with the section.
- **D25** (§2.1). Reading: the `expected` statistical component is recomputed with count-type errors and the bootstrap. Why conservative: it is consistent with "always recomputed from the prediction at θ_ref".
- **D29** (§5.5, G9). The proposed relative reading is superseded by the §19-2 rule in (b). Accept that replacement. Why conservative: the relative tests were shown to misfire both ways, and Δ_i is one-sided and absolute. An equivalent two-measure variant is listed under "still open".
- **D34** (§2.1, §7.3). Reading: the bootstrap p and B apply per sample, and V̂ is block-diagonal with the bias factor (B − 1)/(B − p_s − 2) per block. Why conservative: the samples share no events. The reviewer was unsure only about the summed (p − d)/B statement, which should use Σ_s p_s.
- **D40** (§7.3, P5, G7). Reading: recompute Σ_MC and Σ_data at β̂ for G7 and for reporting only, and do not decide P5 again. Why conservative: G7 is the post-fit check, and P5 stays a design gate, so nothing is re-selected after the fit.
- **D45** (§7.3, §7.4, G1). Reading: multi-start in every iteration, and an EDM failure counts as non-convergence. Why conservative: more non-converged members are counted. It must be reconciled with §7.4 (one multi-start, then §7.3 per basin), which D45 now notes (item 259). The cost of G8 and Σ_boot is unsure.
- **D46** (§18.2, §7.3, §6.7). Reading: non-converged full G6/G2 toys count as T_toy < T_obs, each full toy has its own regenerated bootstrap, and the budget gains n_G6,full + n_G2,full. Why conservative: the counting goes in the direction unfavorable to passing.
- **D48** (§7.5). Reading: "multi-parameter" means a joint region, so d ≥ 2 alone does not force toy-calibrated intervals. Why conservative: this is less strict than the alternative, but G8 tests the coverage of the interval actually used, so no grade results without basis.
- **D51** (§7.3). Reading: the convergence criterion uses the max-norm over components and the current curvature of that fit, with threshold 0.2 for ln det. Why conservative: the max-norm is the strictest norm.
- **D58** (§7.5, §9.2, §9.4). Reading: the criteria for "low counts", "active boundary" and "nonlinearity" are as proposed, and "active boundary" reuses `boundary-solution`. Why conservative: they send more cases to the toy path.
- **D67** (§9.2). Reading: S is evaluated at the fit point with the expected total, and is not re-evaluated after opening. Why conservative: it is fixed before the data are seen (as for C_r). The reviewer was unsure whether you meant θ_ref for the P7 design check.
- **§19-14.1b** (§6.7, §7.3, §14.1). Reading: a budget revision keeps κ, and the redo blocks are pre-reserved by the allocation function. Why conservative: the members are fixed by identity, so the outcome cannot be selected. Anything that changes n_req, the allocation or the intervals is a new κ.
- **§19-14.1d** (§5.1, §14.1). Reading: the execution environment is not in κ, but every ensemble and fit runs in one recorded environment, otherwise `incomplete`. Why conservative: reruns on other hardware are closed by the failure records and the bitwise rule of §19-14.1c. The stricter alternative (environment in κ) is impractical.

### (d) Accept (accepted by the author on 2026-11-09, except D68)

| Item | One-line proposal | Status |
| --- | --- | --- |
| D7 | P5 uses Σ_boot / w everywhere. This is already in the body, settled by computation (the raw form broke the §6.7 guarantee in 24–96% of near-binding passes). | accepted 2026-11-09 |
| D16 | "All three shapes": keep the four as listed. | accepted 2026-11-09 |
| D18 | Per-fold convergence acceptance uses the §8.7 scope, which is broader. | accepted 2026-11-09 |
| D21 | `calib_data.py` does the recomputations and `calib_contract.py check` does the N_d,c redo; align the executor paragraph of §5.2. | accepted 2026-11-09 |
| D33 | Use the proposed complete joint-likelihood formula (φ shift, correlated φ_P, MC auxiliary terms, ω). | accepted 2026-11-09 |
| D35 | The σ⁽⁰⁾ = 0, ρ = 0 removal applies under holdout and under `none`. | accepted 2026-11-09 |
| D36 | Include the profile-mode φ axes in the evaluation points. | accepted 2026-11-09 |
| D49 | n in the toy p-value is n_req (the total). | accepted 2026-11-09 |
| D54 | R_corr is the θ block of F⁻¹; σ_prior of a uniform prior is range/√12. | accepted 2026-11-09 |
| D56 | Δχ²_full, Δχ²_lin and "the two end folds" as proposed. | accepted 2026-11-09 |
| D59 | Power lower bound: Bonferroni α_P/m, split one-sided, Clopper–Pearson, and a new §8.7 row for the cross product. | accepted 2026-11-09 |
| D61 | Use the proposed rule-0 wording: power toys > 20% give "power lower bound not yet computed", and P7 toys make P7 `incomplete`. | accepted 2026-11-09 |
| D62 | The failure-record sentence covers only the check at holdout opening; at lock, the contract is rejected with no record. | accepted 2026-11-09 |
| D65 | CV power toys run only after T_cv. | accepted 2026-11-09 |
| D68 | **Excluded from the blanket instruction; still open.** Proposal: the denominator is the toys with G5 decided, which gives the earlier stop F_G5 > 0.25·Σ_a n_req. Recommend accepting it, explicitly and together with §19-14.1f and D3. | open: excluded, decide with §19-14.1f and D3 |
| D70 | No rounding term in the residual-identity tolerance. | accepted 2026-11-09 |
| D71 | Use the proposed wording "leave the whole shape unused … when not possible". | accepted 2026-11-09 |
| D72 | Add the two missing §9.5 table rows. | accepted 2026-11-09 |
| D79 | tol in the G1 EDM threshold is the minimizer tolerance declared in the plan. | accepted 2026-11-09 |
| §19-14.1c | "Exact recomputation is reproducible" means bitwise-identical numerical fields in the same recorded environment. | accepted 2026-11-09 |

### Other
- **§19-14.1e** (plugin fact). Settled by `core/partition/states.py`: "not yet decided" is safe for correctness. The wait is unbounded until a human acts. This pass corrected the triage's justification, which had the order of checks and "bounded wait" wrong (items 253–254).
- **D81** (not triaged; §7.3, §14.1). Proposal: state that a redo whose carried X already reaches k*(N_tot) is not registered, and that the ensemble is `incomplete` under that κ (remedy plan). Why conservative: it states an outcome the rules already force. Recommend accepting it.

---

## Phase 3: surrogate model and g4sim evaluator

### (a) Author decisions

None open. **§19-g4c is decided by the author (2026-11-10)** (§19 PDE item; rules in §6.7 "PDE split"; Appendix E items 692–726): the PDE may be split out of the efficiency map when the PDE model is exactly the sensor surface's `EFFICIENCY(E)`. The map is built with sensor `efficiency` = 1; a wavelength-independent PDE p is written as p·ε_c into the efficiencies of `g4sim-digi-job/1` (route 2₁); a PDE(E) weights the efficiency-1 map by photon energy from the mapping run's `photons.csv` (route 3); when p is θ, every readout system with an observable not linear in ε uses a per-photon thinning nested in p (route 1); a split check with a nested pair of mapping runs (efficiency 1 and the nominal PDE, same seed and events) is required; resimulation stays allowed and is the fallback. Evidence: en/research-PDE.md (`synthetic`; Geant4 not run) and en/pde-geant4-check.md (source reading of Geant4 and g4sim 0.65.0/0.65.1); verified in three independent rounds (en/pde-verify.md, en/pde-verify2.md, en/pde-verify3.md). New design values of the split check and the route-3 replicas are in §8.7 (phase 3, `provisional-thresholds`); D83 gains the proposed upstream requests (20)–(23).

### (b) Rules settled by computation, tagged "to be confirmed by the author"
- **§19-g9** (§6.7 local dimension reduction; computed on the synthetic ZDC fixture with the g4sim S7 map builder and replica sampler, Geant4 transport not run). Rule: m is the smallest number of directions for which both (1) the 1% rule per observable and (2) s_⊥ = tr(V_G⁻¹ U_⊥U_⊥ᵀ) ≤ 0.05 per study hold (the quantity and bound of §5.4 condition 2). Evidence: with the 1% rule alone, a joint fit of two reducing studies that share φ_map lost 0.11 ± 0.008 of G6 power at the plan's map/data error ratio 0.7–0.9, and up to 0.80 when the map dominates, with 68% coverage changes up to 0.045 and G8 failing where the full basis passed. With condition 2, all 1160 runs on the 53-bin map met the acceptance: power loss ≤ 0.013 ± 0.004, |Δcov68| ≤ 0.004, no new G8 failure, and m stays well below n_obs. The k/n centre of §6.7 (S7 M1) was also confirmed: with the replica mean the bias of ln LY reached −0.48 σ_tot. Open: confirmation with a real Geant4 mapping run. **Confirm.**

### (b′) Requirements settled by plugin source: accepted by the author (2026-11-09)
These 23 rules of phase 3 (16 from the binding and S7 checks, 7 from the S8/S9 check; the eighth S8/S9 rule is under phase 4) are imposed by this workflow because of how the g4sim sources work. **All were accepted by the author on 2026-11-09** (Appendix E items 637–691); their tags in the spec now read "(accepted by the author, 2026-11-09; source en/…)". From the g4sim binding check (v0.62.0):
- **A1, A3 (D31)** [accepted 2026-11-09] (§6.6 check). `run_seed` = `logical_run_seed` in every evaluation, and the `logical_run_seed` values are pairwise distinct, checked on the block registry (S_b, t). Evidence: the Philox key comes from `run_seed` (`rng.py`); H lies in [1, 2³¹ − 1], so 10⁴ seeds collide with probability about 2%. This was the open part of D31, closed by this acceptance.
- **A3** [accepted 2026-11-09] (§14.1 allocation function). One seed per block, and m_blk·N_ev ≤ 2³². Evidence: g4sim allows at most 2³² global events per seed (`rng.py`).
- **A7** [accepted 2026-11-09] (§5.1 model identity). The Geant4 version and the data-set versions belong to the identity. Evidence: `build_hash` hashes only the executable.
- **A5** [accepted 2026-11-09] (§11.4 Table 2). θ binds to the LY and r of the `response-pipeline/1` scintillation stage. Evidence: `response.py` reads them there.
- **A19** [accepted 2026-11-09] (§14.1). Run records are not placed in a design artifacts directory. Evidence: `contracts/design.py` C2.1 refuses a repeated `logical_run_seed` outside one `seed_group`.

From the g4sim S7 check (v0.63.0, `g4sim-S7-check.md`):
- **M1** [accepted 2026-11-09] (§6.7 nominal map). Predictions use ε_0 = k/n (replica 0); the basis uses only the replica spread. (Its former third clause, predictions at ε_0 + B_map φ_map formed linearly from U, is replaced by the author's decision of 2026-11-09; see the note below.) Evidence: g4sim's replicas are centred on the Jeffreys mean; confirmed by en/compute-19-g9.md (replica-mean centre: bias up to −0.48 σ_tot, G8 fails on bias).
- **M2** [accepted 2026-11-09] (§6.6). `replica` = 0 in every evaluation, and no response stage is named `efficiency_map/<k>`. Evidence: a non-zero `replica` also selects Dirichlet replica r of a mapped map (`response.py`).
- **M3** [accepted 2026-11-09] (§11.4 full optical tracking path). A PDE(λ) after transport only as this workflow's thinning of `photons.csv` rows, with surface `efficiency` 1. Evidence: g4sim has no response stage for it (C3).
- **M4** [accepted 2026-11-09] (§5.4 multi-component row). This workflow digitizes a multi-component material itself and measures d_a in its own paired comparison. Evidence: `scintillation_event` takes one map, and `validation_response_findings` refuses more than one component (C19).
- **m2** [accepted 2026-11-09] (§6.7 registration key). The map document is never rewritten; the key holds `map_sha256`, R and `CORE_VERSION`. Evidence: any change of the bytes changes every replica.
- **m3** [accepted 2026-11-09] (§6.6 check item 1). Mapping runs are in the non-overlap check; within a θ scan with the shared seed of D28 the design points share one (`logical_run_seed`, interval) by design.
- **m4** [accepted 2026-11-09] (§5.4 efficiency-map row). The full optical run of the comparison meets g4sim's validation conditions. Evidence: `validation_findings`, `validation_response_findings`.
- **m7** [accepted 2026-11-09] (§15.1 ZDC fixture). The optical extension of the fixture (optical crystal, gap volume, SiPM skin with `efficiency`, `optical_scope`, single-cell mapping specification, C22).
- **m8** [accepted 2026-11-09] (§11.4 Table 2 optical row). A mapping run per design point; the production run uses the same materials (`map-stale`) and is resimulated; the mapped template is a box placed once, unrotated (C22).
- **m9** [accepted 2026-11-09] (§5.1 masked hash). The map hash and the mapping-run settings in the identity; the plan records the mapping run's `run_id`, seed and interval itself. Evidence: `hashes.mapping_run_id` holds the `request_id` (D83 (4)).
- **§4 (U = M V)** [accepted 2026-11-09] (§6.7 propagation). U from re-digitizations at the replicas with `replica` = 0 and `map_replica` = r, U = M V; when μ is not linear in ε, U is defined as M V. Evidence: exact for linear μ; the non-linearity was negligible in en/compute-19-g9.md (1 − R² ≤ 7 × 10⁻⁵).

Note on M1: **decided by the author on 2026-11-09** ("the fixed-map mode need not keep the linear construction"; applied in Appendix E items 619–636). In the fixed-map mode U may be obtained by digitizing at each replica's per-bin efficiencies through `g4sim-digi-job/1` (`replica` = 0, otherwise the nominal job; the same rules as the joint-pattern replicas: keys checked for jobs without conditions, Python only for jobs with conditions, one digitization path within a readout system). The linear construction U = J B_map is an option only for observables linear in ε, recorded per observable in the plan and rejected by `calib_design.py` otherwise. The k/n centre is kept. Cost: R digitization jobs per construction of U where the linear construction takes none (§6.7, §14.1, D84). The decided text carries no tag; the M1 tag now covers only the k/n centre above (§6.7, C20), which was accepted on 2026-11-09 with the other (b′) rules.

From the g4sim S8 and S9 check (v0.65.0, `g4sim-S8-S9-check.md`), formerly tagged "(settled by plugin source, en/g4sim-S8-S9-check.md; to be confirmed by the author)", now "(accepted by the author, 2026-11-09; source en/g4sim-S8-S9-check.md)"; seven in phase 3 here (the last two added by the verification `d28-s89-verify.md`), the eighth under phase 4:
- **Job route for g4sim's own replicas** [accepted 2026-11-09] (§6.6 "`replica` is always 0", inside the M2 rule; W10). g4sim's own map replica r may also be evaluated by writing `efficiency_map.efficiencies(map, bin, r)` into a digitization job's `efficiencies`, with `replica` = 0. Evidence: `digitize.py` takes per-bin efficiencies as data, and `replica` enters only the keys.
- **Checks of every digitization job** [accepted 2026-11-09] (§6.6 Check; W10, W18, D31; corrected by `d28-s89-verify.md` M1). `calib_design.py` checks the job's `run_seed` = `logical_run_seed`, `replica` = 0; for a job without conditions, its `keys` equal those `digitize.job_with_keys` computes; a job with conditions carries no keys and is digitized in Python only; and, with conditions, `event_time_ns` against the event-time rule the plan records (D87 (h), accepted 2026-11-09). Evidence: `g4sim_digi` uses the precomputed keys and never reads `run_seed` (`g4sim_digi.cc`); `job_with_keys` refuses a job with conditions (`digitize.py` 88–89).
- **`g4sim_digi` hash in the execution record** [accepted 2026-11-09] (§14.1 plan/record table; W11). Evidence: no g4sim record hashes the `g4sim_digi` executable; `build_hash` covers `g4sim_run` only.
- **Pilot with the ensemble's response implementation; conditions in Python only** [accepted 2026-11-09] (§14.1 "Budget and scheduling limits"; W12). Evidence: on g4sim's registered workload Python took 3.44–3.57 of the transport and `g4sim_digi` 0.21–0.23 (0.78–0.80 with per-photon times); `job_with_keys` refuses a job with conditions.
- **A misaligned geometry enters phase 3 or 4 only with a recorded overlaid run** [accepted 2026-11-09] (§17; W14). Evidence: `geant4_run.py run-spec` takes no overlay (C25, D83 (7)).
- **One digitization path within an ensemble** [accepted 2026-11-09] (§6.6 "Common random numbers"; `d28-s89-verify.md` m5). Within one readout system, all evaluations of one ensemble and all re-digitizations of one batch of events use the same path (`g4sim-digi-job/1`, in Python or `g4sim_digi`, or not). Evidence: the job path counts channel streams by volume ID × C + c (`digitize.py` 152), the other path by the readout's cellID, so mixed paths share no sensor or electronics noise.
- **Every digitization job built from and checked against the hashed documents** [accepted 2026-11-09] (§5.1 `response-pipeline/1` item, §14, §14.1, §15.3.19; `d28-s89-verify.md` m6). The job's stage, sensor, electronics, timing and channels equal `response-pipeline/1` at the evaluation's θ, its efficiencies are the map's or the declared replica's, its `conditions` are the snapshot, and its SHA-256 is in the execution record. Evidence: a job duplicates these parameters, has no schema and no builder (D83 (14)) and is not hashed for the model identity, so a job built with other values would run under an unchanged identity.

### (b″) Choices of the D28 verification: accepted by the author (2026-11-09)
These 3 choices go beyond `research-D28.md`; they belong to D28 (accepted) (`d28-verify.md`, Appendix E items 517–543). **All three were accepted by the author on 2026-11-09** (Appendix E items 637–691); their tags now read "(choice of the D28 verification, accepted by the author, 2026-11-09; source en/d28-verify.md …)".
- **Joint-replica digitization** [accepted 2026-11-09] (§6.7, "Predictions at a joint-pattern replica"; major 1 as corrected). A joint-pattern replica is digitized through `g4sim-digi-job/1` with `efficiencies` ε_j^(r) and otherwise the nominal job (`replica` = 0), so U_j = M_j/√(R − 1) also holds for observables not linear in ε; `calib_design.py` checks once per scan that the job reproduces, event by event, the photoelectrons of `response.scintillation_event` with `map_replica` = r for g4sim's own replicas (charge and code are not comparable, `d28-s89-verify.md` m2). Evidence: `digitize.py` takes per-bin efficiencies as data and draws the photon streams as `response.scintillation_event` does; the report's alternative (a linear J_j(ε − ε̄), with non-linear observables sent to the fallback) rested on the premise that no such entry point exists.
- **C of the θ-noise item** [accepted 2026-11-09] (§8.2 note 3, fifth item; major 4). C = V_G + Σ_jl w_j w_l Σ_jl, so V_MC, V_emu and V_learn enter C. Evidence: the study had no MC noise (C = V_data + V_map, `emulator_noise.py`); V_G is the fit's Gaussian-block covariance.
- **Repetitions of the §8.7 θ-noise calibration** [accepted 2026-11-09] (§8.7 row; minor 9). At least 2000 repetitions per configuration (se of the pull sd ≈ 0.016). Evidence: the study's P ensembles had N = 2000; the criterion is a pull-sd excess of 0.05.

### (c) Accept?
None.

### (d) Accept (accepted by the author on 2026-11-09, except D68)

| Item | One-line proposal | Status |
| --- | --- | --- |
| D17 | §19 "1% of the trace" yields to the per-observable rule of §6.7. | accepted 2026-11-09 |
| D28 | "Independent" means independent of the other uses; mapping runs share a seed within a θ scan, and map errors must not be treated as independent across points. Revised (en/research-D28.md): the shared seed is the default, conditional on workflow-drawn joint-pattern replicas keyed by the scan (or the analytic covariance for observables linear in ε), one φ_map for the scan profiled through the surrogate model; independent seeds only when the new P5 θ-noise item (s_i ≤ 0.25, κ_i ≤ 0.05, design values) passes; fallback: the nearest design point's replicas, full correlation assumed; the event interval [0, N_map) is now adopted (it left b′). Note in §6.7: true map errors highly correlated (≈ 0.89), g4sim's replicas uncorrelated (0.013 ± 0.079). Open points: D85. | revised and accepted 2026-11-09 |
| D43 | The threshold for a "non-negligible U_⊥ component" in Poisson and binomial blocks is τ_num (a variance, per observable). | accepted 2026-11-09 |
| D44 | The P3 remedy level in the map-varies-with-θ mode is the plan. | accepted 2026-11-09 |

### (d′) Accepted by the author (2026-11-09), not triaged

| Item | What was adopted | Status |
| --- | --- | --- |
| D86 | Model identity of alignment overlays and condition snapshots (§5.1): the overlay folded into the masked detector-spec item (stripped of `description` and `source_of_facts`, θ/φ entries masked; the item is the pair of hashes; the IR's `alignment` field never hashed); the snapshot, with the plan's event-time rule, folded into the `response-pipeline/1` item; five items kept (the sixth-item alternative not adopted); a plan that varies alignment applies an overlay at every design point, the nominal one included. | accepted 2026-11-09 |
| D87 | Statistical roles of conditions and alignment (§11.4 "Conditions"): known `gain_factor`/`threshold` → ψ; with a non-negligible uncertainty (criterion of D37, still open) → φ by the JSON Pointer of the snapshot row, re-digitized in Python only; calibrated per channel and IOV → θ, "piecewise independent" on the snapshot's IOVs (a common gain binds to the `sensor` stage); `dead` never θ or φ; `temperature_K` no role; overlay shifts and rotations → θ or φ at the resimulation level, an overlay at every design point; reconstruction-side alignment → θ of nodes 6–7; the plan records each event's time. | accepted 2026-11-09 |

### Other
- Plugin facts (settled; for information):
  - D31 (its open part, the response-layer requirement of b′, was accepted on 2026-11-09; nothing of it remains open);
  - D75 (Birks: deterministic rerun, no event weight, G4 does not apply);
  - §19-g3 (no split-error bound under k_B; the §5.4 fallback is the rule);
  - §19-g4a (no stage 2→3 hand-off);
  - §19-g4b (settled by plugin source (S7): ε_c includes the PDE, the sensor surface's `efficiency`; the outdated `$comment` is D83 (2)).
- Deferred to phase 3:
  - D6 (weighted truth MC for G8 pseudo-data);
  - §19-5 (G8 with surrogate pseudo-data);
  - §19-8 (non-local degeneracy; the RICH replica);
  - §19-9 (C++ density kernels in phase 3; the classifier/SBI boundary in phase 5);
  - §19-g5 (derived fields of the model identity: integration tests).
- Not triaged:
  - D83 (g4sim defects to raise upstream; (1), the built map failing its own `efficiency-map/1` schema because of `form.uniformity`, blocks a schema check of mapped maps; (1)–(6) are all still open in v0.65.0). Proposal: raise (1)–(19) upstream (since 2026-11-10, (1)–(23): items (20)–(23) of the PDE split, which block nothing); how this workflow's checks treat a built map until g4sim fixes the schema is for you. (6), added with the D28 revision, asks g4sim to document that replica keys are per map (a scan key is explicitly not requested) and blocks nothing. (7)–(19), added with the S8/S9 check: (7) no recorded run of a misaligned geometry (`run-spec` takes no overlay) blocks a misaligned geometry in phase 3 or 4; (8) the overlay hash mixes sources into `geometry_id` (blocks nothing: D86 strips them); (9) `g4sim_digi` silently ignores conditions, which blocks a phase-3 evaluator that sends conditions jobs to C++; (10) reconstruction uses the true misalignment, which blocks the §3.6 reconstruction-side alignment study with a misaligned simulation; (11)–(19) (dead channels keep charge, invisible fast-simulation deposits, no key check, no job schema, unvalidated snapshot defaults, linear condition lookup, no event times, ignored `temperature_K`, one overlay per IR) block nothing.
  - D84 (finite-replica noise of U: with the full basis, the G6 size reached 0.044–0.12 at R = 100 and up to 0.027 at R = 400 when the map error exceeds the data error in many independent directions, so g4sim's R ≥ 100 does not suffice there). Proposal: a design-stage G6 size check with toys that redraw the replicas (≤ 1.5α, §8.7), with R increased or the G6 reference toy-calibrated when it fails; a fixed minimum R is the alternative and needs calibration. Since g4sim S8 the re-digitization at redrawn replicas costs about 15 times less with `g4sim_digi` (except with per-photon times and conditions jobs).

---

## Phase 4: dependency graph and specialization

### (b′) Requirement settled by plugin source: accepted by the author (2026-11-09)
- **`source_of_facts` of exported condition snapshots and alignment overlays** [accepted 2026-11-09] (§10.4 "Feeding back to g4sim", §19 production use; en/g4sim-S8-S9-check.md W2, W17). This workflow writes the hash of the calibration result, with its effective grade and flags, into the `source_of_facts` of every exported `condition-snapshot/1` and `alignment-overlay/1`, and `calib_use.py` checks offline that each carries it. Evidence: `source_of_facts` is optional in both g4sim S9 schemas. Accepted by the author on 2026-11-09 (§19-g6 itself stays deferred to phase 4).

### Deferred
Deferred to phase 4. No decision is needed before then.
- §19-1: default correlation-kernel source table.
- §19-4: default alternative hypotheses per detector type.
- §19-g6: enforcement of `validated-in-scope` in g4sim.
- §19-g7: keeping results after a Geant4/g4sim upgrade via T2.
- §19-g8: posterior update and versioning of ξ.

## Phase 5: extensions

No item blocks phase 5. Two items are deferred to it but tagged "blocks no phase" (§19-12, §19-14; see "none"), and §19-9 is split between phase 3 and phase 5.

---

## None (blocks no phase)

### (b) Computed and awaiting confirmation (no rule to code)
- **D12** (§2.1, G7 example). Evidence: the frozen-V̂ baseline is exactly 0.01 (simulated 0.0104 for d = 1 and 0.0105 for d = 3), so "0.000" was wrong. The regenerated 0.033 needs the setup now stated in the text. **Confirm** the wording.
- **D73** (§9.2). The "about 6%" is a per-check false-trigger rate under the old tolerance. It is reproduced (6.1%) only with the unit at the predicted center and t 1.3σ_t below a decimal boundary; with the §2.1 window maximum, the rate is ≤ 9 × 10⁻⁷. **Confirm** the §9.2 setup statement. The §15.3.5 negative-control wording is still open; see the list below.

### (c) Accept?
- **§19-15**. Reading: accept as a documented limitation that the directional distribution of V_emu/V_learn^bias has no independent test (P6 and closure test the scale). Why conservative: no rule is relaxed. If you want a phase-3 directional test, it becomes a compute item.

### (d) Accept (accepted by the author on 2026-11-09, except D68)

| Item | One-line proposal | Status |
| --- | --- | --- |
| D14 | Symbol clashes: keep Appendix A, and use section-qualified identifiers in code (editorial). | accepted 2026-11-09 |
| D26 | Accept the recomputed numerical examples, now including §15.3.9 "0.105 → 0.096" (item 277). | accepted 2026-11-09 |
| §19-11 | Keep the current text: mislabeling of uncertainty sources is a publisher precondition, with no check from the values. | accepted 2026-11-09 |

### Other
- §19-g1 (plugin fact). The `external` source is rejected; the rule is binding. Narrowing it would be a g4sim change request.
- §19-7 (compute, ongoing). The §8.7 threshold calibrations stay under `provisional-thresholds`. First computations exist for notes 4, 5, 6 and the P5 b_J bound.
- Deferred:
  - §19-6 (cross-event effects; beyond the roadmap);
  - §19-12 (non-negligible rounding: interval likelihood; phase 5);
  - §19-14 (sharing replicas among toys; phase 5).
- **D82** (not triaged). Proposal: no rule change; state in §2.1 that P5 decides on the point estimate of Σ_boot. Recommend accepting it.
- **D85** (not triaged; tag "blocks no phase (phase-3 calibration; `provisional-thresholds`)"). Open points of the D28 revision: the unexplained pull width 1.05 under purely nested coupling; G7, toy-calibrated intervals and a φ_map shared across studies not simulated; only R = 200, one study, one optical θ; the P5 bounds from one study. Proposal: calibrate per the new §8.7 row in phase 3, with the Geant4 confirmation of §19-g9, and keep `provisional-thresholds` until then. Since g4sim S8 its re-digitizations cost about 15 times less with `g4sim_digi` (new point (6)).

---

## Still open after computation (nothing here is decided in the body)

| Item | What remains open | Phase | Suggested handling |
| --- | --- | --- | --- |
| D4 | A constraint whose enclosure is unbounded, because a lineage step divides by, or takes the log of, a box containing 0. This happens for a read value of 0 (fixed decimals) or a difference straddling 0 (any format). | 2 | Choose between "uncheckable, passes vacuously" and "reject at locking a contract whose format admits such a box". Recommend the second, which is conservative. |
| D29 / §19-2 | An equivalent two-measure variant (\|c2\|/s ≤ 0.15 and an expansive odd part ≤ 0.10) if you prefer separate even and odd tests. Also open: more than one shift-mode φ, toy-detector confirmation, the refit reproducibility check and the 1.5c margin assumption. | 2 (`provisional-thresholds`) | Keep Δ_i, and calibrate on the toy detector. |
| D30 / D33 | Reuse of the toy auxiliary measurement across θ for a θ-dependent efficiency template. Also, item 270 took the option of a separate design-stage MC for the scope decision; the alternative is to reuse the P5 design-stage MC. | 2 | Decide with D33. Keep the separate sample unless budget forbids it. |
| D57 | (1) Calibration of the tolerances, in four cases the toy did not cover: σ_noise > 0, V differing between basins (where the ln det comparison was reasoned, not computed), the coverage of the toy-calibrated interval, and the RICH replica (phase 3). (2) **For you:** the remedy level of G8 under multimodality, plan vs contract. The bias test fails on every bimodal variant, and the cause is the contract. (3) Endpoints on a physical boundary (G2) were not tested. (4) σ_prior of a uniform prior: settled by the acceptance of D54 (range/√12). | 2 (3 for RICH) | (2): recommend a §8.4 note giving remedy level contract when the pseudo-data θ̂ fall in a non-truth basin. |
| D68 / §19-14.1f | The denominator, and with it the stop threshold: 0.25·Σ_a n_req vs 0.25·(Σ_a n_req + X_max). | 2 | See D68 above. Accept the decided-G5 denominator. |
| D73 | The wording of the §15.3.5 negative control. As written, it would show no triggers; §15.3.5 now marks the rate as open (item 249). | none (test of phase 2) | Adopt the wording proposed in D73. |
| §19-3 | The effect of the discarded V_model part on the size of T_v. The extension of condition 2 to Poisson and binomial blocks was not simulated. | 2 (deliverable) | Run the T_v size study (≥ 10⁴ repetitions). |
| §19-13 | Non-Gaussian blocks (no P5 term; only G8 detects the effect); MC that is not smooth in θ; calibration of 0.15. | 2 (deliverable) | Calibrate per §8.7. |
| §19-7 | The §8.7 calibrations in general. | 1–3 deliverables | Keep `provisional-thresholds` until done. |
| §19-g9 | Confirmation with a real Geant4 mapping run of the ZDC fixture extended with optics (the computation used a synthetic detection model in place of Geant4 transport). | 3 | Run it when Geant4 is available (plan in `g4sim-S7-check.md` §4). |
| D84 | The number of replicas R: the G6 size of the full basis exceeds 1.5α when the map error exceeds the data error in many independent directions (0.044–0.12 at R = 100, up to 0.027 at R = 400). | 3 | Choose between a design-stage G6 size check with redrawn replicas (recommended) and a minimum-R rule. |
| D85 | The open points of the D28 revision (pull width 1.05 under nested coupling; G7, toy-calibrated intervals, cross-study φ_map not simulated; R = 200, one study, one optical θ; the P5 bounds s_i ≤ 0.25, κ_i ≤ 0.05 from one study). | none (phase-3 calibration, `provisional-thresholds`) | Calibrate per the §8.7 row together with the Geant4 confirmation of §19-g9. |
| §19-g4b | Nothing on the g4sim facts (settled by plugin source, S7). Only the outdated `$comment` of `efficiency_map.json` remains, as D83 (2). | 3 | Raise upstream with D83. |

## Deferred items, with their phase

| Item | Subject | Deferred to | Tag |
| --- | --- | --- | --- |
| D6 | Weighted or negatively weighted truth MC for G8 | 3 | blocks phase 3 |
| §19-1 | Default source table for f, C, ℓ | 4 | blocks phase 4 |
| §19-4 | Default alternative hypotheses per type | 4 | blocks phase 4 |
| §19-5 | G8 for resimulation-level parameters via surrogate pseudo-data | 3 | blocks phase 3 |
| §19-6 | Cross-event effects | beyond §17 | blocks no phase |
| §19-8 | Non-local or multimodal degeneracy | 3 | blocks phase 3 |
| §19-9 | C++ density kernels; classifier/SBI boundary | 3; 5 | blocks phase 3 |
| §19-12 | Non-negligible rounding (interval likelihood, Neyman) | 5 | blocks no phase |
| §19-14 | Sharing replicas among toys | 5 | blocks no phase |
| §19-g5 | Derived fields of the model identity | 3 | blocks phase 3 |
| §19-g6 | Production-use enforcement in g4sim | 4 | blocks phase 4 |
| §19-g7 | Keeping results after a simulation-identity change (T2) | 4 | blocks phase 4 |
| §19-g8 | Posterior update and versioning of ξ | 4 | blocks phase 4 |
